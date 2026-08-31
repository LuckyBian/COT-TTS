#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from cot_tts_single_infer_common import (
    BEST_MODEL_SPECS,
    INFER_ROOT,
    InferResult,
    generate_audio_from_cot,
    generate_cot,
    load_single_infer_runtime,
    make_infer_args,
    model_spec,
    prepare_runtime_audio,
    read_target_text,
    write_failure_artifacts,
    write_result_manifest,
)


DEFAULT_OUTPUT_ROOT = INFER_ROOT / "outputs_normal"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single-sample normal inference.")
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
    parser.add_argument("--attn-implementation", type=str, default="sdpa")
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
    runtime = None
    stage = "setup"
    try:
        target_text = read_target_text(args.text, str(args.text_file) if args.text_file else "")
        output_dir.mkdir(parents=True, exist_ok=True)
        run_log_path = output_dir / "run.log"
        generated_cot_dst = output_dir / "generated_cot.txt"
        generated_wav_dst = output_dir / "output.wav"

        temperature = args.temperature if args.temperature >= 0 else float(spec["temperature"])
        top_p = args.top_p if args.top_p >= 0 else float(spec["top_p"])
        audio_retries = args.audio_retries if args.audio_retries > 0 else int(spec["audio_retries"])

        stage = "prepare_audio"
        runtime_audio_dir, history_16k, reference_16k = prepare_runtime_audio(args.history_audio, args.reference_audio)

        stage = "load_runtime"
        runtime = load_single_infer_runtime(
            model_size=args.model_size,
            device=args.device,
            torch_dtype=args.torch_dtype,
            attn_implementation=args.attn_implementation,
        )

        infer_args = make_infer_args(
            history_mode=args.history_mode,
            torch_dtype=args.torch_dtype,
            attn_implementation=args.attn_implementation,
            do_sample=args.do_sample,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=args.repetition_penalty,
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            cot_max_new_tokens=args.cot_max_new_tokens,
            cot_min_new_tokens=args.cot_min_new_tokens,
            audio_max_new_tokens=args.audio_max_new_tokens,
            audio_min_new_tokens=args.audio_min_new_tokens,
            max_semantic_tokens=args.max_semantic_tokens,
            sample_rate=args.sample_rate,
        )

        stage = "generate_cot"
        cot_error = None
        cot_text = ""
        for _ in range(max(1, args.cot_retries)):
            try:
                cot_text = generate_cot(
                    runtime=runtime,
                    infer_args=infer_args,
                    history_audio_path=history_16k,
                    reference_audio_path=reference_16k,
                    target_text=target_text,
                )
                generated_cot_dst.write_text(cot_text + "\n", encoding="utf-8")
                cot_error = None
                break
            except Exception as exc:
                cot_error = exc
        if cot_error is not None:
            raise cot_error

        stage = "generate_audio"
        audio_error = None
        for _ in range(max(1, audio_retries)):
            try:
                generate_audio_from_cot(
                    runtime=runtime,
                    infer_args=infer_args,
                    history_audio_path=history_16k,
                    reference_audio_path=reference_16k,
                    target_text=target_text,
                    cot_text=cot_text,
                    output_wav_path=generated_wav_dst,
                    global_source=args.global_source,
                )
                audio_error = None
                break
            except Exception as exc:
                audio_error = exc
        if audio_error is not None:
            raise audio_error

        run_log_path.write_text(
            "\n".join(
                [
                    f"model_size={args.model_size}",
                    f"checkpoint_path={checkpoint_path}",
                    f"history_audio={args.history_audio}",
                    f"reference_audio={args.reference_audio}",
                    f"language={args.language}",
                    f"sample_id={args.sample_id}",
                    f"attn_implementation={args.attn_implementation}",
                    f"temperature={temperature}",
                    f"top_p={top_p}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

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
