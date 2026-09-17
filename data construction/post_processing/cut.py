#!/usr/bin/env python3
"""Split each audio JSON into scenes and add scene_index to segments."""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "test" / "json_all_reference"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "test" / "json_all_scenes"
DEFAULT_MODEL_PATH = os.environ.get(
    "DEEPSEEK_MODEL_PATH",
    str(REPO_ROOT / "model" / "deepseek" / "DeepSeek-R1-Distill-Qwen-14B"),
)
DEFAULT_CUDA_VISIBLE_DEVICES = os.environ.get("DEEPSEEK_CUDA_VISIBLE_DEVICES", "0")
DEFAULT_TP_SIZE = int(os.environ.get("DEEPSEEK_TP_SIZE", str(len(DEFAULT_CUDA_VISIBLE_DEVICES.split(",")))))
DEFAULT_GPU_MEMORY_UTIL = float(os.environ.get("DEEPSEEK_GPU_MEM_UTIL", "0.9"))
DEFAULT_MAX_MODEL_LEN = int(os.environ.get("DEEPSEEK_MAX_MODEL_LEN", "4096"))
DEFAULT_MAX_BATCHED_TOKENS = int(os.environ.get("DEEPSEEK_MAX_BATCHED_TOKENS", "16384"))
DEFAULT_MAX_NUM_SEQS = int(os.environ.get("DEEPSEEK_MAX_NUM_SEQS", "64"))
DEFAULT_ENABLE_CHUNKED_PREFILL = os.environ.get("DEEPSEEK_ENABLE_CHUNKED_PREFILL", "1") != "0"
DEFAULT_TRUST_REMOTE_CODE = os.environ.get("DEEPSEEK_TRUST_REMOTE_CODE", "1") != "0"
DEFAULT_TEMPERATURE = float(os.environ.get("DEEPSEEK_TEMPERATURE", "0.0"))
DEFAULT_TOP_P = float(os.environ.get("DEEPSEEK_TOP_P", "1.0"))
DEFAULT_MAX_NEW_TOKENS = int(os.environ.get("DEEPSEEK_MAX_NEW_TOKENS", "256"))
DEFAULT_REPETITION_PENALTY = float(os.environ.get("DEEPSEEK_REPETITION_PENALTY", "1.0"))
DEFAULT_PROMPT_BATCH_SIZE = int(os.environ.get("DEEPSEEK_PROMPT_BATCH_SIZE", "32"))
SHORT_AUDIO_SCENE_SECONDS = 2 * 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add scene_index fields to per-audio JSON files.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--log-path", type=Path, default=None)
    parser.add_argument("--skip-existing", action="store_true", default=False)
    parser.add_argument("--fixed-t-gap", type=float, default=None)
    parser.add_argument("--max-lines-per-block", type=int, default=100)
    parser.add_argument("--short-audio-seconds", type=float, default=SHORT_AUDIO_SCENE_SECONDS)
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--cuda-visible-devices", default=DEFAULT_CUDA_VISIBLE_DEVICES)
    parser.add_argument("--tensor-parallel-size", type=int, default=DEFAULT_TP_SIZE)
    parser.add_argument("--gpu-memory-utilization", type=float, default=DEFAULT_GPU_MEMORY_UTIL)
    parser.add_argument("--max-model-len", type=int, default=DEFAULT_MAX_MODEL_LEN)
    parser.add_argument("--max-num-batched-tokens", type=int, default=DEFAULT_MAX_BATCHED_TOKENS)
    parser.add_argument("--max-num-seqs", type=int, default=DEFAULT_MAX_NUM_SEQS)
    parser.add_argument("--max-new-tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument("--repetition-penalty", type=float, default=DEFAULT_REPETITION_PENALTY)
    parser.add_argument("--prompt-batch-size", type=int, default=DEFAULT_PROMPT_BATCH_SIZE)
    parser.add_argument("--disable-chunked-prefill", action="store_true")
    parser.add_argument("--disable-trust-remote-code", action="store_true")
    return parser.parse_args()


def make_logger(log_path: Path | None) -> Callable[[str], None]:
    def log(message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line, flush=True)
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    return log


def safe_filename(name: str) -> str:
    text = str(name or "unknown")
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        text = text.replace(char, "_")
    return text.replace(" ", "_")


def iter_json_files(input_dir: Path):
    for path in sorted(input_dir.iterdir()):
        if path.is_file() and path.suffix.lower() == ".json":
            yield path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")
    os.replace(tmp_path, path)


def get_segments(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("segment"), list):
        return data["segment"]
    if isinstance(data, dict) and isinstance(data.get("segments"), list):
        return data["segments"]
    raise ValueError("Input JSON must contain a 'segment' or 'segments' list.")


def output_path_for(input_path: Path, data: Any, output_dir: Path) -> Path:
    if isinstance(data, dict) and data.get("name"):
        return output_dir / f"{safe_filename(str(data['name']))}.json"
    return output_dir / input_path.name


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values_sorted[int(k)]
    return values_sorted[f] * (c - k) + values_sorted[c] * (k - f)


def compute_gaps(segs: list[dict[str, Any]]) -> list[float]:
    gaps = []
    for i in range(1, len(segs)):
        prev_end = segs[i - 1].get("end")
        curr_start = segs[i].get("start")
        if prev_end is None or curr_start is None:
            continue
        gaps.append(float(curr_start) - float(prev_end))
    return gaps


def pick_cut_candidates_by_gap(segs: list[dict[str, Any]], t_gap: float) -> list[int]:
    cuts = []
    for i in range(1, len(segs)):
        prev_end = segs[i - 1].get("end")
        curr_start = segs[i].get("start")
        if prev_end is None or curr_start is None:
            continue
        if float(curr_start) - float(prev_end) >= t_gap:
            cuts.append(i)
    return cuts


def split_by_indices(items: list[Any], cut_indices: list[int], max_chunk_size: int | None = None) -> list[list[Any]]:
    indices = sorted(set(idx for idx in cut_indices if 0 < idx < len(items)))
    pieces = []
    prev = 0
    for idx in indices:
        pieces.append(items[prev:idx])
        prev = idx
    pieces.append(items[prev:])

    if not max_chunk_size or max_chunk_size <= 0:
        return pieces

    out = []
    for piece in pieces:
        if len(piece) <= max_chunk_size:
            out.append(piece)
        else:
            for start in range(0, len(piece), max_chunk_size):
                out.append(piece[start : start + max_chunk_size])
    return out


def build_block_prompt(rel_lines: list[tuple[float, int, str]], t_gap: float, block_start: float) -> list[dict[str, str]]:
    lines = []
    for rel_t, idx, text in rel_lines:
        text_short = (text or "").replace("\n", " ").strip()
        if len(text_short) > 160:
            text_short = text_short[:160] + "..."
        lines.append(f"({rel_t:.3f}, {idx}) \"{text_short}\"")

    return [
        {
            "role": "system",
            "content": (
                "你是影视分场编辑。仅依据台词内容和时间戳判断同一场景的连贯性。"
                "返回本粗块内部的切分点索引，这些索引表示从该索引的句子开始是一个新场景。"
                "输出必须是严格 JSON 数组，纯数字、升序、不得包含 0，也不得等于总句数。"
            ),
        },
        {
            "role": "user",
            "content": (
                "【任务】\n"
                "- 仅考虑时间连续性和台词主题变化。\n"
                "- 不考虑音效、音乐、情感。\n"
                f"- 阈值参考：相邻两句相对时间间隔 >= {t_gap:.2f}s 时更可能换场景。\n\n"
                f"【粗块起始时刻(绝对)】{block_start:.3f}s\n"
                "【句子清单】（相对时间, 索引, 文本）\n"
                + "\n".join(lines)
                + "\n\n请仅输出 JSON 数组，如：[10, 23]"
            ),
        },
    ]


def parse_llm_cut_indices(text: str, block_len: int) -> list[int]:
    def normalize(values: Any) -> list[int]:
        if not isinstance(values, list):
            return []
        cuts = []
        for value in values:
            if isinstance(value, int) and 0 < value < block_len:
                cuts.append(value)
            elif isinstance(value, float) and value.is_integer():
                value_int = int(value)
                if 0 < value_int < block_len:
                    cuts.append(value_int)
        return sorted(set(cuts))

    text = text.strip()
    try:
        direct_cuts = normalize(json.loads(text))
        if direct_cuts:
            return direct_cuts
    except Exception:
        pass

    candidates = []
    stack = []
    for idx, char in enumerate(text):
        if char == "[":
            stack.append(idx)
        elif char == "]" and stack:
            start = stack.pop()
            candidates.append(text[start : idx + 1])

    for candidate in reversed(candidates):
        try:
            cuts = normalize(json.loads(candidate))
        except Exception:
            continue
        if cuts:
            return cuts
    return []


class BatchedDeepSeekRunner:
    def __init__(self, args: argparse.Namespace, log: Callable[[str], None]) -> None:
        from vllm import LLM, SamplingParams

        self.log = log
        self.prompt_batch_size = max(1, args.prompt_batch_size)
        log(
            "[INFO] init vLLM: "
            f"model={args.model_path}, tp={args.tensor_parallel_size}, "
            f"gpu_mem={args.gpu_memory_utilization}, max_model_len={args.max_model_len}"
        )
        self.llm = LLM(
            model=args.model_path,
            tensor_parallel_size=args.tensor_parallel_size,
            gpu_memory_utilization=args.gpu_memory_utilization,
            max_model_len=args.max_model_len,
            max_num_batched_tokens=args.max_num_batched_tokens,
            max_num_seqs=args.max_num_seqs,
            trust_remote_code=not args.disable_trust_remote_code,
            enable_chunked_prefill=not args.disable_chunked_prefill,
        )
        self.tokenizer = self.llm.get_tokenizer()
        self.sampling_params = SamplingParams(
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_new_tokens,
            repetition_penalty=args.repetition_penalty,
        )

    def build_prompt(self, messages: Sequence[dict[str, str]]) -> str:
        try:
            return self.tokenizer.apply_chat_template(
                list(messages),
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            return "\n\n".join(message.get("content", "") for message in messages)

    def generate(self, prompts: Sequence[str]) -> list[str]:
        results = []
        for start in range(0, len(prompts), self.prompt_batch_size):
            batch = list(prompts[start : start + self.prompt_batch_size])
            try:
                outputs = self.llm.generate(batch, self.sampling_params, use_tqdm=False)
            except Exception as exc:
                self.log(f"[WARN] DeepSeek batch failed for prompts {start}-{start + len(batch) - 1}: {exc}")
                results.extend([""] * len(batch))
                continue
            for output in outputs:
                results.append(output.outputs[0].text.strip() if output.outputs else "")
        return results


def assign_scene_index_to_segments(
    segs: list[dict[str, Any]],
    runner: BatchedDeepSeekRunner | None,
    fixed_t_gap: float | None,
    max_lines_per_block: int,
    short_audio_seconds: float,
    log: Callable[[str], None],
    source_name: str,
) -> tuple[float, int]:
    if not segs:
        log(f"[INFO] {source_name}: empty segments, skip scene split")
        return 0.0, 0

    audio_start = float(segs[0].get("start") or 0.0)
    audio_end = float(segs[-1].get("end") or segs[-1].get("start") or audio_start)
    audio_duration = max(0.0, audio_end - audio_start)
    if audio_duration < short_audio_seconds:
        for seg in segs:
            seg["scene_index"] = 0
        log(f"[INFO] {source_name}: short audio {audio_duration:.2f}s < {short_audio_seconds}s, single scene")
        return 0.0, 1

    if runner is None:
        raise ValueError("runner is required for audio longer than short-audio threshold")

    gaps = compute_gaps(segs)
    t_gap = float(fixed_t_gap) if fixed_t_gap is not None else (max(3.0, percentile(gaps, 95)) if gaps else 3.0)
    coarse_cuts = pick_cut_candidates_by_gap(segs, t_gap)
    coarse_blocks = split_by_indices(segs, coarse_cuts, max_chunk_size=max_lines_per_block)
    log(
        f"[INFO] {source_name}: duration={audio_duration:.2f}s, segs={len(segs)}, "
        f"t_gap={t_gap:.2f}, coarse_cuts={len(coarse_cuts)}, coarse_blocks={len(coarse_blocks)}"
    )

    block_infos = []
    offset = 0
    for block in coarse_blocks:
        if not block:
            continue
        block_start = float(block[0].get("start") or 0.0)
        rel_lines = [
            (float(seg.get("start") or 0.0) - block_start, idx, str(seg.get("text") or ""))
            for idx, seg in enumerate(block)
        ]
        block_infos.append(
            {
                "offset": offset,
                "block_len": len(block),
                "block_start": block_start,
                "prompt": runner.build_prompt(build_block_prompt(rel_lines, t_gap, block_start)),
            }
        )
        offset += len(block)

    outputs = runner.generate([info["prompt"] for info in block_infos]) if block_infos else []
    final_cuts = []
    for info, llm_output in zip(block_infos, outputs):
        llm_indices = parse_llm_cut_indices(llm_output, info["block_len"])
        if llm_indices:
            log(f"[INFO] {source_name}: block@{info['block_start']:.3f}s parsed_cuts={llm_indices}")
        elif not llm_output:
            log(f"[WARN] {source_name}: LLM returned empty output for block@{info['block_start']:.3f}s")
        else:
            preview = llm_output.replace("\n", " ").strip()
            log(f"[WARN] {source_name}: LLM output parsed to empty cuts raw={preview[:200]!r}")
        final_cuts.extend(info["offset"] + idx for idx in llm_indices)

    scenes = split_by_indices(segs, final_cuts)
    for scene_index, scene in enumerate(scenes):
        for seg in scene:
            seg["scene_index"] = scene_index
    return t_gap, len(scenes)


def main() -> None:
    args = parse_args()
    if args.cuda_visible_devices:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.cuda_visible_devices

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    log_path = args.log_path.resolve() if args.log_path else output_dir / "cut_debug.log"
    log = make_logger(log_path)

    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory not found: {input_dir}")

    log(
        "[INFO] start cut job: "
        f"host={socket.gethostname()}, pid={os.getpid()}, cwd={Path.cwd()}, "
        f"input_dir={input_dir}, output_dir={output_dir}, skip_existing={args.skip_existing}"
    )

    runner: BatchedDeepSeekRunner | None = None
    written = 0
    skipped = 0
    for json_path in iter_json_files(input_dir):
        try:
            data = load_json(json_path)
            out_path = output_path_for(json_path, data, output_dir)
            if args.skip_existing and out_path.exists():
                skipped += 1
                log(f"[INFO] skip existing output: src={json_path.name}, out={out_path.name}")
                continue

            segs = get_segments(data)
            audio_start = float(segs[0].get("start") or 0.0) if segs else 0.0
            audio_end = float(segs[-1].get("end") or segs[-1].get("start") or audio_start) if segs else 0.0
            audio_duration = max(0.0, audio_end - audio_start)
            if audio_duration >= args.short_audio_seconds and runner is None:
                runner = BatchedDeepSeekRunner(args, log)

            t_gap, num_scenes = assign_scene_index_to_segments(
                segs=segs,
                runner=runner,
                fixed_t_gap=args.fixed_t_gap,
                max_lines_per_block=args.max_lines_per_block,
                short_audio_seconds=args.short_audio_seconds,
                log=log,
                source_name=json_path.name,
            )
            dump_json(out_path, data)
            written += 1
            log(
                f"[OK] {json_path.name}: duration={audio_duration:.2f}s, "
                f"scenes={num_scenes}, t_gap={t_gap:.2f}, out={out_path.name}"
            )
        except Exception as exc:
            skipped += 1
            log(f"[WARN] skip file: {json_path} ({exc})")

    log(f"[DONE] written={written}, skipped={skipped}, out_dir={output_dir}")


if __name__ == "__main__":
    main()
