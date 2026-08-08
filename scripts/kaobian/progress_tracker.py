#!/usr/bin/env python3
"""
学习进度追踪工具
━━━━━━━━━━━━━━━━━━
记录每日学习情况、模考成绩，自动生成进度报告和可视化，
帮助曾周了解自己的备考状态、发现薄弱模块。

使用方法：
    python progress_tracker.py                    # 交互式记录今日学习
    python progress_tracker.py --log 公基 90 法律  # 快速记录（模块 分钟 备注）
    python progress_tracker.py --report           # 生成进度报告
    python progress_tracker.py --mock 72          # 记录模考成绩
    python progress_tracker.py --stats            # 查看统计
    python progress_tracker.py --chart            # 生成进度图表HTML
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ============================================================
# 配置
# ============================================================

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "kaobian" / "progress"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = ROOT / "output" / "kaobian" / "zengzhou"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STUDY_LOG_FILE = DATA_DIR / "study_log.json"
MOCK_EXAM_FILE = DATA_DIR / "mock_exams.json"

# 考试模块定义
MODULES = {
    "公基": {"full": "公共基础知识", "target_score": 19, "total": 24},
    "言语": {"full": "言语理解与表达", "target_score": 20, "total": 25},
    "判断": {"full": "判断推理", "target_score": 22, "total": 26.5},
    "数量": {"full": "数量关系", "target_score": 9, "total": 14.5},
    "资料": {"full": "资料分析", "target_score": 8, "total": 10},
}

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]

# ============================================================
# 数据加载
# ============================================================

def load_study_log() -> dict:
    if STUDY_LOG_FILE.exists():
        with open(STUDY_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"records": []}


def save_study_log(data: dict):
    with open(STUDY_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_mock_exams() -> dict:
    if MOCK_EXAM_FILE.exists():
        with open(MOCK_EXAM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"exams": []}


def save_mock_exams(data: dict):
    with open(MOCK_EXAM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# 记录逻辑
# ============================================================

def log_study(module: str, minutes: int, note: str = ""):
    """记录今日学习"""
    today = datetime.now().strftime("%Y-%m-%d")

    if module not in MODULES:
        print(f"❌ 未知模块: {module}")
        print(f"   可用模块: {', '.join(MODULES.keys())}")
        return

    data = load_study_log()
    record = {
        "date": today,
        "module": module,
        "minutes": minutes,
        "note": note,
        "logged_at": datetime.now().isoformat(),
    }
    data["records"].append(record)
    save_study_log(data)

    hours = minutes / 60
    print(f"✅ 已记录: [{today}] {MODULES[module]['full']} — {hours:.1f}小时")
    if note:
        print(f"   备注: {note}")


def log_mock_exam(total_score: float, scores_detail: Optional[dict] = None):
    """记录模考成绩"""
    today = datetime.now().strftime("%Y-%m-%d")

    data = load_mock_exams()
    exam = {
        "date": today,
        "total_score": total_score,
        "detail": scores_detail or {},
        "logged_at": datetime.now().isoformat(),
    }
    data["exams"].append(exam)
    save_mock_exams(data)

    # 评级
    if total_score >= 80:
        grade = "🌟 优秀"
    elif total_score >= 72:
        grade = "👍 良好（有望进面）"
    elif total_score >= 65:
        grade = "📚 还需努力"
    else:
        grade = "💪 加油追赶"

    print(f"✅ 已记录模考: [{today}] {total_score}分 — {grade}")

    # 与目标对比
    target = 75
    gap = total_score - target
    if gap >= 0:
        print(f"   🎯 已超过目标 {gap} 分！")
    else:
        print(f"   🎯 距目标还差 {abs(gap)} 分")


def interactive_log():
    """交互式记录"""
    print("\n📝 记录今日学习")
    print("=" * 40)
    print("模块代号:")
    for key, info in MODULES.items():
        print(f"  {key} = {info['full']}")

    while True:
        module = input("\n模块（回车结束）: ").strip()
        if not module:
            break
        if module not in MODULES:
            print(f"  ❌ 无效模块，可用: {', '.join(MODULES.keys())}")
            continue

        try:
            minutes = int(input("学习时长（分钟）: ").strip())
        except ValueError:
            print("  ❌ 请输入数字")
            continue

        note = input("备注（可选）: ").strip()
        log_study(module, minutes, note)


# ============================================================
# 统计分析
# ============================================================

def calculate_stats() -> dict:
    """计算统计数据"""
    study_data = load_study_log()
    mock_data = load_mock_exams()
    records = study_data["records"]
    exams = mock_data["exams"]

    if not records:
        return {"error": "暂无学习记录"}

    today = datetime.now()

    # 总学习时长
    total_minutes = sum(r["minutes"] for r in records)
    total_hours = total_minutes / 60

    # 各模块时长
    module_hours = {}
    for r in records:
        m = r["module"]
        if m not in module_hours:
            module_hours[m] = 0
        module_hours[m] += r["minutes"] / 60

    # 最近7天统计
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    week_records = [r for r in records if r["date"] >= week_ago]
    week_minutes = sum(r["minutes"] for r in week_records)
    week_days = len(set(r["date"] for r in week_records))

    # 连续打卡天数
    dates = sorted(set(r["date"] for r in records), reverse=True)
    streak = 0
    for i, d in enumerate(dates):
        expected = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if d == expected:
            streak += 1
        else:
            break

    # 模考统计
    mock_stats = {}
    if exams:
        scores = [e["total_score"] for e in exams]
        mock_stats = {
            "count": len(exams),
            "latest": scores[-1],
            "highest": max(scores),
            "lowest": min(scores),
            "avg": sum(scores) / len(scores),
            "trend": "📈 上升" if len(scores) >= 2 and scores[-1] > scores[-2] else
                      "📉 下降" if len(scores) >= 2 and scores[-1] < scores[-2] else "➡️ 持平",
        }

    return {
        "total_hours": total_hours,
        "total_days": len(dates),
        "module_hours": module_hours,
        "week_hours": week_minutes / 60,
        "week_days": week_days,
        "streak": streak,
        "mock_stats": mock_stats,
    }


def print_stats():
    """打印统计"""
    stats = calculate_stats()
    if "error" in stats:
        print(f"❌ {stats['error']}")
        return

    print("\n📊 学习统计")
    print("=" * 50)
    print(f"  总学习时长: {stats['total_hours']:.1f} 小时")
    print(f"  累计学习天数: {stats['total_days']} 天")
    print(f"  连续打卡: {stats['streak']} 天 🔥")
    print(f"  本周学习: {stats['week_hours']:.1f}小时 / {stats['week_days']}天")
    print()

    print("📚 各模块学习时长:")
    target_total = sum(m["target_score"] for m in MODULES.values())
    for key, info in MODULES.items():
        hours = stats["module_hours"].get(key, 0)
        pct = hours / max(stats["total_hours"], 0.1) * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {key} ({info['full']}): {hours:5.1f}h {bar} {pct:.0f}%")

    if stats["mock_stats"]:
        m = stats["mock_stats"]
        print(f"\n📝 模考成绩:")
        print(f"  次数: {m['count']} | 最新: {m['latest']} | 最高: {m['highest']} | 平均: {m['avg']:.1f}")
        print(f"  趋势: {m['trend']}")
        print(f"  距目标(75分): {'+' if m['latest'] >= 75 else ''}{m['latest'] - 75:.0f}分")


# ============================================================
# 报告生成
# ============================================================

def generate_report():
    """生成进度报告"""
    stats = calculate_stats()
    if "error" in stats:
        print(f"❌ {stats['error']}")
        return

    today = datetime.now()
    report_path = OUTPUT_DIR / f"学习进度报告_{today.strftime('%Y%m%d')}.md"

    # 计算进度百分比（按时间推算）
    # 目标：基础期(8-10月)约200小时，强化期(10-12月)约400小时，冲刺期(1-3月)约500小时
    # 总计约1100小时
    total_target = 1100
    progress_pct = min(100, stats["total_hours"] / total_target * 100)

    lines = [
        f"# 📊 学习进度报告",
        f"",
        f"> 生成时间：{today.strftime('%Y-%m-%d %H:%M')}",
        f"> 备考阶段：基础期（2026年8-10月）",
        f"> 目标分数：综合基础知识 75分+",
        f"",
        f"---",
        f"",
        f"## 🎯 总体概览",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总学习时长 | **{stats['total_hours']:.1f} 小时** |",
        f"| 累计学习天数 | {stats['total_days']} 天 |",
        f"| 连续打卡 | {stats['streak']} 天 🔥 |",
        f"| 本周学习 | {stats['week_hours']:.1f}小时 / {stats['week_days']}天 |",
        f"| 总进度 | {progress_pct:.1f}% (目标{total_target}h) |",
        f"",
        f"### 进度条",
        f"",
        f"`{'█' * int(progress_pct / 5)}{'░' * (20 - int(progress_pct / 5))}` {progress_pct:.1f}%",
        f"",
        f"---",
        f"",
        f"## 📚 各模块投入",
        f"",
        f"| 模块 | 学习时长 | 占比 | 推荐占比 | 状态 |",
        f"|------|---------|------|---------|------|",
    ]

    # 推荐分配比例（公基占大头因为它内容最多）
    recommended = {"公基": 35, "言语": 20, "判断": 20, "数量": 15, "资料": 10}
    for key, info in MODULES.items():
        hours = stats["module_hours"].get(key, 0)
        pct = hours / max(stats["total_hours"], 0.1) * 100
        rec = recommended.get(key, 20)
        diff = pct - rec
        status = "✅ 均衡" if abs(diff) < 10 else ("⚠️ 偏多" if diff > 0 else "🔴 偏少")
        lines.append(f"| {key} | {hours:.1f}h | {pct:.0f}% | {rec}% | {status} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 📝 模考成绩",
        f"",
    ]

    if stats["mock_stats"]:
        m = stats["mock_stats"]
        lines += [
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 模考次数 | {m['count']} |",
            f"| 最新成绩 | **{m['latest']}** 分 |",
            f"| 最高成绩 | {m['highest']} 分 |",
            f"| 最低成绩 | {m['lowest']} 分 |",
            f"| 平均成绩 | {m['avg']:.1f} 分 |",
            f"| 趋势 | {m['trend']} |",
            f"| 距目标 | {'+' if m['latest'] >= 75 else ''}{m['latest'] - 75:.0f}分 |",
            f"",
        ]
    else:
        lines.append("> 暂无模考记录，建议基础阶段结束后开始第一次模考")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## 🏔️ 本周分析",
        f"",
    ]

    if stats["week_days"] >= 5:
        lines.append(f"✅ 本周学习天数达标（{stats['week_days']}/7天）")
    else:
        lines.append(f"⚠️ 本周学习天数不足（{stats['week_days']}/7天），建议保持每天至少2小时")
    lines.append(f"📊 周学习时长: {stats['week_hours']:.1f}小时")

    lines += [
        f"",
        f"---",
        f"",
        f"## 💡 建议",
        f"",
    ]

    # 基于数据给出建议
    suggestions = []
    module_hours = stats["module_hours"]

    if module_hours.get("公基", 0) < stats["total_hours"] * 0.2:
        suggestions.append("- 🔴 **公基投入不足**：公基占24分且内容最多，建议提升至总时间的35%")
    if module_hours.get("资料", 0) < 1:
        suggestions.append("- 🟡 **资料分析练习较少**：这是高性价比模块，每天保持2篇练习即可稳定提分")
    if stats["streak"] < 3:
        suggestions.append("- 🟡 **连续打卡中断**：保持每天都学一点比突击更有效")
    if stats.get("week_hours", 0) < 10:
        suggestions.append("- 🔴 **本周学习时长偏低**：基础期建议每周至少15-20小时")
    if not stats["mock_stats"]:
        suggestions.append("- 💡 **建议完成基础阶段后开始模考**：用模考成绩校准学习方向")

    if not suggestions:
        suggestions.append("- ✅ 当前节奏不错，继续保持！")

    lines.extend(suggestions)

    lines += [
        f"",
        f"---",
        f"",
        f"*自动生成 | 数据文件: {STUDY_LOG_FILE}*",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n📊 报告已生成: {report_path}")
    return report_path


# ============================================================
# HTML 图表生成
# ============================================================

def generate_chart_html():
    """生成可视化进度图HTML"""
    stats = calculate_stats()
    mock_data = load_mock_exams()
    study_data = load_study_log()

    exams = mock_data["exams"]
    records = study_data["records"]

    # 准备数据
    dates = []
    daily_hours = []
    if records:
        # 按日期汇总学习时长
        from collections import defaultdict
        daily = defaultdict(int)
        for r in records:
            daily[r["date"]] += r["minutes"]
        sorted_dates = sorted(daily.keys())[-30:]  # 最近30天
        dates = sorted_dates
        daily_hours = [daily[d] / 60 for d in sorted_dates]

    mock_dates = [e["date"] for e in exams]
    mock_scores = [e["total_score"] for e in exams]

    chart_path = OUTPUT_DIR / f"学习进度图_{datetime.now().strftime('%Y%m%d')}.html"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>曾周 · 考编学习进度</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Microsoft YaHei', sans-serif;
    background: #f5f5f5;
    color: #333;
    padding: 20px;
  }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ text-align: center; margin-bottom: 8px; font-size: 24px; }}
  .subtitle {{ text-align: center; color: #999; margin-bottom: 24px; font-size: 14px; }}
  .card {{
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }}
  .card h2 {{ font-size: 18px; margin-bottom: 16px; color: #1a1a1a; }}
  .kpi-row {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }}
  .kpi {{
    flex: 1;
    min-width: 120px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
  }}
  .kpi.green {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
  .kpi.orange {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
  .kpi.blue {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
  .kpi .value {{ font-size: 32px; font-weight: bold; }}
  .kpi .label {{ font-size: 13px; opacity: 0.9; margin-top: 4px; }}
  .bar-chart {{ margin-top: 12px; }}
  .bar-row {{
    display: flex;
    align-items: center;
    margin-bottom: 8px;
  }}
  .bar-label {{ width: 60px; font-size: 13px; text-align: right; margin-right: 12px; }}
  .bar-track {{
    flex: 1;
    height: 24px;
    background: #f0f0f0;
    border-radius: 12px;
    overflow: hidden;
  }}
  .bar-fill {{
    height: 100%;
    border-radius: 12px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    transition: width 0.5s;
  }}
  .bar-value {{ width: 60px; font-size: 13px; margin-left: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0; }}
  th {{ color: #999; font-weight: normal; font-size: 12px; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; }}
  .tag-up {{ background: #e8f5e9; color: #2e7d32; }}
  .tag-down {{ background: #fce4ec; color: #c62828; }}
  .footer {{ text-align: center; color: #ccc; margin-top: 24px; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
  <h1>📊 曾周 · 考编备考进度</h1>
  <p class="subtitle">目标：综合基础知识 75分+ | 目标区域：龙岩新罗区 | {datetime.now().strftime('%Y-%m-%d')}</p>

  <!-- KPI卡片 -->
  <div class="card">
    <h2>🎯 关键指标</h2>
    <div class="kpi-row">
      <div class="kpi">
        <div class="value">{stats['total_hours']:.0f}</div>
        <div class="label">总学习小时</div>
      </div>
      <div class="kpi green">
        <div class="value">{stats['streak']}</div>
        <div class="label">连续打卡天 🔥</div>
      </div>
      <div class="kpi orange">
        <div class="value">{stats['week_hours']:.1f}</div>
        <div class="label">本周学习小时</div>
      </div>
      <div class="kpi blue">
        <div class="value">{stats['mock_stats'].get('latest', '-') if stats['mock_stats'] else '-'}</div>
        <div class="label">最新模考分</div>
      </div>
    </div>
  </div>

  <!-- 模块分布 -->
  <div class="card">
    <h2>📚 各模块学习时长分布</h2>
    <div class="bar-chart">
"""

    total = max(stats["total_hours"], 0.1)
    for key, info in MODULES.items():
        hours = stats["module_hours"].get(key, 0)
        pct = hours / total * 100
        html += f"""      <div class="bar-row">
        <div class="bar-label">{key}</div>
        <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
        <div class="bar-value">{hours:.1f}h ({pct:.0f}%)</div>
      </div>
"""

    html += """    </div>
  </div>

  <!-- 模考成绩 -->
  <div class="card">
    <h2>📝 模考成绩记录</h2>
"""

    if exams:
        html += """    <table>
      <tr><th>日期</th><th>总分</th><th>距目标(75)</th><th>趋势</th></tr>
"""
        prev = None
        for e in exams[-10:]:  # 最近10次
            gap = e["total_score"] - 75
            gap_str = f"+{gap:.0f}" if gap >= 0 else f"{gap:.0f}"
            trend = ""
            if prev is not None:
                if e["total_score"] > prev:
                    trend = '<span class="tag tag-up">📈</span>'
                elif e["total_score"] < prev:
                    trend = '<span class="tag tag-down">📉</span>'
                else:
                    trend = '➡️'
            html += f"""      <tr><td>{e['date']}</td><td><b>{e['total_score']}</b></td><td>{gap_str}</td><td>{trend}</td></tr>
"""
            prev = e["total_score"]
        html += "    </table>\n"
    else:
        html += "    <p style='color:#999'>暂无模考记录</p>\n"

    html += f"""  </div>

  <p class="footer">自动生成 | 曾周考编备考追踪 | 数据来源：本地学习日志</p>
</div>
</body>
</html>"""

    with open(chart_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"📈 图表已生成: {chart_path}")
    return chart_path


# ============================================================
# CLI
# ============================================================

def print_help():
    print(__doc__)


def main():
    args = sys.argv[1:]

    if not args:
        interactive_log()
        return

    if "--help" in args or "-h" in args:
        print_help()
        return

    if "--log" in args:
        try:
            idx = args.index("--log")
            module = args[idx + 1]
            minutes = int(args[idx + 2])
            note = args[idx + 3] if len(args) > idx + 3 else ""
            log_study(module, minutes, note)
        except (IndexError, ValueError):
            print("❌ 用法: --log <模块> <分钟> [备注]")
            print(f"   模块: {', '.join(MODULES.keys())}")
        return

    if "--mock" in args:
        try:
            idx = args.index("--mock")
            score = float(args[idx + 1])
            log_mock_exam(score)
        except (IndexError, ValueError):
            print("❌ 用法: --mock <分数>")
        return

    if "--stats" in args:
        print_stats()
        return

    if "--report" in args:
        generate_report()
        generate_chart_html()
        return

    if "--chart" in args:
        generate_chart_html()
        return

    print(f"❌ 未知参数: {' '.join(args)}")
    print_help()


if __name__ == "__main__":
    main()
