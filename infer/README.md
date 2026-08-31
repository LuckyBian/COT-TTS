# COT-TTS Inference

## Introduction

This folder provides a minimal single-sample **normal inference** pipeline for
the best COT-TTS `0.6B` and `1.7B` models.

Input:

- historical dialogue audio
- reference audio
- target text

Output:

- generated COT reasoning text
- synthesized target audio

This version only keeps the default normal inference path. Edit-mode and
environment bundling are intentionally omitted.

## Required Models

Place the required model folders under:

```text
infer/
├── models/
│   ├── best_0p6/
│   ├── best_1p7/
│   └── Spark-TTS-0.5B/
```

Download source:

- Hugging Face repo: `https://huggingface.co/HKUSTAudio/COT-TTS`

Expected subfolders under `infer/models/`:

- `best_0p6`
- `best_1p7`
- `Spark-TTS-0.5B`

Example:

```bash
cd infer/models
huggingface-cli download HKUSTAudio/COT-TTS best_0p6 best_1p7 Spark-TTS-0.5B --repo-type model --local-dir .
```

## Environment

Clone the repo, then create the local inference environment under `infer/runtime_env`:

```bash
cd infer
bash setup_infer_env.sh
source activate_infer_env.sh
```

This installs the pinned Python dependencies from `requirements.txt` into a
local virtualenv, so users do not need any machine-specific Python path.

Notes:

- The default install target is Linux + CUDA 12.4.
- If a machine uses a different CUDA stack, override `TORCH_INDEX_URL` before
  running `setup_infer_env.sh`.
- `flash-attn` is not required by default in this repo-level setup.

## Demo Command

```bash
cd infer

source activate_infer_env.sh

python infer_single_normal.py \
  --model-size 1p7 \
  --history-audio demo/eval-zh-837534_his.wav \
  --reference-audio demo/eval-zh-837534_ref.wav \
  --text-file demo/eval-zh-837534.txt \
  --language zh \
  --sample-id eval-zh-837534_demo \
  --output-root demo/outputs \
  --device cuda:2 \
  --history-mode full \
  --torch-dtype bfloat16 \
  --attn-implementation sdpa \
  --cot-max-new-tokens 800 \
  --audio-max-new-tokens 1600 \
  --temperature 0.6 \
  --top-p 0.8 \
  --global-source ref \
  --audio-retries 2
```

For `0.6B`, change:

```bash
--model-size 0p6 --temperature 0.95 --audio-retries 3
```

## Outputs

Normal inference writes:

- `outputs_normal/<model-size>/<sample-id>/generated_cot.txt`
- `outputs_normal/<model-size>/<sample-id>/output.wav`
- `outputs_normal/<model-size>/<sample-id>/run.log`
- `outputs_normal/<model-size>/<sample-id>/manifest.json`
