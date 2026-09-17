#!/usr/bin/env python3
"""Normalize speaker labels within each scene."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "test" / "json_all_scenes"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "test" / "json_all_scene_speakers"
DEFAULT_ORIGINAL_SPEAKER_FIELD = "original_speaker"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize speaker labels independently inside each scene. "
            "For example, Speaker-23/Speaker-14/Speaker-5 in one scene become "
            "Speaker-0/Speaker-1/Speaker-2 by first appearance order."
        )
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--speaker-field", default="speaker")
    parser.add_argument("--scene-field", default="scene_index")
    parser.add_argument("--prefix", default="Speaker")
    parser.add_argument("--original-speaker-field", default=DEFAULT_ORIGINAL_SPEAKER_FIELD)
    parser.add_argument(
        "--no-keep-original",
        action="store_true",
        help="Do not keep the pre-normalization speaker label.",
    )
    parser.add_argument("--indent", type=int, default=2)
    return parser.parse_args()


def iter_json_files(input_dir: Path):
    for path in sorted(input_dir.iterdir()):
        if path.is_file() and path.suffix.lower() == ".json":
            yield path


def get_segments(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("segment"), list):
        return data["segment"]
    if isinstance(data, dict) and isinstance(data.get("segments"), list):
        return data["segments"]
    return []


def normalize_scene_speakers(
    data: Any,
    speaker_field: str,
    scene_field: str,
    prefix: str,
    keep_original: bool,
    original_speaker_field: str,
) -> tuple[int, int]:
    segments = get_segments(data)
    mappings: dict[str, dict[str, str]] = defaultdict(dict)
    changed = 0
    missing = 0

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        scene_value = segment.get(scene_field, 0)
        scene_key = str(scene_value)
        speaker_value = segment.get(speaker_field)
        if speaker_value is None:
            missing += 1
            continue

        speaker_key = str(speaker_value)
        scene_map = mappings[scene_key]
        if speaker_key not in scene_map:
            scene_map[speaker_key] = f"{prefix}-{len(scene_map)}"

        normalized_speaker = scene_map[speaker_key]
        if keep_original:
            segment[original_speaker_field] = speaker_value
        if speaker_value != normalized_speaker:
            changed += 1
        segment[speaker_field] = normalized_speaker

    return changed, missing


def write_json(path: Path, data: Any, indent: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")
    os.replace(tmp_path, path)


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input JSON directory not found: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    files = list(iter_json_files(input_dir))
    total_changed = 0
    total_missing = 0
    for input_json in files:
        data = json.loads(input_json.read_text(encoding="utf-8"))
        changed, missing = normalize_scene_speakers(
            data=data,
            speaker_field=args.speaker_field,
            scene_field=args.scene_field,
            prefix=args.prefix,
            keep_original=not args.no_keep_original,
            original_speaker_field=args.original_speaker_field,
        )
        write_json(output_dir / input_json.name, data, args.indent)
        total_changed += changed
        total_missing += missing
        print(f"{input_json.name}: changed={changed}, missing_speaker={missing}", flush=True)

    print(
        f"Done. files={len(files)}, changed={total_changed}, "
        f"missing_speaker={total_missing}, output_dir={output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
