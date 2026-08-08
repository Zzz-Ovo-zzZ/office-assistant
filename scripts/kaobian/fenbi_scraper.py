#!/usr/bin/env python3
"""
粉笔职位库历史岗位爬虫
━━━━━━━━━━━━━━━━━━━━━━
从粉笔职位库 (fenbi.com) 抓取历年龙岩地区艺术设计类岗位数据，
生成结构化汇总，补充搜索引擎无法覆盖的底层职位数据。

数据源：粉笔职位库(fenbi.com/page/positions)
数据范围：福建省考 + 福建事业单位联考 + 教师招聘

使用方法：
    python fenbi_scraper.py                  # 搜索艺术设计类岗位
    python fenbi_scraper.py --keyword 视觉传达  # 按关键词搜索
    python fenbi_scraper.py --all-years      # 遍历所有年份
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 粉笔职位库 API 端点
FENBI_POSITIONS_URL = "https://www.fenbi.com/page/positions"

# 考试类型
EXAM_TYPES = {
    "省考": {"id": 1, "name": "福建省考"},
    "事业单位": {"id": 16, "name": "福建事业单位联考"},
}

# 龙岩各区县 region_id（粉笔编码）
LONGYAN_REGIONS = {
    240: "龙岩市",
    241: "新罗区",
    242: "永定区",
    243: "长汀县",
    244: "上杭县",
    245: "武平县",
    246: "连城县",
    247: "漳平市",
}

# 搜索关键词
KEYWORDS = [
    "艺术设计", "视觉传达", "设计学", "美术", "新媒体",
    "宣传", "融媒体", "文化", "企划", "品牌",
    "艺术设计类", "设计学类",
]

# ============================================================
# 网页抓取
# ============================================================

def fetch_url(url: str, timeout: int = 20) -> Optional[str]:
    """抓取网页"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ⚠️ 抓取失败: {e}")
        return None


def search_positions(exam_type: str, year: int, region_id: int = 240, page: int = 1) -> Optional[str]:
    """搜索粉笔职位库"""
    exam_id = EXAM_TYPES[exam_type]["id"]

    # 粉笔职位搜索URL
    url = f"{FENBI_POSITIONS_URL}/{exam_id}"
    params = {
        "region": str(region_id),
        "page": str(page),
    }
    full_url = f"{url}?{urllib.parse.urlencode(params)}"

    print(f"  请求: {full_url[:100]}...")
    return fetch_url(full_url)


def parse_position_list(html: str) -> list[dict]:
    """从页面HTML中提取岗位列表"""
    positions = []

    # 尝试多种模式匹配岗位信息
    # 模式1：表格行
    row_pattern = re.compile(
        r'<tr[^>]*>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>(.*?)</td>',
        re.DOTALL | re.IGNORECASE
    )

    # 模式2：卡片式布局（粉笔新版）
    card_pattern = re.compile(
        r'class="[^"]*position-item[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        re.DOTALL | re.IGNORECASE
    )

    # 先尝试从HTML中提取结构化数据
    # 粉笔页面通常有一个 __NEXT_DATA__ 或类似的 JSON 块
    json_pattern = re.compile(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*type="application/json"[^>]*>(.*?)</script>',
        re.DOTALL
    )
    json_match = json_pattern.search(html)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            # 尝试从 Next.js 数据结构中提取
            props = data.get("props", {}).get("pageProps", {})
            if "positions" in props:
                return props["positions"]
            if "list" in props:
                return props["list"]
        except json.JSONDecodeError:
            pass

    # 模式3：从链接中提取岗位名称 + URL
    link_pattern = re.compile(
        r'<a\s[^>]*href="(/page/positions/\d+/\d+)[^"]*"[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )

    for match in link_pattern.finditer(html):
        href = match.group(1)
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()

        if len(text) > 3 and len(text) < 200:
            positions.append({
                "title": text,
                "url": f"https://www.fenbi.com{href}",
            })

    return positions


def get_position_detail(url: str) -> Optional[dict]:
    """获取单个岗位详情"""
    html = fetch_url(url)
    if not html:
        return None

    detail = {"url": url}

    # 提取岗位名称
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    if title_match:
        detail["title"] = title_match.group(1).strip()

    # 提取关键字段
    fields = {
        "招录人数": r'(?:招录人数|招聘人数|招考人数)[：:]\s*(\d+)',
        "专业要求": r'(?:专业|专业要求)[：:]\s*(.*?)(?:<|。|；)',
        "学历要求": r'(?:学历|学历要求)[：:]\s*(.*?)(?:<|。|；)',
        "政治面貌": r'(?:政治面貌)[：:]\s*(.*?)(?:<|。|；)',
        "工作地点": r'(?:工作地点|地区)[：:]\s*(.*?)(?:<|。|；)',
    }

    for key, pattern in fields.items():
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            detail[key] = re.sub(r'<[^>]+>', '', match.group(1)).strip()

    return detail


# ============================================================
# 匹配逻辑
# ============================================================

def is_match_for_zengzhou(title: str, detail: dict = None) -> tuple[bool, str]:
    """判断岗位是否匹配曾周的条件"""
    text = title
    if detail:
        for v in detail.values():
            if isinstance(v, str):
                text += " " + v

    # 排除关键词
    exclude = ["研究生", "硕士", "博士", "医学", "护理", "临床",
               "执业医师", "法律职业资格", "注册会计师"]
    for kw in exclude:
        if kw in text:
            return False, f"排除: {kw}"

    # 匹配关键词
    priority_matches = []
    for kw in ["艺术设计", "视觉传达", "设计学类", "艺术设计类",
               "美术", "设计", "新媒体", "宣传", "融媒体", "企划"]:
        if kw in text:
            priority_matches.append(kw)

    if priority_matches:
        return True, f"匹配: {', '.join(priority_matches[:3])}"

    # 不限专业也算
    if "不限" in title or "专业不限" in text:
        return True, "匹配: 不限专业"

    return False, "不匹配"


# ============================================================
# 批量搜索
# ============================================================

def crawl_all(keyword: str = None):
    """遍历搜索历年岗位"""
    print("🔍 粉笔职位库 — 历史岗位搜索")
    print("=" * 60)
    print(f"   目标区域: 龙岩市（含各区县）")
    print(f"   目标专业: 艺术设计类 / 视觉传达设计")
    print(f"   时间跨度: 2022-2026")
    print()

    all_matches = []

    for exam_name, exam_info in EXAM_TYPES.items():
        for year in range(2022, 2027):
            print(f"\n📡 {exam_name} — {year}年")

            for region_id, region_name in LONGYAN_REGIONS.items():
                html = search_positions(exam_name, year, region_id)
                if not html:
                    print(f"   {region_name}: 无数据")
                    continue

                positions = parse_position_list(html)
                print(f"   {region_name}: 找到 {len(positions)} 个岗位")

                for pos in positions:
                    matched, reason = is_match_for_zengzhou(pos.get("title", ""))
                    if keyword and keyword not in pos.get("title", ""):
                        matched = False

                    if matched:
                        pos["exam"] = exam_name
                        pos["year"] = year
                        pos["region"] = region_name
                        pos["match_reason"] = reason
                        all_matches.append(pos)
                        print(f"     ✅ {pos['title'][:60]} — {reason}")

                time.sleep(0.3)  # 礼貌延迟

    # 保存结果
    result = {
        "search_time": datetime.now().isoformat(),
        "total_matches": len(all_matches),
        "positions": all_matches,
    }

    save_path = DATA_DIR / f"fenbi_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"📊 搜索完成: 共 {len(all_matches)} 个匹配岗位")
    print(f"💾 保存至: {save_path}")

    return result


def crawl_single_page(url: str):
    """抓取单个粉笔职位页面"""
    print(f"🔍 分析: {url}")
    html = fetch_url(url)
    if not html:
        print("  ❌ 无法访问")
        return []

    positions = parse_position_list(html)
    print(f"  解析到 {len(positions)} 个岗位")

    matches = []
    for pos in positions:
        matched, reason = is_match_for_zengzhou(pos.get("title", ""))
        if matched:
            matches.append(pos)
            print(f"  ✅ {pos['title'][:60]} — {reason}")

    return matches


def generate_report(results: list[dict]):
    """生成搜索报告"""
    if not results:
        print("\n📭 无结果，不生成报告")
        return

    report_path = OUTPUT_DIR / f"粉笔岗位搜索_{datetime.now().strftime('%Y%m%d')}.md"

    # 按年份分组
    by_year = {}
    for r in results:
        y = r.get("year", "未知")
        if y not in by_year:
            by_year[y] = []
        by_year[y].append(r)

    lines = [
        f"# 🔍 粉笔职位库搜索报告",
        f"",
        f"> 搜索时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 匹配岗位：{len(results)} 个",
        f"> 目标专业：艺术设计类 / 视觉传达设计",
        f"",
        f"---",
        f"",
    ]

    for year in sorted(by_year.keys(), reverse=True):
        lines.append(f"## {year}年（{len(by_year[year])}个）")
        lines.append("")
        lines.append("| 考试 | 区域 | 岗位名称 | 匹配原因 |")
        lines.append("|------|------|---------|---------|")
        for r in by_year[year]:
            exam = r.get("exam", "?")
            region = r.get("region", "?")
            title = r.get("title", "?")[:40]
            reason = r.get("match_reason", "")
            lines.append(f"| {exam} | {region} | [{title}]({r.get('url', '')}) | {reason} |")
        lines.append("")

    lines += [
        f"---",
        f"*数据来源：粉笔职位库 (fenbi.com)*",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"📊 报告: {report_path}")
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

    keyword = None
    if "--keyword" in args:
        try:
            idx = args.index("--keyword")
            keyword = args[idx + 1]
        except IndexError:
            pass

    # 快速模式：直接搜索几个已知URL
    if "--quick" in args:
        print("⚡ 快速模式：搜索已知粉笔页面...\n")
        known_urls = [
            # 2026省考龙岩
            "https://fenbi.com/page/positions/1/487206?region=240",
            # 2026事业单位龙岩
            "https://www.fenbi.com/page/positions/16/520363",
        ]

        all_results = []
        for url in known_urls:
            matches = crawl_single_page(url)
            all_results.extend(matches)
            time.sleep(0.5)

        if all_results:
            generate_report(all_results)
        return

    # 默认模式：全量搜索
    result = crawl_all(keyword=keyword)
    if result["positions"]:
        generate_report(result["positions"])


if __name__ == "__main__":
    main()
