# 薇Steria 训练集

用于微调 AI薇Steria 角色扮演能力的对话数据集。当前版本 **V1.1（27 条）**。

## 文件清单

| 文件 | 版本 | 编码 | 大小 | 说明 |
| --- | --- | --- | --- | --- |
| [`薇Steria训练集V1.1.jsonl`](薇Steria训练集V1.1.jsonl) | **V1.1** | UTF-8 | 16 KB | **训练用（当前版本）**，27 条 |
| [`薇Steria训练集V1.1.clean.csv`](薇Steria训练集V1.1.clean.csv) | **V1.1** | UTF-8+BOM | 13 KB | 同内容表格版，Excel 可直接打开 |
| [`V1.1_改动说明.md`](V1.1_改动说明.md) | — | UTF-8 | 18 KB | V1.0 → V1.1 逐条 before/after 对照 |
| [`薇Steria训练集V1.0.jsonl`](薇Steria训练集V1.0.jsonl) | V1.0 | UTF-8 | 35 KB | 上一版，29 条，保留作对照 |
| [`薇Steria训练集V1.0.clean.csv`](薇Steria训练集V1.0.clean.csv) | V1.0 | UTF-8+BOM | 31 KB | 同内容表格版 |
| [`薇Steria训练集V1.0.CSV`](薇Steria训练集V1.0.CSV) | V1.0 | **GBK** | 16 KB | 原始导出文件，表头有错位，仅作存档 |

> **推荐直接使用 `薇Steria训练集V1.1.jsonl`。**

## 数据格式

### jsonl

每行一个独立 JSON 对象，可直接用于 OpenAI / LLaMA-Factory / ms-swift / Axolotl 等框架：

```json
{"messages":[
  {"role":"system",    "content":"你是虚拟主播薇Steria……"},
  {"role":"user",      "content":"……"},
  {"role":"assistant", "content":"……"}
]}
```

- 全部 27 条共用同一个 system 提示词
- `ensure_ascii=False`，中文以 UTF-8 原样存储
- 单轮对话（system / user / assistant 各一条）

### clean.csv

```csv
system,user,assistant
"你是虚拟主播薇Steria…","观众的问题…","薇Steria 的回复…"
```

三列对应对话的三条消息，行内遵循 RFC 4180 引号转义规则（`""` 表示一个双引号）。

## V1.1 修订内容

V1.0 单条样本的 system 占 297 字，而 27 条 assistant 加起来才 1141 字——system 抢了约 1/4 的 token，还写着一堆对话里从未出现过的设定。V1.1 三列都做了调整：

**system：297 → 111 字**
- 删掉数据里 0 次出现的设定：紫藤树精灵、森林书记官、文豪偶像、东北口音、V圈歌势等
- 补上数据里占比最大、原 system 却完全没提的一项：**聊动画、吐槽角色**（10/27 条）
- 回复长度从「1到5句话为主」对齐成「1到3句为主」，与改短后的 assistant 一致
- 修订后 system : assistant 总量 = **1 : 10.3**（原为 1 : 3.8）

**assistant：平均 64 → 42 字，最长 321 → 93 字**
- 行数 **29 → 27**（删掉 2 条弱相关：原第 6 行答非所问、原第 12 行只回「哈哈哈」）
- 12 行精简改写，15 行原文本来就 ≤ 100 字，**原样保留**——没有为了凑字数往里加内容

**user：修了 7 处 ASR 错字**（其余 20 行逐字未改）
- 「灵活底色」→灵魂底色、「远离显示」→远离现实、「主包」→主播、「男楞」→男人
- 补漏字：「那不得一百个」「所以让人向往」
- 「的」→「得」：「美好得不切实际」「多姿多彩得多」「死得早」
- 只修听错/漏字，不改提问意思；脚本强制每处改动与原句相似度 ≥ 0.75

详见 [`V1.1_改动说明.md`](V1.1_改动说明.md)。

## 数据一致性

- V1.1 的 `jsonl` 与 `clean.csv`：**27/27 条内容完全一致**，两种格式可互换
- V1.1 全部 27 行均为**合法 JSON**，消息结构统一为 `system → user → assistant`

## 原始数据（V1.0.CSV）的四个问题

`薇Steria训练集V1.0.CSV` 是原始导出文件，存在以下问题，转 clean 版时已全部处理：

1. **编码为 GBK（无 BOM）** —— 直接按 UTF-8 读取会抛 `UnicodeDecodeError`
2. **表头错位** —— 原表头是 `system,,,备注`，但数据列实际为 `system,user,assistant`。用 `csv.DictReader` 按列名取值时 `row['user']` 恒为空，会导致 29 条数据被**静默全部跳过**
3. **system 列被 Excel 自动填充污染** —— 原有的 21 个「不同」提示词，逐字比对后只差 `回复通常简短自然，1到N句话为主` 里的一个数字（N=3..22）
4. **部分行 system 为空** —— 合并单元格导出只把值写入首行所致，现已回填统一模板

## ⚠️ 编码注意事项

`薇Steria训练集V1.0.CSV` 是 **GBK** 编码且不带 BOM。在 GitHub 网页上直接查看该文件会显示乱码——这是编码问题，**不是文件损坏**。下载后请用支持 GBK 的工具打开：

```powershell
# PowerShell（Windows 中文环境默认 GBK，可直接读）
Get-Content .\薇Steria训练集V1.0.CSV

# 转换为 UTF-8
$gbk = [System.Text.Encoding]::GetEncoding("GBK")
$text = $gbk.GetString([System.IO.File]::ReadAllBytes(".\薇Steria训练集V1.0.CSV"))
[System.IO.File]::WriteAllText(".\converted.csv", $text, (New-Object System.Text.UTF8Encoding $true))
```

```python
# Python
import pandas as pd
df = pd.read_csv("薇Steria训练集V1.0.CSV", encoding="gbk")
```

**日常请使用 V1.1 的 `jsonl` 或 `clean.csv`**，两者都是标准 UTF-8。

## 用法示例

```python
import json

with open("薇Steria训练集V1.1.jsonl", encoding="utf-8") as f:
    samples = [json.loads(line) for line in f if line.strip()]

print(len(samples))                       # 27
print(samples[0]["messages"][0]["role"])  # system
print(len(samples[0]["messages"][0]["content"]), "字")  # 111
```

```python
import pandas as pd

df = pd.read_csv("薇Steria训练集V1.1.clean.csv", encoding="utf-8-sig")
print(df.columns.tolist())  # ['system', 'user', 'assistant']
print(len(df))              # 27
```

## 人设概要

薇Steria 是 B 站虚拟主播，粉丝叫「薇她命」。说话口语化、有情绪，爱笑爱反问，回复简短（1~3 句）。招牌话题是**婚恋**：相亲、彩礼、恋爱幻想，嘴上恨嫁实际单身；也爱**聊动画、吐槽角色**。

> ⚠️ V1.1 已删除「紫藤树精灵」「森林书记官」「文豪偶像」等设定——因为训练数据里从未出现，保留只会让模型学不到、却以为该演。若模型被问到这些还答得头头是道，那是它在用预训练知识**自己编造**。

## 版本历史

| 版本 | 条数 | system 字数 | assistant 均长 | 说明 |
| --- | --- | --- | --- | --- |
| V1.0 | 29 | 297 | 64 字 | 首版，system 冗长、含无数据支持的设定 |
| **V1.1** | **27** | **111** | **42 字** | system 贴数据、assistant 改短、user 修错字 |

## 相关目录

- [`../评测集/`](../评测集/) —— 检验微调后模型「像不像薇Steria」的评分表
- [`../tools/`](../tools/) —— 数据构建与校验脚本（`build_v1_1.py`、`verify_v1_1.py`、`verify_eval.py`、`eval_to_jsonl.py`、`csv_to_jsonl.py`）
