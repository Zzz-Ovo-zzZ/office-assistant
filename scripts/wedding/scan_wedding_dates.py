"""订婚吉日双源交叉验证 v3 — 加入国务院2026放假调休"""
from datetime import datetime, timedelta
from cnlunar import Lunar as CLunar
from lunar_python import Solar

FORBIDDEN_DZ = {'午', '未'}
MARRIAGE_KEYS = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']

# ═══ 17类传统禁忌 —— 在黄历之前先毙 ═══
YANG_GONG = [
    (1,13),(2,11),(3,9),(4,7),(5,5),(6,3),
    (7,1),(7,29),(8,27),(9,25),(10,23),(11,21),(12,19)
]

def check_traditional_forbidden(L, d):
    """17类传统禁忌 + 四绝/四离/破日 + 节气当天。命中即返回失败理由"""
    lm = L.lunarMonth
    ld = L.lunarDay
    dz = L.day8Char[-1]
    jc = getattr(L, 'today12DayOfficer', '')

    if ld == 1:  return '朔日(初一)'
    if ld == 15: return '望日(十五)'
    if ld in (5, 14, 23): return f'月忌(初{ld})'
    if (lm, ld) in YANG_GONG: return '杨公忌日'
    if dz == '午': return '冲鼠(午日)'
    if dz == '未': return '冲牛(未日)'
    if jc == '破': return '破日'

    # 四绝日/四离日/节气当天
    jq = getattr(L, 'todaySolarTerms', '') or ''
    if '立春' in jq: return '立春当天'
    if '立夏' in jq: return '立夏当天'
    if '立秋' in jq: return '立秋当天'
    if '立冬' in jq: return '立冬当天'
    if '春分' in jq: return '春分当天'
    if '秋分' in jq: return '秋分当天'
    if '夏至' in jq: return '夏至当天'
    if '冬至' in jq: return '冬至当天'

    # 四绝 = 立春/立夏/立秋/立冬前一日, 四离 = 二分二至前一日
    s = Solar.fromYmd(d.year, d.month, d.day)
    l = s.getLunar()
    next_jq = l.getNextJieQi() if hasattr(l, 'getNextJieQi') else None
    if next_jq:
        nj_name = next_jq.getName() if hasattr(next_jq, 'getName') else str(next_jq)
        nj_solar = next_jq.getSolar() if hasattr(next_jq, 'getSolar') else None
        if nj_solar:
            nj_d = datetime(nj_solar.getYear(), nj_solar.getMonth(), nj_solar.getDay())
            if (nj_d - d).days <= 1:  # 次日就是节气
                for term in ['立春','立夏','立秋','立冬']:
                    if term in nj_name:
                        return f'四绝日({term}前日)'
                for term in ['春分','秋分','夏至','冬至']:
                    if term in nj_name:
                        return f'四离日({term}前日)'

    return None

# ═══ 国务院2026放假调休（关键数据） ═══
HOLIDAYS = {
    # 中秋假期 9/25(五) - 9/27(日) 3天
    datetime(2026,9,25): ('中秋节假期', True),
    datetime(2026,9,26): ('中秋节假期', True),
    datetime(2026,9,27): ('中秋节假期', True),
    # 国庆假期 10/1(四) - 10/7(三) 7天
    **{datetime(2026,10,i): ('国庆假期', True) for i in range(1,8)},
}

# 调休上班日 — 虽然日历上是周末但实际要上班
WORK_SATURDAYS = {
    datetime(2026,9,20): '国庆调班',
    datetime(2026,10,10): '国庆调班',
}

def day_type(d):
    """判断日期的实际类型（考虑调休）"""
    if d in HOLIDAYS:
        return HOLIDAYS[d][0], HOLIDAYS[d][1]
    if d in WORK_SATURDAYS:
        return '调休上班日', False
    if d.weekday() >= 5:
        return '周末', True
    return '工作日', False

def check_cnlunar(d):
    L = CLunar(datetime(d.year, d.month, d.day))
    dz = L.day8Char[-1]
    good = [x.strip() for x in (L.goodThing or [])]
    bad = [x.strip() for x in (L.badThing or [])]
    return L, {
        'dz': dz, 'ganzhi': L.day8Char,
        'all_yi': good, 'all_ji': bad,
        'marriage_yi': [x for x in good if any(k in x for k in MARRIAGE_KEYS)],
        'marriage_ji': [x for x in bad if any(k in x for k in MARRIAGE_KEYS)],
        'all_bad': '诸事不宜' in ' '.join(good),
        'jianchu': getattr(L, 'today12DayOfficer', '?'),
        'level': getattr(L, 'todayLevelName', '?'),
    }

def check_lp(d):
    s = Solar.fromYmd(d.year, d.month, d.day)
    l = s.getLunar()
    dz = l.getDayInGanZhiExact()[-1]
    yi = list(l.getDayYi()); ji = list(l.getDayJi())
    return {
        'dz': dz, 'ganzhi': l.getDayInGanZhiExact(),
        'all_yi': yi, 'all_ji': ji,
        'marriage_yi': [x for x in yi if any(k in x for k in MARRIAGE_KEYS)],
        'marriage_ji': [x for x in ji if any(k in x for k in MARRIAGE_KEYS)],
    }

def judge(cn, lp, L, d):
    # ── 第零关：传统禁忌 ──
    taboo = check_traditional_forbidden(L, d)
    if taboo:
        return 0, f'🔴 传统禁忌: {taboo}', cn['dz'], taboo

    dz = cn['dz']
    if dz != lp['dz']: return 0, '日支双源不一致', dz, 'cn='+dz+' lp='+lp['dz']
    if dz in FORBIDDEN_DZ: return 0, f'冲{"鼠" if dz=="午" else "牛"}', dz, '生肖冲煞'

    cn_yi = cn['marriage_yi']; cn_ji = cn['marriage_ji']
    lp_yi = lp['marriage_yi']; lp_ji = lp['marriage_ji']

    # 冲突：cn诸事不宜 vs lp宜嫁娶
    if cn['all_bad'] and lp_yi:
        return 3, '⚠️ cn诸事不宜 vs lp宜嫁娶 冲突', dz, cn['level'][:60]
    # 双源一致宜
    if cn_yi and lp_yi and not cn_ji and not lp_ji:
        return 1, '🟢 双源一致宜嫁娶', dz, ''
    # cn诸事不宜 + lp无嫁娶
    if cn['all_bad']:
        return 0, '🔴 cn诸事不宜', dz, cn['level'][:60]
    # 双源一致忌
    if cn_ji and lp_ji:
        return 0, '🔴 双源一致忌嫁娶', dz, ''
    # 一源宜一源忌
    if cn_yi and lp_ji: return 3, '⚠️ cn宜 vs lp忌 冲突', dz, ''
    if lp_yi and cn_ji: return 3, '⚠️ lp宜 vs cn忌 冲突', dz, ''
    # 单源宜
    if cn_yi and not lp_yi and not lp_ji: return 1, '🟢 cn宜 lp无', dz, ''
    if lp_yi and not cn_yi and not cn_ji: return 1, '🟢 lp宜 cn无', dz, ''
    # 单源忌
    if cn_ji and not lp_ji and not lp_yi: return 0, '🔴 cn忌 lp无', dz, ''
    if lp_ji and not cn_yi and not cn_ji: return 0, '🔴 lp忌 cn无', dz, ''
    # 双源均无
    if not cn_yi and not cn_ji and not lp_yi and not lp_ji:
        return 2, '🟡 双源无嫁娶条目', dz, ''
    return 2, '🟡 待查', dz, ''

# ─── 扫描：只收录实际可休日（假日+周末，不含调休上班日） ───
results = []
d = datetime(2026, 9, 1)
while d <= datetime(2026, 12, 31):
    label, is_rest = day_type(d)
    if is_rest:  # 只扫实际休息日
        L_obj, cn = check_cnlunar(d)
        lp = check_lp(d)
        verdict, reason, dz, detail = judge(cn, lp, L_obj, d)
        results.append((d, label, verdict, reason, dz, cn, lp, detail))
    d += timedelta(days=1)

# ─── 输出 ───
print('=' * 155)
print('订婚吉日扫描  2026年9-12月  |  v3 国务院放假调休 + 双源黄历')
print('=' * 155)

MONTHS = {9:'9月',10:'10月',11:'11月',12:'12月'}
by_month = {}
for r in results: by_month.setdefault(r[0].month, []).append(r)

for m in sorted(by_month):
    print(f'\n── {MONTHS[m]} ──')
    hdr = f'{"日期":<12} {"周":<3} {"类型":<10} {"日支":<4} {"cn嫁娶宜":<14} {"cn嫁娶忌":<14} {"lp嫁娶宜":<14} {"lp嫁娶忌":<14} {"判决"}'
    print(hdr); print('-' * 145)
    for d, label, v, reason, dz, cn, lp, detail in by_month[m]:
        wk = '一二三四五六日'[d.weekday()]
        cn_yi_s = ','.join(cn['marriage_yi'][:3]) if cn['marriage_yi'] else ('诸事不宜' if cn['all_bad'] else '-')
        cn_ji_s = ','.join(cn['marriage_ji'][:3]) if cn['marriage_ji'] else '-'
        lp_yi_s = ','.join(lp['marriage_yi'][:3]) if lp['marriage_yi'] else '-'
        lp_ji_s = ','.join(lp['marriage_ji'][:3]) if lp['marriage_ji'] else '-'
        icon = {1:'🔥', 2:'🟡', 3:'⚠️', 0:'❌'}[v]
        extra = f' | {detail}' if detail else ''
        print(f'{d.strftime("%Y-%m-%d"):<12} 周{wk:<2} {label:<10} {dz:<4} {cn_yi_s:<14} {cn_ji_s:<14} {lp_yi_s:<14} {lp_ji_s:<14} {icon} {reason}{extra}')

# ─── 汇总 ───
print('\n' + '=' * 155)
print('汇总（仅含实际休息日：节假日+周末，已排除调休上班日）')
print('=' * 155)

good = [r for r in results if r[2]==1]
neut = [r for r in results if r[2]==2]
conflict = [r for r in results if r[2]==3]
bad = [r for r in results if r[2]==0]

print(f'\n🔥 宜嫁娶: {len(good)} 天')
for r in good:
    d=r[0]; print(f'   {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]:<2} {r[1]:<10} {r[4]} {r[3]}')

print(f'\n⚠️ 双源冲突: {len(conflict)} 天')
for r in conflict:
    d=r[0]; cn=r[5]; lp=r[6]
    print(f'   {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]:<2} {r[1]:<10} {r[4]} {r[3]}')
    print(f'      cn: 宜={cn["marriage_yi"]} 忌={cn["marriage_ji"]} | lp: 宜={lp["marriage_yi"]} 忌={lp["marriage_ji"]}')

print(f'\n🟡 双源无条目: {len(neut)} 天')
for r in neut:
    d=r[0]; print(f'   {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]} {r[1]}')

print(f'\n❌ 不可用: {len(bad)} 天')
print(f'\n📌 两个调休上班日（不列入扫描）: 9/20(日)·国庆调班 / 10/10(六)·国庆调班')
