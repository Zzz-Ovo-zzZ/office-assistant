# -*- coding: utf-8 -*-
"""
对账脚本 · 数据提取 + 诊断
财务累欠明细表(应收/实收/累欠)  vs  合同整理表(合同起止/月租金)
只读源文件，不改动。
"""
import json
import os
import re
from collections import defaultdict, Counter

import openpyxl

from config import BILL, CTR, TMP as OUT


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def load_bill():
    """财务表三大板块，每行一个房源（按表头名定位列，兼容各板块列结构差异）"""
    wb = openpyxl.load_workbook(BILL, read_only=True, data_only=True)
    records = []
    idx = 0
    for name in ["顺泰", "置业、龙州", "龙津"]:
        ws = wb[name]
        rows = ws.iter_rows(values_only=True)
        header = next(rows)
        colmap = {str(h).strip(): i for i, h in enumerate(header) if h is not None and str(h).strip()}

        def c(*names):
            for n in names:
                if n in colmap:
                    return colmap[n]
            return None

        ying_idx = [c(f"{m}月应收") for m in range(1, 13)]
        shi_idx = [c(f"{m}月实收") for m in range(1, 13)]
        c_tenant = c("承租人")
        c_mc = c("物业编码")
        c_unit = c("承租单元")
        c_bz = c("备注")

        for i, row in enumerate(rows, 2):
            g = lambda j: row[j] if (j is not None and j < len(row)) else None
            tenant = g(c_tenant)
            if tenant is None or str(tenant).strip() == "":
                continue
            if str(tenant).strip() == "总计":
                continue
            ying_mon = [num(g(j)) for j in ying_idx]
            shi_mon = [num(g(j)) for j in shi_idx]
            rec = {
                "板块": name,
                "sheet": name,
                "idx": idx,
                "excel_row": i,
                "承租人": str(tenant).strip(),
                "物业编码": str(g(c_mc)).strip() if g(c_mc) else "",
                "承租单元": str(g(c_unit)).strip() if g(c_unit) else "",
                "24年欠款": num(g(c("24年欠款"))),
                "调整金额": num(g(c("调整金额"))),
                "调整后24年欠款": num(g(c("调整后24年欠款"))),
                "24年预收25年": num(g(c("24年预收25年", "24年预收25"))),
                "应收月": ying_mon,
                "应收合计": num(g(c("1-12月应收"))),
                "实收月": shi_mon,
                "实收合计": num(g(c("1-12月实收"))),
                "欠款合计": num(g(c("1-12月欠款"))),
                "调整后欠款": num(g(c("调整后1-12月欠款"))),
                "备注": str(g(c_bz)).strip() if g(c_bz) else "",
            }
            # 财务计费月份(应收>0 的月份, 1-based)
            rec["财务计费月"] = [k + 1 for k, v in enumerate(ying_mon) if v is not None and v > 0]
            rec["财务计费月数"] = len(rec["财务计费月"])
            records.append(rec)
            idx += 1
    wb.close()
    return records


def load_contracts():
    """合同表「导入格式」，每行一个合同(房源)"""
    wb = openpyxl.load_workbook(CTR, read_only=True, data_only=True)
    ws = wb["导入格式"]
    contracts = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        g = lambda j: row[j] if j < len(row) else None
        if g(0) is None:
            continue
        c = {
            "序号": g(0),
            "单多房源": str(g(2)).strip() if g(2) else "",
            "是否已结束": str(g(3)).strip() if g(3) else "",
            "优惠免租": str(g(4)).strip() if g(4) else "",
            "完成情况": str(g(6)).strip() if g(6) else "",
            "合同类别": str(g(7)).strip() if g(7) else "",
            "合同编号": str(g(8)).strip() if g(8) else "",
            "承租方": str(g(9)).strip() if g(9) else "",
            "项目名称": str(g(10)).strip() if g(10) else "",
            "房号集合": str(g(11)).strip() if g(11) else "",
            "面积": num(g(12)),
            "签约日期": str(g(13)).strip() if g(13) else "",
            "录入起始": g(14),
            "解除时间": g(15),
            "月租金": num(g(19)),
            "租金递增": str(g(31)).strip() if g(31) else "",
            "备注": str(g(33)).strip() if g(33) else "",
            "楼栋": str(g(44)).strip() if g(44) else "",
            "资产所在层": g(45),
            "资产名称": str(g(46)).strip() if g(46) else "",
            "楼宇名称": str(g(48)).strip() if g(48) else "",
            "楼层": g(49),
            "资产简写": str(g(50)).strip() if g(50) else "",
            "房源编码": str(g(51)).strip() if g(51) else "",
            "合同起始": g(52),
            "合同到期": g(53),
        }
        contracts.append(c)
    wb.close()
    return contracts


def main():
    bill = load_bill()
    contracts = load_contracts()
    print(f"财务房源行数: {len(bill)}")
    print(f"合同行数: {len(contracts)}")

    # 板块分布
    print("\n=== 财务各板块房源数 ===")
    for k, v in Counter(r["板块"] for r in bill).items():
        print(f"  {k}: {v}")

    # 财务板块物业编码前缀(项目)分布
    print("\n=== 财务各板块「物业编码」第一段(项目/园区)分布 ===")
    for bank in ["顺泰", "置业、龙州", "龙津"]:
        pre = Counter()
        for r in bill:
            if r["板块"] != bank:
                continue
            mc = r["物业编码"]
            first = mc.split("-")[0] if mc else "(空)"
            pre[first] += 1
        print(f"  [{bank}]")
        for k, v in pre.most_common():
            print(f"     {k}: {v}")

    # 合同项目分布 + 各项目承租方
    print("\n=== 合同表「项目名称」分布 ===")
    proj_tenant = defaultdict(set)
    for c in contracts:
        proj_tenant[c["项目名称"]].add(c["承租方"])
    for k, v in Counter(c["项目名称"] for c in contracts).most_common():
        print(f"  {k}: {v} 行, 承租方去重 {len(proj_tenant[k])}")

    # 保存中间数据
    with open(os.path.join(OUT, "bill.json"), "w", encoding="utf-8") as f:
        json.dump(bill, f, ensure_ascii=False, default=str)
    with open(os.path.join(OUT, "contracts.json"), "w", encoding="utf-8") as f:
        json.dump(contracts, f, ensure_ascii=False, default=str)
    print("\n已保存 bill.json / contracts.json")


if __name__ == "__main__":
    main()
