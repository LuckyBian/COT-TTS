#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import json
import shutil
from collections import OrderedDict
from datetime import datetime
from pathlib import Path


DOCS_ROOT = Path("/aifs4su/weizhenbian/code/COT-TTS/docs")
DEMO_ROOT = Path("/aifs4su/weizhenbian/code/cot-tts-eval/demo")
GT_ROOT = Path("/aifs4su/weizhenbian/code/cot-tts-baseline/GT")

MODEL_SPECS = OrderedDict(
    [
        (
            "ground_truth",
            {
                "key": "ground_truth",
                "display_key": "ground-truth",
                "name": "Ground Truth",
                "family": "gt",
                "family_label": "GT",
            },
        ),
        (
            "0.6B_n",
            {
                "key": "final__our-0.6",
                "display_key": "our-0.6",
                "name": "Our-0.6B",
                "family": "final",
                "family_label": "Our",
            },
        ),
        (
            "1.7B_n",
            {
                "key": "final__our-1.7",
                "display_key": "our-1.7",
                "name": "Our-1.7B",
                "family": "final",
                "family_label": "Our",
            },
        ),
        (
            "three-dia-a3b-fish2",
            {
                "key": "three__dia-a3b-fish2",
                "display_key": "three__dia-a3b-fish2",
                "name": "Three-stage: DiA + A3B + Fish2",
                "family": "three",
                "family_label": "Three-stage",
            },
        ),
        (
            "three-dia-a3b-voxcpm",
            {
                "key": "three__dia-a3b-voxcpm",
                "display_key": "three__dia-a3b-voxcpm",
                "name": "Three-stage: DiA + A3B + VoxCPM",
                "family": "three",
                "family_label": "Three-stage",
            },
        ),
        (
            "three-qwen3asr-a3b-fish2",
            {
                "key": "three__qwen3asr-a3b-fish2",
                "display_key": "three__qwen3asr-a3b-fish2",
                "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
                "family": "three",
                "family_label": "Three-stage",
            },
        ),
        (
            "three-qwenasr-a3b-voxcpm",
            {
                "key": "three__qwenasr-a3b-voxcpm",
                "display_key": "three__qwenasr-a3b-voxcpm",
                "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
                "family": "three",
                "family_label": "Three-stage",
            },
        ),
        (
            "two-qwen-fish",
            {
                "key": "two__qwen-fish",
                "display_key": "two__qwen-fish",
                "name": "Two-stage: Qwen + Fish",
                "family": "two",
                "family_label": "Two-stage",
            },
        ),
        (
            "two-qwen-voxcpm",
            {
                "key": "two__qwen-voxcpm",
                "display_key": "two__qwen-voxcpm",
                "name": "Two-stage: Qwen + VoxCPM",
                "family": "two",
                "family_label": "Two-stage",
            },
        ),
        (
            "two-qwen3omni-seedvc",
            {
                "key": "two__qwen3omni-seedvc",
                "display_key": "two__qwen3omni-seedvc",
                "name": "Two-stage: Qwen3-Omni + SeedVC",
                "family": "two",
                "family_label": "Two-stage",
            },
        ),
    ]
)

LANGUAGE_LIMITS = {
    "en": 5,
    "zh": 5,
}

LANGUAGE_ORDER = {
    "zh": 0,
    "en": 1,
}

PREFERRED_EVAL_IDS = {
    "en": [
        "eval-en-100552",
        "eval-en-284755",
        "eval-en-955164",
        "eval-en-1167838",
        "eval-en-1541641",
    ],
}


def read_manifest() -> OrderedDict[str, dict]:
    grouped: OrderedDict[str, dict] = OrderedDict()
    manifest_path = DEMO_ROOT / "manifest.tsv"
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            eval_id = row["eval_id"]
            item = grouped.setdefault(
                eval_id,
                {
                    "eval_id": eval_id,
                    "language": row["language"],
                    "history_audio": Path(row["history_audio"]),
                    "target_text_path": Path(row["target_text"]),
                    "reference_audio": GT_ROOT / row["language"] / "ref_audio" / f"{eval_id}.wav",
                    "outputs": {},
                },
            )
            item["outputs"][row["model"]] = Path(row["output_audio"])
    return grouped


def load_existing_featured() -> list[dict]:
    demo_data_path = DOCS_ROOT / "demo-data.js"
    if not demo_data_path.exists():
        return []
    text = demo_data_path.read_text(encoding="utf-8")
    marker = '"featured": '
    start = text.find(marker)
    if start < 0:
        return []
    bracket_start = text.find("[", start)
    if bracket_start < 0:
        return []
    depth = 0
    for idx in range(bracket_start, len(text)):
        char = text[idx]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return ast.literal_eval(text[bracket_start:idx + 1])
    return []


def ensure_clean_demo_dirs() -> None:
    for path in DOCS_ROOT.iterdir():
        if path.is_dir() and (path.name.startswith("eval-en-") or path.name.startswith("eval-zh-")):
            shutil.rmtree(path)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def parse_cot(eval_id: str, language: str) -> tuple[str, str]:
    cot_path = GT_ROOT / language / "cot" / f"{eval_id}.txt"
    text = cot_path.read_text(encoding="utf-8").strip()
    summary = ""
    if "[Summary]" in text:
        summary = text.split("[Summary]", 1)[1].strip()
    return summary, text


def main() -> None:
    grouped = read_manifest()
    existing_featured = load_existing_featured()
    ensure_clean_demo_dirs()

    items = []
    total_entries = 0
    kept_per_language = {key: 0 for key in LANGUAGE_LIMITS}
    preferred_rank = {}
    for language, eval_ids in PREFERRED_EVAL_IDS.items():
        for rank, eval_id in enumerate(eval_ids):
            preferred_rank[(language, eval_id)] = rank

    grouped_items = sorted(
        grouped.items(),
        key=lambda pair: (
            LANGUAGE_ORDER.get(pair[1]["language"], 999),
            preferred_rank.get((pair[1]["language"], pair[0]), 999),
            pair[0],
        ),
    )

    for eval_id, payload in grouped_items:
        language = payload["language"]
        limit = LANGUAGE_LIMITS.get(language)
        if limit is not None and kept_per_language[language] >= limit:
            continue

        if not payload["history_audio"].exists() or not payload["target_text_path"].exists():
            continue

        sample_dir = DOCS_ROOT / eval_id
        sample_dir.mkdir(parents=True, exist_ok=True)
        history_dst = sample_dir / "final__our-0.6" / "history.wav"
        copy_file(payload["history_audio"], history_dst)
        ref_rel = Path(eval_id) / "reference_audio.wav"
        if payload["reference_audio"].exists():
            copy_file(payload["reference_audio"], DOCS_ROOT / ref_rel)
        target_text = payload["target_text_path"].read_text(encoding="utf-8").strip()

        models = []
        gt_src = GT_ROOT / language / "target_audio" / f"{eval_id}.wav"
        if gt_src.exists():
            gt_rel = Path(eval_id) / "ground_truth" / "output.wav"
            copy_file(gt_src, DOCS_ROOT / gt_rel)
            meta = MODEL_SPECS["ground_truth"]
            models.append(
                {
                    "key": meta["key"],
                    "display_key": meta["display_key"],
                    "name": meta["name"],
                    "family": meta["family"],
                    "family_label": meta["family_label"],
                    "output_audio": str(gt_rel).replace("\\", "/"),
                }
            )

        for model_name, meta in list(MODEL_SPECS.items())[1:]:
            output_src = payload["outputs"].get(model_name)
            if output_src is None or not output_src.exists():
                continue
            output_rel = Path(eval_id) / meta["key"] / "output.wav"
            output_dst = DOCS_ROOT / output_rel
            copy_file(output_src, output_dst)
            models.append(
                {
                    "key": meta["key"],
                    "display_key": meta["display_key"],
                    "name": meta["name"],
                    "family": meta["family"],
                    "family_label": meta["family_label"],
                    "output_audio": str(output_rel).replace("\\", "/"),
                }
            )
        total_entries += len(models)
        kept_per_language[language] = kept_per_language.get(language, 0) + 1
        items.append(
            {
                "eval_id": eval_id,
                "language": language,
                "history_audio": f"{eval_id}/final__our-0.6/history.wav",
                "reference_audio": str(ref_rel).replace("\\", "/"),
                "target_text": target_text,
                "models": models,
            }
        )

    demo_data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "num_eval_ids": len(items),
            "num_model_entries": total_entries,
            "num_featured_cases": len(existing_featured),
        },
        "featured": existing_featured,
        "items": sorted(
            items,
            key=lambda item: (
                LANGUAGE_ORDER.get(item["language"], 999),
                item["eval_id"],
            ),
        ),
    }
    demo_js = "window.DEMO_DATA = " + json.dumps(demo_data, ensure_ascii=False, indent=2) + ";\n"
    (DOCS_ROOT / "demo-data.js").write_text(demo_js, encoding="utf-8")
    print(json.dumps(demo_data["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
