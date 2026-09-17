from abc import ABC, abstractmethod
from diart import argdoc, utils
from diart import blocks
from diart import operators as dops
from diart.audio import FilePath, AudioLoader
from diart.progress import ProgressBar, RichProgressBar
from diart.sinks import PredictionAccumulator, StreamingPlot, WindowClosedException
from typing import Text, Optional, Tuple, Callable, List, Dict, Any
import rx
import rx.operators as ops
from rx.subject import Subject
from rx.core import Observer
from einops import rearrange
from pyannote.core import Annotation, SlidingWindowFeature, SlidingWindow, Segment
from traceback import print_exc
from pathlib import Path
import torch
import numpy as np
import logging

class AudioSource(ABC):
    """Represents a source of audio that can start streaming via the `stream` property.

    Parameters
    ----------
    uri: Text
        Unique identifier of the audio source.
    sample_rate: int
        Sample rate of the audio source.
    """

    def __init__(self, uri: Text, sample_rate: int):
        self.uri = uri
        self.sample_rate = sample_rate
        self.stream = Subject()

    @property
    def duration(self) -> Optional[float]:
        """The duration of the stream if known. Defaults to None (unknown duration)."""
        return None

    @abstractmethod
    def read(self):
        """Start reading the source and yielding samples through the stream."""
        pass

    @abstractmethod
    def close(self):
        """Stop reading the source and close all open streams."""
        pass


class FileAudioSource(AudioSource):
    """Represents an audio source tied to a file.

    Parameters
    ----------
    file: FilePath
        Path to the file to stream.
    sample_rate: int
        Sample rate of the chunks emitted.
    padding: (float, float)
        Left and right padding to add to the file (in seconds).
        Defaults to (0, 0).
    block_duration: int
        Duration of each emitted chunk in seconds.
        Defaults to 0.5 seconds.
    """

    def __init__(
        self,
        file: FilePath,
        sample_rate: int,
        padding: Tuple[float, float] = (0, 0),
        block_duration: float = 0.5,
    ):
        super().__init__(Path(file).stem, sample_rate)
        self.loader = AudioLoader(self.sample_rate, mono=True)
        self._duration = self.loader.get_duration(file)
        self.file = file
        self.resolution = 1 / self.sample_rate
        self.block_size = int(np.rint(block_duration * self.sample_rate))
        self.padding_start, self.padding_end = padding
        self.is_closed = False

    @property
    def duration(self) -> Optional[float]:
        # The duration of a file is known
        return self.padding_start + self._duration + self.padding_end

    def read(self):
        """Send each chunk of samples through the stream"""
        waveform = self.loader.load(self.file)

        # Add zero padding at the beginning if required
        if self.padding_start > 0:
            num_pad_samples = int(np.rint(self.padding_start * self.sample_rate))
            zero_padding = torch.zeros(waveform.shape[0], num_pad_samples)
            waveform = torch.cat([zero_padding, waveform], dim=1)

        # Add zero padding at the end if required
        if self.padding_end > 0:
            num_pad_samples = int(np.rint(self.padding_end * self.sample_rate))
            zero_padding = torch.zeros(waveform.shape[0], num_pad_samples)
            waveform = torch.cat([waveform, zero_padding], dim=1)

        # Split into blocks
        _, num_samples = waveform.shape
        chunks = rearrange(
            waveform.unfold(1, self.block_size, self.block_size),
            "channel chunk sample -> chunk channel sample",
        ).numpy()

        # Add last incomplete chunk with padding
        if num_samples % self.block_size != 0:
            last_chunk = (
                waveform[:, chunks.shape[0] * self.block_size :].unsqueeze(0).numpy()
            )
            diff_samples = self.block_size - last_chunk.shape[-1]
            last_chunk = np.concatenate(
                [last_chunk, np.zeros((1, 1, diff_samples))], axis=-1
            )
            chunks = np.vstack([chunks, last_chunk])

        # Stream blocks
        for i, waveform in enumerate(chunks):
            try:
                if self.is_closed:
                    break
                self.stream.on_next(waveform)
            except BaseException as e:
                self.stream.on_error(e)
                break
        self.stream.on_completed()
        self.close()

    def close(self):
        self.is_closed = True


# ============= 重新实现StreamingInference类 =============
class StreamingInference:
    """Performs inference in real time given a pipeline and an audio source.
    Streams an audio source to an online speaker diarization pipeline.
    It allows users to attach a chain of operations in the form of hooks.

    Parameters
    ----------
    pipeline: StreamingPipeline
        Configured speaker diarization pipeline.
    source: AudioSource
        Audio source to be read and streamed.
    batch_size: int
        Number of inputs to send to the pipeline at once.
        Defaults to 1.
    do_profile: bool
        If True, compute and report the processing time of the pipeline.
        Defaults to True.
    do_plot: bool
        If True, draw predictions in a moving plot.
        Defaults to False.
    show_progress: bool
        If True, show a progress bar.
        Defaults to True.
    progress_bar: Optional[diart.progress.ProgressBar]
        Progress bar.
        If description is not provided, set to 'Streaming <source uri>'.
        Defaults to RichProgressBar().
    """

    def __init__(
        self,
        pipeline: blocks.Pipeline,
        source: AudioSource,
        batch_size: int = 1,
        do_profile: bool = True,
        do_plot: bool = False,
        show_progress: bool = True,
        progress_bar: Optional[ProgressBar] = None,
    ):
        self.pipeline = pipeline
        self.source = source
        self.batch_size = batch_size
        self.do_profile = do_profile
        self.do_plot = do_plot
        self.show_progress = show_progress
        self.accumulator = PredictionAccumulator(self.source.uri)
        self.unit = "chunk" if self.batch_size == 1 else "batch"
        self._observers = []

        chunk_duration = self.pipeline.config.duration
        step_duration = self.pipeline.config.step
        sample_rate = self.pipeline.config.sample_rate

        # Estimate the total number of chunks that the source will emit
        self.num_chunks = None
        if self.source.duration is not None:
            numerator = self.source.duration - chunk_duration + step_duration
            self.num_chunks = int(np.ceil(numerator / step_duration))

        # Show progress if required
        self._pbar = progress_bar
        if self.show_progress:
            if self._pbar is None:
                self._pbar = RichProgressBar()
            self._pbar.create(
                total=self.num_chunks,
                description=f"Streaming {self.source.uri}",
                unit=self.unit,
            )

        # Initialize chronometer for profiling
        self._chrono = utils.Chronometer(self.unit, self._pbar)

        self.stream = self.source.stream

        # Rearrange stream to form sliding windows
        self.stream = self.stream.pipe(
            dops.rearrange_audio_stream(
                chunk_duration, step_duration, source.sample_rate
            ),
        )

        # Dynamic resampling if the audio source isn't compatible
        if sample_rate != self.source.sample_rate:
            msg = (
                f"Audio source has sample rate {self.source.sample_rate}, "
                f"but pipeline's is {sample_rate}. Will resample."
            )
            logging.warning(msg)
            self.stream = self.stream.pipe(
                ops.map(
                    blocks.Resample(
                        self.source.sample_rate,
                        sample_rate,
                        self.pipeline.config.device,
                    )
                )
            )

        # Form batches
        self.stream = self.stream.pipe(
            ops.buffer_with_count(count=self.batch_size),
        )

        if self.do_profile:
            self.stream = self.stream.pipe(
                ops.do_action(on_next=lambda _: self._chrono.start()),
                ops.map(self.pipeline),
                ops.do_action(on_next=lambda _: self._chrono.stop()),
            )
        else:
            self.stream = self.stream.pipe(ops.map(self.pipeline))

        self.stream = self.stream.pipe(
            ops.flat_map(lambda results: rx.from_iterable(results)),
            ops.do(self.accumulator),
        )

        if show_progress:
            self.stream = self.stream.pipe(
                ops.do_action(on_next=lambda _: self._pbar.update())
            )

    def _close_pbar(self):
        if self._pbar is not None:
            self._pbar.close()

    def _close_chronometer(self):
        if self.do_profile:
            if self._chrono.is_running:
                self._chrono.stop(do_count=False)
            self._chrono.report()

    def attach_hooks(
        self, *hooks: Callable[[Tuple[Annotation, SlidingWindowFeature]], None]
    ):
        """Attach hooks to the pipeline.

        Parameters
        ----------
        *hooks: (Tuple[Annotation, SlidingWindowFeature]) -> None
            Hook functions to consume emitted annotations and audio.
        """
        self.stream = self.stream.pipe(*[ops.do_action(hook) for hook in hooks])

    def attach_observers(self, *observers: Observer):
        """Attach rx observers to the pipeline.

        Parameters
        ----------
        *observers: Observer
            Observers to consume emitted annotations and audio.
        """
        self.stream = self.stream.pipe(*[ops.do(sink) for sink in observers])
        self._observers.extend(observers)

    def _handle_error(self, error: BaseException):
        # Compensate for Rx not always calling on_error
        for sink in self._observers:
            sink.on_error(error)
        # Always close the source in case of bad termination
        self.source.close()
        # Special treatment for a user interruption (counted as normal termination)
        window_closed = isinstance(error, WindowClosedException)
        interrupted = isinstance(error, KeyboardInterrupt)
        if not window_closed and not interrupted:
            print_exc()
        # Close internal states
        self._close_pbar()
        self._close_chronometer()

    def _handle_completion(self):
        # Close internal states
        self._close_pbar()
        self._close_chronometer()

    def __call__(self) -> Annotation:
        """Stream audio chunks from `source` to `pipeline`.

        Returns
        -------
        predictions: Annotation
            Speaker diarization pipeline predictions
        """
        if self.show_progress:
            self._pbar.start()
        config = self.pipeline.config
        observable = self.stream
        if self.do_plot:
            # Buffering is needed for the real-time plot, so we do this at the very end
            observable = self.stream.pipe(
                dops.buffer_output(
                    duration=config.duration,
                    step=config.step,
                    latency=config.latency,
                    sample_rate=config.sample_rate,
                ),
                ops.do(StreamingPlot(config.duration, config.latency)),
            )
        observable.subscribe(
            on_error=self._handle_error,
            on_completed=self._handle_completion,
        )
        # FIXME if read() isn't blocking, the prediction returned is empty
        self.source.read()
        return self.accumulator.get_prediction()

class StreamingProcessor:
    """实时处理器，支持500ms chunk"""
    
    def __init__(self, 
                 segmentation_model,
                 embedding_model,
                 chunk_duration: float = 0.5,  # 500ms
                 step_duration: float = 0.5,   # 500ms
                 sample_rate: int = 16000,
                 device: Optional[str] = None):
        """
        初始化实时处理器
        
        Args:
            segmentation_model: 分段模型
            embedding_model: 嵌入模型
            chunk_duration: chunk持续时间（秒），默认0.5秒
            step_duration: 步长（秒），默认0.5秒
            sample_rate: 采样率
            device: 设备
        """
        self.chunk_duration = chunk_duration
        self.step_duration = step_duration
        self.sample_rate = sample_rate
        self.chunk_size = int(chunk_duration * sample_rate)
        self.device = torch.device(device if device else ('cuda' if torch.cuda.is_available() else 'cpu'))
        self.segmentation_model = segmentation_model
        self.embedding_model = embedding_model
        
        # 创建支持小chunk的pipeline配置
        pipeline_class = utils.get_pipeline_class("SpeakerDiarization")
        config = pipeline_class.get_config_class()(
            segmentation=segmentation_model,
            embedding=embedding_model,
            duration=chunk_duration,  # 使用小chunk
            step=step_duration,       # 使用小step
            latency=step_duration,    # 设置延迟等于step
            device=self.device,
            sample_rate=sample_rate,
        )
        self.pipeline = pipeline_class(config)
        
        # 设置timestamp_shift来补偿延迟造成的时间偏移
        self.pipeline.set_timestamp_shift(0.0)
        
        # 结果存储
        self.chunk_results = []
        
        # print(f"Processor初始化: chunk_duration={chunk_duration}s, chunk_size={self.chunk_size}")
        # print(f"Pipeline配置: duration={config.duration}s, step={config.step}s, latency={config.latency}s")
    def reset(self):
        """
        重置处理器状态，清空所有缓存的结果和重置pipeline状态
        """
        # 清空结果存储
        self.chunk_results = []
        
        # 重置pipeline状态
        try:
            # 如果pipeline有reset方法，调用它
            if hasattr(self.pipeline, 'reset'):
                self.pipeline.reset()
            
            # 如果pipeline有内部状态需要重置，可以重新创建pipeline
            # 但这里我们先保持原有的pipeline，只重置结果存储
            
            # 重新设置timestamp_shift
            self.pipeline.set_timestamp_shift(0.0)
            
            print("TrueRealTimeProcessor状态已重置")
            
        except Exception as e:
            print(f"重置pipeline状态时出错: {e}")
            # 如果重置失败，重新创建pipeline
            try:
                pipeline_class = utils.get_pipeline_class("SpeakerDiarization")
                config = pipeline_class.get_config_class()(
                    segmentation=self.segmentation_model,
                    embedding=self.embedding_model,
                    duration=self.chunk_duration,
                    step=self.step_duration,
                    latency=self.step_duration,
                    device=self.device,
                    sample_rate=self.sample_rate,
                )
                self.pipeline = pipeline_class(config)
                self.pipeline.set_timestamp_shift(0.0)
                print("Pipeline已重新创建")
            except Exception as e2:
                print(f"重新创建pipeline时出错: {e2}")
    
    def get_chunk_count(self) -> int:
        """
        获取已处理的chunk数量
        
        Returns:
            已处理的chunk数量
        """
        return len(self.chunk_results)
    
    def get_results(self) -> List[Dict[str, Any]]:
        """
        获取所有chunk的结果
        
        Returns:
            包含所有chunk结果的列表
        """
        return self.chunk_results.copy()
        
    def process_chunk(self, audio_chunk: np.ndarray, chunk_idx: int) -> Dict[str, Any]:
        """
        处理单个音频chunk
        
        Args:
            audio_chunk: 音频数据 (shape: [channels, samples] 或 [samples])
            chunk_idx: chunk索引
            
        Returns:
            包含说话人分离结果的字典
        """
        # 确保音频格式正确
        if audio_chunk.ndim == 1:
            audio_chunk = audio_chunk.reshape(1, -1)
        
        # 如果chunk长度不足，进行填充
        if audio_chunk.shape[1] < self.chunk_size:
            padding = self.chunk_size - audio_chunk.shape[1]
            audio_chunk = np.pad(audio_chunk, ((0, 0), (0, padding)), mode='constant')
        elif audio_chunk.shape[1] > self.chunk_size:
            # 如果chunk太长，截断
            audio_chunk = audio_chunk[:, :self.chunk_size]
        
        # 确保是numpy数组
        if not isinstance(audio_chunk, np.ndarray):
            audio_chunk = np.array(audio_chunk)
        
        # 确保数据类型正确
        audio_chunk = audio_chunk.astype(np.float32)
        
        # 确保数据是连续的
        audio_chunk = np.ascontiguousarray(audio_chunk)
        
        # 重要：diart期望的格式是(samples, channels)，所以需要转置
        if audio_chunk.shape[0] == 1:  # 如果是(1, samples)格式
            audio_chunk = audio_chunk.T  # 转置为(samples, 1)
        
        # 创建SlidingWindowFeature对象
        # 注意：SlidingWindow的duration和step是每个样本的时间分辨率，不是整个chunk的时长
        resolution = 1.0 / self.sample_rate  # 每个样本的时间分辨率
        sliding_window = SlidingWindow(
            duration=resolution,
            step=resolution,
            start=chunk_idx * self.step_duration
        )
        waveform_feature = SlidingWindowFeature(audio_chunk, sliding_window)
        
        # 运行pipeline
        try:
            # 对于diart的pipeline，传递SlidingWindowFeature对象
            result = self.pipeline([waveform_feature])
            
            # 检查结果类型
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            
            if isinstance(result, tuple):
                annotation, features = result
            else:
                annotation = result
                features = None
            
            # 分析结果
            speakers = list(annotation.labels())
            segments = []
            
            for segment, track, speaker in annotation.itertracks(yield_label=True):
                segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'speaker': speaker,
                    'duration': segment.duration
                })
            
            chunk_result = {
                'chunk_idx': chunk_idx,
                'speakers': speakers,
                'segments': segments,
                'annotation': annotation,
                'audio_chunk': audio_chunk,
                'has_speech': len(segments) > 0
            }
            
            self.chunk_results.append(chunk_result)
            return chunk_result
            
        except Exception as e:
            print(f"处理chunk {chunk_idx} 时出错: {e}")
            import traceback
            traceback.print_exc()
            return {
                'chunk_idx': chunk_idx,
                'error': str(e),
                'audio_chunk': audio_chunk,
                'has_speech': False
            }

class PostProcessor:
    """后处理器：使用embedding比较来降低说话人分离错误率"""
    
    def __init__(self, 
                 embedding_model: str = "pyannote/embedding",
                 similarity_threshold: float = 0.7,
                 device: Optional[str] = None):
        """
        初始化后处理器
        
        Args:
            embedding_model: embedding模型路径或名称
            use_auth_token: HuggingFace访问令牌
            similarity_threshold: 相似度阈值
            device: 计算设备
        """
        self.similarity_threshold = similarity_threshold
        self.device = torch.device(device if device else ('cuda' if torch.cuda.is_available() else 'cpu'))
        
        # 初始化embedding模型
        from pyannote.audio import Model, Inference
        
        # 加载embedding模型
        self.embedding_model = Model.from_pretrained(
            embedding_model
        )
        self.embedding_model.to(self.device)
        
        # 创建Inference实例
        self.inference = Inference(
            self.embedding_model,
            window="whole",  # 使用whole window模式
            device=self.device
        )
        
        # 音频加载器
        from pyannote.audio import Audio
        self.audio = Audio(sample_rate=16000, mono="downmix")
        
    
    def extract_segment_embedding(self, waveform: np.ndarray) -> np.ndarray:
        """
        提取单个segment的embedding
        
        Args:
            waveform: 音频数据
            
        Returns:
            embedding向量
        """
        try:            
            # 提取embedding
            with torch.no_grad():
                waveform = torch.from_numpy(waveform).to(self.device).unsqueeze(0)
                embedding = self.inference({"waveform": waveform, "sample_rate": 16000})
                embedding = embedding.squeeze()
                
                # 归一化embedding
                embedding = embedding / np.linalg.norm(embedding)
                
            return embedding
            
        except Exception as e:
            print(f"提取segment embedding失败: {e}")
            return None
    
    def calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        计算两个embedding的余弦相似度
        
        Args:
            emb1: 第一个embedding
            emb2: 第二个embedding
            
        Returns:
            相似度分数 (0-1)
        """
        if emb1 is None or emb2 is None:
            return 0.0
        
        # 计算余弦相似度
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    def post_process_prediction(self, 
                              prediction: Annotation, 
                              audio_data: np.ndarray,
                              min_segment_duration: float = 0.5) -> Annotation:
        """
        对预测结果进行后处理，使用embedding比较来修正说话人标签
        
        Args:
            prediction: 原始预测结果
            audio_data: 音频数据
            min_segment_duration: 最小segment持续时间
            
        Returns:
            修正后的预测结果
        """
        
        # 创建新的Annotation对象
        corrected_prediction = Annotation()
        
        # 获取所有segments，按时间排序
        segments = []
        for segment, track, speaker in prediction.itertracks(yield_label=True):
            if segment.duration > min_segment_duration:  # 过滤太短的segment
                start_sample = int(segment.start * 16000)
                end_sample = int(segment.end * 16000)
                segment_audio = audio_data[start_sample:end_sample]
                segments.append({
                    'segment': segment,
                    'track': track,
                    'speaker': speaker,
                    'embedding': None,
                    'waveform': segment_audio
                })
        
        # 按时间排序
        segments.sort(key=lambda x: x['segment'].start)
                
        # 提取所有segments的embedding
        for i, seg_info in enumerate(segments):
            embedding = self.extract_segment_embedding(seg_info['waveform'])
            seg_info['embedding'] = embedding
                    
        # 进行embedding比较和修正
        corrected_speakers = {}
        
        for i, seg_info in enumerate(segments):
            current_embedding = seg_info['embedding']
            if current_embedding is None:
                # 如果无法提取embedding，保持原标签
                corrected_speakers[seg_info['speaker']] = seg_info['speaker']
                continue
            
            # 初始化最佳相似度和说话人
            best_similarity = 0.0
            best_speaker = None
            
            # 与前面的segments比较（减少计算量）
            compare_range = min(5, i)
            
            for j in range(max(0, i - compare_range), i):
                prev_seg_info = segments[j]
                prev_embedding = prev_seg_info['embedding']
                
                if prev_embedding is not None:
                    similarity = self.calculate_similarity(current_embedding, prev_embedding)
                    
                    if similarity > best_similarity and similarity >= self.similarity_threshold:
                        best_similarity = similarity
                        best_speaker = prev_seg_info['speaker']
            
            # 与后面的segments比较（减少计算量）
            forward_compare_range = min(5, len(segments) - i - 1)
            
            for j in range(i + 1, min(i + 1 + forward_compare_range, len(segments))):
                next_seg_info = segments[j]
                next_embedding = next_seg_info['embedding']
                
                if next_embedding is not None:
                    similarity = self.calculate_similarity(current_embedding, next_embedding)
                    
                    if similarity > best_similarity and similarity >= self.similarity_threshold:
                        best_similarity = similarity
                        best_speaker = next_seg_info['speaker']
            
            # 如果找到相似的speaker，使用相同的标签
            if best_speaker is not None:
                corrected_speakers[seg_info['speaker']] = best_speaker
                seg_info['corrected_speaker'] = best_speaker
            else:
                # 如果没有找到相似的，保持原标签或分配新标签
                # if seg_info['speaker'] not in corrected_speakers:
                #     corrected_speakers[seg_info['speaker']] = f"SPEAKER_{next_speaker_id:02d}"
                #     next_speaker_id += 1
                
                # seg_info['corrected_speaker'] = corrected_speakers[seg_info['speaker']]
                seg_info['corrected_speaker'] = seg_info['speaker']
        
        # 构建修正后的Annotation
        for seg_info in segments:
            corrected_speaker = seg_info.get('corrected_speaker', seg_info['speaker'])
            corrected_prediction[seg_info['segment'], seg_info['track']] = corrected_speaker
        
        print("Diarization post-processing complete")
        
        # 合并间隔小于1秒的相同speaker segments
        merged_prediction = self._merge_close_segments(corrected_prediction, max_gap=1.0)
        
        
        return merged_prediction
    
    def merge_close_segments(self, prediction: Annotation, max_gap: float = 1.0) -> Annotation:
        """
        合并间隔小于指定时间的相同speaker segments
        
        Args:
            prediction: 输入预测结果
            max_gap: 最大间隔时间（秒）
            
        Returns:
            合并后的预测结果
        """
        # 收集所有segments并按时间排序
        all_segments = []
        for segment, track, speaker in prediction.itertracks(yield_label=True):
            if segment.duration > 0.5:
                all_segments.append({
                    'segment': segment,
                    'track': track,
                    'speaker': speaker
                })
        
        # 按开始时间排序
        all_segments.sort(key=lambda x: x['segment'].start)
        
        if not all_segments:
            return Annotation()
        
        # 创建新的Annotation
        merged_prediction = Annotation()
        
        # 逐个处理segments，检查是否可以与前一个合并
        merged_segments = []
        current_seg = all_segments[0]
        
        for i in range(1, len(all_segments)):
            next_seg = all_segments[i]
            
            # 检查是否是同一个说话人且间隔小于阈值
            if (current_seg['speaker'] == next_seg['speaker'] and 
                next_seg['segment'].start - current_seg['segment'].end <= max_gap):
                # 合并segments
                current_seg['segment'] = Segment(
                    current_seg['segment'].start, 
                    next_seg['segment'].end
                )
            else:
                # 不能合并，保存当前segment并开始新的
                merged_segments.append(current_seg)
                current_seg = next_seg
        
        # 添加最后一个segment
        merged_segments.append(current_seg)
        
        # 添加到结果
        for seg_info in merged_segments:
            merged_prediction[seg_info['segment'], seg_info['track']] = seg_info['speaker']
        
        return merged_prediction