window.DEMO_DATA = {
  "generated_at": "2026-07-13T14:43:33",
  "summary": {
    "num_eval_ids": 16,
    "num_model_entries": 176,
    "num_featured_cases": 2
  },
  "featured": [
    {
      "key": "res",
      "title": "Responding to another speaker",
      "history_audio": "featured/res/history_audio.wav",
      "target_text": "不必了，有我三位师弟在已经足够了。有需要我会再通知你们，你们退下吧。",
      "reference_audio": "featured/res/reference_audio.wav",
      "understanding_text": "我这次回来只是为了探亲，不必如此招摇过市。[严肃] \n是!令主大人,属下为您挑选了几位高手护您周全。[陈述]",
      "cot_text": "<Act>: 拒绝护送提议，表达自信\n<Scene>: 拒绝多余的护送，保持低调\n<Motivation>: 自信且独立，不愿依赖他人\n<Goal>: 希望对方退下，避免麻烦\n<Emotion>: 从之前的严肃转向坚定拒绝\n<Valid duration | Total duration>: 3.730000s | 5.349375s\n<Loudness | Expressive Intensity>: -31.379914dBFS | 0.850000\n<Naturalness Score>: 4.000000\n<Noise Score>: 4.500000\n[Summary]\n因为说话人自信且独立，所以用自信的方式坚决拒绝'不必了，有我三位师弟在已经足够了，有需要我会再通知你们退下。'",
      "output_audio": "featured/res/output_audio.wav"
    },
    {
      "key": "continue",
      "title": "Continuing the same speaker",
      "history_audio": "featured/continue/history_audio.wav",
      "target_text": "丞相本以位极人臣，突取而代之，难独天下悠悠之口，不得人心。",
      "reference_audio": "featured/continue/reference_audio.wav",
      "understanding_text": "此刻人人庆贺独他不贵幸讯，心生不快便出声发问朱增道。[心生不满] \n非丞相不可称帝，而是时机未到。[无奈解释] \n汉室虽微，然并无暴虐。[安抚解释]",
      "cot_text": "<Act>: 陈述事实\n<Scene>: 讨论丞相地位及不得人心的情况\n<Motivation>: 表达对丞相地位的担忧和不得人心的感慨\n<Goal>: 引起对方注意，可能希望对方理解当前困境\n<Emotion>: 延续之前的不满情绪，进一步表达无奈\n<Valid duration | Total duration>: 6.440000s | 7.981875s\n<Loudness | Expressive Intensity>: -31.489794dBFS | 0.850000\n<Naturalness Score>: 4.000000\n<Noise Score>: 4.500000\n[Summary]\n因为丞相地位难以取代且不得人心，所以无奈地愤怒的感慨。",
      "output_audio": "featured/continue/output_audio.wav"
    }
  ],
  "items": [
    {
      "eval_id": "eval-en-103618",
      "language": "en",
      "history_audio": "eval-en-103618/final__our-0.6/history.wav",
      "target_text": "I'm not breaking the law. I put the goddamn thing in there. They can find it if they can think to look.",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-103618/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-103618/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-103618/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-103618/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-103618/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-103618/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-103618/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-103618/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-103618/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-103618/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-103618/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-1179847",
      "language": "en",
      "history_audio": "eval-en-1179847/final__our-0.6/history.wav",
      "target_text": "But he's the only key I have to finding my sister. Besides, killing him is not going to fix your real.",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1179847/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1179847/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1179847/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1179847/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1179847/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1179847/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1179847/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1179847/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1179847/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1179847/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1179847/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-1537564",
      "language": "en",
      "history_audio": "eval-en-1537564/final__our-0.6/history.wav",
      "target_text": "I got no reason to lie to you. Just give him the car, and we both get to live.",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1537564/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1537564/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1537564/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1537564/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1537564/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1537564/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1537564/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1537564/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1537564/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1537564/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1537564/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-1657303",
      "language": "en",
      "history_audio": "eval-en-1657303/final__our-0.6/history.wav",
      "target_text": "Yeah, she was a nightmare, but she was the closest thing we had to a mother.",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1657303/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1657303/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1657303/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1657303/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1657303/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1657303/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1657303/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1657303/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1657303/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1657303/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1657303/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-370534",
      "language": "en",
      "history_audio": "eval-en-370534/final__our-0.6/history.wav",
      "target_text": "I will not permit you to risk everything we are doing here. There is simply too much at stake.",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-370534/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-370534/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-370534/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-370534/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-370534/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-370534/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-370534/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-370534/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-370534/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-370534/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-370534/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-689535",
      "language": "en",
      "history_audio": "eval-en-689535/final__our-0.6/history.wav",
      "target_text": "Look, we all have people we want to get back to, and we're gonna try and find a way. But nothing's gonna happen if we starve to death.",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-689535/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-689535/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-689535/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-689535/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-689535/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-689535/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-689535/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-689535/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-689535/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-689535/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-689535/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-763759",
      "language": "en",
      "history_audio": "eval-en-763759/final__our-0.6/history.wav",
      "target_text": "Say it, motherfucker! I dare you. Say this was the last place your boss was seen.",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-763759/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-763759/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-763759/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-763759/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-763759/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-763759/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-763759/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-763759/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-763759/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-763759/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-763759/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-982121",
      "language": "en",
      "history_audio": "eval-en-982121/final__our-0.6/history.wav",
      "target_text": "There's still a lot of people panicking out there, so we need to make sure they know this is a false alarm and find whoever did this.",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-982121/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-982121/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-982121/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-982121/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-982121/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-982121/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-982121/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-982121/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-982121/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-982121/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-982121/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-1006034",
      "language": "zh",
      "history_audio": "eval-zh-1006034/final__our-0.6/history.wav",
      "target_text": "就因为我是乔家人，所以只能被你们误会责骂，永远不能翻身吗？",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-1006034/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-1006034/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-1006034/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-1006034/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-1006034/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-1006034/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-1006034/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-1006034/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-1006034/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-1006034/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-1006034/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-101214",
      "language": "zh",
      "history_audio": "eval-zh-101214/final__our-0.6/history.wav",
      "target_text": "今后你们有机会站在世界的舞台上，你们所代表的，是中国人的精神。",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-101214/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-101214/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-101214/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-101214/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-101214/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-101214/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-101214/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-101214/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-101214/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-101214/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-101214/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-1084075",
      "language": "zh",
      "history_audio": "eval-zh-1084075/final__our-0.6/history.wav",
      "target_text": "本尊就站在这儿，你若能杀得了本尊，来杀便是。",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-1084075/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-1084075/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-1084075/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-1084075/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-1084075/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-1084075/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-1084075/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-1084075/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-1084075/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-1084075/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-1084075/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-161950",
      "language": "zh",
      "history_audio": "eval-zh-161950/final__our-0.6/history.wav",
      "target_text": "老人家，你若如此顽抗，莫怪本官不客气。",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-161950/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-161950/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-161950/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-161950/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-161950/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-161950/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-161950/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-161950/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-161950/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-161950/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-161950/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-539281",
      "language": "zh",
      "history_audio": "eval-zh-539281/final__our-0.6/history.wav",
      "target_text": "去什么港岛？我提前毕业的申请都批了，我要一路向南建设特区。",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-539281/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-539281/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-539281/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-539281/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-539281/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-539281/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-539281/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-539281/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-539281/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-539281/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-539281/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-796511",
      "language": "zh",
      "history_audio": "eval-zh-796511/final__our-0.6/history.wav",
      "target_text": "不是说永令春是个暴脾气，一点就爆吗？",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-796511/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-796511/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-796511/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-796511/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-796511/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-796511/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-796511/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-796511/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-796511/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-796511/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-796511/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-969498",
      "language": "zh",
      "history_audio": "eval-zh-969498/final__our-0.6/history.wav",
      "target_text": "怪我，怪我一时鬼迷心窍，竟然想做出。",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-969498/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-969498/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-969498/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-969498/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-969498/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-969498/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-969498/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-969498/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-969498/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-969498/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-969498/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-996310",
      "language": "zh",
      "history_audio": "eval-zh-996310/final__our-0.6/history.wav",
      "target_text": "他们骁勇又如何，还不是要败？将军不知，这更痛快的，在这儿。",
      "models": [
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "COTalker-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-996310/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-0.6-edit",
          "display_key": "our-0.6-edit",
          "name": "COTalker-0.6B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-996310/final__our-0.6-edit/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "COTalker-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-996310/final__our-1.7/output.wav"
        },
        {
          "key": "final__our-1.7-edit",
          "display_key": "our-1.7-edit",
          "name": "COTalker-1.7B Edit",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-996310/final__our-1.7-edit/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-996310/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-996310/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-996310/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-996310/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-996310/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-996310/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-996310/two__qwen3omni-seedvc/output.wav"
        }
      ]
    }
  ]
};
