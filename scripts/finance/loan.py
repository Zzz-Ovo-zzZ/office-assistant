#!/usr/bin/env python3
"""
贷款计算 — 等额本息 / 等额本金 / 提前还款
============================================
房贷、车贷等常见还款方式的月供、总利息、提前还款省息测算。

约定（与 engine.py 一致）:
  · 「利率」用百分数表示 —— 传 3.5 即 3.5%（内部自动 ÷100）。
  · 「金额」单位为元，返回结果保留两位小数。

模块内容:
  - 等额本息     equal_installment(...)
  - 等额本金     equal_principal(...)
  - 提前还款测算  prepayment_saving(...)

快速使用:
  from scripts.finance import equal_installment
  equal_installment(本金=1000000, 年利率=3.5, 期数=360)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


# ============================ 枚举定义 ============================

class LoanMethod(Enum):
    """还款方式"""
    INSTALLMENT = ("等额本息", "每月月供固定，前期利息占比高")
    PRINCIPAL = ("等额本金", "每月还本金固定，月供逐月递减")

    def __init__(self, label: str, desc: str):
        self.label = label
        self.desc = desc


# ============================ 结果数据类 ============================

@dataclass
class LoanResult:
    """贷款计算结果"""
    principal: float          # 贷款本金(元)
    annual_rate: float        # 年利率(百分数)
    months: int               # 期数(月)
    method: LoanMethod
    monthly_payment: float    # 月供(等额本息固定值 / 等额本金首月值)
    last_payment: float       # 末月月供(等额本息同月供 / 等额本金末月值)
    total_interest: float     # 总利息(元)
    total_payment: float      # 本息合计(元)

    def summary(self) -> str:
        return (f"[{self.method.label}] 贷款 {self.principal:,.2f} 元，"
                f"年利率 {self.annual_rate}%，分 {self.months} 期 → "
                f"月供 {self.monthly_payment:,.2f} 元"
                f"{'（首月）' if self.method == LoanMethod.PRINCIPAL else ''}，"
                f"总利息 {self.total_interest:,.2f} 元，"
                f"本息合计 {self.total_payment:,.2f} 元")


# ============================ 核心计算 ============================

class LoanCalculator:
    """贷款计算器（静态方法，利率用百分数）"""

    @staticmethod
    def equal_installment(principal: float, annual_rate: float, months: int) -> LoanResult:
        """等额本息：M = P × i × (1+i)^n / ((1+i)^n - 1)"""
        i = annual_rate / 100 / 12
        if i == 0:
            m = principal / months
        else:
            m = principal * i * (1 + i) ** months / ((1 + i) ** months - 1)
        total = m * months
        return LoanResult(principal, annual_rate, months, LoanMethod.INSTALLMENT,
                          round(m, 2), round(m, 2),
                          round(total - principal, 2), round(total, 2))

    @staticmethod
    def equal_principal(principal: float, annual_rate: float, months: int) -> LoanResult:
        """等额本金：每期本金固定 P/n，利息逐月递减，总利息 = P×i×(n+1)/2"""
        i = annual_rate / 100 / 12
        per_principal = principal / months
        first = per_principal + principal * i          # 首月
        last = per_principal + per_principal * i       # 末月
        total_interest = principal * i * (months + 1) / 2
        total = principal + total_interest
        return LoanResult(principal, annual_rate, months, LoanMethod.PRINCIPAL,
                          round(first, 2), round(last, 2),
                          round(total_interest, 2), round(total, 2))

    @staticmethod
    def _remaining_principal(principal: float, i: float, months: int,
                             paid_months: int) -> float:
        """等额本息还完 paid_months 期后的剩余本金"""
        return (principal * ((1 + i) ** months - (1 + i) ** paid_months)
                / ((1 + i) ** months - 1))

    @staticmethod
    def prepayment_saving(principal: float, annual_rate: float, months: int,
                          paid_months: int, prepay_amount: float = 0.0) -> Tuple[float, float, int]:
        """等额本息提前还款省息测算（缩短期限、月供不变）。

        参数:
          prepay_amount: 提前还款金额；传 0 或省略 = 一次性还清剩余本金。

        返回: (剩余本金, 节省利息, 缩短期数)
        """
        i = annual_rate / 100 / 12
        m = principal * i * (1 + i) ** months / ((1 + i) ** months - 1)
        remaining = LoanCalculator._remaining_principal(principal, i, months, paid_months)

        if prepay_amount <= 0 or prepay_amount >= remaining:
            # 一次性还清剩余本金，省下的利息 = 剩余期数应付总额 - 剩余本金
            left_periods = months - paid_months
            saved = m * left_periods - remaining
            return round(remaining, 2), round(saved, 2), left_periods

        # 提前还部分，月供不变，重算剩余期数
        new_remaining = remaining - prepay_amount
        if new_remaining <= 0:
            return 0.0, round(m * (months - paid_months) - remaining, 2), months - paid_months

        new_periods = math.ceil(math.log(m / (m - new_remaining * i)) / math.log(1 + i))
        old_left_interest = m * (months - paid_months) - remaining
        new_interest = m * new_periods - new_remaining
        saved = old_left_interest - new_interest
        return round(remaining, 2), round(saved, 2), (months - paid_months) - new_periods


# ============================ 便捷入口 ============================

def equal_installment(本金: float, 年利率: float, 期数: int) -> LoanResult:
    """等额本息（中文参数便捷入口）"""
    return LoanCalculator.equal_installment(本金, 年利率, 期数)


def equal_principal(本金: float, 年利率: float, 期数: int) -> LoanResult:
    """等额本金（中文参数便捷入口）"""
    return LoanCalculator.equal_principal(本金, 年利率, 期数)


def 房贷对比(本金: float, 年利率: float, 期数: int) -> None:
    """同时打印等额本息与等额本金两种方式的对比（等额本金总利息更少）"""
    a = LoanCalculator.equal_installment(本金, 年利率, 期数)
    b = LoanCalculator.equal_principal(本金, 年利率, 期数)
    print(a.summary())
    print(b.summary())
    print(f"  → 等额本金比等额本息总利息少 {a.total_interest - b.total_interest:,.2f} 元")


# ============================ 自测 ============================

if __name__ == "__main__":
    print("=" * 60)
    print("🏦 贷款计算自测")
    print("=" * 60)

    print("\n【等额本息】", LoanCalculator.equal_installment(1000000, 3.5, 360).summary())
    print("【等额本金】", LoanCalculator.equal_principal(1000000, 3.5, 360).summary())

    print("\n【房贷对比】")
    房贷对比(1000000, 3.5, 360)

    print("\n【提前还款】还 5 年(60期)后一次性还清:")
    r, saved, months_saved = LoanCalculator.prepayment_saving(1000000, 3.5, 360, 60)
    print(f"  剩余本金 {r:,.2f} 元，省利息 {saved:,.2f} 元，缩短 {months_saved} 期")
