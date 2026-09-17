#!/usr/bin/env python3
"""Add emotion labels to standardized JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "test" / "json_all"
DEFAULT_EMOTION_DIR = REPO_ROOT / "test" / "emotion"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "test" / "json_all_emo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add emo-tag fields to standardized JSON files.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--emotion-dir", type=Path, default=DEFAULT_EMOTION_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--missing-label", default="none")
    parser.add_argument("--indent", type=int, default=2)
    return parser.parse_args()


def load_emotion_map(emotion_dir: Path) -> dict[str, str]:
    if not emotion_dir.is_dir():
        raise NotADirectoryError(f"Emotion directory not found: {emotion_dir}")
    emotion_map: dict[str, str] = {}
    for txt_path in sorted(emotion_dir.glob("*.txt")):
        label = txt_path.read_text(encoding="utf-8").strip()
        emotion_map[txt_path.stem] = label or "none"
    return emotion_map


def add_emotion_tags(data: dict, emotion_map: dict[str, str], missing_label: str) -> tuple[int, int]:
    matched = 0
    missing = 0
    segments = data.get("segment")
    if segments is None:
        segments = data.get("segments")

    if not isinstance(segments, list):
        return matched, missing

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_id = segment.get("segment_id")
        label = emotion_map.get(segment_id, missing_label)
        segment["emo-tag"] = label
        if label == missing_label:
            missing += 1
        else:
            matched += 1
    return matched, missing


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input JSON directory not found: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    emotion_map = load_emotion_map(args.emotion_dir.resolve())
    json_files = sorted(input_dir.glob("*.json"))

    total_matched = 0
    total_missing = 0
    for input_json in json_files:
        data = json.loads(input_json.read_text(encoding="utf-8"))
        matched, missing = add_emotion_tags(data, emotion_map, args.missing_label)
        output_json = output_dir / input_json.name
        output_json.write_text(
            json.dumps(data, ensure_ascii=False, indent=args.indent),
            encoding="utf-8",
        )
        total_matched += matched
        total_missing += missing
        print(f"{input_json.name}: matched={matched}, missing={missing}", flush=True)

    print(
        f"Done. files={len(json_files)}, matched={total_matched}, missing={total_missing}, "
        f"output_dir={output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
