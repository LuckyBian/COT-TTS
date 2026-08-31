#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterable

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA_PATH = Path(
    "/aifs4su/mmdata/processed_data/StyleCraft/TTS/09_cot-tts/data/high_qual/movie1/"
    "metadata.need_cot_true.speaker_generic.text_replaced.json"
)
DEFAULT_CODEC_DIR = Path(
    "/aifs4su/mmdata/processed_data/StyleCraft/TTS/09_cot-tts/data/high_qual/movie1/spark_codec"
)
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "one_cot_tts_sample.json"
DEFAULT_TASK_NAME = "COT-TTS"
DEFAULT_GLOBAL_PREFIX = "bicodec_global"
DEFAULT_SEMANTIC_PREFIX = "bicodec_semantic"
DEFAULT_GLOBAL_PREFIX_LEN = 32


def iter_json_array(path: Path, chunk_size: int = 1024 * 1024) -> Iterable[dict[str, Any]]:
    """Stream a large JSON array without loading it fully into memory."""
    decoder = json.JSONDecoder()
    buffer = ""
    pos = 0
    started = False

    with path.open("r", encoding="utf-8") as src:
        while True:
            if pos > 0:
                buffer = buffer[pos:]
                pos = 0

            chunk = src.read(chunk_size)
            if chunk:
                buffer += chunk
            elif not buffer.strip():
                return

            while True:
                while pos < len(buffer) and buffer[pos].isspace():
                    pos += 1

                if not started:
                    if pos >= len(buffer):
                        break
                    if buffer[pos] != "[":
                        raise ValueError(f"{path} is not a JSON array")
                    started = True
                    pos += 1
                    continue

                while pos < len(buffer) and buffer[pos].isspace():
                    pos += 1
                if pos < len(buffer) and buffer[pos] == ",":
                    pos += 1
                    continue
                if pos < len(buffer) and buffer[pos] == "]":
                    return
                if pos >= len(buffer):
                    break

                try:
                    obj, next_pos = decoder.raw_decode(buffer, pos)
                except json.JSONDecodeError:
                    if chunk:
                        break
                    raise

                if not isinstance(obj, dict):
                    raise ValueError(f"{path} contains a non-object array item")
                yield obj
                pos = next_pos

            if not chunk:
                if buffer[pos:].strip():
                    raise ValueError(f"Trailing undecoded content in {path}")
                return


def load_codec_pt(path: Path) -> dict[str, Any] | None:
    try:
        obj = torch.load(path, map_location="cpu")
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def tensor_to_ids(x: Any) -> list[int]:
    if x is None:
        return []
    if isinstance(x, torch.Tensor):
        return [int(v) for v in x.reshape(-1).tolist()]
    if isinstance(x, (list, tuple)):
        return [int(v) for v in x]
    return []


def ids_to_tokens(ids: list[int], prefix: str) -> str:
    return " ".join(f"<|{prefix}_{i}|>" for i in ids)


def global_tokens_from_pt(pt: dict[str, Any], key: str, prefix: str, prefix_len: int) -> str:
    ids = tensor_to_ids(pt.get(key))[:prefix_len]
    return ids_to_tokens(ids, prefix) if ids else ""


def semantic_tokens_from_pt(pt: dict[str, Any], prefix: str) -> str:
    ids = tensor_to_ids(pt.get("semantic_tgt"))
    return ids_to_tokens(ids, prefix) if ids else ""


def target_audio_tokens_from_pt(pt: dict[str, Any], global_prefix: str, semantic_prefix: str, prefix_len: int) -> str:
    parts = [
        global_tokens_from_pt(pt, "global_tgt", global_prefix, prefix_len),
        semantic_tokens_from_pt(pt, semantic_prefix),
    ]
    return " ".join(part for part in parts if part)


def codec_path(codec_dir: Path, segment_id: str) -> Path:
    return codec_dir / f"{segment_id}.pt"


def build_history_audio_tokens(
    dialog_segments: list[dict[str, Any]],
    codec_dir: Path,
    global_prefix: str,
    semantic_prefix: str,
    prefix_len: int,
) -> str | None:
    """
    Match the original stage2 builder:
    - first history segment uses global + semantic
    - later history segments only use semantic
    """
    parts: list[str] = []
    for idx, segment in enumerate(dialog_segments):
        segment_id = str(segment.get("segment_id", "") or "").strip()
        if not segment_id:
            return None

        pt = load_codec_pt(codec_path(codec_dir, segment_id))
        if pt is None:
            return None

        if idx == 0:
            tokens = target_audio_tokens_from_pt(pt, global_prefix, semantic_prefix, prefix_len)
        else:
            tokens = semantic_tokens_from_pt(pt, semantic_prefix)

        if not tokens:
            return None
        parts.append(tokens)

    return " ".join(parts) if parts else None


def build_under_text(dialog_segments: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for segment in dialog_segments:
        text = str(segment.get("text", "") or "").strip()
        emotion = str(segment.get("emotion_tag", "") or "").strip()
        if not text:
            continue
        if emotion:
            parts.append(f"{text}[{emotion}]")
        else:
            parts.append(text)
    return "\n".join(parts)


def build_cot_text(target: dict[str, Any]) -> str:
    """Prefer the already assembled cot_text if present; otherwise keep a small fallback."""
    cot_text = str(target.get("cot_text", "") or "").strip()
    if cot_text:
        return cot_text

    features = target.get("features")
    features = features if isinstance(features, dict) else {}
    summary = str(target.get("summ", "") or "").strip()
    lines = [
        f"<Emotion>: {str(target.get('emotion_tag', '') or '').strip()}",
        f"<Valid duration | Total duration>: {str(features.get('active_duration', '') or '').strip()} | {str(features.get('duration', '') or '').strip()}",
        f"<Loudness | Expressive Intensity>: {str(features.get('loudness', '') or '').strip()} | {str(features.get('expressive_intensity', '') or '').strip()}",
    ]
    if summary:
        lines.append(f"[Summary] {summary}")
    return "\n".join(line for line in lines if line.strip())


def build_ref_audio_tokens(
    target: dict[str, Any],
    target_pt: dict[str, Any],
    codec_dir: Path,
    global_prefix: str,
    prefix_len: int,
) -> str:
    """
    Prefer ref_segment_id if available.
    Fall back to global_ref from the target pt.
    """
    ref_segment_id = str(target.get("ref_segment_id", "") or "").strip()
    if ref_segment_id:
        ref_pt = load_codec_pt(codec_path(codec_dir, ref_segment_id))
        if ref_pt is not None:
            ref_tokens = global_tokens_from_pt(ref_pt, "global_tgt", global_prefix, prefix_len)
            if ref_tokens:
                return ref_tokens

    return global_tokens_from_pt(target_pt, "global_ref", global_prefix, prefix_len)


def build_user_content(task: str, history_audio: str, text: str, ref_audio: str) -> str:
    return (
        f"<bos>"
        f"<task_start>{task}<task_end>"
        f"<history_start>"
        f"<audio_his_start>{history_audio}<audio_his_end>"
        f"<history_end>"
        f"<target_start>"
        f"<text_start>{text}<text_end>"
        f"<audio_ref_start>{ref_audio}<audio_ref_end>"
        f"<target_end>"
        f"<output_start>"
    )


def build_assistant_content(under_text: str, cot_text: str, target_audio: str) -> str:
    return (
        f"<under_start>{under_text}<under_end>"
        f"<cot_start>{cot_text}<cot_end>"
        f"<audio_tar_start>{target_audio}<audio_tar_end>"
        f"<output_end>"
        f"<eos>"
    )


def convert_sample(
    sample: dict[str, Any],
    codec_dir: Path,
    task_name: str,
    global_prefix: str,
    semantic_prefix: str,
    prefix_len: int,
) -> dict[str, Any] | None:
    dialog_segments = sample.get("dialog_segments")
    target = sample.get("target_segment")
    if not isinstance(dialog_segments, list) or not dialog_segments or not isinstance(target, dict):
        return None
    if not all(isinstance(segment, dict) for segment in dialog_segments):
        return None

    target_segment_id = str(target.get("segment_id", "") or sample.get("next_segment_id", "") or "").strip()
    target_text = str(target.get("text", "") or sample.get("next_text", "") or "").strip()
    if not target_segment_id or not target_text:
        return None

    target_pt = load_codec_pt(codec_path(codec_dir, target_segment_id))
    if target_pt is None:
        return None

    history_audio = build_history_audio_tokens(
        dialog_segments=dialog_segments,
        codec_dir=codec_dir,
        global_prefix=global_prefix,
        semantic_prefix=semantic_prefix,
        prefix_len=prefix_len,
    )
    target_audio = target_audio_tokens_from_pt(target_pt, global_prefix, semantic_prefix, prefix_len)
    ref_audio = build_ref_audio_tokens(target, target_pt, codec_dir, global_prefix, prefix_len)
    if not history_audio or not target_audio or not ref_audio:
        return None

    under_text = build_under_text(dialog_segments)
    cot_text = build_cot_text(target)
    user_content = build_user_content(task_name, history_audio, target_text, ref_audio)
    assistant_content = build_assistant_content(under_text, cot_text, target_audio)

    return {
        "index": str(sample.get("index", "") or f"movie1-{target_segment_id}"),
        "source_name": "cot-tts",
        "messages": [
            {"role": "user", "content": user_content, "loss_mask": 0},
            {"role": "assistant", "content": assistant_content, "loss_mask": 1},
        ],
        "meta": {
            "movie_id": sample.get("movie_id", ""),
            "movie_name": sample.get("movie_name", ""),
            "scene_index": sample.get("scene_index"),
            "dialog_count": sample.get("dialog_count"),
            "history_segment_ids": [
                str(segment.get("segment_id", "") or "")
                for segment in dialog_segments
                if isinstance(segment, dict)
            ],
            "target_segment_id": target_segment_id,
            "ref_segment_id": str(target.get("ref_segment_id", "") or ""),
            "codec_dir": str(codec_dir),
        },
    }


def find_first_valid_sample(
    metadata_path: Path,
    codec_dir: Path,
    task_name: str,
    global_prefix: str,
    semantic_prefix: str,
    prefix_len: int,
    max_scan: int,
) -> tuple[dict[str, Any], int]:
    scanned = 0
    for sample in iter_json_array(metadata_path):
        scanned += 1
        converted = convert_sample(sample, codec_dir, task_name, global_prefix, semantic_prefix, prefix_len)
        if converted is not None:
            return converted, scanned
        if max_scan > 0 and scanned >= max_scan:
            break
    raise RuntimeError(f"Could not build a valid sample after scanning {scanned} records from {metadata_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build one COT-TTS training sample from metadata + spark codec.")
    parser.add_argument("--metadata_path", default=str(DEFAULT_METADATA_PATH))
    parser.add_argument("--codec_dir", default=str(DEFAULT_CODEC_DIR))
    parser.add_argument("--output_path", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--task_name", default=DEFAULT_TASK_NAME)
    parser.add_argument("--global_prefix", default=DEFAULT_GLOBAL_PREFIX)
    parser.add_argument("--semantic_prefix", default=DEFAULT_SEMANTIC_PREFIX)
    parser.add_argument("--global_prefix_len", type=int, default=DEFAULT_GLOBAL_PREFIX_LEN)
    parser.add_argument("--max_scan", type=int, default=5000, help="Maximum metadata records to scan before giving up.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata_path = Path(args.metadata_path)
    codec_dir = Path(args.codec_dir)
    output_path = Path(args.output_path)

    if not metadata_path.is_file():
        raise FileNotFoundError(f"Missing metadata file: {metadata_path}")
    if not codec_dir.is_dir():
        raise FileNotFoundError(f"Missing codec directory: {codec_dir}")

    sample, scanned = find_first_valid_sample(
        metadata_path=metadata_path,
        codec_dir=codec_dir,
        task_name=args.task_name,
        global_prefix=args.global_prefix,
        semantic_prefix=args.semantic_prefix,
        prefix_len=args.global_prefix_len,
        max_scan=args.max_scan,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Built one sample after scanning {scanned} metadata rows.")
    print(f"Saved to: {output_path}")
    print(f"index: {sample['index']}")
    print(f"target_segment_id: {sample['meta']['target_segment_id']}")


if __name__ == "__main__":
    main()
