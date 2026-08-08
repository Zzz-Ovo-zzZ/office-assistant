#!/usr/bin/env python3
"""
错题库管理工具
━━━━━━━━━━━━━━━━━━
管理曾周的错题，支持录入、分类、查询、智能组卷，
按模块和错误次数优先出题，帮助高效复习薄弱环节。

使用方法：
    python question_bank.py                     # 交互式录入错题
    python question_bank.py --add               # 快速录入（引导式）
    python question_bank.py --quiz 公基 10       # 按模块智能组卷（模块 题数）
    python question_bank.py --quiz all 30        # 综合组卷
    python question_bank.py --list 公基           # 列出某模块所有错题
    python question_bank.py --list all --weak     # 列出高频错题（≥3次）
    python question_bank.py --stats              # 错题统计
    python question_bank.py --review             # 复习模式（随机出题）
    python question_bank.py --export             # 导出错题本(markdown)
"""

import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ============================================================
# 配置
# ============================================================

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "kaobian"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = ROOT / "output" / "kaobian" / "zengzhou"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

QUESTION_BANK_FILE = DATA_DIR / "question_bank.json"

# 模块和子模块定义
MODULES = {
    "公基": ["政治", "法律", "经济", "管理", "公文", "科技", "文史", "时政"],
    "言语": ["逻辑填空", "片段阅读", "语句表达"],
    "判断": ["图形推理", "事件排序", "类比推理", "定义判断", "逻辑判断"],
    "数量": ["数字推理", "数学运算"],
    "资料": ["增长", "比重", "倍数", "平均数", "综合分析"],
}

# 难度标记
DIFFICULTIES = ["简单", "中等", "较难", "很难"]

# 错误原因
ERROR_REASONS = [
    "知识点不会",
    "粗心大意",
    "时间不够",
    "概念混淆",
    "计算错误",
    "审题不清",
    "选项看错",
    "方法不对",
    "蒙的/猜的",
]

# ============================================================
# 数据加载
# ============================================================

def load_bank() -> dict:
    if QUESTION_BANK_FILE.exists():
        with open(QUESTION_BANK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"questions": [], "review_history": []}


def save_bank(data: dict):
    with open(QUESTION_BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# 录入逻辑
# ============================================================

def add_question_interactive():
    """交互式录入错题"""
    print("\n📝 录入错题")
    print("=" * 50)

    data = load_bank()

    # 选择模块
    print("\n模块:")
    for i, (mod, subs) in enumerate(MODULES.items(), 1):
        print(f"  {i}. {mod} ({', '.join(subs)})")

    mod_choice = input("\n选择模块(1-5): ").strip()
    try:
        mod_idx = int(mod_choice) - 1
        module = list(MODULES.keys())[mod_idx]
    except (ValueError, IndexError):
        print("❌ 无效选择")
        return

    # 选择子模块
    subs = MODULES[module]
    print(f"\n子模块:")
    for i, sub in enumerate(subs, 1):
        print(f"  {i}. {sub}")

    sub_choice = input(f"\n选择子模块(1-{len(subs)}): ").strip()
    try:
        sub_idx = int(sub_choice) - 1
        sub_module = subs[sub_idx]
    except (ValueError, IndexError):
        print("❌ 无效选择")
        return

    # 题目内容
    print("\n题目内容（可多行输入，输入空行结束）:")
    lines = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)
    content = "\n".join(lines)

    if not content:
        print("❌ 题目内容不能为空")
        return

    # 选项（可选）
    print("\n选项（可选，直接回车跳过，格式: A.xxx）:")
    options = {}
    for opt in ["A", "B", "C", "D"]:
        val = input(f"  {opt}. ").strip()
        if val:
            options[opt] = val

    # 正确答案
    answer = input("\n正确答案（A/B/C/D，或其他）: ").strip().upper()

    # 你的答案
    your_answer = input("你的答案（A/B/C/D，或其他）: ").strip().upper()

    # 难度
    print(f"\n难度:")
    for i, d in enumerate(DIFFICULTIES, 1):
        print(f"  {i}. {d}")
    diff_choice = input("选择难度(1-4): ").strip()
    try:
        difficulty = DIFFICULTIES[int(diff_choice) - 1]
    except (ValueError, IndexError):
        difficulty = "中等"

    # 错误原因
    print(f"\n错误原因:")
    for i, r in enumerate(ERROR_REASONS, 1):
        print(f"  {i}. {r}")
    reason_choice = input("选择原因(1-9): ").strip()
    try:
        error_reason = ERROR_REASONS[int(reason_choice) - 1]
    except (ValueError, IndexError):
        error_reason = "知识点不会"

    # 备注
    note = input("\n备注/心得（可选）: ").strip()

    # 构建题目对象
    question = {
        "id": len(data["questions"]) + 1,
        "module": module,
        "sub_module": sub_module,
        "content": content,
        "options": options,
        "answer": answer,
        "your_answer": your_answer,
        "difficulty": difficulty,
        "error_reason": error_reason,
        "note": note,
        "error_count": 1,  # 错过几次
        "mastered": False,  # 是否已掌握
        "created_at": datetime.now().isoformat(),
        "last_reviewed": None,
        "tags": [],
    }

    data["questions"].append(question)
    save_bank(data)

    print(f"\n✅ 错题已录入 (ID: {question['id']}) | {module}/{sub_module} | {difficulty}")


def add_question_quick(module: str, sub_module: str, content: str,
                       answer: str = "", your_answer: str = "",
                       difficulty: str = "中等", error_reason: str = ""):
    """快速命令行录入"""
    if module not in MODULES:
        print(f"❌ 未知模块: {module}")
        return

    data = load_bank()

    question = {
        "id": len(data["questions"]) + 1,
        "module": module,
        "sub_module": sub_module,
        "content": content,
        "options": {},
        "answer": answer.upper(),
        "your_answer": your_answer.upper(),
        "difficulty": difficulty,
        "error_reason": error_reason or "知识点不会",
        "note": "",
        "error_count": 1,
        "mastered": False,
        "created_at": datetime.now().isoformat(),
        "last_reviewed": None,
        "tags": [],
    }

    data["questions"].append(question)
    save_bank(data)

    print(f"✅ 错题已录入 (ID: {question['id']}) | {module}/{sub_module}")


# ============================================================
# 智能组卷
# ============================================================

def smart_quiz(module: str = "all", num_questions: int = 10, weak_focus: bool = True):
    """
    智能组卷
    - module: 模块名或 "all"
    - num_questions: 出题数量
    - weak_focus: 是否优先出高频错题
    """
    data = load_bank()
    all_questions = data["questions"]

    if not all_questions:
        print("❌ 错题库为空，请先录入错题")
        return

    # 筛选
    pool = all_questions
    if module != "all":
        pool = [q for q in all_questions if q["module"] == module]

    if not pool:
        print(f"❌ 模块 [{module}] 没有错题记录")
        return

    # 排除已掌握的
    pool = [q for q in pool if not q.get("mastered", False)]

    if not pool:
        print(f"✅ 模块 [{module}] 所有错题已掌握！")
        return

    # 排序：错误次数多 + 难度高 + 最近未复习的优先
    def sort_key(q):
        error_weight = q.get("error_count", 1) * 3
        diff_weight = {"简单": 0, "中等": 1, "较难": 2, "很难": 3}.get(q.get("difficulty", "中等"), 1)
        # 最近复习过的排在后面
        recently_reviewed = 0
        if q.get("last_reviewed"):
            try:
                days_ago = (datetime.now() - datetime.fromisoformat(q["last_reviewed"])).days
                recently_reviewed = max(0, 30 - days_ago)  # 30天内的加权重
            except:
                pass
        return -(error_weight + diff_weight * 2 - recently_reviewed * 0.5)

    pool.sort(key=sort_key)

    # 出题
    selected = pool[:num_questions]
    if len(selected) < num_questions:
        print(f"⚠️ 符合条件的错题仅 {len(selected)} 道，不足 {num_questions} 题")

    # 生成试卷
    today = datetime.now().strftime("%Y%m%d")
    quiz_path = OUTPUT_DIR / f"错题组卷_{module}_{today}.md"

    lines = [
        f"# 📝 错题复习卷",
        f"",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 模块：{module if module != 'all' else '综合'}",
        f"> 题量：{len(selected)} 题",
        f"> 策略：优先高频错题 + 高难度 + 未复习",
        f"",
        f"---",
        f"",
    ]

    for i, q in enumerate(selected, 1):
        lines.append(f"## {i}. [{q['module']}/{q['sub_module']}] ⭐ 错过{q.get('error_count', 1)}次")
        lines.append(f"")
        lines.append(f"**题目**：{q['content']}")
        if q.get("options"):
            lines.append("")
            for opt in ["A", "B", "C", "D"]:
                if opt in q["options"]:
                    lines.append(f"- {opt}. {q['options'][opt]}")
        lines.append(f"")
        lines.append(f"> 难度：{q.get('difficulty', '未知')} | 错误原因：{q.get('error_reason', '未知')}")
        if q.get("note"):
            lines.append(f"> 笔记：{q['note']}")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## ✅ 答案",
        f"",
    ]

    for i, q in enumerate(selected, 1):
        lines.append(f"**{i}.** 正确答案：**{q.get('answer', '?')}** | 你的答案：{q.get('your_answer', '?')}")
        if q.get("note"):
            lines.append(f"  > {q['note']}")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## 📊 本次组卷统计",
        f"",
    ]

    # 统计
    module_count = {}
    for q in selected:
        m = q["module"]
        module_count[m] = module_count.get(m, 0) + 1
    for m, c in module_count.items():
        lines.append(f"- {m}: {c}题")
    lines.append(f"- 平均错误次数: {sum(q.get('error_count', 1) for q in selected) / len(selected):.1f}")

    lines += [
        f"",
        f"---",
        f"",
        f"*自动生成 | 错题库总量: {len(all_questions)} 题*",
    ]

    with open(quiz_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n📝 组卷已生成: {quiz_path}")
    print(f"   模块: {module} | 题量: {len(selected)} | 来源: {len(pool)}道可用错题")
    return quiz_path


# ============================================================
# 复习模式
# ============================================================

def review_mode():
    """交互式复习"""
    data = load_bank()
    all_questions = [q for q in data["questions"] if not q.get("mastered", False)]

    if not all_questions:
        print("✅ 所有错题已掌握！")
        return

    # 按优先级排序
    all_questions.sort(key=lambda q: -(q.get("error_count", 1)))

    print(f"\n🔄 错题复习模式")
    print(f"   待复习: {len(all_questions)} 题")
    print(f"   按回车看答案，输入 'm' 标记已掌握，'q' 退出")
    print("=" * 60)

    correct = 0
    total = 0

    random.shuffle(all_questions)  # 先打乱，保持一定随机性
    # 但前5题优先高频错题
    high_freq = [q for q in all_questions if q.get("error_count", 1) >= 3]
    normal = [q for q in all_questions if q.get("error_count", 1) < 3]
    random.shuffle(high_freq)
    random.shuffle(normal)
    questions = high_freq + normal

    for q in questions[:20]:  # 每次最多20题
        total += 1
        print(f"\n{'─' * 50}")
        print(f"[{q['module']}/{q['sub_module']}] 错过{q.get('error_count', 1)}次 | {q.get('difficulty', '')}")
        print(f"\n{q['content']}")
        if q.get("options"):
            for opt in ["A", "B", "C", "D"]:
                if opt in q["options"]:
                    print(f"  {opt}. {q['options'][opt]}")

        choice = input("\n你的答案(A/B/C/D/m/q): ").strip().lower()

        if choice == "q":
            break
        elif choice == "m":
            q["mastered"] = True
            q["last_reviewed"] = datetime.now().isoformat()
            print(f"  ✅ 已标记为掌握")
            continue

        print(f"\n  正确答案: **{q.get('answer', '?')}** | 你的答案: {choice.upper()}")
        if q.get("note"):
            print(f"  💡 {q['note']}")

        result = input("\n  答对了吗？(y/n): ").strip().lower()
        if result == "y":
            correct += 1
            # 答对一次减少错误计数权重
            q["error_count"] = max(0, q.get("error_count", 1) - 0.5)
            print(f"  👍 很好！")
        else:
            q["error_count"] = q.get("error_count", 1) + 1
            print(f"  📝 继续加油，错误次数+1")

        q["last_reviewed"] = datetime.now().isoformat()

    save_bank(data)

    print(f"\n{'=' * 60}")
    print(f"本次复习: {correct}/{total} 正确")
    remaining = len([q for q in data["questions"] if not q.get("mastered", False)])
    print(f"剩余待复习: {remaining} 题")
    print(f"总计错题: {len(data['questions'])} 题")


# ============================================================
# 统计 + 列表
# ============================================================

def list_questions(module: str = "all", weak_only: bool = False):
    """列出错题"""
    data = load_bank()
    questions = data["questions"]

    if module != "all":
        questions = [q for q in questions if q["module"] == module]

    if weak_only:
        questions = [q for q in questions if q.get("error_count", 1) >= 3]

    if not questions:
        print("📭 无匹配错题")
        return

    mastered = [q for q in questions if q.get("mastered")]
    active = [q for q in questions if not q.get("mastered")]

    print(f"\n📋 错题列表 ({module if module != 'all' else '全部'})")
    print(f"   活跃: {len(active)} | 已掌握: {len(mastered)}")
    print("-" * 60)

    questions.sort(key=lambda q: -q.get("error_count", 1))

    for q in questions[:30]:
        icon = "✅" if q.get("mastered") else "❌"
        star = "⭐" * min(q.get("error_count", 1), 5)
        content_preview = q["content"][:50].replace("\n", " ")
        print(f"{icon} [{q['module'][:2]}/{q['sub_module'][:4]}] {star} {content_preview}...")


def print_stats():
    """错题统计"""
    data = load_bank()
    questions = data["questions"]

    if not questions:
        print("📭 错题库为空")
        return

    total = len(questions)
    active = len([q for q in questions if not q.get("mastered")])
    mastered = total - active
    avg_errors = sum(q.get("error_count", 1) for q in questions) / total

    print(f"\n📊 错题库统计")
    print("=" * 50)
    print(f"  总计: {total} 题 | 活跃: {active} | 已掌握: {mastered}")
    print(f"  平均错误次数: {avg_errors:.1f}")
    print()

    # 按模块统计
    print("📚 按模块分布:")
    module_stats = {}
    for q in questions:
        m = q["module"]
        if m not in module_stats:
            module_stats[m] = {"total": 0, "mastered": 0, "errors": 0}
        module_stats[m]["total"] += 1
        if q.get("mastered"):
            module_stats[m]["mastered"] += 1
        module_stats[m]["errors"] += q.get("error_count", 1)

    for mod in MODULES:
        if mod in module_stats:
            s = module_stats[mod]
            print(f"  {mod}: {s['total']}题 (掌握{s['mastered']}) | 平均错{s['errors']/s['total']:.1f}次")

    print()

    # 按错误原因统计
    print("🔍 错误原因分布:")
    reason_stats = {}
    for q in questions:
        reason = q.get("error_reason", "未知")
        reason_stats[reason] = reason_stats.get(reason, 0) + 1

    for reason, count in sorted(reason_stats.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"  {reason}: {count} {bar}")

    print()

    # 按难度统计
    print("📈 难度分布:")
    diff_stats = {}
    for q in questions:
        d = q.get("difficulty", "未知")
        diff_stats[d] = diff_stats.get(d, 0) + 1
    for d in DIFFICULTIES:
        count = diff_stats.get(d, 0)
        if count > 0:
            print(f"  {d}: {count}题")


# ============================================================
# 导出
# ============================================================

def export_bank():
    """导出错题本为markdown"""
    data = load_bank()
    questions = data["questions"]

    if not questions:
        print("📭 错题库为空")
        return

    export_path = OUTPUT_DIR / f"错题本导出_{datetime.now().strftime('%Y%m%d')}.md"

    lines = [
        f"# 📕 曾周 · 错题本",
        f"",
        f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 总计：{len(questions)} 题",
        f"",
        f"---",
        f"",
    ]

    for mod in MODULES:
        mod_questions = [q for q in questions if q["module"] == mod]
        if not mod_questions:
            continue

        active = [q for q in mod_questions if not q.get("mastered")]
        mastered = [q for q in mod_questions if q.get("mastered")]

        lines.append(f"## {mod} ({len(mod_questions)}题 | 活跃{len(active)} | 掌握{len(mastered)})")
        lines.append("")

        mod_questions.sort(key=lambda q: -q.get("error_count", 1))

        for q in mod_questions:
            icon = "✅" if q.get("mastered") else "❌"
            lines.append(f"### {icon} {q['sub_module']} — 错过{q.get('error_count', 1)}次")
            lines.append(f"")
            lines.append(f"**题目**：{q['content']}")
            if q.get("options"):
                for opt in ["A", "B", "C", "D"]:
                    if opt in q["options"]:
                        lines.append(f"- {opt}. {q['options'][opt]}")
            lines.append(f"")
            lines.append(f"- 正确答案：**{q.get('answer', '?')}**")
            lines.append(f"- 你的答案：{q.get('your_answer', '?')}")
            lines.append(f"- 错误原因：{q.get('error_reason', '未知')}")
            if q.get("note"):
                lines.append(f"- 笔记：{q['note']}")
            lines.append("")

    lines += [
        f"---",
        f"*自动导出*",
    ]

    with open(export_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"📕 错题本已导出: {export_path}")
    print(f"   总计 {len(questions)} 题")
    return export_path


# ============================================================
# CLI
# ============================================================

def print_help():
    print(__doc__)


def main():
    args = sys.argv[1:]

    if not args:
        add_question_interactive()
        return

    if "--help" in args or "-h" in args:
        print_help()
        return

    if "--add" in args:
        add_question_interactive()
        return

    if "--quiz" in args:
        try:
            idx = args.index("--quiz")
            module = args[idx + 1]
            num = int(args[idx + 2]) if len(args) > idx + 2 else 10
            smart_quiz(module, num)
        except (IndexError, ValueError):
            print("❌ 用法: --quiz <模块|all> [题数]")
            print(f"   模块: {', '.join(MODULES.keys())}")
        return

    if "--list" in args:
        module = "all"
        weak_only = "--weak" in args
        try:
            idx = args.index("--list")
            if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
                module = args[idx + 1]
        except (IndexError, ValueError):
            pass
        list_questions(module, weak_only)
        return

    if "--stats" in args:
        print_stats()
        return

    if "--review" in args:
        review_mode()
        return

    if "--export" in args:
        export_bank()
        return

    print(f"❌ 未知参数: {' '.join(args)}")
    print_help()


if __name__ == "__main__":
    main()
