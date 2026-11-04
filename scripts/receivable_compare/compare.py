# -*- coding: utf-8 -*-
"""
系统应收 vs 整理应收 · 25年1-12月 对比表

数据源：
  1. 系统数据 25年系统应收数据_2026.11.3.xlsx —— sheet1 逐条应收流水
     按「对方名称」汇总「应收金额」(应缴总额, 含税)
  2. 整理数据 25年应收整理(分公司）_2026.11.3.xlsx —— Sheet1 汇总表
     同一「承租人」多行合并求和「1-12月应收」

口径：系统侧=应收金额(应缴总额)；对比=全年总额；匹配=精确→模糊
产出：对比 Excel（汇总 / 对比明细 / 仅系统有 / 仅整理有 4 个 sheet）
"""
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.project_config import path_of, require  # noqa: E402

# ── 数据源（路径见 config.local.json，缺失时给中文提示）──
SYS = str(require(path_of("receivable_sys"), "系统应收数据（25年）"))
ORG = str(require(path_of("receivable_org"), "整理应收数据（25年）"))

OUT_DIR = str(path_of("receivable_out"))
os.makedirs(OUT_DIR, exist_ok=True)
DATE = "2026.11.3"
OUT_EXCEL = os.path.join(OUT_DIR, f"置业_系统应收vs整理应收_对比_{DATE}.xlsx")

# 差异判定容差（元）
EPS = 0.005


def num(v):
    """金额解析：去逗号；None/--/空 → None"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    if s in ("", "--", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def norm_name(s):
    """去括号内容 + 去空格（用于精确匹配，兼容「带括号地名」写法差异）"""
    s = str(s).strip()
    s = re.sub(r"[（(].*?[）)]", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def fuzzy_key(s):
    """模糊名键：去公司类型词 + 去地域前缀，识别简称/全称/改名"""
    s = norm_name(s)
    for w in ["股份有限公司", "有限责任公司", "有限公司"]:
        s = s.replace(w, "")
    s = s.replace("股份", "").replace("责任", "").replace("有限", "").replace("公司", "")
    for pre in ["龙岩市", "福建省", "龙岩", "福建"]:
        if s.startswith(pre):
            s = s[len(pre):]
            break
    return s


def levenshtein(a, b):
    """编辑距离（中文字符级）"""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


# ── 读取 ────────────────────────────────────────────────
def load_sys():
    """系统 sheet1 → {对方名称: 应收金额合计}"""
    wb = openpyxl.load_workbook(SYS, read_only=True, data_only=True)
    ws = wb["sheet1"]
    out = defaultdict(float)
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:  # 表头
            continue
        name = str(row[0]).strip() if row[0] is not None else ""
        if not name or name == "总计":
            continue
        v = num(row[8])
        out[name] += (v or 0.0)
    wb.close()
    return dict(out)


def load_org():
    """整理 Sheet1 → {承租人: {金额, 所属公司集合, 备注}}，同名多行合并"""
    wb = openpyxl.load_workbook(ORG, read_only=True, data_only=True)
    ws = wb["Sheet1"]
    acc = {}
    order = []  # 保序
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        name = str(row[1]).strip() if row[1] is not None else ""
        if not name or name == "总计":
            continue
        comp = str(row[0]).strip() if row[0] is not None else ""
        amt = num(row[2]) or 0.0
        note = str(row[3]).strip() if row[3] is not None else ""
        if name not in acc:
            acc[name] = {"金额": 0.0, "公司": [], "备注": []}
            order.append(name)
        acc[name]["金额"] += amt
        if comp and comp not in acc[name]["公司"]:
            acc[name]["公司"].append(comp)
        if note and note not in acc[name]["备注"]:
            acc[name]["备注"].append(note)
    wb.close()
    out = {}
    for n in order:
        d = acc[n]
        out[n] = {
            "金额": round(d["金额"], 2),
            "公司": "/".join(d["公司"]),
            "备注": "；".join(d["备注"]),
        }
    return out


def match(sys_data, org_data):
    """精确→模糊→近似 一对一匹配，返回 (对比明细, 仅系统, 仅整理)"""
    exact_idx = defaultdict(list)
    fuzzy_idx = defaultdict(list)
    org_names = list(org_data.keys())
    org_norm = {n: norm_name(n) for n in org_names}
    org_fuzzy = {n: fuzzy_key(n) for n in org_names}
    for n in org_names:
        exact_idx[norm_name(n)].append(n)
        fk = fuzzy_key(n)
        if fk:
            fuzzy_idx[fk].append(n)

    matched = []   # (系统名, 整理名, 系统金额, 匹配方式)
    only_sys = []  # (系统名, 金额, 候选说明)
    used = set()

    for name, amt in sys_data.items():
        nm = norm_name(name)
        fk = fuzzy_key(name)
        # ① 精确
        cands = [n for n in exact_idx.get(nm, []) if n not in used]
        if cands:
            pick = cands[0]
            used.add(pick)
            matched.append((name, pick, amt, "精确"))
            continue
        # ② 模糊（fuzzy_key 相等，唯一候选）
        cands = [n for n in fuzzy_idx.get(fk, []) if n not in used] if fk else []
        if len(cands) == 1:
            pick = cands[0]
            used.add(pick)
            matched.append((name, pick, amt, "模糊"))
            continue
        # ③ 近似-包含（fuzzy_key 互为子串，唯一候选，如「海德馨汽车」⊂「泰豪海德馨汽车」）
        if fk:
            sub_cands = [n for n in org_names
                         if n not in used and org_fuzzy[n] and (fk in org_fuzzy[n] or org_fuzzy[n] in fk)]
            if len(sub_cands) == 1:
                pick = sub_cands[0]
                used.add(pick)
                matched.append((name, pick, amt, "近似"))
                continue
        # ④ 近似-编辑距离（≤1 字，且名称≥6字，唯一候选，如「武勘」vs「武堪」）
        if len(nm) >= 6:
            edit_cands = [n for n in org_names
                          if n not in used and levenshtein(nm, org_norm[n]) <= 1]
            if len(edit_cands) == 1:
                pick = edit_cands[0]
                used.add(pick)
                matched.append((name, pick, amt, "近似"))
                continue
        # 未匹配，记录候选提示
        hint = ""
        if fk:
            multi = [n for n in fuzzy_idx.get(fk, []) if n not in used]
            if len(multi) > 1:
                hint = f"模糊匹配有 {len(multi)} 个候选：{'、'.join(multi[:4])}"
        only_sys.append((name, amt, hint))

    only_org = [(n, org_data[n]) for n in org_data if n not in used]
    return matched, only_sys, only_org


# ── 生成 Excel ──────────────────────────────────────────
HDR_FILL = PatternFill("solid", fgColor="4472C4")
HDR_FONT = Font(bold=True, color="FFFFFF")
FILL_OK = PatternFill("solid", fgColor="E2EFDA")   # 绿：相符
FILL_DIFF = PatternFill("solid", fgColor="FFE699")  # 黄：有差异
FILL_SYS = PatternFill("solid", fgColor="FCE4D6")   # 橙：仅系统有
FILL_ORG = PatternFill("solid", fgColor="DDEBF7")   # 蓝：仅整理有
WRAP = Alignment(wrap_text=True, vertical="top")
RIGHT = Alignment(horizontal="right")


def style_header(ws, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")


def auto_width(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def build_excel(matched, only_sys, only_org, sys_data, org_data):
    wb = Workbook()

    def r2(v):
        return round(v, 2)

    sys_total = round(sum(sys_data.values()), 2)
    org_total = round(sum(d["金额"] for d in org_data.values()), 2)

    # 对比明细按差异绝对值降序
    rows = []
    for sname, oname, samt, mode in matched:
        oamt = org_data[oname]["金额"]
        diff = r2(samt - oamt)
        if abs(diff) < EPS:
            concl = "相符"
        elif diff > 0:
            concl = f"系统多 {diff:.2f}"
        else:
            concl = f"系统少 {abs(diff):.2f}"
        rows.append([sname, org_data[oname]["公司"], r2(samt), oamt, diff,
                     concl, mode, org_data[oname]["备注"]])
    rows.sort(key=lambda x: -abs(x[4]))

    # ── Sheet1 汇总 ──
    ws = wb.active
    ws.title = "汇总"
    n_ok = sum(1 for r in rows if r[5] == "相符")
    n_more = sum(1 for r in rows if r[5].startswith("系统多"))
    n_less = sum(1 for r in rows if r[5].startswith("系统少"))
    diff_total = round(sum(r[4] for r in rows), 2)
    summary = [
        ["一、总体", ""],
        ["系统企业数", len(sys_data)],
        ["系统应收合计(元)", sys_total],
        ["整理企业数", len(org_data)],
        ["整理应收合计(元)", org_total],
        ["匹配成功(交集)", len(rows)],
        ["仅系统有", len(only_sys)],
        ["仅整理有", len(only_org)],
        ["差异总额(系统-整理, 交集部分)", diff_total],
        [],
        ["二、名称匹配方式", ""],
        [f"  精确", sum(1 for r in rows if r[6] == "精确")],
        [f"  模糊", sum(1 for r in rows if r[6] == "模糊")],
        [f"  近似(同名变体)", sum(1 for r in rows if r[6] == "近似")],
        [],
        ["三、对比结论", ""],
        [f"  相符", n_ok],
        [f"  系统多", n_more],
        [f"  系统少", n_less],
    ]
    for r in summary:
        ws.append(r)
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 18
    for i in range(2, len(summary) + 1):
        row = summary[i - 1]
        if len(row) >= 2 and isinstance(row[1], (int, float)):
            ws.cell(row=i, column=2).alignment = RIGHT

    # ── Sheet2 对比明细 ──
    ws2 = wb.create_sheet("对比明细")
    hdr = ["企业名称", "所属公司", "系统应收(元)", "整理应收(元)", "差异(元)",
           "结论", "匹配方式", "整理备注"]
    ws2.append(hdr)
    style_header(ws2, len(hdr))
    for r in rows:
        ws2.append(r)
    # 着色 + 金额右对齐
    for i, r in enumerate(rows, start=2):
        ws2.cell(row=i, column=6).fill = FILL_OK if r[5] == "相符" else FILL_DIFF
        ws2.cell(row=i, column=8).alignment = WRAP
        for c in (3, 4, 5):
            ws2.cell(row=i, column=c).alignment = RIGHT
    auto_width(ws2, [30, 14, 14, 14, 14, 14, 9, 40])
    ws2.freeze_panes = "A2"
    ws2.auto_filter.ref = f"A1:H{len(rows) + 1}"

    # ── Sheet3 仅系统有 ──
    ws3 = wb.create_sheet("仅系统有")
    hdr3 = ["企业名称", "系统应收(元)", "备注"]
    ws3.append(hdr3)
    style_header(ws3, len(hdr3))
    only_sys.sort(key=lambda x: -(x[1] or 0))
    for r in only_sys:
        ws3.append(list(r))
    for i, r in enumerate(only_sys, start=2):
        ws3.cell(row=i, column=1).fill = FILL_SYS
        ws3.cell(row=i, column=2).alignment = RIGHT
        ws3.cell(row=i, column=3).alignment = WRAP
    auto_width(ws3, [30, 14, 50])
    ws3.freeze_panes = "A2"

    # ── Sheet4 仅整理有 ──
    ws4 = wb.create_sheet("仅整理有")
    hdr4 = ["企业名称", "所属公司", "整理应收(元)", "备注"]
    ws4.append(hdr4)
    style_header(ws4, len(hdr4))
    only_org.sort(key=lambda x: -(x[1]["金额"] or 0))
    for n, d in only_org:
        ws4.append([n, d["公司"], d["金额"], d["备注"]])
    for i, (n, d) in enumerate(only_org, start=2):
        ws4.cell(row=i, column=1).fill = FILL_ORG
        ws4.cell(row=i, column=3).alignment = RIGHT
        ws4.cell(row=i, column=4).alignment = WRAP
    auto_width(ws4, [30, 14, 14, 50])
    ws4.freeze_panes = "A2"

    wb.save(OUT_EXCEL)
    return {
        "sys_total": sys_total, "org_total": org_total,
        "n_matched": len(rows), "n_only_sys": len(only_sys), "n_only_org": len(only_org),
        "diff_total": diff_total,
    }


def main():
    sys_data = load_sys()
    org_data = load_org()
    matched, only_sys, only_org = match(sys_data, org_data)

    print(f"系统企业数: {len(sys_data)}, 应收合计: {round(sum(sys_data.values()), 2)}")
    print(f"整理企业数: {len(org_data)}, 应收合计: {round(sum(d['金额'] for d in org_data.values()), 2)}")
    print(f"匹配成功: {len(matched)}  仅系统: {len(only_sys)}  仅整理: {len(only_org)}")
    print(f"匹配方式:", dict(Counter(m[3] for m in matched)))

    r = build_excel(matched, only_sys, only_org, sys_data, org_data)

    # ── 守恒校验 ──
    matched_sys_sum = round(sum(m[2] for m in matched), 2)
    only_sys_sum = round(sum(x[1] for x in only_sys), 2)
    matched_org_sum = round(sum(org_data[m[1]]["金额"] for m in matched), 2)
    only_org_sum = round(sum(d["金额"] for n, d in only_org), 2)
    print("\n── 金额守恒校验 ──")
    print(f"系统侧: 匹配 {matched_sys_sum} + 仅系统 {only_sys_sum} = {round(matched_sys_sum + only_sys_sum, 2)} (应≈{r['sys_total']})")
    print(f"整理侧: 匹配 {matched_org_sum} + 仅整理 {only_org_sum} = {round(matched_org_sum + only_org_sum, 2)} (应≈{r['org_total']})")
    print(f"数量守恒: 交集{r['n_matched']}+仅系统{r['n_only_sys']}={r['n_matched']+r['n_only_sys']}(应={len(sys_data)}); "
          f"交集{r['n_matched']}+仅整理{r['n_only_org']}={r['n_matched']+r['n_only_org']}(应={len(org_data)})")
    print(f"差异总额(系统-整理, 交集): {r['diff_total']}")
    print(f"\n已生成: {OUT_EXCEL}")


if __name__ == "__main__":
    main()
