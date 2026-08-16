#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import soundfile as sf
import torch


INFER_ROOT = Path(__file__).resolve().parent
REPO_ROOT = INFER_ROOT.parent.parent
VEOMNI_ENV_PYTHON = Path("/aifs4su/weizhenbian/envs/veomni/bin/python")
SPARK_MODEL_DIR = INFER_ROOT / "models" / "Spark-TTS-0.5B"
FINAL_INFER_NEW_DIR = REPO_ROOT / "cot-tts-eval" / "final-infer-new"
VENDOR_DIR = INFER_ROOT / "vendor"
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

BEST_MODEL_SPECS = {
    "0p6": {
        "checkpoint_path": INFER_ROOT / "models" / "best_0p6",
        "hf_model_dir": INFER_ROOT / "models" / "best_0p6" / "hf_ckpt",
        "tokenizer_path": INFER_ROOT / "models" / "best_0p6" / "hf_ckpt",
        "family": "0p6",
        "tag": "0p6_single_best",
        "normal_script": REPO_ROOT / "VeOmni" / "final-infer" / "highqual_cot_audio_best_infer_0p6.py",
        "temperature": 0.95,
        "top_p": 0.8,
        "audio_retries": 3,
    },
    "1p7": {
        "checkpoint_path": INFER_ROOT / "models" / "best_1p7",
        "hf_model_dir": INFER_ROOT / "models" / "best_1p7" / "hf_ckpt",
        "tokenizer_path": INFER_ROOT / "models" / "best_1p7" / "hf_ckpt",
        "family": "1p7",
        "tag": "1p7_single_best",
        "normal_script": REPO_ROOT / "VeOmni" / "final-infer" / "highqual_cot_audio_best_infer.py",
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


def build_single_case_dataset(
    *,
    dataset_root: Path,
    language: str,
    sample_id: str,
    history_audio_path: Path,
    reference_audio_path: Path,
    target_text: str,
    cot_text: str | None = None,
) -> dict[str, Path]:
    lang_root = dataset_root / language
    his_dir = lang_root / "his_audio_denoise"
    ref_dir = lang_root / "ref_audio"
    text_dir = lang_root / "target_text_qwen"
    cot_dir = lang_root / "cot"
    for path in (his_dir, ref_dir, text_dir):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(history_audio_path, his_dir / f"{sample_id}{history_audio_path.suffix or '.wav'}")
    shutil.copy2(reference_audio_path, ref_dir / f"{sample_id}{reference_audio_path.suffix or '.wav'}")

    history_dst = his_dir / f"{sample_id}.wav"
    ref_dst = ref_dir / f"{sample_id}.wav"
    if history_dst.name != f"{sample_id}{history_audio_path.suffix or '.wav'}":
        shutil.copy2(history_audio_path, history_dst)
    if ref_dst.name != f"{sample_id}{reference_audio_path.suffix or '.wav'}":
        shutil.copy2(reference_audio_path, ref_dst)
    text_path = text_dir / f"{sample_id}.txt"
    text_path.write_text(target_text.strip() + "\n", encoding="utf-8")
    cot_path = None
    if cot_text is not None:
        cot_dir.mkdir(parents=True, exist_ok=True)
        cot_path = cot_dir / f"{sample_id}.txt"
        cot_path.write_text(cot_text.strip() + "\n", encoding="utf-8")
    return {
        "lang_root": lang_root,
        "history_path": history_dst,
        "reference_path": ref_dst,
        "text_path": text_path,
        "cot_path": cot_path,
    }


def visible_device_env(device: str) -> tuple[dict[str, str], str]:
    env = os.environ.copy()
    env.setdefault("TOKENIZERS_PARALLELISM", "false")
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    if device.startswith("cuda:"):
        index = device.split(":", 1)[1]
        env["CUDA_VISIBLE_DEVICES"] = index
        return env, "cuda:0"
    return env, device


def write_model_spec_json(*, model_size: str, path: Path) -> list[dict[str, str | int]]:
    spec = model_spec(model_size)
    payload = [
        {
            "family": str(spec["family"]),
            "run_name": "single_infer",
            "tag": str(spec["tag"]),
            "checkpoint_path": str(spec["checkpoint_path"]),
            "infer_script": str(spec["normal_script"]),
            "workers_per_gpu": 1,
        }
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def run_formal_infer(
    *,
    model_size: str,
    mode: str,
    data_root: Path,
    output_root: Path,
    language: str,
    sample_id: str | None = None,
    device: str,
    history_mode: str,
    torch_dtype: str,
    attn_implementation: str,
    temperature: float,
    top_p: float,
    cot_max_new_tokens: int | None,
    audio_max_new_tokens: int,
    cot_min_new_tokens: int | None = None,
    audio_min_new_tokens: int = 256,
    do_sample: bool = True,
    repetition_penalty: float = 1.0,
    no_repeat_ngram_size: int = 0,
    cot_retries: int | None = None,
    audio_retries: int | None = None,
    max_semantic_tokens: int = 0,
    global_source: str = "ref",
    sample_rate: int = 16000,
    overwrite: bool = True,
    run_log_path: Path | None = None,
) -> list[str]:
    spec = model_spec(model_size)
    env, _ = visible_device_env(device)
    if mode == "normal":
        model_specs_json = output_root.parent / "single_model_spec.json"
        write_model_spec_json(model_size=model_size, path=model_specs_json)
        cmd = [
            str(VEOMNI_ENV_PYTHON),
            str(FINAL_INFER_NEW_DIR / "run_stage3_top3x2_full_infer.py"),
            "--python-bin",
            str(VEOMNI_ENV_PYTHON),
            "--data-root",
            str(data_root),
            "--run-root",
            str(output_root.parent / "_runner"),
            "--output-root",
            str(output_root),
            "--log-dir",
            str(output_root.parent / "_runner_logs"),
            "--model-specs-json",
            str(model_specs_json),
            "--gpu-ids",
            "0",
            "--workers-per-gpu",
            "1",
            "--languages",
            language,
            "--limit",
            "1",
            "--audio-retries",
            str(audio_retries if audio_retries is not None else spec["audio_retries"]),
            "--worker-launch-retries",
            "2",
        ]
        if overwrite:
            cmd.append("--overwrite")
    else:
        fixed_evalset_tsv = output_root.parent / "single_fixed_evalset.tsv"
        eval_id = sample_id if sample_id else data_root.name
        fixed_evalset_tsv.write_text(f"eval_id\tlanguage\n{eval_id}\t{language}\n", encoding="utf-8")
        cmd = [
            str(VEOMNI_ENV_PYTHON),
            str(FINAL_INFER_NEW_DIR / "run_edit_best_model_on_fixed_evalset.py"),
            "--gt-root",
            str(data_root),
            "--fixed-evalset-tsv",
            str(fixed_evalset_tsv),
            "--output-root",
            str(output_root),
            "--python-bin",
            str(VEOMNI_ENV_PYTHON),
            "--infer-script",
            str(spec["edit_script"]),
            "--checkpoint-path",
            str(spec["checkpoint_path"]),
            "--languages",
            language,
            "--gpu-ids",
            "0",
            "--workers-per-gpu",
            "1",
            "--device",
            "cuda:0" if device.startswith("cuda") else device,
            "--torch-dtype",
            torch_dtype,
            "--attn-implementation",
            attn_implementation,
            "--history-mode",
            history_mode,
            "--audio-max-new-tokens",
            str(audio_max_new_tokens),
            "--audio-min-new-tokens",
            str(audio_min_new_tokens),
            "--temperature",
            str(temperature),
            "--top-p",
            str(top_p),
            "--seed",
            "42",
        ]
        if overwrite:
            cmd.append("--overwrite")
    if run_log_path is not None:
        run_log_path.parent.mkdir(parents=True, exist_ok=True)
        with run_log_path.open("w", encoding="utf-8") as handle:
            subprocess.run(cmd, check=True, env=env, stdout=handle, stderr=subprocess.STDOUT)
    else:
        subprocess.run(cmd, check=True, env=env)
    return cmd


def collect_formal_outputs(output_root: Path, model_size: str, language: str, sample_id: str) -> tuple[Path, Path]:
    tag = str(model_spec(model_size)["tag"])
    cot_path = output_root / tag / language / "cot" / f"{sample_id}.txt"
    wav_path = output_root / tag / language / "wav" / f"{sample_id}.wav"
    if not cot_path.exists():
        raise FileNotFoundError(f"Generated COT not found: {cot_path}")
    if not wav_path.exists():
        raise FileNotFoundError(f"Generated wav not found: {wav_path}")
    return cot_path, wav_path


def collect_edit_only_output(output_root: Path, language: str, sample_id: str) -> tuple[Path, Path]:
    cot_path = output_root / language / "cot" / f"{sample_id}.txt"
    wav_path = output_root / language / "wav" / f"{sample_id}.wav"
    if not cot_path.exists():
        raise FileNotFoundError(f"Edited COT output not found: {cot_path}")
    if not wav_path.exists():
        raise FileNotFoundError(f"Generated wav not found: {wav_path}")
    return cot_path, wav_path


def wait_for_manual_edit(target_path: Path) -> None:
    if not target_path.exists():
        raise FileNotFoundError(target_path)
    initial_mtime_ns = target_path.stat().st_mtime_ns
    print(f"[waiting] Edit and save: {target_path}", flush=True)
    input("[waiting] After saving the txt file, press Enter here to continue.")
    current_mtime_ns = target_path.stat().st_mtime_ns
    if current_mtime_ns == initial_mtime_ns:
        print("[warning] File timestamp did not change. Continuing with current file contents.", flush=True)
