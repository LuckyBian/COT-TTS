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

VENDOR_ROOT = Path(__file__).resolve().parent
if str(VENDOR_ROOT) not in sys.path:
    sys.path.insert(0, str(VENDOR_ROOT))


DEFAULT_RUN_DIR = str(VENDOR_ROOT.parent / "models" / "best_1p7")
DEFAULT_SPARK_MODEL_DIR = str(VENDOR_ROOT.parent / "models" / "Spark-TTS-0.5B")
DEFAULT_AUDIO_DIR = str(VENDOR_ROOT.parent / "demo")
DEFAULT_TEXT_DIR = str(VENDOR_ROOT.parent / "demo")
DEFAULT_OUTPUT_DIR = str(VENDOR_ROOT.parent / "outputs_normal")
AUDIO_SUFFIXES = (".wav", ".mp3", ".flac", ".m4a", ".ogg")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch COT-TTS demo inference with editable COT and audio-only continuation."
    )
    parser.add_argument("--run_dir", type=str, default=DEFAULT_RUN_DIR, help="Run dir with checkpoints/ and model_assets/.")
    parser.add_argument("--checkpoint_path", type=str, default="", help="Checkpoint dir. Empty means latest under run_dir/checkpoints.")
    parser.add_argument("--hf_model_dir", type=str, default="", help="HF dir. Empty means <checkpoint_path>/hf_ckpt.")
    parser.add_argument("--tokenizer_path", type=str, default="", help="Tokenizer dir. Empty means auto resolve.")
    parser.add_argument("--auto_convert_dcp", action=argparse.BooleanOptionalAction, default=True)

    parser.add_argument("--audio_dir", type=str, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--text_dir", type=str, default=DEFAULT_TEXT_DIR)
    parser.add_argument("--output_dir", type=str, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--demo_ids", nargs="*", type=int, default=list(range(1, 12)))
    parser.add_argument(
        "--history_glob",
        type=str,
        default="",
        help=(
            "Optional history glob template relative to audio_dir, e.g. 'case{id}/his*.wav' or 'his{id}_*.wav'. "
            "Default auto-detects his{id}.wav, his{id}_*.wav, and his{id}/* audio files."
        ),
    )
    parser.add_argument("--ref_template", type=str, default="ref{id}.wav", help="Reference audio template relative to audio_dir.")
    parser.add_argument("--text_template", type=str, default="tar{id}.txt", help="Target text template relative to text_dir.")
    parser.add_argument(
        "--history_mode",
        choices=["full", "semantic", "full_first_then_semantic"],
        default="full",
        help="How to put history audio into <audio_his_start>. full means global+semantic for every history file.",
    )

    parser.add_argument("--spark_model_dir", type=str, default=DEFAULT_SPARK_MODEL_DIR)
    parser.add_argument("--global_prefix", type=str, default="bicodec_global")
    parser.add_argument("--semantic_prefix", type=str, default="bicodec_semantic")
    parser.add_argument("--global_prefix_len", type=int, default=32)

    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--torch_dtype", choices=["bfloat16", "float16", "float32"], default="bfloat16")
    parser.add_argument("--attn_implementation", type=str, default="flash_attention_2")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sample_rate", type=int, default=16000)

    parser.add_argument("--cot_max_new_tokens", type=int, default=512)
    parser.add_argument("--cot_min_new_tokens", type=int, default=32)
    parser.add_argument("--audio_max_new_tokens", type=int, default=1600)
    parser.add_argument("--audio_min_new_tokens", type=int, default=256)
    parser.add_argument("--do_sample", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--top_p", type=float, default=0.8)
    parser.add_argument("--repetition_penalty", type=float, default=1.0)
    parser.add_argument("--no_repeat_ngram_size", type=int, default=0)

    parser.add_argument("--max_semantic_tokens", type=int, default=0)
    parser.add_argument("--use_ref_global_tokens", action="store_true")
    parser.add_argument("--skip_edit", action="store_true", help="Skip manual editing and reuse the generated COT.")
    return parser.parse_args()


def resolve_device(device_str: str) -> torch.device:
    if device_str.startswith("cuda") and not torch.cuda.is_available():
        return torch.device("cpu")
    return torch.device(device_str)


def resolve_run_dir(args: argparse.Namespace, checkpoint_path: Path) -> Path:
    if args.checkpoint_path and not args.run_dir:
        if checkpoint_path.parent.name != "checkpoints":
            raise ValueError("--run_dir is required when checkpoint_path is not under <run_dir>/checkpoints/")
        return checkpoint_path.parent.parent
    if args.checkpoint_path and args.run_dir == DEFAULT_RUN_DIR:
        if checkpoint_path.parent.name == "checkpoints":
            return checkpoint_path.parent.parent
    return Path(args.run_dir)


def set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def find_latest_checkpoint(run_dir: Path) -> Path:
    ckpt_root = run_dir / "checkpoints"
    if not ckpt_root.exists():
        raise FileNotFoundError(f"checkpoints dir not found: {ckpt_root}")

    cands: list[tuple[int, Path]] = []
    for path in ckpt_root.iterdir():
        if not path.is_dir():
            continue
        match = re.match(r"global_step_(\d+)$", path.name)
        if match and (path / ".metadata").exists():
            cands.append((int(match.group(1)), path))

    if not cands:
        raise FileNotFoundError(f"No complete global_step_* checkpoint under {ckpt_root}")
    cands.sort(key=lambda item: item[0])
    return cands[-1][1]


def ensure_hf_model_dir(args: argparse.Namespace, checkpoint_path: Path) -> Path:
    hf_dir = Path(args.hf_model_dir) if args.hf_model_dir else checkpoint_path / "hf_ckpt"
    if (hf_dir / "config.json").exists():
        return hf_dir

    if not args.auto_convert_dcp:
        raise FileNotFoundError(
            f"HF model dir not found: {hf_dir}. Provide --hf_model_dir or enable --auto_convert_dcp."
        )

    model_assets_dir = Path(args.run_dir) / "model_assets"
    if not model_assets_dir.exists():
        raise FileNotFoundError(f"model_assets dir not found: {model_assets_dir}")

    merge_to_hf_pt = load_merge_to_hf_pt()

    os.makedirs(hf_dir, exist_ok=True)
    merge_to_hf_pt(load_dir=str(checkpoint_path), save_path=str(hf_dir), model_assets_dir=str(model_assets_dir))
    return hf_dir


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
    merge_path = VEOMNI_ROOT / "scripts" / "merge_dcp_to_hf.py"
    if not merge_path.is_file():
        raise FileNotFoundError(f"merge_dcp_to_hf.py not found: {merge_path}")

    spec = importlib.util.spec_from_file_location("veomni_merge_dcp_to_hf", merge_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load merge module from {merge_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.merge_to_hf_pt


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


def encode_audio_global(audio_tokenizer: BiCodecTokenizer, audio_path: Path, global_prefix_len: int) -> list[int]:
    audio_for_global, tmp_path = maybe_trim_ref_audio(audio_path)
    try:
        global_ids, _ = audio_tokenizer.tokenize(audio_for_global)
        return flatten_long_tensor(global_ids)[:global_prefix_len]
    finally:
        if tmp_path is not None:
            Path(tmp_path).unlink(missing_ok=True)


def encode_audio_semantic(audio_tokenizer: BiCodecTokenizer, audio_path: Path) -> list[int]:
    _, semantic_ids = audio_tokenizer.tokenize(str(audio_path))
    return flatten_long_tensor(semantic_ids)


def encode_audio_full(
    audio_tokenizer: BiCodecTokenizer,
    audio_path: Path,
    global_prefix_len: int,
) -> tuple[list[int], list[int]]:
    global_ids, semantic_ids = audio_tokenizer.tokenize(str(audio_path))
    return flatten_long_tensor(global_ids)[:global_prefix_len], flatten_long_tensor(semantic_ids)


def format_template(template: str, demo_id: int) -> str:
    return template.format(id=demo_id, demo_id=demo_id, n=demo_id)


def natural_key(path: Path) -> list[Any]:
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part for part in parts]


def audio_files_under(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    files = [item for item in path.iterdir() if item.is_file() and item.suffix.lower() in AUDIO_SUFFIXES]
    return sorted(files, key=natural_key)


def resolve_history_paths(args: argparse.Namespace, demo_id: int) -> list[Path]:
    audio_dir = Path(args.audio_dir)
    if args.history_glob:
        paths = [p for p in audio_dir.glob(format_template(args.history_glob, demo_id)) if p.is_file()]
        return sorted(paths, key=natural_key)

    direct_matches = []
    for suffix in AUDIO_SUFFIXES:
        path = audio_dir / f"his{demo_id}{suffix}"
        if path.exists():
            direct_matches.append(path)
    if direct_matches:
        return sorted(direct_matches, key=natural_key)

    glob_matches = [p for p in audio_dir.glob(f"his{demo_id}_*") if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES]
    if glob_matches:
        return sorted(glob_matches, key=natural_key)

    return audio_files_under(audio_dir / f"his{demo_id}")


def resolve_ref_path(args: argparse.Namespace, demo_id: int) -> Path:
    path = Path(args.audio_dir) / format_template(args.ref_template, demo_id)
    if path.exists():
        return path
    raise FileNotFoundError(path)


def resolve_text_path(args: argparse.Namespace, demo_id: int) -> Path:
    path = Path(args.text_dir) / format_template(args.text_template, demo_id)
    if path.exists():
        return path
    raise FileNotFoundError(path)


def build_history_tokens(
    args: argparse.Namespace,
    audio_tokenizer: BiCodecTokenizer,
    history_paths: list[Path],
) -> tuple[str, int, int]:
    if not history_paths:
        return "", 0, 0

    global_count = 0
    semantic_count = 0
    parts: list[str] = []
    for idx, history_path in enumerate(history_paths):
        if args.history_mode == "full" or (args.history_mode == "full_first_then_semantic" and idx == 0):
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
        assistant_prefix_ids = tokenizer(
            assistant_prefix,
            add_special_tokens=False,
            return_tensors="pt",
        )["input_ids"]
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

    required_markers = [
        "<Scene>:",
        "<Motivation>:",
        "<Goal>:",
        "<Emotion>:",
        "[Summary]",
    ]
    return all(marker in cot_text for marker in required_markers)


def get_edited_cot(generated_cot: str, cot_path: Path, skip_edit: bool) -> str | None:
    generated_cot = sanitize_cot_text(generated_cot)
    if not is_valid_cot_text(generated_cot):
        print("[WARN] Generated COT format is invalid. Regenerating current COT...")
        return None

    cot_path.parent.mkdir(parents=True, exist_ok=True)
    cot_path.write_text(generated_cot + "\n", encoding="utf-8")
    initial_mtime_ns = cot_path.stat().st_mtime_ns

    print(generated_cot)

    if skip_edit:
        return generated_cot

    if not sys.stdin.isatty():
        edited_cot = sanitize_cot_text(cot_path.read_text(encoding="utf-8"))
        if not is_valid_cot_text(edited_cot):
            raise RuntimeError(f"Edited COT format is invalid: {cot_path}")
        return edited_cot

    command = input(
        f"Edit {cot_path.name}, save it, then press Enter to continue; type 's' to keep current text: "
    ).strip().lower()
    if command == "s":
        return generated_cot

    current_mtime_ns = cot_path.stat().st_mtime_ns
    if current_mtime_ns == initial_mtime_ns:
        print("[WARN] The expected cot file was not modified. Regenerating current COT...")
        return None

    edited_cot = sanitize_cot_text(cot_path.read_text(encoding="utf-8"))
    if not is_valid_cot_text(edited_cot):
        print("[WARN] Edited COT format is invalid. Regenerating current COT...")
        return None
    return edited_cot


def infer_one(
    args: argparse.Namespace,
    demo_id: int,
    tokenizer,
    model,
    audio_tokenizer: BiCodecTokenizer,
    device: torch.device,
    out_dir: Path,
) -> None:
    history_paths = resolve_history_paths(args, demo_id)
    ref_path = resolve_ref_path(args, demo_id)
    text_path = resolve_text_path(args, demo_id)
    if not history_paths:
        raise FileNotFoundError(f"No history audio found for demo {demo_id} under {args.audio_dir}")

    text = read_text(text_path)
    history_tokens, _, _ = build_history_tokens(args, audio_tokenizer, history_paths)
    ref_global_ids = encode_audio_global(audio_tokenizer, ref_path, args.global_prefix_len)
    if not ref_global_ids:
        raise RuntimeError(f"Reference audio produced no global tokens: {ref_path}")

    user_prompt = build_user_prompt(
        text=text,
        history_tokens=history_tokens,
        ref_tokens=to_tokens(ref_global_ids, args.global_prefix),
    )

    demo_prefix = out_dir / f"demo{demo_id:02d}"
    cot_path = demo_prefix.with_suffix(".cot.txt")
    edited_cot: str | None = None
    while edited_cot is None:
        cot_input_ids = build_input_ids(tokenizer, user_prompt, "<cot_start>", device)
        cot_gen_text = generate_text(
            model,
            tokenizer,
            cot_input_ids,
            **generation_kwargs(
                tokenizer,
                max_new_tokens=args.cot_max_new_tokens,
                min_new_tokens=args.cot_min_new_tokens,
                do_sample=args.do_sample,
                temperature=args.temperature,
                top_p=args.top_p,
                repetition_penalty=args.repetition_penalty,
                no_repeat_ngram_size=args.no_repeat_ngram_size,
                stop_tokens=["<cot_end>", "<output_end>", "<eos>"],
            ),
        )
        generated_cot = extract_between(cot_gen_text, "", "<cot_end>")
        if not generated_cot.strip():
            raise RuntimeError(f"Demo {demo_id}: no COT text generated before <cot_end>.")
        edited_cot = get_edited_cot(generated_cot, cot_path, args.skip_edit)

    audio_input_ids = build_input_ids(
        tokenizer,
        user_prompt,
        f"<cot_start>{edited_cot}<cot_end><audio_tar_start>",
        device,
    )
    audio_gen_text = generate_text(
        model,
        tokenizer,
        audio_input_ids,
        **generation_kwargs(
            tokenizer,
            max_new_tokens=args.audio_max_new_tokens,
            min_new_tokens=args.audio_min_new_tokens,
            do_sample=args.do_sample,
            temperature=args.temperature,
            top_p=args.top_p,
            repetition_penalty=args.repetition_penalty,
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            stop_tokens=["<audio_tar_end>", "<output_end>", "<eos>"],
        ),
    )

    generated_global_ids, semantic_ids = parse_audio_ids(audio_gen_text, args.global_prefix, args.semantic_prefix)
    if args.max_semantic_tokens > 0 and len(semantic_ids) > args.max_semantic_tokens:
        semantic_ids = semantic_ids[: args.max_semantic_tokens]
    if not semantic_ids:
        raise RuntimeError(f"Demo {demo_id}: no semantic audio tokens found in stage-2 generation.")

    if args.use_ref_global_tokens or not generated_global_ids:
        global_ids = ref_global_ids
    else:
        global_ids = generated_global_ids

    wav = audio_tokenizer.detokenize(
        torch.tensor(global_ids, dtype=torch.long, device=device).unsqueeze(0),
        torch.tensor(semantic_ids, dtype=torch.long, device=device).unsqueeze(0),
    )
    wav = torch.as_tensor(wav).reshape(-1).detach().cpu().numpy()

    wav_path = demo_prefix.with_suffix(".wav")
    sf.write(str(wav_path), wav, samplerate=args.sample_rate)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    checkpoint_path = Path(args.checkpoint_path) if args.checkpoint_path else Path()
    run_dir = resolve_run_dir(args, checkpoint_path) if args.checkpoint_path else Path(args.run_dir)
    args.run_dir = str(run_dir)
    if not args.checkpoint_path:
        checkpoint_path = find_latest_checkpoint(run_dir)
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

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for demo_id in args.demo_ids:
        infer_one(args, demo_id, tokenizer, model, audio_tokenizer, device, out_dir)


if __name__ == "__main__":
    main()
