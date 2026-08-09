window.DEMO_DATA = {
  "generated_at": "2026-08-09T12:24:35",
  "summary": {
    "num_eval_ids": 10,
    "num_model_entries": 100,
    "num_featured_cases": 2
  },
  "featured": [
    {
      "key": "res",
      "title": "Responding to another speaker",
      "history_audio": "featured/res/history_audio.wav",
      "target_text": "爹，你这叫什么话呀？你是因为担心我才过来帮我的。尤承安他满肚子阴谋诡计，是我连累了你啊。",
      "reference_audio": "featured/res/reference_audio.wav",
      "understanding_text": "没有爹没事儿。[安慰回应]\n他们有没有给你吃什么毒虫毒药？[担心询问]\n啊，没有。[平静否认]\n你怎么来了，是不是他们拿我要挟你？哎呀，爹真没用，一不留神就被他们打晕，带到这儿来了。本来是想帮你的，反倒成了你的累赘。[自责与失望]",
      "cot_text": "<Act>: 安慰父亲并澄清责任归属\n<Scene>: 对话中父亲出现帮助，但结果反成累赘\n<Motivation>: 不愿父亲因为被抓而责怪自己\n<Goal>: 希望父亲不要继续自责，并让他明白自己并不怪他\n<Emotion>: 情绪从心疼安慰逐渐转为愧疚自责\n<Valid duration | Total duration>: 7.630000s | 8.551250s\n<Loudness | Expressive Intensity>: -30.449077dBFS | 0.820557\n[Summary]\n因为父亲担心自己才赶来帮忙却遭到算计，所以先安慰父亲不要自责，随后将责任归于尤承安的阴谋，并因自己连累父亲而感到愧疚。",
      "output_audio": "featured/res/output_audio.wav"
    },
    {
      "key": "continue",
      "title": "Continuing the same speaker",
      "history_audio": "featured/continue/history_audio.wav",
      "target_text": "丞相本以位极人臣，突取而代之，难独天下悠悠之口，不得人心。",
      "reference_audio": "featured/continue/reference_audio.wav",
      "understanding_text": "此刻人人庆贺独他不贵幸讯，心生不快便出声发问朱增道。[心生不满] \n非丞相不可称帝，而是时机未到。[无奈解释] \n汉室虽微，然并无暴虐。[安抚解释]",
      "cot_text": "<Act>: 陈述事实\n<Scene>: 讨论丞相地位及不得人心的情况\n<Motivation>: 表达对丞相地位的担忧和不得人心的感慨\n<Goal>: 引起对方注意，可能希望对方理解当前困境\n<Emotion>: 延续之前的不满情绪，进一步表达无奈\n<Valid duration | Total duration>: 6.440000s | 7.981875s\n<Loudness | Expressive Intensity>: -31.489794dBFS | 0.850000\n[Summary]\n因为丞相地位难以取代且不得人心，所以无奈地担忧感慨。",
      "output_audio": "featured/continue/output_audio.wav"
    }
  ],
  "items": [
    {
      "eval_id": "eval-zh-175656",
      "language": "zh",
      "history_audio": "eval-zh-175656/final__our-0.6/history.wav",
      "reference_audio": "eval-zh-175656/reference_audio.wav",
      "target_text": "这围墙，咱俩四岁的时候就翻过，现在练就了一身功夫，倒是要抄起钥匙了。",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-zh-175656/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-175656/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-175656/final__our-1.7/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-175656/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-175656/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-175656/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-175656/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-175656/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-175656/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-175656/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-539281",
      "language": "zh",
      "history_audio": "eval-zh-539281/final__our-0.6/history.wav",
      "reference_audio": "eval-zh-539281/reference_audio.wav",
      "target_text": "去什么港岛？我提前毕业的申请都批了，我要一路向南建设特区。",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-zh-539281/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-539281/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-539281/final__our-1.7/output.wav"
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
      "eval_id": "eval-zh-78789",
      "language": "zh",
      "history_audio": "eval-zh-78789/final__our-0.6/history.wav",
      "reference_audio": "eval-zh-78789/reference_audio.wav",
      "target_text": "我跟你们说什么来着？你们看着别人是在挣钱，但我告诉你们，那是个大坑，是陷阱。",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-zh-78789/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-78789/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-78789/final__our-1.7/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-78789/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-78789/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-78789/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-78789/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-78789/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-78789/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-78789/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-837534",
      "language": "zh",
      "history_audio": "eval-zh-837534/final__our-0.6/history.wav",
      "reference_audio": "eval-zh-837534/reference_audio.wav",
      "target_text": "不必了，有我三位师弟在已经足够了。有需要我会再通知你们，你们退下吧。",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-zh-837534/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-837534/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-837534/final__our-1.7/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-837534/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-837534/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-837534/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-837534/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-837534/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-837534/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-837534/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-zh-888122",
      "language": "zh",
      "history_audio": "eval-zh-888122/final__our-0.6/history.wav",
      "reference_audio": "eval-zh-888122/reference_audio.wav",
      "target_text": "你可别吹了啊！你那策略不就烧钱吗？",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-zh-888122/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-888122/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-zh-888122/final__our-1.7/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-888122/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-888122/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-888122/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-zh-888122/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-888122/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-888122/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-zh-888122/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-100552",
      "language": "en",
      "history_audio": "eval-en-100552/final__our-0.6/history.wav",
      "reference_audio": "eval-en-100552/reference_audio.wav",
      "target_text": "Hardman has designs on my job. He's gonna need a power base. I need to make sure every department is happy. I can't do that alone.",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-en-100552/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-100552/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-100552/final__our-1.7/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-100552/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-100552/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-100552/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-100552/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-100552/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-100552/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-100552/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-1167838",
      "language": "en",
      "history_audio": "eval-en-1167838/final__our-0.6/history.wav",
      "reference_audio": "eval-en-1167838/reference_audio.wav",
      "target_text": "Fair, but you never watch my stories. Although I'm always hoping you would.",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-en-1167838/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1167838/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1167838/final__our-1.7/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1167838/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1167838/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1167838/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1167838/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1167838/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1167838/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1167838/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-1541641",
      "language": "en",
      "history_audio": "eval-en-1541641/final__our-0.6/history.wav",
      "reference_audio": "eval-en-1541641/reference_audio.wav",
      "target_text": "Don't do this. Don't throw away everything that we've worked so hard for.",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-en-1541641/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1541641/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-1541641/final__our-1.7/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1541641/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1541641/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1541641/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-1541641/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1541641/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1541641/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-1541641/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-284755",
      "language": "en",
      "history_audio": "eval-en-284755/final__our-0.6/history.wav",
      "reference_audio": "eval-en-284755/reference_audio.wav",
      "target_text": "You know what I've learned from screwing up so much? If your lady's mad and you have no idea why, there's only one thing to say.",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-en-284755/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-284755/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-284755/final__our-1.7/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-284755/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-284755/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-284755/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-284755/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-284755/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-284755/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-284755/two__qwen3omni-seedvc/output.wav"
        }
      ]
    },
    {
      "eval_id": "eval-en-955164",
      "language": "en",
      "history_audio": "eval-en-955164/final__our-0.6/history.wav",
      "reference_audio": "eval-en-955164/reference_audio.wav",
      "target_text": "We have two minutes to undo whatever she just did before it's too late.",
      "models": [
        {
          "key": "ground_truth",
          "display_key": "ground-truth",
          "name": "Ground Truth",
          "family": "gt",
          "family_label": "GT",
          "output_audio": "eval-en-955164/ground_truth/output.wav"
        },
        {
          "key": "final__our-0.6",
          "display_key": "our-0.6",
          "name": "Our-0.6B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-955164/final__our-0.6/output.wav"
        },
        {
          "key": "final__our-1.7",
          "display_key": "our-1.7",
          "name": "Our-1.7B",
          "family": "final",
          "family_label": "Our",
          "output_audio": "eval-en-955164/final__our-1.7/output.wav"
        },
        {
          "key": "three__dia-a3b-fish2",
          "display_key": "three__dia-a3b-fish2",
          "name": "Three-stage: DiA + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-955164/three__dia-a3b-fish2/output.wav"
        },
        {
          "key": "three__dia-a3b-voxcpm",
          "display_key": "three__dia-a3b-voxcpm",
          "name": "Three-stage: DiA + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-955164/three__dia-a3b-voxcpm/output.wav"
        },
        {
          "key": "three__qwen3asr-a3b-fish2",
          "display_key": "three__qwen3asr-a3b-fish2",
          "name": "Three-stage: Qwen3-ASR + A3B + Fish2",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-955164/three__qwen3asr-a3b-fish2/output.wav"
        },
        {
          "key": "three__qwenasr-a3b-voxcpm",
          "display_key": "three__qwenasr-a3b-voxcpm",
          "name": "Three-stage: Qwen-ASR + A3B + VoxCPM",
          "family": "three",
          "family_label": "Three-stage",
          "output_audio": "eval-en-955164/three__qwenasr-a3b-voxcpm/output.wav"
        },
        {
          "key": "two__qwen-fish",
          "display_key": "two__qwen-fish",
          "name": "Two-stage: Qwen + Fish",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-955164/two__qwen-fish/output.wav"
        },
        {
          "key": "two__qwen-voxcpm",
          "display_key": "two__qwen-voxcpm",
          "name": "Two-stage: Qwen + VoxCPM",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-955164/two__qwen-voxcpm/output.wav"
        },
        {
          "key": "two__qwen3omni-seedvc",
          "display_key": "two__qwen3omni-seedvc",
          "name": "Two-stage: Qwen3-Omni + SeedVC",
          "family": "two",
          "family_label": "Two-stage",
          "output_audio": "eval-en-955164/two__qwen3omni-seedvc/output.wav"
        }
      ]
    }
  ]
};
