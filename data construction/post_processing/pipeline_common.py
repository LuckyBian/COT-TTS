#!/usr/bin/env python3
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    text = str(name or "unknown")
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        text = text.replace(char, "_")
    return text.replace(" ", "_")


def iter_json_files(input_dir: Path) -> Iterator[Path]:
    for path in sorted(input_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}:
            yield path


def load_json(path: Path) -> Any:
    raw = path.read_bytes().replace(b"\x00", b"")
    text = raw.decode("utf-8", errors="ignore").strip()
    if not text:
        raise ValueError(f"Empty JSON file: {path}")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    try:
        item, end = decoder.raw_decode(text)
    except json.JSONDecodeError as exc:
        context = text[max(0, exc.pos - 80): min(len(text), exc.pos + 80)]
        raise ValueError(
            f"Failed to decode JSON content in {path} near char {exc.pos}: {context!r}"
        ) from exc

    trailing = text[end:].strip()
    if not trailing:
        return item

    if "\n" in text:
        jsonl_items: List[Any] = []
        jsonl_ok = True
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if not line:
                continue
            try:
                jsonl_items.append(json.loads(line))
            except json.JSONDecodeError:
                jsonl_ok = False
                break
        if jsonl_ok and jsonl_items:
            if len(jsonl_items) == 1:
                return jsonl_items[0]
            return jsonl_items

    return item


def dump_json_atomic(path: Path, data: Any, indent: int = 2) -> None:
    ensure_dir(path.parent)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    os.replace(tmp_path, path)


def load_segments_from_json(data: Any) -> Optional[List[Dict[str, Any]]]:
    if isinstance(data, dict) and isinstance(data.get("segment"), list):
        return data["segment"]
    if isinstance(data, dict) and isinstance(data.get("segments"), list):
        return data["segments"]
    if isinstance(data, list) and all(isinstance(x, dict) for x in data):
        return data
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_segment(seg: Dict[str, Any], fallback_segment_id: str) -> Dict[str, Any]:
    text = seg.get("text")
    if text is None:
        text = seg.get("sentence")

    lang = seg.get("lang")
    if lang is None:
        lang = seg.get("language")

    return {
        "segment_id": str(seg.get("segment_id") or fallback_segment_id),
        "speaker": seg.get("speaker"),
        "start": _to_float(seg.get("start")),
        "end": _to_float(seg.get("end")),
        "text": text,
        "lang": lang,
    }


def normalize_movie_record(data: Any, source_path: Path) -> Dict[str, Any]:
    segments = load_segments_from_json(data)
    if segments is None:
        raise ValueError(f"Unsupported JSON structure: {source_path}")

    stem = source_path.stem
    output: Dict[str, Any] = {
        "name": stem,
        "source_file": source_path.name,
        "segment": [],
    }

    if isinstance(data, dict):
        if data.get("name") is not None:
            output["name"] = data.get("name")
        if data.get("source_file") is not None:
            output["source_file"] = data.get("source_file")
        if data.get("meta") is not None:
            output["meta"] = data.get("meta")
        if data.get("num_speakers") is not None:
            output["num_speakers"] = data.get("num_speakers")
        if data.get("languages") is not None:
            output["languages"] = data.get("languages")

    for index, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        fallback_segment_id = f"{stem}_{index:06d}"
        output["segment"].append(normalize_segment(seg, fallback_segment_id))

    return output


def build_output_filename(movie: Dict[str, Any], default_stem: str) -> str:
    return f"{safe_filename(str(movie.get('name') or default_stem))}.json"
