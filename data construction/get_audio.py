#!/usr/bin/env python3
import argparse
import json
import subprocess
from multiprocessing import Pool
from pathlib import Path
from typing import Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_AUDIO_DIR = REPO_ROOT / "data" / "audios"
DEFAULT_JSON_DIR = REPO_ROOT / "test" / "json_all"
DEFAULT_SEGMENT_DIR = REPO_ROOT / "test" / "segment"


def load_segments_from_json(data) -> Optional[List[Dict]]:
    if isinstance(data, dict) and isinstance(data.get("segment"), list):
        return data["segment"]
    if isinstance(data, dict) and isinstance(data.get("segments"), list):
        return data["segments"]
    if isinstance(data, list) and all(isinstance(x, dict) for x in data):
        return data
    return None


def cut_audio_with_ffmpeg(infile: Path, outfile: Path, start: float, end: float) -> None:
    duration = end - start
    if duration <= 0:
        raise ValueError(f"Invalid duration: start={start}, end={end}")

    outfile.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-i",
        str(infile),
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(outfile),
    ]
    subprocess.run(cmd, check=True)


def infer_audio_stem(json_path: Path, data) -> str:
    if isinstance(data, dict):
        source_file = data.get("source_file")
        if isinstance(source_file, str) and source_file:
            return Path(source_file).stem
        name = data.get("name")
        if isinstance(name, str) and name:
            return name
    return json_path.stem


def find_audio(audio_dir: Path, stem: str) -> Optional[Path]:
    for suffix in (".wav", ".mp3", ".flac", ".m4a"):
        path = audio_dir / f"{stem}{suffix}"
        if path.exists():
            return path
    return None


def process_one_json(task) -> None:
    json_path, audio_dir, segment_dir = task
    json_path = Path(json_path)
    audio_dir = Path(audio_dir)
    segment_dir = Path(segment_dir)

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"[ERROR] Failed to load JSON {json_path}: {exc}")
        return

    segments = load_segments_from_json(data)
    if segments is None:
        print(f"[WARN] Unsupported JSON structure, skip: {json_path}")
        return

    audio_stem = infer_audio_stem(json_path, data)
    audio_path = find_audio(audio_dir, audio_stem)
    if audio_path is None:
        print(f"[WARN] Audio not found for JSON: {json_path} -> {audio_dir}/{audio_stem}.*")
        return

    for idx, seg in enumerate(segments):
        seg_id = seg.get("segment_id")
        start = seg.get("start")
        end = seg.get("end")

        if seg_id is None:
            print(f"[WARN] No segment_id in {json_path} segment index {idx}, skip.")
            continue
        if start is None or end is None:
            print(f"[WARN] Missing start/end in {json_path} segment {seg_id}, skip.")
            continue

        out_path = segment_dir / f"{seg_id}.wav"
        if out_path.exists():
            print(f"[SKIP] Segment already exists: {out_path}")
            continue

        try:
            start = float(start)
            end = float(end)
            cut_audio_with_ffmpeg(audio_path, out_path, start, end)
            print(f"[OK] {json_path} -> {out_path}")
        except Exception as exc:
            print(f"[ERROR] Failed to cut segment {seg_id} from {audio_path}: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cut segment audio from first-stage JSON.")
    parser.add_argument("--audio-dir", default=str(DEFAULT_AUDIO_DIR))
    parser.add_argument("--json-dir", default=str(DEFAULT_JSON_DIR))
    parser.add_argument("--segment-dir", default=str(DEFAULT_SEGMENT_DIR))
    parser.add_argument("--num-workers", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audio_dir = Path(args.audio_dir)
    json_dir = Path(args.json_dir)
    segment_dir = Path(args.segment_dir)
    segment_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(path for path in json_dir.iterdir() if path.suffix.lower() == ".json")
    print(f"Found {len(json_files)} JSON files.")

    tasks = [(path, audio_dir, segment_dir) for path in json_files]
    if args.num_workers <= 1:
        for task in tasks:
            process_one_json(task)
    else:
        with Pool(processes=args.num_workers) as pool:
            for _ in pool.imap_unordered(process_one_json, tasks):
                pass

    print("\nAll done.")


if __name__ == "__main__":
    main()
