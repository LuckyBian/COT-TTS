# Data Construction

## Overview

This directory contains data construction utilities for the COT-TTS training pipeline.

The goal of this stage is to convert raw audio and metadata into the final training format used by the model:

1. raw wav/audio paths
2. Spark BiCodec intermediate `.pt` files
3. task-level JSON / JSONL samples
4. parquet parts for efficient training

The current scripts are:

- `extract_bicodec_from_tsv.py`
- `build_asr_from_tsv.py`
- `build_tts_from_tsv.py`
- `build_one_cot_tts_sample.py`
- `jsonl_to_parquet.py`

## What To Prepare

Before constructing training data, we need the following inputs:

1. audio files
   raw wav paths that can be read by Spark-TTS `BiCodecTokenizer`
2. Spark-TTS model assets
   used to extract BiCodec representations
3. metadata JSON
   structured metadata describing history segments, target segment, reference segment, text, emotion, and COT-related fields
4. tokenizer conventions
   the final training format assumes audio ids will later be converted into special tokens such as:
   - `<|bicodec_global_xxx|>`
   - `<|bicodec_semantic_xxx|>`

For COT-TTS specifically, the key metadata units are:

- `dialog_segments`
- `target_segment`
- `target_segment.ref_segment_id`
- `target_segment.text`
- optional fields such as `emotion_tag`, `features`, `cot_text`

## Audio Codec Preparation

The first step is extracting audio codec tensors from wav files.

Script:

- `extract_bicodec_from_tsv.py`

This script:

1. reads a TSV file containing audio paths
2. runs Spark-TTS `BiCodecTokenizer` on each wav
3. saves the extracted codec tensors as `.pt` files

Each saved `.pt` file contains:

- `semantic_tgt`: target semantic codec sequence
- `global_tgt`: target global codec sequence
- `global_ref`: reference-style global codec sequence extracted from the first half of the same audio

These `.pt` files are the intermediate representation used later when building training samples.

Expected TSV format:

```tsv
path
/path/to/sample_0001.wav
/path/to/sample_0002.wav
```

## Target JSON Structure

After metadata and codec files are ready, the final training sample should be organized into the unified JSON structure below:

```json
{
  "index": "sample_id",
  "source_name": "cot-tts",
  "messages": [
    {
      "role": "user",
      "content": "<bos><task_start>...<task_end>...",
      "loss_mask": 0
    },
    {
      "role": "assistant",
      "content": "<under_start>...<under_end><cot_start>...<cot_end><audio_tar_start>...<audio_tar_end><output_end><eos>",
      "loss_mask": 1
    }
  ],
  "meta": {
    "movie_id": "...",
    "history_segment_ids": ["...", "..."],
    "target_segment_id": "...",
    "ref_segment_id": "..."
  }
}
```

The training side mainly consumes:

- `index`
- `source_name`
- `messages`
- `meta`

## ASR Example

We also keep a minimal ASR builder based on the unified template.

Script:

- `build_asr_from_tsv.py`

Input expectation:

- a TSV with at least:
  - `path`
  - `text`
- a codec directory containing:
  - `<utt_id>.pt`

For the ASR task, we use the structure:

```text
<bos>
<task_start>aaa<task_end>
<history_start>
<audio_his_start>ccc<audio_his_end>
<history_end>
<target_start>
<audio_tar_start>hhh<audio_tar_end>
<audio_ref_start>fff<audio_ref_end>
<target_end>
<output_start>
<under_start>iii<under_end>
<cot_start>ggg<cot_end>
<text_start>ddd<text_end>
<output_end>
<eos>
```

In this ASR version:

- `aaa`: has value, usually `ASR`
- `hhh`: has value, built from target audio codec tokens
- `ddd`: has value, built from transcript text
- `ccc`, `fff`, `iii`, `ggg`: kept empty

## TTS Example

We also keep a minimal TTS builder based on the unified template.

Script:

- `build_tts_from_tsv.py`

Input expectation:

- a TSV with at least:
  - `path`
  - `text`
  - `ref_path`
- a codec directory containing:
  - `<utt_id>.pt`

For the TTS task, we use the structure:

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

In this TTS version:

- `aaa`: has value, usually `TTS`
- `ddd`: has value, built from input text
- `fff`: has value, built from reference audio `global` tokens only
- `hhh`: has value, built from target audio `global + semantic` tokens
- `ccc`, `iii`, `ggg`: kept empty

## COT-TTS Example

We use COT-TTS as the demonstration task for data construction.

Script:

- `build_one_cot_tts_sample.py`

This script shows how to construct one sample from:

- one metadata file
- one `spark_codec` directory

The construction logic is:

1. read one metadata sample containing:
   - `dialog_segments`
   - `target_segment`
2. load codec `.pt` files for:
   - history segments
   - target segment
   - optional reference segment
3. convert codec tensors into token strings
4. assemble the final `messages` structure

For COT-TTS, the audio fields are built as follows:

- `audio_his`
  - first history segment: `global + semantic`
  - later history segments: `semantic only`
- `audio_ref`
  - `global only`
- `audio_tar`
  - `global + semantic`

The text fields are built as follows:

- `text_start ... text_end`
  target text from `target_segment.text`
- `under_start ... under_end`
  summarized from history text and emotion tags
- `cot_start ... cot_end`
  preferably from `target_segment.cot_text`, or from fallback metadata fields

This gives us one complete training sample in the same format that later full-dataset builders will use.

## JSONL To Parquet

After JSON / JSONL samples are ready, the final step is converting them into parquet parts for efficient training.

Script:

- `jsonl_to_parquet.py`

This script:

1. reads JSONL training samples
2. normalizes `messages` and `meta`
3. writes chunked parquet files such as:
   - `part-00000.parquet`
   - `part-00001.parquet`

Supported features:

- chunked writing
- resume from existing parquet parts
- overwrite existing parquet output
- configurable compression

This is the final storage format recommended for large-scale training.

## Minimal Pipeline

The current minimal pipeline in this directory is:

1. `extract_bicodec_from_tsv.py`
   extract Spark BiCodec tensors from wav files
2. `build_asr_from_tsv.py`
   build ASR training samples from TSV(path,text) + codec files
3. `build_tts_from_tsv.py`
   build TTS training samples from TSV(path,text,ref_path) + codec files
4. `build_one_cot_tts_sample.py`
   build one example COT-TTS training sample from metadata + codec files
5. `jsonl_to_parquet.py`
   convert JSONL training data into parquet parts for efficient loading
