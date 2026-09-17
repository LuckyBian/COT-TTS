#!/usr/bin/env python3
"""Attach audio features and MOS scores to standardized JSON files."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "test" / "json_all_emo"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "test" / "json_all_audio_features"
DEFAULT_FEATURES_TSV = REPO_ROOT / "test" / "metrics" / "audio_features.tsv"
DEFAULT_DNSMOS_TSV = REPO_ROOT / "test" / "metrics" / "dnsmos.tsv"
DEFAULT_UTMOS_TSV = REPO_ROOT / "test" / "metrics" / "utmosv2.tsv"


FLOAT_FIELDS = {
    "total_duration_sec",
    "active_duration_sec",
    "silence_duration_sec",
    "active_ratio",
    "rms",
    "rms_dbfs",
    "peak_dbfs",
    "active_rms",
    "active_rms_dbfs",
    "active_peak_dbfs",
    "arousal",
    "dominance",
    "valence",
    "expression_intensity",
    "dnsmos",
    "utmosv2",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add audio features and metric scores to JSON segments.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--features-tsv", type=Path, default=DEFAULT_FEATURES_TSV)
    parser.add_argument("--dnsmos-tsv", type=Path, default=DEFAULT_DNSMOS_TSV)
    parser.add_argument("--utmosv2-tsv", type=Path, default=DEFAULT_UTMOS_TSV)
    parser.add_argument("--indent", type=int, default=2)
    return parser.parse_args()


def parse_float(text: str):
    if text is None:
        return None
    text = str(text).strip()
    if not text or text.lower() == "nan":
        return None
    value = float(text)
    if math.isnan(value):
        return None
    return value


def read_tsv(tsv_path: Path) -> dict[str, dict]:
    if not tsv_path.exists():
        return {}
    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        id_col = "segment_id" if "segment_id" in (reader.fieldnames or []) else "eval_id"
        result = {}
        for row in reader:
            segment_id = (row.get(id_col) or "").strip()
            if not segment_id:
                continue
            clean = {}
            for key, value in row.items():
                if key == id_col:
                    continue
                clean[key] = parse_float(value) if key in FLOAT_FIELDS else value
            result[segment_id] = clean
    return result


def build_public_audio_features(
    segment_id: str,
    feature_map: dict[str, dict],
    dnsmos_map: dict[str, dict],
    utmos_map: dict[str, dict],
) -> dict:
    raw_features = feature_map.get(segment_id, {})
    public_features = {
        "duration": raw_features.get("total_duration_sec"),
        "active_duration": raw_features.get("active_duration_sec"),
        "loudness": raw_features.get("rms_dbfs"),
        "expressive_intensity": raw_features.get("expression_intensity"),
    }
    if segment_id in utmos_map:
        public_features["naturalness score"] = utmos_map[segment_id].get("utmosv2")
    if segment_id in dnsmos_map:
        public_features["noise score"] = dnsmos_map[segment_id].get("dnsmos")
    return {key: value for key, value in public_features.items() if value is not None}


def attach(data: dict, feature_map: dict[str, dict], dnsmos_map: dict[str, dict], utmos_map: dict[str, dict]) -> tuple[int, int]:
    matched = 0
    missing = 0
    segments = data.get("segment")
    if segments is None:
        segments = data.get("segments")
    if not isinstance(segments, list):
        return matched, missing

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_id = segment.get("segment_id")
        features = build_public_audio_features(segment_id, feature_map, dnsmos_map, utmos_map)

        if features:
            segment["audio_features"] = features
            matched += 1
        else:
            missing += 1
    return matched, missing


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input JSON directory not found: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_map = read_tsv(args.features_tsv.resolve())
    dnsmos_map = read_tsv(args.dnsmos_tsv.resolve())
    utmos_map = read_tsv(args.utmosv2_tsv.resolve())
    print(
        f"Loaded features={len(feature_map)}, dnsmos={len(dnsmos_map)}, utmosv2={len(utmos_map)}",
        flush=True,
    )

    total_matched = 0
    total_missing = 0
    files = sorted(input_dir.glob("*.json"))
    for input_json in files:
        data = json.loads(input_json.read_text(encoding="utf-8"))
        matched, missing = attach(data, feature_map, dnsmos_map, utmos_map)
        (output_dir / input_json.name).write_text(
            json.dumps(data, ensure_ascii=False, indent=args.indent),
            encoding="utf-8",
        )
        total_matched += matched
        total_missing += missing
        print(f"{input_json.name}: matched={matched}, missing={missing}", flush=True)

    print(
        f"Done. files={len(files)}, matched={total_matched}, missing={total_missing}, output_dir={output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
