# -*- coding: utf-8 -*-
"""精确重算 + 结论生成"""
import json
import re
from collections import Counter

from config import TMP as T


def free_months_2025(bz):
    if not bz or "免租" not in bz:
        return set()
    free = set()
    pat = r"(\d{4})\.(\d{1,2})\.(\d{1,2})\s*[-—~–至]\s*(\d{4})\.(\d{1,2})\.(\d{1,2})"
    for m in re.finditer(pat, bz):
        sy, sm = int(m.group(1)), int(m.group(2))
        ey, em = int(m.group(4)), int(m.group(5))
        if sy > 2025 or ey < 2025:
            continue
        ms = sm if sy == 2025 else 1
        me = em if ey == 2025 else 12
        for mo in range(ms, me + 1):
            free.add(mo)
    return free


def actual_rent(m):
    """财务实际月租：固定值 or 平均"""
    vals = [v for v in (m.get("财务各月应收金额") or []) if v and v > 0]
    if not vals:
        return None, "无"
    uniq = set(round(v, 2) for v in vals)
    if len(uniq) == 1:
        return round(vals[0], 2), "固定"
    return round(sum(vals) / len(vals), 2), "平均"


def month_range(months):
    if not months:
        return "无"
    return f"{months[0]}~{months[-1]}月"


def compress_months(amounts):
    """12 个月金额列表 → 自然语言（连续相同金额合并为区间）"""
    a = [0.0 if (v is None or v == 0) else round(float(v), 2) for v in (amounts or [])]
    a = (a + [0.0] * 12)[:12]
    segs = []
    i = 0
    while i < 12:
        v = a[i]
        j = i
        while j < 12 and a[j] == v:
            j += 1
        segs.append((i + 1, j, v))
        i = j
    parts = []
    for s, e, v in segs:
        rng = f"{s}~{e}月" if s != e else f"{s}月"
        if v == 0:
            parts.append(f"{rng}无")
        elif v < 0:
            parts.append(f"{rng}{v:g}元(冲销)")
        else:
            parts.append(f"{rng}每月{v:g}元" if s != e else f"{rng}{v:g}元")
    return "，".join(parts)


def build_ctr_amounts(m):
    """合同 12 月应收金额（合同覆盖月份=月租金，免租月=0，未覆盖月=0）"""
    free = set(m.get("免租月", []))
    cmonths = set(m.get("合同推算月份") or [])
    rent = m["月租金"] or 0
    return [rent if (mo in cmonths and mo not in free) else 0.0 for mo in range(1, 13)]


def make_conclusion(m):
    fm = m["财务应收月数"]
    cm = m["精确推算月数"]
    free = m.get("免租月", [])
    rent = m["月租金"]

    bill_desc = compress_months(m.get("财务各月应收金额"))
    bill_total = m["财务应收合计"]
    shi_desc = compress_months(m.get("财务各月实收金额"))
    shi_total = m.get("财务实收合计") or 0
    ctr_desc = compress_months(build_ctr_amounts(m))
    ctr_total = m["精确推算金额"]

    # 对比结论
    if fm == cm and abs(m["精确金额差异"]) < 1:
        compare = "与合同应收相符"
        if free:
            compare += f"（含免租{len(free)}个月）"
    elif fm == 0 and cm == 0:
        sy = str(m["录入起始"])[:4]
        compare = f"2025年均无应收（合同{sy}年才起租，相符）"
    else:
        parts = []
        if cm == 0 and fm > 0:
            parts.append(f"合同漏录2025年（财务收了{fm}个月）")
        elif fm == 0 and cm > 0:
            parts.append(f"财务无应收（合同应{cm}个月，可能免租/退租/漏记）")
        elif fm != cm:
            diff = fm - cm
            word = f"财务多收{diff}个月" if diff > 0 else f"财务少收{-diff}个月"
            parts.append(f"{word}（合同{cm}个月，财务{fm}个月）")
        if free:
            parts.append(f"含免租{len(free)}个月")
        if rent and abs(m["精确金额差异"]) >= 1 and cm > 0:
            ar = m.get("实际月租")
            if ar:
                parts.append(f"月租不同（合同{rent:g}元，财务{ar:g}元）")
        if not parts:
            parts.append(f"金额不同（合同{round(ctr_total, 2):g}元，财务{round(bill_total, 2):g}元）")
        compare = "；".join(parts)

    # 月租差异大（>50%），加醒目提醒
    ar = m.get("实际月租")
    if rent and ar and (rent / ar > 1.5 or ar / rent > 1.5):
        compare += "；⚠️月租差异大，请核对"

    return (f"【财务应收】{bill_desc}；合计{bill_total:g}元\n"
            f"【财务实收】{shi_desc}；合计{shi_total:g}元\n"
            f"【合同应收】{ctr_desc}；合计{ctr_total:g}元\n"
            f"【对比】{compare}")


def make_ub_conclusion(x):
    """财务有-合同无对应 的结论"""
    bill_desc = compress_months(x.get("财务各月应收金额"))
    bill_total = x.get("应收合计") or 0
    shi_desc = compress_months(x.get("财务各月实收金额"))
    shi_total = x.get("实收合计") or 0
    return (f"【财务应收】{bill_desc}；合计{bill_total:g}元\n"
            f"【财务实收】{shi_desc}；合计{shi_total:g}元\n"
            f"【合同应收】无对应\n"
            f"【对比】{x['原因']}")


def make_uc_conclusion(c):
    """合同有-财务无对应 的结论"""
    cmonths = set(c.get("合同推算月份") or [])
    rent = c["月租金"] or 0
    amounts = [rent if mo in cmonths else 0.0 for mo in range(1, 13)]
    ctr_desc = compress_months(amounts)
    ctr_total = round(rent * (c.get("合同推算月数") or 0), 2)
    return (f"【财务应收】无此房源应收\n"
            f"【财务实收】无\n"
            f"【合同应收】{ctr_desc}；合计{ctr_total:g}元\n"
            f"【对比】合同有、财务无对应")


def main():
    matched = json.load(open(T + r"\matched.json", encoding="utf-8"))
    for m in matched:
        bz = m["备注"] or ""
        free = free_months_2025(bz)
        m["免租月"] = sorted(free)
        base = m["合同推算月数"] if m["合同推算月数"] is not None else 0
        exact_cnt = max(0, base - len(free))
        m["精确推算月数"] = exact_cnt
        m["精确推算金额"] = round((m["月租金"] or 0) * exact_cnt, 2)
        m["精确月数差异"] = m["财务应收月数"] - exact_cnt
        m["精确金额差异"] = round(m["财务应收合计"] - m["精确推算金额"], 2)
        ar, ar_type = actual_rent(m)
        m["实际月租"] = ar
        m["实际月租类型"] = ar_type
        m["结论"] = make_conclusion(m)
    json.dump(matched, open(T + r"\matched.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 未匹配财务：生成结论
    ub = json.load(open(T + r"\unmatched_bill.json", encoding="utf-8"))
    for x in ub:
        x["结论"] = make_ub_conclusion(x)
    json.dump(ub, open(T + r"\unmatched_bill.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 未匹配合同：生成结论
    uc = json.load(open(T + r"\unmatched_ctr.json", encoding="utf-8"))
    for c in uc:
        c["结论"] = make_uc_conclusion(c)
    json.dump(uc, open(T + r"\unmatched_ctr.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 结论分布
    c = Counter()
    for m in matched:
        if m["结论"].startswith("与合同应收相符"):
            c["相符"] += 1
        elif "实际应收" in m["结论"]:
            c["月份差异"] += 1
        else:
            c["金额/其他"] += 1
    print("结论分布:", dict(c))
    print(f"匹配 {len(matched)}, 相符 {c.get('相符',0)}, 财务无对应 {len(ub)}, 合同无对应 {len(uc)}")
    # 打印几个结论样例
    print("\n=== 结论样例 ===")
    seen = set()
    for m in matched:
        key = m["结论"][:30]
        if key not in seen:
            seen.add(key)
            print(f"  {m['承租人'][:12]} | {m['结论'][:90]}")
        if len(seen) >= 6:
            break
    print("\n=== 财务无对应结论样例 ===")
    for x in ub[:3]:
        print(f"  {x['承租人'][:12]} | {x['结论'][:90]}")
    print("\n=== 合同无对应结论样例 ===")
    for c in uc[:3]:
        print(f"  {c['承租方'][:12]} | {c['结论'][:90]}")


if __name__ == "__main__":
    main()
