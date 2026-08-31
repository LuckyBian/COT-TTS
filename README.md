# COT-TTS

COT-TTS is a context-aware reasoning text-to-speech task. Given historical
dialogue audio, target text, and reference speech, a system is required to
infer the intended speaking manner, generate explicit intermediate reasoning,
and synthesize contextually appropriate speech with the specified speaker
timbre.

This repository currently hosts the public demo page and the released challenge
resources. Additional code, data, and evaluation resources will be released
progressively.

## Released Resources

| Resource  | Link |
| ---  | --- |
| Challenge proposal | [https://arxiv.org/abs/2606.21933](https://arxiv.org/abs/2606.21933) |
| Challenge website | [https://iscslp2026-cot-tts.github.io/challenge-website/](https://iscslp2026-cot-tts.github.io/challenge-website/) |
| Training Dataset | [https://huggingface.co/datasets/HKUSTAudio/ISCSLP2026-CoT-TTS](https://huggingface.co/datasets/HKUSTAudio/ISCSLP2026-CoT-TTS) |
| Open-source model | [https://github.com/LuckyBian/COT-TTS/tree/main/infer](https://github.com/LuckyBian/COT-TTS/tree/main/infer) |
| Training code | [https://github.com/LuckyBian/COT-TTS/tree/main/train](https://github.com/LuckyBian/COT-TTS/tree/main/train) |
| Challenge baseline | [https://github.com/iscslp2026-cot-tts/baseline](https://github.com/iscslp2026-cot-tts/baseline) |
| Demo page | [https://luckybian.github.io/COT-TTS](https://luckybian.github.io/COT-TTS) |

## Coming Soon

| Resource | Status |
| --- | --- |
| COT-TTS paper | Coming soon |
| Data processing pipeline | Coming soon |
| Evaluation data | Coming soon |

## Demo Page

The demo page lives at [https://luckybian.github.io/COT-TTS](https://luckybian.github.io/COT-TTS).
It is a fully static website with a short project overview, architecture
figures, representative featured examples, and a comparison table containing
historical dialogue audio, target text, model names, and generated audio.

To preview locally:

```bash
cd docs
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
