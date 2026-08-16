window.CONTROL_DEMO_DATA = {
  case_id: "eval-zh-837534",
  language: "zh",
  default_case: {
    history_audio: "control/zh_837534/history_audio.wav",
    target_text: "不必了，有我三位师弟在已经足够了。有需要我会再通知你们，你们退下吧。",
    cot_text:
      "<Act>: 拒绝并安排退下\n<Scene>: 对话中，对方多次表达关心，但Speaker-1显得不耐烦，可能是在处理某种事务或安排\n<Motivation>: Speaker-1可能感到被烦扰，希望结束对话，专注于自己的事务\n<Goal>: 希望对方退下，结束当前对话\n<Emotion>: 情绪略带不耐烦，情绪有所缓和，但仍有不满\n<Valid duration | Total duration>: 4.230000s | 5.535000s\n<Loudness | Expressive Intensity>: -31.245544dBFS | 0.765820\n[Summary]\n因为Speaker-1感到被烦扰，所以用'略带不耐烦'的方式说了'不必了，有我三位师弟在已经足够了，有需要我会再通知你们退下。'",
    output_audio: "control/zh_837534/default.wav",
  },
  rows: [
    {
      variable: "Total duration",
      note: "Edit the overall utterance length while preserving the same dialogue context.",
      items: [
        { label: "4.5s", audio: "control/zh_837534/time_4.wav" },
        { label: "6.5s", audio: "control/zh_837534/time_6.wav" },
        { label: "7.5s", audio: "control/zh_837534/time_7.wav" },
        { label: "8.5s", audio: "control/zh_837534/time_8.wav" },
      ],
    },
    {
      variable: "Rhythm",
      note: "Edit valid duration and total duration jointly to reshape the speaking rhythm.",
      items: [
        { label: "3.2s / 4.1s", audio: "control/zh_837534/rhythm_3p2_4p1.wav" },
        { label: "3.7s / 4.8s", audio: "control/zh_837534/rhythm_3p7_4p8.wav" },
        { label: "4.9s / 6.4s", audio: "control/zh_837534/rhythm_4p9_6p4.wav" },
        { label: "5.6s / 7.5s", audio: "control/zh_837534/rhythm_5p6_7p5.wav" },
      ],
    },
    {
      variable: "Expressive intensity",
      note: "Edit the expressive-intensity value to strengthen or soften the emotional delivery.",
      items: [
        { label: "0.5", audio: "control/zh_837534/emo_0p5.wav" },
        { label: "0.6", audio: "control/zh_837534/emo_0p6.wav" },
        { label: "0.8", audio: "control/zh_837534/emo_0p8.wav" },
        { label: "0.9", audio: "control/zh_837534/emo_0p9.wav" },
      ],
    },
  ],
};
