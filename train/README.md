# COTalker 1.7B Training

## Overview

This project contains the training code for the three-stage COTalker 1.7B setup.  
The model takes:

- historical dialogue audio
- target text
- reference audio

and is trained to:

- explicitly generate intermediate chain-of-thought style speaking-manner reasoning
- generate target speech with the desired speaker timbre and context-appropriate expression

The full training pipeline is divided into three stages:

1. Stage 1: `ASR` and `TTS` only
2. Stage 2: all tasks
3. Stage 3: `COT-TTS` only

This directory only includes the code required for training. Large model weights, audio codec extraction outputs, parquet datasets, and intermediate checkpoints are not included.

## Model Download

Qwen3 1.7B base model:

- https://huggingface.co/Qwen/Qwen3-1.7B

The default location is:

```text
models/Qwen3-1.7B
```

## Audio Codec Extraction

Audio codec extraction is based on Spark-TTS:

- https://github.com/SparkAudio/Spark-TTS

You should first use Spark-TTS to extract audio codec representations, then organize them into the training data format described below.  
This repository assumes the codec tokens and special-token system have already been prepared.

## Data Format

Before training, samples should be organized into the following sequence formats and then converted into `parquet` files for training.

### ASR

```text
<bos>
<task_start>ASR<task_end>
<history_start>
<audio_his_start><audio_his_end>
<history_end>
<target_start>
<audio_tar_start>
<global_0001> ... <global_0032>
<semantic_0001> ... <semantic_0168>
<audio_tar_end>
<audio_ref_start><audio_ref_end>
<target_end>
<output_start>
<under_start><under_end>
<cot_start><cot_end>
<text_start>
Hello World.
<text_end>
<output_end>
<eos>
```

### TTS

```text
<bos>
<task_start>TTS<task_end>
<history_start>
<audio_his_start><audio_his_end>
<history_end>
<target_start>
<text_start>
Hello World.
<text_end>
<audio_ref_start>
<global_0001> ... <global_0032>
<audio_ref_end>
<target_end>
<output_start>
<under_start><under_end>
<cot_start><cot_end>
<audio_tar_start>
<global_0001> ... <global_0032>
<semantic_0001> ... <semantic_0168>
<audio_tar_end>
<output_end>
<eos>
```

### COT-TTS

```text
<bos>
<task_start>COT-TTS<task_end>
<history_start>
<audio_his_start>
<global_0001> ... <global_0032>
<semantic_0001> ... <semantic_0145>
<audio_his_end>
<history_end>
<target_start>
<text_start>
Hello World.
<text_end>
<audio_ref_start>
<global_0001> ... <global_0032>
<audio_ref_end>
<target_end>
<output_start>
<under_start>
Speaker-0:xxxx[emo]
<under_end>
<cot_start>
Analysis text
<cot_end>
<audio_tar_start>
<global_0001> ... <global_0032>
<semantic_0001> ... <semantic_0168>
<audio_tar_end>
<output_end>
<eos>
```

### Features

```text
<bos>
<task_start>Features<task_end>
<history_start>
<audio_his_start><audio_his_end>
<history_end>
<target_start>
<audio_tar_start>
<global_0001> ... <global_0032>
<semantic_0001> ... <semantic_0168>
<audio_tar_end>
<audio_ref_start><audio_ref_end>
<target_end>
<output_start>
<under_start><under_end>
<cot_start>Duration: 3.12s<cot_end>
<output_end>
<eos>
```

### Spk-Clone

```text
<bos>
<task_start>Spk-Clone<task_end>
<history_start>
<audio_his_start><audio_his_end>
<history_end>
<target_start>
<text_start><text_end>
<audio_ref_start><global_0001>...<audio_ref_end>
<cot_start>Analysis text<cot_end>
<target_end>
<output_start>
<under_start><under_end>
<audio_tar_start><global_0001>...<audio_tar_end>
<output_end>
<eos>
```

### Dia

```text
<bos>
<task_start>Dia<task_end>
<history_start>
<audio_his_start>
<global_0001> ... <global_0032>
<semantic_0001> ... <semantic_0145>
<audio_his_end>
<history_end>
<target_start>
<text_start><text_end>
<audio_ref_start><audio_ref_end>
<target_end>
<output_start>
<under_start>Speaker-0: xxxxxx[emo]...<under_end>
<cot_start><cot_end>
<audio_tar_start><audio_tar_end>
<output_end>
<eos>
```

### InsTTS

```text
<bos>
<task_start>InsTTS<task_end>
<history_start>
<audio_his_start><audio_his_end>
<history_end>
<target_start>
<text_start>Hello World.<text_end>
<audio_ref_start><global_0001>...<audio_ref_end>
<cot_start>Analysis text<cot_end>
<target_end>
<output_start>
<under_start><under_end>
<audio_tar_start>
<global_0001> ... <global_0032>
<semantic_0001> ... <semantic_0168>
<audio_tar_end>
<output_end>
<eos>
```

The default dataset layout is:

```text
data/stage1/parquet
data/stage2/parquet
data/stage3/parquet
```

The three training stages use data as follows:

1. `stage1`: `ASR` and `TTS` only
2. `stage2`: all tasks
3. `stage3`: `COT-TTS` only

If your current data is still in raw json / jsonl / metadata format, you should first build samples following the templates above, then convert them into `parquet`.

## Environment

You can use the environment files included in this directory.

### Option 1

```bash
bash create_env.sh
```

### Option 2

```bash
conda env create -f environment.yml
conda activate veomni-infer
pip install -r requirements.lock.txt
```

## Training Commands

The following commands assume you are running them from the `train-upload` root directory.

### Stage 1

```bash
bash scripts/train_stage1.sh
```

### Stage 2

```bash
INIT_CKPT=checkpoints/stage1/global_step_xxxxx \
TRAIN_PATH=data/stage2/parquet \
bash scripts/train_stage2.sh
```

### Stage 3

```bash
INIT_CKPT=checkpoints/stage2/global_step_xxxxx \
TRAIN_PATH=data/stage3/parquet \
bash scripts/train_stage3.sh
```