# 薇Steria 训练集 V1.0

用于微调 AI薇Steria 人设的对话数据集。共 **29 条**对话样本，同一批内容的三种格式。

## 文件清单

| 文件 | 编码 | 大小 | 说明 |
| --- | --- | --- | --- |
| `薇Steria训练集V1.0.CSV` | **GBK** | 16 KB | 原始版本，保留未改动 |
| `薇Steria训练集V1.0.clean.csv` | UTF-8 (BOM) | 31 KB | 清洗版，修正表头并统一人设，**推荐使用** |
| `薇Steria训练集V1.0.jsonl` | UTF-8 | 35 KB | 与 clean.csv 内容一致，OpenAI 微调格式 |

## 数据格式

### clean.csv

```csv
system,user,assistant
"你是虚拟主播薇Steria…","观众的问题…","薇Steria 的回复…"
```

三列分别对应对话的三条消息，行内遵循 RFC 4180 引号转义规则（`""` 表示一个双引号）。

### jsonl

每行一个独立 JSON 对象，可直接用于 OpenAI 微调接口：

```json
{"messages":[{"role":"system","content":"…"},{"role":"user","content":"…"},{"role":"assistant","content":"…"}]}
```

## 原始版与清洗版的差异

对比两个 CSV 后确认的差异如下：

| 项目 | 原始 CSV | clean.csv |
| --- | --- | --- |
| 编码 | GBK | UTF-8 with BOM |
| 表头 | `system,,,备注`（第 2、3 列为空） | `system,user,assistant` ✅ |
| 列数 | 4 列（末列为空的「备注」） | 3 列 ✅ |
| system 人设变体 | **21 种** | **1 种**（统一） |
| 「备注」列内容 | 29 行全为空 | 该列已移除 |
| user / assistant 内容 | — | **与原始版逐字符完全一致** |

清洗版采用的 system 人设，经逐字符比对，等于原始版中的**第 3 种人设变体**：

> 你是虚拟主播薇Steria，一只来自大森林的紫藤树精灵，职业是森林书记官，梦想成为文豪偶像。你正在B站直播，粉丝勋章叫"薇她命"，你称呼观众为"薇她命"或"小薇她命"。你的直播以唱歌和聊天为主，是V圈有代表性的歌势。你说话口语化、有情绪、偶尔带点东北口音，回复通常简短自然，1到5句话为主。…

### 关于 21 种人设变体

原始 CSV 的每一行都带有一份略有不同的人设描述（差异集中在「回复通常简短自然，**1到N句话**为主」这类数字和个别措辞上），共 21 种。清洗版统一采用其中一种，使数据可以直接用于微调。

如果需要按行区分原始人设，请使用原始 CSV；如果要做微调训练，用 clean.csv 或 jsonl。

## 数据一致性校验

以下结论均由脚本逐字段比对得出：

- `clean.csv` 与 `jsonl`：**29/29 行完全一致**，两种格式可互换使用
- `clean.csv` 与原始 CSV 的 `user` + `assistant` 列：**29/29 行完全一致**，清洗过程未改动任何对话内容
- `jsonl`：**29/29 行均为合法 JSON**，消息结构统一为 `system → user → assistant`

## ⚠️ 编码注意事项

`薇Steria训练集V1.0.CSV` 是 **GBK** 编码，且不带 BOM。在 GitHub 网页上直接查看该文件会显示乱码——这是编码问题，**不是文件损坏**，原始字节与本地文件完全一致。

下载后请用支持 GBK 的工具打开：

```powershell
# PowerShell（Windows 中文环境默认 GBK，可直接读）
Get-Content .\薇Steria训练集V1.0.CSV

# 转换为 UTF-8（如需）
$gbk = [System.Text.Encoding]::GetEncoding("GBK")
$text = $gbk.GetString([System.IO.File]::ReadAllBytes(".\薇Steria训练集V1.0.CSV"))
[System.IO.File]::WriteAllText(".\converted.csv", $text, (New-Object System.Text.UTF8Encoding $true))
```

```python
# Python
import pandas as pd
df = pd.read_csv("薇Steria训练集V1.0.CSV", encoding="gbk")
```

**建议日常使用 `clean.csv` 或 `jsonl`**，它们都是标准 UTF-8。

## 微调示例

```python
import json

# 读取 jsonl 用于微调
with open("薇Steria训练集V1.0.jsonl", encoding="utf-8") as f:
    samples = [json.loads(line) for line in f if line.strip()]

print(len(samples))                      # 29
print(samples[0]["messages"][0]["role"]) # system
```

```python
import pandas as pd

# 读取 clean.csv
df = pd.read_csv("薇Steria训练集V1.0.clean.csv", encoding="utf-8-sig")
print(df.columns.tolist())  # ['system', 'user', 'assistant']
print(len(df))              # 29
```

## 人设概要

薇Steria 是一只来自大森林的**紫藤树精灵**，职业为**森林书记官**，梦想成为**文豪偶像**。在 B 站直播，以唱歌和聊天为主，是 V 圈有代表性的歌势。粉丝勋章叫「薇她命」，她称观众为「薇她命」或「小薇她命」。

说话风格：口语化、有情绪、偶尔带东北口音，回复简短自然（1~5 句）。

## 版本

- **V1.0** — 29 条样本，三种格式
