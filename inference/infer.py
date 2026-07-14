#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.machinery
import importlib.util
import os
import re
import sys
import tempfile
import types
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch

VEOMNI_ROOT = Path(__file__).resolve().parent
if str(VEOMNI_ROOT) not in sys.path:
    sys.path.insert(0, str(VEOMNI_ROOT))

SPARK_TTS_ROOT = VEOMNI_ROOT / "Spark-TTS"
if str(SPARK_TTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SPARK_TTS_ROOT))


DEFAULT_RUN_DIR = str(VEOMNI_ROOT / "models")
BEST_CHECKPOINT_PATH = str(VEOMNI_ROOT / "models" / "hf_ckpt")
DEFAULT_SPARK_MODEL_DIR = str(VEOMNI_ROOT / "models" / "spark_tts")
DEFAULT_OUTPUT_ROOT = str(VEOMNI_ROOT / "output")


def install_sklearn_stub() -> None:
    if "sklearn" in sys.modules:
        return

    sklearn_stub = types.ModuleType("sklearn")
    sklearn_stub.__spec__ = importlib.machinery.ModuleSpec("sklearn", loader=None)
    metrics_stub = types.ModuleType("sklearn.metrics")
    metrics_stub.__spec__ = importlib.machinery.ModuleSpec("sklearn.metrics", loader=None)

    def roc_curve(*_args, **_kwargs):
        raise RuntimeError("The lightweight sklearn stub does not implement roc_curve.")

    metrics_stub.roc_curve = roc_curve
    sklearn_stub.metrics = metrics_stub
    sys.modules["sklearn"] = sklearn_stub
    sys.modules["sklearn.metrics"] = metrics_stub


def load_merge_to_hf_pt():
    install_sklearn_stub()
    merge_path = VEOMNI_ROOT / "merge_dcp_to_hf.py"
    if not merge_path.is_file():
        raise FileNotFoundError(f"merge_dcp_to_hf.py not found: {merge_path}")

    spec = importlib.util.spec_from_file_location("veomni_merge_dcp_to_hf", merge_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load merge module from {merge_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.merge_to_hf_pt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="1.7B final inference with best parameters.")
    parser.add_argument("--run_dir", type=str, default=DEFAULT_RUN_DIR)
    parser.add_argument("--checkpoint_path", type=str, default=BEST_CHECKPOINT_PATH)
    parser.add_argument("--hf_model_dir", type=str, default="")
    parser.add_argument("--tokenizer_path", type=str, default="")
    parser.add_argument("--auto_convert_dcp", action=argparse.BooleanOptionalAction, default=True)

    parser.add_argument("--text", type=str, default="")
    parser.add_argument("--text_path", type=str, default="")
    parser.add_argument("--ref_audio_path", type=str, required=True)
    parser.add_argument("--history_audio_path", type=str, required=True)
    parser.add_argument("--output_root", type=str, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--save_wav_path", type=str, default="")
    parser.add_argument("--save_cot_path", type=str, default="")

    parser.add_argument("--spark_model_dir", type=str, default=DEFAULT_SPARK_MODEL_DIR)
    parser.add_argument("--global_prefix", type=str, default="bicodec_global")
    parser.add_argument("--semantic_prefix", type=str, default="bicodec_semantic")
    parser.add_argument("--global_prefix_len", type=int, default=32)
    parser.add_argument("--history_mode", choices=["full", "semantic", "full_first_then_semantic"], default="full")

    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--torch_dtype", choices=["bfloat16", "float16", "float32"], default="bfloat16")
    parser.add_argument("--attn_implementation", type=str, default="eager")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sample_rate", type=int, default=16000)

    parser.add_argument("--cot_max_new_tokens", type=int, default=800)
    parser.add_argument("--cot_min_new_tokens", type=int, default=32)
    parser.add_argument("--audio_max_new_tokens", type=int, default=1600)
    parser.add_argument("--audio_min_new_tokens", type=int, default=256)
    parser.add_argument("--do_sample", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--top_p", type=float, default=0.8)
    parser.add_argument("--repetition_penalty", type=float, default=1.0)
    parser.add_argument("--no_repeat_ngram_size", type=int, default=0)
    parser.add_argument("--max_semantic_tokens", type=int, default=0)

    parser.add_argument("--naturalness_score", type=float, default=4.0)
    parser.add_argument("--noise_score", type=float, default=4.5)
    parser.add_argument("--expressive_intensity", type=float, default=0.85)
    parser.add_argument("--global_source", choices=["generated", "ref"], default="ref")
    parser.add_argument("--cot_retries", type=int, default=4)
    parser.add_argument("--audio_retries", type=int, default=2)
    parser.add_argument("--edit_cot", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def resolve_device(device_str: str) -> torch.device:
    if not device_str.startswith("cuda"):
        return torch.device(device_str)
    if not torch.cuda.is_available():
        return torch.device("cpu")
    if device_str == "cuda":
        return torch.device("cuda")
    try:
        requested_index = int(device_str.split(":", 1)[1])
    except (IndexError, ValueError):
        return torch.device("cuda")
    visible_count = torch.cuda.device_count()
    if requested_index < visible_count:
        return torch.device(device_str)
    print(
        f"[warn] requested device {device_str} is not available in the current visible CUDA set "
        f"(count={visible_count}); falling back to cuda:0"
        , flush=True
    )
    return torch.device("cuda:0")


def resolve_run_dir(args: argparse.Namespace, checkpoint_path: Path) -> Path:
    if checkpoint_path.name == "hf_ckpt":
        return checkpoint_path.parent
    if args.checkpoint_path and not args.run_dir:
        if checkpoint_path.parent.name != "checkpoints":
            raise ValueError("--run_dir is required when checkpoint_path is not under <run_dir>/checkpoints/")
        return checkpoint_path.parent.parent
    if args.checkpoint_path and args.run_dir == DEFAULT_RUN_DIR and checkpoint_path.parent.name == "checkpoints":
        return checkpoint_path.parent.parent
    return Path(args.run_dir)


def set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def ensure_hf_model_dir(args: argparse.Namespace, checkpoint_path: Path) -> Path:
    if checkpoint_path.name == "hf_ckpt" and (checkpoint_path / "config.json").exists():
        return checkpoint_path
    hf_dir = Path(args.hf_model_dir) if args.hf_model_dir else checkpoint_path / "hf_ckpt"
    if (hf_dir / "config.json").exists():
        return hf_dir
    if not args.auto_convert_dcp:
        raise FileNotFoundError(f"HF model dir not found: {hf_dir}. Provide --hf_model_dir or enable --auto_convert_dcp.")
    model_assets_dir = Path(args.run_dir) / "model_assets"
    if not model_assets_dir.exists():
        raise FileNotFoundError(f"model_assets dir not found: {model_assets_dir}")
    merge_to_hf_pt = load_merge_to_hf_pt()
    os.makedirs(hf_dir, exist_ok=True)
    merge_to_hf_pt(load_dir=str(checkpoint_path), save_path=str(hf_dir), model_assets_dir=str(model_assets_dir))
    return hf_dir


def resolve_tokenizer_dir(args: argparse.Namespace, run_dir: Path, hf_dir: Path) -> Path:
    candidates = []
    if args.tokenizer_path:
        candidates.append(Path(args.tokenizer_path))
    candidates.extend([run_dir / "model_assets", hf_dir])
    for candidate in candidates:
        if (candidate / "tokenizer.json").exists() and (candidate / "tokenizer_config.json").exists():
            return candidate
    raise FileNotFoundError("Cannot find tokenizer dir. Checked: " + ", ".join(str(p) for p in candidates))


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Empty target text: {path}")
    return text


def resolve_target_text(args: argparse.Namespace) -> str:
    if args.text.strip():
        return args.text.strip()
    if args.text_path:
        return read_text(Path(args.text_path))
    raise ValueError("Either --text or --text_path is required.")


def flatten_long_tensor(x: torch.Tensor) -> list[int]:
    return [int(v) for v in torch.as_tensor(x).long().reshape(-1).tolist()]


def to_tokens(ids: list[int], prefix: str) -> str:
    return " ".join(f"<|{prefix}_{idx}|>" for idx in ids)


def remove_silence(audio: np.ndarray, threshold: float) -> np.ndarray:
    if audio.ndim == 1:
        energy = np.abs(audio)
    else:
        energy = np.max(np.abs(audio), axis=1)
    non_silent = np.where(energy > threshold)[0]
    if len(non_silent) == 0:
        return audio
    return audio[non_silent]


def maybe_trim_ref_audio(audio_path: Path) -> tuple[str, str | None]:
    audio, sample_rate = sf.read(str(audio_path))
    audio = np.asarray(audio)
    if audio.size == 0:
        return str(audio_path), None
    peak = float(np.max(np.abs(audio)))
    if peak <= 0.0:
        return str(audio_path), None
    trimmed = remove_silence(audio, threshold=max(peak * 0.01, 1e-4))
    if trimmed.shape == audio.shape:
        return str(audio_path), None
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()
    sf.write(tmp_path, trimmed, sample_rate)
    return tmp_path, tmp_path


def encode_audio_global(audio_tokenizer, audio_path: Path, global_prefix_len: int) -> list[int]:
    audio_for_global, tmp_path = maybe_trim_ref_audio(audio_path)
    try:
        global_ids, _ = audio_tokenizer.tokenize(audio_for_global)
        return flatten_long_tensor(global_ids)[:global_prefix_len]
    finally:
        if tmp_path is not None:
            Path(tmp_path).unlink(missing_ok=True)


def encode_audio_semantic(audio_tokenizer, audio_path: Path) -> list[int]:
    _, semantic_ids = audio_tokenizer.tokenize(str(audio_path))
    return flatten_long_tensor(semantic_ids)


def encode_audio_full(audio_tokenizer, audio_path: Path, global_prefix_len: int) -> tuple[list[int], list[int]]:
    global_ids, semantic_ids = audio_tokenizer.tokenize(str(audio_path))
    return flatten_long_tensor(global_ids)[:global_prefix_len], flatten_long_tensor(semantic_ids)


def build_history_tokens(args: argparse.Namespace, audio_tokenizer, history_paths: list[Path]) -> tuple[str, int, int]:
    if not history_paths:
        return "", 0, 0
    global_count = 0
    semantic_count = 0
    parts: list[str] = []
    for idx, history_path in enumerate(history_paths):
        use_full = args.history_mode == "full" or (args.history_mode == "full_first_then_semantic" and idx == 0)
        if use_full:
            global_ids, semantic_ids = encode_audio_full(audio_tokenizer, history_path, args.global_prefix_len)
            if global_ids:
                parts.append(to_tokens(global_ids, args.global_prefix))
                global_count += len(global_ids)
        else:
            semantic_ids = encode_audio_semantic(audio_tokenizer, history_path)
        if semantic_ids:
            parts.append(to_tokens(semantic_ids, args.semantic_prefix))
            semantic_count += len(semantic_ids)
    return " ".join(parts), global_count, semantic_count


def build_user_prompt(text: str, history_tokens: str, ref_tokens: str) -> str:
    return (
        "<bos>"
        "<task_start>COT-TTS<task_end>"
        "<history_start>"
        "<spk_his_start><spk_his_end>"
        f"<audio_his_start>{history_tokens}<audio_his_end>"
        "<history_end>"
        "<target_start>"
        f"<text_start>{text}<text_end>"
        "<spk_tar_start><spk_tar_end>"
        f"<audio_ref_start>{ref_tokens}<audio_ref_end>"
        "<target_end>"
        "<output_start>"
    )


def extract_between(text: str, start: str, end: str) -> str:
    start_idx = text.find(start)
    if start_idx < 0:
        return ""
    start_idx += len(start)
    end_idx = text.find(end, start_idx)
    if end_idx < 0:
        return text[start_idx:]
    return text[start_idx:end_idx]


def parse_audio_ids(text: str, global_prefix: str, semantic_prefix: str) -> tuple[list[int], list[int]]:
    global_ids = [int(x) for x in re.findall(rf"{re.escape(global_prefix)}_(\d+)", text)]
    semantic_ids = [int(x) for x in re.findall(rf"{re.escape(semantic_prefix)}_(\d+)", text)]
    return global_ids, semantic_ids


def resolve_stop_token_ids(tokenizer, extra_tokens: list[str]) -> list[int]:
    stop_ids: list[int] = []
    seen: set[int] = set()

    def _add(token_id) -> None:
        if token_id is None:
            return
        token_id = int(token_id)
        if token_id < 0 or token_id in seen:
            return
        seen.add(token_id)
        stop_ids.append(token_id)

    eos_token_id = tokenizer.eos_token_id
    if isinstance(eos_token_id, (list, tuple)):
        for token_id in eos_token_id:
            _add(token_id)
    else:
        _add(eos_token_id)

    for token in extra_tokens:
        token_ids = tokenizer.encode(token, add_special_tokens=False)
        if len(token_ids) == 1:
            _add(token_ids[0])
    return stop_ids


def generation_kwargs(
    tokenizer,
    *,
    max_new_tokens: int,
    min_new_tokens: int,
    do_sample: bool,
    temperature: float,
    top_p: float,
    repetition_penalty: float,
    no_repeat_ngram_size: int,
    stop_tokens: list[str],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "min_new_tokens": min_new_tokens,
        "do_sample": do_sample,
        "temperature": temperature,
        "top_p": top_p,
        "eos_token_id": resolve_stop_token_ids(tokenizer, stop_tokens),
        "pad_token_id": tokenizer.eos_token_id,
    }
    if repetition_penalty > 1.0:
        kwargs["repetition_penalty"] = repetition_penalty
    if no_repeat_ngram_size > 0:
        kwargs["no_repeat_ngram_size"] = no_repeat_ngram_size
    return kwargs


def build_input_ids(tokenizer, user_prompt: str, assistant_prefix: str, device: torch.device) -> torch.Tensor:
    input_ids = tokenizer.apply_chat_template(
        [{"role": "user", "content": user_prompt}],
        add_generation_prompt=True,
        return_tensors="pt",
    )
    if assistant_prefix:
        assistant_prefix_ids = tokenizer(assistant_prefix, add_special_tokens=False, return_tensors="pt")["input_ids"]
        input_ids = torch.cat([input_ids, assistant_prefix_ids], dim=1)
    return input_ids.to(device)


def generate_text(model, tokenizer, input_ids: torch.Tensor, **gen_kwargs) -> str:
    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            attention_mask=torch.ones_like(input_ids),
            **gen_kwargs,
        )
    return tokenizer.decode(output_ids[0, input_ids.shape[1] :], skip_special_tokens=False)


def sanitize_cot_text(cot_text: str) -> str:
    cot_text = cot_text.replace("<cot_start>", "").replace("<cot_end>", "")
    act_idx = cot_text.find("<Act>")
    if act_idx >= 0:
        cot_text = cot_text[act_idx:]
    return cot_text.strip()


def is_valid_cot_text(cot_text: str) -> bool:
    cot_text = sanitize_cot_text(cot_text)
    if not cot_text.startswith("<Act>:"):
        return False
    required_markers = ["<Scene>:", "<Motivation>:", "<Goal>:", "<Emotion>:", "[Summary]"]
    return all(marker in cot_text for marker in required_markers)


def extract_loudness_value(cot_text: str) -> str:
    match = re.search(r"<Loudness \| Expressive Intensity>:\s*([^|]+)\|\s*([^\n]+)", cot_text)
    if match:
        return match.group(1).strip()
    return "-30.000000dBFS"


def upsert_line(lines: list[str], prefix: str, new_line: str, before_prefix: str = "[Summary]") -> None:
    for idx, line in enumerate(lines):
        if line.startswith(prefix):
            lines[idx] = new_line
            return
    insert_idx = len(lines)
    for idx, line in enumerate(lines):
        if line.startswith(before_prefix):
            insert_idx = idx
            break
    lines.insert(insert_idx, new_line)


def apply_cot_controls(
    generated_cot: str,
    *,
    naturalness_score: float,
    noise_score: float,
    expressive_intensity: float,
) -> str:
    cot_text = sanitize_cot_text(generated_cot)
    lines = [line.rstrip() for line in cot_text.splitlines() if line.strip()]
    loudness_value = extract_loudness_value(cot_text)
    upsert_line(
        lines,
        "<Loudness | Expressive Intensity>:",
        f"<Loudness | Expressive Intensity>: {loudness_value} | {expressive_intensity:.6f}",
    )
    upsert_line(lines, "<Naturalness Score>:", f"<Naturalness Score>: {naturalness_score:.6f}")
    upsert_line(lines, "<Noise Score>:", f"<Noise Score>: {noise_score:.6f}")
    return "\n".join(lines).strip()


def is_strict_cot_text(cot_text: str) -> bool:
    cot_text = sanitize_cot_text(cot_text)
    if not is_valid_cot_text(cot_text):
        return False
    required_prefixes = [
        "<Act>:",
        "<Scene>:",
        "<Motivation>:",
        "<Goal>:",
        "<Emotion>:",
        "<Naturalness Score>:",
        "<Noise Score>:",
        "<Loudness | Expressive Intensity>:",
        "[Summary]",
    ]
    lines = [line.strip() for line in cot_text.splitlines() if line.strip()]
    return all(any(line.startswith(prefix) for line in lines) for prefix in required_prefixes)


def maybe_edit_cot(cot_text: str, cot_path: Path, edit_cot: bool) -> str:
    cot_path.parent.mkdir(parents=True, exist_ok=True)
    cot_path.write_text(cot_text + "\n", encoding="utf-8")
    if not edit_cot:
        return cot_text

    if not sys.stdin.isatty():
        edited_cot = sanitize_cot_text(cot_path.read_text(encoding="utf-8"))
        if not is_strict_cot_text(edited_cot):
            raise RuntimeError(f"Edited COT format is invalid: {cot_path}")
        return edited_cot

    while True:
        input(f"Edit COT at {cot_path}, save it, then press Enter to continue.")
        edited_cot = sanitize_cot_text(cot_path.read_text(encoding="utf-8"))
        if is_strict_cot_text(edited_cot):
            return edited_cot
        print("[warn] Edited COT format is invalid. Please fix it and press Enter again.", flush=True)


def generate_valid_cot(
    tokenizer,
    model,
    user_prompt: str,
    device: torch.device,
    args: argparse.Namespace,
) -> tuple[str, str]:
    last_generated = ""
    for _ in range(int(args.cot_retries)):
        input_ids = build_input_ids(tokenizer, user_prompt, "<cot_start>", device)
        cot_generation = generate_text(
            model,
            tokenizer,
            input_ids,
            **generation_kwargs(
                tokenizer,
                max_new_tokens=int(args.cot_max_new_tokens),
                min_new_tokens=int(args.cot_min_new_tokens),
                do_sample=bool(args.do_sample),
                temperature=float(args.temperature),
                top_p=float(args.top_p),
                repetition_penalty=float(args.repetition_penalty),
                no_repeat_ngram_size=int(args.no_repeat_ngram_size),
                stop_tokens=["<cot_end>", "<output_end>", "<eos>"],
            ),
        )
        last_generated = extract_between(cot_generation, "", "<cot_end>")
        if last_generated.strip() and is_valid_cot_text(last_generated):
            return cot_generation, sanitize_cot_text(last_generated)
    raise RuntimeError(f"Failed to generate valid COT after retries. Last COT: {last_generated}")


def generate_audio_tokens(
    tokenizer,
    model,
    user_prompt: str,
    controlled_cot: str,
    device: torch.device,
    args: argparse.Namespace,
) -> tuple[str, list[int], list[int]]:
    last_generation = ""
    for _ in range(int(args.audio_retries)):
        input_ids = build_input_ids(tokenizer, user_prompt, f"<cot_start>{controlled_cot}<cot_end><audio_tar_start>", device)
        audio_generation = generate_text(
            model,
            tokenizer,
            input_ids,
            **generation_kwargs(
                tokenizer,
                max_new_tokens=int(args.audio_max_new_tokens),
                min_new_tokens=int(args.audio_min_new_tokens),
                do_sample=bool(args.do_sample),
                temperature=float(args.temperature),
                top_p=float(args.top_p),
                repetition_penalty=float(args.repetition_penalty),
                no_repeat_ngram_size=int(args.no_repeat_ngram_size),
                stop_tokens=["<audio_tar_end>", "<output_end>", "<eos>"],
            ),
        )
        last_generation = audio_generation
        generated_global_ids, semantic_ids = parse_audio_ids(audio_generation, args.global_prefix, args.semantic_prefix)
        if int(args.max_semantic_tokens) > 0 and len(semantic_ids) > int(args.max_semantic_tokens):
            semantic_ids = semantic_ids[: int(args.max_semantic_tokens)]
        if semantic_ids:
            return audio_generation, generated_global_ids, semantic_ids
    raise RuntimeError(f"Failed to generate semantic audio tokens after retries. Last output: {last_generation}")


def pick_global_ids(args: argparse.Namespace, generated_global_ids: list[int], ref_global_ids: list[int]) -> tuple[list[int], str]:
    expected_len = len(ref_global_ids)
    if args.global_source != "generated":
        return ref_global_ids, "ref"
    if len(generated_global_ids) != expected_len:
        print(
            f"[fallback] generated global token count {len(generated_global_ids)} "
            f"!= expected {expected_len}, using ref global tokens"
            , flush=True
        )
        return ref_global_ids, "ref_fallback_bad_generated_length"
    return generated_global_ids, "generated"


def build_prompt_for_case(
    args: argparse.Namespace,
    history_path: Path,
    ref_path: Path,
    text: str,
    audio_tokenizer,
) -> tuple[str, str, list[int], int, int]:
    history_tokens, history_global_count, history_semantic_count = build_history_tokens(args, audio_tokenizer, [history_path])
    ref_global_ids = encode_audio_global(audio_tokenizer, ref_path, args.global_prefix_len)
    if not ref_global_ids:
        raise RuntimeError(f"Reference audio produced no global tokens: {ref_path}")
    user_prompt = build_user_prompt(text=text, history_tokens=history_tokens, ref_tokens=to_tokens(ref_global_ids, args.global_prefix))
    return user_prompt, text, ref_global_ids, history_global_count, history_semantic_count


def infer_one(args: argparse.Namespace, tokenizer, model, audio_tokenizer, device: torch.device) -> None:
    history_path = Path(args.history_audio_path)
    ref_path = Path(args.ref_audio_path)
    text = resolve_target_text(args)
    sample_name = Path(args.save_wav_path).stem if args.save_wav_path else ref_path.stem
    cot_path = Path(args.save_cot_path) if args.save_cot_path else Path(args.output_root) / f"{sample_name}.cot.txt"
    wav_path = Path(args.save_wav_path) if args.save_wav_path else Path(args.output_root) / f"{sample_name}.wav"
    if cot_path.exists() and wav_path.exists() and not args.overwrite:
        print(f"[skip] {sample_name}")
        return

    print(f"[run] {sample_name}")
    user_prompt, _text, ref_global_ids, _hg, _hs = build_prompt_for_case(args, history_path, ref_path, text, audio_tokenizer)
    _cot_generation, generated_cot = generate_valid_cot(tokenizer, model, user_prompt, device, args)
    controlled_cot = apply_cot_controls(
        generated_cot,
        naturalness_score=args.naturalness_score,
        noise_score=args.noise_score,
        expressive_intensity=args.expressive_intensity,
    )
    if not is_strict_cot_text(controlled_cot):
        raise RuntimeError("Controlled COT became invalid after applying controls.")

    cot_path.parent.mkdir(parents=True, exist_ok=True)
    controlled_cot = maybe_edit_cot(controlled_cot, cot_path, args.edit_cot)

    _audio_generation, generated_global_ids, semantic_ids = generate_audio_tokens(
        tokenizer,
        model,
        user_prompt,
        controlled_cot,
        device,
        args,
    )
    global_ids, _actual_global_source = pick_global_ids(args, generated_global_ids, ref_global_ids)
    wav = audio_tokenizer.detokenize(
        torch.tensor(global_ids, dtype=torch.long, device=device).unsqueeze(0),
        torch.tensor(semantic_ids, dtype=torch.long, device=device).unsqueeze(0),
    )
    wav = torch.as_tensor(wav).reshape(-1).detach().cpu().numpy()

    wav_path.parent.mkdir(parents=True, exist_ok=True)
    cot_path.write_text(controlled_cot + "\n", encoding="utf-8")
    sf.write(str(wav_path), wav, samplerate=args.sample_rate)
    print(f"[done] wav={wav_path} cot={cot_path}")


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    checkpoint_path = Path(args.checkpoint_path)
    run_dir = resolve_run_dir(args, checkpoint_path)
    args.run_dir = str(run_dir)

    device = resolve_device(args.device)
    if device.type == "cuda" and device.index is not None:
        torch.cuda.set_device(device)

    hf_dir = ensure_hf_model_dir(args, checkpoint_path)
    tokenizer_dir = resolve_tokenizer_dir(args, run_dir, hf_dir)
    install_sklearn_stub()

    from sparktts.models.audio_tokenizer import BiCodecTokenizer
    from veomni.models import build_foundation_model, build_tokenizer

    tokenizer = build_tokenizer(str(tokenizer_dir))
    model = build_foundation_model(
        config_path=str(hf_dir),
        weights_path=str(hf_dir),
        torch_dtype=args.torch_dtype,
        attn_implementation=args.attn_implementation,
    ).eval().to(device)
    audio_tokenizer = BiCodecTokenizer(args.spark_model_dir, device=device)

    infer_one(args, tokenizer, model, audio_tokenizer, device)


if __name__ == "__main__":
    main()
