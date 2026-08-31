#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

export NCCL_TIMEOUT="${NCCL_TIMEOUT:-7200}"
export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"
export TOKENIZERS_PARALLELISM=false
export TORCH_NCCL_AVOID_RECORD_STREAMS=1
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export CACHE_ROOT="${CACHE_ROOT:-$PROJECT_ROOT/tmp}"
export HF_HOME="${HF_HOME:-$CACHE_ROOT/hf_home}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-$HF_HOME/datasets}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME/transformers}"
mkdir -p "$HF_DATASETS_CACHE" "$TRANSFORMERS_CACHE"

export NNODES="${NNODES:-${SLURM_NNODES:-1}}"
export NODE_RANK="${NODE_RANK:-${SLURM_NODEID:-0}}"
export MASTER_PORT="${MASTER_PORT:-29500}"
if [[ -z "${MASTER_ADDR:-}" ]] && [[ -n "${SLURM_JOB_NODELIST:-}" ]]; then
  export MASTER_ADDR
  MASTER_ADDR="$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)"
fi

RUN_ID="${RUN_ID:-${SLURM_JOB_ID:-$(date +%Y%m%d_%H%M%S)}}"
OUT_DIR="${OUT_DIR:-$PROJECT_ROOT/outputs/stage1_1p7b/${RUN_ID}}"
TRAIN_PATH="${TRAIN_PATH:-$PROJECT_ROOT/data/stage1/parquet}"
ATTN_IMPL="${ATTN_IMPL:-sdpa}"
mkdir -p "$OUT_DIR"
NODE_ID="${SLURM_NODEID:-0}"
NODE_WORK_DIR="$OUT_DIR/node${NODE_ID}"
mkdir -p "$NODE_WORK_DIR"
LOG_FILE="$OUT_DIR/train_node${NODE_ID}.log"

{
  cd "$NODE_WORK_DIR" || exit 1
  bash "$PROJECT_ROOT/train.sh" \
    "$PROJECT_ROOT/tasks/train_torch.py" \
    "$PROJECT_ROOT/configs/stage1_1p7b.yaml" \
    --train.output_dir "$OUT_DIR" \
    --data.train_path "$TRAIN_PATH" \
    --model.attn_implementation "$ATTN_IMPL" \
    --train.init_device cuda \
    --train.num_train_epochs 1 \
    --train.save_steps 2000 \
    --train.save_epochs 1 \
    --train.save_hf_weights false
} 2>&1 | tee "$LOG_FILE"
