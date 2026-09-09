# -*- coding: utf-8 -*-
"""
数据正确性校验：
1. 财务源表逐行回读，比对提取值（应收/实收/累欠/各月）
2. 合同源表逐行回读，比对提取值
3. 汇总守恒（= 源表总计）
4. 匹配+未匹配 数量与金额守恒
"""
import json
import re

import openpyxl

from config import BILL, CTR, TMP as T


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def eq(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < 0.005


def main():
    bill = json.load(open(T + r"\bill.json", encoding="utf-8"))
    contracts = json.load(open(T + r"\contracts.json", encoding="utf-8"))

    # ───────── 校验A：财务源表逐行回读（顺序索引对应，处理重复行） ─────────
    print("=" * 60)
    print("校验A：财务源表逐行回读比对")
    wb = openpyxl.load_workbook(BILL, read_only=True, data_only=True)
    rec_fail = []
    rec_total = 0
    idx = 0
    for name in ["顺泰", "置业、龙州", "龙津"]:
        ws = wb[name]
        for i, row in enumerate(ws.iter_rows(values_only=True), 1):
            if i == 1:
                continue
            g = lambda j: row[j] if j < len(row) else None
            tenant = g(0)
            if tenant is None or str(tenant).strip() == "":
                continue
            if str(tenant).strip() == "总计":
                continue
            rec_total += 1
            if idx >= len(bill):
                rec_fail.append((name, i, str(tenant), "bill.json 缺记录"))
                idx += 1
                continue
            b = bill[idx]
            idx += 1
            mc = str(g(1)).strip() if g(1) else ""
            # 定位字段
            if b["板块"] != name or b["承租人"] != str(tenant).strip() or b["物业编码"] != mc:
                rec_fail.append((name, i, str(tenant), f"定位错位: bill[{idx-1}]={b['板块']}/{b['承租人'][:8]}/{b['物业编码'][:20]}"))
                continue
            fields = [("应收合计", 19), ("实收合计", 32), ("调整后欠款", 34)]
            for fname, fidx in fields:
                if not eq(b[fname], num(g(fidx))):
                    rec_fail.append((name, i, str(tenant), f"{fname}: 提取={b[fname]} 源表={num(g(fidx))}"))
            for mi in range(12):
                src = num(g(7 + mi))
                got = b["应收月"][mi]
                if not eq(src, got):
                    rec_fail.append((name, i, str(tenant), f"应收{mi+1}月: 提取={got} 源表={src}"))
    wb.close()
    print(f"财务数据行总数: {rec_total}")
    print(f"逐字段比对失败数: {len(rec_fail)}")
    if rec_fail:
        print("  失败样例(前20):")
        for f in rec_fail[:20]:
            print("   ", f)

    # ───────── 校验B：合同源表逐行回读 ─────────
    print("=" * 60)
    print("校验B：合同源表逐行回读比对")
    wb2 = openpyxl.load_workbook(CTR, read_only=True, data_only=True)
    ws2 = wb2["导入格式"]
    ctr_fail = []
    ctr_total = 0
    for i, row in enumerate(ws2.iter_rows(values_only=True)):
        if i == 0:
            continue
        g = lambda j: row[j] if j < len(row) else None
        if g(0) is None:
            continue
        ctr_total += 1
        c = contracts[i - 1] if i - 1 < len(contracts) else None
        if c is None:
            ctr_fail.append((i, "缺记录"))
            continue
        checks = [
            ("承租方", str(g(9)).strip() if g(9) else "", c["承租方"]),
            ("房号集合", str(g(11)).strip() if g(11) else "", c["房号集合"]),
            ("月租金", num(g(19)), c["月租金"]),
            ("面积", num(g(12)), c["面积"]),
        ]
        for fname, src, got in checks:
            if fname in ("承租方", "房号集合"):
                if src != got:
                    ctr_fail.append((i, f"{fname}: 源={src[:20]} 提取={got[:20]}"))
            else:
                if not eq(src, got):
                    ctr_fail.append((i, f"{fname}: 源={src} 提取={got}"))
    wb2.close()
    print(f"合同数据行总数: {ctr_total}")
    print(f"逐字段比对失败数: {len(ctr_fail)}")
    if ctr_fail:
        print("  失败样例(前20):")
        for f in ctr_fail[:20]:
            print("   ", f)

    # ───────── 校验C：汇总守恒 ─────────
    print("=" * 60)
    print("校验C：汇总守恒")
    ys = sum(num(b["应收合计"]) or 0 for b in bill)
    ss = sum(num(b["实收合计"]) or 0 for b in bill)
    qk = sum(num(b["调整后欠款"]) or 0 for b in bill)
    print(f"三大板块合计: 应收={ys/10000:.4f}万 实收={ss/10000:.4f}万 累欠={qk/10000:.4f}万")
    print(f"目标(源表总计): 应收=4380.867555万 实收=2681.901651万 累欠=8275.436043万")
    print(f"应收一致: {abs(ys/10000 - 4380.867555) < 0.01}")
    print(f"实收一致: {abs(ss/10000 - 2681.901651) < 0.01}")
    print(f"累欠一致: {abs(qk/10000 - 8275.436043) < 0.01}")

    # ───────── 校验D：匹配+未匹配 守恒 ─────────
    print("=" * 60)
    print("校验D：匹配+未匹配 守恒")
    matched = json.load(open(T + r"\matched.json", encoding="utf-8"))
    ub = json.load(open(T + r"\unmatched_bill.json", encoding="utf-8"))
    print(f"bill总数={len(bill)}, 匹配={len(matched)}, 未匹配={len(ub)}, 匹配+未匹配={len(matched)+len(ub)}")
    print(f"数量守恒: {len(matched)+len(ub) == len(bill)}")
    m_qk = sum(num(x["调整后欠款"]) or 0 for x in matched)
    u_qk = sum(num(x["调整后欠款"]) or 0 for x in ub)
    print(f"累欠守恒: 匹配{m_qk/10000:.4f} + 未匹配{u_qk/10000:.4f} = {(m_qk+u_qk)/10000:.4f}万 vs 总{qk/10000:.4f}万")
    print(f"累欠守恒一致: {abs(m_qk+u_qk-qk) < 0.5}")


if __name__ == "__main__":
    main()
