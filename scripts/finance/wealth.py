#!/usr/bin/env python3
"""
财富规划引擎 — 财务自由与理财评估
==================================
提供 72 法则、4% 法则、理财指数、机会成本、财务自由年限等「财富规划」计算，
与 engine.py 的「收益计算」互补。

约定（同 engine.py）:
  · 所有「利率/收益率/通胀率」统一使用**百分数**表示 —— 传 10 即代表 10%（内部自动 ÷100）。
  · 所有「金额」单位为元，返回结果四舍五入保留两位小数。
  · 「累积投资倍数」采用期初投入口径（每年年初投 1 元），与 engine.regular_invest
    （月末投入）口径不同，二者不可混用。

模块内容:
  - 72法则        rule_of_72(...) / rule_of_72_exact(...)
  - 通胀因子      inflation_factor(...)
  - 累积投资倍数  invest_multiple(...)
  - 机会成本      opportunity_cost(...)
  - 财务自由      4% 法则 fire_assets(...) / 年限 fire_years_to_retire(...)
  - 理财指数      wealth_score(...)

快速使用:
  from scripts.finance import WealthEngine
  WealthEngine.fire_assets(年开支=100000)                 # 所需资产 250 万
  WealthEngine.rule_of_72(10)                             # 7.2 年翻倍
  WealthEngine.wealth_score(净资产=1000000, 平均年龄=30, 年工资=200000)
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log


# ============================ 结果数据类 ============================

@dataclass
class FireResult:
    """财务自由测算结果（4% 法则）"""
    annual_expense: float      # 年开支(元)
    withdrawal_rate: float     # 安全取款率(百分数)
    required_assets: float     # 所需金融资产(元)

    def summary(self) -> str:
        return (f"[4%法则] 年开支 {self.annual_expense:,.2f} 元，"
                f"按 {self.withdrawal_rate}% 安全取款率 → "
                f"需金融资产 {self.required_assets:,.2f} 元（≈ 年开支的 {100 / self.withdrawal_rate:.0f} 倍）")


@dataclass
class WealthScoreResult:
    """理财指数评估结果"""
    net_worth: float           # 净资产(元)
    avg_age: float             # 平均年龄(岁)
    annual_salary: float       # 年工资收入(元)
    score: float               # 理财指数
    rating: str                # 评级

    def summary(self) -> str:
        return (f"[理财指数] 净资产 {self.net_worth:,.0f} 元 / (平均年龄 {self.avg_age:g} × "
                f"年工资 {self.annual_salary:,.0f} 元) → 指数 {self.score:.2f}，评级「{self.rating}」")


# ============================ 核心计算 ============================

class WealthEngine:
    """财富规划引擎（全部静态方法，利率/收益率用百分数）"""

    @staticmethod
    def rule_of_72(annual_rate: float) -> float:
        """72 法则：资产翻倍所需年数 ≈ 72 / 年化收益率(%)。快速估算用。"""
        return round(72 / annual_rate, 2)

    @staticmethod
    def rule_of_72_exact(annual_rate: float) -> float:
        """精确翻倍年数 = ln2 / ln(1 + r)。72 法则的精确版。"""
        return round(log(2) / log(1 + annual_rate / 100), 2)

    @staticmethod
    def inflation_factor(inflation_rate: float, years: float) -> float:
        """通胀因子 INF = (1 + 通胀率)^年数。表示 N 年后 1 元购买力等价于今天的 1/INF。"""
        return round((1 + inflation_rate / 100) ** years, 4)

    @staticmethod
    def invest_multiple(years: float, annual_rate: float) -> float:
        """累积投资倍数：每年初投入 1 元，年化 r，N 年后累积倍数 P = ((1+r)^(N+1) − 1) / r。

        对应《财富捷径》口径：年化 10% 时 P(30) = 10 × (1.1^31 − 1) ≈ 181.9。
        注：这里是「期初投入」口径，与 engine.regular_invest（月末投入）不同。
        """
        r = annual_rate / 100
        return round(((1 + r) ** (years + 1) - 1) / r, 2)

    @staticmethod
    def opportunity_cost(amount: float, annual_rate: float, years: float) -> float:
        """机会成本 = 金额 × (1 + 年化收益率)^年数。花掉的钱若拿去投资，N 年后的价值。"""
        return round(amount * (1 + annual_rate / 100) ** years, 2)

    @staticmethod
    def fire_assets(annual_expense: float, withdrawal_rate: float = 4.0) -> FireResult:
        """4% 法则：实现财务自由所需金融资产 = 年开支 / 安全取款率。

        默认 4% 取款率时，所需资产 = 年开支 × 25。年开支应为「家庭年总开支」，
        若已有房租/退休金等被动收入，可先从年开支中扣除。
        """
        if withdrawal_rate <= 0:
            raise ValueError("安全取款率必须大于 0")
        required = annual_expense / (withdrawal_rate / 100)
        return FireResult(annual_expense, withdrawal_rate, round(required, 2))

    @staticmethod
    def fire_years_to_retire(savings_rate: float, real_return: float = 5.0) -> float:
        """财务自由年限：在给定「储蓄率」下还需工作多少年才能财务自由。

        储蓄率 = (年收入 − 年开支) / 年收入（百分数，如 30 表示 30%）。
        基于《财富捷径》的储蓄率→年限对照表（假设扣除通胀后实际收益率 5%），线性插值。
        仅对 real_return=5.0 提供精确表；其他收益率仅作提示（返回表值不变）。
        """
        # 储蓄率(%) -> 财务自由所需年数（实际收益率 5%）
        table = {
            5: 65.5, 10: 51.0, 15: 42.8, 20: 36.7, 25: 31.9,
            30: 28.0, 35: 24.8, 40: 22.0, 45: 19.6, 50: 17.0,
            55: 14.5, 60: 12.5, 70: 8.5, 80: 5.5,
        }
        if savings_rate <= 0:
            return float("inf")  # 无储蓄则永远无法财务自由
        # 表内直接命中
        if savings_rate in table:
            return table[savings_rate]
        # 线性插值（先找到相邻两个断点）
        keys = sorted(table)
        if savings_rate < keys[0]:
            return table[keys[0]]  # 低于最低档，取最低档
        if savings_rate > keys[-1]:
            return table[keys[-1]]
        for lo, hi in zip(keys, keys[1:]):
            if lo < savings_rate <= hi:
                frac = (savings_rate - lo) / (hi - lo)
                return round(table[lo] + (table[hi] - table[lo]) * frac, 2)
        return table[keys[-1]]

    @staticmethod
    def wealth_score(net_worth: float, avg_age: float, annual_salary: float) -> WealthScoreResult:
        """理财指数 = 10 × 净资产 / (平均年龄 × 年工资收入)。

        - 净资产 = 总资产 − 总债务（含存款、基金、房产、车等）
        - 年工资 = 仅劳动收入，不含被动收入（利息、分红、房租）
        - 平均年龄 = 家庭成员年龄平均值
        注意：参加工作不足 5 年、或继承/赠与资产未扣除的家庭，不适用此公式。
        """
        if avg_age <= 0 or annual_salary <= 0:
            raise ValueError("平均年龄与年工资收入必须大于 0")
        score = 10 * net_worth / (avg_age * annual_salary)
        score = round(score, 2)
        # 评级标准
        if score < 0.5:
            rating = "⚠️ 不及格"
        elif score < 1.0:
            rating = "🔶 接近及格"
        elif score < 1.5:
            rating = "✅ 及格"
        elif score < 2.0:
            rating = "⭐ 优秀"
        elif score <= 3.0:
            rating = "🏆 卓越"
        else:
            rating = "👑 极致"
        return WealthScoreResult(net_worth, avg_age, annual_salary, score, rating)


# ============================ 自测 ============================

if __name__ == "__main__":
    print("=" * 60)
    print("💰 财富规划引擎自测")
    print("=" * 60)

    print("\n【72法则】年化 10% →", WealthEngine.rule_of_72(10), "年翻倍（精确",
          WealthEngine.rule_of_72_exact(10), "年）")
    print("【通胀因子】4% 通胀 25 年 →", WealthEngine.inflation_factor(4, 25), "倍")
    print("【累积倍数】年化 10% 投 30 年 → P =", WealthEngine.invest_multiple(30, 10),
          "（对应每年初投 1 元，30 年后 181.9 元）")
    print("【机会成本】一杯 30 元咖啡，10% 年化 40 年 →", WealthEngine.opportunity_cost(30, 10, 40), "元")

    print("\n【财务自由】", WealthEngine.fire_assets(100000).summary())
    print("【财务自由年限】储蓄率 30% →", WealthEngine.fire_years_to_retire(30), "年")
    print("【理财指数】", WealthEngine.wealth_score(1000000, 30, 200000).summary())
