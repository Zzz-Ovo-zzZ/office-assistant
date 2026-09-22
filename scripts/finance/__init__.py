#!/usr/bin/env python3
"""
理财助手模块
============
提供个人理财相关能力:

模块:
  engine  - 收益计算引擎 (复利/定存/国债/定投/年化/多方案对比)
  loan    - 贷款计算 (等额本息/等额本金/提前还款)
  ledger  - 记账台账 (CSV 流水 + 汇总)
  wealth  - 财富规划 (72法则/4%法则/理财指数/机会成本/财务自由)

快速使用:
  from scripts.finance import compare_deposit_vs_bond
  compare_deposit_vs_bond(本金=100000, 定存利率=1.9, 国债利率=2.2, 年限=3)

  from scripts.finance import Ledger
  Ledger().add_entry("2026-09-22", "收入", "工资", 15000, "9月工资")
"""

from .engine import (
    FinanceEngine, DepositMode, ProductType, Product,
    CompoundResult, DepositResult, BondResult, InvestResult, CompareResult,
    compare_deposit_vs_bond,
)
from .loan import (
    LoanCalculator, LoanMethod, LoanResult,
    equal_installment, equal_principal, 房贷对比,
)
from .ledger import Ledger
from .wealth import WealthEngine, FireResult, WealthScoreResult


__all__ = [
    # engine
    "FinanceEngine", "DepositMode", "ProductType", "Product",
    "CompoundResult", "DepositResult", "BondResult", "InvestResult", "CompareResult",
    "compare_deposit_vs_bond",
    # loan
    "LoanCalculator", "LoanMethod", "LoanResult",
    "equal_installment", "equal_principal", "房贷对比",
    # ledger
    "Ledger",
    # wealth
    "WealthEngine", "FireResult", "WealthScoreResult",
]
