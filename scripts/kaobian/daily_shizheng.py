#!/usr/bin/env python3
"""
每日时政热点收集工具
━━━━━━━━━━━━━━━━━━━━
自动收集人民网、新华网等权威媒体的当日时政要闻，
按公基考试维度分类（政治/经济/文化/科技/法律/生态），
生成每日时政速览文件，方便曾周积累公基时政素材。

使用方法：
    python daily_shizheng.py              # 收集今日时政，生成日报
    python daily_shizheng.py --date 20260801  # 收集指定日期
    python daily_shizheng.py --week       # 生成本周时政周报
    python daily_shizheng.py --month 8    # 生成8月时政月报
    python daily_shizheng.py --quiz 5     # 从近期时政中出5道模拟题
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

# ============================================================
# 配置
# ============================================================

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "kaobian" / "shizheng"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = ROOT / "output" / "kaobian" / "zengzhou" / "shizheng"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# ============================================================
# RSS 源配置
# ============================================================

RSS_SOURCES = [
    {
        "name": "人民网-时政",
        "url": "http://politics.people.com.cn/rss/politics.xml",
        "category": "政治",
    },
    {
        "name": "新华网-要闻",
        "url": "http://www.news.cn/politics/xhll.xml",
        "category": "政治",
    },
    {
        "name": "人民网-经济",
        "url": "http://finance.people.com.cn/rss/finance.xml",
        "category": "经济",
    },
    {
        "name": "新华网-财经",
        "url": "http://www.news.cn/fortune/index.xml",
        "category": "经济",
    },
    {
        "name": "人民网-科技",
        "url": "http://scitech.people.com.cn/rss/scitech.xml",
        "category": "科技",
    },
]

# 手动抓取的网页源（无RSS，解析HTML标题）
HTML_SOURCES = [
    {
        "name": "人民日报-要闻",
        "url": "http://paper.people.com.cn/rmrb/html/latest.html",
        "category": "政治",
    },
    {
        "name": "中国政府网-政策",
        "url": "https://www.gov.cn/zhengce/zuixin.htm",
        "category": "政治",
    },
]

# ============================================================
# 分类关键词（用于自动分类 + 知识库标记）
# ============================================================

CATEGORY_KEYWORDS = {
    "政治": ["习近平", "国务院", "中央", "政治局", "全国人大", "政协", "外交部",
             "国防", "军队", "党建", "从严治党", "巡视", "纪委", "监察",
             "人事任免", "领导干部", "主题教育", "二十大", "中国式现代化",
             "国务院常务会议", "中央经济工作会议", "两会"],
    "经济": ["GDP", "经济增长", "财政收入", "减税", "降费", "营商环境",
             "民营企业", "中小企业", "制造业", "产业链", "供应链",
             "消费", "投资", "出口", "外贸", "一带一路", "RCEP",
             "金融", "银行", "证券", "保险", "房地产", "数字经济",
             "平台经济", "新能源", "碳中和", "碳达峰"],
    "文化": ["文化遗产", "非遗", "博物馆", "文物", "考古", "传统节日",
             "文化产业", "文旅", "旅游", "电影", "出版", "网络文学",
             "中华文明", "文化自信", "社会主义核心价值观"],
    "科技": ["航天", "卫星", "火箭", "空间站", "月球", "火星",
             "芯片", "半导体", "人工智能", "AI", "5G", "6G", "量子",
             "新能源车", "光伏", "风电", "核电", "生物医药", "基因",
             "深海", "极地", "北斗", "超级计算机", "大飞机"],
    "法律": ["立法", "修订", "施行", "司法解释", "最高法", "最高检",
             "宪法", "民法典", "刑法", "行政法", "食品安全法",
             "未成年人保护", "反垄断", "数据安全", "个人信息保护"],
    "生态": ["碳达峰", "碳中和", "绿水青山", "污染防治", "垃圾分类",
             "生物多样性", "国家公园", "长江禁渔", "黄河流域",
             "沙尘暴", "空气质量", "PM2.5", "新能源"],
    "民生": ["教育", "医疗", "养老", "住房", "就业", "收入", "社保",
             "医保", "扶贫", "乡村振兴", "粮食安全", "食品安全",
             "最低工资", "假期", "一老一小", "三孩"],
    "福建本地": ["福建", "福州", "厦门", "泉州", "龙岩", "漳州", "三明",
                "莆田", "南平", "宁德", "平潭", "闽", "海峡",
                "两岸", "台胞", "海丝", "武夷山", "土楼", "古田"],
}

# ============================================================
# RSS 解析
# ============================================================

def fetch_rss(url: str) -> Optional[str]:
    """抓取RSS源XML"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("gbk", errors="replace")
    except Exception as e:
        print(f"  ⚠️ RSS抓取失败 [{url}]: {e}")
        return None


def parse_rss_items(xml_content: str) -> list[dict]:
    """简易RSS XML解析（不依赖feedparser库）"""
    items = []

    # 匹配 <item>...</item> 块
    item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL | re.IGNORECASE)
    title_pattern = re.compile(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', re.IGNORECASE)
    link_pattern = re.compile(r'<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>', re.IGNORECASE)
    desc_pattern = re.compile(r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>', re.DOTALL | re.IGNORECASE)
    pubdate_pattern = re.compile(r'<pubDate>(.*?)</pubDate>', re.IGNORECASE)

    for item_match in item_pattern.finditer(xml_content):
        item_xml = item_match.group(1)

        title_m = title_pattern.search(item_xml)
        link_m = link_pattern.search(item_xml)
        desc_m = desc_pattern.search(item_xml)
        date_m = pubdate_pattern.search(item_xml)

        if title_m:
            title = title_m.group(1).strip()
            # 清理HTML标签
            title = re.sub(r'<[^>]+>', '', title)

            desc = ""
            if desc_m:
                desc = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip()
                desc = desc[:200]  # 截断

            items.append({
                "title": title,
                "url": link_m.group(1).strip() if link_m else "",
                "summary": desc,
                "pub_date": date_m.group(1).strip() if date_m else "",
            })

    return items


# ============================================================
# HTML 标题提取
# ============================================================

def fetch_html_titles(url: str) -> list[dict]:
    """从HTML页面提取新闻标题列表"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            try:
                html = content.decode("utf-8")
            except UnicodeDecodeError:
                html = content.decode("gbk", errors="replace")
    except Exception as e:
        print(f"  ⚠️ HTML抓取失败 [{url}]: {e}")
        return []

    items = []
    # 找所有包含链接的标题文本
    link_pattern = re.compile(
        r'<a\s[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )

    for match in link_pattern.finditer(html):
        href = match.group(1)
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()

        if len(text) >= 8 and len(text) <= 200:
            if not href.startswith("http"):
                href = urljoin(url, href)
            items.append({"title": text, "url": href, "summary": ""})

    return items[:30]


# ============================================================
# 分类 + 去重
# ============================================================

def classify_article(title: str, summary: str = "", source_category: str = "") -> list[str]:
    """自动分类一篇文章，返回可能属于的类别"""
    text = title + " " + summary
    categories = []

    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                if cat not in categories:
                    categories.append(cat)
                break

    if not categories:
        categories.append("综合")

    return categories


def deduplicate(items: list[dict]) -> list[dict]:
    """按标题相似度去重"""
    seen = set()
    result = []
    for item in items:
        # 取标题前20字作为去重键
        key = item["title"][:20]
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ============================================================
# 收集逻辑
# ============================================================

def collect_today(date_str: str = None) -> dict:
    """收集指定日期的时政要闻"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")

    print(f"📡 时政热点收集 — {date_str}")
    print("=" * 60)

    all_articles = []

    # 1. RSS源
    for src in RSS_SOURCES:
        print(f"\n📡 RSS: {src['name']}")
        xml = fetch_rss(src["url"])
        if xml:
            items = parse_rss_items(xml)
            for item in items:
                item["_source"] = src["name"]
                item["_source_cat"] = src["category"]
            print(f"   获取 {len(items)} 条")
            all_articles.extend(items)

        time.sleep(0.5)  # 礼貌延迟

    # 2. HTML源
    for src in HTML_SOURCES:
        print(f"\n📡 HTML: {src['name']}")
        items = fetch_html_titles(src["url"])
        for item in items:
            item["_source"] = src["name"]
            item["_source_cat"] = src["category"]
        print(f"   获取 {len(items)} 条")
        all_articles.extend(items)

        time.sleep(0.5)

    # 3. 去重
    before = len(all_articles)
    all_articles = deduplicate(all_articles)
    print(f"\n📊 去重: {before} → {len(all_articles)} 条")

    # 4. 分类
    categorized = {}
    for article in all_articles:
        cats = classify_article(article["title"], article.get("summary", ""),
                                article.get("_source_cat", ""))
        article["_categories"] = cats
        for cat in cats:
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(article)

    # 5. 保存
    result = {
        "date": date_str,
        "collected_at": datetime.now().isoformat(),
        "total": len(all_articles),
        "categorized": {cat: len(items) for cat, items in categorized.items()},
        "articles": all_articles,
    }

    save_file = DATA_DIR / f"shizheng_{date_str}.json"
    with open(save_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n💾 原始数据: {save_file}")
    print(f"   分类统计: {result['categorized']}")

    return result


# ============================================================
# 日报/周报/月报生成
# ============================================================

def generate_daily_report(data: dict):
    """生成每日时政速览"""
    date_str = data["date"]
    report_path = OUTPUT_DIR / f"时政日报_{date_str}.md"

    lines = [
        f"# 📰 时政日报 — {date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
        f"",
        f"> 📊 今日收录 {data['total']} 条要闻 | 生成时间 {datetime.now().strftime('%H:%M')}",
        f"",
        f"---",
        f"",
    ]

    # 按分类整理
    categorized = {}
    for article in data["articles"]:
        for cat in article.get("_categories", ["综合"]):
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(article)

    # 优先展示公基高分值类别
    priority_order = ["政治", "经济", "法律", "文化", "科技", "生态", "民生", "福建本地", "综合"]

    for cat in priority_order:
        if cat not in categorized:
            continue
        articles = categorized[cat][:10]  # 每个类别最多10条
        lines.append(f"## {cat}")
        lines.append("")
        for a in articles:
            lines.append(f"- **[{a['title']}]({a['url']})**  [{a.get('_source', '')}]")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"### 💡 公基考点提示",
        f"",
        f"今日时政中以下内容为公基高频考点：",
        f"",
    ]

    # 自动提示高频考点
    tips = []
    for article in data["articles"]:
        title = article["title"]
        if any(kw in title for kw in ["习近平", "国务院常务会议", "中央经济"]):
            tips.append(f"- ⭐ **政治**：{title[:60]}（领导人讲话/重要会议常出单选题）")
        if any(kw in title for kw in ["GDP", "CPI", "PMI", "降准", "降息", "LPR"]):
            tips.append(f"- ⭐ **经济**：{title[:60]}（经济数据常出资料分析题）")
        if any(kw in title for kw in ["立法", "修订", "施行", "最高法"]):
            tips.append(f"- ⭐ **法律**：{title[:60]}（新法新规常出判断题）")

    if tips:
        lines.extend(tips[:5])
    else:
        lines.append("- 今日暂无特别突出的考点，持续关注中")

    lines += [
        f"",
        f"---",
        f"",
        f"*自动生成 | 数据来源：人民网、新华网、中国政府网*",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"📊 日报已生成: {report_path}")
    return report_path


def generate_weekly_report():
    """生成本周时政周报"""
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())

    all_articles = []
    for i in range(7):
        d = (week_start + timedelta(days=i)).strftime("%Y%m%d")
        file = DATA_DIR / f"shizheng_{d}.json"
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_articles.extend(data["articles"])

    all_articles = deduplicate(all_articles)
    week_str = f"{week_start.strftime('%Y%m%d')}-{today.strftime('%Y%m%d')}"

    report_path = OUTPUT_DIR / f"时政周报_{week_str}.md"

    lines = [
        f"# 📰 时政周报 — {week_start.strftime('%m/%d')} - {today.strftime('%m/%d')}",
        f"",
        f"> 📊 本周收录 {len(all_articles)} 条要闻",
        f"",
        f"---",
        f"",
        f"## 🔥 本周重点（公基高频考点）",
        f"",
    ]

    # 按关键词聚合热点
    hot_topics = {}
    for article in all_articles:
        title = article["title"]
        for kw in ["习近平", "国务院", "中央政治", "二十大", "中国式现代化", "两会",
                    "GDP", "碳达峰", "碳中和", "乡村振兴", "一带一路", "航天"]:
            if kw in title:
                key = kw[:4]
                if key not in hot_topics:
                    hot_topics[key] = []
                hot_topics[key].append(title[:60])
                break

    for topic, titles in sorted(hot_topics.items(), key=lambda x: -len(x[1])):
        lines.append(f"### {topic}（{len(titles)}条相关）")
        for t in titles[:3]:
            lines.append(f"- {t}")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## 📋 本周时政要点速记",
        f"",
        f"| 类别 | 关键事件 | 可能考点 |",
        f"|------|---------|---------|",
    ]

    # 每类挑最重要的3条
    categorized = {}
    for article in all_articles:
        for cat in article.get("_categories", ["综合"]):
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(article)

    for cat in ["政治", "经济", "法律", "科技", "文化"]:
        if cat in categorized:
            for a in categorized[cat][:3]:
                lines.append(f"| {cat} | {a['title'][:40]} | 待补充 |")

    lines += [
        f"",
        f"---",
        f"*自动生成 | 数据来源：人民网、新华网、中国政府网*",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"📊 周报已生成: {report_path}")
    return report_path


# ============================================================
# 模拟题生成
# ============================================================

def generate_quiz(num_questions: int = 5):
    """从近期时政中生成公基模拟题"""
    # 加载最近7天的时政
    all_articles = []
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        file = DATA_DIR / f"shizheng_{d}.json"
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_articles.extend(data["articles"])

    if not all_articles:
        print("❌ 没有足够的时政数据，请先运行收集: python daily_shizheng.py")
        return

    all_articles = deduplicate(all_articles)

    report_path = OUTPUT_DIR / f"时政模拟题_{datetime.now().strftime('%Y%m%d')}.md"
    lines = [
        f"# 📝 时政常识模拟题",
        f"",
        f"> 基于近7天时政热点自动生成 | {datetime.now().strftime('%Y-%m-%d')}",
        f"> 共 {num_questions} 题 | 题型：单选",
        f"",
        f"---",
        f"",
    ]

    # 从热门时政中选素材出题
    political_articles = [a for a in all_articles
                          if any(kw in a["title"] for kw in ["习近平", "国务院", "中央", "部长", "政策"])]
    selected = political_articles[:num_questions]

    for i, article in enumerate(selected, 1):
        lines.append(f"### {i}. {article['title']}")
        lines.append(f"")
        lines.append(f"A. [选项待补充]")
        lines.append(f"B. [选项待补充]")
        lines.append(f"C. [选项待补充]")
        lines.append(f"D. [选项待补充]")
        lines.append(f"")
        lines.append(f"> 来源：[{article.get('_source', '未知')}]({article['url']})")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"### 参考答案",
        f"",
    ]
    for i in range(1, num_questions + 1):
        lines.append(f"{i}. [待完善] — 建议手动补充选项和正确答案")

    lines += [
        f"",
        f"> 💡 提示：当前为半自动生成，建议根据实际时政内容手工完善选项和答案。",
        f"> 此功能的价值在于**框定出题范围**——近7天最重要的时政事件。",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"📝 模拟题已生成: {report_path}")
    return report_path


# ============================================================
# CLI
# ============================================================

def print_help():
    print(__doc__)


def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print_help()
        return

    if "--date" in args:
        try:
            idx = args.index("--date")
            date_str = args[idx + 1]
        except IndexError:
            print("❌ 用法: --date YYYYMMDD")
            return
    else:
        date_str = datetime.now().strftime("%Y%m%d")

    if "--week" in args:
        # 先收集本周数据
        today = datetime.now()
        for i in range(7):
            d = (today - timedelta(days=i)).strftime("%Y%m%d")
            if not (DATA_DIR / f"shizheng_{d}.json").exists():
                print(f"📡 补充收集 {d}...")
            try:
                collect_today(d)
            except Exception as e:
                print(f"  ⚠️ {d} 收集失败: {e}")
        generate_weekly_report()
        return

    if "--month" in args:
        print("📡 月报功能开发中，请先使用 --week 生成本周周报")
        return

    if "--quiz" in args:
        try:
            idx = args.index("--quiz")
            num = int(args[idx + 1])
        except (IndexError, ValueError):
            num = 5
        # 确保有数据
        if not list(DATA_DIR.glob("shizheng_*.json")):
            print("📡 没有时政数据，先收集今天的...")
            collect_today()
        generate_quiz(num)
        return

    # 默认：收集今日 + 生成日报
    try:
        data = collect_today(date_str)
        if data["total"] > 0:
            generate_daily_report(data)
        else:
            print("\n⚠️ 今日未收集到时政数据，请检查网络或稍后重试")
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
