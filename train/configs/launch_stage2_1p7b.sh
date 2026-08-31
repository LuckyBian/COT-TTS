#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

export NCCL_TIMEOUT="${NCCL_TIMEOUT:-7200}"
export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3,4,5,6,7}"
export TOKENIZERS_PARALLELISM=false
export TORCH_NCCL_AVOID_RECORD_STREAMS=1
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

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

INIT_CKPT="${INIT_CKPT:-}"
if [[ -z "$INIT_CKPT" ]]; then
  echo "ERROR: please provide INIT_CKPT for stage2_1p7b." >&2
  exit 1
fi
if [[ "$INIT_CKPT" == */hf_ckpt ]]; then
  INIT_CKPT="${INIT_CKPT%/hf_ckpt}"
fi
if [[ ! -f "$INIT_CKPT/.metadata" ]]; then
  echo "ERROR: INIT_CKPT must point to a DCP checkpoint directory containing .metadata, got: $INIT_CKPT" >&2
  exit 1
fi

TRAIN_SIZE="${TRAIN_SIZE:-12000000000}"
MAX_SEQ_LEN="${MAX_SEQ_LEN:-3072}"
TRAIN_PATH="${TRAIN_PATH:-$PROJECT_ROOT/data/stage2/parquet}"
ATTN_IMPL="${ATTN_IMPL:-sdpa}"

RUN_ID="${RUN_ID:-${SLURM_JOB_ID:-$(date +%Y%m%d_%H%M%S)}}"
OUT_DIR="${OUT_DIR:-$PROJECT_ROOT/outputs/stage2_1p7b/${RUN_ID}}"
mkdir -p "$OUT_DIR"

NODE_ID="${SLURM_NODEID:-0}"
NODE_WORK_DIR="$OUT_DIR/node${NODE_ID}"
mkdir -p "$NODE_WORK_DIR"
LOG_FILE="$OUT_DIR/train_node${NODE_ID}.log"

{
  cd "$NODE_WORK_DIR" || exit 1
  bash "$PROJECT_ROOT/train.sh" \
    "$PROJECT_ROOT/tasks/train_torch.py" \
    "$PROJECT_ROOT/configs/stage2_1p7b.yaml" \
    --train.output_dir "$OUT_DIR" \
    --model.attn_implementation "$ATTN_IMPL" \
    --train.data_parallel_mode ddp \
    --train.init_device cuda \
    --train.global_batch_size 128 \
    --train.micro_batch_size 2 \
    --train.load_checkpoint_path "$INIT_CKPT" \
    --train.load_model_only true \
    --data.train_path "$TRAIN_PATH" \
    --data.num_workers 8 \
    --data.prefetch_factor 2 \
    --train.enable_gradient_checkpointing true \
    --data.train_size "$TRAIN_SIZE" \
    --train.lr_warmup_ratio 0.1 \
    --train.lr_decay_style cosine \
    --train.lr 1.0e-5 \
    --train.lr_min 1.0e-6 \
    --train.weight_decay 0.1 \
    --train.max_grad_norm 1.0 \
    --train.num_train_epochs 3 \
    --data.max_seq_len "$MAX_SEQ_LEN" \
    --data.audio_his_drop_prob 0.5 \
    --data.audio_his_drop_ratio_max 0.10 \
    --data.audio_his_drop_skip_prefix_tokens 32 \
    --train.save_steps 0 \
    --train.save_best_steps 1000 \
    --train.logging_steps 10 \
    --train.save_epochs 0 \
    --train.save_epoch_points 0.5 0.75 1.0 1.25 1.5 2.0 2.5 3.0 \
    --train.save_hf_weights false \
    --train.keep_last_checkpoints 0 \
    --train.keep_best_and_last_checkpoints true \
    --train.wandb_name qwen3-1p7b-stage2-3ep
} 2>&1 | tee "$LOG_FILE"
