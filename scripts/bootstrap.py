#!/usr/bin/env python3
"""一键初始化 / 自检 —— 换电脑后先跑这一条。

用法:
    python scripts/bootstrap.py              # 自检并创建运行时目录
    python scripts/bootstrap.py --install     # 同时安装 requirements.txt 依赖
    python scripts/bootstrap.py --init-config # 由 config.example.json 生成本机 config.local.json
    python scripts/bootstrap.py --init-env    # 由 .env.example 生成室内设计所需的 .env

设计目标：任何一台 Windows 电脑 clone 本仓库后，跑一次本脚本即可与原作者环境一致。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.console import force_utf8  # noqa: E402

force_utf8()

# (import 名, pip 名, 用途)
CORE_DEPS = [
    ("openpyxl", "openpyxl", "Excel 读写 / 资产对账"),
    ("markdown", "markdown", "md → html"),
    ("lunar_python", "lunar-python", "婚嫁择日（寿星天文历）"),
    ("cnlunar", "cnlunar", "神煞双源对比"),
    ("requests", "requests", "岗位监控 / 线索采集 / 地理编码"),
]
OPT_DEPS = [
    ("PyQt6", "PyQt6", "办公记事本"),
    ("win32com", "pywin32", "WPS/Excel COM 桥接"),
    ("pystray", "pystray", "番茄钟系统托盘"),
    ("PIL", "Pillow", "图标与托盘绘制"),
]

OK, BAD, WARN = "[OK]", "[!!]", "[??]"


def has_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def check_python() -> bool:
    v = sys.version_info
    good = v >= (3, 10)
    print(f"{OK if good else BAD} Python {v.major}.{v.minor}.{v.micro}"
          f"{'' if good else '（需要 3.10+，推荐 3.12）'}")
    return good


def report_deps() -> bool:
    print("\n-- 依赖检查 --")
    missing_core = []
    for mod, pip_name, why in CORE_DEPS:
        ok = has_module(mod)
        print(f"{OK if ok else BAD} {pip_name:<14} {why}")
        if not ok:
            missing_core.append(pip_name)
    for mod, pip_name, why in OPT_DEPS:
        ok = has_module(mod)
        print(f"{OK if ok else WARN} {pip_name:<14} {why}（可选）")

    if missing_core:
        print(f"\n缺少核心依赖，安装：python -m pip install {' '.join(missing_core)}")
        print("或一次性安装：python -m pip install -r requirements.txt")
    return not missing_core


def init_config() -> None:
    src = ROOT / "config.example.json"
    dst = ROOT / "config.local.json"
    if dst.exists():
        print(f"{OK} config.local.json 已存在，跳过")
        return
    shutil.copyfile(src, dst)
    print(f"{OK} 已生成 config.local.json —— 请按本机情况修改 synology_root / amap_key")


def init_env_files() -> None:
    pairs = [
        (ROOT / ".claude" / "skills" / "interior-design" / ".env.example",
         ROOT / ".claude" / "skills" / "interior-design" / ".env", "室内设计生图 Key"),
    ]
    for src, dst, why in pairs:
        if not src.exists():
            continue
        if dst.exists():
            print(f"{OK} {dst.relative_to(ROOT)} 已存在，跳过")
        else:
            shutil.copyfile(src, dst)
            print(f"{OK} 已生成 {dst.relative_to(ROOT)} —— 请填写{why}")


def make_dirs() -> None:
    from scripts.project_config import ensure_runtime_dirs
    dirs = ensure_runtime_dirs()
    print(f"{OK} 运行时目录 {len(dirs)} 个（temp / ledger / assessments / kaobian / kk_data）")


def smoke_test() -> bool:
    print("\n-- 冒烟测试 --")
    try:
        from scripts.fitness import quick_report
        r = quick_report(gender="男", age=30, height_cm=176, weight_kg=82, goal="cut")
        print(f"{OK} 健身引擎：BMI {r['bmi'].bmi} / TDEE {r['tdee']} kcal / 蛋白 {r['macros']['protein_g']}g")
    except Exception as exc:
        print(f"{BAD} 健身引擎异常：{exc}")
        return False

    try:
        from scripts.finance import WealthEngine
        years = WealthEngine.rule_of_72(10)
        print(f"{OK} 理财引擎：72 法则（10%）→ 约 {getattr(years, 'years', years)} 年翻倍")
    except Exception as exc:
        print(f"{BAD} 理财引擎异常：{exc}")
        return False

    try:
        from scripts.project_config import CONFIG, PROJECT_ROOT
        print(f"{OK} 配置加载：synology_root = {CONFIG['synology_root']} | 项目根 = {PROJECT_ROOT.name}")
    except Exception as exc:
        print(f"{BAD} 配置加载异常：{exc}")
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="办公助手 · 环境初始化与自检")
    ap.add_argument("--install", action="store_true", help="安装 requirements.txt")
    ap.add_argument("--init-config", action="store_true", help="生成 config.local.json")
    ap.add_argument("--init-env", action="store_true", help="生成室内设计 .env")
    args = ap.parse_args()

    print("=" * 56)
    print("办公助手 · 环境初始化")
    print("=" * 56)

    py_ok = check_python()

    if args.install:
        print("\n-- 安装依赖 --")
        subprocess.call([sys.executable, "-m", "pip", "install", "-r",
                         str(ROOT / "requirements.txt")])

    if args.init_config:
        print()
        init_config()
    if args.init_env:
        init_env_files()

    deps_ok = report_deps()
    make_dirs()
    smoke_ok = smoke_test()

    print("\n" + "=" * 56)
    if py_ok and deps_ok and smoke_ok:
        print("环境就绪 ✅  可开始使用")
        print("常用入口：python scripts/bootstrap.py --init-config（首次）")
        return 0
    print("环境未就绪，请按上面的提示补齐 ⚠️")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
