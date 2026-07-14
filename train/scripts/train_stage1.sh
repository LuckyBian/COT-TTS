#!/bin/bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export NCCL_TIMEOUT=7200
export NCCL_DEBUG=WARN
export TOKENIZERS_PARALLELISM=false
export TORCH_NCCL_AVOID_RECORD_STREAMS=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export CACHE_ROOT="${CACHE_ROOT:-$ROOT_DIR/tmp}"
export HF_HOME=$CACHE_ROOT/hf_home
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TRANSFORMERS_CACHE=$HF_HOME/transformers
mkdir -p "$HF_DATASETS_CACHE" "$TRANSFORMERS_CACHE"

MODEL_PATH="${MODEL_PATH:-$ROOT_DIR/models/Qwen3-1.7B}"
TOKENIZER_PATH="${TOKENIZER_PATH:-$ROOT_DIR/models/qwen3_1.7b_sparktts_with_special}"
TRAIN_PATH="${TRAIN_PATH:-$ROOT_DIR/data/stage1/parquet}"

export NNODES="${NNODES:-${SLURM_NNODES:-1}}"
export NODE_RANK="${NODE_RANK:-${SLURM_NODEID:-0}}"
export MASTER_PORT="${MASTER_PORT:-29500}"
if [[ -z "${MASTER_ADDR:-}" ]] && [[ -n "${SLURM_JOB_NODELIST:-}" ]]; then
  export MASTER_ADDR
  MASTER_ADDR="$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)"
fi

RUN_ID="${SLURM_JOB_ID:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${OUT_DIR:-$ROOT_DIR/outputs/stage1/${RUN_ID}}"
mkdir -p "$OUT_DIR"
NODE_ID="${SLURM_NODEID:-0}"
NODE_WORK_DIR="$OUT_DIR/node${NODE_ID}"
mkdir -p "$NODE_WORK_DIR"
LOG_FILE="$OUT_DIR/train_node${NODE_ID}.log"

{
  echo "===== launch info ====="
  date
  echo "RUN_ID=$RUN_ID"
  echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
  echo "SLURM_NODEID=${SLURM_NODEID:-}"
  echo "OUT_DIR=$OUT_DIR"
  echo "NODE_WORK_DIR=$NODE_WORK_DIR"
  echo "NNODES=${NNODES:-}"
  echo "NODE_RANK=${NODE_RANK:-}"
  echo "MASTER_ADDR=${MASTER_ADDR:-}"
  echo "MASTER_PORT=${MASTER_PORT:-}"
  echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
  echo "NCCL_TIMEOUT=$NCCL_TIMEOUT"
  echo "HF_HOME=$HF_HOME"
  echo "MODEL_PATH=$MODEL_PATH"
  echo "TOKENIZER_PATH=$TOKENIZER_PATH"
  echo "TRAIN_PATH=$TRAIN_PATH"
  echo "----- gpu info -----"
  nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
  echo "----- launch command -----"
  echo "bash $ROOT_DIR/train.sh $ROOT_DIR/tasks/train_torch.py $ROOT_DIR/configs/stage1.yaml --train.output_dir $OUT_DIR --model.attn_implementation flash_attention_2 --train.init_device cuda --train.save_steps 2000 --train.save_epochs 1 --train.save_hf_weights false"
  echo "========================="
  cd "$NODE_WORK_DIR" || exit 1
  bash "$ROOT_DIR/train.sh" \
    "$ROOT_DIR/tasks/train_torch.py" \
    "$ROOT_DIR/configs/stage1.yaml" \
    --train.output_dir "$OUT_DIR" \
    --model.model_path "$MODEL_PATH" \
    --model.tokenizer_path "$TOKENIZER_PATH" \
    --model.attn_implementation flash_attention_2 \
    --data.train_path "$TRAIN_PATH" \
    --train.init_device cuda \
    --train.save_steps 2000 \
    --train.save_epochs 1 \
    --train.save_hf_weights false
} 2>&1 | tee "$LOG_FILE"
