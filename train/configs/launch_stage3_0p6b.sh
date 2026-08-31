#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1,2,3,4,5,6}"
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

INIT_CKPT="${INIT_CKPT:-}"
if [[ -z "$INIT_CKPT" ]]; then
  echo "ERROR: please provide INIT_CKPT for stage3_0p6b." >&2
  exit 1
fi
if [[ "$INIT_CKPT" == */hf_ckpt ]]; then
  INIT_CKPT="${INIT_CKPT%/hf_ckpt}"
fi
if [[ ! -f "$INIT_CKPT/.metadata" ]]; then
  echo "ERROR: INIT_CKPT must point to a DCP checkpoint directory containing .metadata, got: $INIT_CKPT" >&2
  exit 1
fi

TRAIN_SIZE="${TRAIN_SIZE:-3200000000}"
MAX_SEQ_LEN="${MAX_SEQ_LEN:-3072}"
TRAIN_PATH="${TRAIN_PATH:-$PROJECT_ROOT/data/stage3/parquet}"
ATTN_IMPL="${ATTN_IMPL:-sdpa}"

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${OUT_DIR:-$PROJECT_ROOT/outputs/stage3_0p6b/${RUN_ID}}"
mkdir -p "$OUT_DIR"
LOG_PATH="$OUT_DIR/train.log"

bash train.sh tasks/train_torch.py configs/stage3_0p6b.yaml \
  --train.output_dir "$OUT_DIR" \
  --model.attn_implementation "$ATTN_IMPL" \
  --train.data_parallel_mode ddp \
  --train.init_device cuda \
  --train.global_batch_size 96 \
  --train.micro_batch_size 4 \
  --train.load_checkpoint_path "$INIT_CKPT" \
  --train.load_model_only true \
  --data.train_path "$TRAIN_PATH" \
  --data.num_workers 16 \
  --data.prefetch_factor 4 \
  --train.enable_gradient_checkpointing false \
  --data.train_size "$TRAIN_SIZE" \
  --train.lr_warmup_ratio 0.08 \
  --train.lr_decay_style cosine \
  --train.lr 3.0e-6 \
  --train.lr_min 3.0e-7 \
  --train.weight_decay 0.1 \
  --train.max_grad_norm 1.0 \
  --train.num_train_epochs 1 \
  --data.max_seq_len "$MAX_SEQ_LEN" \
  --data.audio_his_drop_prob 0.0 \
  --data.audio_his_drop_ratio_max 0.10 \
  --data.audio_his_drop_skip_prefix_tokens 32 \
  --train.save_steps 0 \
  --train.save_best_steps 1000 \
  --train.logging_steps 10 \
  --train.save_epochs 0 \
  --train.save_epoch_points 0.5 1.0 \
  --train.save_hf_weights false \
  --train.keep_last_checkpoints 0 \
  --train.keep_best_and_last_checkpoints false \
  --train.wandb_name qwen3-stage3-0p6b-1ep \
  2>&1 | tee "$LOG_PATH"
