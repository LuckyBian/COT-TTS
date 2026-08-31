#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,3,4,5,7}"
export NCCL_TIMEOUT="${NCCL_TIMEOUT:-7200}"
export CACHE_ROOT="${CACHE_ROOT:-$PROJECT_ROOT/tmp}"
export HF_HOME="${HF_HOME:-$CACHE_ROOT/hf_home}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-$HF_HOME/datasets}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME/transformers}"
mkdir -p "$HF_DATASETS_CACHE" "$TRANSFORMERS_CACHE"

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${OUT_DIR:-$PROJECT_ROOT/outputs/stage1_0p6b/${RUN_ID}}"
TRAIN_PATH="${TRAIN_PATH:-$PROJECT_ROOT/data/stage1/parquet}"
ATTN_IMPL="${ATTN_IMPL:-sdpa}"
mkdir -p "$OUT_DIR"

bash train.sh tasks/train_torch.py configs/stage1_0p6b.yaml \
  --train.output_dir "$OUT_DIR" \
  --data.train_path "$TRAIN_PATH" \
  --model.attn_implementation "$ATTN_IMPL" \
  --train.data_parallel_mode ddp \
  --train.init_device cuda \
  --train.global_batch_size 72 \
  --train.micro_batch_size 3 \
  --data.num_workers 8 \
  --train.enable_gradient_checkpointing false \
  --data.train_size 20000000000 \
  --train.num_train_epochs 1 \
  --train.save_steps 5000 \
  --train.save_epochs 1 \
  --train.save_hf_weights false
