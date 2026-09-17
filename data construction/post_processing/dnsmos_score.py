#!/usr/bin/env python3
"""Compute DNSMOSPro scores for audio segments."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_TSV = REPO_ROOT / "test" / "metrics" / "segments.tsv"
DEFAULT_OUTPUT_TSV = REPO_ROOT / "test" / "metrics" / "dnsmos.tsv"
DEFAULT_MODEL = REPO_ROOT / "model" / "dnsmospro" / "NISQA" / "model_best.pt"
TARGET_SR = 16000
TARGET_LEN = 10 * TARGET_SR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute DNSMOSPro scores into a TSV.")
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_INPUT_TSV)
    parser.add_argument("--output-tsv", type=Path, default=DEFAULT_OUTPUT_TSV)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--batch-size", type=int, default=32)
    return parser.parse_args()


def read_rows(tsv_path: Path) -> list[tuple[str, Path]]:
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = []
        for row in reader:
            path_text = (row.get("output_audio") or row.get("path") or "").strip()
            eval_id = (row.get("eval_id") or "").strip()
            if not path_text:
                continue
            path = Path(path_text)
            if not path.is_absolute():
                path = (tsv_path.parent / path).resolve()
            rows.append((eval_id or path.stem, path))
    return rows


def load_audio(path: Path) -> np.ndarray:
    samples, sr = sf.read(str(path), always_2d=False, dtype="float32")
    if samples.ndim == 2:
        samples = np.mean(samples, axis=1)
    if sr != TARGET_SR:
        samples = librosa.resample(samples, orig_sr=sr, target_sr=TARGET_SR, res_type="scipy")
    samples = np.asarray(samples, dtype=np.float32)
    if samples.size == 0:
        raise ValueError(f"Empty audio file: {path}")
    while samples.shape[0] < TARGET_LEN:
        samples = np.concatenate([samples, samples], axis=0)
    return samples[:TARGET_LEN]


def stft(samples: np.ndarray) -> np.ndarray:
    spec = librosa.stft(y=samples, win_length=320, hop_length=160, n_fft=320)
    spec = np.abs(spec).T
    spec = np.clip(spec, 10 ** -7, 10 ** 7)
    return np.log10(spec)


def build_spec(path: Path) -> torch.Tensor:
    return torch.FloatTensor(stft(load_audio(path))).unsqueeze(0)


def batched(items, batch_size: int):
    for start in range(0, len(items), max(1, batch_size)):
        yield items[start : start + max(1, batch_size)]


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input_tsv.resolve())
    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    model = torch.jit.load(str(args.model_path.resolve()), map_location=torch.device(args.device)).to(args.device)
    model.eval()

    output_rows = []
    for batch in batched(rows, args.batch_size):
        eval_ids = [item[0] for item in batch]
        paths = [item[1] for item in batch]
        try:
            spec_batch = torch.stack([build_spec(path) for path in paths], dim=0).to(args.device)
            with torch.no_grad():
                scores = model(spec_batch)[:, 0].detach().cpu().numpy().astype("float64").tolist()
        except Exception as exc:
            print(f"[dnsmos] batch failed: {exc}", flush=True)
            scores = [math.nan] * len(batch)
        output_rows.extend(zip(eval_ids, scores))
        print(f"processed {len(output_rows)}/{len(rows)}", flush=True)

    with args.output_tsv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["segment_id", "dnsmos"])
        for eval_id, score in output_rows:
            writer.writerow([eval_id, "nan" if math.isnan(score) else f"{score:.6f}"])
    print(f"Wrote {len(output_rows)} rows to {args.output_tsv}")


if __name__ == "__main__":
    main()
