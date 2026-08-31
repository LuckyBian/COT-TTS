import json
import math
import os
import re
import shutil
import time
import pickle
from dataclasses import asdict
from datetime import timedelta
from functools import partial
from typing import Any, Dict, List, Optional, Set

import torch
import torch.distributed as dist
import wandb
from tqdm import trange

# from veomni.arguments import DataArguments, ModelArguments, TrainingArguments, parse_args, save_args
from veomni.arguments import VeOmniArguments, parse_args, save_args
from veomni.checkpoint import build_checkpointer
from veomni.data import (
    build_chat_template,
    build_dataloader,
    build_dataset,
)
from veomni.data.data_transform import process_pretrain_example, process_sft_example
from veomni.distributed.clip_grad_norm import veomni_clip_grad_norm
from veomni.distributed.offloading import build_activation_offloading_context
from veomni.distributed.parallel_state import get_parallel_state, init_parallel_state
from veomni.distributed.torch_parallelize import build_parallelize_model
from veomni.models import build_foundation_model, build_tokenizer, save_model_assets
from veomni.optim import build_lr_scheduler, build_optimizer
from veomni.utils import helper
from veomni.utils.device import (
    get_device_type,
    get_dist_comm_backend,
    get_torch_device,
    is_nccl_backend,
    synchronize,
)
from veomni.utils.dist_utils import all_reduce
from veomni.utils.loss_utils import count_loss_token, mean_global_loss
from veomni.utils.save_safetensor_utils import save_hf_safetensor


logger = helper.create_logger(__name__)


def _checkpoint_embedding_vocab_size(checkpoint_path: str) -> Optional[int]:
    metadata_path = os.path.join(checkpoint_path, ".metadata")
    if not os.path.isfile(metadata_path):
        return None
    try:
        with open(metadata_path, "rb") as f:
            metadata = pickle.load(f)
    except Exception:
        return None

    state_dict_metadata = getattr(metadata, "state_dict_metadata", {})
    for key in ("model.model.embed_tokens.weight", "model.embed_tokens.weight"):
        item = state_dict_metadata.get(key)
        size = getattr(item, "size", None)
        if size is not None and len(size) >= 1:
            return int(size[0])
    return None


def _maybe_resize_token_embeddings(model: torch.nn.Module, tokenizer_or_size, reason: str = "tokenizer") -> None:
    """Expand model embeddings when tokenizer/checkpoint has more tokens."""
    target_size = len(tokenizer_or_size) if not isinstance(tokenizer_or_size, int) else tokenizer_or_size
    input_embeddings = model.get_input_embeddings()
    model_vocab_size = input_embeddings.weight.shape[0]
    original_dtype = input_embeddings.weight.dtype
    if target_size <= model_vocab_size:
        return

    logger.info_rank0(
        "%s vocab size (%s) is larger than model embeddings (%s), resizing token embeddings.",
        reason,
        target_size,
        model_vocab_size,
    )
    model.resize_token_embeddings(target_size)
    new_size = model.get_input_embeddings().weight.shape[0]
    logger.info_rank0(f"Resized token embeddings to {new_size}.")
    # Keep model dtype consistent after resize (important for flash-attn fp16/bf16 requirement).
    current_dtype = model.get_input_embeddings().weight.dtype
    if current_dtype != original_dtype:
        model.to(dtype=original_dtype)
        logger.info_rank0(f"Casted model back to dtype {original_dtype} after resizing embeddings.")


def _prune_old_step_checkpoints(checkpoint_root: str, keep_last: int) -> None:
    """Keep latest N global_step_* checkpoints and delete older ones."""
    if keep_last <= 0 or not os.path.isdir(checkpoint_root):
        return

    pattern = re.compile(r"^global_step_(\d+)$")
    step_dirs = []
    for name in os.listdir(checkpoint_root):
        m = pattern.match(name)
        if m is None:
            continue
        full_path = os.path.join(checkpoint_root, name)
        if not os.path.isdir(full_path):
            continue
        step_dirs.append((int(m.group(1)), full_path))

    if len(step_dirs) <= keep_last:
        return

    step_dirs.sort(key=lambda x: x[0])
    to_remove = step_dirs[:-keep_last]
    for step, path in to_remove:
        shutil.rmtree(path, ignore_errors=True)
        logger.info_rank0(f"Pruned old checkpoint: global_step_{step}")


def _prune_step_checkpoints_except(checkpoint_root: str, keep_steps: Set[int]) -> None:
    """Delete global_step_* checkpoints except the explicitly retained steps."""
    if not os.path.isdir(checkpoint_root):
        return

    pattern = re.compile(r"^global_step_(\d+)$")
    for name in os.listdir(checkpoint_root):
        m = pattern.match(name)
        if m is None:
            continue
        step = int(m.group(1))
        if step in keep_steps:
            continue
        full_path = os.path.join(checkpoint_root, name)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path, ignore_errors=True)
            logger.info_rank0(f"Pruned checkpoint outside best/last retention: global_step_{step}")


def _remove_step_checkpoint(checkpoint_root: str, step: int) -> None:
    path = os.path.join(checkpoint_root, f"global_step_{step}")
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        logger.info_rank0(f"Pruned previous best checkpoint: global_step_{step}")


def _save_training_checkpoint(
    Checkpointer,
    args,
    model,
    optimizer,
    lr_scheduler,
    train_dataloader,
    environ_meter,
    global_step: int,
) -> str:
    helper.empty_cache()
    save_checkpoint_path = os.path.join(args.train.save_checkpoint_path, f"global_step_{global_step}")
    state = {
        "model": model,
        "optimizer": optimizer,
        "extra_state": {
            "global_step": global_step,
            "lr_scheduler": lr_scheduler.state_dict(),
            "train_dataloader": train_dataloader.state_dict(),
            "environ_meter": environ_meter.state_dict(),
            "torch_rng_state": torch.get_rng_state(),
        },
    }
    Checkpointer.save(args.train.save_checkpoint_path, state, global_steps=global_step)
    return save_checkpoint_path


def _epoch_point_steps(save_epoch_points: List[float], train_steps: int, num_train_epochs: int) -> List[int]:
    """Convert absolute fractional epochs to global steps, preserving configured order."""
    steps: List[int] = []
    seen = set()
    max_step = train_steps * num_train_epochs
    for point in save_epoch_points:
        if point <= 0:
            continue
        step = max(1, min(max_step, int(math.ceil(point * train_steps))))
        if step in seen:
            continue
        seen.add(step)
        steps.append(step)
    return steps


def _log_trainable_parameters(model: torch.nn.Module, architecture: str) -> None:
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    ratio = 100 * trainable / total if total else 0
    logger.info_rank0(
        f"train_architecture={architecture}: trainable parameters {trainable:,} / {total:,} ({ratio:.4f}%)."
    )


# @dataclass
# class Arguments:
#     model: "ModelArguments" = field(default_factory=ModelArguments)
#     data: "DataArguments" = field(default_factory=DataArguments)
#     train: "TrainingArguments" = field(default_factory=TrainingArguments)


def main():
    nccl_timeout = os.getenv("NCCL_TIMEOUT", None)
    pg_nccl_timeout = None
    if nccl_timeout is not None and is_nccl_backend():
        pg_nccl_timeout = timedelta(seconds=int(nccl_timeout))
    logger.info(f"Process_group timeout: {nccl_timeout}")
    dist.init_process_group(backend=get_dist_comm_backend(), timeout=pg_nccl_timeout)

    args = parse_args(VeOmniArguments)
    logger.info(f"Process rank: {args.train.global_rank}, world size: {args.train.world_size}")
    logger.info_rank0(json.dumps(asdict(args), indent=2))
    get_torch_device().set_device(f"{get_device_type()}:{args.train.local_rank}")
    helper.set_seed(args.train.seed, args.train.enable_full_determinism)
    helper.enable_high_precision_for_bf16()
    if args.train.local_rank == 0:
        helper.enable_third_party_logging()

    if args.train.global_rank == 0:
        save_args(args, args.train.output_dir)

    # Gradient checkpointing debug
    torch.utils.checkpoint.set_checkpoint_debug_enabled(args.train.debug_gradient_checkpointing)

    # Model checkpointer
    Checkpointer = build_checkpointer(dist_backend=args.train.data_parallel_mode, ckpt_manager=args.train.ckpt_manager)

    init_parallel_state(
        dp_size=args.train.data_parallel_size,
        dp_replicate_size=args.train.data_parallel_replicate_size,
        dp_shard_size=args.train.data_parallel_shard_size,
        tp_size=args.train.tensor_parallel_size,
        ep_size=args.train.expert_parallel_size,
        pp_size=args.train.pipeline_parallel_size,
        cp_size=args.train.context_parallel_size,
        ulysses_size=args.train.ulysses_parallel_size,
        dp_mode=args.train.data_parallel_mode,
    )

    logger.info_rank0("Prepare data")
    tokenizer = build_tokenizer(args.model.tokenizer_path)
    if args.data.data_type == "plaintext":
        transform = partial(
            process_pretrain_example,
            tokenizer=tokenizer,
            max_seq_len=args.data.max_seq_len,
            text_keys=args.data.text_keys,
        )
    elif args.data.data_type == "conversation":
        chat_template = build_chat_template(args.data.chat_template, tokenizer)
        transform = partial(
            process_sft_example,
            chat_template=chat_template,
            max_seq_len=args.data.max_seq_len,
            text_keys=args.data.text_keys,
            audio_his_drop_prob=args.data.audio_his_drop_prob,
            audio_his_drop_ratio_max=args.data.audio_his_drop_ratio_max,
            audio_his_drop_skip_prefix_tokens=args.data.audio_his_drop_skip_prefix_tokens,
        )
    else:
        raise NotImplementedError(f"Unsupported data type: {args.data.data_type}.")

    train_dataset = build_dataset(
        dataset_name=args.data.dataset_name,
        transform=transform,
        dataloader_batch_size=args.train.dataloader_batch_size,
        seed=args.train.seed,
        **asdict(args.data),
    )
    dataset_length = None if not hasattr(train_dataset, "__len__") else len(train_dataset)
    if args.data.datasets_type == "mapping":
        dataset_length = dataset_length / args.train.data_parallel_size
    args.train.compute_train_steps(args.data.max_seq_len, args.data.train_size, dataset_length)

    train_dataloader = build_dataloader(
        dataloader_type=args.data.dataloader_type,
        dataset=train_dataset,
        micro_batch_size=args.train.micro_batch_size,
        global_batch_size=args.train.global_batch_size,
        dataloader_batch_size=args.train.dataloader_batch_size,
        seed=args.train.seed,
        max_seq_len=args.data.max_seq_len,
        train_steps=args.train.train_steps,
        rmpad=args.train.rmpad,
        rmpad_with_pos_ids=args.train.rmpad_with_pos_ids,
        dyn_bsz=args.train.dyn_bsz,
        bsz_warmup_ratio=args.train.bsz_warmup_ratio,
        bsz_warmup_init_mbtoken=args.train.bsz_warmup_init_mbtoken,
        pad_packed_to_length=args.train.pad_packed_to_length,
        dyn_bsz_margin=args.train.dyn_bsz_margin,
        dyn_bsz_buffer_size=args.train.dyn_bsz_buffer_size,
        num_workers=args.data.num_workers,
        drop_last=args.data.drop_last,
        pin_memory=args.data.pin_memory,
        prefetch_factor=args.data.prefetch_factor,
    )

    logger.info_rank0("Prepare model")
    model = build_foundation_model(
        config_path=args.model.config_path,
        weights_path=args.model.model_path,
        torch_dtype="bfloat16" if args.train.enable_mixed_precision else "float32",
        attn_implementation=args.model.attn_implementation,
        moe_implementation=args.model.moe_implementation,
        init_device=args.train.init_device,
    )
    checkpoint_vocab_size = (
        _checkpoint_embedding_vocab_size(args.train.load_checkpoint_path)
        if args.train.load_checkpoint_path and args.train.load_model_only
        else None
    )
    if checkpoint_vocab_size is not None and checkpoint_vocab_size < len(tokenizer):
        _maybe_resize_token_embeddings(model, checkpoint_vocab_size, reason="Checkpoint")
    else:
        _maybe_resize_token_embeddings(model, tokenizer, reason="Tokenizer")
    model_config = model.config
    helper.print_device_mem_info("VRAM usage after building model")

    loaded_model_only_before_parallel = False
    if args.train.load_checkpoint_path and args.train.load_model_only:
        state = {"model": model}
        Checkpointer.load(args.train.load_checkpoint_path, state)
        dist.barrier()
        loaded_model_only_before_parallel = True
        logger.info_rank0(
            f"Loaded model weights before parallel wrapping from {args.train.load_checkpoint_path}; "
            "optimizer/scheduler/dataloader states were reset."
        )
        _maybe_resize_token_embeddings(model, tokenizer, reason="Tokenizer")

    if args.train.train_architecture == "lora":
        from veomni.utils.lora_utils import add_lora_to_model, freeze_parameters

        logger.info_rank0("Inject LoRA adapters into the SFT model.")
        freeze_parameters(model)
        add_lora_to_model(
            model,
            lora_rank=args.model.lora_rank,
            lora_alpha=args.model.lora_alpha,
            lora_target_modules=args.model.lora_target_modules,
            init_lora_weights=args.model.init_lora_weights,
            pretrained_lora_path=args.model.pretrained_lora_path,
            lora_target_modules_support=args.model.lora_target_modules_support.split(","),
        )
        if args.train.enable_mixed_precision:
            model.to(torch.bfloat16)
    elif args.train.train_architecture == "full":
        logger.info_rank0("train_architecture is full")
    else:
        raise ValueError(f"Unsupported train_architecture: {args.train.train_architecture}")

    _log_trainable_parameters(model, args.train.train_architecture)

    get_optimizer_pre_hook = getattr(model, "get_optimizer_pre_hook", None)
    model = build_parallelize_model(
        model,
        init_device=args.train.init_device,
        weights_path=args.model.model_path,
        enable_full_shard=args.train.enable_full_shard,
        enable_reshard_after_forward=args.train.enable_reshard_after_forward,
        enable_mixed_precision=args.train.enable_mixed_precision,
        enable_gradient_checkpointing=args.train.enable_gradient_checkpointing,
        enable_fsdp_offload=args.train.enable_fsdp_offload,
        basic_modules=list(set(getattr(model, "_no_split_modules", None) or []) | set(args.model.basic_modules)),
        enable_reentrant=args.train.enable_reentrant,
        enable_forward_prefetch=args.train.enable_forward_prefetch,
    )

    optimizer = build_optimizer(
        model,
        lr=args.train.lr,
        weight_decay=args.train.weight_decay,
        fused=True,
        optimizer_type=args.train.optimizer,
    )
    if get_optimizer_pre_hook is not None:
        optimizer_pre_hook = get_optimizer_pre_hook(model, model_config, args.train.data_parallel_mode)
        optimizer.register_step_pre_hook(optimizer_pre_hook)

    lr_scheduler = build_lr_scheduler(
        optimizer,
        train_steps=args.train.train_steps * args.train.num_train_epochs,
        lr=args.train.lr,
        lr_min=args.train.lr_min,
        lr_decay_style=args.train.lr_decay_style,
        lr_decay_ratio=args.train.lr_decay_ratio,
        lr_warmup_ratio=args.train.lr_warmup_ratio,
        lr_start=args.train.lr_start,
    )

    model_assets = None
    if args.train.global_rank == 0:
        if args.train.use_wandb:
            wandb.init(
                project=args.train.wandb_project,
                name=args.train.wandb_name,
                id=args.train.wandb_id,
                resume="allow" if args.train.wandb_id else None,
                settings=wandb.Settings(console="off"),
                config={**vars(args.model), **vars(args.data), **vars(args.train)},  # flatten dict
            )

        # save model_assets before training
        model_assets = [model_config, tokenizer if args.data.data_type == "plaintext" else chat_template]
        save_model_assets(args.train.model_assets_dir, model_assets)

    if args.train.profile_this_rank:
        profiler = helper.create_profiler(
            start_step=args.train.profile_start_step,
            end_step=args.train.profile_end_step,
            trace_dir=args.train.profile_trace_dir,
            record_shapes=args.train.profile_record_shapes,
            profile_memory=args.train.profile_profile_memory,
            with_stack=args.train.profile_with_stack,
            global_rank=args.train.global_rank,
        )
        profiler.start()

    start_epoch, start_step, global_step = 0, 0, 0
    save_checkpoint_path = None
    saved_checkpoint_steps: Set[int] = set()
    best_checkpoint_step: Optional[int] = None
    best_checkpoint_loss: Optional[float] = None
    last_checkpoint_step: Optional[int] = None
    environ_meter = helper.EnvironMeter(
        config=model_config,
        global_batch_size=args.train.global_batch_size,
        rmpad=args.train.rmpad,
        rmpad_with_pos_ids=args.train.rmpad_with_pos_ids,
        empty_cache_steps=args.train.empty_cache_steps,
        enable_multisource=args.data.enable_multisource,
        dataloader=train_dataloader,
        data_path=args.data.train_path,
    )

    if args.train.load_checkpoint_path and not loaded_model_only_before_parallel:
        if args.train.load_model_only:
            state = {"model": model}
            Checkpointer.load(args.train.load_checkpoint_path, state)
            dist.barrier()
            logger.info_rank0(
                f"Loaded model weights only from {args.train.load_checkpoint_path}; optimizer/scheduler/dataloader states were reset."
            )
            _maybe_resize_token_embeddings(model, tokenizer, reason="Tokenizer")
        else:
            state = {"model": model, "optimizer": optimizer, "extra_state": {}}  # cannot be None
            Checkpointer.load(args.train.load_checkpoint_path, state)
            global_step = state["extra_state"]["global_step"]
            start_epoch = global_step // args.train.train_steps
            start_step = global_step % args.train.train_steps
            lr_scheduler.load_state_dict(state["extra_state"]["lr_scheduler"])
            train_dataloader.load_state_dict(state["extra_state"]["train_dataloader"])
            environ_meter.load_state_dict(state["extra_state"]["environ_meter"])
            torch.set_rng_state(state["extra_state"]["torch_rng_state"])
            if start_step == 0:  # resume at the end of epoch
                iter(train_dataloader)  # clear resume state and prefetch data

            dist.barrier()
            logger.info_rank0(f"Load distributed checkpoint from {args.train.load_checkpoint_path} successfully!")

    helper.empty_cache()
    model_fwd_context, model_bwd_context = build_activation_offloading_context(
        args.train.enable_activation_offload, args.train.enable_gradient_checkpointing, args.train.activation_gpu_limit
    )
    model.train()
    logger.info(
        f"rank{args.train.local_rank} Start training, train_steps: {args.train.train_steps}, epochs: {args.train.num_train_epochs}"
    )
    save_epoch_point_steps = _epoch_point_steps(
        args.train.save_epoch_points, args.train.train_steps, args.train.num_train_epochs
    )
    save_epoch_point_step_set = set(save_epoch_point_steps)
    next_save_epoch_point_idx = 0
    while (
        next_save_epoch_point_idx < len(save_epoch_point_steps)
        and save_epoch_point_steps[next_save_epoch_point_idx] <= global_step
    ):
        next_save_epoch_point_idx += 1
    if save_epoch_point_steps:
        logger.info_rank0(
            "Save epoch points %s resolved to global steps %s"
            % (args.train.save_epoch_points, save_epoch_point_steps)
        )
    for epoch in range(start_epoch, args.train.num_train_epochs):
        if hasattr(train_dataloader, "set_epoch"):
            train_dataloader.set_epoch(epoch)

        logging_steps = max(1, args.train.logging_steps)
        data_loader_tqdm = trange(
            args.train.train_steps,
            desc=f"Epoch {epoch + 1}/{args.train.num_train_epochs}",
            total=args.train.train_steps,
            initial=start_step,
            disable=args.train.local_rank != 0,
        )
        pending_tqdm_updates = 0
        data_iterator = iter(train_dataloader)
        for step_idx in range(start_step, args.train.train_steps):
            global_step += 1
            pending_tqdm_updates += 1

            try:
                micro_batches: List[Dict[str, Any]] = next(data_iterator)
            except StopIteration:
                logger.info(f"epoch:{epoch} Dataloader finished with drop_last {args.data.drop_last}")
                break

            if global_step == 1:
                helper.print_example(example=micro_batches[0], rank=args.train.local_rank)

            total_loss = 0
            synchronize()
            start_time = time.time()

            micro_batches_token_num = count_loss_token(micro_batches)
            num_micro_steps = len(micro_batches)

            for micro_step, micro_batch in enumerate(micro_batches):
                if (
                    args.train.data_parallel_mode == "fsdp2"
                    and not args.train.enable_reshard_after_backward
                    and num_micro_steps > 1
                ):
                    if micro_step == 0:
                        model.set_reshard_after_backward(False)
                    elif micro_step == num_micro_steps - 1:
                        model.set_reshard_after_backward(True)
                environ_meter.add(micro_batch)
                micro_batch_token_num = count_loss_token(micro_batch)
                if args.data.enable_multisource:
                    micro_batch.pop("ds_idx", None)
                    micro_batch.pop("cur_token_num", None)
                    micro_batch.pop("source_name", None)

                micro_batch = {
                    k: v.to(get_device_type(), non_blocking=True) if isinstance(v, torch.Tensor) else v
                    for k, v in micro_batch.items()
                }
                with model_fwd_context:
                    loss = model(**micro_batch, use_cache=False).loss

                loss, _ = mean_global_loss(loss, micro_batch_token_num, micro_batches_token_num)

                with model_bwd_context:
                    loss.backward()

                total_loss += loss.item()
                del micro_batch

            grad_norm = veomni_clip_grad_norm(model, args.train.max_grad_norm)

            optimizer.step()
            lr_scheduler.step()
            optimizer.zero_grad()
            if hasattr(grad_norm, "full_tensor"):
                grad_norm = grad_norm.full_tensor().item()

            # collect mean loss across data parallel group
            total_loss, grad_norm = all_reduce((total_loss, grad_norm), group=get_parallel_state().fsdp_group)
            synchronize()
            delta_time = time.time() - start_time
            lr = max(lr_scheduler.get_last_lr())
            train_metrics = environ_meter.step(delta_time, global_step=global_step)

            should_refresh_tqdm = (
                pending_tqdm_updates >= logging_steps or global_step == 1 or (step_idx + 1) == args.train.train_steps
            )
            if should_refresh_tqdm:
                data_loader_tqdm.set_postfix_str(
                    f"loss: {total_loss:.4f}, grad_norm: {grad_norm:.4f}, lr: {lr:.2e}", refresh=False
                )
                data_loader_tqdm.update(pending_tqdm_updates)
                pending_tqdm_updates = 0

            if args.train.global_rank == 0:
                if args.train.use_wandb:
                    train_metrics.update(
                        {"training/loss": total_loss, "training/grad_norm": grad_norm, "training/lr": lr}
                    )
                    wandb.log(train_metrics, step=global_step)

            if args.train.profile_this_rank and global_step <= args.train.profile_end_step:
                profiler.step()
                if global_step == args.train.profile_end_step:
                    profiler.stop()

            should_save_by_steps = bool(args.train.save_steps and global_step % args.train.save_steps == 0)
            should_check_best = bool(args.train.save_best_steps and global_step % args.train.save_best_steps == 0)
            current_checkpoint_loss = float(total_loss)
            should_save_by_best = should_check_best and (
                best_checkpoint_loss is None or current_checkpoint_loss < best_checkpoint_loss
            )
            should_save_by_epoch_point = (
                next_save_epoch_point_idx < len(save_epoch_point_steps)
                and global_step >= save_epoch_point_steps[next_save_epoch_point_idx]
            )
            if (
                should_save_by_steps or should_save_by_epoch_point or should_save_by_best
            ) and global_step not in saved_checkpoint_steps:
                previous_best_checkpoint_step = best_checkpoint_step
                save_checkpoint_path = _save_training_checkpoint(
                    Checkpointer,
                    args,
                    model,
                    optimizer,
                    lr_scheduler,
                    train_dataloader,
                    environ_meter,
                    global_step,
                )
                saved_checkpoint_steps.add(global_step)
                last_checkpoint_step = global_step
                if should_save_by_best:
                    best_checkpoint_loss = current_checkpoint_loss
                    best_checkpoint_step = global_step

                while (
                    next_save_epoch_point_idx < len(save_epoch_point_steps)
                    and global_step >= save_epoch_point_steps[next_save_epoch_point_idx]
                ):
                    next_save_epoch_point_idx += 1
                dist.barrier()
                if (
                    args.train.global_rank == 0
                    and args.train.keep_best_and_last_checkpoints
                    and best_checkpoint_step is not None
                    and last_checkpoint_step is not None
                ):
                    _prune_step_checkpoints_except(
                        args.train.save_checkpoint_path, {best_checkpoint_step, last_checkpoint_step}
                    )
                elif (
                    args.train.global_rank == 0
                    and should_save_by_best
                    and previous_best_checkpoint_step is not None
                    and previous_best_checkpoint_step not in save_epoch_point_step_set
                    and previous_best_checkpoint_step != global_step
                ):
                    _remove_step_checkpoint(args.train.save_checkpoint_path, previous_best_checkpoint_step)
                elif args.train.global_rank == 0 and args.train.keep_last_checkpoints > 0:
                    _prune_old_step_checkpoints(args.train.save_checkpoint_path, args.train.keep_last_checkpoints)
                dist.barrier()
                logger.info_rank0(f"Distributed checkpoint saved at {save_checkpoint_path} successfully!")

        if pending_tqdm_updates > 0:
            data_loader_tqdm.update(pending_tqdm_updates)
        data_loader_tqdm.close()
        start_step = 0
        helper.print_device_mem_info(f"VRAM usage after epoch {epoch + 1}")
        if args.train.save_epochs and (epoch + 1) % args.train.save_epochs == 0 and global_step not in saved_checkpoint_steps:
            save_checkpoint_path = _save_training_checkpoint(
                Checkpointer,
                args,
                model,
                optimizer,
                lr_scheduler,
                train_dataloader,
                environ_meter,
                global_step,
            )
            saved_checkpoint_steps.add(global_step)
            last_checkpoint_step = global_step
            dist.barrier()
            if (
                args.train.global_rank == 0
                and args.train.keep_best_and_last_checkpoints
                and best_checkpoint_step is not None
                and last_checkpoint_step is not None
            ):
                _prune_step_checkpoints_except(args.train.save_checkpoint_path, {best_checkpoint_step, last_checkpoint_step})
            elif args.train.global_rank == 0 and args.train.keep_last_checkpoints > 0:
                _prune_old_step_checkpoints(args.train.save_checkpoint_path, args.train.keep_last_checkpoints)
            dist.barrier()
            logger.info_rank0(f"Distributed checkpoint saved at {save_checkpoint_path} successfully!")

    synchronize()
    # release memory
    del optimizer, lr_scheduler
    helper.empty_cache()
    # save model in huggingface's format
    if args.train.save_hf_weights and save_checkpoint_path is not None:
        hf_weights_path = os.path.join(save_checkpoint_path, "hf_ckpt")
        save_hf_safetensor(
            save_hf_safetensor_path=hf_weights_path,
            ckpt_manager=args.train.ckpt_manager,
            model_assets=model_assets,
            train_architecture=args.train.train_architecture,
            save_checkpoint_path=save_checkpoint_path,
            is_rank_0=args.train.global_rank == 0,
            model=model,
            fqn_to_index_mapping=args.model.fqn_to_index_mapping,
        )

    dist.barrier()
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
