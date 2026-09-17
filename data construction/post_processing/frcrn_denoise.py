#!/usr/bin/env python3
"""Run FRCRN noise suppression for audio paths listed in a TSV file."""

from __future__ import annotations

import argparse
import contextlib
import csv
import math
import os
import platform
import queue
import sys
import time
from multiprocessing import get_context
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TSV = REPO_ROOT / "test" / "frcrn" / "segment.tsv"
DEFAULT_OUT_DIR = REPO_ROOT / "test" / "segment_denoised"
DEFAULT_MODEL = REPO_ROOT / "model" / "frcrn"
DEFAULT_CACHE_DIR = REPO_ROOT / ".cache"


def parse_gpu_ids(gpu_text: str) -> list[int]:
    gpu_ids = []
    for item in gpu_text.split(","):
        item = item.strip()
        if item:
            gpu_ids.append(int(item))
    if not gpu_ids:
        raise ValueError("GPU list cannot be empty, for example: --gpus 0 or --gpus 0,1")
    return gpu_ids


def format_seconds(seconds: float | None) -> str:
    if seconds is None or math.isinf(seconds):
        return "--:--:--"
    seconds = max(0, int(seconds))
    hours, remain = divmod(seconds, 3600)
    minutes, secs = divmod(remain, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def render_progress(done: int, total: int, error_count: int, start_time: float) -> None:
    elapsed = max(time.time() - start_time, 1e-6)
    rate = done / elapsed
    remaining = max(total - done, 0)
    eta_seconds = (remaining / rate) if rate > 0 else math.inf
    percent = (done / total * 100) if total else 100.0

    bar_width = 24
    filled = min(bar_width, int(bar_width * done / total)) if total else bar_width
    bar = "#" * filled + "-" * (bar_width - filled)
    msg = (
        f"\r[{bar}] {done}/{total} {percent:5.1f}% | "
        f"err={error_count} | {rate:.2f} it/s | "
        f"elapsed={format_seconds(elapsed)} | eta={format_seconds(eta_seconds)}"
    )
    sys.stdout.write(msg)
    sys.stdout.flush()


def resolve_input_path(path_text: str, tsv_path: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (tsv_path.parent / path).resolve()


def build_tasks(tsv_path: Path, out_dir: Path, overwrite: bool) -> tuple[list[tuple[str, str]], int, int]:
    if not tsv_path.exists():
        raise FileNotFoundError(f"TSV does not exist: {tsv_path}")

    tasks = []
    skipped = 0
    missing = 0

    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if "path" not in (reader.fieldnames or []):
            raise ValueError(f"{tsv_path} does not contain a 'path' column.")

        for row in reader:
            path_text = (row.get("path") or "").strip()
            if not path_text:
                continue

            in_path = resolve_input_path(path_text, tsv_path)
            out_path = out_dir / in_path.name

            if not in_path.exists():
                print(f"[Missing] {in_path}", flush=True)
                missing += 1
                continue

            if out_path.exists() and not overwrite:
                skipped += 1
                continue

            tasks.append((str(in_path), str(out_path)))

    return tasks, skipped, missing


def set_runtime_env(tmp_dir: Path, modelscope_cache: Path, hf_cache: Path) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    modelscope_cache.mkdir(parents=True, exist_ok=True)
    hf_cache.mkdir(parents=True, exist_ok=True)

    os.environ["TMPDIR"] = str(tmp_dir)
    os.environ["TEMP"] = str(tmp_dir)
    os.environ["TMP"] = str(tmp_dir)
    os.environ["MODELSCOPE_CACHE"] = str(modelscope_cache)
    os.environ["HF_HOME"] = str(hf_cache)
    os.environ["TRANSFORMERS_CACHE"] = str(hf_cache)

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")


def worker_loop(
    device: str,
    worker_idx: int,
    model: str,
    tmp_base: str,
    modelscope_cache: str,
    hf_cache: str,
    task_queue,
    result_queue,
) -> None:
    worker_tmp = Path(tmp_base) / f"worker_{worker_idx}"
    set_runtime_env(worker_tmp, Path(modelscope_cache), Path(hf_cache))

    try:
        import torch
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks

        torch.set_num_threads(1)
        if hasattr(torch, "set_num_interop_threads"):
            torch.set_num_interop_threads(1)
        if device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.set_device(int(device.split(":", 1)[1]))
    except Exception as e:
        print(f"[Worker {worker_idx}] import/init warning on {device}: {e}", flush=True)
        result_queue.put(("worker_error", str(e)))
        return

    print(f"[Worker {worker_idx}] init FRCRN pipeline on {device}", flush=True)
    try:
        ans = pipeline(
            task=Tasks.acoustic_noise_suppression,
            model=model,
            device=device,
        )
    except Exception as e:
        print(f"[Worker {worker_idx}] pipeline init failed on {device}: {e}", flush=True)
        result_queue.put(("worker_error", str(e)))
        return

    processed = 0
    start_time = time.time()

    while True:
        try:
            task = task_queue.get(timeout=5)
        except queue.Empty:
            continue

        if task is None:
            break

        in_path, out_path = task
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(os.devnull, "w") as devnull, contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                result = ans(in_path, output_path=out_path)
            processed += 1
            result_queue.put(("ok", result.get("output_wav", out_path)))
        except Exception as e:
            print(f"[Error][{device}] {in_path}: {e}", flush=True)
            result_queue.put(("error", in_path))

    result_queue.put(
        ("worker_done", {"device": device, "processed": processed, "elapsed": time.time() - start_time})
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch denoise audio segments with FRCRN.")
    parser.add_argument("--tsv", type=Path, default=DEFAULT_TSV, help="TSV file with a 'path' column.")
    parser.add_argument(
        "--out-dir",
        "--out_dir",
        dest="out_dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for denoised audio files.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=str(DEFAULT_MODEL),
        help="Local FRCRN model directory or a ModelScope model id.",
    )
    parser.add_argument("--gpus", type=str, default="0", help="GPU ids, for example: 0 or 0,1.")
    parser.add_argument("--cpu", action="store_true", help="Run on CPU instead of CUDA.")
    parser.add_argument(
        "--workers-per-gpu",
        "--workers_per_gpu",
        dest="workers_per_gpu",
        type=int,
        default=1,
        help="Number of worker processes per GPU.",
    )
    parser.add_argument(
        "--start-method",
        "--start_method",
        dest="start_method",
        type=str,
        default="fork" if platform.system() == "Linux" else "spawn",
        choices=["fork", "spawn", "forkserver"],
        help="Multiprocessing start method.",
    )
    parser.add_argument("--tmp-dir", type=Path, default=DEFAULT_CACHE_DIR / "frcrn_tmp")
    parser.add_argument("--modelscope-cache", type=Path, default=DEFAULT_CACHE_DIR / "modelscope")
    parser.add_argument("--hf-cache", type=Path, default=DEFAULT_CACHE_DIR / "huggingface")
    parser.add_argument("--overwrite", action="store_true", help="Reprocess files that already exist.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tsv_path = args.tsv.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks, skipped, missing = build_tasks(tsv_path, out_dir, args.overwrite)
    devices = ["cpu"] if args.cpu else [f"cuda:{gpu_id}" for gpu_id in parse_gpu_ids(args.gpus)]
    total_workers = len(devices) if args.cpu else len(devices) * args.workers_per_gpu

    print(f"TSV: {tsv_path}", flush=True)
    print(f"Output dir: {out_dir}", flush=True)
    print(f"Model: {args.model}", flush=True)
    print(f"Devices: {devices}", flush=True)
    print(f"Workers: {total_workers}", flush=True)
    print(f"Pre-skip existing files: {skipped}", flush=True)
    print(f"Missing input files: {missing}", flush=True)
    print(f"Files queued for processing: {len(tasks)}", flush=True)

    if not tasks:
        print("No files need processing.", flush=True)
        return

    worker_devices = []
    for device in devices:
        repeats = 1 if args.cpu else args.workers_per_gpu
        worker_devices.extend([device] * repeats)

    ctx = get_context(args.start_method)
    task_queue = ctx.Queue()
    result_queue = ctx.Queue()
    workers = []

    for worker_idx, device in enumerate(worker_devices):
        p = ctx.Process(
            target=worker_loop,
            args=(
                device,
                worker_idx,
                args.model,
                str(args.tmp_dir.resolve()),
                str(args.modelscope_cache.resolve()),
                str(args.hf_cache.resolve()),
                task_queue,
                result_queue,
            ),
        )
        p.start()
        workers.append(p)

    for task in tasks:
        task_queue.put(task)

    for _ in workers:
        task_queue.put(None)

    done_workers = 0
    ok_count = 0
    error_count = 0
    start_time = time.time()
    report_every = max(10, min(200, math.ceil(len(tasks) / 20)))
    last_progress_time = 0.0

    render_progress(done=0, total=len(tasks), error_count=0, start_time=start_time)

    while done_workers < len(workers):
        msg_type, payload = result_queue.get()
        if msg_type == "ok":
            ok_count += 1
        elif msg_type in {"error", "worker_error"}:
            error_count += 1
            if msg_type == "worker_error":
                done_workers += 1
                continue
        elif msg_type == "worker_done":
            done_workers += 1
            sys.stdout.write("\n")
            print(f"[WorkerDone] {payload}", flush=True)
            last_progress_time = 0.0

        if msg_type in {"ok", "error"}:
            total_finished = ok_count + error_count
            now = time.time()
            if total_finished == len(tasks) or total_finished % report_every == 0 or now - last_progress_time >= 2.0:
                render_progress(
                    done=total_finished,
                    total=len(tasks),
                    error_count=error_count,
                    start_time=start_time,
                )
                last_progress_time = now

    for p in workers:
        p.join()

    total_elapsed = time.time() - start_time
    sys.stdout.write("\n")
    print(
        f"Done. ok={ok_count}, error={error_count}, skipped={skipped}, "
        f"missing={missing}, elapsed={total_elapsed:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
