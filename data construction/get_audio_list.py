from pathlib import Path
import pandas as pd

# 设置音频目录和输出TSV文件路径
repo_root = Path(__file__).resolve().parent
audio_dir = repo_root / "data" / "audios"
tsv_path = repo_root / "data" / "audio_list.tsv"

# 获取所有音频文件路径（支持常见格式）
audio_files = sorted(
    [str(f.relative_to(repo_root)) for f in audio_dir.glob("*") if f.suffix.lower() in [".wav", ".mp3", ".flac", ".m4a"]]
)

# 写入TSV文件
df = pd.DataFrame(audio_files, columns=["path"])
tsv_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(tsv_path, sep="\t", index=False)
