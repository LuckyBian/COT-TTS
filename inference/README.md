# Inference

Self-contained COTalker 1.7B inference bundle for context-aware reasoning speech generation. Given historical dialogue audio, target text, and reference speech, the model explicitly reasons about the intended speaking manner and generates contextually appropriate speech with the target speaker timbre. The intermediate chain-of-thought analysis can also be inspected and edited before waveform generation.

## Input / Output

Inputs:

- History dialogue audio: `--history_audio_path`
- Reference audio: `--ref_audio_path`
- Target text: `--text` or `--text_path`

Outputs:

- Generated COT analysis text: `--save_cot_path`
- Generated audio: `--save_wav_path`
- Optional manual COT editing before audio generation: `--edit_cot`

Example input mode:

- one history audio file
- one reference audio file
- one target sentence or one target text file

## Download

Before inference, prepare the following:

1. VeOmni 1.7B HF checkpoint
   Link: `https://drive.google.com/file/d/1WEUuQJtC91LX3eJwjIas7gi2RUxjWiIU/view?usp=sharing`
   Place it at:
   - `models/hf_ckpt`

2. Spark-TTS model files
   Link: `https://drive.google.com/file/d/1dvVt2KX2Uat82dhmwuYippkpJnC7NewV/view?usp=sharing`
   Place them at:
   - `models/spark_tts`

3. Spark-TTS codebase
   This bundle already includes:
   - `Spark-TTS/`

   If needed, you can replace it with the official repo:

```bash
git clone https://github.com/SparkAudio/Spark-TTS.git
```

## Environment Setup

This bundle was built from a Python `venv`, not a conda env.

Recommended way:

```bash
cd infer-upload
bash create_env.sh
source .venv/bin/activate
```

Alternative conda/mamba way:

```bash
conda env create -f environment.yml
conda activate veomni-infer
pip install -r requirements.lock.txt
```

Environment notes:

- The default `--attn_implementation` is `eager` for better portability.
- If someone has a compatible machine and wants faster attention, they can install a matching `flash-attn` and run with `--attn_implementation flash_attention_2`.
- The local repo copy of `veomni/` is used directly by `infer.py`, so no editable `veomni` install is required.

## Inference

Standard inference:

```bash
python infer.py \
  --device cuda:0 \
  --history_audio_path /path/to/his.wav \
  --ref_audio_path /path/to/ref.wav \
  --text_path /path/to/text.txt \
  --save_wav_path ./output/sample.wav \
  --save_cot_path ./output/sample.cot.txt \
  --temperature 0.6 \
  --top_p 0.8 \
  --expressive_intensity 0.85 \
  --naturalness_score 4.0 \
  --noise_score 4.5 \
  --global_source ref \
  --do_sample
```

Editable COT inference:

```bash
python infer.py \
  --device cuda:0 \
  --history_audio_path /path/to/his.wav \
  --ref_audio_path /path/to/ref.wav \
  --text_path /path/to/text.txt \
  --save_wav_path ./output/sample.wav \
  --save_cot_path ./output/sample.cot.txt \
  --temperature 0.6 \
  --top_p 0.8 \
  --expressive_intensity 0.85 \
  --naturalness_score 4.0 \
  --noise_score 4.5 \
  --global_source ref \
  --edit_cot \
  --do_sample
```
