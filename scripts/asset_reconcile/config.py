# -*- coding: utf-8 -*-
"""置业资产 · 财务累欠 vs 合同 对账 — 路径与参数配置

所有机器相关路径都走 ``scripts/project_config.py``（config.local.json / 环境变量），
代码里不再出现盘符，换电脑只改 config.local.json。
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.project_config import PROJECT_ROOT, path_of, require  # noqa: E402

# ── 数据源 ──────────────────────────────────────────────
# 财务累欠明细表（含 顺泰/置业龙州/龙津 三大板块的应收、实收、累欠）
BILL = str(require(path_of("bill"), "财务累欠明细表"))

# 合同整理表（「导入格式」表：合同起止时间、月租金、房号集合、备注）
CTR = str(require(path_of("contracts"), "置业合同整理表"))

# ── 中间文件（临时，随仓库走，已 gitignore）─────────────
TMP = str(PROJECT_ROOT / "temp")

# ── 输出（对账结果，放在财务累欠表同目录，方便对照） ─────
OUT_DIR = path_of("reconcile_out")
try:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
except OSError as exc:  # 数据盘未挂载 / 无权限时给出可操作提示
    raise SystemExit(f"输出目录不可写：{OUT_DIR}\n{exc}\n请检查 config.local.json 的 paths.reconcile_out")

# 结果文件名里的日期。要用当天日期就改成：datetime.date.today().strftime("%Y.%m.%d")
DATE = "2026.9.9"

OUT_EXCEL = str(OUT_DIR / f"置业_财务累欠与合同对账_{DATE}.xlsx")
OUT_MD = str(OUT_DIR / f"置业_财务累欠与合同对账_文字说明_{DATE}.md")

# ── 匹配/对账参数 ───────────────────────────────────────
# 面积匹配容差（相对误差 ≤ 此值视为同一房源）
AREA_TOL = 0.30
# 财务三大板块对应的 sheet 名（顺序影响 bill.json 行序，务必与源表一致）
BILL_SHEETS = ["顺泰", "置业、龙州", "龙津"]
