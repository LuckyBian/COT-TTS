#!/usr/bin/env python3
"""Add same-speaker reference segment ids to JSON files."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "test" / "json_all_audio_features"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "test" / "json_all_reference"
DEFAULT_FIELD_NAME = "reference_segment_id"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "For each segment, find another segment from the same speaker with "
            "different text and write its segment_id into the JSON."
        )
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--field-name", default=DEFAULT_FIELD_NAME)
    parser.add_argument("--indent", type=int, default=2)
    return parser.parse_args()


def normalize_text(text: object) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", "", str(text)).strip()


def choose_reference(segment: dict, candidates: list[dict]) -> str | None:
    segment_id = segment.get("segment_id")
    text = normalize_text(segment.get("text"))
    for candidate in candidates:
        candidate_id = candidate.get("segment_id")
        if not candidate_id or candidate_id == segment_id:
            continue
        if normalize_text(candidate.get("text")) == text:
            continue
        return str(candidate_id)
    return str(segment_id) if segment_id else None


def add_reference_ids(data: dict, field_name: str) -> tuple[int, int]:
    segments = data.get("segment")
    if segments is None:
        segments = data.get("segments")
    if not isinstance(segments, list):
        return 0, 0

    by_speaker: dict[str, list[dict]] = defaultdict(list)
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        speaker = segment.get("speaker")
        if speaker is not None:
            by_speaker[str(speaker)].append(segment)

    matched = 0
    missing = 0
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        speaker = segment.get("speaker")
        candidates = by_speaker.get(str(speaker), []) if speaker is not None else []
        reference_id = choose_reference(segment, candidates)
        segment[field_name] = reference_id
        if reference_id == segment.get("segment_id"):
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

    total_matched = 0
    total_missing = 0
    files = sorted(input_dir.glob("*.json"))
    for input_json in files:
        data = json.loads(input_json.read_text(encoding="utf-8"))
        matched, missing = add_reference_ids(data, args.field_name)
        (output_dir / input_json.name).write_text(
            json.dumps(data, ensure_ascii=False, indent=args.indent),
            encoding="utf-8",
        )
        total_matched += matched
        total_missing += missing
        print(f"{input_json.name}: matched={matched}, missing={missing}", flush=True)

    print(
        f"Done. files={len(files)}, matched={total_matched}, missing={total_missing}, output_dir={output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
