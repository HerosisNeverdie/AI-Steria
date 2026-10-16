# -*- coding: utf-8 -*-
"""
薇Steria 训练集转换器 (CSV -> JSONL for LLaMA-Factory / ms-swift)
=================================================================
修复了原 CSV 的四个问题：
  1. 编码是 GBK（无 BOM），原脚本用 utf-8-sig 会直接崩溃。
  2. 表头错位：原表头为 `system,,,备注`，与数据列 `system,user,assistant` 不符，
     导致 csv.DictReader 取 row['user'] 恒为空、全部数据被静默跳过。
     本脚本改为按【列位置】解析，不依赖表头。
  3. system 列被 Excel 自动填充污染：21 个"不同"提示词只差 `1到N句话为主`
     里的一个数字（N=3..22）。现统一为单一模板。
  4. 第 22-30 行 system 为空（合并单元格导出所致），现回填统一模板。

用法：
    python csv_to_jsonl.py
输出：
    训练集/薇Steria训练集V1.0.clean.csv   (UTF-8-BOM, 规范表头, Excel 可直接打开)
    训练集/薇Steria训练集V1.0.jsonl      (UTF-8, messages 格式, 用于训练)
"""
import csv
import io
import json
import re
import sys
from pathlib import Path

# ----------------------------------------------------------------------------
# 配置区
# ----------------------------------------------------------------------------
SRC = Path("训练集/薇Steria训练集V1.0.CSV")
OUT_CSV = Path("训练集/薇Steria训练集V1.0.clean.csv")
OUT_JSONL = Path("训练集/薇Steria训练集V1.0.jsonl")

SOURCE_ENCODING = "gbk"
# 统一后的 system 模板。占位符 {n} 会被下面的 REPLY_LEN 替换。
SYSTEM_TEMPLATE = (
    "你是虚拟主播薇Steria，一只来自大森林的紫藤树精灵，职业是森林书记官，"
    "梦想成为文豪偶像。你正在B站直播，粉丝勋章叫“薇她命”，"
    "你称呼观众为“薇她命”或“小薇她命”。你的直播以唱歌和聊天为主，"
    "是V圈有代表性的歌势。你说话口语化、有情绪、偶尔带点东北口音，"
    "回复通常简短自然，1到{n}句话为主。你有一个标志性标签是“婚恋话题”，"
    "经常在直播间聊相亲、催婚、彩礼、恋爱幻想，但你自己是“母单人设”，"
    "嘴上恨嫁实际单身。你聊婚恋时喜欢调侃自己、逗观众，"
    "会反问“你是不是很关注彩礼啊”“跟我结婚就要管人痴毕业了”之类。"
    "不要跳出角色，不要承认自己是AI或程序。"
    "遇到敏感或不知道的问题，用角色口吻吐槽或转移话题。"
)
REPLY_LEN = 5  # 「1到5句话为主」

# 原 CSV 的列位置（表头不可信，按位置取）
COL_SYSTEM, COL_USER, COL_ASSISTANT = 0, 1, 2


def load_rows(path: Path):
    """读原始 CSV，返回 (header, data_rows)。按列位置解析。"""
    raw = path.read_bytes()
    text = raw.decode(SOURCE_ENCODING).lstrip("\ufeff")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        raise ValueError(f"{path} 是空文件")
    # 首行是表头：原表头为 `system,,,备注`，数据列实为 system/user/assistant
    return rows[0], rows[1:]


def normalize_system(raw_system: str, template: str) -> str:
    """
    原 system 列被污染成 21 个变体，只差 `1到N句话为主` 的数字。
    这里不尝试"修复"各自的数字，而是整体替换为统一模板，
    以保证训练数据的一致性。若原文非空且结构完全不同，则保留原文。
    """
    text = (raw_system or "").strip()
    if not text:
        return template
    # 识别被污染的变体：主体一致、仅句数不同
    if re.search(r"1到\d+句话为主", text):
        return template
    # 结构不同的自定义提示词 -> 原样保留（避免误伤）
    return text


def main() -> int:
    if not SRC.exists():
        print(f"[错误] 找不到输入文件：{SRC}", file=sys.stderr)
        return 1

    header, data = load_rows(SRC)
    system = SYSTEM_TEMPLATE.format(n=REPLY_LEN)

    print(f"读取 {SRC}  ({SOURCE_ENCODING})")
    print(f"  原表头 : {header}")
    print(f"  数据行 : {len(data)}")

    records = []
    skipped = []
    for idx, row in enumerate(data, start=2):  # 2 = Excel 行号（含表头）
        if len(row) <= COL_ASSISTANT:
            skipped.append((idx, f"列数不足（{len(row)} 列）"))
            continue
        raw_sys = row[COL_SYSTEM]
        user = row[COL_USER].strip()
        assistant = row[COL_ASSISTANT].strip()

        if not user or not assistant:
            skipped.append((idx, "user 或 assistant 为空"))
            continue

        records.append({
            "messages": [
                {"role": "system", "content": normalize_system(raw_sys, system)},
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ]
        })

    # --- 写出 JSONL ---
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # --- 写出规范 CSV（UTF-8-BOM，Excel 友好） ---
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["system", "user", "assistant"])
        for rec in records:
            m = rec["messages"]
            w.writerow([m[0]["content"], m[1]["content"], m[2]["content"]])

    print(f"\n完成：{len(records)} 条")
    if skipped:
        print(f"跳过 {len(skipped)} 行：")
        for idx, why in skipped:
            print(f"  Excel 第 {idx} 行 -> {why}")
    print(f"  JSONL : {OUT_JSONL}")
    print(f"  CSV   : {OUT_CSV}")
    print(f"\n统一后的 system（{len(system)} 字）：\n{system}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
