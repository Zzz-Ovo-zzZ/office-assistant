"""
聚焦分析 — 用户候选日期
9月: 4, 12, 19, 27, 28
10月: 1, 2, 3, 4, 5, 6, 11, 18, 25
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime
from lunar_python import Solar

# ═══════════ 复制核心分析函数 ═══════════

ENGAGEMENT_YI = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']
ENGAGEMENT_JI = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']

CLASH_DZ = {'午', '未'}  # 冲鼠(男)/冲牛(女)

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

HOLIDAY_NAMES = {
    **{datetime(2026,9,25): '中秋假期', datetime(2026,9,26): '中秋假期', datetime(2026,9,27): '中秋假期'},
    **{datetime(2026,10,i): '国庆假期' for i in range(1,8)},
}
WORKDAYS = {datetime(2026,9,20), datetime(2026,10,10)}


def is_rest_day(d):
    if d in WORKDAYS:
        return False
    if d in HOLIDAY_NAMES:
        return True
    if d.weekday() >= 5:
        return True
    return False


def get_jianchu(lunar):
    month_ganzhi = lunar.getMonthInGanZhiExact()
    day_ganzhi = lunar.getDayInGanZhiExact()
    month_zhi = month_ganzhi[-1]
    day_zhi = day_ganzhi[-1]
    m_idx = DIZHI.index(month_zhi)
    d_idx = DIZHI.index(day_zhi)
    jc_idx = (d_idx - m_idx + 12) % 12
    return JIANCHU[jc_idx]


def check_hard_reject(d, lunar):
    lm = lunar.getMonth()
    ld = lunar.getDay()
    day_ganzhi = lunar.getDayInGanZhiExact()
    day_zhi = day_ganzhi[-1]

    if ld == 1:
        return True, '朔日(初一)'
    if ld == 15:
        return True, '望日(十五)'

    if (lm, ld) in YANG_GONG:
        return True, '杨公忌日'

    if day_zhi in CLASH_DZ:
        animal = '鼠' if day_zhi == '午' else '牛'
        return True, f'冲{animal}({day_zhi}日)'

    jc = get_jianchu(lunar)
    if jc == '破':
        return True, '破日'

    # 节气检查
    jq_list = lunar.getJieQi()
    if jq_list and not isinstance(jq_list, str):
        for jq in jq_list:
            jq_name = jq.getName() if hasattr(jq, 'getName') else str(jq)
            if jq_name in EIGHT_JIEQI:
                return True, f'{jq_name}当天'
    elif isinstance(jq_list, str) and jq_list:
        for term in EIGHT_JIEQI:
            if term in jq_list:
                return True, f'{term}当天'

    nj = lunar.getNextJieQi()
    if nj:
        nj_name = nj.getName() if hasattr(nj, 'getName') else str(nj)
        if nj_name in EIGHT_JIEQI:
            nj_s = nj.getSolar() if hasattr(nj, 'getSolar') else None
            if nj_s:
                nj_d = datetime(nj_s.getYear(), nj_s.getMonth(), nj_s.getDay())
                if (nj_d - d).days <= 1:
                    if (nj_d - d).days == 0:
                        return True, f'{nj_name}当天'
                    else:
                        for term in ['立春','立夏','立秋','立冬']:
                            if term in nj_name:
                                return True, f'四绝日({term}前日)'
                        for term in ['春分','秋分','夏至','冬至']:
                            if term in nj_name:
                                return True, f'四离日({term}前日)'

    pj = lunar.getPrevJieQi()
    if pj:
        pj_name = pj.getName() if hasattr(pj, 'getName') else str(pj)
        if pj_name in EIGHT_JIEQI:
            pj_s = pj.getSolar() if hasattr(pj, 'getSolar') else None
            if pj_s:
                pj_d = datetime(pj_s.getYear(), pj_s.getMonth(), pj_s.getDay())
                if (d - pj_d).days == 0:
                    return True, f'{pj_name}当天'

    return False, None


def score_day(d, lunar):
    score = 50
    details = {}

    day_ganzhi = lunar.getDayInGanZhiExact()
    day_zhi = day_ganzhi[-1]
    details['日柱'] = day_ganzhi

    # 宜忌条目
    yi = list(lunar.getDayYi())
    ji = list(lunar.getDayJi())

    yi_marry = [x for x in yi if any(k in x for k in ENGAGEMENT_YI)]
    ji_marry = [x for x in ji if any(k in x for k in ENGAGEMENT_JI)]

    if yi_marry:
        if any('嫁娶' in x for x in yi_marry):
            score += 25
            details['宜嫁娶'] = yi_marry
        elif any(x in ['纳采', '订婚', '订盟'] for xs in yi_marry for x in xs.split()):
            score += 15
            details['宜纳采/订婚'] = yi_marry
        else:
            score += 10
            details['宜婚嫁相关'] = yi_marry

    if ji_marry:
        score -= 25
        details['忌婚嫁'] = ji_marry

    details['yi_marry'] = yi_marry
    details['ji_marry'] = ji_marry

    # 吉神
    jishen = list(lunar.getDayJiShen())
    details['jishen'] = jishen
    top_ji = [s for s in jishen if s in TOP_LUCKY]
    score += len(top_ji) * 5
    if top_ji:
        details['关键吉神'] = top_ji

    # 凶煞
    xiongsha = list(lunar.getDayXiongSha())
    details['xiongsha'] = xiongsha
    top_xiong = [s for s in xiongsha if s in TOP_UNLUCKY]
    score -= len(top_xiong) * 5
    if top_xiong:
        details['关键凶煞'] = top_xiong

    # 黄道/黑道
    tianshen_type = lunar.getDayTianShenType()
    tianshen = lunar.getDayTianShen()
    tianshen_luck = lunar.getDayTianShenLuck()
    details['天神'] = f'{tianshen}({tianshen_type}, {tianshen_luck})'

    if tianshen_type == '黄道':
        score += 8
    elif tianshen_type == '黑道':
        score -= 8

    # 二十八宿
    xiu = lunar.getXiu()
    details['星宿'] = xiu
    if xiu in GOOD_XIU:
        score += 5

    # 建除
    jc = get_jianchu(lunar)
    details['建除'] = jc
    jc_bonus = {'成': 10, '定': 8, '开': 8, '除': 5, '执': 2,
                '危': -5, '闭': -5, '满': -3, '建': 0, '平': 0, '收': 0}
    score += jc_bonus.get(jc, 0)

    score = max(0, min(100, score))
    return score, details


def make_tier(score):
    if score >= 75:
        return '★★★★★ 强烈推荐'
    elif score >= 65:
        return '★★★★  推荐'
    elif score >= 55:
        return '★★★   可选'
    elif score >= 45:
        return '★★    勉强'
    else:
        return '★     不建议'


def lunar_from_solar(d):
    solar = Solar.fromYmd(d.year, d.month, d.day)
    lunar = solar.getLunar()
    m = lunar.getMonth()
    day = lunar.getDay()
    return f'{m}月{day}日'


# ═══════════ 主分析 ═══════════

def main():
    # 候选日期
    candidate_dates = [
        # 9月
        datetime(2026, 9, 4),
        datetime(2026, 9, 12),
        datetime(2026, 9, 19),
        datetime(2026, 9, 27),
        datetime(2026, 9, 28),
        # 10月
        datetime(2026, 10, 1),
        datetime(2026, 10, 2),
        datetime(2026, 10, 3),
        datetime(2026, 10, 4),
        datetime(2026, 10, 5),
        datetime(2026, 10, 6),
        datetime(2026, 10, 11),
        datetime(2026, 10, 18),
        datetime(2026, 10, 25),
    ]

    out = []
    def w(s=''): out.append(s)

    w('=' * 100)
    w('  候选日期聚焦分析  9月: 4,12,19,27,28  |  10月: 1,2,3,4,5,6,11,18,25')
    w('  数据源: lunar-python (寿星天文历)  |  男方: 丙子鼠(冲午) 女方: 丁丑牛(冲未)')
    w('=' * 100)
    w()

    passed = []
    rejected = []

    for d in candidate_dates:
        wk = '一二三四五六日'[d.weekday()]
        solar = Solar.fromYmd(d.year, d.month, d.day)
        lunar = solar.getLunar()

        # 日期类型
        is_rest = is_rest_day(d)
        if d in HOLIDAY_NAMES:
            day_type = HOLIDAY_NAMES[d]
        elif d in WORKDAYS:
            day_type = '补班日'
        elif is_rest:
            day_type = '周末'
        else:
            day_type = '工作日'

        ln = lunar_from_solar(d)
        day_ganzhi = lunar.getDayInGanZhiExact()
        jc = get_jianchu(lunar)

        w(f'{"─" * 100}')
        w(f'  {d.strftime("%Y-%m-%d")}  周{wk}  {day_type}')
        w(f'  农历: {ln}  日柱: {day_ganzhi}  建除: {jc}')

        is_reject, reject_reason = check_hard_reject(d, lunar)

        if is_reject:
            w(f'  ❌ 硬毙: {reject_reason}')
            rejected.append((d, wk, day_type, ln, day_ganzhi, reject_reason))
        else:
            score, details = score_day(d, lunar)
            tier = make_tier(score)
            passed.append((d, wk, day_type, ln, day_ganzhi, score, tier, details))

            w(f'  得分: {score}  |  {tier}')
            w(f'  星宿: {details.get("星宿", "?")}  |  天神: {details.get("天神", "?")}')
            yi_marry = details.get('yi_marry', [])
            ji_marry = details.get('ji_marry', [])
            w(f'  宜婚嫁: {yi_marry if yi_marry else "(无)"}')
            w(f'  忌婚嫁: {ji_marry if ji_marry else "(无)"}')
            w(f'  吉神: {details.get("jishen", [])}')
            w(f'  凶煞: {details.get("xiongsha", [])}')
            if '关键吉神' in details:
                w(f'  ▲ 关键吉神: {details["关键吉神"]}')
            if '关键凶煞' in details:
                w(f'  ▼ 关键凶煞: {details["关键凶煞"]}')

    # ── 汇总 ──
    w()
    w('=' * 100)
    w('  汇总对比')
    w('=' * 100)
    w()

    if passed:
        # 按得分排序
        passed.sort(key=lambda r: -r[5])
        w(f'{"排名":<4} {"日期":<12} {"周":<3} {"类型":<10} {"农历":<10} {"日柱":<10} {"得分":<5} {"等级":<16} {"宜婚嫁"}')
        w('-' * 100)
        for i, (d, wk, day_type, ln, gz, score, tier, details) in enumerate(passed, 1):
            yi_str = '、'.join(details.get('yi_marry', []) or ['(无)'])
            w(f'{i:<4} {d.strftime("%Y-%m-%d"):<12} 周{wk:<2} {day_type:<10} {ln:<10} {gz:<10} {score:>3}  {tier:<16} {yi_str}')
    else:
        w('  无通过日期!')

    if rejected:
        w()
        w('已排除:')
        for d, wk, day_type, ln, gz, reason in rejected:
            w(f'  ❌ {d.strftime("%Y-%m-%d")} 周{wk} {day_type} {ln} {gz} → {reason}')

    w()
    w('=' * 100)

    return '\n'.join(out)


if __name__ == '__main__':
    report = main()
    print(report)

    # 保存
    report_path = r'D:\Code Files\Cursor\办公助手\output\候选日期分析_9月10月_20260610.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'\n报告已保存: {report_path}')
