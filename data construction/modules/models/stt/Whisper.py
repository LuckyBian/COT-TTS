import os
import sys
from typing import Optional, Union, List, Dict
from types import SimpleNamespace
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
import logging
import threading
from pathlib import Path
import ffmpeg
import librosa
import numpy as np
import torch
from whisper import audio
from modules import config as global_config
from modules.models.stt.STTModel import STTModel, TranscribeResult
from modules.models.stt.STTModel import NP_AUDIO
from modules.models.stt.diarization import PostProcessor
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import webrtcvad
import yaml
from pyannote.audio import Pipeline
import tempfile
from scipy.io import wavfile
import whisper


def analyze_segment(segment_info, transcribe_result):
    segment_start = segment_info['start']
    segment_end = segment_info['end']

    return {
        'start': segment_start,
        'end': segment_end,
        'text': transcribe_result.text,
        'speaker': segment_info['speaker'],
        'lang': transcribe_result.lang,
        'segment_id': segment_info['segment_id']
    }


def build_output_payload(segments: List[Dict], sample_rate: int) -> Dict:
    languages = sorted({seg.get("lang") for seg in segments if seg.get("lang")})
    num_speakers = len({seg.get("speaker") for seg in segments if seg.get("speaker")})
    return {
        "segments": segments,
        "num_speakers": num_speakers,
        "languages": languages,
        "meta": {
            "rtf_hint": None,
            "sample_rate": sample_rate
        }
    }

def resample_audio_to_array(input_file, sample_rate=16000, channels=1):
    try:
        # Probe the input file to get audio metadata
        probe = ffmpeg.probe(input_file)
        audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
        if not audio_streams:
            raise ValueError(f"No audio stream found in file '{input_file}'")
        original_channels = int(audio_streams[0]['channels'])
        # Run ffmpeg and pipe the output as raw audio
        process = (
            ffmpeg
            .input(input_file)
            .output(
                'pipe:',           # Send output to stdout
                format='f32le',    # 32-bit float PCM
                ar=sample_rate,    # Resample to desired sample rate
                ac=original_channels  # Use original number of channels
            )
            .run(capture_stdout=True, capture_stderr=True)
        )
        # Decode the raw audio data to a NumPy array
        audio_data = np.frombuffer(process[0], dtype=np.float32)
        if original_channels > 1:
            audio_data = audio_data.reshape(-1, original_channels)
        return sample_rate, audio_data

    except ffmpeg.Error as e:
        #error message from FFmpeg stderr
        error_message = e.stderr.decode('utf-8')
        raise ValueError(f"Error processing file '{input_file}': {error_message}")

class WhisperModel(STTModel):
    SAMPLE_RATE = audio.SAMPLE_RATE

    lock = threading.Lock()

    logger = logging.getLogger(__name__)

    model: Optional[object] = None

    def __init__(self, flag_diarize=True, model_type=0):
        start_time = time.time()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.dtype = 'float16'

        self.whisper_model = whisper.load_model(global_config.whisper_path, device=self.device)

        self.spk_num_path = global_config.spk_num_path
        self.embedding_path = global_config.embedding_path

        self.segmentation_path = global_config.segmentation_path

        if not hasattr(global_config, 'max_utt_count') or global_config.max_utt_count is None:
            self.max_utt_count = 11
        else:
            self.max_utt_count = global_config.max_utt_count

        self.flag_diarize = flag_diarize

        self.generate_yaml(self.spk_num_path, self.embedding_path, self.segmentation_path)
         
        self.pipeline = Pipeline.from_pretrained(self.spk_num_path)
        self.pipeline.to(torch.device(self.device))

        self.post_diarization = PostProcessor(
            embedding_model=self.embedding_path,
            similarity_threshold=0.7,
            device=self.device
        )

        self.logger.info(f'init model takes: {time.time()-start_time:.2f}s')

    def generate_yaml(self, spk_num_path, embedding_path, segmentation_path):
        config = {
            'version': '3.1.0',
            'pipeline': {
                'name': 'pyannote.audio.pipelines.SpeakerDiarization',
                'params': {
                    'clustering': 'AgglomerativeClustering',
                    'embedding': embedding_path,
                    'embedding_batch_size': 32,
                    'embedding_exclude_overlap': True,
                    'segmentation': segmentation_path,
                    'segmentation_batch_size': 32,
                }
            },
            'params': {
                'clustering': {
                    'method': 'centroid',
                    'min_cluster_size': 12,
                    'threshold': 0.7045654963945799,
                },
                'segmentation': {
                    'min_duration_off': 0.0
                }
            }
        }
        with open(spk_num_path, 'w') as yaml_file:
            yaml.dump(config, yaml_file, default_flow_style=False)

    def resample_audio(self, audio: NP_AUDIO):
        sr, data = audio
        if sr == self.SAMPLE_RATE:
            return sr, data
        data = librosa.resample(data, orig_sr=sr, target_sr=self.SAMPLE_RATE)
        return self.SAMPLE_RATE, data

    def ensure_float32(self, audio: NP_AUDIO):
        sr, data = audio
        if data.dtype == np.int16:
            data = data.astype(np.float32)
            data /= np.iinfo(np.int16).max
        elif data.dtype == np.int32:
            data = data.astype(np.float32)
            data /= np.iinfo(np.int32).max
        elif data.dtype == np.float64:
            data = data.astype(np.float32)
        elif data.dtype == np.float32:
            pass
        else:
            raise ValueError(f"Unsupported data type: {data.dtype}")

        return sr, data

    def ensure_stereo_to_mono(self, audio: NP_AUDIO):
        sr, data = audio
        if data.ndim == 2:
            data = data.mean(axis=1)
        return sr, data

    def normalize_audio(self, audio: NP_AUDIO):
        audio = self.ensure_float32(audio=audio)
        audio = self.resample_audio(audio=audio)
        audio = self.ensure_stereo_to_mono(audio=audio)
        return audio

    def diarize_then_transcribe(
        self,
        audio: NP_AUDIO,
        speaker_embeddings: Dict = None,
        flag_format=False,
        context_txts: List[str] = None,
        output_json_path: Optional[Union[str, Path]] = None,
        save_one_spk: bool = False
    ) -> TranscribeResult:
        total_start_time = time.time()
        
        # 1. 音频预处理
        if isinstance(audio, str) or isinstance(audio, Path):
            audio_path = str(audio)
            try:
                audio = resample_audio_to_array(audio, sample_rate=16000)
                self.logger.info(f'load audio file cost {time.time()-total_start_time:.2f}s')
            except ValueError as e:
                self.logger.info(f"resample audio error: {e}")
                return [], []

        # 如果输入是音频数据，需要先保存为临时文件供pyannote使用
        _, audio_data = self.normalize_audio(audio=audio)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            audio_path = temp_file.name
            # 转换为int16并写入wav文件
            audio_int16 = (audio_data * 32767).astype(np.int16)
            wavfile.write(audio_path, self.SAMPLE_RATE, audio_int16)
        
        # 2. 使用pyannote进行说话人分离
        self.logger.info("Start diarization using pyannote...")
        diarization_start_time = time.time()        
        diarization = self.pipeline(audio_path)        
        self.logger.info(f"Diarization done, cost: {time.time() - diarization_start_time:.2f}s")
        
        # 3. 基于分离结果进行转录
        transcribe_start_time = time.time()
        self.logger.info("Start transcribe based on diarization result...")
        
        # 规范化音频数据用于转录
        # _, audio_data = self.normalize_audio(audio=audio)
        diarization = self.post_diarization.merge_close_segments(diarization)

        
        # 收集所有说话人片段
        speaker_segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # 处理不同格式的说话人标签
            if speaker.startswith('SPEAKER_') and speaker[8:].isdigit():
                # 处理 SPEAKER_00, SPEAKER_01 等格式
                speaker_num = int(speaker[8:]) + 1  # 将0-based转换为1-based
                formatted_speaker = f'Speaker-{speaker_num}'
            elif speaker.startswith('speaker') and speaker[7:].isdigit():
                # 处理 speaker0, speaker1 等格式
                speaker_num = int(speaker[7:]) + 1  # 将0-based转换为1-based
                formatted_speaker = f'Speaker-{speaker_num}'
            else:
                # 其他格式直接使用原始标签
                formatted_speaker = speaker
                
            # 提取该片段的音频
            start_sample = int(turn.start * self.SAMPLE_RATE)
            end_sample = int(turn.end * self.SAMPLE_RATE)
            segment_audio = audio_data[start_sample:end_sample]
            
            # 检查音频长度是否超过30秒
            if len(segment_audio) > self.SAMPLE_RATE * 30:  # 超过30秒
                self.logger.info(f"Detect long audio segment, use VAD to split")
                # 使用VAD分割长音频
                vad_segments = self.split_long_audio_with_vad(segment_audio, max_duration=30.0)
                
                # 将分割后的片段添加到speaker_segments中
                for i, vad_seg in enumerate(vad_segments):
                    # 调整时间戳，使其相对于原始音频
                    adjusted_start = turn.start + vad_seg['start']
                    adjusted_end = turn.start + vad_seg['end']
                    
                    speaker_segments.append({
                        'start': adjusted_start,
                        'end': adjusted_end,
                        'speaker': formatted_speaker,
                        'audio': vad_seg['audio'],
                        'segment_id': str(uuid.uuid4())
                    })
                # 如果当前片段小于1.5秒，且与上一个片段属于同一个人，并且间隔小于1s，则合并
            elif len(segment_audio) < self.SAMPLE_RATE * 1.5 and len(speaker_segments) > 0 and speaker_segments[-1]['speaker'] == formatted_speaker \
                    and turn.start - speaker_segments[-1]['end'] < 1 and len(speaker_segments[-1]['audio']) < self.SAMPLE_RATE * 30:
                    speaker_segments[-1]['end'] = turn.end
                    speaker_segments[-1]['audio'] = audio_data[int(speaker_segments[-1]['start'] * self.SAMPLE_RATE):end_sample]
                # 如果上一个片段小于1.5秒，且当前片段与上一个片段属于同一个人，并且间隔小于2s，则合并
            elif len(speaker_segments) > 0 and speaker_segments[-1]['speaker'] == formatted_speaker \
                    and len(speaker_segments[-1]['audio']) < self.SAMPLE_RATE * 1.5 and turn.start - speaker_segments[-1]['end'] < 2 \
                    and len(speaker_segments[-1]['audio']) < self.SAMPLE_RATE * 30:
                    speaker_segments[-1]['end'] = turn.end
                    speaker_segments[-1]['audio'] = audio_data[int(speaker_segments[-1]['start'] * self.SAMPLE_RATE):end_sample]
            else:
                # 音频长度正常，直接添加
                speaker_segments.append({
                    'start': turn.start,
                    'end': turn.end,
                    'speaker': formatted_speaker,
                    'audio': segment_audio,
                    'segment_id': str(uuid.uuid4())
                })
        
        self.logger.info(f"检测到 {len(set([seg['speaker'] for seg in speaker_segments]))} 个说话人，共 {len(speaker_segments)} 个片段")
        
        if len(set([seg['speaker'] for seg in speaker_segments])) == 1 and not save_one_spk:
            self.logger.info("仅检测到一个说话人，将继续转录并按统一 JSON 格式保存结果。")
            
        # 重新分配说话人标签，按首次出现时间排序
        speaker_first_appearance = {}
        for seg in speaker_segments:
            speaker = seg['speaker']
            if speaker not in speaker_first_appearance:
                speaker_first_appearance[speaker] = seg['start']
        
        # 按首次出现时间排序说话人
        sorted_speakers = sorted(speaker_first_appearance.keys(), 
                               key=lambda x: speaker_first_appearance[x])
        
        # 创建新的说话人映射
        speaker_mapping = {}
        for i, old_speaker in enumerate(sorted_speakers):
            speaker_mapping[old_speaker] = f'Speaker-{i + 1}'
        
        # 更新所有片段的说话人标签
        for seg in speaker_segments:
            seg['speaker'] = speaker_mapping[seg['speaker']]
        
        # 4. 对每个片段进行转录
        result_with_speaker = []
        results, unique_languages = self._transcribe_segments(speaker_segments, context_txts)

        # 直接配对（不进行合法性检查）
        paired_segments = list(zip(speaker_segments, results))

        with ThreadPoolExecutor(max_workers=8) as executor:  # 请按需调整线程数
            futures = []
            for segment_info, transcribe_result in paired_segments:
                futures.append(
                    executor.submit(
                        analyze_segment,
                        segment_info,
                        transcribe_result
                    )
                )

            for f in futures:
                try:
                    result_with_speaker.append(f.result())
                except Exception as e:
                    self.logger.error(f"❌ 片段处理出错: {e}")

        # 按时间排序
        result_with_speaker.sort(key=lambda x: x['start'])
        
        self.logger.info(f"Transcribe Done, cost: {time.time() - transcribe_start_time:.2f}s")
        
        self.logger.info(f"Total cost: {time.time() - total_start_time:.2f}s")

        import json
        from pathlib import Path

        # 添加保存 JSON 的逻辑（可根据需要修改保存路径和文件名）
        # 保存路径
        save_path = Path(output_json_path) if output_json_path else Path("diarization_transcript.json")
        output_payload = build_output_payload(result_with_speaker, self.SAMPLE_RATE)
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(output_payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"❌ 保存 JSON 失败: {e}")


        return output_payload
    
    def _transcribe_segments(self, segments: List[Dict], context_txts: List[str] = None):
        model = self.whisper_model

        results = []
        languages = []

        for segment in segments:
            audio = segment['audio']  # np.ndarray, float32, 单通道

            # Whisper 要求是 [-1, 1] 的 float32
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            if np.max(np.abs(audio)) > 1.0:
                audio = audio / np.max(np.abs(audio))

            try:
                result = model.transcribe(
                    audio,
                    language=None,
                    fp16=(self.device == 'cuda'),
                    without_timestamps=True
                )
                text = result.get("text", "").strip()
                lang = result.get("language", "unknown")
            except Exception as e:
                self.logger.warning(f"Whisper large-v3 识别出错: {e}")
                text = ""
                lang = "unknown"

            results.append(SimpleNamespace(text=text, lang=lang))
            languages.append(lang)

        return results, list(set(languages))

            
    def split_long_audio_with_vad(self, audio_data: np.ndarray, max_duration: float = 30.0) -> List[Dict]:
        """
        使用VAD将超过指定时长的音频分割成小于指定时长的小段
        
        Args:
            audio_data: 音频数据
            max_duration: 最大时长（秒），默认30秒
            
        Returns:
            分割后的音频片段列表，每个片段包含start、end、audio信息
        """
        max_samples = int(max_duration * self.SAMPLE_RATE)
        
        segments = []
        current_start = 0
        current_end = max_samples
        
        while current_start < len(audio_data):
            # 提取当前片段
            segment_audio = audio_data[current_start:current_end]
            
            # 如果当前片段小于最大时长，直接添加
            if len(segment_audio) < max_samples:
                segments.append({
                    'start': current_start / self.SAMPLE_RATE,
                    'end': current_end / self.SAMPLE_RATE,
                    'audio': segment_audio
                })
                break
            
            # 使用VAD检测语音活动，寻找合适的切分点
            try:
                # 将音频转换为int16格式用于VAD处理
                audio_int16 = (segment_audio * 32767).astype(np.int16)
                audio_bytes = audio_int16.tobytes()
                
                # 使用VAD检测语音活动状态
                vad_speech_frames = self.detect_speech_activity(audio_bytes, self.SAMPLE_RATE)
                
                # 寻找最佳切分点（在语音停顿处）
                best_split_point = self.find_best_split_point(vad_speech_frames, len(segment_audio))
                
                # 添加当前片段
                segments.append({
                    'start': current_start / self.SAMPLE_RATE,
                    'end': (current_start + best_split_point) / self.SAMPLE_RATE,
                    'audio': segment_audio[:best_split_point]
                })
                
                # 更新下一个片段的起始位置
                current_start += best_split_point
                current_end = min(current_start + max_samples, len(audio_data))
                    
            except Exception as e:
                self.logger.warning(f"VAD处理失败，使用简单切分: {e}")
                # VAD处理失败时，在中间位置切分
                mid_point = len(segment_audio) // 2
                segments.append({
                    'start': current_start / self.SAMPLE_RATE,
                    'end': (current_start + mid_point) / self.SAMPLE_RATE,
                    'audio': segment_audio[:mid_point]
                })
                current_start += mid_point
                current_end = min(current_start + max_samples, len(audio_data))
        
        return segments


    def detect_speech_activity(self, audio_bytes: bytes, sample_rate: int, frame_duration_ms: int = 30) -> List[bool]:
        vad = webrtcvad.Vad(2)  # 使用中等敏感度
        frame_size = int(sample_rate * frame_duration_ms / 1000.0 * 2)  # 16位采样
        speech_frames = []
        
        offset = 0
        while offset + frame_size <= len(audio_bytes):
            frame = audio_bytes[offset:offset + frame_size]
            try:
                is_speech = vad.is_speech(frame, sample_rate)
                speech_frames.append(is_speech)
            except Exception:
                # 如果VAD检测失败，假设为语音
                speech_frames.append(True)
            offset += frame_size
        
        return speech_frames

    def find_best_split_point(self, speech_frames: List[bool], audio_length: int, frame_duration_ms: int = 30) -> int:
        """
        在语音停顿处寻找最佳切分点
        
        Args:
            speech_frames: 语音活动状态列表
            audio_length: 音频长度（采样点数）
            frame_duration_ms: 帧时长（毫秒）
            
        Returns:
            最佳切分点（采样点数）
        """
        if not speech_frames:
            return audio_length // 2
        
        frame_size = int(self.SAMPLE_RATE * frame_duration_ms / 1000.0 * 2)  # 16位采样
        target_duration = 30.0  # 目标时长30秒
        target_frames = int(target_duration * 1000 / frame_duration_ms)

        
        # 寻找最佳切分点
        best_split_frame = target_frames
        best_score = 0
        
        for frame_idx in range(target_frames):
            if speech_frames[frame_idx]:
                continue
            
            # 计算当前位置的静音长度（向前和向后）
            silence_before = 0
            silence_after = 0
            
            # 向前计算连续静音帧数
            for i in range(frame_idx - 1, max(0, frame_idx - 10), -1):
                if not speech_frames[i]:
                    silence_before += 1
                else:
                    break
            
            # 向后计算连续静音帧数
            for i in range(frame_idx, min(len(speech_frames), frame_idx + 10)):
                if not speech_frames[i]:
                    silence_after += 1
                else:
                    break
                        
            silent_frames = silence_before + silence_after
            
            if silent_frames > best_score:
                best_score = silent_frames
                best_split_frame = frame_idx
        
        # 转换为采样点数
        split_point = best_split_frame * frame_size
        
        # 确保切分点在合理范围内
        split_point = max(frame_size, min(split_point, audio_length - frame_size))
        
        return split_point


import os
import json
import argparse
import time
from pathlib import Path
import numpy as np
import multiprocessing


def parse_args():
    parser = argparse.ArgumentParser(description="Batch diarization and transcription from TSV list")

    repo_root = Path(__file__).resolve().parents[3]
    parser.add_argument(
        "--tsv_path", type=str, default=str(repo_root / "data" / "audio_list.tsv"),
        help="Path to TSV file, each line is an audio path"
    )
    parser.add_argument(
        "--output_dir", type=str, default=str(repo_root / "test" / "json"),
        help="Directory to save output JSONs"
    )
    parser.add_argument(
        "--embedding_dir", type=str, default="speaker_test/embedding",
        help="Path to speaker embedding (.npy) directory"
    )
    parser.add_argument(
        "--context_txt", type=str, nargs="*", default=["韩餐"],
        help="Optional context prompts"
    )
    parser.add_argument(
        "--save_one_spk", action="store_true",
        help="If set, only the most prominent speaker segment will be saved"
    )
    parser.add_argument(
        "--num_workers", type=int, default=1,
        help="Number of processes to use for parallel processing"
    )

    return parser.parse_args()


def process_audio_batch(audio_paths_chunk, args):
    """每个子进程处理一个批次的音频路径"""
    from modules.models.stt.Whisper import WhisperModel

    repo_root = Path(__file__).resolve().parents[3]
    model = WhisperModel(True, 1)

    speaker_embeddings = {
        f.stem: np.load(f)
        for f in Path(args.embedding_dir).glob("*.npy")
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for audio_path in audio_paths_chunk:
        audio_path = Path(audio_path)
        if not audio_path.is_absolute():
            audio_path = repo_root / audio_path
        if not audio_path.exists():
            print(f"❌ 文件不存在，跳过: {audio_path}")
            continue

        try:
            output_json_path = output_dir / (audio_path.stem + ".json")

            _ = model.diarize_then_transcribe(
                audio=str(audio_path),
                speaker_embeddings=speaker_embeddings,
                flag_format=False,
                context_txts=args.context_txt,
                output_json_path=output_json_path,
                save_one_spk=args.save_one_spk
            )

            print(f"✅ [PID {os.getpid()}] 保存转录结果至: {output_json_path}")
        except Exception as e:
            print(f"❌ [PID {os.getpid()}] 处理 {audio_path.name} 时出错: {e}")


if __name__ == "__main__":
    args = parse_args()
    start_time = time.time()

    tsv_path = Path(args.tsv_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载音频路径列表
    with open(tsv_path, "r", encoding="utf-8") as f:
        audio_paths = [line.strip() for line in f if line.strip()]

    print(f"\n🔊 共加载 {len(audio_paths)} 个音频，将使用 {args.num_workers} 个进程并行处理。")

    # 拆分音频列表为子任务
    chunk_size = len(audio_paths) // args.num_workers + 1
    audio_chunks = [audio_paths[i:i + chunk_size] for i in range(0, len(audio_paths), chunk_size)]

    ctx = multiprocessing.get_context("spawn")  # 更稳定的多进程上下文（兼容 CUDA）
    with ctx.Pool(processes=args.num_workers) as pool:
        pool.starmap(process_audio_batch, [(chunk, args) for chunk in audio_chunks])

    elapsed = time.time() - start_time
    print(f"\n✅ 全部完成，耗时: {elapsed:.2f} 秒")
