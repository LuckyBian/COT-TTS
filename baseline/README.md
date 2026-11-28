# Baseline Models and Prompts

This document describes the seven cascaded baselines shown on the [COT-TTS demo page](../docs/README.md), including their model identities, inputs, intermediate outputs, and actual LLM prompt templates. The descriptions follow the existing experimental runners. This folder contains documentation only; baseline inference code, checkpoints, and generated data are not bundled here.

## Models

| Component | Model / checkpoint | Role |
|---|---|---|
| ASR | **Qwen3-ASR-1.7B** | Transcribe historical dialogue audio for the ASR-based three-stage systems. |
| Text LLM | **Qwen3-30B-A3B-Instruct-2507** | Infer delivery from a textual history and the target text. This is the text-only Qwen model. |
| Audio-language model | **Qwen3-Omni-30B-A3B-Instruct** | Read historical audio directly; produce either a textual delivery specification or native speech, depending on the pipeline. |
| Fish TTS | **Fish Audio S2 Pro** | Synthesize the tagged target text with reference-speaker conditioning. The experimental alias `Fish2` resolves to the `s2-pro` checkpoint and `codec.pth`. |
| VoxCPM TTS | **VoxCPM2** | Synthesize a style-described target text using the reference waveform. The experimental alias `VoxCPM` refers to the local `VoxCPM2` checkpoint. |
| Voice conversion | **Seed-VC** | Convert Qwen3-Omni's generated speech toward the reference speaker. The configured checkpoint is `DiT_seed_v2_uvit_whisper_small_wavenet_bigvgan_pruned.pth`, with `config_dit_mel_seed_uvit_whisper_small_wavenet.yml`. |

**DiA input.** The DiA-conditioned runners consume a prepared speaker-separated history in `his_segment_json`. Each usable segment supplies its text, speaker label, and timestamps; optional language and emotion fields are retained when present. These runners do not load an additional DiA checkpoint. The source segment files do not record an upstream ASR/diarization model identity, so the DiA label here identifies the prepared history representation, not a separately verified model checkpoint. The project's general audio annotation pipeline is described in [data construction](../data%20construction/README.md).

## Baseline configurations

Let **H** denote historical dialogue audio, **T** the target text, and **R** the reference waveform.

| Demo baseline | History supplied to the reasoning model | Reasoning model | Speech backend |
|---|---|---|---|
| DiA + A3B + Fish2 | Speaker-separated, timestamped history text | Qwen3-30B-A3B-Instruct-2507 | Fish Audio S2 Pro |
| DiA + A3B + VoxCPM | Speaker-separated, timestamped history text | Qwen3-30B-A3B-Instruct-2507 | VoxCPM2 |
| Qwen3-ASR + A3B + Fish2 | Plain history transcript from Qwen3-ASR-1.7B | Qwen3-30B-A3B-Instruct-2507 | Fish Audio S2 Pro |
| Qwen-ASR + A3B + VoxCPM | Plain history transcript from Qwen3-ASR-1.7B | Qwen3-30B-A3B-Instruct-2507 | VoxCPM2 |
| Qwen + Fish | H, supplied as audio | Qwen3-Omni-30B-A3B-Instruct | Fish Audio S2 Pro |
| Qwen + VoxCPM | H, supplied as audio | Qwen3-Omni-30B-A3B-Instruct | VoxCPM2 |
| Qwen3-Omni + SeedVC | H and R, supplied as audio | Qwen3-Omni-30B-A3B-Instruct, including native speech generation | Seed-VC |

All systems also receive T. In the three-stage systems, the stages are history transcription/diarization preparation, text reasoning, and TTS. The DiA history is prepared in advance. In the two-stage Qwen + TTS systems, Qwen3-Omni replaces the separate transcript and text-LLM stages.

The shorter demo labels `A3B`, `Qwen`, `Qwen-ASR`, `Fish2`, and `VoxCPM` refer to the full model names above.

## Intermediate output and TTS adaptation

The DiA, ASR, and Qwen3-Omni-to-TTS reasoning stages all request this JSON schema:

```json
{
  "analysis": "Concise contextual analysis and delivery description.",
  "tagged_text": "The target sentence with a few inline style tags."
}
```

- **Fish Audio S2 Pro:** use `tagged_text` as the synthesis text. The Fish runner also receives R and the corresponding reference transcript. The `analysis` string is retained as an intermediate output.
- **VoxCPM2:** remove square-bracket tags from `tagged_text`, collapse whitespace in `analysis`, and construct the synthesis text as `({analysis}){clean_target_text}`. The reference waveform is passed separately. The parentheses carry a delivery/style description; there is no extra LLM call that summarizes the analysis again.

The Fish and VoxCPM variants use **identical LLM prompts within each history-input family and language**, verified against the source functions. This includes the words “Fish Audio” and the Fish tag list inside the VoxCPM variants' prompts: the backend adaptation occurs after the LLM output. The templates below preserve that actual behavior rather than rewriting the prompts to sound backend-specific.

**Qwen3-Omni + Seed-VC differs:** Qwen3-Omni receives H, R, and T in one multimodal user message and produces native speech. Its prompt requires the visible assistant text and spoken output to contain only T. It does not request the JSON analysis/tagged-text schema. The native speech then becomes the source for Seed-VC; R is the conversion target. The native generator's default built-in speaker is `Ethan`, and reference audio in its prompt is not a substitute for a dedicated voice-conversion stage. The files saved under its legacy `analysis_result` directory are the generated assistant text, not a requested CoT analysis.

## Prompt conventions

The templates below are rendered directly from the experimental prompt-building functions, preserving wording and the tag whitelist. Only runtime values are replaced by placeholders:

- `{history_text}`: the formatted DiA history or the Qwen3-ASR transcript, depending on the section.
- `{target_text}`: the target sentence after the runner removes pre-existing square-bracket tags.

For audio-input prompts, the history waveform is supplied as an audio content item alongside the textual prompt. For native Qwen3-Omni speech generation, the reference waveform is a second audio content item. Audio data are not represented by a `{history_text}` substitution in those cases.

The task-specific prompts are supplied as user messages through the relevant model's chat template. There is no separate task-specific system prompt in these runners.

## 1. Speaker-separated history → text LLM → TTS

The history is sorted by segment start time and formatted as `[MM:SS.ss-MM:SS.ss] Speaker-ID: utterance`, optionally followed by `(lang=..., emotion=...)`. Both Fish and VoxCPM variants use these templates.

<details>
<summary>Chinese prompt</summary>

```text
你正在为 Fish Audio 准备有表现力的中文 TTS 输入。

输入：
- 说话人分离后的历史对话：包含说话人标签和时间戳，用来理解上下文与人物关系。
- 目标文本：现在需要被说出的句子。

说话人分离后的历史对话：
{history_text}

目标文本：
{target_text}

任务：
1. 根据带说话人的历史对话，判断当前说话情境、人物关系、情绪、节奏和表达方式。
2. 生成带 Fish Audio 风格标签的目标文本。

Fish Audio 支持标签：
[happy], [sad], [angry], [fearful], [surprised], [disgusted], [neutral], [excited], [calm], [serious], [whisper], [shouting], [laughing], [crying], [sigh], [pause], [short pause], [long pause], [breath], [inhale], [exhale], [emphasis], [soft], [fast], [slow]

要求：
- 不要翻译目标文本。
- 除了插入短标签，目标文本正文尽量保持原样。
- 只能从上面的 Fish Audio 支持标签中选择标签，不要发明新标签。
- 只使用少量关键标签，不要过度打标签。
- 标签应放在影响其后语气的位置；如果描述整句，也可以放在句末。
- 标签必须是 [] 内的短英文标签。
- "analysis" 里要简短说明历史说话人轮次如何影响目标文本的表达。
- 只返回 JSON。

JSON 格式：
{
  "analysis": "...",
  "tagged_text": "..."
}
```

</details>

<details>
<summary>English prompt</summary>

```text
You are preparing expressive English TTS input for Fish Audio.

Inputs:
- Diarized history dialogue: previous dialogue context with speaker labels and timestamps.
- Target text: the sentence that must be spoken now.

Diarized history dialogue:
{history_text}

Target text:
{target_text}

Task:
1. Use the speaker-separated history to infer the current speaking situation, speaker relationship, emotion, rhythm, and delivery.
2. Produce the target text with short Fish Audio style tags.

Supported Fish Audio tags:
[happy], [sad], [angry], [fearful], [surprised], [disgusted], [neutral], [excited], [calm], [serious], [whisper], [shouting], [laughing], [crying], [sigh], [pause], [short pause], [long pause], [breath], [inhale], [exhale], [emphasis], [soft], [fast], [slow]

Requirements:
- Do not translate the target text.
- Keep the target text wording unchanged except for inserting short tags.
- Use tags only from the supported Fish Audio tag list above. Do not invent new tags.
- Use only a few helpful tags. Do not over-tag.
- Put tags inline where they affect delivery, or at the end only if they describe the whole utterance.
- Tags must be short English tags inside [].
- In "analysis", mention how speaker turns in the history affect the target delivery.
- Return JSON only.

JSON schema:
{
  "analysis": "...",
  "tagged_text": "..."
}
```

</details>

## 2. Qwen3-ASR transcript → text LLM → TTS

The history is the plain ASR transcript. The text LLM is not given the history waveform in this pipeline. Both Fish and VoxCPM variants use these templates.

<details>
<summary>Chinese prompt</summary>

```text
你正在为 Fish Audio 准备有表现力的中文 TTS 输入。

输入：
- 历史对话 ASR 文本：由历史对话音频转写得到，用来理解当前上下文。
- 目标文本：现在需要被说出的句子。

历史对话 ASR 文本：
{history_text}

目标文本：
{target_text}

任务：
1. 分析当前说话情境。请根据历史对话和目标文本自行决定分析维度，不要从预设维度列表中选择。
2. 生成带有 Fish Audio 风格标签的目标文本。

Fish Audio 支持标签：
[happy], [sad], [angry], [fearful], [surprised], [disgusted], [neutral], [excited], [calm], [serious], [whisper], [shouting], [laughing], [crying], [sigh], [pause], [short pause], [long pause], [breath], [inhale], [exhale], [emphasis], [soft], [fast], [slow]

要求：
- 不要翻译目标文本。
- 除了插入短标签，目标文本正文尽量保持原样。
- 只能从上面的 Fish Audio 支持标签中选择标签，不要发明新标签。
- 只使用少量关键标签，不要过度打标签。
- 标签应放在影响其后语气的位置；如果描述整句，也可以放在句末。
- 标签必须是 [] 内的短英文标签。
- "analysis" 中每个分析维度都要简短，用短语或短句，不要写长段落。
- 只返回 JSON。

JSON 格式：
{
  "analysis": "...",
  "tagged_text": "..."
}
```

</details>

<details>
<summary>English prompt</summary>

```text
You are preparing expressive English TTS input for Fish Audio.

Inputs:
- History dialogue ASR text: previous dialogue context transcribed from history audio.
- Target text: the sentence that must be spoken now.

History dialogue ASR text:
{history_text}

Target text:
{target_text}

Task:
1. Analyze the current speaking situation. Decide the analysis dimensions yourself based on the history dialogue and target text; do not choose from a predefined list.
2. Produce the target text with short Fish Audio style tags in English square brackets.

Supported Fish Audio tags:
[happy], [sad], [angry], [fearful], [surprised], [disgusted], [neutral], [excited], [calm], [serious], [whisper], [shouting], [laughing], [crying], [sigh], [pause], [short pause], [long pause], [breath], [inhale], [exhale], [emphasis], [soft], [fast], [slow]

Requirements:
- Do not translate the target text.
- Keep the target text wording unchanged except for inserting short tags.
- Use tags only from the supported Fish Audio tag list above. Do not invent new tags.
- Use only a few helpful tags. Do not over-tag.
- Put tags inline where they affect delivery, or at the end only if they describe the whole utterance.
- Tags must be short English tags inside [].
- In "analysis", keep each analysis dimension brief. Use concise phrases or short sentences, not long paragraphs.
- Return JSON only.

JSON schema:
{
  "analysis": "...",
  "tagged_text": "..."
}
```

</details>

## 3. History audio → Qwen3-Omni → TTS

The user message contains the history audio followed by the following text prompt. Qwen3-Omni is called with `return_audio=False`; its textual JSON is adapted for Fish or VoxCPM as described above. R is supplied to the downstream TTS backend, not to this reasoning call.

<details>
<summary>Chinese prompt</summary>

```text
你正在为 Fish Audio 准备有表现力的中文 TTS 输入。

输入：
- 历史对话音频：之前的对话上下文，用来理解当前情境、人物关系、说话状态和表达方式。
- 目标文本：现在需要被说出的句子。

目标文本：
{target_text}

任务：
1. 分析当前说话情境。请根据历史对话音频和目标文本自行决定分析维度，不要从预设维度列表中选择。
2. 生成带有 Fish Audio 风格标签的目标文本。

Fish Audio 支持标签：
[happy], [sad], [angry], [fearful], [surprised], [disgusted], [neutral], [excited], [calm], [serious], [whisper], [shouting], [laughing], [crying], [sigh], [pause], [short pause], [long pause], [breath], [inhale], [exhale], [emphasis], [soft], [fast], [slow]

要求：
- 不要翻译目标文本。
- 除了插入短标签，目标文本正文尽量保持原样。
- 只能从上面的 Fish Audio 支持标签中选择标签，不要发明新标签。
- 只使用少量关键标签，不要过度打标签。
- 标签应放在影响其后语气的位置；如果描述整句，也可以放在句末。
- 标签必须是 [] 内的短英文标签。
- "analysis" 中每个分析维度都要简短，用短语或短句，不要写长段落。
- "analysis" 和 "tagged_text" 的值都必须是合法 JSON 字符串，必须用英文双引号包裹。
- 只返回 JSON。

JSON 格式：
{
  "analysis": "...",
  "tagged_text": "..."
}
```

</details>

<details>
<summary>English prompt</summary>

```text
You are preparing expressive English TTS input for Fish Audio.

Inputs:
- History dialogue audio: previous dialogue context. Use it to understand the current situation, relationship, speaker state, and intended delivery.
- Target text: the sentence that must be spoken now.

Target text:
{target_text}

Task:
1. Analyze the current speaking situation. Decide the analysis dimensions yourself based on the history dialogue audio and target text; do not choose from a predefined list.
2. Produce the target text with short Fish Audio style tags in English square brackets.

Supported Fish Audio tags:
[happy], [sad], [angry], [fearful], [surprised], [disgusted], [neutral], [excited], [calm], [serious], [whisper], [shouting], [laughing], [crying], [sigh], [pause], [short pause], [long pause], [breath], [inhale], [exhale], [emphasis], [soft], [fast], [slow]

Requirements:
- Do not translate the target text.
- Keep the target text wording unchanged except for inserting short tags.
- Use tags only from the supported Fish Audio tag list above. Do not invent new tags.
- Use only a few helpful tags. Do not over-tag.
- Put tags inline where they affect delivery, or at the end only if they describe the whole utterance.
- Tags must be short English tags inside [].
- In "analysis", keep each analysis dimension brief. Use concise phrases or short sentences, not long paragraphs.
- The values of "analysis" and "tagged_text" must be valid JSON strings wrapped in double quotes.
- Return JSON only.

JSON schema:
{
  "analysis": "...",
  "tagged_text": "..."
}
```

</details>

## 4. Native Qwen3-Omni speech → Seed-VC

The user message contains the history audio, the reference audio, and the following text prompt, in that order. Native audio is requested with `return_audio=True`, then converted by Seed-VC.

<details>
<summary>Chinese prompt</summary>

```text
你正在根据历史对话音频，为一个有表现力的中文 TTS 输出做情境和语气分析。

输入：
- 历史对话音频：用来理解当前上下文、人物关系和说话状态。
- 参考音频：用来参考说话人的音色和表达风格。
- 目标文本：现在需要被说出的句子。

目标文本：
{target_text}

任务：
只把历史对话音频和参考音频作为内部上下文，用来决定目标文本的表达方式。
随后为目标文本生成 TTS。

关键要求：
- 不要翻译目标文本。
- 可见的 assistant 文本必须只包含目标文本本身，不能包含其他任何内容。
- 音频中必须只说目标文本本身，不能说其他任何内容。
- 不要输出或读出分析、标签、括号、前缀、解释、总结、提示语或元信息。
- 不要说“下面是输出音频”“这是音频”“目标文本是”等类似说明。
- 目标文本正文必须保持原样。
```

</details>

<details>
<summary>English prompt</summary>

```text
You are preparing expressive English TTS output from audio context.

Inputs:
- History dialogue audio: use it to understand the current context, relationship, and speaking state.
- Reference audio: use it as a cue for speaker timbre and delivery style.
- Target text: the sentence that must be spoken now.

Target text:
{target_text}

Task:
Use the history dialogue audio and reference audio only as private context for choosing the delivery.
Then produce TTS for the target text.

Critical requirements:
- Do not translate the target text.
- The visible assistant text must be exactly the target text and nothing else.
- The audio must speak only the target text and nothing else.
- Do not output or speak analysis, labels, brackets, prefaces, explanations, summaries, or meta text.
- Do not say phrases such as "Here is the audio", "Below is the output audio", "The target text is", or similar.
- Keep the target text wording unchanged.
```

</details>
