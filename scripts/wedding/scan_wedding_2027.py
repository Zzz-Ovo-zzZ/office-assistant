"""
结婚三场连排扫描 — 2027年2月21日 ~ 6月30日
================================================
数据源: lunar-python (寿星天文历)
场景:
  ① 新干(周六) + 永丰(周日) 连着两天 —— 女方亲友圈两场宴席
  ② 龙岩(最正式主场) —— 紧邻的下一个周末(周六或周日取更优者)

硬约束:
  - 冲鼠(午日)/ 冲牛(未日)
  - 朔日(初一)/ 望日(十五)/ 月忌(初五·十四·廿三)
  - 杨公忌日 / 破日
  - 四绝日(立春立夏立秋立冬前一日)/ 四离日(二分二至前一日)
  - 八节当天 / 清明当天(及前一日, 谨慎)
  - 除夕至正月十五(本范围起点 2/21 已过, 天然规避)
  - 无父母忌日(用户确认)
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from lunar_python import Solar

# ═══════════════ 配置 ═══════════════
START = datetime(2027, 2, 21)
END   = datetime(2027, 6, 30)

MARRIAGE_YI = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']
MARRIAGE_JI = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']

# 男方 1996 丙子鼠 → 冲午日 ; 女方 1997 丁丑牛 → 冲未日
CLASH_DZ = {'午', '未'}

YANG_GONG = {
    (1,13), (2,11), (3,9), (4,7), (5,5), (6,3),
    (7,1), (7,29), (8,27), (9,25), (10,23), (11,21), (12,19)
}

TOP_LUCKY = {'天德', '月德', '天德合', '月德合', '天赦', '不将', '天喜', '红鸾',
             '母仓', '续世', '益后', '三合', '六合', '五合', '天恩', '天贵',
             '凤凰日', '麒麟日', '圣心', '福厚', '吉庆', '时德', '相日', '民日',
             '月恩', '四相', '岁德', '岁德合', '六仪', '要安', '金堂', '玉宇'}

TOP_UNLUCKY = {'月厌', '厌对', '四废', '五虚', '四穷', '劫煞', '灾煞', '月煞',
               '天吏', '致死', '死气', '月破', '月刑', '月害', '重丧', '天狗',
               '天罡', '河魁', '大耗', '小耗', '官符', '白虎', '朱雀'}

GOOD_XIU = {'房', '心', '尾', '斗', '牛', '室', '壁', '箕', '女'}
JIANCHU = ['建', '除', '满', '平', '定', '执', '破', '危', '成', '收', '开', '闭']
DIZHI = '子丑寅卯辰巳午未申酉戌亥'
EIGHT_JIEQI = {'立春', '立夏', '立秋', '立冬', '春分', '秋分', '夏至', '冬至'}

# 2027 年清明日期 (节气, 公历约 4/4~4/5), 预先定位
QINGMING_DATES = set()
_tmp = Solar.fromYmd(2027, 3, 1).getLunar().getJieQiTable()
for _name, _solar in _tmp.items():
    if _name == '清明':
        QINGMING_DATES.add(datetime(_solar.getYear(), _solar.getMonth(), _solar.getDay()))

# 2027 固定节日 (标注用; 官方调休尚未公布)
FIXED_HOLIDAYS = {
    datetime(2027, 5, 1): '劳动节',
    datetime(2027, 5, 4): '青年节',
    datetime(2027, 6, 1): '儿童节',
}


def get_jianchu(lunar):
    month_ganzhi = lunar.getMonthInGanZhiExact()
    day_ganzhi = lunar.getDayInGanZhiExact()
    m_idx = DIZHI.index(month_ganzhi[-1])
    d_idx = DIZHI.index(day_ganzhi[-1])
    return JIANCHU[(d_idx - m_idx + 12) % 12]


def hard_reject(d, lunar):
    """硬毙检查, 返回 (是否毙, 原因)"""
    lm = lunar.getMonth()
    ld = lunar.getDay()
    day_zhi = lunar.getDayInGanZhiExact()[-1]

    if ld == 1:  return True, '朔日(初一)'
    if ld == 15: return True, '望日(十五)'
    if ld in (5, 14, 23): return True, f'月忌(初{ld})'
    if (lm, ld) in YANG_GONG: return True, '杨公忌日'
    if day_zhi == '午': return True, '冲鼠(午日)'
    if day_zhi == '未': return True, '冲牛(未日)'
    if get_jianchu(lunar) == '破': return True, '破日'

    # 清明当天 + 前一日(谨慎)
    if d in QINGMING_DATES: return True, '清明当天'
    if (d + timedelta(days=1)) in QINGMING_DATES: return True, '清明前一日'

    # 八节当天 + 四绝四离(次日为八节)
    nj = lunar.getNextJieQi()
    if nj:
        nj_name = nj.getName() if hasattr(nj, 'getName') else str(nj)
        if nj_name in EIGHT_JIEQI:
            nj_s = nj.getSolar() if hasattr(nj, 'getSolar') else None
            if nj_s:
                nj_d = datetime(nj_s.getYear(), nj_s.getMonth(), nj_s.getDay())
                delta = (nj_d - d).days
                if delta == 0:
                    return True, f'{nj_name}当天'
                if delta == 1:
                    tag = '四绝' if nj_name in ('立春','立夏','立秋','立冬') else '四离'
                    return True, f'{tag}日({nj_name}前日)'

    # 当天本身是八节
    jq_list = lunar.getJieQi()
    if jq_list:
        for jq in jq_list:
            jq_name = jq.getName() if hasattr(jq, 'getName') else str(jq)
            if jq_name in EIGHT_JIEQI:
                return True, f'{jq_name}当天'

    return False, None


def score_day(d, lunar):
    score = 50
    yi = list(lunar.getDayYi())
    ji = list(lunar.getDayJi())
    yi_marry = [x for x in yi if any(k in x for k in MARRIAGE_YI)]
    ji_marry = [x for x in ji if any(k in x for k in MARRIAGE_JI)]

    if yi_marry:
        if any('嫁娶' in x for x in yi_marry):
            score += 25
        elif any(x in ('纳采', '订婚', '订盟') for x in yi_marry):
            score += 15
        else:
            score += 10
    if ji_marry:
        score -= 25

    jishen = list(lunar.getDayJiShen())
    top_ji = [s for s in jishen if s in TOP_LUCKY]
    score += len(top_ji) * 5

    xiongsha = list(lunar.getDayXiongSha())
    top_xiong = [s for s in xiongsha if s in TOP_UNLUCKY]
    score -= len(top_xiong) * 5

    if lunar.getDayTianShenType() == '黄道':
        score += 8
    elif lunar.getDayTianShenType() == '黑道':
        score -= 8

    if lunar.getXiu() in GOOD_XIU:
        score += 5

    jc = get_jianchu(lunar)
    jc_bonus = {'成':10, '定':8, '开':8, '除':5, '执':2,
                '危':-5, '闭':-5, '满':-3, '建':0, '平':0, '收':0}
    score += jc_bonus.get(jc, 0)

    return max(0, min(100, score)), {
        '日柱': lunar.getDayInGanZhiExact(),
        '农历': f'{lunar.getMonth()}月{lunar.getDay()}日',
        '宜': yi_marry, '忌': ji_marry,
        '吉神': top_ji, '凶煞': top_xiong,
        '建除': jc, '星宿': lunar.getXiu(),
        '天神': f'{lunar.getDayTianShen()}({lunar.getDayTianShenType()},{lunar.getDayTianShenLuck()})',
    }


def tier_name(s):
    if s >= 75: return '★★★★★ 强烈推荐'
    if s >= 65: return '★★★★ 推荐'
    if s >= 55: return '★★★ 可选'
    if s >= 45: return '★★ 勉强'
    return '★ 不建议'


def holiday_note(d, lunar):
    notes = []
    if d in FIXED_HOLIDAYS:
        notes.append(FIXED_HOLIDAYS[d])
    if lunar.getMonth() == 5 and lunar.getDay() == 5:
        notes.append('端午节')
    return '·'.join(notes)


# ═══════════════ 逐日扫描 ═══════════════
day_info = {}  # date -> (reject_reason or None, score, details)

d = START
while d <= END:
    solar = Solar.fromYmd(d.year, d.month, d.day)
    lunar = solar.getLunar()
    rej, reason = hard_reject(d, lunar)
    if rej:
        day_info[d] = (reason, None, None)
    else:
        s, det = score_day(d, lunar)
        day_info[d] = (None, s, det)
    d += timedelta(days=1)

def wk(d):
    return '一二三四五六日'[d.weekday()]

def info(d):
    return day_info[d]

# ═══════════════ 构建方案 ═══════════════
# 江西两场 = 周六+周日; 龙岩 = 下一周末(下周六/周日取更优)
plans = []

d = START
while d <= END:
    if d.weekday() == 5:  # 周六
        sat, sun = d, d + timedelta(days=1)
        if sun > END:
            break
        r_sat = info(sat)[0]
        r_sun = info(sun)[0]
        if r_sat or r_sun:
            d += timedelta(days=1)
            continue

        # 下一周末: 下周六 + 下周日
        nxt_sat = sat + timedelta(days=7)
        nxt_sun = nxt_sat + timedelta(days=1)
        ly_candidates = []
        for c in (nxt_sat, nxt_sun):
            if c <= END:
                c_rej, c_score, _ = info(c)
                if not c_rej:
                    ly_candidates.append((c, c_score))
        if not ly_candidates:
            d += timedelta(days=1)
            continue

        ly_date, ly_score = max(ly_candidates, key=lambda x: x[1])
        sat_score = info(sat)[1]
        sun_score = info(sun)[1]
        # 组合分: 江西两天取短板(连着办), 龙岩(最正式)权重略高
        jx_bottleneck = min(sat_score, sun_score)
        combo = 0.48 * jx_bottleneck + 0.52 * ly_score

        plans.append({
            'sat': sat, 'sun': sun, 'ly': ly_date,
            'sat_score': sat_score, 'sun_score': sun_score, 'ly_score': ly_score,
            'combo': combo,
        })
    d += timedelta(days=1)

plans.sort(key=lambda p: -p['combo'])

# ═══════════════ 输出 ═══════════════
out = []
def w(s=''):
    out.append(s)

w('=' * 130)
w('💒 结婚三场连排扫描  2027-02-21 ~ 2027-06-30')
w('数据源: lunar-python (寿星天文历)')
w('男 1996丙子鼠(避午日) × 女 1997丁丑牛(避未日) | 无父母忌日')
w('场次: 新干(周六) + 永丰(周日) → 龙岩(紧邻下周末, 最正式)')
w('=' * 130)
w()
w(f'清明硬毙: {sorted(QINGMING_DATES)}')
w()

# 推荐方案表
w('一、推荐方案 (按组合分降序)')
w('-' * 130)
hdr = (f'{"新干(周六)":<14} {"永丰(周日)":<14} {"龙岩(下周末)":<14} '
       f'{"江西短板":<8} {"龙岩分":<8} {"组合分":<8} {"龙岩备注"}')
w(hdr)
w('-' * 130)
for i, p in enumerate(plans, 1):
    sat, sun, ly = p['sat'], p['sun'], p['ly']
    ls = Solar.fromYmd(ly.year, ly.month, ly.day).getLunar()
    w(f'{sat.strftime("%Y-%m-%d"):<14} {sun.strftime("%Y-%m-%d"):<14} '
      f'{ly.strftime("%Y-%m-%d"):<14} '
      f'{p["sat_score"]:>2}/{p["sun_score"]:<2}{"":<2} '
      f'{p["ly_score"]:>3}     {p["combo"]:>6.1f}  '
      f'{holiday_note(ly, ls) or "-"}')

# 每个方案详细
w()
w('二、方案详情 (仅列 Top 15)')
w('-' * 130)
for i, p in enumerate(plans[:15], 1):
    sat, sun, ly = p['sat'], p['sun'], p['ly']
    w(f'\n【方案 {i}】组合分 {p["combo"]:.1f}')
    for label, dd, sc in [('新干(周六)', sat, p['sat_score']),
                          ('永丰(周日)', sun, p['sun_score']),
                          ('龙岩(下周末)', ly, p['ly_score'])]:
        _, _, det = info(dd)
        ls = Solar.fromYmd(dd.year, dd.month, dd.day).getLunar()
        hn = holiday_note(dd, ls)
        w(f'   {label:<10} {dd.strftime("%Y-%m-%d")} 周{wk(dd)}  得分 {sc:>3}  {tier_name(sc)}'
          f'   {det["农历"]}  {det["日柱"]}日  建除:{det["建除"]} 星宿:{det["星宿"]}'
          + (f'  [节假日:{hn}]' if hn else ''))
        w(f'           宜婚嫁:{det["宜"] or "-"}  忌:{det["忌"] or "-"}  吉神:{det["吉神"] or "-"}  凶煞:{det["凶煞"] or "-"}')

# 硬毙日清单(仅周末)
w()
w('三、范围内心仪周末被毙的日子(供避雷参考)')
w('-' * 130)
rejected_weekend = []
dd = START
while dd <= END:
    if dd.weekday() >= 5:
        rej, _, _ = info(dd)
        if rej:
            rejected_weekend.append((dd, rej))
    dd += timedelta(days=1)
for dd, rej in rejected_weekend:
    ls = Solar.fromYmd(dd.year, dd.month, dd.day).getLunar()
    w(f'   {dd.strftime("%Y-%m-%d")} 周{wk(dd)}  →  {rej}  ({ls.getMonth()}月{ls.getDay()}日)')

w()
w('=' * 130)
w(f'共 {len(plans)} 组可连排方案 | 输出完毕')
w('=' * 130)

print('\n'.join(out))
