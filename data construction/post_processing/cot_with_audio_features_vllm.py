#!/usr/bin/env python3
import csv
import ast
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from vllm import LLM, SamplingParams
except ImportError as exc:
    raise SystemExit(
        "vllm is required for this script. Please install it in your deepseek environment."
    ) from exc


# ========== vLLM / 模型配置 ==========
REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = os.environ.get(
    "DEEPSEEK_MODEL_PATH",
    str(REPO_ROOT / "model" / "deepseek" / "DeepSeek-R1-Distill-Qwen-14B"),
)
CUDA_VISIBLE_DEVICES = os.environ.get("DEEPSEEK_CUDA_VISIBLE_DEVICES", "0,1,3,4")
TENSOR_PARALLEL_SIZE = int(os.environ.get("DEEPSEEK_TP_SIZE", str(len(CUDA_VISIBLE_DEVICES.split(",")))))
GPU_MEMORY_UTILIZATION = float(os.environ.get("DEEPSEEK_GPU_MEM_UTIL", "0.80"))
MAX_MODEL_LEN = int(os.environ.get("DEEPSEEK_MAX_MODEL_LEN", "4096"))
MAX_NUM_BATCHED_TOKENS = int(os.environ.get("DEEPSEEK_MAX_BATCHED_TOKENS", "12288"))
MAX_NUM_SEQS = int(os.environ.get("DEEPSEEK_MAX_NUM_SEQS", "96"))
ENABLE_CHUNKED_PREFILL = os.environ.get("DEEPSEEK_ENABLE_CHUNKED_PREFILL", "1") != "0"
TRUST_REMOTE_CODE = os.environ.get("DEEPSEEK_TRUST_REMOTE_CODE", "1") != "0"

TEMPERATURE = float(os.environ.get("DEEPSEEK_TEMPERATURE", "0.0"))
TOP_P = float(os.environ.get("DEEPSEEK_TOP_P", "1.0"))
MAX_NEW_TOKENS = int(os.environ.get("DEEPSEEK_MAX_NEW_TOKENS", "1536"))
REPETITION_PENALTY = float(os.environ.get("DEEPSEEK_REPETITION_PENALTY", "1.0"))
PROMPT_BATCH_SIZE = int(os.environ.get("DEEPSEEK_PROMPT_BATCH_SIZE", "64"))

# ========== 输入 / 输出 ==========
INPUT_TSV = os.environ.get(
    "DEEPSEEK_INPUT_TSV",
    "",
)
INPUT_DIR = os.environ.get(
    "DEEPSEEK_INPUT_DIR",
    str(REPO_ROOT / "test" / "json_all_scene_speakers"),
)
SHARD_INDEX = int(os.environ.get("DEEPSEEK_SHARD_INDEX", "0"))
NUM_SHARDS = int(os.environ.get("DEEPSEEK_NUM_SHARDS", "1"))
OUT_DIR = os.environ.get(
    "DEEPSEEK_OUT_DIR",
    str(REPO_ROOT / "test" / "json_all_cot"),
)
ERROR_LOG_PATH = os.environ.get(
    "DEEPSEEK_ERROR_LOG",
    os.path.join(OUT_DIR, f"_errors_shard{SHARD_INDEX}_of_{NUM_SHARDS}.log"),
)

# ========== 参数 ==========
MAX_TEXT_PER_LINE = 220
MAX_LINES_PER_WINDOW = 5
DEBUG_RAW = os.environ.get("DEEPSEEK_DEBUG_RAW", "0") == "1"
DEBUG_STOP_ON_BAD_JSON = os.environ.get("DEEPSEEK_DEBUG_STOP_ON_BAD_JSON", "0") == "1"
ENABLE_RETRY_ON_BAD_OUTPUT = os.environ.get("DEEPSEEK_ENABLE_RETRY", "1") != "0"
MAX_MOVIES: Optional[int] = (
    int(os.environ["DEEPSEEK_MAX_MOVIES"])
    if os.environ.get("DEEPSEEK_MAX_MOVIES")
    else None
)


def shorten(s: str, n: int) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "..."


def safe_filename(name: str) -> str:
    name = name or "unknown"
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(char, "_")
    return name.replace(" ", "_")


def extract_json_block(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S | re.I).strip()
    if t.startswith("```"):
        t = t.strip("`").strip()
        if t.startswith("json"):
            t = t[4:].strip()
    lb1, rb1 = t.find("{"), t.rfind("}")
    if lb1 != -1 and rb1 != -1 and lb1 < rb1:
        return t[lb1 : rb1 + 1]
    return ""


def normalize_json_like_text(text: str) -> str:
    t = text.strip()
    t = t.replace("“", '"').replace("”", '"')
    t = t.replace("‘", "'").replace("’", "'")
    t = t.replace("\u00a0", " ")
    t = re.sub(r",(\s*[}\]])", r"\1", t)
    return t


def escape_newlines_in_json_strings(text: str) -> str:
    chars: List[str] = []
    in_string = False
    escape = False

    for ch in text:
        if escape:
            chars.append(ch)
            escape = False
            continue

        if ch == "\\":
            chars.append(ch)
            escape = True
            continue

        if ch == '"':
            chars.append(ch)
            in_string = not in_string
            continue

        if in_string and ch in "\r\n":
            chars.append("\\n")
            continue

        chars.append(ch)

    return "".join(chars)


def repair_unescaped_quotes_in_json_strings(text: str) -> str:
    chars: List[str] = []
    in_string = False
    escape = False
    n = len(text)
    i = 0

    while i < n:
        ch = text[i]

        if escape:
            chars.append(ch)
            escape = False
            i += 1
            continue

        if ch == "\\":
            chars.append(ch)
            escape = True
            i += 1
            continue

        if ch == '"':
            if not in_string:
                chars.append(ch)
                in_string = True
                i += 1
                continue

            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            next_ch = text[j] if j < n else ""

            # Inside a JSON string, a quote should usually be followed by
            # ',', '}', ']', or ':' to terminate the string. Otherwise treat
            # it as a stray inner quote and escape it.
            if next_ch in {",", "}", "]", ":"} or j >= n:
                chars.append(ch)
                in_string = False
            else:
                chars.append('\\"')
            i += 1
            continue

        chars.append(ch)
        i += 1

    return "".join(chars)


def try_parse_json(text: str, fallback=None):
    blk = extract_json_block(text)
    if not blk:
        return fallback
    blk = normalize_json_like_text(blk)
    blk = escape_newlines_in_json_strings(blk)
    blk = repair_unescaped_quotes_in_json_strings(blk)
    try:
        return json.loads(blk)
    except Exception:
        pass

    blk2 = blk.replace("True", "true").replace("False", "false").replace("None", "null")
    try:
        return json.loads(blk2)
    except Exception:
        pass

    try:
        obj = ast.literal_eval(blk)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    try:
        obj = ast.literal_eval(
            blk.replace("true", "True").replace("false", "False").replace("null", "None")
        )
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    return fallback


def group_scenes_from_segments(segs: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    scenes: Dict[int, List[Dict[str, Any]]] = {}
    for seg in segs:
        scene_idx = int(seg.get("scene_index", 0))
        scenes.setdefault(scene_idx, []).append(seg)
    for scene_idx in scenes.keys():
        scenes[scene_idx].sort(
            key=lambda x: (float(x.get("start", 0.0)), float(x.get("end", 0.0)))
        )
    return scenes


def format_acoustic_events(seg: Dict[str, Any]) -> str:
    events = seg.get("acoustic_events") or seg.get("events") or []
    if not isinstance(events, list):
        return ""

    items = []
    for event in events:
        if isinstance(event, (list, tuple)) and len(event) >= 3:
            label = str(event[0]) if event[0] is not None else ""
            items.append(f"{label}({event[1]}-{event[2]})")
        elif isinstance(event, (list, tuple)) and len(event) >= 1:
            label = str(event[0]) if event[0] is not None else ""
            items.append(label)

    if not items:
        return ""

    uniq = []
    for item in items:
        if item not in uniq:
            uniq.append(item)
    return shorten("；".join(uniq), 200)


def _format_feature_value(value: Any) -> str:
    if value is None or value == "":
        return "?"
    try:
        return f"{float(value):.3f}"
    except Exception:
        return shorten(str(value), 30)


def format_audio_features(seg: Dict[str, Any]) -> str:
    features = seg.get("audio_features") or {}
    if not isinstance(features, dict):
        return ""

    labels = [
        ("duration", "总时长"),
        ("active_duration", "有效时长"),
        ("loudness", "响度"),
        ("expressive_intensity", "表达强度"),
        ("naturalness score", "自然度"),
        ("noise score", "噪声/音质"),
    ]
    parts = []
    for key, label in labels:
        if key in features:
            parts.append(f"{label}={_format_feature_value(features.get(key))}")
    return "；".join(parts)


def build_window_lines(scene_segs: List[Dict[str, Any]], idx: int) -> List[str]:
    start_idx = max(0, idx - (MAX_LINES_PER_WINDOW - 1))
    lines = []
    local_id = 0

    for pos in range(start_idx, idx + 1):
        seg = scene_segs[pos]
        speaker = seg.get("speaker", "Unknown")
        text = shorten(seg.get("text", ""), MAX_TEXT_PER_LINE)
        raw_emo_tag = shorten(str(seg.get("emo-tag", "") or "?"), 20)
        events_desc = format_acoustic_events(seg)
        audio_feature_desc = format_audio_features(seg)

        parts = [
            f"#{local_id}",
            f"说话人={speaker}",
            f"原emo-tag={raw_emo_tag}",
        ]
        if events_desc:
            parts.append(f"音频事件={events_desc}")
        if audio_feature_desc:
            parts.append(f"音频特征={audio_feature_desc}")

        lines.append(" | ".join(parts) + f"\n台词：{text}")
        local_id += 1

    return lines


def build_cot_messages(
    window_lines: List[str],
    target_seg: Dict[str, Any],
    is_first_in_scene: bool,
) -> List[Dict[str, str]]:
    speaker = target_seg.get("speaker", "Unknown")
    text = target_seg.get("text", "") or ""
    raw_emo_tag = shorten(str(target_seg.get("emo-tag", "") or "?"), 20)
    audio_feature_desc = format_audio_features(target_seg) or "无"

    history_note = (
        "当前句是本场景第一句，只能基于当前句本身分析。"
        if is_first_in_scene
        else "你可以利用窗口中前面的历史台词分析当前句。"
    )

    user_msg = {
        "role": "user",
        "content": (
            "任务：只根据当前窗口、目标台词、原始 emo-tag、音频事件和音频特征，分析最后一句台词。你可以先在内部思考，但最终只能输出一个 JSON 对象；不要输出思考过程、解释、markdown、代码块。\n"
            "规则：emo_tag 必须是 4 到 8 个字的中文短句；必须明确写出情感程度、态度或说话方式，不能只有裸情绪词。"
            "优先写成“略带惊讶、低落回应、压着怒气、试探追问、克制陈述、强作镇定”这种带修饰的短语，不能只写“惊讶、悲伤、生气、开心”。"
            "必须结合台词和历史语境细化，不能只把 happy/sad/angry 直译成空泛词。"
            "若证据不足，情感判断必须保守，不要夸大强度。只能使用当前窗口信息，不能引用窗口外信息、未来台词、固定人设。"
            "音频特征只能作为辅助证据：响度、有效时长和表达强度可辅助判断说话方式，自然度和噪声/音质主要用于判断证据可靠性，不要机械照抄数值。"
            "每个 dimX.text 必须是单行中文短句，尽量20字内；无法判断就写“无法根据当前历史判断”。"
            "dim4 只分析当前认知状态和说话动机。summ 必须用这个句式：因为（关键原因/上下文），所以用'怎样的方式'说了‘目标台词’。"
            "所有字段值都必须单行；如果要引用目标台词，不要在字符串内部再使用双引号。\n\n"
            "输出 JSON 结构：\n"
            "{\n"
            '  "emo_tag": "中文短句",\n'
            '  "dim1_language_act": {"need_cot": true, "text": "..."},\n'
            '  "dim2_addressee": {"need_cot": true, "text": "..."},\n'
            '  "dim3_scene_semantics": {"need_cot": true, "text": "..."},\n'
            '  "dim4_cognition_persona_motivation": {"need_cot": true, "text": "..."},\n'
            '  "dim5_expected_outcome": {"need_cot": true, "text": "..."},\n'
            '  "dim6_emotion_trajectory": {"need_cot": true, "text": "..."},\n'
            '  "summ": "一小段综合总结"\n'
            "}\n\n"
            "【分析目标】\n"
            f"- 目标说话人：{speaker}\n"
            f"- 目标台词：{text}\n"
            f"- 原始 emo-tag：{raw_emo_tag}\n"
            f"- 音频特征：{audio_feature_desc}\n"
            f"- 历史说明：{history_note}\n\n"
            "【对话窗口（按时间顺序，最后一条是目标句）】\n"
            + "\n\n".join(window_lines)
            + "\n\n【分析任务】\n"
            "请先生成一个更贴合语境的中文 emo_tag（不超过10字），"
            "后面的 6 维分析和 summ 也要优先依据这个新 emo_tag 来推断，"
            "再从以下 6 个角度分析最后一句台词：\n"
            "1) 语言行为分析：当前台词主要在做什么。\n"
            "2) 受话对象分析：主要是对谁说的。\n"
            "3) 场景语义分析：这句话出现时的对话局面或语境。\n"
            "4) 认知-动机分析：结合历史，推测说话人当下心理状态和行为动因。\n"
            "5) 期望结果分析：希望达到什么沟通或情感效果。\n"
            "6) 情绪轨迹分析：相对前文，情绪是延续、升级还是缓和，大致原因是什么。\n\n"
            "答案必须直接从 { 开始，到 } 结束。"
        ),
    }

    return [user_msg]


def build_retry_cot_messages(
    window_lines: List[str],
    target_seg: Dict[str, Any],
    is_first_in_scene: bool,
) -> List[Dict[str, str]]:
    speaker = target_seg.get("speaker", "Unknown")
    text = target_seg.get("text", "") or ""
    raw_emo_tag = shorten(str(target_seg.get("emo-tag", "") or "?"), 20)
    audio_feature_desc = format_audio_features(target_seg) or "无"

    history_note = (
        "当前句是本场景第一句，只能基于当前句本身分析。"
        if is_first_in_scene
        else "可以利用前面历史台词分析当前句。"
    )

    user_msg = {
        "role": "user",
        "content": (
            "只输出一个 JSON 对象，不要输出思考过程、解释、markdown、代码块。\n"
            "只能使用当前窗口信息。\n"
            "可以参考音频特征辅助判断说话方式，但不要机械照抄数值。\n"
            "emo_tag 必须是 4 到 8 个字的中文情感短语，必须体现情感程度、态度或说话方式，不能只有裸情绪词。"
            "优先使用类似“略感惊讶、低落回应、试探追问、克制陈述、压着怒气”这种带修饰短语。"
            "不能复述台词内容，不能直接输出 happy/sad/angry，证据不足时必须保守。\n"
            "每个 dimX.text 必须是单行中文短句，尽量 12 字内；无法判断就写“无法根据当前历史判断”。\n"
            "summ 必须单行，且使用句式：因为（关键原因/上下文），所以用'怎样的方式'说了‘目标台词’。\n\n"
            "输出 JSON 结构：\n"
            "{\n"
            '  "emo_tag": "中文情感短语",\n'
            '  "dim1_language_act": {"need_cot": true, "text": "..."},\n'
            '  "dim2_addressee": {"need_cot": true, "text": "..."},\n'
            '  "dim3_scene_semantics": {"need_cot": true, "text": "..."},\n'
            '  "dim4_cognition_persona_motivation": {"need_cot": true, "text": "..."},\n'
            '  "dim5_expected_outcome": {"need_cot": true, "text": "..."},\n'
            '  "dim6_emotion_trajectory": {"need_cot": true, "text": "..."},\n'
            '  "summ": "..."'
            "\n}\n\n"
            "【分析目标】\n"
            f"- 目标说话人：{speaker}\n"
            f"- 目标台词：{text}\n"
            f"- 原始 emo-tag：{raw_emo_tag}\n"
            f"- 音频特征：{audio_feature_desc}\n"
            f"- 历史说明：{history_note}\n\n"
            "【对话窗口】\n"
            + "\n\n".join(window_lines)
            + "\n\n答案必须直接从 { 开始，到 } 结束。"
        ),
    }

    return [user_msg]


def build_fallback_cot(seg: Dict[str, Any]) -> Dict[str, Any]:
    text = shorten(seg.get("text", "") or "这句台词", 80)
    fallback_emo = shorten(str(seg.get("emo-tag", "") or "情绪不明"), 10)
    return {
        "emo_tag": fallback_emo or "情绪不明",
        "dim1_language_act": {"need_cot": True, "text": "COT 生成失败。"},
        "dim2_addressee": {"need_cot": True, "text": "COT 生成失败。"},
        "dim3_scene_semantics": {"need_cot": True, "text": "COT 生成失败。"},
        "dim4_cognition_persona_motivation": {
            "need_cot": True,
            "text": "COT 生成失败。",
        },
        "dim5_expected_outcome": {"need_cot": True, "text": "COT 生成失败。"},
        "dim6_emotion_trajectory": {"need_cot": True, "text": "COT 生成失败。"},
        "summ": f"因为上下文分析失败，所以说了“{text}”。",
    }


@dataclass
class PromptTask:
    scene_idx: int
    local_i: int
    global_seg_id: str
    seg: Dict[str, Any]
    prompt: str
    retry_prompt: str


class BatchedDeepSeekRunner:
    def __init__(self) -> None:
        print(
            "[INFO] init vLLM: "
            f"model={MODEL_PATH}, tp={TENSOR_PARALLEL_SIZE}, "
            f"cuda_visible_devices={os.environ.get('CUDA_VISIBLE_DEVICES', '<unset>')}, "
            f"gpu_mem={GPU_MEMORY_UTILIZATION}, "
            f"max_model_len={MAX_MODEL_LEN}, "
            f"max_batched_tokens={MAX_NUM_BATCHED_TOKENS}, "
            f"max_num_seqs={MAX_NUM_SEQS}"
        )
        self.llm = LLM(
            model=MODEL_PATH,
            tensor_parallel_size=TENSOR_PARALLEL_SIZE,
            gpu_memory_utilization=GPU_MEMORY_UTILIZATION,
            max_model_len=MAX_MODEL_LEN,
            max_num_batched_tokens=MAX_NUM_BATCHED_TOKENS,
            max_num_seqs=MAX_NUM_SEQS,
            trust_remote_code=TRUST_REMOTE_CODE,
            enable_chunked_prefill=ENABLE_CHUNKED_PREFILL,
        )
        self.tokenizer = self.llm.get_tokenizer()
        self.sampling_params = SamplingParams(
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=MAX_NEW_TOKENS,
            repetition_penalty=REPETITION_PENALTY,
        )

    def build_prompt(self, messages: Sequence[Dict[str, str]]) -> str:
        try:
            return self.tokenizer.apply_chat_template(
                list(messages),
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            return "\n\n".join(m.get("content", "") for m in messages)

    def generate(self, prompts: Sequence[str]) -> List[str]:
        outputs = self.llm.generate(list(prompts), self.sampling_params, use_tqdm=False)
        texts: List[str] = []
        for output in outputs:
            if output.outputs:
                texts.append(output.outputs[0].text.strip())
            else:
                texts.append("")
        return texts


def read_tsv_paths(tsv_path: str) -> Iterable[str]:
    with open(tsv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        first_row = next(reader, None)
        if first_row is None:
            return
        header = [cell.strip() for cell in first_row]
        path_idx = 0
        has_header = len(header) >= 1 and header[0].lower() == "path"
        if has_header:
            if "path" in [x.lower() for x in header]:
                path_idx = [x.lower() for x in header].index("path")
        else:
            row = first_row
            if row and row[0].strip():
                yield row[0].strip()

        for row in reader:
            if not row:
                continue
            if path_idx >= len(row):
                continue
            path = row[path_idx].strip()
            if path:
                yield path


def read_unique_tsv_paths(tsv_path: str) -> List[str]:
    seen = set()
    paths: List[str] = []
    for path in read_tsv_paths(tsv_path):
        norm_path = os.path.abspath(path)
        if norm_path in seen:
            continue
        seen.add(norm_path)
        paths.append(norm_path)
    return paths


def build_out_path(movie: Dict[str, Any]) -> str:
    movie_id = movie.get("id", "")
    name = movie.get("name", "")
    safe_name = safe_filename(name or movie_id or "unknown")
    if movie_id:
        safe_id = safe_filename(movie_id)
        out_fname = f"{safe_id}__{safe_name}__cot.json"
    else:
        out_fname = f"{safe_name}__cot.json"
    return os.path.join(OUT_DIR, out_fname)


def log_error(message: str) -> None:
    print(message)
    os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message.rstrip() + "\n")


def load_movie(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_tasks_for_movie(movie: Dict[str, Any], runner: BatchedDeepSeekRunner) -> List[PromptTask]:
    segs = movie.get("segment", [])
    if not isinstance(segs, list) or not segs:
        return []

    tasks: List[PromptTask] = []
    scenes = group_scenes_from_segments(segs)
    for scene_idx in sorted(scenes.keys()):
        scene_segs = scenes[scene_idx]
        for local_i, seg in enumerate(scene_segs):
            global_seg_id = seg.get("segment_id", f"scene{scene_idx}_idx{local_i}")
            window_lines = build_window_lines(scene_segs, local_i)
            messages = build_cot_messages(window_lines, seg, local_i == 0)
            retry_messages = build_retry_cot_messages(window_lines, seg, local_i == 0)
            prompt = runner.build_prompt(messages)
            retry_prompt = runner.build_prompt(retry_messages)
            tasks.append(
                PromptTask(
                    scene_idx=scene_idx,
                    local_i=local_i,
                    global_seg_id=global_seg_id,
                    seg=seg,
                    prompt=prompt,
                    retry_prompt=retry_prompt,
                )
            )
    return tasks


def force_need_cot_true(value: Any, default_text: str = "无法根据当前历史判断") -> Dict[str, Any]:
    if isinstance(value, dict):
        item = dict(value)
    else:
        item = {"text": default_text}
    item["need_cot"] = True
    if "text" not in item:
        item["text"] = default_text
    return item


def apply_cot_result(seg: Dict[str, Any], parsed: Dict[str, Any]) -> None:
    emo_tag_cn = shorten(str(parsed.get("emo_tag", "") or seg.get("emo-tag", "") or "情绪不明"), 10)
    seg["emo-tag"] = emo_tag_cn
    seg["cot"] = {
        "dim1_language_act": force_need_cot_true(parsed.get(
            "dim1_language_act",
            {"text": "无法根据当前历史判断"},
        )),
        "dim2_addressee": force_need_cot_true(parsed.get(
            "dim2_addressee",
            {"text": "无法根据当前历史判断"},
        )),
        "dim3_scene_semantics": force_need_cot_true(parsed.get(
            "dim3_scene_semantics",
            {"text": "无法根据当前历史判断"},
        )),
        "dim4_cognition_persona_motivation": force_need_cot_true(parsed.get(
            "dim4_cognition_persona_motivation",
            {"text": "无法根据当前历史判断"},
        )),
        "dim5_expected_outcome": force_need_cot_true(parsed.get(
            "dim5_expected_outcome",
            {"text": "无法根据当前历史判断"},
        )),
        "dim6_emotion_trajectory": force_need_cot_true(parsed.get(
            "dim6_emotion_trajectory",
            {"text": "无法根据当前历史判断"},
        )),
        "summ": parsed.get("summ", ""),
    }
    seg["summ"] = seg["cot"].get("summ", "")


def is_bad_emo_tag(emo_tag: Any, seg: Dict[str, Any]) -> bool:
    emo = str(emo_tag or "").strip()
    if not emo:
        return True
    if len(emo) > 10:
        return True
    lowered = emo.lower()
    if lowered in {"happy", "sad", "angry", "neutral", "fear", "surprise", "disgust"}:
        return True

    text = str(seg.get("text", "") or "").strip()
    if text:
        text_lower = text.lower()
        if len(emo) >= 4 and emo.lower() in text_lower:
            return True
        if len(emo) >= 4 and emo in text:
            return True
    return False


def parse_and_validate_output(raw: str, seg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    parsed = try_parse_json(raw, fallback=None)
    if not isinstance(parsed, dict):
        return None
    if is_bad_emo_tag(parsed.get("emo_tag", ""), seg):
        return None
    return parsed


def handle_bad_json(task: PromptTask, raw: str, reason: str) -> None:
    print(f"[WARN] bad COT json for seg={task.global_seg_id}, reason={reason}, write fallback.")
    if DEBUG_STOP_ON_BAD_JSON:
        print("\n[DEBUG BAD JSON] segment_id:", task.global_seg_id)
        print("[DEBUG BAD JSON] prompt:\n")
        print(task.prompt)
        print("\n[DEBUG BAD JSON] raw output:\n")
        print(raw)
        raise RuntimeError(f"bad COT json for seg={task.global_seg_id}")


def save_movie(movie: Dict[str, Any], out_path: str) -> None:
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(movie, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, out_path)


def annotate_movie_cot(
    movie: Dict[str, Any],
    out_path: str,
    runner: BatchedDeepSeekRunner,
) -> int:
    tasks = build_tasks_for_movie(movie, runner)
    if not tasks:
        print("[WARN] movie has no segments, skip COT.")
        save_movie(movie, out_path)
        return 0

    print(f"  [INFO] pending prompts: {len(tasks)}")
    total_calls = 0
    t0 = time.time()

    for batch_start in range(0, len(tasks), PROMPT_BATCH_SIZE):
        batch_tasks = tasks[batch_start : batch_start + PROMPT_BATCH_SIZE]
        prompts = [task.prompt for task in batch_tasks]
        raws = runner.generate(prompts)

        for task, raw in zip(batch_tasks, raws):
            total_calls += 1
            if DEBUG_RAW:
                print(f"\n[DEBUG COT {task.global_seg_id}] {raw}\n")

            parsed = parse_and_validate_output(raw, task.seg)
            reason = "parse_or_validation_failed"
            if not isinstance(parsed, dict) and ENABLE_RETRY_ON_BAD_OUTPUT:
                retry_raw = runner.generate([task.retry_prompt])[0]
                total_calls += 1
                if DEBUG_RAW:
                    print(f"\n[DEBUG RETRY {task.global_seg_id}] {retry_raw}\n")
                parsed = parse_and_validate_output(retry_raw, task.seg)
                raw = retry_raw
                reason = "retry_failed"

            if not isinstance(parsed, dict):
                handle_bad_json(task, raw, reason)
                parsed = build_fallback_cot(task.seg)
            apply_cot_result(task.seg, parsed)

        save_movie(movie, out_path)
        print(
            f"  [SAVE BATCH] {min(batch_start + len(batch_tasks), len(tasks))}/{len(tasks)} "
            f"→ {out_path}"
        )

    elapsed = time.time() - t0
    print(f"[INFO] movie COT done. LLM calls: {total_calls}, elapsed={elapsed:.2f}s")
    return total_calls


def iter_movies_from_tsv(tsv_path: str) -> Iterable[Tuple[str, Dict[str, Any]]]:
    all_paths = read_unique_tsv_paths(tsv_path)
    shard_paths = [
        path for idx, path in enumerate(all_paths) if (idx % NUM_SHARDS) == SHARD_INDEX
    ]

    for norm_path in shard_paths:
        if not os.path.exists(norm_path):
            log_error(f"[WARN] input json not found, skip: {norm_path}")
            continue

        try:
            movie = load_movie(norm_path)
        except Exception as exc:
            log_error(f"[ERROR] failed to load json: {norm_path} | {exc}")
            continue

        if not isinstance(movie, dict):
            log_error(f"[WARN] item is not a movie dict, skip: {norm_path}")
            continue

        yield norm_path, movie


def iter_movies_from_dir(input_dir: str) -> Iterable[Tuple[str, Dict[str, Any]]]:
    json_paths = sorted(Path(input_dir).glob("*.json"))
    shard_paths = [
        path for idx, path in enumerate(json_paths) if (idx % NUM_SHARDS) == SHARD_INDEX
    ]

    for path in shard_paths:
        try:
            movie = load_movie(str(path))
        except Exception as exc:
            log_error(f"[ERROR] failed to load json: {path} | {exc}")
            continue

        if not isinstance(movie, dict):
            log_error(f"[WARN] item is not a movie dict, skip: {path}")
            continue

        yield str(path), movie


def main() -> None:
    if CUDA_VISIBLE_DEVICES:
        os.environ["CUDA_VISIBLE_DEVICES"] = CUDA_VISIBLE_DEVICES

    os.makedirs(OUT_DIR, exist_ok=True)

    use_tsv = bool(INPUT_TSV)
    if use_tsv and not os.path.exists(INPUT_TSV):
        raise FileNotFoundError(f"input tsv not found: {INPUT_TSV}")
    if not use_tsv and not os.path.isdir(INPUT_DIR):
        raise NotADirectoryError(f"input dir not found: {INPUT_DIR}")
    if NUM_SHARDS <= 0:
        raise ValueError("DEEPSEEK_NUM_SHARDS must be >= 1")
    if SHARD_INDEX < 0 or SHARD_INDEX >= NUM_SHARDS:
        raise ValueError("DEEPSEEK_SHARD_INDEX must satisfy 0 <= index < num_shards")

    runner = BatchedDeepSeekRunner()
    processed = 0
    skipped = 0
    total_calls = 0

    print(
        f"[INFO] shard config: shard_index={SHARD_INDEX}, num_shards={NUM_SHARDS}, "
        f"error_log={ERROR_LOG_PATH}"
    )
    if use_tsv:
        total_unique = len(read_unique_tsv_paths(INPUT_TSV))
        movie_iter = iter_movies_from_tsv(INPUT_TSV)
        print(f"[INFO] input_tsv={INPUT_TSV}")
    else:
        total_unique = len(sorted(Path(INPUT_DIR).glob("*.json")))
        movie_iter = iter_movies_from_dir(INPUT_DIR)
        print(f"[INFO] input_dir={INPUT_DIR}")
    shard_count = sum(1 for idx in range(total_unique) if (idx % NUM_SHARDS) == SHARD_INDEX)
    print(f"[INFO] total_unique_inputs={total_unique}, shard_inputs={shard_count}")

    for idx, (src_path, movie) in enumerate(movie_iter):
        if MAX_MOVIES is not None and processed >= MAX_MOVIES:
            break

        out_path = build_out_path(movie)
        movie_id = movie.get("id", f"movie-{idx}")
        name = movie.get("name", "")

        print(f"\n[INFO] COT for movie {movie_id} ({name})")
        print(f"  [SRC] {src_path}")
        print(f"  [OUT] {out_path}")

        if os.path.exists(out_path):
            skipped += 1
            print(f"[SKIP] {movie_id} 已处理，文件存在：{out_path}")
            continue

        try:
            calls = annotate_movie_cot(movie, out_path, runner)
            total_calls += calls
            processed += 1
            print(f"[MOVIE DONE] movie {movie_id} → {out_path}")
        except Exception as exc:
            log_error(f"[ERROR] failed to process movie: {src_path} | {exc}")
            continue

    print(f"\n[DONE] Total movies processed: {processed}")
    print(f"[DONE] Total movies skipped: {skipped}")
    print(f"[DONE] Total LLM calls: {total_calls}")
    print(f"COT files saved under: {OUT_DIR}")


if __name__ == "__main__":
    main()
