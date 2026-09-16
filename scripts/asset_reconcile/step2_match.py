# -*- coding: utf-8 -*-
"""
对账核心 v3 · 匹配(承租人 精确→模糊 + 面积 + 房源房号数字) + 整月粗算推算应收
产出 matched.json / unmatched_bill.json / unmatched_ctr.json
"""
import json
import re
from collections import defaultdict, Counter

from config import TMP

BILL_JSON = TMP + r"\bill.json"
CTR_JSON = TMP + r"\contracts.json"
OUT = TMP


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def norm_name(s):
    s = str(s).strip()
    s = re.sub(r"[（(].*?[）)]", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def fuzzy_key(s):
    """模糊名字键：去公司类型词 + 去地域前缀，用于识别改名/简写"""
    s = norm_name(s)
    for w in ["股份有限公司", "有限责任公司", "有限公司"]:
        s = s.replace(w, "")
    s = s.replace("股份", "").replace("责任", "").replace("有限", "").replace("公司", "")
    for pre in ["龙岩市", "龙岩", "福建", "福建省"]:
        if s.startswith(pre):
            s = s[len(pre):]
            break
    return s


def bill_area(r):
    mc = r["物业编码"]
    if not mc:
        return None
    m = re.search(r"面积[:：]\s*([\d.]+)", mc)
    if m:
        return float(m.group(1))
    m = re.search(r"([\d.]+)\s*㎡", mc)
    if m:
        return float(m.group(1))
    return None


def ctr_area(c):
    if c["面积"]:
        return c["面积"]
    fh = c["房号集合"]
    m = re.search(r"/([\d.]+)$", fh)
    if m:
        return float(m.group(1))
    return None


def bill_house(s):
    """财务房源 → (楼栋号, 房号, 楼层号)"""
    if not s:
        return None, None, None
    bld = None
    for pat in [r"(\d+)\s*#", r"标准厂房\s*(\d+)", r"(\d+)\s*幢", r"(\d+)\s*号楼", r"(\d+)\s*#厂房"]:
        m = re.search(pat, s)
        if m:
            bld = int(m.group(1))
            break
    # 房号：第一个 3 位数字（100~999，排除楼栋号）
    room = None
    for n in re.findall(r"\d+", s):
        ni = int(n)
        if 100 <= ni <= 999 and ni != bld:
            room = ni
            break
    floor = room // 100 if room else None
    if floor is None:
        cn = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        for k, v in cn.items():
            if k + "层" in s:
                floor = v
                break
    if floor is None:
        m = re.search(r"(\d+)\s*层", s)
        if m:
            floor = int(m.group(1))
    return bld, room, floor


def ctr_house(c):
    """合同 → (楼栋号, 房号, 楼层号)"""
    fh = c["房号集合"] or ""
    parts = fh.split("/")
    bld = None
    if parts and parts[0]:
        m = re.search(r"\d+", parts[0])
        if m:
            bld = int(m.group(0))
    floor = None
    if len(parts) >= 2:
        m = re.search(r"\d+", parts[1])
        if m:
            floor = int(m.group(0))
    # 房号：第 3 段里的 3 位数字（如 "203"、"南侧三层301"）
    room = None
    if len(parts) >= 3:
        m = re.search(r"(\d{3})", parts[2])
        if m:
            room = int(m.group(1))
    if floor is None and room:
        floor = room // 100
    return bld, room, floor


def parse_ym(v):
    if v is None:
        return None, None
    s = str(v)
    m = re.search(r"(\d{4})[-/.](\d{1,2})", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def covers_2025(c):
    sy, _ = parse_ym(c["录入起始"])
    ey, _ = parse_ym(c["解除时间"])
    if sy is None or ey is None:
        return False
    return not (sy > 2025 or ey < 2025)


def is_multi_row_house(c):
    fh = c["房号集合"]
    return bool(re.search(r"[、;，]", fh))


def calc_months(start_str, end_str):
    sy, sm = parse_ym(start_str)
    ey, em = parse_ym(end_str)
    if sy is None or ey is None:
        return None, []
    if sy > 2025 or ey < 2025:
        return 0, []
    ms = sm if sy == 2025 else 1
    me = em if ey == 2025 else 12
    if ms > me:
        return 0, []
    return len(list(range(ms, me + 1))), list(range(ms, me + 1))


def conf_level(rel, gap):
    if rel <= 0.03 or gap <= 3.0:
        return "高"
    if rel <= 0.15:
        return "中"
    return "低"


def main():
    bill = json.load(open(BILL_JSON, encoding="utf-8"))
    ctr = json.load(open(CTR_JSON, encoding="utf-8"))

    # 合同索引：精确名 + 模糊名
    cidx_exact = defaultdict(list)
    cidx_fuzzy = defaultdict(list)
    multi_contracts = []
    for c in ctr:
        if is_multi_row_house(c):
            multi_contracts.append(c)
            continue
        cidx_exact[norm_name(c["承租方"])].append(c)
        cidx_fuzzy[fuzzy_key(c["承租方"])].append(c)

    def candidates_for(r):
        """返回该财务房源的合同候选（精确名优先，其次模糊名）"""
        t = norm_name(r["承租人"])
        cs = cidx_exact.get(t)
        if cs:
            return cs, "精确"
        fk = fuzzy_key(r["承租人"])
        if not fk:
            return [], "无"
        cs = cidx_fuzzy.get(fk)
        if cs:
            return cs, "模糊"
        return [], "无"

    matched = []
    unmatched_bill = []
    used_ctr = set()

    for r in bill:
        cs, name_mode = candidates_for(r)
        avail = [c for c in cs if id(c) not in used_ctr]
        ba = bill_area(r)
        bf = bill_house(r["物业编码"]) or bill_house(r["承租单元"])

        if not cs:
            unmatched_bill.append({"rec": r, "原因": "承租人无同名合同(改名/漏录)", "候选": []})
            continue
        if ba is None and bf[0] is None and bf[1] is None:
            unmatched_bill.append({"rec": r, "原因": "财务无面积且无房号", "候选": []})
            continue

        # ① 房号精确匹配（楼栋 + 完整房号），最可靠
        if bf[0] is not None and bf[1] is not None:
            hit = False
            for c in avail:
                cf = ctr_house(c)
                if cf[0] is not None and cf[1] is not None and cf[0] == bf[0] and cf[1] == bf[1]:
                    used_ctr.add(id(c))
                    matched.append((r, c, "房号", None, name_mode))
                    hit = True
                    break
            if hit:
                continue

        # ② 面积匹配（优先覆盖2025 + 房号一致 + 面积最近；楼层冲突不匹配）
        if ba is not None:
            cands = []
            for c in avail:
                ca = ctr_area(c)
                if ca is None:
                    continue
                rel = abs(ca - ba) / ba
                gap = abs(ca - ba)
                cf = ctr_house(c)
                # 0=房号一致 1=不确定 2=楼层冲突
                if bf[0] and cf[0] and bf[1] and cf[1] and bf[0] == cf[0] and bf[1] == cf[1]:
                    hm = 0
                elif bf[0] and cf[0] and bf[2] and cf[2] and bf[0] == cf[0] and bf[2] != cf[2]:
                    hm = 2
                else:
                    hm = 1
                cands.append((rel, gap, hm, c))
            if cands:
                cands.sort(key=lambda x: (0 if covers_2025(x[3]) else 1, x[2], x[0], x[1]))
                rel, gap, hm, best_c = cands[0]
                if rel <= 0.30 and hm != 2:
                    used_ctr.add(id(best_c))
                    matched.append((r, best_c, conf_level(rel, gap), rel, name_mode))
                    continue

        # ③ 楼层匹配（房号提取不到时退而求其次）
        if bf[0] is not None and bf[2] is not None:
            for c in avail:
                cf = ctr_house(c)
                if cf[0] is not None and cf[2] is not None and cf[0] == bf[0] and cf[2] == bf[2]:
                    used_ctr.add(id(c))
                    matched.append((r, c, "楼层", None, name_mode))
                    break
            else:
                reason = "面积差大且房号未匹配" if ba is not None else "财务无面积且房号未匹配"
                unmatched_bill.append({"rec": r, "原因": reason, "候选": cs})
            continue

        reason = "面积差大(>30%)" if ba is not None else "财务无面积"
        unmatched_bill.append({"rec": r, "原因": reason, "候选": cs})

    unmatched_ctr = [c for c in ctr if id(c) not in used_ctr]

    result = []
    for r, c, lvl, rel, name_mode in matched:
        rj = num(r["应收合计"]) or 0.0
        r_months = r["财务计费月"]
        r_month_cnt = r["财务计费月数"]
        c_month_cnt, c_months = calc_months(c["录入起始"], c["解除时间"])
        rent = num(c["月租金"]) or 0.0
        calc_amt = round(rent * (c_month_cnt or 0), 2) if c_month_cnt else 0.0
        result.append({
            "idx": r["idx"], "excel_row": r["excel_row"], "sheet": r["sheet"],
            "板块": r["板块"], "承租人": r["承租人"], "物业编码": r["物业编码"],
            "承租单元": r["承租单元"],
            "财务应收月": r_months, "财务应收月数": r_month_cnt,
            "财务各月应收金额": r["应收月"],
            "财务各月实收金额": r["实收月"],
            "财务应收合计": rj, "财务实收合计": num(r["实收合计"]) or 0.0,
            "调整后欠款": num(r["调整后欠款"]) or 0.0,
            "合同编号": c["合同编号"], "合同承租方": c["承租方"],
            "项目名称": c["项目名称"], "房号集合": c["房号集合"],
            "合同面积": ctr_area(c), "财务面积": bill_area(r),
            "月租金": rent, "录入起始": str(c["录入起始"]), "解除时间": str(c["解除时间"]),
            "合同推算月数": c_month_cnt, "合同推算月份": c_months,
            "合同推算金额": calc_amt,
            "月数差异": (r_month_cnt - c_month_cnt) if c_month_cnt is not None else None,
            "金额差异": round(rj - calc_amt, 2),
            "面积相对差": round(rel, 3) if rel else None,
            "匹配置信度": lvl,
            "名字匹配": name_mode,
            "优惠免租": c["优惠免租"], "备注": c["备注"],
        })

    json.dump(result, open(OUT + r"\matched.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    ub = []
    for item in unmatched_bill:
        r = item["rec"]
        ub.append({
            "idx": r["idx"], "excel_row": r["excel_row"], "sheet": r["sheet"],
            "板块": r["板块"], "承租人": r["承租人"], "物业编码": r["物业编码"],
            "承租单元": r["承租单元"], "应收合计": num(r["应收合计"]),
            "实收合计": num(r["实收合计"]), "调整后欠款": num(r["调整后欠款"]),
            "财务计费月": r["财务计费月"], "财务计费月数": r["财务计费月数"],
            "财务各月应收金额": r["应收月"],
            "财务各月实收金额": r["实收月"],
            "原因": item["原因"],
            "候选": [{"房号集合": c["房号集合"], "面积": ctr_area(c), "月租金": c["月租金"],
                     "录入起始": str(c["录入起始"]), "解除时间": str(c["解除时间"]),
                     "备注": c["备注"][:40]} for c in item["候选"][:6]],
        })
    json.dump(ub, open(OUT + r"\unmatched_bill.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    uc = []
    for c in unmatched_ctr:
        c_month_cnt, c_months = calc_months(c["录入起始"], c["解除时间"])
        uc.append({"承租方": c["承租方"], "项目名称": c["项目名称"], "房号集合": c["房号集合"],
                   "面积": ctr_area(c), "月租金": c["月租金"], "录入起始": str(c["录入起始"]),
                   "解除时间": str(c["解除时间"]), "是否已结束": c["是否已结束"],
                   "合同推算月数": c_month_cnt, "合同推算月份": c_months,
                   "备注": c["备注"][:50]})
    json.dump(uc, open(OUT + r"\unmatched_ctr.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"财务房源: {len(bill)}, 合同行: {len(ctr)}")
    print(f"匹配成功: {len(matched)}")
    print("  置信度:", dict(Counter(m["匹配置信度"] for m in result)))
    print("  名字匹配:", dict(Counter(m["名字匹配"] for m in result)))
    print(f"未匹配财务: {len(unmatched_bill)}")
    print(f"未匹配合同: {len(unmatched_ctr)} (含多房号一行 {len(multi_contracts)})")


if __name__ == "__main__":
    main()
