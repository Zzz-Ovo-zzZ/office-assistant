# -*- coding: utf-8 -*-
"""
step6 · 回填结论（COM 精确写单元格版）

把对账结论(matched + unmatched_bill)按「sheet + excel_row」精确写回源表副本的「应收情况」列。
- 用 Excel/WPS COM 只改目标单元格，公式、缓存值、跨文件引用、格式全部原样保留；
- 另存为副本，不改动源表；
- 结论文本含换行，写入时设置 WrapText 使其正常显示。
"""
import json
import os
import subprocess
import sys

from config import BILL, TMP

SHEETS = ["顺泰", "置业、龙州", "龙津"]
TOTAL = 1159  # 三个板块有效房源行总数（顺泰535 + 置业、龙州431 + 龙津193）
COL = 2       # 「应收情况」列（1-based），三个板块均为第 2 列


def main():
    matched = json.load(open(TMP + r"\matched.json", encoding="utf-8"))
    ub = json.load(open(TMP + r"\unmatched_bill.json", encoding="utf-8"))

    rows = []
    for m in matched:
        rows.append({"sheet": m["sheet"], "row": m["excel_row"], "col": COL, "text": m["结论"]})
    for u in ub:
        rows.append({"sheet": u["sheet"], "row": u["excel_row"], "col": COL, "text": u["结论"]})
    assert len(rows) == TOTAL, f"待写入 {len(rows)} 条 != {TOTAL}"
    print(f"待写入结论 {len(rows)} 条")

    out = os.path.splitext(BILL)[0] + "_已填结论.xlsx"
    cfg = {"src": BILL, "out": out, "rows": rows}
    data_path = TMP + r"\fill_data.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False)
    print(f"回填数据已写入 {data_path}")

    ps_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fill_via_com.ps1")
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_script,
           "-DataPath", data_path]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.stdout:
        print(r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr)
    if r.returncode != 0:
        sys.exit(r.returncode)
    print(f"完成 → {out}")


if __name__ == "__main__":
    main()
