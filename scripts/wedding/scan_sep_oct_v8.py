"""订婚吉日扫描 v8 — 放宽月忌 + 聚焦9-10月 + 输出5推荐"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from cnlunar import Lunar as CLunar
from lunar_python import Solar

FORBIDDEN_DZ = {'午', '未'}  # 午冲鼠(男方), 未冲牛(女方)
MARRIAGE_KEYS = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']

# ═══ 传统禁忌 ═══
YANG_GONG = [
    (1,13),(2,11),(3,9),(4,7),(5,5),(6,3),
    (7,1),(7,29),(8,27),(9,25),(10,23),(11,21),(12,19)
]

# ═══ 2026放假 ═══
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
    """v8: 月忌降级为警告，其他硬禁忌保留"""
    lm = L.lunarMonth; ld = L.lunarDay
    dz = L.day8Char[-1]; jc = getattr(L, 'today12DayOfficer', '')

    # ── 硬毙（不可商量）──
    if ld == 1:  return 'hard', '朔日(初一)'
    if ld == 15: return 'hard', '望日(十五)'
    if (lm, ld) in YANG_GONG: return 'hard', '杨公忌日'
    if dz == '午': return 'hard', '冲鼠(午日)'
    if dz == '未': return 'hard', '冲牛(未日)'
    if jc == '破': return 'hard', '破日'

    # 四绝四离 + 节气当天
    jq = getattr(L, 'todaySolarTerms', '') or ''
    for term in ['立春','立夏','立秋','立冬','春分','秋分','夏至','冬至']:
        if term in jq: return 'hard', f'{term}当天'

    # 四绝 = 四立前一日, 四离 = 二分二至前一日
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

    # ── v8 软警告：月忌不再毙，只标注 ──
    if ld in (5, 14, 23): return 'soft', f'月忌(初{ld})'

    return None, None

def check_cnlunar(d):
    L = CLunar(datetime(d.year, d.month, d.day))
    good = [x.strip() for x in (L.goodThing or [])]
    bad = [x.strip() for x in (L.badThing or [])]
    return L, {
        'dz': L.day8Char[-1], 'ganzhi': L.day8Char,
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
    yi = list(l.getDayYi()); ji = list(l.getDayJi())
    return {
        'dz': l.getDayInGanZhiExact()[-1],
        'ganzhi': l.getDayInGanZhiExact(),
        'all_yi': yi, 'all_ji': ji,
        'marriage_yi': [x for x in yi if any(k in x for k in MARRIAGE_KEYS)],
        'marriage_ji': [x for x in ji if any(k in x for k in MARRIAGE_KEYS)],
    }

def judge(cn, lp, L, d):
    # 第零关：传统禁忌
    level, taboo_reason = check_traditional(L, d)
    if level == 'hard':
        return 'hard_reject', f'传统禁忌: {taboo_reason}', cn['dz'], taboo_reason

    dz = cn['dz']
    if dz != lp['dz']: return 'hard_reject', '日支双源不一致', dz, 'cn='+dz+' lp='+lp['dz']

    cn_yi = cn['marriage_yi']; cn_ji = cn['marriage_ji']
    lp_yi = lp['marriage_yi']; lp_ji = lp['marriage_ji']

    # 黄历条目冲突
    if cn['all_bad'] and lp_yi: return 'conflict', 'cn诸事不宜 vs lp宜嫁娶 冲突', dz, cn['level'][:60]
    if cn_yi and lp_ji: return 'conflict', 'cn宜 vs lp忌 冲突', dz, ''
    if lp_yi and cn_ji: return 'conflict', 'lp宜 vs cn忌 冲突', dz, ''

    # 同源内部矛盾（宜嫁娶但忌纳采/订盟）
    cn_self_conflict = cn_yi and cn_ji
    lp_self_conflict = lp_yi and lp_ji

    # 双源一致宜
    if cn_yi and lp_yi and not cn_ji and not lp_ji:
        return 'ideal', '双源一致宜嫁娶', dz, ''
    # cn诸事不宜
    if cn['all_bad']: return 'hard_reject', 'cn诸事不宜', dz, cn['level'][:60]
    # 双源一致忌
    if cn_ji and lp_ji: return 'hard_reject', '双源一致忌嫁娶', dz, ''
    # 单源宜 + 同源自矛盾
    if cn_yi and not lp_yi and not lp_ji:
        tag = '[同源自矛盾]' if cn_self_conflict else ''
        return 'single_good', f'cn宜 lp无 {tag}', dz, ','.join(cn_ji) if cn_self_conflict else ''
    if lp_yi and not cn_yi and not cn_ji:
        tag = '[同源自矛盾]' if lp_self_conflict else ''
        return 'single_good', f'lp宜 cn无 {tag}', dz, ','.join(lp_ji) if lp_self_conflict else ''
    # 单源忌
    if cn_ji and not lp_ji and not lp_yi: return 'hard_reject', 'cn忌 lp无', dz, ''
    if lp_ji and not cn_yi and not cn_ji: return 'hard_reject', 'lp忌 cn无', dz, ''
    # 双源均无
    if not cn_yi and not cn_ji and not lp_yi and not lp_ji:
        return 'neutral', '双源无嫁娶条目', dz, ''
    return 'neutral', '待查', dz, ''

# ═══ 扫描 9-10月 ═══
results = []
d = datetime(2026, 9, 1)
while d <= datetime(2026, 10, 31):
    label, is_rest = day_type(d)
    if is_rest:
        L_obj, cn = check_cnlunar(d)
        lp = check_lp(d)
        verdict, reason, dz, detail = judge(cn, lp, L_obj, d)
        soft_warn = None
        # 检查软警告（月忌等）
        sw_level, sw_reason = check_traditional(L_obj, d)
        if sw_level == 'soft':
            soft_warn = sw_reason
        results.append((d, label, verdict, reason, dz, cn, lp, detail, soft_warn))
    d += timedelta(days=1)

# ═══ 输出 ═══
print('=' * 130)
print('订婚吉日扫描 v8  2026年9-10月  |  月忌降级为警告 + 双源黄历')
print('=' * 130)
print()

for m in [9, 10]:
    month_label = f'{m}月'
    print(f'── {month_label} ──')
    print(f'{"日期":<12} {"周":<3} {"类型":<8} {"日支":<4} {"判决":<22} {"黄历详情":<50} {"备注"}')
    print('-' * 130)
    for d, label, v, reason, dz, cn, lp, detail, soft in results:
        if d.month != m: continue
        wk = '一二三四五六日'[d.weekday()]
        icon = {'ideal': '[IDEAL]', 'single_good': '[  OK  ]', 'neutral': '[ NEUT ]',
                'conflict': '[CONFL]', 'hard_reject': '[ REJ  ]'}[v]
        cn_yi_s = ','.join(cn['marriage_yi'][:3]) if cn['marriage_yi'] else ('X' if cn['all_bad'] else '-')
        cn_ji_s = ','.join(cn['marriage_ji'][:3]) if cn['marriage_ji'] else '-'
        lp_yi_s = ','.join(lp['marriage_yi'][:3]) if lp['marriage_yi'] else '-'
        lp_ji_s = ','.join(lp['marriage_ji'][:3]) if lp['marriage_ji'] else '-'
        yi_ji = f'cn宜:{cn_yi_s} 忌:{cn_ji_s} | lp宜:{lp_yi_s} 忌:{lp_ji_s}'
        notes = []
        if soft: notes.append(f'[!{soft}]')
        if detail: notes.append(detail)
        note_str = ' | '.join(notes)
        print(f'{d.strftime("%Y-%m-%d"):<12} 周{wk:<2} {label:<8} {dz:<4} {icon:<22} {yi_ji:<50} {note_str}')

print()
print('=' * 130)
print('汇总')
print('=' * 130)

ideal = [r for r in results if r[2] == 'ideal']
single = [r for r in results if r[2] == 'single_good']
neutral = [r for r in results if r[2] == 'neutral']
conflict = [r for r in results if r[2] == 'conflict']
rejected = [r for r in results if r[2] == 'hard_reject']

print(f'\n[IDEAL] 双源一致宜嫁娶: {len(ideal)}天')
for r in ideal:
    d=r[0]; soft=r[8]; tag = f'  [!{soft}]' if soft else ''
    print(f'  {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]} {r[1]}{tag}')

print(f'\n[OK] 单源宜嫁娶: {len(single)}天')
for r in single:
    d=r[0]; soft=r[8]; tag = f'  [!{soft}]' if soft else ''
    detail = f' [{r[7]}]' if r[7] else ''
    print(f'  {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]} {r[1]}{tag}{detail}')

print(f'\n[NEUT] 双源无条目: {len(neutral)}天')
for r in neutral:
    d=r[0]; soft=r[8]; tag = f'  [!{soft}]' if soft else ''
    print(f'  {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]} {r[1]}{tag}')

print(f'\n[CONFL] 双源冲突: {len(conflict)}天')
for r in conflict:
    d=r[0]; cn=r[5]; lp=r[6]
    print(f'  {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]} {r[1]} {r[3]}')
    print(f'    cn: 宜={cn["marriage_yi"]} 忌={cn["marriage_ji"]} | lp: 宜={lp["marriage_yi"]} 忌={lp["marriage_ji"]}')

print(f'\n[REJ] 硬毙: {len(rejected)}天')
for r in rejected:
    d=r[0]; print(f'  {d.strftime("%Y-%m-%d")} 周{"一二三四五六日"[d.weekday()]} {r[1]} -> {r[3]}')

print()
print(f'调休上班日(不列入): 9/20(日)国庆调班, 10/10(六)国庆调班')
