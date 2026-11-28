"""Causal under, CoT, and speech conditioning without model-loading dependencies."""

from __future__ import annotations

class ProtocolError(RuntimeError):
    pass


def marker_ids(encode, marker: str) -> list[int]:
    ids = list(encode(marker))
    if len(ids) != 1:
        raise ProtocolError(f"Expected a single tokenizer token for {marker}")
    return ids


def generated_tail(prefix, output, phase: str) -> list[int]:
    prefix, output = list(prefix), list(output)
    if output[:len(prefix)] != prefix:
        raise ProtocolError(f"{phase}: generation changed the input prefix")
    tail = output[len(prefix):]
    if not tail:
        raise ProtocolError(f"{phase}: no generated tokens")
    return tail


def generate_analysis(prompt_ids, generate, encode, decode) -> dict:
    """Keep the generated under token IDs in every subsequent causal prefix."""
    context = list(prompt_ids)
    analysis = {}
    for phase in ("under", "cot"):
        prefix = context + marker_ids(encode, f"<{phase}_start>")
        output = list(generate(prefix, phase))
        tail = generated_tail(prefix, output, phase)
        if len(tail) < 2 or tail[-1] != marker_ids(encode, f"<{phase}_end>")[0]:
            raise ProtocolError(f"{phase}: missing content or required <{phase}_end>")
        text = decode(tail[:-1]).strip()
        if not text:
            raise ProtocolError(f"{phase}: empty content")
        if any(marker in text for marker in (
            "<under_start>", "<under_end>", "<cot_start>", "<cot_end>",
            "<audio_tar_start>", "<audio_tar_end>", "<output_end>",
        )):
            raise ProtocolError(f"{phase}: generation crossed a section boundary")
        if phase == "cot":
            required = ("<Act>:", "<Scene>:", "<Motivation>:", "<Goal>:", "<Emotion>:", "[Summary]")
            if not text.startswith("<Act>:") or not all(field in text for field in required):
                raise ProtocolError("cot: missing required analysis fields")
            analysis["generated_cot_text"] = text
        analysis[f"{phase}_context_ids"] = output
        analysis[f"{phase}_generated_ids"] = tail
        context = output
    return analysis


def speech_context(analysis, encode) -> list[int]:
    return list(analysis["cot_context_ids"]) + marker_ids(encode, "<audio_tar_start>")
