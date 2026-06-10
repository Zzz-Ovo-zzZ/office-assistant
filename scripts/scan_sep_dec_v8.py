"""订婚吉日扫描 v8 — 放宽月忌 + 全量展示9-12月 + 聚焦9-10月5推荐"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from cnlunar import Lunar as CLunar
from lunar_python import Solar

FORBIDDEN_DZ = {'午', '未'}
MARRIAGE_KEYS = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']

YANG_GONG = [
    (1,13),(2,11),(3,9),(4,7),(5,5),(6,3),
    (7,1),(7,29),(8,27),(9,25),(10,23),(11,21),(12,19)
]

# 放假安排
HOLIDAYS = {
    datetime(2026,9,25): '中秋假期', datetime(2026,9,26): '中秋假期', datetime(2026,9,27): '中秋假期',
    **{datetime(2026,10,i): '国庆假期' for i in range(1,8)},
}
WORK_SATURDAYS = {datetime(2026,9,20): '国庆调班', datetime(2026,10,10): '国庆调班'}

def day_type(d):
    if d in HOLIDAYS: return HOLIDAYS[d], True
    if d in WORK_SATURDAYS: return '调休上班日', False
    if d.weekday() >= 5: return '周末', True
    return '工作日', False

def check_traditional(L, d):
    """返回 (级别, 理由)
    级别: hard=硬毙 | soft=警告(月忌) | None=无禁忌"""
    lm = L.lunarMonth; ld = L.lunarDay
    dz = L.day8Char[-1]; jc = getattr(L, 'today12DayOfficer', '')

    # ── 硬毙 ──
    if ld == 1:  return 'hard', '朔日(初一)'
    if ld == 15: return 'hard', '望日(十五)'
    if (lm, ld) in YANG_GONG: return 'hard', '杨公忌日'
    if dz == '午': return 'hard', '冲鼠(午日)'
    if dz == '未': return 'hard', '冲牛(未日)'
    if jc == '破': return 'hard', '破日'

    jq = getattr(L, 'todaySolarTerms', '') or ''
    for term in ['立春','立夏','立秋','立冬','春分','秋分','夏至','冬至']:
        if term in jq: return 'hard', f'{term}当天'

    # 四绝/四离
    s = Solar.fromYmd(d.year, d.month, d.day)
    l = s.getLunar()
    nj = l.getNextJieQi() if hasattr(l, 'getNextJieQi') else None
    if nj:
        nj_name = nj.getName() if hasattr(nj, 'getName') else str(nj)
        nj_solar = nj.getSolar() if hasattr(nj, 'getSolar') else None
        if nj_solar:
            nj_d = datetime(nj_solar.getYear(), nj_solar.getMonth(), nj_solar.getDay())
            if (nj_d - d).days <= 1:
                for term in ['立春','立夏','立秋','立冬']:
                    if term in nj_name: return 'hard', f'四绝日({term}前日)'
                for term in ['春分','秋分','夏至','冬至']:
                    if term in nj_name: return 'hard', f'四离日({term}前日)'

    # ── v8 软警告：月忌不再毙 ──
    if ld in (5, 14, 23): return 'soft', f'月忌(初{ld})'

    return None, None

def check_cnlunar(d):
    L = CLunar(datetime(d.year, d.month, d.day))
    good = [x.strip() for x in (L.goodThing or [])]
    bad = [x.strip() for x in (L.badThing or [])]
    return L, {
        'dz': L.day8Char[-1], 'ganzhi': L.day8Char,
        'lm': L.lunarMonth, 'ld': L.lunarDay,
        'all_yi': good, 'all_ji': bad,
        'marriage_yi': [x for x in good if any(k in x for k in MARRIAGE_KEYS)],
        'marriage_ji': [x for x in bad if any(k in x for k in MARRIAGE_KEYS)],
        'all_bad': '诸事不宜' in ' '.join(good),
        'jianchu': getattr(L, 'today12DayOfficer', '?'),
    }

def check_lp(d):
    s = Solar.fromYmd(d.year, d.month, d.day)
    l = s.getLunar()
    yi = list(l.getDayYi()); ji = list(l.getDayJi())
    return {
        'dz': l.getDayInGanZhiExact()[-1],
        'ganzhi': l.getDayInGanZhiExact(),
        'all_yi': yi, 'all_ji': ji,
        'marriage_yi': [x for x in yi if any(k in x for k in MARRIAGE_KEYS)],
        'marriage_ji': [x for x in ji if any(k in x for k in MARRIAGE_KEYS)],
    }

def judge(cn, lp, L, d):
    # 传统禁忌
    level, taboo = check_traditional(L, d)
    if level == 'hard':
        return 'hard_reject', taboo, cn['dz'], ''

    soft_tag = taboo if level == 'soft' else None

    dz = cn['dz']
    if dz != lp['dz']:
        return 'hard_reject', '日支双源不一致', dz, ''

    cn_yi = cn['marriage_yi']; cn_ji = cn['marriage_ji']
    lp_yi = lp['marriage_yi']; lp_ji = lp['marriage_ji']

    # 同源内部矛盾
    cn_self = cn_yi and cn_ji
    lp_self = lp_yi and lp_ji

    # 分级判定
    if cn['all_bad'] and lp_yi: return 'conflict', 'cn诸事不宜 vs lp宜嫁娶', dz, ''
    if cn_yi and lp_ji: return 'conflict', 'cn宜 vs lp忌', dz, ''
    if lp_yi and cn_ji: return 'conflict', 'lp宜 vs cn忌', dz, ''

    if cn_yi and lp_yi and not cn_ji and not lp_ji:
        return 'ideal', '双源一致宜嫁娶', dz, soft_tag
    if cn['all_bad']: return 'hard_reject', 'cn诸事不宜', dz, ''
    if cn_ji and lp_ji: return 'hard_reject', '双源一致忌嫁娶', dz, ''

    if cn_yi and not lp_yi and not lp_ji:
        return 'single_good', 'cn宜 lp无', dz, soft_tag
    if lp_yi and not cn_yi and not cn_ji:
        return 'single_good', 'lp宜 cn无', dz, soft_tag

    if cn_ji and not lp_ji and not lp_yi: return 'hard_reject', 'cn忌 lp无', dz, ''
    if lp_ji and not cn_yi and not cn_ji: return 'hard_reject', 'lp忌 cn无', dz, ''

    if not cn_yi and not cn_ji and not lp_yi and not lp_ji:
        return 'neutral', '双源无嫁娶条目', dz, soft_tag
    return 'neutral', '待查', dz, soft_tag

# ═══ 扫描 9-12月 ═══
results = []
d = datetime(2026, 9, 1)
while d <= datetime(2026, 12, 31):
    label, is_rest = day_type(d)
    if is_rest:
        L_obj, cn = check_cnlunar(d)
        lp = check_lp(d)
        verdict, reason, dz, detail = judge(cn, lp, L_obj, d)
        results.append((d, label, verdict, reason, dz, cn, lp, detail))
    d += timedelta(days=1)

# ═══ 输出 ═══
def w(s): return s
print('=' * 140)
print(w('订婚吉日扫描 v8  2026年9-12月  |  月忌降级为[!]警告不再毙 + 双源黄历'))
print('=' * 140)

MONTHS = {9:'9月',10:'10月',11:'11月',12:'12月'}
for m in [9, 10, 11, 12]:
    month_dates = [r for r in results if r[0].month == m]
    if not month_dates: continue
    print(f'\n{w("──")} {MONTHS[m]} {w("──")}')
    print(f'{"日期":<12} {"周":<3} {"类型":<10} {"农历":<6} {"日支":<4} {"判决":<24} {"详情"}')
    print('-' * 140)
    for d, label, v, reason, dz, cn, lp, flag in month_dates:
        wk = '一二三四五六日'[d.weekday()]
        nongli = f'{cn["lm"]}/{cn["ld"]}'
        icons = {'ideal': '** [IDEAL]', 'single_good': '++ [ OK  ]', 'neutral': '== [ NEUT ]',
                 'conflict': '?? [CONFL]', 'hard_reject': 'XX [ REJ  ]'}
        icon = icons[v]

        cn_yi_s = ','.join(cn['marriage_yi'][:3]) if cn['marriage_yi'] else ('X' if cn['all_bad'] else '-')
        cn_ji_s = ','.join(cn['marriage_ji'][:3]) if cn['marriage_ji'] else '-'
        lp_yi_s = ','.join(lp['marriage_yi'][:3]) if lp['marriage_yi'] else '-'
        lp_ji_s = ','.join(lp['marriage_ji'][:3]) if lp['marriage_ji'] else '-'

        detail_parts = []
        if flag: detail_parts.append(f'[!{flag}]')
        if reason: detail_parts.append(reason)

        # 黄历摘要
        if v in ('ideal', 'single_good'):
            detail_parts.append(f'cn宜={cn_yi_s} | lp宜={lp_yi_s}')

        print(f'{d.strftime("%Y-%m-%d"):<12} 周{wk:<2} {label:<10} {nongli:<6} {dz:<4} {icon:<24} {", ".join(detail_parts)}')

print()
print('=' * 140)
print('【汇总统计】')
print('=' * 140)

ideal = [r for r in results if r[2] == 'ideal']
single = [r for r in results if r[2] == 'single_good']
neutral = [r for r in results if r[2] == 'neutral']
conflict = [r for r in results if r[2] == 'conflict']
rejected = [r for r in results if r[2] == 'hard_reject']

print(f'\n** [IDEAL] 双源一致宜嫁娶: {len(ideal)}天')
for r in ideal:
    d=r[0]; flag=r[7]; wk='一二三四五六日'[d.weekday()]
    extra = f'  [! {flag}]' if flag else ''
    print(f'  {d.strftime("%Y-%m-%d")} 周{wk} {r[1]}{extra}')

print(f'\n++ [OK] 单源宜嫁娶: {len(single)}天')
for r in single:
    d=r[0]; flag=r[7]; wk='一二三四五六日'[d.weekday()]
    extra = f'  [! {flag}]' if flag else ''
    print(f'  {d.strftime("%Y-%m-%d")} 周{wk} {r[1]}{extra}  <- {r[3]}')

print(f'\n== [NEUT] 双源无条目: {len(neutral)}天')
for r in neutral:
    d=r[0]; flag=r[7]; wk='一二三四五六日'[d.weekday()]
    extra = f'  [! {flag}]' if flag else ''
    print(f'  {d.strftime("%Y-%m-%d")} 周{wk} {r[1]}{extra}')

print(f'\n?? [CONFL] 双源冲突: {len(conflict)}天')
for r in conflict:
    d=r[0]; cn=r[5]; lp=r[6]; wk='一二三四五六日'[d.weekday()]
    print(f'  {d.strftime("%Y-%m-%d")} 周{wk} {r[1]} -> {r[3]}')
    print(f'    cn: 宜={cn["marriage_yi"]} 忌={cn["marriage_ji"]} | lp: 宜={lp["marriage_yi"]} 忌={lp["marriage_ji"]}')

print(f'\nXX [REJ] 硬毙: {len(rejected)}天')
for r in rejected:
    d=r[0]; wk='一二三四五六日'[d.weekday()]
    print(f'  {d.strftime("%Y-%m-%d")} 周{wk} {r[1]} -> {r[3]}')

print(f'\n调休上班日(不列入): 9/20(日)国庆调班, 10/10(六)国庆调班')
print(f'\n[!] 标记 = 月忌警告（传统上不太理想，但非硬禁忌，用户自行判断）')
