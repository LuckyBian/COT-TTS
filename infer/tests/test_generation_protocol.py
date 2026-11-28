"""CPU-only checks for causal conditioning and incomplete generation handling."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generation_protocol import ProtocolError, generate_analysis, speech_context


COT = (
    "<Act>: responds\n<Scene>: conversation\n<Motivation>: explain\n"
    "<Goal>: reassure\n<Emotion>: confident\n"
    "<Valid duration | Total duration>: 2.0s | 2.5s\n"
    "<Loudness | Expressive Intensity>: -23.0dBFS | 0.95\n"
    "[Summary] A confident response."
)
MARKERS = {marker: index for index, marker in enumerate((
    "<under_start>", "<under_end>", "<cot_start>", "<cot_end>", "<audio_tar_start>",
), start=10)}


def encode(text):
    # Body text intentionally cannot be re-encoded through this test tokenizer.
    return [MARKERS[text]]


def decode(ids):
    return {(101, 102): "speaker_1: Hello.", (201, 202): COT}[tuple(ids)]


class CausalGenerationTests(unittest.TestCase):
    def test_exact_generated_ids_condition_cot_and_speech(self):
        prompt = [1, 2, 3]
        under = prompt + [MARKERS["<under_start>"], 101, 102, MARKERS["<under_end>"]]
        cot = under + [MARKERS["<cot_start>"], 201, 202, MARKERS["<cot_end>"]]
        calls = []

        def generate(prefix, phase):
            calls.append((phase, list(prefix)))
            return under if phase == "under" else cot

        result = generate_analysis(prompt, generate, encode, decode)
        self.assertEqual(calls, [
            ("under", prompt + [MARKERS["<under_start>"]]),
            ("cot", under + [MARKERS["<cot_start>"]]),
        ])
        self.assertEqual(speech_context(result, encode), cot + [MARKERS["<audio_tar_start>"]])
        self.assertEqual(result["generated_cot_text"], COT)
        self.assertIn("| 0.95", result["generated_cot_text"])
        self.assertNotIn("under_text", result)

    def test_under_must_have_content_and_end_marker(self):
        for tail in ([], [MARKERS["<under_end>"]], [101, 102], [101, 102, 999]):
            with self.subTest(tail=tail), self.assertRaises(ProtocolError):
                generate_analysis([1], lambda prefix, phase: prefix + tail, encode, decode)

    def test_cot_must_end_before_speech(self):
        def generate(prefix, phase):
            return prefix + ([101, 102, MARKERS["<under_end>"]] if phase == "under" else [201, 202])

        with self.assertRaises(ProtocolError):
            generate_analysis([1], generate, encode, decode)

    def test_model_must_preserve_input_prefix(self):
        with self.assertRaises(ProtocolError):
            generate_analysis([1], lambda prefix, phase: [999, 101, 102, MARKERS["<under_end>"]], encode, decode)

    def test_under_cannot_cross_into_cot(self):
        with self.assertRaises(ProtocolError):
            generate_analysis(
                [1], lambda prefix, phase: prefix + [101, MARKERS["<under_end>"]],
                encode, lambda ids: "speaker_1: Hello.<cot_start>",
            )

    def test_cot_requires_analysis_fields(self):
        def generate(prefix, phase):
            return prefix + [101, MARKERS[f"<{phase}_end>"]]

        with self.assertRaises(ProtocolError):
            generate_analysis([1], generate, encode, lambda ids: "incomplete analysis")

    def test_section_markers_must_be_atomic(self):
        with self.assertRaises(ProtocolError):
            generate_analysis([1], lambda prefix, phase: prefix, lambda text: [1, 2], decode)


if __name__ == "__main__":
    unittest.main()
