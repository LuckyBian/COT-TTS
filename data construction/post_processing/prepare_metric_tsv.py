#!/usr/bin/env python3
"""Prepare TSV files used by audio metric scripts."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "test" / "segment_denoised"
DEFAULT_OUTPUT_TSV = REPO_ROOT / "test" / "metrics" / "segments.tsv"
AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".m4a"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a TSV with output_audio/eval_id/path columns.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-tsv", type=Path, default=DEFAULT_OUTPUT_TSV)
    parser.add_argument("--absolute", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_tsv = args.output_tsv.resolve()
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory not found: {input_dir}")

    audio_files = sorted(
        path.resolve()
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )
    output_tsv.parent.mkdir(parents=True, exist_ok=True)

    with output_tsv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["eval_id", "output_audio", "path"])
        for audio_path in audio_files:
            path_text = (
                str(audio_path)
                if args.absolute
                else os.path.relpath(audio_path, output_tsv.parent)
            )
            writer.writerow([audio_path.stem, path_text, path_text])

    print(f"Wrote {len(audio_files)} rows to {output_tsv}")


if __name__ == "__main__":
    main()
