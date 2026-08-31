#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import sys
import types
from pathlib import Path
from typing import Iterable


# Some pyarrow environments try to import pandas even though we do not need it.
if "pandas" not in sys.modules:
    pandas_stub = types.ModuleType("pandas")
    pandas_stub.__version__ = "0.0.0"
    sys.modules["pandas"] = pandas_stub

import pyarrow as pa
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "parquet"


def iter_jsonl(path: str, skip_items: int = 0) -> Iterable[dict]:
    seen = 0
    with open(path, "r", encoding="utf-8") as src:
        for line in src:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if seen < skip_items:
                seen += 1
                continue
            yield obj
            seen += 1


def get_existing_parts_info(out_dir: str) -> tuple[list[tuple[int, str]], int]:
    if not os.path.isdir(out_dir):
        return [], 0

    parts: list[tuple[int, str]] = []
    for name in os.listdir(out_dir):
        if not (name.startswith("part-") and name.endswith(".parquet")):
            continue
        try:
            idx = int(name[len("part-") : -len(".parquet")])
        except ValueError:
            continue
        parts.append((idx, os.path.join(out_dir, name)))
    parts.sort(key=lambda item: item[0])

    total_rows = 0
    for _, path in parts:
        total_rows += pq.ParquetFile(path).metadata.num_rows
    return parts, total_rows


def normalize_message(msg: dict) -> dict:
    role = str(msg.get("role", "user"))
    content = str(msg.get("content", ""))
    default_loss_mask = 1 if role == "assistant" else 0
    raw_loss_mask = msg.get("loss_mask", default_loss_mask)
    try:
        loss_mask = int(raw_loss_mask)
    except Exception:
        loss_mask = default_loss_mask
    return {"role": role, "content": content, "loss_mask": loss_mask}


def build_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("index", pa.large_string()),
            pa.field("source_name", pa.large_string()),
            pa.field(
                "messages",
                pa.list_(
                    pa.struct(
                        [
                            pa.field("role", pa.large_string()),
                            pa.field("content", pa.large_string()),
                            pa.field("loss_mask", pa.int64()),
                        ]
                    )
                ),
            ),
            pa.field("meta", pa.large_string()),
        ]
    )


def normalize_record(record: dict) -> dict:
    messages = record.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    meta = record.get("meta", {})
    return {
        "index": str(record.get("index", "")),
        "source_name": str(record.get("source_name", "")),
        "messages": [normalize_message(msg) for msg in messages if isinstance(msg, dict)],
        "meta": meta if isinstance(meta, str) else json.dumps(meta, ensure_ascii=False),
    }


def to_parquet_parts(
    input_jsonl: str,
    out_dir: str,
    chunk_size: int,
    compress: str,
    max_samples: int,
    resume: bool,
    overwrite: bool,
) -> None:
    if not os.path.isfile(input_jsonl):
        raise FileNotFoundError(f"Input JSONL not found: {input_jsonl}")

    if overwrite and os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    existing_parts, existing_rows = get_existing_parts_info(out_dir)
    if existing_parts and not resume:
        raise RuntimeError(
            f"Found existing parquet parts in {out_dir}. "
            "Use --resume to continue, --overwrite to rebuild, or clear the directory first."
        )

    start_part = existing_parts[-1][0] + 1 if existing_parts else 0
    start_skip = existing_rows if resume else 0
    if resume and existing_parts:
        print(
            f"RESUME enabled: detected {len(existing_parts)} parts, "
            f"skipping {existing_rows} rows, next_part={start_part}",
            flush=True,
        )

    if max_samples and start_skip >= max_samples:
        print(f"Nothing to do: existing_rows={start_skip} >= max_samples={max_samples}", flush=True)
        return

    schema = build_schema()
    iterator = iter_jsonl(input_jsonl, skip_items=start_skip)
    part = start_part
    written = start_skip

    while True:
        rows: list[dict] = []
        try:
            for _ in range(chunk_size):
                item = next(iterator)
                rows.append(normalize_record(item))
                written += 1
                if max_samples and written >= max_samples:
                    break
        except StopIteration:
            pass

        if not rows:
            break

        table = pa.Table.from_pylist(rows, schema=schema)
        out_path = os.path.join(out_dir, f"part-{part:05d}.parquet")
        pq.write_table(table, out_path, compression=compress)
        print(f"WROTE {out_path} rows={table.num_rows} total_rows={written}", flush=True)
        part += 1

        if max_samples and written >= max_samples:
            break

    print(f"Done. parts_written_now={part - start_part} total_parts={part} total_rows={written}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert training JSONL into parquet parts.")
    parser.add_argument("--input", required=True, help="Input JSONL path.")
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help=f"Output parquet directory. Default: {DEFAULT_OUT_DIR}",
    )
    parser.add_argument("--chunk-size", type=int, default=20000, help="Rows per parquet part.")
    parser.add_argument("--compress", default="snappy", help="Parquet compression codec.")
    parser.add_argument("--max-samples", type=int, default=0, help="Optional max number of samples to convert.")
    parser.add_argument("--resume", action="store_true", help="Resume from existing parquet parts.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output directory before conversion.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    to_parquet_parts(
        input_jsonl=args.input,
        out_dir=args.out_dir,
        chunk_size=args.chunk_size,
        compress=args.compress,
        max_samples=args.max_samples,
        resume=args.resume,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
