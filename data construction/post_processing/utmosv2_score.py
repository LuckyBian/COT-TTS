#!/usr/bin/env python3
"""Compute UTMOSv2 scores for audio segments."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_TSV = REPO_ROOT / "test" / "metrics" / "segments.tsv"
DEFAULT_OUTPUT_TSV = REPO_ROOT / "test" / "metrics" / "utmosv2.tsv"
DEFAULT_MODEL_DIR = REPO_ROOT / "model" / "utmosv2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute UTMOSv2 scores into a TSV.")
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_INPUT_TSV)
    parser.add_argument("--output-tsv", type=Path, default=DEFAULT_OUTPUT_TSV)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--folds", default="0,1,2,3,4")
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--predict-dataset", default="sarulab")
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


def parse_folds(text: str) -> list[int]:
    folds = [int(item.strip()) for item in text.split(",") if item.strip()]
    if not folds:
        raise ValueError("No folds provided.")
    return folds


def batched(items, batch_size: int):
    for start in range(0, len(items), max(1, batch_size)):
        yield items[start : start + max(1, batch_size)]


def main() -> None:
    args = parse_args()
    from utmosv2.dataset._schema import DatasetItem
    from utmosv2.utils import get_dataset
    import utmosv2

    rows = read_rows(args.input_tsv.resolve())
    folds = parse_folds(args.folds)
    models = []
    for fold in folds:
        checkpoint_path = args.model_dir.resolve() / f"fold{fold}_s42_best_model.pth"
        print(f"[utmosv2] loading fold={fold}: {checkpoint_path}", flush=True)
        model = utmosv2.create_model(pretrained=True, checkpoint_path=checkpoint_path, fold=fold, device=args.device)
        model.eval().to(args.device)
        models.append(model)

    score_sums = [0.0] * len(rows)
    valid = [True] * len(rows)
    for batch_start in range(0, len(rows), max(1, args.batch_size)):
        batch = rows[batch_start : batch_start + max(1, args.batch_size)]
        paths = [path for _eval_id, path in batch]
        data_internal = [DatasetItem(file_path=path, dataset_name=args.predict_dataset) for path in paths]
        template = models[0]
        old_state = getattr(template._cfg.dataset, "remove_silent_section", None)
        template._cfg.dataset.remove_silent_section = True
        dataset = get_dataset(template._cfg, data_internal, template._cfg.phase)
        template._cfg.dataset.remove_silent_section = old_state

        for model in models:
            dataloader = torch.utils.data.DataLoader(
                dataset,
                batch_size=args.batch_size,
                shuffle=False,
                num_workers=args.num_workers,
                pin_memory=args.device.startswith("cuda"),
            )
            try:
                predictions = model._predict_impl(
                    dataloader=dataloader,
                    num_repetitions=1,
                    device=args.device,
                    verbose=False,
                )
                if hasattr(predictions, "detach"):
                    values = predictions.detach().cpu().numpy().astype("float64").tolist()
                else:
                    values = np.asarray(predictions, dtype="float64").tolist()
            except Exception as exc:
                print(f"[utmosv2] batch failed: {exc}", flush=True)
                values = [math.nan] * len(batch)
            for local_idx, value in enumerate(values):
                global_idx = batch_start + local_idx
                if math.isnan(value):
                    valid[global_idx] = False
                else:
                    score_sums[global_idx] += float(value)
        print(f"processed {min(batch_start + len(batch), len(rows))}/{len(rows)}", flush=True)

    args.output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_tsv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["segment_id", "utmosv2"])
        for idx, (eval_id, _path) in enumerate(rows):
            score = score_sums[idx] / len(models) if valid[idx] else math.nan
            writer.writerow([eval_id, "nan" if math.isnan(score) else f"{score:.6f}"])
    print(f"Wrote {len(rows)} rows to {args.output_tsv}")


if __name__ == "__main__":
    main()
