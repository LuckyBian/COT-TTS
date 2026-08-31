#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import soundfile as sf
import torch


INFER_ROOT = Path(__file__).resolve().parent
SPARK_MODEL_DIR = INFER_ROOT / "models" / "Spark-TTS-0.5B"
VENDOR_DIR = INFER_ROOT / "vendor"
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

BEST_MODEL_SPECS = {
    "0p6": {
        "checkpoint_path": INFER_ROOT / "models" / "best_0p6",
        "hf_model_dir": INFER_ROOT / "models" / "best_0p6" / "hf_ckpt",
        "tokenizer_path": INFER_ROOT / "models" / "best_0p6" / "hf_ckpt",
        "temperature": 0.95,
        "top_p": 0.8,
        "audio_retries": 3,
    },
    "1p7": {
        "checkpoint_path": INFER_ROOT / "models" / "best_1p7",
        "hf_model_dir": INFER_ROOT / "models" / "best_1p7" / "hf_ckpt",
        "tokenizer_path": INFER_ROOT / "models" / "best_1p7" / "hf_ckpt",
        "temperature": 0.6,
        "top_p": 0.8,
        "audio_retries": 2,
    },
}


@dataclass
class InferResult:
    model_size: str
    checkpoint_path: str
    history_audio_path: str
    reference_audio_path: str
    target_text: str
    generated_cot_path: str | None = None
    edited_cot_path: str | None = None
    generated_wav_path: str | None = None
    run_log_path: str | None = None
    mode: str | None = None
    language: str | None = None
    command: list[str] | None = None


def model_spec(model_size: str) -> dict:
    if model_size not in BEST_MODEL_SPECS:
        raise KeyError(f"Unsupported model size: {model_size}")
    return BEST_MODEL_SPECS[model_size]


def _demo_infer_module():
    import highqual_cot_audio_edit_demo_infer as demo_infer  # type: ignore

    return demo_infer


def make_infer_args(
    *,
    history_mode: str,
    torch_dtype: str,
    attn_implementation: str,
    do_sample: bool,
    temperature: float,
    top_p: float,
    repetition_penalty: float,
    no_repeat_ngram_size: int,
    cot_max_new_tokens: int,
    cot_min_new_tokens: int,
    audio_max_new_tokens: int,
    audio_min_new_tokens: int,
    max_semantic_tokens: int,
    sample_rate: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        history_mode=history_mode,
        global_prefix="bicodec_global",
        semantic_prefix="bicodec_semantic",
        global_prefix_len=32,
        torch_dtype=torch_dtype,
        attn_implementation=attn_implementation,
        do_sample=do_sample,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        no_repeat_ngram_size=no_repeat_ngram_size,
        cot_max_new_tokens=cot_max_new_tokens,
        cot_min_new_tokens=cot_min_new_tokens,
        audio_max_new_tokens=audio_max_new_tokens,
        audio_min_new_tokens=audio_min_new_tokens,
        max_semantic_tokens=max_semantic_tokens,
        sample_rate=sample_rate,
    )


def normalize_audio_to_16k(input_path: Path, output_path: Path) -> Path:
    audio, sample_rate = sf.read(str(input_path))
    audio_np = np.asarray(audio)
    if audio_np.ndim == 1:
        audio_tensor = torch.from_numpy(audio_np).float().unsqueeze(0)
    else:
        audio_tensor = torch.from_numpy(audio_np.T).float()

    if sample_rate != 16000:
        import torchaudio.functional as F

        audio_tensor = F.resample(audio_tensor, sample_rate, 16000)

    audio_out = audio_tensor.squeeze(0).cpu().numpy() if audio_tensor.shape[0] == 1 else audio_tensor.T.cpu().numpy()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), audio_out, 16000)
    return output_path


def prepare_runtime_audio(history_audio_path: Path, reference_audio_path: Path) -> tuple[Path, Path, Path]:
    runtime_dir = Path(tempfile.mkdtemp(prefix="cot_tts_single_audio_", dir=str(INFER_ROOT)))
    history_16k = normalize_audio_to_16k(history_audio_path, runtime_dir / "history_16k.wav")
    reference_16k = normalize_audio_to_16k(reference_audio_path, runtime_dir / "reference_16k.wav")
    return runtime_dir, history_16k, reference_16k


def load_single_infer_runtime(
    *,
    model_size: str,
    device: str,
    torch_dtype: str,
    attn_implementation: str,
):
    spec = model_spec(model_size)
    demo_infer = _demo_infer_module()
    checkpoint_path = Path(spec["checkpoint_path"])
    hf_dir = Path(spec["hf_model_dir"])
    tokenizer_dir = Path(spec["tokenizer_path"])
    resolved_device = demo_infer.resolve_device(device)
    if resolved_device.type == "cuda" and resolved_device.index is not None:
        torch.cuda.set_device(resolved_device)

    demo_infer.install_sklearn_stub()
    from sparktts.models.audio_tokenizer import BiCodecTokenizer
    from veomni.models import build_foundation_model, build_tokenizer

    tokenizer = build_tokenizer(str(tokenizer_dir))
    model = build_foundation_model(
        config_path=str(hf_dir),
        weights_path=str(hf_dir),
        torch_dtype=torch_dtype,
        attn_implementation=attn_implementation,
    ).eval().to(resolved_device)
    audio_tokenizer = BiCodecTokenizer(str(SPARK_MODEL_DIR), device=resolved_device)
    return {
        "spec": spec,
        "checkpoint_path": checkpoint_path,
        "tokenizer": tokenizer,
        "model": model,
        "audio_tokenizer": audio_tokenizer,
        "device": resolved_device,
        "demo_infer": demo_infer,
    }


def sanitize_user_cot(cot_text: str) -> str:
    demo_infer = _demo_infer_module()
    return demo_infer.sanitize_cot_text(cot_text).strip()


def generate_cot(
    *,
    runtime: dict,
    infer_args: SimpleNamespace,
    history_audio_path: Path,
    reference_audio_path: Path,
    target_text: str,
) -> str:
    demo_infer = runtime["demo_infer"]
    audio_tokenizer = runtime["audio_tokenizer"]
    tokenizer = runtime["tokenizer"]
    model = runtime["model"]
    device = runtime["device"]

    history_tokens, _, _ = demo_infer.build_history_tokens(infer_args, audio_tokenizer, [history_audio_path])
    ref_global_ids = demo_infer.encode_audio_global(audio_tokenizer, reference_audio_path, infer_args.global_prefix_len)
    if not ref_global_ids:
        raise RuntimeError(f"Reference audio produced no global tokens: {reference_audio_path}")

    user_prompt = demo_infer.build_user_prompt(
        text=target_text,
        history_tokens=history_tokens,
        ref_tokens=demo_infer.to_tokens(ref_global_ids, infer_args.global_prefix),
    )
    cot_input_ids = demo_infer.build_input_ids(tokenizer, user_prompt, "<cot_start>", device)
    cot_gen_text = demo_infer.generate_text(
        model,
        tokenizer,
        cot_input_ids,
        **demo_infer.generation_kwargs(
            tokenizer,
            max_new_tokens=infer_args.cot_max_new_tokens,
            min_new_tokens=infer_args.cot_min_new_tokens,
            do_sample=infer_args.do_sample,
            temperature=infer_args.temperature,
            top_p=infer_args.top_p,
            repetition_penalty=infer_args.repetition_penalty,
            no_repeat_ngram_size=infer_args.no_repeat_ngram_size,
            stop_tokens=["<cot_end>", "<output_end>", "<eos>"],
        ),
    )
    cot_text = demo_infer.extract_between(cot_gen_text, "", "<cot_end>")
    cot_text = sanitize_user_cot(cot_text)
    if not cot_text:
        raise RuntimeError("Model generated empty COT text.")
    return cot_text


def generate_audio_from_cot(
    *,
    runtime: dict,
    infer_args: SimpleNamespace,
    history_audio_path: Path,
    reference_audio_path: Path,
    target_text: str,
    cot_text: str,
    output_wav_path: Path,
    global_source: str = "ref",
) -> Path:
    demo_infer = runtime["demo_infer"]
    audio_tokenizer = runtime["audio_tokenizer"]
    tokenizer = runtime["tokenizer"]
    model = runtime["model"]
    device = runtime["device"]

    history_tokens, _, _ = demo_infer.build_history_tokens(infer_args, audio_tokenizer, [history_audio_path])
    ref_global_ids = demo_infer.encode_audio_global(audio_tokenizer, reference_audio_path, infer_args.global_prefix_len)
    if not ref_global_ids:
        raise RuntimeError(f"Reference audio produced no global tokens: {reference_audio_path}")

    user_prompt = demo_infer.build_user_prompt(
        text=target_text,
        history_tokens=history_tokens,
        ref_tokens=demo_infer.to_tokens(ref_global_ids, infer_args.global_prefix),
    )
    audio_input_ids = demo_infer.build_input_ids(
        tokenizer,
        user_prompt,
        f"<cot_start>{sanitize_user_cot(cot_text)}<cot_end><audio_tar_start>",
        device,
    )
    audio_gen_text = demo_infer.generate_text(
        model,
        tokenizer,
        audio_input_ids,
        **demo_infer.generation_kwargs(
            tokenizer,
            max_new_tokens=infer_args.audio_max_new_tokens,
            min_new_tokens=infer_args.audio_min_new_tokens,
            do_sample=infer_args.do_sample,
            temperature=infer_args.temperature,
            top_p=infer_args.top_p,
            repetition_penalty=infer_args.repetition_penalty,
            no_repeat_ngram_size=infer_args.no_repeat_ngram_size,
            stop_tokens=["<audio_tar_end>", "<output_end>", "<eos>"],
        ),
    )
    generated_global_ids, semantic_ids = demo_infer.parse_audio_ids(
        audio_gen_text,
        infer_args.global_prefix,
        infer_args.semantic_prefix,
    )
    if infer_args.max_semantic_tokens > 0 and len(semantic_ids) > infer_args.max_semantic_tokens:
        semantic_ids = semantic_ids[: infer_args.max_semantic_tokens]
    if not semantic_ids:
        raise RuntimeError("Model generated no semantic audio tokens.")

    if global_source == "generated" and generated_global_ids:
        global_ids = generated_global_ids
    else:
        global_ids = ref_global_ids

    wav = audio_tokenizer.detokenize(
        torch.tensor(global_ids, dtype=torch.long, device=device).unsqueeze(0),
        torch.tensor(semantic_ids, dtype=torch.long, device=device).unsqueeze(0),
    )
    wav = torch.as_tensor(wav).reshape(-1).detach().cpu().numpy()
    output_wav_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_wav_path), wav, samplerate=infer_args.sample_rate)
    return output_wav_path


def read_target_text(text: str, text_file: str) -> str:
    if text.strip():
        return text.strip()
    if text_file:
        value = Path(text_file).read_text(encoding="utf-8").strip()
        if value:
            return value
    raise ValueError("Target text is empty. Provide --text or --text-file.")


def write_result_manifest(path: Path, result: InferResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")


def write_failure_artifacts(
    output_dir: Path,
    *,
    model_size: str,
    checkpoint_path: str,
    history_audio_path: str,
    reference_audio_path: str,
    target_text: str,
    error: Exception,
    stage: str,
    manifest_name: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "error.txt").write_text(f"stage={stage}\nerror={error}\n", encoding="utf-8")
    result = InferResult(
        model_size=model_size,
        checkpoint_path=checkpoint_path,
        history_audio_path=history_audio_path,
        reference_audio_path=reference_audio_path,
        target_text=target_text,
        mode="failed",
    )
    write_result_manifest(output_dir / manifest_name, result)
