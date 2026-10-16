# -*- coding: utf-8 -*-
"""
评测集只读校验（不会修改你的 CSV，可以随时跑）
=============================================
检查 评测集/薇Steria评测集V1.0.csv：
  1. 表头 / 编号 / 必填单元格
  2. 「必过」只能是 是 / 否
  3. system 列必须和训练集 V1.1 的 system 逐字一致（评测和训练不能两套提示词）
  4. 参考答案长度是否还在 V1.1 的 40~90 字标准附近
  5. 各分类条数统计

用法：
    python tools/verify_eval.py
"""
import csv
import io
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EVAL = Path("评测集/薇Steria评测集V1.0.csv")
TRAIN = Path("训练集/薇Steria训练集V1.1.clean.csv")

HEADER = ["编号", "分类", "system", "user", "assistant", "考察点", "判定标准", "必过", "备注"]
REQUIRED = ["编号", "分类", "user", "考察点", "判定标准", "必过"]  # 不能为空
MAX_REF = 110      # 参考答案硬上限
MIN_ROWS = 15      # 低于这个数统计意义太弱

fails = []


def check(cond, msg):
    print(("  [OK]   " if cond else "  [FAIL] ") + msg)
    if not cond:
        fails.append(msg)


if not EVAL.exists():
    print(f"[错误] 找不到 {EVAL}", file=sys.stderr)
    raise SystemExit(1)

raw = EVAL.read_text(encoding="utf-8-sig")
rows = list(csv.DictReader(io.StringIO(raw, newline="")))
header = list(rows[0].keys()) if rows else []

print("=== 1. 结构 ===")
check(header == HEADER, f"表头正确：{header}")
check(len(rows) >= MIN_ROWS, f"条数 {len(rows)} ≥ {MIN_ROWS}")
ids = [r["编号"].strip() for r in rows]
check(len(set(ids)) == len(ids), f"编号不重复（{len(ids)} 条）")
check(all(i.startswith("E") and i[1:].isdigit() for i in ids), "编号格式为 E01 / E02 …")

print("\n=== 2. 必填内容 ===")
empty = [(r["编号"], k) for r in rows for k in REQUIRED if not (r.get(k) or "").strip()]
check(not empty, f"必填单元格无空缺（空缺: {empty or '无'}）")
bad_must = [r["编号"] for r in rows if r["必过"].strip() not in ("是", "否")]
check(not bad_must, f"「必过」列只出现 是/否（异常: {bad_must or '无'}）")
dup_user = [u for u, c in Counter(r["user"].strip() for r in rows).items() if c > 1]
check(not dup_user, f"没有重复的 user 提问（重复: {dup_user or '无'}）")

print("\n=== 3. system 与训练集一致性 ===")
train = list(csv.DictReader(TRAIN.open(encoding="utf-8-sig")))
train_sys = {r["system"] for r in train}
check(len(train_sys) == 1, "训练集里 system 唯一")
train_sys = train_sys.pop()
eval_sys = {r["system"].strip() for r in rows}
check(eval_sys == {train_sys}, f"评测集 system 与训练集逐字一致（{len(train_sys)} 字）")
if eval_sys != {train_sys}:
    for s in eval_sys:
        print(f"         评测集里出现: {s[:60]}…")

print("\n=== 4. 参考答案长度（对齐 V1.1 的 40~90 字标准）===")
lens = {r["编号"]: len(r["assistant"]) for r in rows}
over = {k: v for k, v in lens.items() if v > MAX_REF}
check(not over, f"没有超过 {MAX_REF} 字的参考答案（超标: {over or '无'}）")
longish = {k: v for k, v in lens.items() if v > 90}
print(f"         平均 {sum(lens.values())/len(lens):.0f} 字，最长 {max(lens.values())} 字"
      f"，超过 90 字的: {longish or '无'}")

print("\n=== 5. 分类分布 ===")
cats = Counter(r["分类"].strip() for r in rows)
for c, n in cats.most_common():
    print(f"         {c:<4} {n:>2} 条  {'█' * n}")
check(len(cats) >= 4, f"覆盖 {len(cats)} 个分类（≥4）")
check(all(n >= 3 for n in cats.values()), "每个分类至少 3 条")

must = sum(1 for r in rows if r["必过"].strip() == "是")
print(f"\n         必过项 {must} 条 / 参考项 {len(rows) - must} 条")

print("\n" + "=" * 60)
if fails:
    print(f"校验失败 {len(fails)} 项：")
    for f in fails:
        print("  -", f)
    raise SystemExit(1)
print("全部校验通过 ✅")
