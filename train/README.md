# COT-TTS Train

## Overview

This directory contains a minimal training scaffold copied from the VeOmni framework for the COT-TTS project.

The current copy focuses on the framework layer only:

- `veomni/`: core training framework, including arguments, data pipeline, distributed training, model wrappers, ops, optimizers, schedulers, and utilities
- `tasks/`: task entrypoints, including the generic torch training launcher
- `train.sh`: distributed training launcher based on `torchrun`
- `pyproject.toml`, `uv.lock`, `Makefile`, `build.sh`: project packaging and build metadata
- `env/environment.yaml`: original environment description kept as reference
- `requirements.veomni.freeze.txt`: original exported package snapshot kept as reference
- `requirements.txt`: GitHub-friendly install list without machine-specific local paths
- `setup_train_env.sh`: one-command local environment setup under `train/runtime_env`

To keep this directory clean and reusable, the following are intentionally not copied here yet:

- training data
- pretrained model weights
- experiment configs
- outputs, checkpoints, logs, and inference artifacts

The tokenizer assets used by the released training configs are included under:

- `model/qwen3_sparktts_with_under_special`

This gives us a clean base that we can later adapt into the final COT-TTS training codebase.

## Data Format

The training data is organized around one unified sequence template, and all tasks are defined as variations of this structure:

```text
<bos>
<task_start>aaa<task_end>
<history_start>
<audio_his_start>ccc<audio_his_end>
<history_end>
<target_start>
<text_start>ddd<text_end>
<audio_ref_start>fff<audio_ref_end>
<target_end>
<output_start>
<under_start>iii<under_end>
<cot_start>ggg<cot_end>
<audio_tar_start>hhh<audio_tar_end>
<output_end>
<eos>
```

In this template:

- `aaa` is the task name
- `ccc` is the history audio token sequence
- `ddd` is the target text
- `fff` is the reference audio token sequence
- `iii` is the under/understanding field
- `ggg` is the chain-of-thought field
- `hhh` is the target audio token sequence

Different tasks do not introduce completely different data formats. Instead, they reuse this common structure and adjust which fields are present, emphasized, or supervised.

## Model Download

The released training code expects the base models to be downloaded separately from the official model pages:

- Qwen3 0.6B: `https://huggingface.co/Qwen/Qwen3-0.6B`
- Qwen3 1.7B: `https://huggingface.co/Qwen/Qwen3-1.7B`
- Spark-TTS: `https://huggingface.co/SparkAudio/Spark-TTS-0.5B`

## Environment Setup

Clone the repo, then create the local training environment under `train/runtime_env`:

```bash
cd train
bash setup_train_env.sh
source runtime_env/bin/activate
```

This avoids any dependency on machine-specific personal virtual environment
paths.

The dependency snapshot was exported from a Python `3.11.8` environment.

Notes:

- The default install target is Linux + CUDA 12.4.
- If a machine uses a different CUDA stack, override `TORCH_INDEX_URL` before
  running `setup_train_env.sh`.
- `flash-attn` is not required by the default setup script.

If you need to compare or rebuild dependencies, use these files:

- `pyproject.toml`
- `uv.lock`
- `env/environment.yaml`
- `requirements.veomni.freeze.txt`
- `requirements.txt`

## Paths and Local Setup

The released configs use repository-relative paths for models, tokenizer, and
outputs. Training data paths should be prepared locally and can be passed in
through the launch scripts.

Before running training, users should download:

- `model/Qwen3-0.6B`
- `model/Qwen3-1.7B`
- `model/Spark-TTS`

and prepare their own parquet data directories for each stage.
