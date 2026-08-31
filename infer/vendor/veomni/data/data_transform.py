# Copyright 2025 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Union

import torch

from veomni.data.constants import IGNORE_INDEX


if TYPE_CHECKING:
    from transformers import PreTrainedTokenizer

    from .chat_template import ChatTemplate


def split_into_chunks(sequence: Sequence[int], chunk_size: int) -> List[List[int]]:
    """
    Splits a long sequence into chunks.
    """
    total_len = len(sequence)
    chunks = []
    for i in range(0, total_len, chunk_size):
        chunks.append(sequence[i : i + chunk_size])

    return chunks


def process_pretrain_example(
    example: Dict[str, Any],
    tokenizer: "PreTrainedTokenizer",
    max_seq_len: int,
    text_keys: Union[str, List[str]] = "content_split",
    source_name: Optional[str] = None,
) -> List[Dict[str, "torch.Tensor"]]:
    examples = []
    if isinstance(text_keys, str):
        text_example = example[text_keys]
    elif isinstance(text_keys, list):
        for key in text_keys:
            if key in example:
                text_example = example[key]
                break
        else:
            raise ValueError(f"None of the keys {text_keys} are found in the example.")
    else:
        raise ValueError(f"text_keys must be a string or a list of strings, but got {type(text_keys)}")

    tokens = tokenizer.encode(text_example, add_special_tokens=False) + [tokenizer.eos_token_id]
    for input_ids in split_into_chunks(tokens, max_seq_len):
        examples.append(
            {
                "input_ids": torch.tensor(input_ids),
                "attention_mask": torch.tensor([1] * len(input_ids)),
                "labels": torch.tensor(input_ids),
            }
        )

    return examples


def process_sft_example(
    example: Dict[str, Any],
    chat_template: "ChatTemplate",
    max_seq_len: int,
    text_keys: Union[str, List[str]] = "messages",
    source_name: Optional[str] = None,
    audio_his_drop_prob: float = 0.0,
    audio_his_drop_ratio_max: float = 0.0,
    audio_his_drop_skip_prefix_tokens: int = 0,
) -> List[Dict[str, "torch.Tensor"]]:
    if isinstance(text_keys, str):
        text_example = example[text_keys]
    elif isinstance(text_keys, list):
        for key in text_keys:
            if key in example:
                text_example = example[key]
                break
        else:
            raise ValueError(f"None of the keys {text_keys} are found in the example.")
    else:
        raise ValueError(f"text_keys must be a string or a list of strings, but got {type(text_keys)}")

    tokenized_example = chat_template.encode_messages(text_example, max_seq_len=max_seq_len)
    if audio_his_drop_prob > 0 and audio_his_drop_ratio_max > 0:
        _drop_audio_history_span(
            tokenized_example,
            chat_template.tokenizer,
            drop_prob=audio_his_drop_prob,
            ratio_max=audio_his_drop_ratio_max,
            skip_prefix_tokens=audio_his_drop_skip_prefix_tokens,
        )
    tokenized_example = {k: torch.tensor(v) for k, v in tokenized_example.items()}
    return [tokenized_example]


def _encode_single_token(tokenizer: "PreTrainedTokenizer", token: str) -> Optional[int]:
    token_id = tokenizer.convert_tokens_to_ids(token)
    if token_id is not None and token_id != getattr(tokenizer, "unk_token_id", None):
        return int(token_id)

    token_ids = tokenizer.encode(token, add_special_tokens=False)
    if len(token_ids) == 1:
        return int(token_ids[0])
    return None


def _drop_audio_history_span(
    tokenized_example: Dict[str, List[int]],
    tokenizer: "PreTrainedTokenizer",
    drop_prob: float,
    ratio_max: float,
    skip_prefix_tokens: int = 0,
) -> None:
    input_ids = tokenized_example.get("input_ids")
    if not input_ids:
        return

    start_id = _encode_single_token(tokenizer, "<audio_his_start>")
    end_id = _encode_single_token(tokenizer, "<audio_his_end>")
    if start_id is None or end_id is None:
        return

    search_from = 0
    while True:
        try:
            start_pos = input_ids.index(start_id, search_from)
            end_pos = input_ids.index(end_id, start_pos + 1)
        except ValueError:
            break

        content_start = start_pos + 1
        drop_start = min(content_start + max(0, skip_prefix_tokens), end_pos)
        content_len = end_pos - drop_start
        drop_len = 0
        if content_len > 0 and random.random() < drop_prob:
            ratio = random.uniform(0.0, min(1.0, ratio_max))
            drop_len = min(int(round(content_len * ratio)), content_len)

        if drop_len > 0:
            span_start = random.randint(drop_start, end_pos - drop_len)
            span_end = span_start + drop_len
            for key in ("input_ids", "attention_mask", "labels"):
                values = tokenized_example.get(key)
                if values is not None:
                    del values[span_start:span_end]
            search_from = end_pos - drop_len + 1
        else:
            search_from = end_pos + 1


def process_classification_example(
    example: dict[str, Any],
    tokenizer: "PreTrainedTokenizer",
    max_seq_len: int,
    text_keys: Union[str, list[str]] = "text",
    label_key: str = "label",
) -> list[dict[str, "torch.Tensor"]]:
    """
    Convert a single raw example into one classification training sample.

    Args:
        example:
            A single record from the dataset. Expected format (minimal):
                {
                    "<text_key>":  str,   # e.g. news article / sentence
                    "<label_key>": int,   # e.g. 0..(num_labels-1)
                    ...                   # other fields are ignored
                }
            By default:
                text_key  = "text"
                label_key = "label"

        tokenizer:
            A HuggingFace tokenizer used to tokenize the input text.

        max_seq_len:
            Maximum sequence length (in tokens). Text longer than this
            will be truncated to the first `max_seq_len` tokens.

        text_key:
            Key in `example` that contains the raw input text.

        label_key:
            Key in `example` that contains the class id. The value should be int-like.

    Returns:
        A list with exactly one sample dict:
            {
                "input_ids":      LongTensor[L],
                "attention_mask": LongTensor[L],
                "labels":         LongTensor[L],
                "position_ids":   LongTensor[L]
            }
    """
    # 1) text
    if isinstance(text_keys, str):
        text = example[text_keys]
    elif isinstance(text_keys, list):
        for key in text_keys:
            if key in example:
                text = example[key]
                break
        else:
            raise ValueError(f"None of the keys {text_keys} are found in the example.")
    else:
        raise ValueError(f"text_keys must be a string or a list of strings, but got {type(text_keys)}")

    # 2) label
    if label_key not in example:
        raise ValueError(f"Missing label key '{label_key}' in example.")
    try:
        label_val = int(example[label_key])
    except Exception as e:
        raise ValueError(f"Label '{example[label_key]}' is not an int-like value.") from e

    # 3) tokenize
    tokens: list[int] = tokenizer.encode(text, add_special_tokens=True)

    # 4) build samples
    examples: list[dict[str, torch.Tensor]] = []

    def build_sample(seq: list[int]) -> dict[str, "torch.Tensor"]:
        L = len(seq)
        token_labels = torch.full((L,), IGNORE_INDEX, dtype=torch.long)
        token_labels[L - 1] = label_val

        sample: dict[str, torch.Tensor] = {
            "input_ids": torch.tensor(seq, dtype=torch.long),
            "attention_mask": torch.ones(len(seq), dtype=torch.long),
            "labels": token_labels,
        }
        sample["position_ids"] = torch.arange(len(seq), dtype=torch.long)
        return sample

    if len(tokens) > max_seq_len:
        tokens = tokens[:max_seq_len]

    examples.append(build_sample(tokens))
    return examples
