#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import soundfile as sf
import torch

from generation_protocol import (
    ProtocolError,
    generate_analysis,
    generated_tail,
    speech_context,
)


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
        "temperature": 0.95,
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
    under_generated_tokens: int | None = None
    under_used_in_speech_context: bool | None = None


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
    under_max_new_tokens: int,
    under_min_new_tokens: int,
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
        under_max_new_tokens=under_max_new_tokens,
        under_min_new_tokens=under_min_new_tokens,
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


def generate_ids(runtime: dict, infer_args: SimpleNamespace, prefix: list[int], phase: str) -> list[int]:
    demo_infer = runtime["demo_infer"]
    end_marker = {"under": "<under_end>", "cot": "<cot_end>", "audio": "<audio_tar_end>"}[phase]
    kwargs = demo_infer.generation_kwargs(
        runtime["tokenizer"],
        max_new_tokens=getattr(infer_args, f"{phase}_max_new_tokens"),
        min_new_tokens=getattr(infer_args, f"{phase}_min_new_tokens"),
        do_sample=infer_args.do_sample,
        temperature=infer_args.temperature,
        top_p=infer_args.top_p,
        repetition_penalty=infer_args.repetition_penalty,
        no_repeat_ngram_size=infer_args.no_repeat_ngram_size,
        stop_tokens=[end_marker, "<output_end>", "<eos>"],
    )
    max_positions = getattr(runtime["model"].config, "max_position_embeddings", None)
    if max_positions and len(prefix) + kwargs["max_new_tokens"] > max_positions:
        raise ProtocolError(f"{phase}: input would exceed the model context length")
    inputs = torch.tensor([prefix], dtype=torch.long, device=runtime["device"])
    with torch.inference_mode():
        output = runtime["model"].generate(
            input_ids=inputs, attention_mask=torch.ones_like(inputs), **kwargs,
        )
    return output[0].detach().cpu().tolist()


def generate_conditioning(
    *,
    runtime: dict,
    infer_args: SimpleNamespace,
    history_audio_path: Path,
    reference_audio_path: Path,
    target_text: str,
) -> dict:
    demo_infer = runtime["demo_infer"]
    audio_tokenizer = runtime["audio_tokenizer"]
    tokenizer = runtime["tokenizer"]
    device = runtime["device"]

    history_tokens, _, _ = demo_infer.build_history_tokens(infer_args, audio_tokenizer, [history_audio_path])
    ref_global_ids = demo_infer.encode_audio_global(audio_tokenizer, reference_audio_path, infer_args.global_prefix_len)
    if len(ref_global_ids) != infer_args.global_prefix_len:
        raise RuntimeError(f"Reference audio must produce {infer_args.global_prefix_len} global tokens")

    user_prompt = demo_infer.build_user_prompt(
        text=target_text,
        history_tokens=history_tokens,
        ref_tokens=demo_infer.to_tokens(ref_global_ids, infer_args.global_prefix),
    )
    prompt_ids = demo_infer.build_input_ids(tokenizer, user_prompt, "", device)[0].detach().cpu().tolist()
    encode = lambda text: tokenizer.encode(text, add_special_tokens=False)
    analysis = generate_analysis(
        prompt_ids,
        lambda prefix, phase: generate_ids(runtime, infer_args, prefix, phase),
        encode,
        lambda ids: tokenizer.decode(ids, skip_special_tokens=False),
    )
    analysis["reference_global_ids"] = ref_global_ids
    return analysis


def generate_audio_from_cot(
    *,
    runtime: dict,
    infer_args: SimpleNamespace,
    analysis: dict,
    output_wav_path: Path,
    global_source: str = "ref",
) -> Path:
    demo_infer = runtime["demo_infer"]
    audio_tokenizer = runtime["audio_tokenizer"]
    tokenizer = runtime["tokenizer"]
    device = runtime["device"]
    encode = lambda text: tokenizer.encode(text, add_special_tokens=False)
    prefix = speech_context(analysis, encode)
    audio_ids = generated_tail(prefix, generate_ids(runtime, infer_args, prefix, "audio"), "audio")
    stop_ids = demo_infer.resolve_stop_token_ids(tokenizer, ["<audio_tar_end>", "<output_end>", "<eos>"])
    if audio_ids[-1] not in stop_ids:
        raise ProtocolError("audio: reached the token limit without a normal end token")
    audio_gen_text = tokenizer.decode(audio_ids, skip_special_tokens=False)
    generated_global_ids, semantic_ids = demo_infer.parse_audio_ids(
        audio_gen_text, infer_args.global_prefix, infer_args.semantic_prefix,
    )
    if infer_args.max_semantic_tokens > 0 and len(semantic_ids) > infer_args.max_semantic_tokens:
        semantic_ids = semantic_ids[: infer_args.max_semantic_tokens]
    if not semantic_ids:
        raise RuntimeError("Model generated no semantic audio tokens.")

    if global_source == "generated" and generated_global_ids:
        global_ids = generated_global_ids
    else:
        global_ids = analysis["reference_global_ids"]

    wav = audio_tokenizer.detokenize(
        torch.tensor(global_ids, dtype=torch.long, device=device).unsqueeze(0),
        torch.tensor(semantic_ids, dtype=torch.long, device=device).unsqueeze(0),
    )
    wav = torch.as_tensor(wav).reshape(-1).detach().cpu().numpy()
    if wav.size == 0 or not np.isfinite(wav).all():
        raise RuntimeError("Audio decoder returned an empty or non-finite waveform")
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
