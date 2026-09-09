# -*- coding: utf-8 -*-
"""生成对账 Excel（对账明细为总表，三类数据合一）"""
import json
from collections import Counter

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from config import TMP as T, OUT_EXCEL as OUT

matched = json.load(open(T + r"\matched.json", encoding="utf-8"))
ub = json.load(open(T + r"\unmatched_bill.json", encoding="utf-8"))
uc = json.load(open(T + r"\unmatched_ctr.json", encoding="utf-8"))

wb = Workbook()
HDR_FILL = PatternFill("solid", fgColor="4472C4")
HDR_FONT = Font(bold=True, color="FFFFFF")
FILL_MATCH = PatternFill("solid", fgColor="E2EFDA")   # 绿：匹配成功
FILL_BILL = PatternFill("solid", fgColor="FCE4D6")    # 橙：财务有-合同无
FILL_CTR = PatternFill("solid", fgColor="DDEBF7")     # 蓝：合同有-财务无
WARN_FILL = PatternFill("solid", fgColor="FFE699")    # 黄：月租差异大需核对
WRAP = Alignment(wrap_text=True, vertical="top")


def style_header(ws, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")


def auto_width(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


# ───────── Sheet1 汇总 ─────────
ws = wb.active
ws.title = "汇总"
rows = [
    ["一、总体", "数量"],
    ["财务房源(行)", len(matched) + len(ub)],
    ["合同(行)", len(matched) + len(uc)],
    ["匹配成功", len(matched)],
    ["财务有-合同无对应", len(ub)],
    ["合同有-财务无对应", len(uc)],
    [],
    ["二、匹配置信度", ""],
]
rows += [[f"  {k}", v] for k, v in Counter(m["匹配置信度"] for m in matched).items()]
rows += [[], ["三、名字匹配方式", ""]]
rows += [[f"  {k}", v] for k, v in Counter(m["名字匹配"] for m in matched).items()]
rows += [[], ["四、对账结论", ""]]
rows += [[f"  {k}", v] for k, v in Counter(
    "相符" if m["结论"].startswith("与合同应收相符") or "相符" in m["结论"] else "有差异" for m in matched).items()]
rows += [[], ["五、未匹配财务原因", ""]]
rows += [[f"  {k}", v] for k, v in Counter(x["原因"].split("(")[0].split("[")[0] for x in ub).most_common()]
for r in rows:
    ws.append(r)
ws.column_dimensions["A"].width = 40
ws.column_dimensions["B"].width = 16

# ───────── Sheet2 对账明细（总表） ─────────
ws2 = wb.create_sheet("对账明细")
hdr = ["状态", "板块", "承租人", "物业编码(财务)", "房号集合(合同)", "结论",
       "财务应收月数", "财务应收合计(元)", "财务实收合计(元)", "调整后累欠(元)",
       "合同编号", "合同面积", "月租金(元)", "录入起始", "解除时间", "备注"]
ws2.append(hdr)
style_header(ws2, len(hdr))

rows_out = []

# 匹配成功
for m in sorted(matched, key=lambda x: (0 if x["结论"].startswith("与合同应收相符") else 1, -abs(x["精确金额差异"]))):
    rows_out.append(["匹配成功", m["板块"], m["承租人"], m["物业编码"], m["房号集合"], m["结论"],
                     m["财务应收月数"], round(m["财务应收合计"], 2), round(m["财务实收合计"], 2), round(m["调整后欠款"], 2),
                     m["合同编号"], m["合同面积"], m["月租金"], m["录入起始"][:10], m["解除时间"][:10], m["备注"]])

# 财务有-合同无对应
for x in sorted(ub, key=lambda x: -(x["调整后欠款"] or 0)):
    rows_out.append(["财务有-合同无", x["板块"], x["承租人"], x["物业编码"], "", x["结论"],
                     x["财务计费月数"], round(x["应收合计"] or 0, 2), round(x["实收合计"] or 0, 2), round(x["调整后欠款"] or 0, 2),
                     "", "", "", "", "", x["原因"]])

# 合同有-财务无对应
for c in sorted(uc, key=lambda x: (x["项目名称"], x["承租方"])):
    rows_out.append(["合同有-财务无", c["项目名称"], c["承租方"], "", c["房号集合"], c["结论"],
                     "", "", "", "",
                     "", c["面积"], c["月租金"], c["录入起始"][:10], c["解除时间"][:10], c["备注"]])

for r in rows_out:
    ws2.append(r)

# 状态列着色 + 结论列换行
for i, r in enumerate(rows_out, start=2):
    st = r[0]
    fill = FILL_MATCH if st == "匹配成功" else (FILL_BILL if st == "财务有-合同无" else FILL_CTR)
    ws2.cell(row=i, column=1).fill = fill
    ws2.cell(row=i, column=6).alignment = WRAP
    if "⚠️" in (r[5] or ""):
        ws2.cell(row=i, column=6).fill = WARN_FILL

auto_width(ws2, [12, 12, 22, 24, 24, 52, 9, 13, 13, 13, 15, 9, 10, 10, 10, 30])
ws2.freeze_panes = "A2"
ws2.auto_filter.ref = f"A1:P{len(rows_out) + 1}"

wb.save(OUT)
print("已生成:", OUT)
print(f"匹配 {len(matched)}, 财务无对应 {len(ub)}, 合同无对应 {len(uc)}, 总表共 {len(rows_out)} 行")
