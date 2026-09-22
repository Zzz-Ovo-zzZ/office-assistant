#!/usr/bin/env python3
"""
理财助手 — 命令行工具
======================
快速访问所有理财功能。

用法:
  python cli.py compound 本金 年利率 年数 [复利次数]      # 复利终值
  python cli.py deposit  本金 年利率 年数 [mode]         # 定存(mode: once整存整取/rollover复投)
  python cli.py bond     本金 年利率 年数                 # 国债
  python cli.py compare  本金 定存利率 国债利率 年数       # 定存 vs 国债对比
  python cli.py invest   月投额 年利率 月数                # 定投
  python cli.py loan     本金 年利率 期数                  # 贷款(等额本息 vs 等额本金)
  python cli.py ledger   日期 类型 分类 金额 [备注]         # 记一笔流水
  python cli.py report                                    # 台账汇总
  python cli.py rule72   年化收益率                       # 72法则翻倍年数
  python cli.py fire     年开支 [取款率]                  # 4%法则所需资产
  python cli.py fireyears 储蓄率                          # 财务自由年限
  python cli.py score    净资产 平均年龄 年工资           # 理财指数
  python cli.py cost     金额 年化 年数                   # 机会成本
  python cli.py multiple 年数 [年化]                      # 累积投资倍数

注意: 利率一律用百分数，如 3.5 表示 3.5%。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.finance.engine import (
    FinanceEngine, DepositMode, ProductType, Product,
    compare_deposit_vs_bond,
)
from scripts.finance.loan import LoanCalculator, 房贷对比
from scripts.finance.ledger import Ledger
from scripts.finance.wealth import WealthEngine


ARGS = sys.argv[2:]


def _f(i, default=None):
    """取第 i 个参数转 float，缺失用 default，否则报错退出"""
    try:
        return float(ARGS[i])
    except (IndexError, ValueError):
        if default is not None:
            return default
        print(f"❌ 参数错误：第 {i + 1} 个参数应为数字")
        sys.exit(1)


def _i(i, default=None):
    """取第 i 个参数转 int"""
    try:
        return int(float(ARGS[i]))
    except (IndexError, ValueError):
        if default is not None:
            return default
        print(f"❌ 参数错误：第 {i + 1} 个参数应为整数")
        sys.exit(1)


def _s(i, default=""):
    """取第 i 个参数（字符串）"""
    try:
        return ARGS[i]
    except IndexError:
        return default


# ---- 命令实现 ----

def cmd_compound():
    """复利终值"""
    p = _f(0); r = _f(1); y = _f(2); n = _i(3, 1)
    print(FinanceEngine.compound_fv(p, r, y, n).summary())


def cmd_deposit():
    """整存整取定存"""
    p = _f(0); r = _f(1); y = _f(2)
    mode_str = _s(3, "once").lower()
    mode = DepositMode.ROLLOVER if mode_str in ("rollover", "复投", "复利") else DepositMode.ONCE
    print(FinanceEngine.fixed_deposit(p, r, y, mode).summary())


def cmd_bond():
    """国债"""
    p = _f(0); r = _f(1); y = _f(2)
    print(FinanceEngine.treasury_bond(p, r, y).summary())


def cmd_compare():
    """定存 vs 国债对比"""
    p = _f(0, 100000); dr = _f(1, 1.9); br = _f(2, 2.2); y = _f(3, 3)
    rollover = _s(4, "").lower() in ("复投", "rollover", "复利", "1", "yes", "true")
    print(compare_deposit_vs_bond(p, dr, br, y, 复投=rollover).summary())


def cmd_invest():
    """定投"""
    a = _f(0); r = _f(1); m = _i(2)
    print(FinanceEngine.regular_invest(a, r, m).summary())


def cmd_loan():
    """贷款（等额本息 vs 等额本金）"""
    p = _f(0); r = _f(1); n = _i(2)
    房贷对比(p, r, n)


def cmd_ledger():
    """记一笔流水"""
    date = _s(0); typ = _s(1); cat = _s(2); amt = _f(3); note = _s(4, "")
    if not date or not typ or not cat:
        print("用法: ledger 日期 类型 分类 金额 [备注]")
        print("示例: ledger 2026-09-22 收入 工资 15000 9月工资")
        sys.exit(1)
    Ledger().add_entry(date, typ, cat, amt, note)
    print(f"✅ 已记一笔: {date} {typ} {cat} {amt} 元 {note}")


def cmd_report():
    """台账汇总"""
    Ledger().report()


def cmd_rule72():
    """72法则：翻倍年数"""
    r = _f(0)
    print(f"年化 {r}% → 约 {WealthEngine.rule_of_72(r)} 年翻倍（精确 {WealthEngine.rule_of_72_exact(r)} 年）")


def cmd_fire():
    """4%法则：财务自由所需资产"""
    expense = _f(0); rate = _f(1, 4.0)
    print(WealthEngine.fire_assets(expense, rate).summary())


def cmd_fireyears():
    """财务自由年限（按储蓄率）"""
    sr = _f(0)
    print(f"储蓄率 {sr}%（实际收益率 5%）→ 约 {WealthEngine.fire_years_to_retire(sr)} 年财务自由")


def cmd_score():
    """理财指数评估"""
    net = _f(0); age = _f(1); salary = _f(2)
    print(WealthEngine.wealth_score(net, age, salary).summary())


def cmd_cost():
    """机会成本"""
    amt = _f(0); r = _f(1); y = _f(2)
    print(f"现在花 {amt:,.2f} 元（年化 {r}%，{y:g} 年）的机会成本 = {WealthEngine.opportunity_cost(amt, r, y):,.2f} 元")


def cmd_multiple():
    """累积投资倍数"""
    y = _f(0); r = _f(1, 10.0)
    print(f"每年初投 1 元，年化 {r}%，{y:g} 年 → 累积倍数 P = {WealthEngine.invest_multiple(y, r)}")


COMMANDS = {
    "compound": cmd_compound,
    "deposit": cmd_deposit,
    "bond": cmd_bond,
    "compare": cmd_compare,
    "invest": cmd_invest,
    "loan": cmd_loan,
    "ledger": cmd_ledger,
    "report": cmd_report,
    "rule72": cmd_rule72,
    "fire": cmd_fire,
    "fireyears": cmd_fireyears,
    "score": cmd_score,
    "cost": cmd_cost,
    "multiple": cmd_multiple,
}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("可用命令:", ", ".join(COMMANDS))
        return
    cmd = sys.argv[1]
    if cmd in ("help", "-h", "--help"):
        print(__doc__)
        return
    fn = COMMANDS.get(cmd)
    if fn is None:
        print(f"❌ 未知命令: {cmd}\n")
        print(__doc__)
        return
    fn()


if __name__ == "__main__":
    main()
