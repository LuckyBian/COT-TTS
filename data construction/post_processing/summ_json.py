#!/usr/bin/env python3
import argparse
from pathlib import Path

from pipeline_common import (
    build_output_filename,
    dump_json_atomic,
    iter_json_files,
    load_json,
    normalize_movie_record,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "test" / "json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "test" / "json_all"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize first-stage JSON files to a unified per-audio format."
    )
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files whose normalized output already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory not found: {input_dir}")

    written = 0
    skipped = 0
    for json_path in iter_json_files(input_dir):
        try:
            movie = normalize_movie_record(load_json(json_path), json_path)
            out_path = output_dir / build_output_filename(movie, json_path.stem)

            if args.skip_existing and out_path.exists():
                skipped += 1
                continue

            dump_json_atomic(out_path, movie)
            written += 1
            print(f"[OK] {json_path} -> {out_path}")
        except Exception as exc:
            skipped += 1
            print(f"[WARN] skip invalid file: {json_path} ({exc})")

    print(f"[DONE] normalized={written}, skipped={skipped}, out_dir={output_dir}")


if __name__ == "__main__":
    main()
