# -*- coding: utf-8 -*-
"""
评测集 CSV -> 推理用 JSONL
==========================
只导出 system + user 两条消息：评测是让模型「答」，把参考答案塞进去会变成
喂答案。参考答案留在 CSV 里，打分时对照用。

用法：
    python tools/eval_to_jsonl.py
输出：
    评测集/薇Steria评测集V1.0.jsonl
"""
import csv
import io
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EVAL = Path("评测集/薇Steria评测集V1.0.csv")
OUT = Path("评测集/薇Steria评测集V1.0.jsonl")


def main() -> int:
    if not EVAL.exists():
        print(f"[错误] 找不到 {EVAL}", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(io.StringIO(EVAL.read_text(encoding="utf-8-sig"), newline="")))
    kept, skipped = [], []
    for r in rows:
        eid = (r.get("编号") or "").strip()
        user = (r.get("user") or "").strip()
        system = (r.get("system") or "").strip()
        if not user or not system:
            skipped.append(eid or "(无编号)")
            continue
        kept.append({"messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for rec in kept:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"导出 {len(kept)} 条 -> {OUT}")
    if skipped:
        print(f"跳过 {len(skipped)} 行（user 或 system 为空）：{', '.join(skipped)}")
    print("注意：只含 system + user。参考答案在 CSV 的 assistant 列里，不要喂给模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
