# -*- coding: utf-8 -*-
"""独立校验 V1.1：user/system 是否逐字未动、assistant 是否真的改短、删除是否只删了该删的。"""
import csv
import difflib
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import build_v1_1 as B  # 只为对照「预期改写了哪些行」，校验逻辑本身独立重算

# Windows 控制台/重定向默认 GBK，含中文与 emoji 的输出会崩，这里强制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

V10_CSV = Path("训练集/薇Steria训练集V1.0.clean.csv")
V11_CSV = Path("训练集/薇Steria训练集V1.1.clean.csv")
V11_JSONL = Path("训练集/薇Steria训练集V1.1.jsonl")
MIRROR_CSV = Path("data/steria_v1.1.clean.csv")
MIRROR_JSONL = Path("data/steria_v1.1.jsonl")

MAX_LEN = 110
fails = []


def check(cond, msg):
    print(("  [OK]   " if cond else "  [FAIL] ") + msg)
    if not cond:
        fails.append(msg)


def read_csv(path):
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"), newline="")))
    return rows[0], rows[1:]


# ---------- 1. JSONL 结构 ----------
print("=== 1. JSONL 结构 ===")
lines = [l for l in V11_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
objs = [json.loads(l) for l in lines]
check(len(objs) == len(lines), "每一行都是合法 JSON")
check(all(set(o.keys()) == {"messages"} for o in objs), "每条顶层只有 messages 字段")
check(all([m["role"] for m in o["messages"]] == ["system", "user", "assistant"] for o in objs),
      "角色顺序恒为 system->user->assistant")
check(all(set(m.keys()) == {"role", "content"} for o in objs for m in o["messages"]),
      "每条消息只有 role/content 字段")
check(all(m["content"].strip() for o in objs for m in o["messages"]), "无空 content")

# ---------- 2. 与 V1.0 对照 ----------
print("\n=== 2. 与 V1.0 对照（行号 = Excel 行号） ===")
_, old = read_csv(V10_CSV)
_, new = read_csv(V11_CSV)
check(len(old) == 29, f"V1.0 数据 {len(old)} 行 (期望 29)")
check(len(new) == len(old) - len(B.DROP), f"V1.1 保留 {len(new)} 行 = 29 - 删{len(B.DROP)}")

old_map = {i: r for i, r in enumerate(old, start=2)}
# V1.1 删了行，必须按「V1.0 的行号」对齐，不能重新编号
kept_ids = [i for i in old_map if i not in B.DROP]
new_map = {i: r for i, r in zip(kept_ids, new)}
check(set(new_map) == set(old_map) - set(B.DROP), "删除的正是 DROP 里声明的行，没有误删")

old_sys = old_map[2][0]
# user 列：声明修正的行要逐字对上，其余行必须逐字未动
user_drift = [i for i in new_map if i not in B.USER_FIX and new_map[i][1] != old_map[i][1]]
check(not user_drift, f"未声明的 user 行逐字未动（漂移: {user_drift or '无'}）")
fixed = [i for i in new_map if i in B.USER_FIX]
check(all(new_map[i][1] == B.USER_FIX[i][0] for i in fixed),
      f"声明的 {len(fixed)} 处 user 修正逐字一致")
# 独立重放：声明的片段对必须能原样还原出改后全文（防止「说明写A、实际改B」）
replay_bad = []
for i in fixed:
    rebuilt = old_map[i][1]
    for old_frag, new_frag in B.USER_FIX[i][1]:
        if old_frag not in rebuilt:
            replay_bad.append((i, old_frag, "原句里找不到"))
            continue
        rebuilt = rebuilt.replace(old_frag, new_frag, 1)
    if rebuilt != new_map[i][1]:
        replay_bad.append((i, rebuilt, new_map[i][1]))
check(not replay_bad, f"每处修正的「声明改动」重放后等于「改后全文」（异常: {replay_bad or '无'}）")
ratios = {i: difflib.SequenceMatcher(None, old_map[i][1], new_map[i][1]).ratio() for i in fixed}
check(all(r >= 0.75 for r in ratios.values()),
      f"user 修正都是小改、没有重写提问（相似度 {min(ratios.values()):.2f}~{max(ratios.values()):.2f}）")
check(all("「" not in new_map[i][1] for i in fixed), "改后的 user 里没有混进「」这种说明性括号")
check(not (set(B.USER_FIX) & set(B.DROP)), "没有「既改 user 又删行」的矛盾")
check(all(len(old_map[i][1]) > 0 for i in fixed), "修正前的原句都还在（可从 V1.0 追溯）")
for i in fixed:
    print(f"         第 {i} 行 {ratios[i]:.2f}  {old_map[i][1]}  ->  {new_map[i][1]}")
check(all(r[0] == B.SYSTEM_V1_1 for r in new_map.values()), "system 列已全部替换为新模板（无残留旧文本）")
check(len({r[0] for r in new_map.values()}) == 1, "全部条目共用同一个 system")

# ---------- 2b. 新 system 的「相关性」 ----------
print("\n=== 2b. 新 system 是否贴数据 ===")
check(len(B.SYSTEM_V1_1) < len(old_sys),
      f"system 确实变短：{len(old_sys)} -> {len(B.SYSTEM_V1_1)} 字（{len(B.SYSTEM_V1_1)/len(old_sys):.0%}）")
check(len(B.SYSTEM_V1_1) <= B.MAX_SYSTEM, f"system {len(B.SYSTEM_V1_1)} 字 ≤ 上限 {B.MAX_SYSTEM} 字")
# 数据里 0 次出现的设定必须已删掉
LORELESS = ["紫藤", "精灵", "书记官", "文豪", "东北", "歌势", "母单", "勋章"]
for kw in LORELESS:
    check(kw not in B.SYSTEM_V1_1, f"已删除数据里 0 次出现的设定「{kw}」")
# 反向：system 里保留的每一项设定，数据里必须真有命中
for name, kws in B.COVERAGE.items():
    hit = sum(1 for r in new_map.values() if any(k in r[1] or k in r[2] for k in kws))
    check(hit > 0, f"保留的设定「{name}」在数据里有 {hit}/{len(new_map)} 条命中")
# system 不该比 assistant 总量还抢戏
ratio = sum(len(r[2]) for r in new_map.values()) / len(B.SYSTEM_V1_1)
check(ratio >= 6, f"system : assistant 总量 = 1 : {ratio:.1f}（修订前是 1 : 3.8，system 太抢戏）")

# ---------- 3. 改短是否真的发生 ----------
print("\n=== 3. assistant 长度 ===")
too_long = {i: len(r[2]) for i, r in new_map.items() if len(r[2]) > MAX_LEN}
check(not too_long, f"没有超过 {MAX_LEN} 字的 assistant（超标: {too_long or '无'}）")

changed = {i: r[2] for i, r in new_map.items() if r[2] != old_map[i][2]}
asserted = {i: t for i, t in B.REWRITE.items() if i in new_map}
check(set(changed) == set(asserted), f"实际改动的行 = 脚本声明的 {len(asserted)} 行")
check(all(changed[i] == asserted[i] for i in asserted), "改动内容与脚本声明逐字一致")

grew = {i: (len(old_map[i][2]), len(new_map[i][2])) for i in new_map if len(new_map[i][2]) > len(old_map[i][2])}
check(set(grew) == {26}, f"唯一变长的只有第 26 行（补一句「常规设定确实是正义和友谊」以贴合提问）：{grew}")

over100 = [i for i in old_map if len(old_map[i][2]) > MAX_LEN]
still_over = [i for i in over100 if i in new_map and len(new_map[i][2]) > MAX_LEN]
check(not still_over, f"V1.0 里超长的 {len(over100)} 行已全部压到 {MAX_LEN} 字内：{[(i, len(old_map[i][2]), len(new_map[i][2])) for i in over100]}")

o_avg = sum(len(old_map[i][2]) for i in new_map) / len(new_map)
n_avg = sum(len(r[2]) for r in new_map.values()) / len(new_map)
check(max(len(r[2]) for r in new_map.values()) <= 100,
      f"最长 assistant {max(len(r[2]) for r in new_map.values())} 字 ≤ 100")
print(f"         平均 {o_avg:.0f} -> {n_avg:.0f} 字；最长 {max(len(old_map[i][2]) for i in new_map)} -> {max(len(r[2]) for r in new_map.values())} 字")

# ---------- 4. 相关性抽查 ----------
print("\n=== 4. 相关性抽查（assistant 不得答非所问地留下空话） ===")
FILLER = {"哈哈哈", "哈哈", "笑死", "嗯", "对"}
for i, r in new_map.items():
    a = r[2]
    if a.strip("。！？~～哈笑死") in FILLER:
        check(False, f"第 {i} 行 assistant 近似纯笑声：{a}")
check(True, "没有「只回笑声」的 assistant")
for i, r in new_map.items():
    body = re.sub(r"[^\u4e00-\u9fff]", "", r[2])
    if len(body) < 12:
        check(False, f"第 {i} 行正文过短（{len(body)} 汉字）")
check(True, "每条 assistant 都有 ≥12 个汉字的实义内容")
for kw, i in (("婚恋", 3), ("水牢", 7), ("婚恋", 9), ("市丸银", 24), ("木叶村", 27)):
    check(kw in new_map[i][2], f"第 {i} 行保留了回应提问的关键词「{kw}」")

# ---------- 5. CSV / JSONL / 镜像一致性 ----------
print("\n=== 5. 文件一致性 ===")
check([m["content"] for o in objs for m in o["messages"]] ==
      [c for r in new_map.values() for c in r], "CSV 与 JSONL 内容完全一致")
for a, b in ((V11_CSV, MIRROR_CSV), (V11_JSONL, MIRROR_JSONL)):
    ha = hashlib.sha256(a.read_bytes()).hexdigest()
    hb = hashlib.sha256(b.read_bytes()).hexdigest()
    check(ha == hb, f"{a} 与 {b} 逐字节相同（sha256 {ha[:12]}）")
check(V11_CSV.read_bytes().startswith(b"\xef\xbb\xbf"), "V1.1 CSV 带 UTF-8 BOM（Excel 友好）")
check(not V11_JSONL.read_bytes().startswith(b"\xef\xbb\xbf"), "V1.1 JSONL 无 BOM（训练框架要求）")
check(b"\r\n" not in V11_JSONL.read_bytes(), "V1.1 JSONL 使用 LF 换行")

# ---------- 6. 原始文件未被改动 ----------
print("\n=== 6. V1.0 原件完整性 ===")
check(len(old) == 29 and old[0][2].strip().startswith("我并不是"), "V1.0 clean CSV 仍是 29 行原始内容")
check(Path("训练集/薇Steria训练集V1.0.jsonl").exists(), "V1.0 JSONL 仍在")

print("\n" + "=" * 60)
if fails:
    print(f"校验失败 {len(fails)} 项：")
    for f in fails:
        print("  -", f)
    raise SystemExit(1)
print("全部校验通过 ✅")
