#!/usr/bin/env python3
"""Run speech emotion recognition on audio segments with emotion2vec."""

from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "test" / "segment_denoised"
DEFAULT_MODEL = REPO_ROOT / "model" / "emotion2vec_plus_large"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "test" / "emotion"
AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".m4a"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate one emotion label txt per audio segment.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--tsv", type=Path, default=None, help="Optional TSV with a 'path' column.")
    parser.add_argument("--model", type=str, default=str(DEFAULT_MODEL))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--device", type=str, default="cuda:0", help="For example: cuda:0 or cpu.")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def resolve_tsv_path(path_text: str, tsv_path: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (tsv_path.parent / path).resolve()


def load_audio_paths(input_dir: Path, tsv_path: Path | None) -> list[Path]:
    if tsv_path is None:
        if not input_dir.is_dir():
            raise NotADirectoryError(f"Input directory not found: {input_dir}")
        return sorted(
            path.resolve()
            for path in input_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
        )

    if not tsv_path.exists():
        raise FileNotFoundError(f"TSV not found: {tsv_path}")
    paths: list[Path] = []
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if "path" not in (reader.fieldnames or []):
            raise ValueError(f"{tsv_path} does not contain a 'path' column.")
        for row in reader:
            path_text = (row.get("path") or "").strip()
            if path_text:
                paths.append(resolve_tsv_path(path_text, tsv_path))
    return paths


def chunked(items: list[Path], batch_size: int):
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def output_path_for(audio_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{audio_path.stem}.txt"


def extract_label(result: dict) -> str | None:
    labels = result.get("labels", [])
    scores = result.get("scores", [])
    if not labels or not scores or len(labels) != len(scores):
        return None
    full_label = labels[scores.index(max(scores))]
    if "/" in full_label:
        return full_label.split("/", 1)[1]
    return full_label


def generate_batch(model, audio_paths: list[Path]) -> list[str | None]:
    results = model.generate(
        input=[str(path) for path in audio_paths],
        output_dir=None,
        granularity="utterance",
        extract_embedding=False,
    )
    if not isinstance(results, list) or len(results) != len(audio_paths):
        raise RuntimeError("Batch SER result length does not match input length.")
    return [extract_label(item) if isinstance(item, dict) else None for item in results]


def generate_single(model, audio_path: Path) -> str | None:
    results = model.generate(
        input=str(audio_path),
        output_dir=None,
        granularity="utterance",
        extract_embedding=False,
    )
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        return None
    return extract_label(results[0])


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size must be >= 1")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_paths = load_audio_paths(args.input_dir.resolve(), args.tsv.resolve() if args.tsv else None)
    pending = [
        path
        for path in audio_paths
        if path.exists() and (args.overwrite or not output_path_for(path, output_dir).exists())
    ]
    missing = [path for path in audio_paths if not path.exists()]

    print(f"Input files: {len(audio_paths)}", flush=True)
    print(f"Missing files: {len(missing)}", flush=True)
    print(f"Pending files: {len(pending)}", flush=True)
    print(f"Output dir: {output_dir}", flush=True)
    print(f"Model: {args.model}", flush=True)
    print(f"Device: {args.device}", flush=True)

    if not pending:
        print("No files need processing.", flush=True)
        return

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

    from funasr import AutoModel

    model = AutoModel(model=args.model, device=args.device)
    start_time = time.time()
    done = 0
    success = 0
    failed = 0
    batch_mode_ok = True

    for batch in chunked(pending, args.batch_size):
        try:
            if not batch_mode_ok:
                raise RuntimeError("Batch mode disabled.")
            labels = generate_batch(model, batch)
        except Exception as e:
            if batch_mode_ok:
                print(f"Batch mode failed, falling back to single-file mode: {e}", flush=True)
                batch_mode_ok = False
            labels = [generate_single(model, path) for path in batch]

        for audio_path, label in zip(batch, labels):
            done += 1
            if label:
                output_path_for(audio_path, output_dir).write_text(label, encoding="utf-8")
                success += 1
            else:
                failed += 1

        elapsed = max(time.time() - start_time, 1e-6)
        print(
            f"Progress: {done}/{len(pending)} | success={success} | failed={failed} | "
            f"speed={done / elapsed:.2f}/s",
            flush=True,
        )

    print(f"Done. success={success}, failed={failed}", flush=True)


if __name__ == "__main__":
    main()
