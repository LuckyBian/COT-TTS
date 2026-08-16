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

This version only keeps the default normal inference path. Edit-mode, portable
environment packaging, and large bundled model files are intentionally omitted.

## Required Models

Place the required model folders under:

```text
infer/
├── models/
│   ├── best_0p6/
│   ├── best_1p7/
│   └── Spark-TTS-0.5B/
```

## Environment

If you already have the inference environment, activate it before running:

```bash
source /aifs4su/weizhenbian/envs/veomni/bin/activate
```

If you also prepared a local `runtime_env/` under this folder, you can use:

```bash
source activate_infer_env.sh
```

## Demo Command

```bash
cd /aifs4su/weizhenbian/code/COT-TTS/infer

source /aifs4su/weizhenbian/envs/veomni/bin/activate

python infer_single_normal.py \
  --model-size 1p7 \
  --history-audio /aifs4su/weizhenbian/code/COT-TTS/infer/demo/eval-zh-837534_his.wav \
  --reference-audio /aifs4su/weizhenbian/code/COT-TTS/infer/demo/eval-zh-837534_ref.wav \
  --text-file /aifs4su/weizhenbian/code/COT-TTS/infer/demo/eval-zh-837534.txt \
  --language zh \
  --sample-id eval-zh-837534_demo \
  --output-root /aifs4su/weizhenbian/code/COT-TTS/infer/demo/outputs \
  --device cuda:2 \
  --history-mode full \
  --torch-dtype bfloat16 \
  --attn-implementation flash_attention_2 \
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
