#!/usr/bin/env python3
"""Extract duration, active duration, loudness, and expression intensity."""

from __future__ import annotations

import argparse
import csv
import math
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from transformers import Wav2Vec2Processor
from transformers.models.wav2vec2.modeling_wav2vec2 import Wav2Vec2Model, Wav2Vec2PreTrainedModel


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_TSV = REPO_ROOT / "test" / "metrics" / "segments.tsv"
DEFAULT_OUTPUT_TSV = REPO_ROOT / "test" / "metrics" / "audio_features.tsv"
DEFAULT_MODEL_DIR = REPO_ROOT / "model" / "wav2vec2-large-robust-12-ft-emotion-msp-dim"
TARGET_SR = 16000
EPS = 1e-12


class RegressionHead(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.final_dropout)
        self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, features):
        x = self.dropout(features)
        x = torch.tanh(self.dense(x))
        x = self.dropout(x)
        return self.out_proj(x)


class EmotionModel(Wav2Vec2PreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.wav2vec2 = Wav2Vec2Model(config)
        self.classifier = RegressionHead(config)
        self.init_weights()

    def forward(self, input_values, attention_mask=None):
        outputs = self.wav2vec2(input_values, attention_mask=attention_mask)
        hidden_states = outputs[0]
        if attention_mask is not None and hasattr(self.wav2vec2, "_get_feature_vector_attention_mask"):
            feature_mask = self.wav2vec2._get_feature_vector_attention_mask(hidden_states.shape[1], attention_mask)
            feature_mask = feature_mask.to(hidden_states.device).unsqueeze(-1)
            hidden_states = (hidden_states * feature_mask).sum(dim=1) / feature_mask.sum(dim=1).clamp(min=1)
        else:
            hidden_states = torch.mean(hidden_states, dim=1)
        return hidden_states, self.classifier(hidden_states)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract audio features into a TSV.")
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_INPUT_TSV)
    parser.add_argument("--output-tsv", type=Path, default=DEFAULT_OUTPUT_TSV)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--emotion-batch-size", type=int, default=16)
    parser.add_argument("--max-chunk-sec", type=float, default=20.0)
    parser.add_argument("--no-emotion", action="store_true")
    parser.add_argument("--frame-ms", type=float, default=30.0)
    parser.add_argument("--hop-ms", type=float, default=10.0)
    parser.add_argument("--top-db", type=float, default=40.0)
    parser.add_argument("--silence-dbfs", type=float, default=-45.0)
    parser.add_argument("--min-speech-ms", type=float, default=100.0)
    parser.add_argument("--min-silence-ms", type=float, default=100.0)
    parser.add_argument("--fp16", action="store_true")
    return parser.parse_args()


def read_audio(path: Path) -> tuple[np.ndarray, int]:
    try:
        import soundfile as sf

        audio, sr = sf.read(str(path), always_2d=False, dtype="float32")
    except ImportError:
        from scipy.io import wavfile

        sr, audio = wavfile.read(str(path))
        audio = pcm_to_float(audio)
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0:
        raise ValueError(f"Empty audio file: {path}")
    return audio, int(sr)


def pcm_to_float(audio: np.ndarray) -> np.ndarray:
    if np.issubdtype(audio.dtype, np.floating):
        return audio.astype(np.float32)
    info = np.iinfo(audio.dtype)
    scale = max(abs(info.min), info.max)
    return (audio.astype(np.float32) / float(scale)).clip(-1.0, 1.0)


def resample_audio(audio: np.ndarray, sr: int, target_sr: int) -> np.ndarray:
    if sr == target_sr:
        return audio.astype(np.float32, copy=False)
    from scipy.signal import resample_poly

    gcd = math.gcd(sr, target_sr)
    return resample_poly(audio, target_sr // gcd, sr // gcd).astype(np.float32)


def rms_dbfs(audio: np.ndarray) -> tuple[float, float, float]:
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    peak = float(np.max(np.abs(audio)))
    return rms, 20.0 * math.log10(max(rms, EPS)), 20.0 * math.log10(max(peak, EPS))


def detect_active_segments(audio: np.ndarray, sr: int, args: argparse.Namespace) -> list[tuple[int, int]]:
    frame_len = max(1, int(round(sr * args.frame_ms / 1000.0)))
    hop_len = max(1, int(round(sr * args.hop_ms / 1000.0)))
    starts = list(range(0, max(1, len(audio) - frame_len + 1), hop_len))
    if not starts or starts[-1] + frame_len < len(audio):
        starts.append(max(0, len(audio) - frame_len))
    frame_rms = np.array(
        [np.sqrt(np.mean(np.square(audio[start : start + frame_len], dtype=np.float64))) for start in starts]
    )
    max_rms = float(np.max(frame_rms)) if frame_rms.size else 0.0
    threshold = max(max_rms * (10.0 ** (-args.top_db / 20.0)), 10.0 ** (args.silence_dbfs / 20.0))
    active = frame_rms > threshold
    raw = []
    seg_start = None
    for is_active, start in zip(active, starts):
        if is_active and seg_start is None:
            seg_start = start
        elif not is_active and seg_start is not None:
            raw.append((seg_start, min(len(audio), start + frame_len)))
            seg_start = None
    if seg_start is not None:
        raw.append((seg_start, len(audio)))
    if not raw:
        return []
    min_silence = int(round(sr * args.min_silence_ms / 1000.0))
    merged = [raw[0]]
    for start, end in raw[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= min_silence:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    min_speech = int(round(sr * args.min_speech_ms / 1000.0))
    return [(start, end) for start, end in merged if end - start >= min_speech]


def read_paths(tsv_path: Path) -> list[tuple[str, Path]]:
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames:
            return []
        path_col = "path" if "path" in reader.fieldnames else "output_audio"
        rows = []
        for row in reader:
            path_text = (row.get(path_col) or "").strip()
            eval_id = (row.get("eval_id") or "").strip()
            if not path_text:
                continue
            path = Path(path_text)
            if not path.is_absolute():
                path = (tsv_path.parent / path).resolve()
            rows.append((eval_id or path.stem, path))
    return rows


def load_model(model_dir: Path, device: str):
    processor = Wav2Vec2Processor.from_pretrained(str(model_dir), local_files_only=True)
    model = EmotionModel.from_pretrained(str(model_dir), local_files_only=True).to(device)
    model.eval()
    return processor, model


def autocast_context(device: str, enabled: bool):
    if enabled and device.startswith("cuda"):
        return torch.cuda.amp.autocast()
    return nullcontext()


def predict_emotion(audio_16k: np.ndarray, processor, model, device: str, args: argparse.Namespace) -> dict[str, float | None]:
    if audio_16k.size == 0:
        return {"arousal": None, "dominance": None, "valence": None, "expression_intensity": None}
    chunk_size = max(1, int(round(TARGET_SR * args.max_chunk_sec)))
    sums = np.zeros(3, dtype=np.float64)
    weight_sum = 0.0
    for start in range(0, len(audio_16k), chunk_size):
        chunk = audio_16k[start : start + chunk_size]
        if chunk.size < int(0.1 * TARGET_SR):
            continue
        inputs = processor(chunk, sampling_rate=TARGET_SR, return_tensors="pt")
        with torch.inference_mode(), autocast_context(device, args.fp16):
            pred = model(inputs["input_values"].to(device))[1]
        values = pred.detach().cpu().numpy()[0]
        sums += values * float(chunk.size)
        weight_sum += float(chunk.size)
    if weight_sum <= 0:
        return {"arousal": None, "dominance": None, "valence": None, "expression_intensity": None}
    values = sums / weight_sum
    arousal, dominance, valence = [float(v) for v in values]
    return {
        "arousal": arousal,
        "dominance": dominance,
        "valence": valence,
        "expression_intensity": float(0.7 * arousal + 0.3 * dominance),
    }


def fmt(value: float | None) -> str:
    return "nan" if value is None else f"{float(value):.6f}"


def main() -> None:
    args = parse_args()
    rows = read_paths(args.input_tsv.resolve())
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    processor = model = None
    if not args.no_emotion:
        processor, model = load_model(args.model_dir.resolve(), args.device)

    with args.output_tsv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(
            [
                "segment_id",
                "total_duration_sec",
                "active_duration_sec",
                "silence_duration_sec",
                "active_ratio",
                "rms",
                "rms_dbfs",
                "peak_dbfs",
                "active_rms",
                "active_rms_dbfs",
                "active_peak_dbfs",
                "arousal",
                "dominance",
                "valence",
                "expression_intensity",
            ]
        )
        for idx, (segment_id, audio_path) in enumerate(rows, start=1):
            audio, sr = read_audio(audio_path)
            total_duration = float(len(audio) / sr)
            rms, rms_level, peak_level = rms_dbfs(audio)
            active_segments = detect_active_segments(audio, sr, args)
            active_duration = float(sum(end - start for start, end in active_segments) / sr)
            active_audio = (
                np.concatenate([audio[start:end] for start, end in active_segments]).astype(np.float32)
                if active_segments
                else np.zeros(0, dtype=np.float32)
            )
            active_rms, active_rms_level, active_peak_level = (
                rms_dbfs(active_audio) if active_audio.size else (None, None, None)
            )
            emotion = {"arousal": None, "dominance": None, "valence": None, "expression_intensity": None}
            if not args.no_emotion:
                model_audio = active_audio if active_audio.size else audio
                emotion = predict_emotion(resample_audio(model_audio, sr, TARGET_SR), processor, model, args.device, args)
            writer.writerow(
                [
                    segment_id,
                    fmt(total_duration),
                    fmt(active_duration),
                    fmt(max(0.0, total_duration - active_duration)),
                    fmt(active_duration / total_duration if total_duration > 0 else 0.0),
                    fmt(rms),
                    fmt(rms_level),
                    fmt(peak_level),
                    fmt(active_rms),
                    fmt(active_rms_level),
                    fmt(active_peak_level),
                    fmt(emotion["arousal"]),
                    fmt(emotion["dominance"]),
                    fmt(emotion["valence"]),
                    fmt(emotion["expression_intensity"]),
                ]
            )
            if idx % 50 == 0 or idx == len(rows):
                print(f"processed {idx}/{len(rows)}", flush=True)
    print(f"Wrote {len(rows)} rows to {args.output_tsv}")


if __name__ == "__main__":
    main()
