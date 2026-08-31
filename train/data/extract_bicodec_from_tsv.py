#!/usr/bin/env python3
import argparse
import csv
import os
from pathlib import Path
from queue import Empty

import torch
import torch.multiprocessing as mp
from tqdm import tqdm

try:
    from sparktts.models.audio_tokenizer import BiCodecTokenizer
except ImportError as exc:
    raise ImportError(
        "Cannot import sparktts.models.audio_tokenizer.BiCodecTokenizer. "
        "Make sure the current environment already has Spark-TTS installed."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_ROOT = PROJECT_ROOT / "model" / "Spark-TTS"
DEFAULT_SAVE_DIR = PROJECT_ROOT / "data" / "codec"


def read_tsv(tsv_path: str, save_dir: str, retry_failed: bool = False):
    """Read TSV and skip samples that are already finished or marked as failed."""
    rows = []
    save_path_obj = Path(save_dir)

    existing_ok = set()
    existing_failed = set()
    if save_path_obj.exists():
        existing_ok = {f.stem for f in save_path_obj.glob("*.pt")}
        if not retry_failed:
            existing_failed = {
                f.name[: -len(".err.txt")]
                for f in save_path_obj.glob("*.err.txt")
            }

    total_count = 0
    with open(tsv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            total_count += 1
            path = row.get("path")
            if not path:
                continue

            path = path.strip()
            utt_id = Path(path).stem
            if utt_id in existing_ok or utt_id in existing_failed:
                continue

            rows.append({"path": path, "utt_id": utt_id})

    print(
        f"Total rows: {total_count}, "
        f"existing_ok: {len(existing_ok)}, "
        f"existing_failed: {len(existing_failed)}, "
        f"to_process: {len(rows)}"
    )
    return rows


def shard_list(items, num_shards, shard_idx):
    """Split a list evenly and return one shard."""
    total = len(items)
    per = (total + num_shards - 1) // num_shards
    start = shard_idx * per
    end = min(start + per, total)
    return items[start:end]


def flush_progress(progress_queue, processed_delta, success_delta, failed_delta):
    if processed_delta == 0:
        return 0, 0, 0
    progress_queue.put((processed_delta, success_delta, failed_delta))
    return 0, 0, 0


def write_failure_marker(err_path: Path, exc: Exception):
    try:
        err_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
    except Exception:
        pass


def atomic_torch_save(obj, out_pt: Path):
    tmp_path = out_pt.with_suffix(f".pt.tmp.{os.getpid()}")
    torch.save(obj, str(tmp_path))
    os.replace(tmp_path, out_pt)


def encode_sample(tokenizer: BiCodecTokenizer, wav_path: str):
    """
    Extract codec tensors from one wav file.

    Output:
    - semantic_tgt: semantic codec sequence
    - global_tgt: target global codec sequence
    - global_ref: reference-style global codec sequence from the first half
    """
    wav, ref_wav = tokenizer.process_audio(wav_path)

    with torch.inference_mode():
        feat = tokenizer.extract_wav2vec2_features(wav)
        batch = {
            "wav": torch.from_numpy(wav).unsqueeze(0).float().to(tokenizer.device),
            "ref_wav": ref_wav.to(tokenizer.device),
            "feat": feat.to(tokenizer.device),
        }
        semantic_tgt, global_tgt = tokenizer.model.tokenize(batch)

        half = max(1, len(wav) // 2)
        wav_half = wav[:half]
        half_ref_wav = tokenizer.get_ref_clip(wav_half)
        half_ref_wav = torch.from_numpy(half_ref_wav).unsqueeze(0).float().to(tokenizer.device)
        half_mel = tokenizer.model.mel_transformer(half_ref_wav).squeeze(1)
        global_ref = tokenizer.model.speaker_encoder.tokenize(half_mel.transpose(1, 2))

    return semantic_tgt, global_tgt, global_ref


def process_shard(rank, args, gpu_id, shard, progress_queue):
    """Bind one worker process to one GPU and process its shard."""
    device = torch.device(f"cuda:{gpu_id}")
    torch.cuda.set_device(device)
    torch.set_num_threads(1)
    if hasattr(torch, "set_num_interop_threads"):
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass

    tokenizer = BiCodecTokenizer(model_dir=args.model_root, device=device)

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    report_every = max(1, args.progress_report_every)

    processed_delta = 0
    success_delta = 0
    failed_delta = 0

    for sample in shard:
        wav_path = sample["path"]
        utt_id = sample["utt_id"]
        out_pt = save_dir / f"{utt_id}.pt"
        err_pt = save_dir / f"{utt_id}.err.txt"

        if out_pt.exists() or (err_pt.exists() and not args.retry_failed):
            processed_delta += 1
            if out_pt.exists():
                success_delta += 1
            else:
                failed_delta += 1
            if processed_delta >= report_every:
                processed_delta, success_delta, failed_delta = flush_progress(
                    progress_queue, processed_delta, success_delta, failed_delta
                )
            continue

        try:
            semantic_tgt, global_tgt, global_ref = encode_sample(tokenizer, wav_path)
            obj = {
                "semantic_tgt": semantic_tgt.detach().cpu().long(),
                "global_tgt": global_tgt.detach().cpu().long(),
                "global_ref": global_ref.detach().cpu().long(),
            }
            atomic_torch_save(obj, out_pt)
            if err_pt.exists():
                err_pt.unlink()
            success_delta += 1
        except Exception as exc:
            write_failure_marker(err_pt, exc)
            failed_delta += 1

        processed_delta += 1
        if processed_delta >= report_every:
            processed_delta, success_delta, failed_delta = flush_progress(
                progress_queue, processed_delta, success_delta, failed_delta
            )

    flush_progress(progress_queue, processed_delta, success_delta, failed_delta)


def monitor_progress(progress_queue, total_tasks, procs):
    done = 0
    success = 0
    failed = 0
    bar = tqdm(total=total_tasks, desc="Total", dynamic_ncols=True, mininterval=1.0)

    while True:
        drained = False
        while True:
            if done >= total_tasks and not any(p.is_alive() for p in procs):
                break
            try:
                processed_delta, success_delta, failed_delta = progress_queue.get(timeout=0.2)
            except Empty:
                break

            done += processed_delta
            success += success_delta
            failed += failed_delta
            bar.update(processed_delta)
            drained = True

        if drained:
            bar.set_postfix(success=success, failed=failed, refresh=False)

        if done >= total_tasks and not any(p.is_alive() for p in procs):
            break

    bar.set_postfix(success=success, failed=failed, refresh=False)
    bar.close()
    return success, failed


def parse_args():
    parser = argparse.ArgumentParser(description="Extract Spark BiCodec tensors from wav paths in a TSV file.")
    parser.add_argument("--tsv", required=True, help="Input TSV with a `path` column.")
    parser.add_argument(
        "--model_root",
        default=str(DEFAULT_MODEL_ROOT),
        help="Spark-TTS model root used by BiCodecTokenizer.",
    )
    parser.add_argument(
        "--save_dir",
        default=str(DEFAULT_SAVE_DIR),
        help="Directory to save extracted codec .pt files.",
    )
    parser.add_argument("--gpus", default="0", help="Comma-separated GPU ids, e.g. 0,1,2,3")
    parser.add_argument("--ppg", type=int, default=1, help="Processes per GPU.")
    parser.add_argument(
        "--retry_failed",
        action="store_true",
        help="Retry samples previously marked by .err.txt files.",
    )
    parser.add_argument(
        "--progress_report_every",
        type=int,
        default=8,
        help="How many samples a worker processes before reporting progress.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    rows = read_tsv(args.tsv, args.save_dir, retry_failed=args.retry_failed)
    if not rows:
        print("Done: no new samples to process.")
        return

    gpu_list = [int(x) for x in args.gpus.split(",") if x.strip()]
    num_gpus = len(gpu_list)
    total_procs = num_gpus * args.ppg

    print(f"Launch: {num_gpus} GPUs x {args.ppg} processes per GPU = {total_procs} workers")

    ctx = mp.get_context("spawn")
    progress_queue = ctx.Queue()
    procs = []

    for rank in range(total_procs):
        gpu_id = gpu_list[rank % num_gpus]
        shard = shard_list(rows, total_procs, rank)
        if not shard:
            continue

        proc = ctx.Process(
            target=process_shard,
            args=(rank, args, gpu_id, shard, progress_queue),
            daemon=False,
        )
        proc.start()
        procs.append(proc)

    success, failed = monitor_progress(progress_queue, len(rows), procs)

    for proc in procs:
        proc.join()

    print(f"Done. success={success}, failed={failed}")


if __name__ == "__main__":
    main()
