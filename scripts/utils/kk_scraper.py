#!/usr/bin/env python3
"""
KK网信息采集器 - 龙岩本地论坛康养线索提取
============================================
使用方法:
    # 从浏览器保存的搜索HTML中解析
    python kk_scraper.py parse <html文件路径>

    # 从淘淘居护工分类抓取
    python kk_scraper.py nursing [区域ID]

    # 查看搜索查询URL
    python kk_scraper.py queries

输出: output/kk_report_{日期}.md 或 girlfrend/work/kk_data/ 目录
"""

import sys
import os
import re
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path


# ============================================================
# 配置
# ============================================================

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "girlfriend" / "work" / "kk_data"
TEMP_DIR = PROJECT_ROOT / "temp"

# 搜索查询模板
SEARCH_QUERIES = {
    "直接线索": "site:0597kk.com 养老 OR 康养 OR 康复 OR 护工 OR 护理 OR 保姆",
    "竞品监控": "site:0597kk.com 养老院 OR 福利院 OR 敬老院",
    "医院渠道": "site:0597kk.com 医院 骨科 OR 神经内科 OR 老人",
    "万龄品牌": "site:0597kk.com 万龄",
    "淘淘居护工": "site:taotaoju.vip 护工 OR 老人 OR 护理",
    "社区养老": "site:0597kk.com 社区 老年 OR 老龄 OR 养老",
}

# 业务关键词及权重
KEYWORD_WEIGHTS = {
    # 高价值（直接线索）- 权重 10
    "养老": 10, "康养": 10, "康复": 10, "护工": 10,
    "保姆": 10, "陪护": 10, "护理": 10,
    "失能": 10, "卧床": 10, "术后": 10,
    "中风": 10, "偏瘫": 10, "不能自理": 10,
    "长者": 8, "老年": 5,
    # 中价值（市场情报）- 权重 5
    "骨科": 5, "神经内科": 5, "康复科": 5,
    "养老院": 5, "福利院": 5, "敬老院": 5,
    "万龄": 5, "同心圆": 5, "红炭山": 5,
    "医院": 3, "住院": 5,
    # 背景信息 - 权重 2
    "老人": 3, "老龄化": 2, "退休": 2,
    "社区养老": 2, "居家养老": 5,
}

# KK网版块名称映射
BOARD_NAMES = {
    2: "龙岩热点", 3: "龙岩美食", 5: "汽车频道",
    19: "谈天说地", 22: "社区事务", 43: "原创摄影",
    57: "龙岩摩族", 65: "家有宠物", 77: "母婴亲子",
    94: "二手交易", 114: "拼车信息", 116: "情感天地",
    121: "法律咨询", 133: "单车运动", 136: "婚庆频道",
    143: "K币竞拍", 156: "房屋租售", 157: "龙岩房产",
    158: "家居装修", 159: "求职招聘", 165: "同城热恋",
    170: "游山玩水", 173: "爱心助学", 175: "商家信息",
    179: "水族鱼友", 200: "龙岩户外", 204: "同城群聊",
    205: "家政服务", 206: "教育培训", 207: "二手车",
    210: "钓鱼一族", 235: "房车生活", 237: "汉服龙岩",
    239: "金融理财", 727: "龙岩口腔",
    729: "银行", 730: "新罗政协", 731: "适中镇",
    732: "消防大队", 734: "新罗反诈", 735: "东城街道",
    736: "西陂街道", 737: "北城街道", 738: "新罗文旅",
}


# ============================================================
# 核心功能
# ============================================================

def extract_posts_from_html(html_text):
    """
    从 Google 搜索结果 HTML 中提取 KK 网帖子链接。
    支持多种 Google 搜索结果页的 DOM 结构。
    """
    posts = []

    # 方法1: 标准搜索结果链接
    pattern1 = r'<a href="(https?://(?:www\.)?0597kk\.com/(?:thread-\d+-\d+-\d+\.html|forum\.php\?[^"]*))"[^>]*>'
    links1 = re.findall(pattern1, html_text)
    for url in set(links1):
        posts.append({"url": url, "title": "", "source": "google_search"})

    # 方法2: 带标题的搜索结果
    pattern2 = r'<a href="(https?://(?:www\.)?0597kk\.com/(?:thread-\d+-\d+-\d+\.html|forum\.php\?[^"]*))"[^>]*>\s*(?:<[^>]+>)*\s*(.*?)\s*(?:</[^>]+>)*\s*</a>'
    matches2 = re.findall(pattern2, html_text, re.DOTALL)
    for url, title in matches2:
        title = re.sub(r'<[^>]+>', '', title).strip()
        # 跳过太短的或无意义的标题
        if len(title) > 3:
            # 更新或添加
            existing = [p for p in posts if p["url"] == url]
            if existing and not existing[0]["title"]:
                existing[0]["title"] = title
            elif not existing:
                posts.append({"url": url, "title": title, "source": "google_search"})

    # 方法3: 搜索 0597kk.com 的所有链接（兜底）
    pattern3 = r'(https?://(?:www\.)?0597kk\.com/[^\s"\'<>]+)'
    links3 = re.findall(pattern3, html_text)
    for url in set(links3):
        if not any(p["url"] == url for p in posts):
            # 过滤掉静态资源
            if not re.search(r'\.(js|css|png|jpg|gif|ico|xml)(\?|$)', url):
                posts.append({"url": url, "title": "", "source": "google_search"})

    return posts


def extract_posts_from_archiver(html_gbk):
    """从 KK 网 archiver 页面提取帖子列表"""
    html = html_gbk.decode("gbk", errors="replace") if isinstance(html_gbk, bytes) else html_gbk

    pattern = r'<li><a href="tid-(\d+)\.html">(.*?)</a>\s*\((\d+)'
    matches = re.findall(pattern, html)

    posts = []
    for tid, title_raw, replies in matches:
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        posts.append({
            "tid": tid,
            "title": title,
            "replies": int(replies),
            "url": f"https://www.0597kk.com/thread-{tid}-1-1.html",
            "source": "archiver",
        })
    return posts


def score_post(post):
    """对帖子进行业务相关性评分"""
    title = post.get("title", "")
    score = 0
    matched = []

    for kw, weight in KEYWORD_WEIGHTS.items():
        if kw in title:
            score += weight
            matched.append(kw)

    post["score"] = score
    post["matched_kw"] = matched

    # 分类
    if score >= 15:
        post["level"] = "🔴 高价值线索"
    elif score >= 8:
        post["level"] = "🟡 值得关注"
    elif score >= 3:
        post["level"] = "🟢 背景信息"
    else:
        post["level"] = "⚪ 无关"

    return post


def extract_tid(url):
    """从 URL 中提取帖子 ID"""
    m = re.search(r"thread-(\d+)", url)
    return m.group(1) if m else None


def classify_post(post):
    """判断帖子属于哪个业务场景"""
    title = post.get("title", "")
    url = post.get("url", "")

    if any(kw in title for kw in ["护工", "保姆", "陪护"]):
        return "护工需求"
    if any(kw in title for kw in ["康复", "术后", "中风", "偏瘫"]):
        return "康复需求"
    if any(kw in title for kw in ["养老院", "福利院", "敬老院", "康养"]):
        return "机构咨询"
    if any(kw in title for kw in ["骨科", "神经内科", "医院"]):
        return "医疗相关"
    if "万龄" in title:
        return "品牌提及"
    if "老人" in title or "老年" in title or "长者" in title:
        return "老年话题"
    return "其他"


# ============================================================
# 输出
# ============================================================

def generate_markdown_report(posts, output_path=None):
    """生成 Markdown 格式的采集报告"""
    if not posts:
        return "# KK网采集报告\n\n本次未找到相关帖子。\n"

    posts = sorted(posts, key=lambda x: x.get("score", 0), reverse=True)

    high = [p for p in posts if p.get("score", 0) >= 15]
    med = [p for p in posts if 8 <= p.get("score", 0) < 15]
    low = [p for p in posts if 3 <= p.get("score", 0) < 8]

    now = datetime.now()
    report = f"""# KK网康养信息采集报告

> 📅 采集时间: {now.strftime('%Y-%m-%d %H:%M')}
> 📊 总计: **{len(posts)}** 条 | 🔴 高价值: {len(high)} | 🟡 关注: {len(med)} | 🟢 背景: {len(low)}

---

## 🔴 高价值线索（≥15分）

"""
    if high:
        for i, p in enumerate(high, 1):
            report += f"### {i}. [{p['score']}分] {p['title']}\n\n"
            report += f"| 属性 | 值 |\n"
            report += f"|------|----|\n"
            report += f"| 链接 | {p['url']} |\n"
            report += f"| 分类 | {classify_post(p)} |\n"
            report += f"| 匹配 | {', '.join(p.get('matched_kw', []))} |\n"
            report += f"| 来源 | {p.get('source', '未知')} |\n"
            report += f"| 状态 | ⬜ 待跟进 |\n\n"
    else:
        report += "> 本轮无高价值线索\n\n"

    if med:
        report += "## 🟡 值得关注（8-14分）\n\n"
        report += "| # | 评分 | 标题 | 分类 | 链接 |\n"
        report += "|---|------|------|------|------|\n"
        for i, p in enumerate(med, 1):
            title = p['title'][:40]
            report += f"| {i} | {p['score']} | {title} | {classify_post(p)} | [链接]({p['url']}) |\n"

    if low:
        report += "\n## 🟢 背景信息（3-7分）\n\n"
        for p in low[:10]:
            report += f"- [{p['score']}分] [{p['title'][:60]}]({p['url']}) — {', '.join(p.get('matched_kw', [])[:3])}\n"

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {output_path}")

    return report


def save_leads_json(posts, output_path):
    """将线索保存为 JSON 格式，可追加"""
    existing = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    existing_tids = {p.get("tid") for p in existing if p.get("tid")}

    new_count = 0
    for p in posts:
        tid = p.get("tid") or extract_tid(p.get("url", ""))
        if tid and tid not in existing_tids:
            p["tid"] = tid
            p["found_at"] = datetime.now().strftime("%Y-%m-%d")
            p["status"] = "待跟进"
            p["notes"] = ""
            existing.append(p)
            existing_tids.add(tid)
            new_count += 1

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"📦 线索库: {len(existing)} 条 (新增 {new_count})")
    return existing


# ============================================================
# CLI 入口
# ============================================================

def cmd_queries():
    """打印搜索查询 URL"""
    print("KK网信息采集 - 搜索查询URL\n")
    print("在浏览器中打开以下链接，保存结果页HTML到 temp/ 目录：\n")
    for name, query in SEARCH_QUERIES.items():
        encoded = urllib.parse.quote(query)
        print(f"【{name}】")
        print(f"  https://www.google.com/search?q={encoded}")
        print()


def cmd_parse(filepath):
    """解析本地 HTML 文件，提取帖子"""
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        print("提示: 先在浏览器中搜索并保存HTML到此路径")
        return

    print(f"📄 解析文件: {filepath}")
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    posts = extract_posts_from_html(html)
    print(f"   提取到 {len(posts)} 个 KK 网链接")

    if not posts:
        print("   未找到 KK 网链接，请确认搜索结果的HTML完整性")
        return

    # 评分和分类
    posts = [score_post(p) for p in posts]
    posts = [p for p in posts if p["score"] >= 3]  # 过滤无关内容

    print(f"   过滤后: {len(posts)} 条相关帖子")

    if posts:
        # 输出到 girlfrend/work/kk_data/
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        report_path = OUTPUT_DIR / f"{date_str}_report.md"
        leads_path = OUTPUT_DIR / "leads.json"

        generate_markdown_report(posts, str(report_path))
        save_leads_json(posts, str(leads_path))

        # 简要摘要
        print(f"\n{'='*50}")
        high = [p for p in posts if p.get("score", 0) >= 10]
        if high:
            print(f"🔴 高价值线索 ({len(high)} 条):")
            for p in high[:5]:
                print(f"   [{p['score']}分] {p['title'][:60]}")
                print(f"   → {p['url']}")
        else:
            print("本轮无高价值线索")


def cmd_nursing(area_id="0"):
    """抓取淘淘居保姆/护工分类"""
    area_names = {"0": "全部", "2": "新罗区", "3": "永定", "4": "上杭",
                  "5": "长汀", "6": "武平", "7": "连城", "8": "漳平"}
    area_name = area_names.get(area_id, area_id)

    url = f"http://www.taotaoju.vip/category-catid-232.html"
    if area_id != "0":
        url = f"http://www.taotaoju.vip/category-catid-232-areaid-{area_id}.html"

    print(f"📡 抓取淘淘居护工分类 [{area_name}]")
    print(f"   URL: {url}")

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; KKBot/1.0)"}
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("gbk", errors="replace")

        # 提取信息条目
        items = re.findall(r'href="(/info-\d+\.html)"[^>]*>(.*?)</a>', html)
        print(f"   找到 {len(items)} 条信息\n")

        for link, title in items[:10]:
            title = re.sub(r"<[^>]+>", "", title).strip()
            if title:
                print(f"   {title[:80]}")
                print(f"   http://www.taotaoju.vip{link}")
                print()
    except Exception as e:
        print(f"   ❌ 抓取失败: {e}")
        print("   提示: 淘淘居可能也有反爬，建议用浏览器访问后保存HTML再解析")


def print_usage():
    print(__doc__)
    print("可用命令:")
    print("  queries            - 显示所有搜索查询URL")
    print("  parse <文件路径>    - 从本地HTML解析KK网帖子")
    print("  nursing [区域ID]   - 抓取淘淘居护工分类 (区域: 0=全部 2=新罗区)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "queries":
        cmd_queries()
    elif cmd == "parse":
        filepath = sys.argv[2] if len(sys.argv) > 2 else str(TEMP_DIR / "kk_search.html")
        cmd_parse(filepath)
    elif cmd == "nursing":
        area = sys.argv[2] if len(sys.argv) > 2 else "0"
        cmd_nursing(area)
    else:
        print(f"未知命令: {cmd}")
        print_usage()
