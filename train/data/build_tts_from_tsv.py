#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CODEC_DIR = PROJECT_ROOT / "data" / "codec"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "tts.train.jsonl"
DEFAULT_TASK_NAME = "TTS"
DEFAULT_GLOBAL_PREFIX = "bicodec_global"
DEFAULT_SEMANTIC_PREFIX = "bicodec_semantic"
DEFAULT_GLOBAL_PREFIX_LEN = 32


def iter_tsv(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if isinstance(row, dict):
                yield {str(k): "" if v is None else str(v) for k, v in row.items()}


def load_codec_pt(path: Path) -> dict | None:
    try:
        obj = torch.load(path, map_location="cpu")
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def tensor_to_ids(x) -> list[int]:
    if x is None:
        return []
    if isinstance(x, torch.Tensor):
        return [int(v) for v in x.reshape(-1).tolist()]
    if isinstance(x, (list, tuple)):
        return [int(v) for v in x]
    return []


def ids_to_tokens(ids: list[int], prefix: str) -> str:
    return " ".join(f"<|{prefix}_{i}|>" for i in ids)


def global_tokens_from_pt(pt: dict, key: str, prefix: str, prefix_len: int) -> str:
    ids = tensor_to_ids(pt.get(key))[:prefix_len]
    return ids_to_tokens(ids, prefix) if ids else ""


def target_audio_tokens_from_pt(
    pt: dict,
    global_prefix: str,
    semantic_prefix: str,
    global_prefix_len: int,
) -> str:
    global_ids = tensor_to_ids(pt.get("global_tgt"))[:global_prefix_len]
    semantic_ids = tensor_to_ids(pt.get("semantic_tgt"))
    parts = []
    if global_ids:
        parts.append(ids_to_tokens(global_ids, global_prefix))
    if semantic_ids:
        parts.append(ids_to_tokens(semantic_ids, semantic_prefix))
    return " ".join(parts)


def build_user_content(task_name: str, text: str, ref_audio: str) -> str:
    return (
        f"<bos>"
        f"<task_start>{task_name}<task_end>"
        f"<history_start>"
        f"<audio_his_start><audio_his_end>"
        f"<history_end>"
        f"<target_start>"
        f"<text_start>{text}<text_end>"
        f"<audio_ref_start>{ref_audio}<audio_ref_end>"
        f"<target_end>"
        f"<output_start>"
    )


def build_assistant_content(target_audio: str) -> str:
    return (
        f"<under_start><under_end>"
        f"<cot_start><cot_end>"
        f"<audio_tar_start>{target_audio}<audio_tar_end>"
        f"<output_end>"
        f"<eos>"
    )


def build_record(
    row: dict[str, str],
    codec_dir: Path,
    task_name: str,
    global_prefix: str,
    semantic_prefix: str,
    global_prefix_len: int,
) -> dict | None:
    wav_path = row.get("path", "").strip()
    text = row.get("text", "").strip()
    ref_path = row.get("ref_path", "").strip()
    if not wav_path or not text or not ref_path:
        return None

    utt_id = Path(wav_path).stem
    ref_id = Path(ref_path).stem
    target_pt_path = codec_dir / f"{utt_id}.pt"
    ref_pt_path = codec_dir / f"{ref_id}.pt"

    target_pt = load_codec_pt(target_pt_path)
    ref_pt = load_codec_pt(ref_pt_path)
    if target_pt is None or ref_pt is None:
        return None

    ref_audio = global_tokens_from_pt(ref_pt, "global_tgt", global_prefix, global_prefix_len)
    target_audio = target_audio_tokens_from_pt(target_pt, global_prefix, semantic_prefix, global_prefix_len)
    if not ref_audio or not target_audio:
        return None

    return {
        "index": utt_id,
        "source_name": "tts",
        "messages": [
            {"role": "user", "content": build_user_content(task_name, text, ref_audio), "loss_mask": 0},
            {"role": "assistant", "content": build_assistant_content(target_audio), "loss_mask": 1},
        ],
        "meta": {
            "task": task_name,
            "wav_path": wav_path,
            "ref_path": ref_path,
            "target_codec_pt_path": str(target_pt_path),
            "ref_codec_pt_path": str(ref_pt_path),
            "text": text,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build TTS training jsonl from TSV(path,text,ref_path) and BiCodec .pt files."
    )
    parser.add_argument("--tsv", required=True, help="Input TSV with at least `path`, `text`, and `ref_path` columns.")
    parser.add_argument("--codec_dir", default=str(DEFAULT_CODEC_DIR), help="Directory containing <utt_id>.pt codec files.")
    parser.add_argument("--output_path", default=str(DEFAULT_OUTPUT_PATH), help="Output JSONL path.")
    parser.add_argument("--task_name", default=DEFAULT_TASK_NAME)
    parser.add_argument("--global_prefix", default=DEFAULT_GLOBAL_PREFIX)
    parser.add_argument("--semantic_prefix", default=DEFAULT_SEMANTIC_PREFIX)
    parser.add_argument("--global_prefix_len", type=int, default=DEFAULT_GLOBAL_PREFIX_LEN)
    parser.add_argument("--limit", type=int, default=0, help="Optional max number of written samples.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tsv_path = Path(args.tsv)
    codec_dir = Path(args.codec_dir)
    output_path = Path(args.output_path)

    if not tsv_path.is_file():
        raise FileNotFoundError(f"Missing TSV file: {tsv_path}")
    if not codec_dir.is_dir():
        raise FileNotFoundError(f"Missing codec directory: {codec_dir}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    scanned = 0
    skipped = 0
    with output_path.open("w", encoding="utf-8") as f:
        for row in iter_tsv(tsv_path):
            scanned += 1
            record = build_record(
                row=row,
                codec_dir=codec_dir,
                task_name=args.task_name,
                global_prefix=args.global_prefix,
                semantic_prefix=args.semantic_prefix,
                global_prefix_len=args.global_prefix_len,
            )
            if record is None:
                skipped += 1
                continue

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
            if args.limit > 0 and written >= args.limit:
                break

    print(f"Done. scanned={scanned}, written={written}, skipped={skipped}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
