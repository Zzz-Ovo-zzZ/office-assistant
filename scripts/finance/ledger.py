#!/usr/bin/env python3
"""
记账台账 — CSV 流水 + 汇总
==========================
流水存 CSV（Excel/WPS 可直接打开编辑），本模块负责读取、追加、汇总。

CSV 列结构（UTF-8 带 BOM，Excel/WPS 打开不乱码）:
  日期,类型,分类,金额,备注
  · 日期: YYYY-MM-DD
  · 类型: 收入 / 支出
  · 分类: 工资/理财收益/餐饮/交通/购物/...
  · 金额: 正数(元)，靠「类型」列区分收支
  · 备注: 可选说明

默认流水文件: output/finance/ledger/流水账.csv（可传参覆盖）

快速使用:
  from scripts.finance import Ledger
  ledger = Ledger()
  ledger.add_entry("2026-09-22", "收入", "工资", 15000, "9月工资")
  ledger.report()
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from typing import List, Dict


class Ledger:
    """记账台账：读 CSV 流水、追加、汇总"""

    HEADER = ["日期", "类型", "分类", "金额", "备注"]
    DEFAULT_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "output", "finance", "ledger", "流水账.csv",
    )

    def __init__(self, csv_path: str = None):
        self.csv_path = csv_path or Ledger.DEFAULT_PATH
        self.entries: List[Dict] = []
        self.load()

    # ---- 读写 ----

    def load(self) -> List[Dict]:
        """从 CSV 读取全部流水（文件不存在则返回空）"""
        self.entries = []
        if not os.path.exists(self.csv_path):
            return self.entries
        with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("日期"):
                    continue
                try:
                    row["金额"] = float(row.get("金额") or 0)
                except ValueError:
                    continue
                self.entries.append(row)
        return self.entries

    def add_entry(self, 日期: str, 类型: str, 分类: str, 金额: float,
                  备注: str = "") -> Dict:
        """追加一笔流水并立即写回 CSV。类型为「收入」或「支出」。"""
        entry = {"日期": 日期, "类型": 类型, "分类": 分类,
                 "金额": float(金额), "备注": 备注}
        self.entries.append(entry)
        exists = os.path.exists(self.csv_path)
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        with open(self.csv_path, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(self.HEADER)
            writer.writerow([日期, 类型, 分类, 金额, 备注])
        return entry

    # ---- 汇总 ----

    def summary(self) -> Dict[str, float]:
        """总收入 / 总支出 / 结余"""
        income = sum(e["金额"] for e in self.entries if e["类型"] == "收入")
        expense = sum(e["金额"] for e in self.entries if e["类型"] == "支出")
        return {"总收入": round(income, 2),
                "总支出": round(expense, 2),
                "结余": round(income - expense, 2)}

    def by_category(self) -> Dict[str, Dict[str, float]]:
        """按分类汇总收支，返回 {分类: {"收入": x, "支出": y}}"""
        result = defaultdict(lambda: defaultdict(float))
        for e in self.entries:
            result[e["分类"]][e["类型"]] += e["金额"]
        out = {}
        for cat, d in result.items():
            out[cat] = {"收入": round(d.get("收入", 0), 2),
                        "支出": round(d.get("支出", 0), 2)}
        return out

    def monthly_report(self) -> Dict[str, Dict[str, float]]:
        """按月汇总，返回 {月份: {"收入": x, "支出": y, "结余": z}}"""
        result = defaultdict(lambda: defaultdict(float))
        for e in self.entries:
            month = (e["日期"] or "")[:7]
            result[month][e["类型"]] += e["金额"]
        out = {}
        for month in sorted(result):
            inc = result[month].get("收入", 0)
            exp = result[month].get("支出", 0)
            out[month] = {"收入": round(inc, 2), "支出": round(exp, 2),
                          "结余": round(inc - exp, 2)}
        return out

    def report(self) -> str:
        """生成完整汇总报表（打印并返回文本）"""
        self.load()
        s = self.summary()
        lines = [
            "=" * 60,
            "📒 记账台账汇总",
            "=" * 60,
            f"流水文件: {self.csv_path}",
            f"共 {len(self.entries)} 笔",
            f"💰 总收入: {s['总收入']:,.2f} 元",
            f"💸 总支出: {s['总支出']:,.2f} 元",
            f"📊 结余: {s['结余']:,.2f} 元",
            "",
            "【分类汇总】",
        ]
        for cat, v in sorted(self.by_category().items()):
            lines.append(f"  · {cat}: 收 {v['收入']:,.2f} / 支 {v['支出']:,.2f}")
        lines.append("")
        lines.append("【按月汇总】")
        for month, v in self.monthly_report().items():
            lines.append(f"  · {month}: 收 {v['收入']:,.2f} / 支 {v['支出']:,.2f}"
                         f" / 结余 {v['结余']:,.2f}")
        text = "\n".join(lines)
        print(text)
        return text

    def save_report(self, md_path: str = None) -> str:
        """把汇总报表写入 markdown 文件（默认与流水同目录）"""
        if md_path is None:
            md_path = os.path.splitext(self.csv_path)[0] + "_汇总.md"
        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        text = self.report()
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"汇总已保存: {md_path}")
        return md_path


# ============================ 自测 ============================

if __name__ == "__main__":
    import tempfile

    tmp = os.path.join(tempfile.gettempdir(), "finance_ledger_demo.csv")
    if os.path.exists(tmp):
        os.remove(tmp)

    lg = Ledger(tmp)
    lg.add_entry("2026-09-01", "收入", "工资", 15000, "9月工资")
    lg.add_entry("2026-09-05", "支出", "餐饮", 800, "聚餐")
    lg.add_entry("2026-09-10", "支出", "交通", 300, "加油")
    lg.report()
    os.remove(tmp)
    print("\n(自测临时文件已清理)")
