#!/usr/bin/env python3
"""
考编工具一键启动器
━━━━━━━━━━━━━━━━━━━━
集中管理所有考编相关工具的入口，一键打开所需资源。

使用方法：
    python open_tools.py             # 交互式菜单
    python open_tools.py saduck      # 打开SaDuck知识库
    python open_tools.py tools       # 启动公考小工具
    python open_tools.py radar       # 打开公考雷达网页
    python open_tools.py all         # 打开所有在线资源
"""

import os
import sys
import webbrowser
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS_DIR = ROOT / "tools" / "civil-servans-tools"

# ============================================================
# 快捷入口
# ============================================================

ENTRIES = {
    "saduck": {
        "name": "SaDuck 考公考编知识库",
        "url": "https://saduck.top",
        "desc": "公基/行测/申论/常识 全科免费知识库",
        "type": "web",
    },
    "radar": {
        "name": "公考雷达",
        "url": "https://www.gongkaoleida.com",
        "desc": "岗位匹配推送，设置专业+地区自动提醒",
        "type": "web",
    },
    "fenbi": {
        "name": "粉笔题库",
        "url": "https://tiku.fenbi.com",
        "desc": "在线刷题（网页版）",
        "type": "web",
    },
    "fj_gwy": {
        "name": "福建省公务员考试录用网",
        "url": "http://gwykl.fujian.gov.cn",
        "desc": "省考公告+报名入口",
        "type": "web",
    },
    "fj_sydw": {
        "name": "福建就业网-事业单位招聘",
        "url": "https://www.fj99.org.cn/bys",
        "desc": "事业单位公告+三支一扶",
        "type": "web",
    },
    "ly_rc": {
        "name": "龙岩人才库",
        "url": "https://er.vlongyan.cn",
        "desc": "龙岩市属国企招聘",
        "type": "web",
    },
    "ly_rsj": {
        "name": "龙岩市人社局",
        "url": "http://rsj.longyan.gov.cn/zwgk/gsgg/",
        "desc": "事业单位公告官方发布",
        "type": "web",
    },
    "tools": {
        "name": "公考小工具 (civil-servans-tools)",
        "desc": "PDF排版/计时器/答题纸/OCR",
        "type": "local",
        "script": str(TOOLS_DIR / "main.py"),
    },
}


def open_web(url: str, name: str):
    """打开网页"""
    print(f"🌐 打开 {name}...")
    webbrowser.open(url)


def open_local(script: str, name: str):
    """启动本地工具"""
    print(f"🖥️ 启动 {name}...")
    if not Path(script).exists():
        print(f"   ❌ 未找到: {script}")
        print(f"   请先安装: 下载 civil-servans-tools 到 tools/ 目录")
        return

    try:
        # Windows
        if sys.platform == "win32":
            subprocess.Popen(["python", script], cwd=str(Path(script).parent))
        else:
            subprocess.Popen(["python3", script], cwd=str(Path(script).parent))
        print(f"   ✅ 已启动")
    except Exception as e:
        print(f"   ❌ 启动失败: {e}")


def show_menu():
    """交互式菜单"""
    print("\n🧰 考编工具启动器")
    print("=" * 50)

    print("\n📚 学习平台:")
    print(f"  1. {ENTRIES['saduck']['name']} — {ENTRIES['saduck']['desc']}")
    print(f"  2. {ENTRIES['fenbi']['name']} — {ENTRIES['fenbi']['desc']}")

    print(f"\n🔍 岗位信息:")
    print(f"  3. {ENTRIES['radar']['name']} — {ENTRIES['radar']['desc']}")
    print(f"  4. {ENTRIES['fj_gwy']['name']}")
    print(f"  5. {ENTRIES['fj_sydw']['name']}")
    print(f"  6. {ENTRIES['ly_rc']['name']}")
    print(f"  7. {ENTRIES['ly_rsj']['name']}")

    print(f"\n🛠️ 本地工具:")
    print(f"  8. {ENTRIES['tools']['name']}")
    print(f"     {ENTRIES['tools']['desc']}")

    print(f"\n  9. 打开全部在线资源")
    print(f"  0. 退出")
    print()

    try:
        choice = input("选择 (0-9): ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "1":
        open_web(ENTRIES["saduck"]["url"], ENRIES["saduck"]["name"])
    elif choice == "2":
        open_web(ENTRIES["fenbi"]["url"], ENRIES["fenbi"]["name"])
    elif choice == "3":
        open_web(ENTRIES["radar"]["url"], ENRIES["radar"]["name"])
    elif choice == "4":
        open_web(ENTRIES["fj_gwy"]["url"], ENRIES["fj_gwy"]["name"])
    elif choice == "5":
        open_web(ENTRIES["fj_sydw"]["url"], ENRIES["fj_sydw"]["name"])
    elif choice == "6":
        open_web(ENTRIES["ly_rc"]["url"], ENRIES["ly_rc"]["name"])
    elif choice == "7":
        open_web(ENTRIES["ly_rsj"]["url"], ENRIES["ly_rsj"]["name"])
    elif choice == "8":
        open_local(ENTRIES["tools"]["script"], ENRIES["tools"]["name"])
    elif choice == "9":
        print("\n📡 打开全部在线资源...")
        for key, entry in ENTRIES.items():
            if entry.get("type") == "web":
                open_web(entry["url"], entry["name"])
    elif choice == "0":
        return
    else:
        print("❌ 无效选择")


def main():
    args = sys.argv[1:]

    if not args:
        show_menu()
        return

    cmd = args[0].lower()

    if cmd == "all":
        print("📡 打开全部在线资源...")
        for key, entry in ENTRIES.items():
            if entry.get("type") == "web":
                open_web(entry["url"], entry["name"])
                import time
                time.sleep(0.3)  # 避免浏览器同时打开太多标签
        return

    if cmd in ENTRIES:
        entry = ENTRIES[cmd]
        if entry["type"] == "web":
            open_web(entry["url"], entry["name"])
        else:
            open_local(entry["script"], entry["name"])
        return

    if cmd == "list":
        print("\n📋 可用入口:")
        for key, entry in ENTRIES.items():
            print(f"  {key:12s} → {entry['name']}")
        return

    print(f"❌ 未知入口: {cmd}")
    print(f"   可用: {', '.join(ENTRIES.keys())}, all, list")


if __name__ == "__main__":
    main()
