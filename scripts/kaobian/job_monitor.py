#!/usr/bin/env python3
"""
龙岩考编岗位监控工具
━━━━━━━━━━━━━━━━━━━━
监控龙岩市人社局、人才库、福建就业网等平台的招考公告，
匹配曾周（视觉传达设计）相关岗位，发现新岗位时输出提醒。

使用方法：
    python job_monitor.py                  # 检查所有源，输出新岗位
    python job_monitor.py --init           # 初始化，记录当前岗位为已读（不报警）
    python job_monitor.py --list           # 列出已记录的岗位
    python job_monitor.py --report         # 生成岗位报告（markdown）
    python job_monitor.py --add-url URL    # 手动添加监控URL
"""

import json
import os
import sys
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ============================================================
# 配置
# ============================================================

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent.parent

# 数据存储路径
DATA_DIR = ROOT / "data" / "kaobian"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JOBS_FILE = DATA_DIR / "tracked_jobs.json"
OUTPUT_DIR = ROOT / "output" / "kaobian" / "zengzhou"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# ============================================================
# 监控源配置
# ============================================================

MONITOR_SOURCES = [
    {
        "name": "龙岩市人社局-事业单位招聘",
        "url": "http://rsj.longyan.gov.cn/zwgk/gsgg/",
        "type": "html",
        "list_selector": "ul.list-box li a",  # CSS选择器
        "title_attr": "text",
        "url_attr": "href",
    },
    {
        "name": "龙岩人才库-国企招聘",
        "url": "https://er.vlongyan.cn",
        "type": "html",
        "list_selector": "a.recruitment-item",
        "title_attr": "text",
        "url_attr": "href",
    },
    {
        "name": "福建就业网-事业单位",
        "url": "https://www.fj99.org.cn/bys",
        "type": "html",
        "list_selector": "a[href*='zhaokao']",
        "title_attr": "text",
        "url_attr": "href",
    },
    {
        "name": "福建省公务员考试录用网",
        "url": "http://gwykl.fujian.gov.cn",
        "type": "html",
        "list_selector": "a[href*='announcement'], a[href*='notice']",
        "title_attr": "text",
        "url_attr": "href",
    },
]

# 用户自定义URL（通过 --add-url 添加）
CUSTOM_URLS: list[dict] = []

# ============================================================
# 关键词匹配（针对曾周的专业和偏好）
# ============================================================

MATCH_KEYWORDS = {
    "优先匹配": ["视觉传达", "视觉传达设计", "艺术设计", "设计学", "美术",
                 "融媒体", "新媒体", "宣传", "企划", "品牌"],
    "可考虑": ["艺术设计类", "哲学文学历史学大类", "不限专业", "三不限",
               "综合管理", "文化", "旅游", "博物馆", "图书馆", "文化馆",
               "教师", "美术教师"],
    "排除": ["医学", "护理", "临床", "会计", "审计", "法律职业资格",
             "执业医师", "注册", "工程", "电气", "机械(非设计)"],
}

# ============================================================
# 数据模型
# ============================================================

def load_tracked_jobs() -> dict:
    """加载已记录岗位"""
    if JOBS_FILE.exists():
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": {}, "last_check": None}


def save_tracked_jobs(data: dict):
    """保存岗位数据"""
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def job_hash(title: str, url: str) -> str:
    """生成岗位唯一标识"""
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]


def match_job(title: str) -> tuple[str, int]:
    """
    判断岗位是否匹配曾周的条件
    返回: (级别, 分数) — 分数越高越匹配
    """
    title_lower = title.lower()
    score = 0

    # 排除关键词
    for kw in MATCH_KEYWORDS["排除"]:
        if kw in title:
            return ("不匹配", -1)

    # 优先匹配
    for kw in MATCH_KEYWORDS["优先匹配"]:
        if kw in title_lower:
            score += 10
            break  # 一个优先匹配就够了

    # 可考虑
    for kw in MATCH_KEYWORDS["可考虑"]:
        if kw in title_lower:
            score += 3

    # 判断级别
    if score >= 10:
        level = "🔥 高度匹配"
    elif score >= 3:
        level = "🟡 可考虑"
    elif score > 0:
        level = "⚪ 勉强相关"
    else:
        level = "—— 不相关"

    return (level, score)


# ============================================================
# 网页抓取
# ============================================================

def fetch_html(url: str, timeout: int = 15) -> Optional[str]:
    """抓取网页HTML"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 尝试检测编码
            content = resp.read()
            # 简单处理：先尝试UTF-8，失败则尝试GBK
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return content.decode("gbk")
                except UnicodeDecodeError:
                    return content.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ⚠️ 抓取失败 [{url}]: {e}")
        return None


def parse_html_links(html: str, selector: str, title_attr: str, url_attr: str, base_url: str) -> list[dict]:
    """从HTML中提取链接列表（简易解析，不依赖BeautifulSoup）"""
    import re

    results = []
    # 简易HTML链接提取：找所有<a>标签
    link_pattern = re.compile(
        r'<a\s[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )

    for match in link_pattern.finditer(html):
        href = match.group(1)
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()

        if not text or len(text) < 4:
            continue

        # 补全URL
        if href.startswith("/"):
            from urllib.parse import urljoin
            href = urljoin(base_url, href)
        elif not href.startswith("http"):
            href = urljoin(base_url, href) if base_url else base_url.rstrip("/") + "/" + href.lstrip("/")

        results.append({"title": text, "url": href})

    return results


# ============================================================
# 检查逻辑
# ============================================================

def check_source(source: dict) -> list[dict]:
    """检查单个监控源，返回新发现的匹配岗位"""
    print(f"\n📡 检查: {source['name']}")
    print(f"   URL: {source['url']}")

    html = fetch_html(source["url"])
    if not html:
        return []

    links = parse_html_links(
        html,
        source.get("list_selector", "a"),
        source.get("title_attr", "text"),
        source.get("url_attr", "href"),
        source["url"]
    )

    print(f"   找到 {len(links)} 个链接")

    tracked = load_tracked_jobs()
    new_matches = []

    for link in links[:50]:  # 每个源最多检查50条
        jhash = job_hash(link["title"], link["url"])
        level, score = match_job(link["title"])

        if score < 0:
            continue  # 排除

        if jhash not in tracked["jobs"]:
            tracked["jobs"][jhash] = {
                "title": link["title"],
                "url": link["url"],
                "source": source["name"],
                "level": level,
                "score": score,
                "first_seen": datetime.now().isoformat(),
                "status": "new",
            }
            new_matches.append(tracked["jobs"][jhash])
            print(f"   🆕 {level} | {link['title'][:60]}")

    tracked["last_check"] = datetime.now().isoformat()
    save_tracked_jobs(tracked)

    if not new_matches:
        print(f"   ✅ 无新增匹配岗位")

    return new_matches


def check_all(init_mode: bool = False) -> list[dict]:
    """检查所有监控源"""
    all_new = []

    if init_mode:
        print("🔧 初始化模式：记录当前岗位，不触发提醒\n")

    for source in MONITOR_SOURCES + CUSTOM_URLS:
        try:
            new = check_source(source)
            all_new.extend(new)
        except Exception as e:
            print(f"  ❌ 检查失败 [{source['name']}]: {e}")

    return all_new


# ============================================================
# 报告生成
# ============================================================

def generate_report():
    """生成岗位监控报告"""
    tracked = load_tracked_jobs()
    jobs = list(tracked["jobs"].values())

    # 按分数排序
    jobs.sort(key=lambda j: j.get("score", 0), reverse=True)

    high = [j for j in jobs if j.get("level") == "🔥 高度匹配"]
    consider = [j for j in jobs if j.get("level") == "🟡 可考虑"]

    report_path = OUTPUT_DIR / f"岗位监控报告_{datetime.now().strftime('%Y%m%d')}.md"

    lines = [
        f"# 龙岩考编岗位监控报告",
        f"",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 监控对象：曾周（视觉传达设计 / 新罗区优先）",
        f"> 累计追踪岗位：{len(jobs)} 个",
        f"",
        f"---",
        f"",
        f"## 🔥 高度匹配岗位 ({len(high)})",
        f"",
    ]

    if high:
        lines.append("| 岗位 | 来源 | 发现时间 |")
        lines.append("|------|------|----------|")
        for j in high:
            time_str = j.get("first_seen", "")[:10]
            lines.append(f"| [{j['title'][:40]}]({j['url']}) | {j['source']} | {time_str} |")
    else:
        lines.append("> 暂无高度匹配岗位，请持续关注。")
    lines.append("")

    lines += [
        f"## 🟡 可考虑岗位 ({len(consider)})",
        f"",
    ]
    if consider:
        lines.append("| 岗位 | 来源 | 发现时间 |")
        lines.append("|------|------|----------|")
        for j in consider:
            time_str = j.get("first_seen", "")[:10]
            lines.append(f"| [{j['title'][:40]}]({j['url']}) | {j['source']} | {time_str} |")
    else:
        lines.append("> 暂无")
    lines.append("")

    lines += [
        f"---",
        f"",
        f"## 监控源状态",
        f"",
        f"| 来源 | 上次检查 |",
        f"|------|----------|",
    ]
    last = tracked.get("last_check", "从未")[:19] if tracked.get("last_check") else "从未"
    for s in MONITOR_SOURCES:
        lines.append(f"| {s['name']} | {last} |")
    lines.append("")

    lines += [
        f"## 自定义URL监控",
        f"",
    ]
    if CUSTOM_URLS:
        for u in CUSTOM_URLS:
            lines.append(f"- [{u['name']}]({u['url']})")
    else:
        lines.append("> 暂未添加自定义URL，使用 `--add-url` 添加")
    lines.append("")

    lines += [
        f"---",
        f"",
        f"*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n📊 报告已生成: {report_path}")
    print(f"   高度匹配: {len(high)} | 可考虑: {len(consider)} | 总计: {len(jobs)}")

    return report_path


# ============================================================
# CLI
# ============================================================

def print_help():
    print(__doc__)
    print("监控源列表:")
    for i, s in enumerate(MONITOR_SOURCES, 1):
        print(f"  {i}. {s['name']}")
        print(f"     {s['url']}")
    print()


def main():
    args = sys.argv[1:]

    if not args:
        print("🔍 龙岩考编岗位监控 — 开始检查...")
        print(f"   检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   监控源: {len(MONITOR_SOURCES)} 个官方 + {len(CUSTOM_URLS)} 个自定义")
        print("=" * 60)

        new_jobs = check_all(init_mode=False)

        print("\n" + "=" * 60)
        if new_jobs:
            print(f"\n🎯 发现 {len(new_jobs)} 个新匹配岗位！")
            for j in new_jobs:
                print(f"   {j['level']} | {j['title']}")
                print(f"   → {j['url']}")
        else:
            print("\n✅ 本次检查无新增匹配岗位")

        # 同时生成报告
        generate_report()
        return

    if "--help" in args or "-h" in args:
        print_help()
        return

    if "--init" in args:
        print("🔧 初始化：将当前所有岗位标记为已读（不触发提醒）...")
        check_all(init_mode=True)
        print("\n✅ 初始化完成")
        return

    if "--list" in args:
        tracked = load_tracked_jobs()
        jobs = list(tracked["jobs"].values())
        jobs.sort(key=lambda j: j.get("score", 0), reverse=True)

        print(f"\n📋 已追踪岗位 ({len(jobs)} 个)")
        print("-" * 60)
        for j in jobs:
            icon = {"🔥 高度匹配": "🔴", "🟡 可考虑": "🟡", "⚪ 勉强相关": "⚪"}.get(j.get("level", ""), "⚪")
            status = "🆕" if j.get("status") == "new" else "  "
            print(f"{icon} {status} [{j['source'][:8]}] {j['title'][:50]}")
        return

    if "--report" in args:
        generate_report()
        return

    if "--add-url" in args:
        try:
            idx = args.index("--add-url")
            url = args[idx + 1]
            name = args[idx + 2] if len(args) > idx + 2 else "自定义来源"
            CUSTOM_URLS.append({"name": name, "url": url, "type": "html",
                                "list_selector": "a", "title_attr": "text", "url_attr": "href"})
            print(f"✅ 已添加自定义监控: {name} -> {url}")
        except IndexError:
            print("❌ 用法: --add-url <URL> [名称]")
        return

    print(f"❌ 未知参数: {' '.join(args)}")
    print_help()


if __name__ == "__main__":
    main()
