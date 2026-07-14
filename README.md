# COTalker

COTalker is a context-aware reasoning speech generation framework. Given
historical dialogue audio, target text, and a reference speaker utterance,
COTalker first builds an explicit chain-of-thought interpretation of the
dialogue context, then reasons about the intended speaking manner, and finally
generates expressive target speech with the target speaker timbre.

This repository currently hosts the public demo page and links to the resources
used in our competition submission. More code, data, and evaluation resources
will be released progressively.

## Released Resources

| Resource | Status | Link |
| --- | --- | --- |
| Proposal | Released | [arXiv](https://arxiv.org/abs/2606.21933) |
| Challenge website | Released | [Website](https://iscslp2026-cot-tts.github.io/challenge-website/) |
| Challenge dataset | Released | [Hugging Face](https://huggingface.co/datasets/HKUSTAudio/ISCSLP2026-CoT-TTS) |
| Challenge baseline | Released | [GitHub](https://github.com/iscslp2026-cot-tts/baseline) |
| Demo page source | Released | [Demo Page](https://luckybian.github.io/COTalker/index.html) |
| Model checkpoints and inference scripts | [GitHub](https://github.com/LuckyBian/COTalker/tree/main/inference)  |

## Coming Soon

| Resource | Status |
| --- | --- |
| Full dataset | Coming soon |
| Data processing pipeline | Coming soon |
| Training code | Coming soon |
| Evaluation data | Coming soon |
| Evaluation protocols and metrics | Coming soon |

## Demo Page

The demo page lives in [Demo Page](https://luckybian.github.io/COTalker/index.html). It is a fully static website
with a short project overview, architecture figures, representative COTalker
examples, and a comparison table containing historical dialogue audio, target
text, model names, and generated audio.

To preview locally:

```bash
cd web-demo
python -m http.server 8898
```

Then open:

```text
http://localhost:8898
```

No backend or build step is required.

## Citation

Citation information will be added after the corresponding paper or technical
report is available.
