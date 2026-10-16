# data/

`训练集/` 的**逐字节镜像**，供校验脚本做交叉比对使用。

## 为什么有两个目录

| 目录 | 用途 | 命名风格 |
| --- | --- | --- |
| `训练集/` | 面向人阅读，中文命名，含 V1.0 与 V1.1 | `薇Steria训练集V1.1.jsonl` |
| `data/` | 面向脚本，ASCII 命名，供 `tools/verify_v1_1.py` 做镜像一致性校验 | `steria_v1.1.jsonl` |

两边的同名文件**内容逐字节相同**（脚本用 sha256 强制校验）。改数据时必须两边同步修改，否则校验会失败。

## 文件对照

| `训练集/` | `data/` | 版本 | 条数 |
| --- | --- | --- | --- |
| `薇Steria训练集V1.1.jsonl` | `steria_v1.1.jsonl` | V1.1 | 27 |
| `薇Steria训练集V1.1.clean.csv` | `steria_v1.1.clean.csv` | V1.1 | 27 |
| `薇Steria训练集V1.0.jsonl` | `steria_v1.0.jsonl` | V1.0 | 29 |
| `薇Steria训练集V1.0.clean.csv` | `steria_v1.0.clean.csv` | V1.0 | 29 |
| `薇Steria训练集V1.0.CSV` | `steria_v1.0.raw.csv` | V1.0 原始 | 29 |

> ⚠️ 唯一差异在文件名：`训练集/薇Steria训练集V1.0.CSV`（大写扩展名）对应 `data/steria_v1.0.raw.csv`。两者是同一个 GBK 编码的原始导出文件。

## 在仓库根目录运行校验

```bash
python tools/verify_v1_1.py     # V1.1 结构 + 与 V1.0 对照 + 镜像一致性
python tools/verify_eval.py     # 评测集只读校验
```

两个脚本都会在全部检查通过时 `exit 0`，任一失败 `exit 1`。

## 换行符要求

`.jsonl` / `.csv` / `.py` / `.md` **必须是 LF**。仓库根目录的 [`.gitattributes`](../.gitattributes) 已强制 `eol=lf`，正常克隆不会出问题。

若你在 Windows 上曾手动改过换行符，校验脚本会报：

```
[FAIL] V1.1 JSONL 使用 LF 换行
[FAIL] 训练集\...V1.1.jsonl 与 data\steria_v1.1.jsonl 逐字节相同
```

修复：

```bash
git config core.autocrlf false
git rm --cached -r . && git reset --hard
```
