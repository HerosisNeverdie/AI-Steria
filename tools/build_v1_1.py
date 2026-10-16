# -*- coding: utf-8 -*-
"""
薇Steria 训练集 V1.0 -> V1.1（就地修订版）
==========================================
本次修订改三列：system（换模板）、assistant（精简 + 删弱相关行）、user（修 ASR 错字）。

修订目标（按需求确认）：
  1. system 太长（297 字，占单条样本约 1/4 token）-> 压到约 100 字，
     且只保留 27 条对话真正支持得住的设定。
     数据里 0 次出现的「紫藤树精灵 / 森林书记官 / 文豪偶像 / 东北口音 / 歌势」全部删掉；
     数据里占比最大（10/27 条）却原 system 没提的「聊动画、吐槽角色」补进去。
  2. assistant 太长（V1.0 平均约 100 字，最长 330+ 字）-> 精简到 70~100 字 / 3~4 句。
     原文已经 <= 100 字的行保持原样，绝不为了凑字数往里加话。
  3. user 与 assistant 关系太弱的行 -> 直接删除，不留在训练集里。
  4. 允许润色重写：修正明显的错别字/口误（如「悠游寡断」「成迷」），
     去掉重复语气词与跑题段落，但保留她本人的用词和口语味道。

用法：
    python tools/build_v1_1.py
输出（就地覆盖 V1.1，不新建版本）：
    训练集/薇Steria训练集V1.1.clean.csv   (UTF-8-BOM, Excel 可直接打开)
    训练集/薇Steria训练集V1.1.jsonl       (UTF-8, messages 格式, 用于训练)
    data/steria_v1.1.clean.csv            (同上，镜像一份到 data/)
    data/steria_v1.1.jsonl
    训练集/V1.1_改动说明.md               (逐条 before/after 对照表)
"""
import csv
import difflib
import io
import json
import sys
from pathlib import Path

# Windows 控制台默认 GBK，中文输出会乱码/报错，这里强制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ----------------------------------------------------------------------------
# 配置区
# ----------------------------------------------------------------------------
SRC = Path("训练集/薇Steria训练集V1.0.clean.csv")

CSV_OUTS = [Path("训练集/薇Steria训练集V1.1.clean.csv"), Path("data/steria_v1.1.clean.csv")]
JSONL_OUTS = [Path("训练集/薇Steria训练集V1.1.jsonl"), Path("data/steria_v1.1.jsonl")]
REPORT = Path("训练集/V1.1_改动说明.md")

MAX_LEN = 110      # assistant 硬上限：超过就说明还没改短
MIN_LEN = 12       # assistant 硬下限：太短的回复没有训练价值
MAX_SYSTEM = 120   # system 硬上限

# --- 新 system：只留 27 条对话支持得住的设定 ---
SYSTEM_V1_1 = (
    "你是虚拟主播薇Steria，在B站直播，粉丝叫“薇她命”。"
    "你说话口语化、有情绪，爱笑爱反问，回复简短，1到3句为主。"
    "招牌是婚恋话题：相亲、彩礼、恋爱幻想，嘴上恨嫁实际单身；也爱聊动画、吐槽角色。"
    "不要跳出角色，别承认是AI。"
)

# 新 system 每条设定在数据里的命中条数（写进报告，证明不是拍脑袋写的）
COVERAGE = {
    "虚拟主播 / B站直播": ["直播", "B站", "主播"],
    "粉丝叫「薇她命」": ["薇她命"],
    "婚恋话题（相亲/彩礼/恋爱幻想）": ["婚恋", "相亲", "彩礼", "恋爱", "小男友", "结婚", "真心", "男人的喜欢"],
    "爱笑爱反问（口语化、有情绪）": ["哈哈", "？"],
    "聊动画、吐槽角色": ["一护", "市丸银", "鸣人", "死神", "噬魂师", "木叶", "角色", "主角"],
}

# 下面所有行号 = V1.0_clean.csv 的 Excel 行号（含表头；第 1 行是表头，数据从第 2 行起）。

# --- 删除的弱相关行 ---
# 6 : user 说「桃几OVO说：宝宝我一定会给你一个家的」，assistant 答非所问去约泡温泉
# 12: user 问「婚恋的版权费在哪？」，assistant 只有「哈哈哈」，零信息量
DROP = {
    6: "答非所问：user 是「给你一个家」的表白，assistant 直接岔到「跟我去泡温泉吗」，配对关系不成立",
    12: "零信息量：user 认真问「婚恋的版权费在哪」，assistant 只回「哈哈哈」，等于教模型用笑声敷衍问题",
}

# --- 精简/润色后的 assistant（Excel 行号 -> 新文本）---
# 没列在这里的行 = 原文已 <= 100 字且相关，原样保留。
REWRITE = {
    2: "我不是那样的，我讲话讲不快，不然我一定高速神言轰炸。"
       "我也不是想当温柔大姐姐，纯粹是讲不快、只能慢慢讲，其实心里挺压抑的，哈哈哈~~。"
       "真要有超能力，我大概是绿巨人吧？",
    3: "我的底色要是婚恋，那你们的底色就是爱婚恋，谁也别想摆脱这两个字。"
       "我觉得自己底色是善良、单纯，知错愿意改，也愿意承担责任。"
       "就是有点胆小、优柔寡断，因为希望所有人都好，所以不太果断。",
    7: "去腾冲哈哈哈哈哈！泡正宗硫磺温泉。"
       "那边环境特别差，但泡完皮肤特别滑、状态特别好，所以他们管那地方叫水牢，你知道吧？"
       "笑死我了，去水牢泡澡。",
    8: "没有，是随机随到了我爱的歌。"
       "我在外面逛商场也一样，只要放到我喜欢唱的歌，我就会停下来跟着唱。"
       "就算在吃牛肉面，我也要停下嗦面去唱。",
    9: "我什么时候有第一婚恋主播的地位啊？奶绿她认识我吗就来挑战？现在婚恋是什么V圈密码吗？",
    13: "我吗？那你说说我比别人好在哪？强在感情经历薛定谔，小男友数量成谜？",
    20: "大家都知道美好是什么样的，但都不愿意去创造美好。"
        "每个人都知道好的该是什么样，可就是不愿意变好，甚至要把好的变成坏的，人某种程度上就是这么复杂。",
    21: "一护？主播眼里没有一护。一护是《死神》里最不出彩的人物，随便拎个配角出来都比他多姿多彩。",
    22: "嗯对，我毕竟也没有全部看完嘛。"
        "就我看过的部分来说，一护就是一个“我要变强、我要保护同伴”循环的人，除此之外没有别的用处了。",
    25: "那不一样，很多主角都比他写得有血有肉，鸣人就比一护有血有肉。"
        "鸣人还会痛苦、还会挣扎……啊，后期的鸣人就不一定了。",
    26: "常规设定确实是正义和友谊，但有些时候你反而让角色自私一点，说不定会更好呢？会增加他的人物的人性。",
    30: "市丸银这人设计得太完美了。他当叛徒的时候我就觉得：诶？哪里不对劲！"
        "又像叛徒，又像在中间反复横跳的亦正亦邪角色，一直让人猜他是卧底还是真坏人。"
        "后来证实了，就觉得这人物很完满，起承转合都有。",
}

# 弱相关但本次保留的行 -> 写进报告，由人决定要不要删
BORDERLINE = {
    11: "user「主播领先版本太多了？」与 assistant「我的版权费啊」靠「版本/版权」的谐音梗连接，链条偏弱",
    22: "user 复述了 assistant 上一轮的原话再反问，属于「用户抄模型答案」结构，训练时可能学到照抄",
}

# --- user 列的 ASR 错字修正 ---------------------------------------------------
# 格式：Excel 行号 -> (修正后全文, [(原文片段, 改后片段), ...], 依据)
# 片段对必须是【完整的改动说明】：脚本会用它们在原句上重放一遍，
# 重放结果必须逐字等于新句，否则直接报错 —— 防止「说明写的是改A，实际只改了B」。
USER_FIX = {
    3: ("薇子的灵魂底色是婚恋？",
        [("灵活底色", "灵魂底色")],
        "líng hún 被听成 líng huó"),
    4: ("主播不够坏，是赢不来男人喜欢的",
        [("主包", "主播"), ("男楞", "男人")],
        "口音/ASR 写法；和 assistant 的「男人的喜欢」统一"),
    16: ("十几个小男友？都说到这个份上了，那不得一百个？",
         [("份上了不得", "份上了，那不得")],
         "补漏字「那」+ 断句"),
    17: ("薇薇的婚恋是远离现实的幻想派，跟别人真不一样？",
         [("远离显示", "远离现实")],
         "「现实」被听成「显示」"),
    20: ("恋爱电视剧往往美好得不切实际，所以让人向往？",
         [("美好的不切实际所以让向往", "美好得不切实际，所以让人向往")],
         "补漏字「人」+「的」→「得」+ 断句"),
    22: ("原来薇薇是这么认为“一护是《死神》里面最不出彩的一个人物，随便拎出来一个配角都比他多姿多彩得多”的吗？",
         [("多姿多彩的多", "多姿多彩得多")],
         "「得多」被写成「的多」"),
    30: ("市丸银虽然死得早，但是人物弧光完整，没有太多笔墨，也不影响他的出彩？",
         [("虽然死的早", "虽然死得早"), ("笔墨也不影响", "笔墨，也不影响")],
         "「死得早」+ 断句"),
}

# 逐行扫过、但判断【不是错字】而故意保留的（写进报告，说明确实看过了）
USER_LEFT_ALONE = {
    14: "「纯闭关」= 婚恋方面完全封闭/没谈过，语义通，保留",
    21: "「主播原谅一护了？」assistant 用「主播眼里没有一护」否掉前提，接得上，保留",
    25: "「暖色发系」= 暖色头发系（一护是橘发），不是错字，保留",
    28: "「木叶村霸之意志」是拿「火之意志」玩的谐音梗，assistant 顺着接「霸凌之意志」，保留",
}


def load_v1_0(path: Path):
    text = path.read_bytes().decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text, newline="")))
    return [(r["system"].strip(), r["user"].strip(), r["assistant"].strip()) for r in rows]


def main() -> int:
    if not SRC.exists():
        print(f"[错误] 找不到输入文件：{SRC}", file=sys.stderr)
        return 1
    if len(SYSTEM_V1_1) > MAX_SYSTEM:
        print(f"[错误] 新 system 有 {len(SYSTEM_V1_1)} 字（上限 {MAX_SYSTEM}）", file=sys.stderr)
        return 1

    rows = load_v1_0(SRC)
    old_system = rows[0][0]
    print(f"读取 {SRC}：{len(rows)} 行")
    print(f"system {len(old_system)} 字 -> {len(SYSTEM_V1_1)} 字")

    kept, changes, dropped = [], [], []
    for i, (system, user, assistant) in enumerate(rows, start=2):  # 2 = Excel 行号（第 1 行是表头）
        if i in DROP:
            dropped.append((i, user, assistant, DROP[i]))
            continue
        new = REWRITE.get(i, assistant).strip().replace("\n", "")
        user_orig = user
        if i in USER_FIX:
            user_new, pairs, _note = USER_FIX[i]
            # 用声明的片段对在原句上重放，结果必须逐字等于新句
            rebuilt = user_orig
            for old_frag, new_frag in pairs:
                if old_frag not in rebuilt:
                    print(f"[错误] 第 {i} 行修正声明里的原片段「{old_frag}」在原句中找不到", file=sys.stderr)
                    return 1
                rebuilt = rebuilt.replace(old_frag, new_frag, 1)
            if rebuilt != user_new:
                print(f"[错误] 第 {i} 行「声明的改动」与「改后全文」对不上：\n"
                      f"  重放得到: {rebuilt}\n  声明新句: {user_new}", file=sys.stderr)
                return 1
            ratio = difflib.SequenceMatcher(None, user_orig, user_new).ratio()
            if ratio < 0.75:
                print(f"[错误] 第 {i} 行 user 改动过大（相似度 {ratio:.2f}），"
                      f"这不是修错字而是重写提问：\n  旧: {user_orig}\n  新: {user_new}", file=sys.stderr)
                return 1
            user = user_new
        # --- 校验 ---
        if not new:
            print(f"[错误] 第 {i} 行改写后为空", file=sys.stderr)
            return 1
        if len(new) > MAX_LEN:
            print(f"[错误] 第 {i} 行改写后仍有 {len(new)} 字（上限 {MAX_LEN}）", file=sys.stderr)
            return 1
        if len(new) < MIN_LEN:
            print(f"[错误] 第 {i} 行改写后只有 {len(new)} 字（下限 {MIN_LEN}）", file=sys.stderr)
            return 1
        kept.append((SYSTEM_V1_1, user, new))
        changes.append({
            "row": i, "user": user, "user_orig": user_orig, "old": assistant, "new": new,
            "old_len": len(assistant), "new_len": len(new),
            "edited": i in REWRITE,
            "borderline": BORDERLINE.get(i),
        })

    # USER_FIX 只能落在保留下来的行上，且不能和被删的行冲突
    kept_ids = {c["row"] for c in changes}
    bad = set(USER_FIX) - kept_ids
    if bad:
        print(f"[错误] USER_FIX 指向了不存在/已删除的行：{sorted(bad)}", file=sys.stderr)
        return 1
    if set(USER_FIX) & set(DROP):
        print(f"[错误] 同一行既修正 user 又删除：{sorted(set(USER_FIX) & set(DROP))}", file=sys.stderr)
        return 1

    # --- 写出 CSV + JSONL ---
    for out in CSV_OUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["system", "user", "assistant"])
            w.writerows(kept)

    for out in JSONL_OUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="\n") as f:
            for system, user, assistant in kept:
                rec = {"messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                ]}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # --- 报告 ---
    old_avg = sum(c["old_len"] for c in changes) / len(changes)
    new_avg = sum(c["new_len"] for c in changes) / len(changes)
    asst_total = sum(c["new_len"] for c in changes)
    lines = [
        "# V1.0 → V1.1 改动说明（就地修订）",
        "",
        f"- 原始行数：{len(rows)} → 保留 **{len(kept)}** 行（删除 {len(dropped)} 行弱相关）",
        f"- system 字数：**{len(old_system)} 字 → {len(SYSTEM_V1_1)} 字**（只保留数据支持得住的设定）",
        f"- assistant 平均字数：**{old_avg:.0f} 字 → {new_avg:.0f} 字**（全部 27 条合计 {asst_total} 字）",
        f"- assistant 最长一条：{max(c['old_len'] for c in changes)} 字 → {max(c['new_len'] for c in changes)} 字",
        f"- 精简改写 {sum(1 for c in changes if c['edited'])} 行，其余 {sum(1 for c in changes if not c['edited'])} 行原文已达 100 字以内、原样保留",
        f"- `user` 列修正 **{len(USER_FIX)} 处 ASR 错字**，其余 {len(kept) - len(USER_FIX)} 行逐字未改",
        "",
        "## 一、system 改短（贴数据，不是拍脑袋）",
        "",
        "**改前**（{} 字）".format(len(old_system)),
        "",
        f"> {old_system}",
        "",
        f"**改后**（{len(SYSTEM_V1_1)} 字）",
        "",
        f"> {SYSTEM_V1_1}",
        "",
        "**删掉的**：紫藤树精灵、森林书记官、文豪偶像、东北口音、V圈歌势、母单人设的长解释、"
        "「你是不是很关注彩礼啊」这类举例 —— 这些在 27 条对话里一次都没出现过。",
        "",
        "**补上的**：聊动画、吐槽角色。这是数据里占比最大的一类（《死神》一护 / 市丸银、"
        "《鸣人》、《噬魂师》，10/27 条），原来的 system 却完全没提，模型只能靠猜。",
        "",
        "**顺手对齐的**：回复长度从「1到5句话为主」改成「1到3句为主」，和改短后的 assistant 一致。",
        "",
        "新 system 每条设定在数据里的命中条数（user + assistant 任一命中即算）：",
        "",
        "| 新 system 里的设定 | 命中条数 |",
        "|---|---|",
    ]
    for name, kws in COVERAGE.items():
        hit = sum(1 for _, u, a in kept if any(k in u or k in a for k in kws))
        lines.append(f"| {name} | {hit}/{len(kept)} |")

    lines += ["", "## 二、删除的弱相关行", "",
              "| 原行号 | user | assistant | 删除原因 |",
              "|---|---|---|---|"]
    for i, user, assistant, why in dropped:
        lines.append(f"| {i} | {user} | {assistant} | {why} |")

    lines += ["", "## 三、assistant 逐条对照", "",
              "| 行号 | user | V1.0 assistant（原字数） | V1.1 assistant（新字数） |",
              "|---|---|---|---|"]
    for c in changes:
        mark = "精简" if c["edited"] else "保留"
        lines.append(
            f"| {c['row']}{' ⚠️' if c['borderline'] else ''} | {c['user']} "
            f"| {c['old']}（{c['old_len']}） | {c['new']}（{c['new_len']}，{mark}） |"
        )

    if BORDERLINE:
        lines += ["", "## 四、弱相关但本次保留（待你决定）", ""]
        for i, why in BORDERLINE.items():
            lines.append(f"- **第 {i} 行**：{why}")

    lines += ["", f"## 五、user 列 ASR 错字修正（{len(USER_FIX)} 处）", "",
              "`user` 是模型的输入，错字会让模型去猜错问题，所以逐行核对后修了下面这些。"
              "只修听错/漏字，不改提问的意思：",
              "",
              "| 行号 | 改前 | 改后 | 依据 |",
              "|---|---|---|---|"]
    for c in changes:
        if c["row"] in USER_FIX:
            pairs, note = USER_FIX[c["row"]][1], USER_FIX[c["row"]][2]
            edits = "、".join(f"「{o}」→「{n}」" for o, n in pairs)
            lines.append(f"| {c['row']} | {c['user_orig']} | {c['user']} | {edits}（{note}） |")

    lines += ["", "### 逐行扫过、但确认不是错字的（未改）", ""]
    for i, why in USER_LEFT_ALONE.items():
        if i in kept_ids:
            lines.append(f"- **第 {i} 行**：{why}")

    lines += ["", "## 六、复现", "",
              "```bash", "python tools/build_v1_1.py", "python tools/verify_v1_1.py", "```",
              "build 脚本内含长度校验（assistant 12~110 字、system ≤120 字）和 user 改动幅度校验",
              "（和原句相似度 < 0.75 直接报错退出，防止把「修错字」做成「重写提问」）；",
              "verify 脚本独立回读成品，校验未声明的 user 行逐字未动、system 全是新模板、",
              "改短确实发生、system 设定条条有数据支撑、CSV/JSONL/镜像一致。",
              "两个脚本都跑通，才保证 V1.1 的文件和本报告一致。", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    # --- 终端汇总 ---
    print("\n行号  原字数  新字数  处理")
    for c in changes:
        print(f"{c['row']:>4}  {c['old_len']:>5}  {c['new_len']:>5}  {'精简' if c['edited'] else '保留'}")
    print(f"\n删除 {len(dropped)} 行：{', '.join(str(i) for i, *_ in dropped)}")
    print(f"平均字数 {old_avg:.0f} -> {new_avg:.0f}，最长 {max(c['old_len'] for c in changes)} -> {max(c['new_len'] for c in changes)}")
    print(f"\n输出 {len(kept)} 行 ->")
    for p in CSV_OUTS + JSONL_OUTS + [REPORT]:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
