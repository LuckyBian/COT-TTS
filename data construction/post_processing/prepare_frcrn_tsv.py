#!/usr/bin/env python3
"""Prepare the TSV file expected by the FRCRN denoising script."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "test" / "segment"
DEFAULT_OUTPUT_TSV = REPO_ROOT / "test" / "frcrn" / "segment.tsv"
DEFAULT_EXTENSIONS = (".wav", ".flac", ".mp3", ".m4a")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a TSV with a 'path' column for FRCRN denoising."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing audio segments to denoise.",
    )
    parser.add_argument(
        "--output-tsv",
        type=Path,
        default=DEFAULT_OUTPUT_TSV,
        help="Output TSV path. The file will contain one column named 'path'.",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(DEFAULT_EXTENSIONS),
        help="Audio file extensions to include.",
    )
    parser.add_argument(
        "--absolute",
        action="store_true",
        help="Write absolute paths instead of paths relative to the TSV directory.",
    )
    return parser.parse_args()


def normalize_extensions(extensions: list[str]) -> set[str]:
    return {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}


def iter_audio_files(input_dir: Path, extensions: set[str]) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in extensions
    )


def format_path(path: Path, output_tsv: Path, relative: bool) -> str:
    resolved_path = path.resolve()
    if not relative:
        return str(resolved_path)
    return os.path.relpath(resolved_path, output_tsv.resolve().parent)


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_tsv = args.output_tsv.resolve()
    extensions = normalize_extensions(args.extensions)

    audio_files = iter_audio_files(input_dir, extensions)
    output_tsv.parent.mkdir(parents=True, exist_ok=True)

    with output_tsv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["path"])
        for audio_file in audio_files:
            writer.writerow([format_path(audio_file, output_tsv, not args.absolute)])

    print(f"Wrote {len(audio_files)} audio paths to {output_tsv}")


if __name__ == "__main__":
    main()
