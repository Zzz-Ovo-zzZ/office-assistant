"""订婚吉日双源交叉验证 v2 — 完整标注诸事不宜根因及冲突"""
from datetime import datetime, timedelta
from cnlunar import Lunar as CLunar
from lunar_python import Solar

FORBIDDEN_DZ = {'午', '未'}
MARRIAGE_KEYS = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']

HOLIDAYS = {
    datetime(2026,9,25): '中秋节',
    **{datetime(2026,10,i): '国庆节' for i in range(1,8)},
    datetime(2026,10,18): '重阳节',
}

def check_cnlunar(d):
    L = CLunar(datetime(d.year, d.month, d.day))
    dz = L.day8Char[-1]
    good = [x.strip() for x in (L.goodThing or [])]
    bad = [x.strip() for x in (L.badThing or [])]
    return {
        'dz': dz,
        'ganzhi': L.day8Char,
        'all_yi': good,
        'all_ji': bad,
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
    yi = list(l.getDayYi())
    ji = list(l.getDayJi())
    return {
        'dz': dz,
        'ganzhi': l.getDayInGanZhiExact(),
        'all_yi': yi,
        'all_ji': ji,
        'marriage_yi': [x for x in yi if any(k in x for k in MARRIAGE_KEYS)],
        'marriage_ji': [x for x in ji if any(k in x for k in MARRIAGE_KEYS)],
    }

def judge(cn, lp):
    dz = cn['dz']
    if dz != lp['dz']:
        return 0, '⚠️ 日支双源不一致', dz, 'cn='+dz+' lp='+lp['dz']
    if dz in FORBIDDEN_DZ:
        return 0, f'冲{"鼠" if dz=="午" else "牛"}', dz, '生肖冲煞'

    cn_yi = cn['marriage_yi']; cn_ji = cn['marriage_ji']
    lp_yi = lp['marriage_yi']; lp_ji = lp['marriage_ji']
    cn_all_bad = cn['all_bad']

    # ── 关键：诸事不宜 vs lp宜嫁娶 → 冲突 ──
    if cn_all_bad and lp_yi:
        return 3, '⚠️ cn诸事不宜 vs lp宜嫁娶 冲突', dz, cn['level'][:60]

    # 双源一致宜
    if cn_yi and lp_yi and not cn_ji and not lp_ji:
        return 1, '🟢 双源一致宜嫁娶', dz, ''
    # cn诸事不宜 + lp无嫁娶 → 双源均不可（不是冲突）
    if cn_all_bad:
        return 0, '🔴 cn诸事不宜', dz, cn['level'][:60]
    # 双源一致忌
    if cn_ji and lp_ji:
        return 0, '🔴 双源一致忌嫁娶', dz, ''
    # 一源宜一源忌 → 冲突
    if cn_yi and lp_ji:
        return 3, '⚠️ cn宜 vs lp忌 冲突', dz, ''
    if lp_yi and cn_ji:
        return 3, '⚠️ lp宜 vs cn忌 冲突', dz, ''
    # 单源宜，另一源无
    if cn_yi and not lp_yi and not lp_ji:
        return 1, '🟢 cn宜 lp无', dz, ''
    if lp_yi and not cn_yi and not cn_ji:
        return 1, '🟢 lp宜 cn无', dz, ''
    # 单源忌，另一源无
    if cn_ji and not lp_ji and not lp_yi:
        return 0, '🔴 cn忌 lp无', dz, ''
    if lp_ji and not cn_yi and not cn_yi:
        return 0, '🔴 lp忌 cn无', dz, ''
    # 双源均无
    if not cn_yi and not cn_ji and not lp_yi and not lp_ji:
        return 2, '🟡 双源无嫁娶条目', dz, ''

    return 2, '🟡 待查', dz, ''

results = []
d = datetime(2026, 9, 1)
while d <= datetime(2026, 12, 31):
    h = None
    if d in HOLIDAYS: h = HOLIDAYS[d]
    elif d.weekday() >= 5: h = '周末'
    if h:
        cn = check_cnlunar(d)
        lp = check_lp(d)
        verdict, reason, dz, detail = judge(cn, lp)
        results.append((d, h, verdict, reason, dz, cn, lp, detail))
    d += timedelta(days=1)

# ─── 输出 ───
print('=' * 145)
print('订婚吉日扫描  2026年9-12月  |  双源交叉验证 v2')
print('cnlunar(OPN48 · 协纪辨方书) + lunar-python(6tail)')
print('=' * 145)

MONTHS = {9:'9月',10:'10月',11:'11月',12:'12月'}
by_month = {}
for r in results: by_month.setdefault(r[0].month, []).append(r)

for m in sorted(by_month):
    print(f'\n── {MONTHS[m]} ──')
    hdr = f'{"日期":<12} {"周":<3} {"节日":<8} {"日支":<4} {"cn宜":<14} {"cn忌":<14} {"lp宜":<14} {"lp忌":<14} {"判决"}'
    print(hdr)
    print('-' * 135)
    for d, h, v, reason, dz, cn, lp, detail in by_month[m]:
        wk = '一二三四五六日'[d.weekday()]
        cn_yi_s = ','.join(cn['marriage_yi'][:3]) if cn['marriage_yi'] else ('诸事不宜' if cn['all_bad'] else '-')
        cn_ji_s = ','.join(cn['marriage_ji'][:3]) if cn['marriage_ji'] else '-'
        lp_yi_s = ','.join(lp['marriage_yi'][:3]) if lp['marriage_yi'] else '-'
        lp_ji_s = ','.join(lp['marriage_ji'][:3]) if lp['marriage_ji'] else '-'
        icon = {1:'🔥', 2:'🟡', 3:'⚠️', 0:'❌'}[v]
        extra = f' | {detail}' if detail else ''
        print(f'{d.strftime("%Y-%m-%d"):<12} 周{wk:<2} {h:<8} {dz:<4} {cn_yi_s:<14} {cn_ji_s:<14} {lp_yi_s:<14} {lp_ji_s:<14} {icon} {reason}{extra}')

# ─── 汇总 ───
print('\n' + '=' * 145)
print('汇总')
print('=' * 145)

good = [r for r in results if r[2]==1]
neut = [r for r in results if r[2]==2]
conflict = [r for r in results if r[2]==3]
bad = [r for r in results if r[2]==0]

print(f'\n🔥 宜嫁娶: {len(good)} 天')
for r in good:
    d=r[0]; print(f'   {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]:<2} {r[1]:<8} {r[4]} {r[3]}')

print(f'\n⚠️ 双源冲突: {len(conflict)} 天')
for r in conflict:
    d=r[0]; cn=r[5]; lp=r[6]
    print(f'   {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]:<2} {r[1]:<8} {r[4]} {r[3]}')
    print(f'      cn: 宜={cn["marriage_yi"]} 忌={cn["marriage_ji"]} | lp: 宜={lp["marriage_yi"]} 忌={lp["marriage_ji"]}')

print(f'\n🟡 双源无条目: {len(neut)} 天')
for r in neut:
    d=r[0]; print(f'   {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]} {r[1]}')

print(f'\n❌ 不可用: {len(bad)} 天')
