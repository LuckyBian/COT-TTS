# Audio Data Pipeline

This repository contains an audio annotation pipeline for speaker diarization, ASR, segment cutting, denoising, emotion/audio-feature annotation, scene splitting, scene-local speaker normalization, and COT annotation.

Large model files and generated data are not included. Put input audio under `data/audios/`, download the required models into `model/`, then run the commands below from the repository root.

## Environments

The included `environment.yml` is for the first stage and lightweight post-processing:

```bash
conda env create -f environment.yml
conda activate whisper_newarch
```

Some optional stages use external open-source projects and may need their own environments:

| Stage | Environment / project reference |
| --- | --- |
| FRCRN denoising | FRCRN / ModelScope `speech_frcrn_ans_cirm_16k` |
| emotion2vec | FunASR / ModelScope `emotion2vec_plus_large` |
| DNSMOS | DNSMOSPro / NISQA checkpoint |
| UTMOSv2 | UTMOSv2 project |
| scene split and COT | DeepSeek-R1-Distill-Qwen + vLLM |

## Model Paths

Download open-source models and place them at these relative paths:

| Purpose | Model | Path |
| --- | --- | --- |
| ASR | Whisper large-v3 | `model/whisper-large-v3/large-v3.pt` |
| diarization segmentation | pyannote segmentation 3.0 | `model/pytorch_model_segmentation-3.0.bin` |
| speaker embedding | pyannote / wespeaker embedding | `model/pyannote_model_wespeaker-voxceleb-resnet34-LM.bin` |
| denoising | FRCRN / ModelScope `speech_frcrn_ans_cirm_16k` | `model/frcrn/` |
| emotion | FunASR `emotion2vec_plus_large` | `model/emotion2vec_plus_large/` |
| expressive intensity | wav2vec2 MSP emotion regression | `model/wav2vec2-large-robust-12-ft-emotion-msp-dim/` |
| noise score | DNSMOSPro NISQA | `model/dnsmospro/NISQA/model_best.pt` |
| naturalness score | UTMOSv2 fold checkpoints | `model/utmosv2/` |
| LLM | DeepSeek-R1-Distill-Qwen-14B | `model/deepseek/DeepSeek-R1-Distill-Qwen-14B/` |

`model/config.yaml` is generated automatically by `modules/models/stt/Whisper.py`.

## Input

Put audio files in:

```text
data/audios/
```

Generate the audio list:

```bash
python get_audio_list.py
```

This creates `data/audio_list.tsv`; each line is a relative audio path such as `data/audios/example.wav`.

## Pipeline

### 1. Diarization + ASR

This stage uses pyannote and Whisper only. It does not run BEATs, emotion models, punctuation models, DDC, or any LLM.

```bash
python modules/models/stt/Whisper.py \
  --tsv_path data/audio_list.tsv \
  --output_dir test/json \
  --num_workers 1
```

Output: `test/json/<audio_name>.json`

Each segment contains `start`, `end`, `text`, `speaker`, `lang`, and `segment_id`.

### 2. Normalize JSON

```bash
python post_processing/summ_json.py \
  --input-dir test/json \
  --output-dir test/json_all
```

Output: `test/json_all/<audio_name>.json`

The normalized JSON keeps one file per input audio and uses a `segment` list.

### 3. Cut Segment Audio

```bash
python get_audio.py \
  --audio-dir data/audios \
  --json-dir test/json_all \
  --segment-dir test/segment \
  --num-workers 1
```

Output: `test/segment/<segment_id>.wav`

### 4. FRCRN Denoising

Prepare the TSV:

```bash
python post_processing/prepare_frcrn_tsv.py \
  --input-dir test/segment \
  --output-tsv test/frcrn/segment.tsv
```

The TSV stores paths relative to `test/frcrn/` by default. Use `--absolute` only if your FRCRN environment requires absolute paths.

Run denoising in the FRCRN environment:

```bash
python post_processing/frcrn_denoise.py \
  --tsv test/frcrn/segment.tsv \
  --out-dir test/segment_denoised \
  --model model/frcrn \
  --gpus 0 \
  --workers-per-gpu 1
```

Output: `test/segment_denoised/<segment_id>.wav`

### 5. Emotion Tags

Generate labels:

```bash
python post_processing/ser.py \
  --input-dir test/segment_denoised \
  --output-dir test/emotion \
  --model model/emotion2vec_plus_large \
  --device cuda:0 \
  --batch-size 64
```

Write labels back to JSON:

```bash
python post_processing/add_emo_tag.py \
  --input-dir test/json_all \
  --emotion-dir test/emotion \
  --output-dir test/json_all_emo
```

Output: `test/json_all_emo/<audio_name>.json`

Each segment gets `emo-tag`.

### 6. Audio Features and Scores

Prepare a shared TSV:

```bash
python post_processing/prepare_metric_tsv.py \
  --input-dir test/segment_denoised \
  --output-tsv test/metrics/segments.tsv
```

The TSV stores relative paths by default. Use `--absolute` only when needed.

Extract duration, active duration, loudness, and expressive intensity:

```bash
python post_processing/audio_features.py \
  --input-tsv test/metrics/segments.tsv \
  --output-tsv test/metrics/audio_features.tsv \
  --model-dir model/wav2vec2-large-robust-12-ft-emotion-msp-dim \
  --device cuda:0
```

Compute DNSMOS:

```bash
python post_processing/dnsmos_score.py \
  --input-tsv test/metrics/segments.tsv \
  --output-tsv test/metrics/dnsmos.tsv \
  --model-path model/dnsmospro/NISQA/model_best.pt \
  --device cuda:0
```

Compute UTMOSv2:

```bash
python post_processing/utmosv2_score.py \
  --input-tsv test/metrics/segments.tsv \
  --output-tsv test/metrics/utmosv2.tsv \
  --model-dir model/utmosv2 \
  --folds 0,1,2,3,4 \
  --device cuda:0
```

If UTMOSv2 is used from source instead of installed as a package, add its source directory to `PYTHONPATH` first.

Merge features and scores into JSON:

```bash
python post_processing/add_audio_features.py \
  --input-dir test/json_all_emo \
  --output-dir test/json_all_audio_features \
  --features-tsv test/metrics/audio_features.tsv \
  --dnsmos-tsv test/metrics/dnsmos.tsv \
  --utmosv2-tsv test/metrics/utmosv2.tsv
```

Each segment gets `audio_features.duration`, `audio_features.active_duration`, `audio_features.loudness`, `audio_features.expressive_intensity`, `audio_features.naturalness score`, and `audio_features.noise score`.

### 7. Reference Segment

For each segment, find another segment from the same speaker with different text. If none exists, the segment references itself.

```bash
python post_processing/add_reference_segment.py \
  --input-dir test/json_all_audio_features \
  --output-dir test/json_all_reference
```

Each segment gets `reference_segment_id`.

### 8. Scene Split

This stage first makes coarse cuts by time gaps, then uses DeepSeek/vLLM for fine cuts on longer audio. Short audio under `--short-audio-seconds` is assigned one scene without loading the LLM.

```bash
python post_processing/cut.py \
  --input-dir test/json_all_reference \
  --output-dir test/json_all_scenes \
  --model-path model/deepseek/DeepSeek-R1-Distill-Qwen-14B \
  --cuda-visible-devices 0,1,2,3 \
  --tensor-parallel-size 4
```

Each segment gets `scene_index`.

### 9. Scene-Local Speaker Normalization

Normalize speaker labels independently inside each scene, starting from `Speaker-0`.

```bash
python post_processing/normalize_scene_speakers.py \
  --input-dir test/json_all_scenes \
  --output-dir test/json_all_scene_speakers
```

For example, speakers `Speaker-23`, `Speaker-14`, and `Speaker-5` in the same scene become `Speaker-0`, `Speaker-1`, and `Speaker-2`. The original label is kept in `original_speaker` by default. Add `--no-keep-original` to skip that field.

### 10. COT Annotation

Generate COT annotations using text, `emo-tag`, scene context, and `audio_features`.

```bash
python post_processing/cot_with_audio_features_vllm.py
```

Default paths:

```text
input:  test/json_all_scene_speakers/*.json
output: test/json_all_cot/
```

Useful environment variables:

```bash
export DEEPSEEK_MODEL_PATH=model/deepseek/DeepSeek-R1-Distill-Qwen-14B
export DEEPSEEK_CUDA_VISIBLE_DEVICES=0,1,2,3
export DEEPSEEK_TP_SIZE=4
export DEEPSEEK_PROMPT_BATCH_SIZE=4
```

Each segment gets `cot` and `summ`, and `emo-tag` is updated to the LLM-generated Chinese short tag.

## Output Folders

All generated outputs are written under `test/` and ignored by Git:

| Folder | Content |
| --- | --- |
| `test/json/` | diarization + ASR JSON |
| `test/json_all/` | normalized JSON |
| `test/segment/` | raw audio segments |
| `test/segment_denoised/` | denoised segments |
| `test/emotion/` | emotion label files |
| `test/metrics/` | audio feature / DNSMOS / UTMOS TSV files |
| `test/json_all_emo/` | JSON with `emo-tag` |
| `test/json_all_audio_features/` | JSON with audio features and scores |
| `test/json_all_reference/` | JSON with reference segment IDs |
| `test/json_all_scenes/` | JSON with `scene_index` |
| `test/json_all_scene_speakers/` | JSON with scene-local speaker labels |
| `test/json_all_cot/` | JSON with COT annotations |

## Notes

- The repository is designed to be uploaded without model weights or generated test outputs.
- All default paths are relative to the repository root.
- The diarization stage uses local pyannote/audio and wespeaker-style model files, not an online service.
- Tensor parallel size for DeepSeek/vLLM must be compatible with the model. For Qwen-based 14B models, `--tensor-parallel-size 4` is a typical choice.
