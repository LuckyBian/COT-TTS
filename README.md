# COTalker

COTalker is a context-aware and reasoning-guided text-to-speech system. Given
historical dialogue audio and a target utterance, COTalker first builds an
explicit chain-of-thought style interpretation of the dialogue context,
including speaker intent, scene, motivation, goal, emotion, and speaking style.
The model then uses this structured reasoning to generate expressive speech
that better matches the target text, dialogue context, and speaker state.

This repository currently hosts the public demo page and links to the resources
used in our competition submission. More code, data, and evaluation resources
will be released progressively.

## Released Resources

| Resource | Status | Link |
| --- | --- | --- |
| Competition proposal | Released | [Link](https://example.com/cotalker-proposal) |
| Competition website | Released | [Link](https://example.com/cotalker-competition) |
| Competition baseline | Released | [Link](https://example.com/cotalker-baseline) |
| Competition data | Released | [Link](https://example.com/cotalker-data) |
| Demo page | Released | [Link](https://example.com/cotalker-demo) |

## Coming Soon

| Resource | Status |
| --- | --- |
| Full dataset | Coming soon |
| Data processing pipeline | Coming soon |
| Model checkpoints and inference scripts | Coming soon |
| Training code | Coming soon |
| Evaluation data | Coming soon |
| Evaluation protocols and metrics | Coming soon |

## Demo Page

The demo page is a fully static website. It includes representative COTalker
examples and a comparison table with historical dialogue audio, target text,
model names, and generated audio.

To preview locally:

```bash
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
