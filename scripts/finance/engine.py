#!/usr/bin/env python3
"""
理财引擎 — 收益计算核心
========================
提供存款、国债、定投、复利等收益计算与多方案对比。

约定（务必先看）:
  · 所有「利率」参数统一使用**百分数**表示 —— 传 3.5 即代表 3.5%（内部自动 ÷100）。
  · 所有「金额」单位为元，返回结果四舍五入保留两位小数。
  · 整存整取定存、国债到期一次还本付息，均为**单利**：利息 = 本金 × 年利率 × 年数。

模块内容:
  - 复利终值      compound_fv(...)
  - 单利利息      simple_interest(...)
  - 整存整取定存   fixed_deposit(...)
  - 国债          treasury_bond(...)
  - 定投          regular_invest(...)
  - 年化收益率     annualized(...)
  - 多方案对比     compare_products(...) / compare_deposit_vs_bond(...)

快速使用:
  from scripts.finance import compare_deposit_vs_bond
  compare_deposit_vs_bond(本金=100000, 定存利率=1.9, 国债利率=2.2, 年限=3)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict


# ============================ 枚举定义 ============================

class DepositMode(Enum):
    """定存计息方式"""
    ONCE = ("整存整取(到期一次还本付息)", "单利: 本息和 = 本金 × (1 + 利率 × 年数)")
    ROLLOVER = ("到期自动转存(复利)", "每期本息续存: 本息和 = 本金 × (1 + 利率)^年数")

    def __init__(self, label: str, desc: str):
        self.label = label
        self.desc = desc


class ProductType(Enum):
    """参与对比的产品计息类型"""
    DEPOSIT = ("定期存款", "整存整取，单利")
    BOND = ("国债", "到期一次还本付息，单利")
    COMPOUND = ("复利产品", "按年复利")

    def __init__(self, label: str, desc: str):
        self.label = label
        self.desc = desc


# ============================ 结果数据类 ============================

@dataclass
class CompoundResult:
    """复利计算结果"""
    principal: float          # 本金(元)
    annual_rate: float        # 年利率(百分数)
    years: float              # 年数
    compound_per_year: int    # 每年复利次数
    final_value: float        # 到期本息和(元)
    interest: float           # 利息(元)

    def summary(self) -> str:
        return (f"本金 {self.principal:,.2f} 元，年利率 {self.annual_rate}%，"
                f"存 {self.years:g} 年（每年复利 {self.compound_per_year} 次）→ "
                f"本息和 {self.final_value:,.2f} 元（利息 {self.interest:,.2f} 元）")


@dataclass
class DepositResult:
    """定存计算结果"""
    principal: float
    annual_rate: float
    years: float
    mode: DepositMode
    final_value: float
    interest: float

    def summary(self) -> str:
        return (f"[{self.mode.label}] 本金 {self.principal:,.2f} 元，"
                f"年利率 {self.annual_rate}%，存 {self.years:g} 年 → "
                f"本息和 {self.final_value:,.2f} 元（利息 {self.interest:,.2f} 元）")


@dataclass
class BondResult:
    """国债计算结果（到期一次还本付息）"""
    principal: float
    annual_rate: float
    years: float
    final_value: float
    interest: float

    def summary(self) -> str:
        return (f"[国债] 本金 {self.principal:,.2f} 元，票面利率 {self.annual_rate}%，"
                f"期限 {self.years:g} 年 → 到期本息和 {self.final_value:,.2f} 元"
                f"（利息 {self.interest:,.2f} 元）")


@dataclass
class InvestResult:
    """定投计算结果（月末投入）"""
    monthly_amount: float     # 每月投入(元)
    annual_rate: float        # 年利率(百分数)
    months: int               # 定投月数
    total_invested: float     # 累计投入本金(元)
    final_value: float        # 到期本息和(元)
    interest: float           # 收益(元)

    def summary(self) -> str:
        return (f"[定投] 每月 {self.monthly_amount:,.2f} 元，年化 {self.annual_rate}%，"
                f"投 {self.months} 个月 → 累计投入 {self.total_invested:,.2f} 元，"
                f"终值 {self.final_value:,.2f} 元（收益 {self.interest:,.2f} 元）")


@dataclass
class Product:
    """参与对比的产品"""
    name: str                 # 产品名
    principal: float          # 本金(元)
    annual_rate: float        # 年利率(百分数)
    years: float              # 期限(年)
    kind: ProductType = ProductType.DEPOSIT

    def calc_final_value(self) -> float:
        """按计息类型计算到期本息和"""
        r = self.annual_rate / 100
        if self.kind == ProductType.COMPOUND:
            return self.principal * (1 + r) ** self.years
        # DEPOSIT / BOND 均为单利
        return self.principal * (1 + r * self.years)


@dataclass
class CompareResult:
    """多方案对比结果"""
    products: List[Product]
    rows: List[Dict]          # 每行: name/principal/annual_rate/years/final_value/interest
    best_name: str
    best_value: float
    diff: float               # 最优与次优的差额(元)

    def summary(self) -> str:
        lines = [f"最优: {self.best_name}（到期本息和 {self.best_value:,.2f} 元，"
                 f"比次优多 {self.diff:,.2f} 元）"]
        for r in self.rows:
            lines.append(f"  · {r['name']}: 本息和 {r['final_value']:,.2f} 元"
                         f"（利息 {r['interest']:,.2f} 元）")
        return "\n".join(lines)


# ============================ 核心计算 ============================

class FinanceEngine:
    """理财计算引擎（全部静态方法，利率用百分数）"""

    @staticmethod
    def compound_fv(principal: float, annual_rate: float, years: float,
                    compound_per_year: int = 1) -> CompoundResult:
        """复利终值: FV = P(1 + r/n)^(nt)"""
        r = annual_rate / 100
        fv = principal * (1 + r / compound_per_year) ** (compound_per_year * years)
        return CompoundResult(principal, annual_rate, years, compound_per_year,
                              round(fv, 2), round(fv - principal, 2))

    @staticmethod
    def simple_interest(principal: float, annual_rate: float, years: float) -> float:
        """单利利息 = 本金 × 年利率 × 年数（返回利息，不还本）"""
        return principal * (annual_rate / 100) * years

    @staticmethod
    def fixed_deposit(principal: float, annual_rate: float, years: float,
                      mode: DepositMode = DepositMode.ONCE) -> DepositResult:
        """整存整取定存（ONCE 单利 / ROLLOVER 复利）"""
        r = annual_rate / 100
        if mode == DepositMode.ROLLOVER:
            fv = principal * (1 + r) ** years
        else:  # ONCE 单利
            fv = principal * (1 + r * years)
        return DepositResult(principal, annual_rate, years, mode,
                             round(fv, 2), round(fv - principal, 2))

    @staticmethod
    def treasury_bond(principal: float, annual_rate: float, years: float) -> BondResult:
        """国债到期一次还本付息: 本息和 = P(1 + r×t)"""
        r = annual_rate / 100
        fv = principal * (1 + r * years)
        return BondResult(principal, annual_rate, years,
                          round(fv, 2), round(fv - principal, 2))

    @staticmethod
    def regular_invest(monthly_amount: float, annual_rate: float, months: int) -> InvestResult:
        """定投(月末投入): FV = A × [((1+i)^n - 1) / i]，i 为月利率"""
        i = annual_rate / 100 / 12
        if i == 0:
            fv = monthly_amount * months
        else:
            fv = monthly_amount * (((1 + i) ** months - 1) / i)
        total = monthly_amount * months
        return InvestResult(monthly_amount, annual_rate, months,
                            round(total, 2), round(fv, 2), round(fv - total, 2))

    @staticmethod
    def annualized(profit: float, principal: float, days: int,
                   method: str = "simple") -> float:
        """年化收益率(返回百分数)。

        method: "simple" 简单年化 = 收益率 / 天数 × 365；
                "compound" 复合年化 = (1 + 收益率)^(365/天数) - 1。
        """
        if principal <= 0 or days <= 0:
            return 0.0
        total_return = profit / principal
        if method == "compound":
            annual = ((1 + total_return) ** (365 / days) - 1) * 100
        else:  # simple
            annual = total_return / days * 365 * 100
        return round(annual, 4)

    @staticmethod
    def compare_products(products: List[Product]) -> CompareResult:
        """多方案对比：按到期本息和排序，返回最优方案"""
        rows = []
        for p in products:
            fv = p.calc_final_value()
            rows.append({
                "name": p.name, "principal": p.principal,
                "annual_rate": p.annual_rate, "years": p.years,
                "final_value": round(fv, 2), "interest": round(fv - p.principal, 2),
            })
        ordered = sorted(rows, key=lambda r: r["final_value"], reverse=True)
        best_name = ordered[0]["name"]
        best_value = ordered[0]["final_value"]
        diff = best_value - (ordered[1]["final_value"] if len(ordered) > 1 else best_value)
        return CompareResult(products, rows, best_name, best_value, round(diff, 2))


# ============================ 便捷入口 ============================

def compare_deposit_vs_bond(本金: float = 100000, 定存利率: float = 1.9,
                            国债利率: float = 2.2, 年限: float = 3,
                            复投: bool = False) -> CompareResult:
    """定存 vs 国债 对比（可直接复现「理财对比」报告场景）

    参数:
      本金: 投入金额(元)
      定存利率: 定期存款年利率(百分数，如 1.9)
      国债利率: 储蓄国债票面年利率(百分数，如 2.2)
      年限: 存期(年)
      复投: 定存是否按年复投(默认 False=整存整取单利)

    返回: CompareResult，含两个方案的到期本息和与差额。
    """
    deposit_kind = ProductType.COMPOUND if 复投 else ProductType.DEPOSIT
    products = [
        Product("定期存款", 本金, 定存利率, 年限, deposit_kind),
        Product("储蓄国债", 本金, 国债利率, 年限, ProductType.BOND),
    ]
    return FinanceEngine.compare_products(products)


# ============================ 自测 ============================

if __name__ == "__main__":
    print("=" * 60)
    print("💹 理财引擎自测")
    print("=" * 60)

    print("\n【复利】", FinanceEngine.compound_fv(100000, 2.0, 3).summary())
    print("【定存·整存整取】", FinanceEngine.fixed_deposit(100000, 1.9, 3).summary())
    print("【定存·年复投】", FinanceEngine.fixed_deposit(100000, 1.9, 3, DepositMode.ROLLOVER).summary())
    print("【国债】", FinanceEngine.treasury_bond(100000, 2.2, 3).summary())
    print("【定投】", FinanceEngine.regular_invest(2000, 3.0, 36).summary())

    print("\n【定存 vs 国债对比】")
    print(compare_deposit_vs_bond(100000, 1.9, 2.2, 3).summary())
