#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from cot_tts_single_infer_common import (
    BEST_MODEL_SPECS,
    INFER_ROOT,
    InferResult,
    build_single_case_dataset,
    collect_formal_outputs,
    model_spec,
    prepare_runtime_audio,
    read_target_text,
    run_formal_infer,
    write_failure_artifacts,
    write_result_manifest,
)


DEFAULT_OUTPUT_ROOT = INFER_ROOT / "outputs_normal"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single-sample normal inference via the exact batch infer scripts.")
    parser.add_argument("--model-size", choices=sorted(BEST_MODEL_SPECS.keys()), default="0p6")
    parser.add_argument("--history-audio", type=Path, required=True)
    parser.add_argument("--reference-audio", type=Path, required=True)
    parser.add_argument("--text", type=str, default="")
    parser.add_argument("--text-file", type=Path, default=None)
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--sample-id", type=str, default="sample")
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--history-mode", choices=["full", "semantic", "full_first_then_semantic"], default="full")
    parser.add_argument("--torch-dtype", choices=["bfloat16", "float16", "float32"], default="bfloat16")
    parser.add_argument("--attn-implementation", type=str, default="flash_attention_2")
    parser.add_argument("--cot-max-new-tokens", type=int, default=800)
    parser.add_argument("--cot-min-new-tokens", type=int, default=32)
    parser.add_argument("--audio-max-new-tokens", type=int, default=1600)
    parser.add_argument("--audio-min-new-tokens", type=int, default=256)
    parser.add_argument("--do-sample", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--temperature", type=float, default=-1.0)
    parser.add_argument("--top-p", type=float, default=-1.0)
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument("--no-repeat-ngram-size", type=int, default=0)
    parser.add_argument("--cot-retries", type=int, default=4)
    parser.add_argument("--audio-retries", type=int, default=-1)
    parser.add_argument("--max-semantic-tokens", type=int, default=0)
    parser.add_argument("--global-source", choices=["ref", "generated"], default="ref")
    parser.add_argument("--sample-rate", type=int, default=16000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = model_spec(args.model_size)
    checkpoint_path = Path(spec["checkpoint_path"])
    output_dir = args.output_root / args.model_size / args.sample_id
    manifest_path = output_dir / "manifest.json"
    target_text = ""
    runtime_audio_dir = None
    stage = "setup"
    try:
        target_text = read_target_text(args.text, str(args.text_file) if args.text_file else "")
        output_dir.mkdir(parents=True, exist_ok=True)

        runtime_root = output_dir / "_runtime"
        dataset_root = runtime_root / "input_dataset"
        infer_root = runtime_root / "formal_infer_outputs"
        run_log_path = output_dir / "run.log"

        temperature = args.temperature if args.temperature >= 0 else float(spec["temperature"])
        top_p = args.top_p if args.top_p >= 0 else float(spec["top_p"])
        audio_retries = args.audio_retries if args.audio_retries > 0 else int(spec["audio_retries"])

        stage = "prepare_audio"
        runtime_audio_dir, history_16k, reference_16k = prepare_runtime_audio(args.history_audio, args.reference_audio)

        stage = "build_dataset"
        build_single_case_dataset(
            dataset_root=dataset_root,
            language=args.language,
            sample_id=args.sample_id,
            history_audio_path=history_16k,
            reference_audio_path=reference_16k,
            target_text=target_text,
        )

        stage = "formal_infer"
        cmd = run_formal_infer(
            model_size=args.model_size,
            mode="normal",
            data_root=dataset_root,
            output_root=infer_root,
            language=args.language,
            sample_id=args.sample_id,
            device=args.device,
            history_mode=args.history_mode,
            torch_dtype=args.torch_dtype,
            attn_implementation=args.attn_implementation,
            temperature=temperature,
            top_p=top_p,
            cot_max_new_tokens=args.cot_max_new_tokens,
            cot_min_new_tokens=args.cot_min_new_tokens,
            audio_max_new_tokens=args.audio_max_new_tokens,
            audio_min_new_tokens=args.audio_min_new_tokens,
            do_sample=args.do_sample,
            repetition_penalty=args.repetition_penalty,
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            cot_retries=args.cot_retries,
            audio_retries=audio_retries,
            max_semantic_tokens=args.max_semantic_tokens,
            global_source=args.global_source,
            sample_rate=args.sample_rate,
            overwrite=True,
            run_log_path=run_log_path,
        )

        stage = "collect_outputs"
        generated_cot_src, generated_wav_src = collect_formal_outputs(
            infer_root,
            args.model_size,
            args.language,
            args.sample_id,
        )
        generated_cot_dst = output_dir / "generated_cot.txt"
        generated_wav_dst = output_dir / "output.wav"
        shutil.copy2(generated_cot_src, generated_cot_dst)
        shutil.copy2(generated_wav_src, generated_wav_dst)

        result = InferResult(
            model_size=args.model_size,
            checkpoint_path=str(checkpoint_path),
            history_audio_path=str(args.history_audio),
            reference_audio_path=str(args.reference_audio),
            target_text=target_text,
            generated_cot_path=str(generated_cot_dst),
            generated_wav_path=str(generated_wav_dst),
            run_log_path=str(run_log_path),
            mode="normal",
            language=args.language,
            command=cmd,
        )
        write_result_manifest(manifest_path, result)
        print(f"[done] model={args.model_size}")
        print(f"[cot] {generated_cot_dst}")
        print(f"[wav] {generated_wav_dst}")
    except Exception as exc:
        write_failure_artifacts(
            output_dir,
            model_size=args.model_size,
            checkpoint_path=str(checkpoint_path),
            history_audio_path=str(args.history_audio),
            reference_audio_path=str(args.reference_audio),
            target_text=target_text,
            error=exc,
            stage=stage,
            manifest_name=manifest_path.name,
        )
        print(f"[skip] failed at stage={stage}: {exc}")
    finally:
        if runtime_audio_dir is not None and Path(runtime_audio_dir).exists():
            shutil.rmtree(runtime_audio_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
