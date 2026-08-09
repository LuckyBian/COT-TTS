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

| Resource  | Link |
| ---  | --- |
| Proposal  | [arXiv](https://arxiv.org/abs/2606.21933) |
| Challenge website  | [Website](https://iscslp2026-cot-tts.github.io/challenge-website/) |
| Challenge dataset  | [Hugging Face](https://huggingface.co/datasets/HKUSTAudio/ISCSLP2026-CoT-TTS) |
| Challenge baseline  | [GitHub](https://github.com/iscslp2026-cot-tts/baseline) |
| Demo page source  | [Demo Page](https://luckybian.github.io/COTalker/index.html) |
| Full dataset  | [Hugging Face](https://huggingface.co/datasets/HKUSTAudio/cot_tts) |

## Coming Soon

| Resource | Status |
| --- | --- |
| COTalker paper | Coming soon |
| Cascated system | Coming soon |
| Data processing pipeline | Coming soon |
| Evaluation data | To be released on August 3, 2026 |
| Evaluation protocols and metrics | To be released on August 3, 2026 |

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
