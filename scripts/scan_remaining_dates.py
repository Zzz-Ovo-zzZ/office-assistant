"""
扫描剩余休息日 — 排除用户已列候选日期后的订婚吉日
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from lunar_python import Solar

ENGAGEMENT_YI = ['嫁娶','结婚姻','纳采','订婚','婚姻','纳征','订盟']
ENGAGEMENT_JI = ['嫁娶','结婚姻','纳采','订婚','婚姻','纳征','订盟']
CLASH_DZ = {'午','未'}
YANG_GONG = {(1,13),(2,11),(3,9),(4,7),(5,5),(6,3),(7,1),(7,29),(8,27),(9,25),(10,23),(11,21),(12,19)}
TOP_LUCKY = {'天德','月德','天德合','月德合','天赦','不将','天喜','红鸾','母仓','续世','益后','三合','六合','五合','天恩','天贵','凤凰日','麒麟日','圣心','福厚','吉庆','时德','相日','民日','月恩','四相','岁德','岁德合','六仪','要安','金堂','玉宇'}
TOP_UNLUCKY = {'月厌','厌对','四废','五虚','四穷','劫煞','灾煞','月煞','天吏','致死','死气','月破','月刑','月害','重丧','天狗','天罡','河魁','大耗','小耗','官符','白虎','朱雀'}
GOOD_XIU = {'房','心','尾','斗','牛','室','壁','箕','女'}
JIANCHU = ['建','除','满','平','定','执','破','危','成','收','开','闭']
DIZHI = '子丑寅卯辰巳午未申酉戌亥'
EIGHT_JIEQI = {'立春','立夏','立秋','立冬','春分','秋分','夏至','冬至'}

HOLIDAY_NAMES = {
    **{datetime(2026,9,25): '中秋假期', datetime(2026,9,26): '中秋假期', datetime(2026,9,27): '中秋假期'},
    **{datetime(2026,10,i): '国庆假期' for i in range(1,8)},
}
WORKDAYS = {datetime(2026,9,20), datetime(2026,10,10)}

# 用户已列出的候选日期（本次排除）
EXCLUDED = {
    datetime(2026,9,4), datetime(2026,9,12), datetime(2026,9,19),
    datetime(2026,9,27), datetime(2026,9,28),
    datetime(2026,10,1), datetime(2026,10,2), datetime(2026,10,3),
    datetime(2026,10,4), datetime(2026,10,5), datetime(2026,10,6),
    datetime(2026,10,11), datetime(2026,10,18), datetime(2026,10,25),
}


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
    m_idx = DIZHI.index(month_ganzhi[-1])
    d_idx = DIZHI.index(day_ganzhi[-1])
    return JIANCHU[(d_idx - m_idx + 12) % 12]


def check_hard_reject(d, lunar):
    lm, ld = lunar.getMonth(), lunar.getDay()
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
    details['日柱'] = day_ganzhi

    yi = list(lunar.getDayYi())
    ji = list(lunar.getDayJi())
    yi_marry = [x for x in yi if any(k in x for k in ENGAGEMENT_YI)]
    ji_marry = [x for x in ji if any(k in x for k in ENGAGEMENT_JI)]

    if yi_marry:
        if any('嫁娶' in x for x in yi_marry):
            score += 25
            details['宜嫁娶'] = yi_marry
        elif any(x in ['纳采','订婚','订盟'] for xs in yi_marry for x in xs.split()):
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

    jishen = list(lunar.getDayJiShen())
    details['jishen'] = jishen
    top_ji = [s for s in jishen if s in TOP_LUCKY]
    score += len(top_ji) * 5
    if top_ji:
        details['关键吉神'] = top_ji

    xiongsha = list(lunar.getDayXiongSha())
    details['xiongsha'] = xiongsha
    top_xiong = [s for s in xiongsha if s in TOP_UNLUCKY]
    score -= len(top_xiong) * 5
    if top_xiong:
        details['关键凶煞'] = top_xiong

    tianshen_type = lunar.getDayTianShenType()
    tianshen = lunar.getDayTianShen()
    tianshen_luck = lunar.getDayTianShenLuck()
    details['天神'] = f'{tianshen}({tianshen_type}, {tianshen_luck})'
    if tianshen_type == '黄道':
        score += 8
    elif tianshen_type == '黑道':
        score -= 8

    xiu = lunar.getXiu()
    details['星宿'] = xiu
    if xiu in GOOD_XIU:
        score += 5

    jc = get_jianchu(lunar)
    details['建除'] = jc
    jc_bonus = {'成':10,'定':8,'开':8,'除':5,'执':2,'危':-5,'闭':-5,'满':-3,'建':0,'平':0,'收':0}
    score += jc_bonus.get(jc, 0)

    score = max(0, min(100, score))
    return score, details


def make_tier(s):
    if s >= 75: return '★★★★★ 强烈推荐'
    elif s >= 65: return '★★★★  推荐'
    elif s >= 55: return '★★★   可选'
    elif s >= 45: return '★★    勉强'
    else: return '★     不建议'


def main():
    results = []
    d = datetime(2026, 9, 1)
    while d <= datetime(2026, 10, 31):
        if is_rest_day(d) and d not in EXCLUDED:
            solar = Solar.fromYmd(d.year, d.month, d.day)
            lunar = solar.getLunar()
            is_reject, reason = check_hard_reject(d, lunar)
            if is_reject:
                results.append((d, -1, '硬毙', {}, reason))
            else:
                score, details = score_day(d, lunar)
                results.append((d, score, make_tier(score), details, None))
        d += timedelta(days=1)

    results.sort(key=lambda r: (1 if r[1] < 0 else 0, -r[1]))

    passed = [r for r in results if r[1] >= 0]
    rejected = [r for r in results if r[1] < 0]

    print('=' * 110)
    print('  剩余休息日订婚扫描  2026年9-10月')
    print('  已排除: 用户15个候选日 + 工作日 + 补班日')
    print('=' * 110)
    print()
    print(f'{"排名":<4} {"日期":<12} {"周":<3} {"类型":<10} {"农历":<10} {"日柱":<8} {"得分":<5} {"等级":<16} {"宜婚嫁"}')
    print('-' * 110)

    rank = 0
    for d, score, tier, details, reason in results:
        wk = '一二三四五六日'[d.weekday()]
        lbl = HOLIDAY_NAMES.get(d, '周末')
        solar = Solar.fromYmd(d.year, d.month, d.day)
        lunar = solar.getLunar()
        ln = f'{lunar.getMonth()}月{lunar.getDay()}日'
        gz = lunar.getDayInGanZhiExact()

        if score < 0:
            print(f'{"❌":<4} {d.strftime("%Y-%m-%d"):<12} 周{wk:<2} {lbl:<10} {ln:<10} {gz:<8} {"硬毙":<5} {"":<16} {reason}')
        else:
            rank += 1
            yi_str = '、'.join(details.get('yi_marry', []) or ['(无)'])
            ji_str = '、'.join(details.get('ji_marry', []))
            flag = ''
            if ji_str:
                flag += f'  忌:{ji_str}'
            print(f'{rank:<4} {d.strftime("%Y-%m-%d"):<12} 周{wk:<2} {lbl:<10} {ln:<10} {gz:<8} {score:>3}  {tier:<14}  {yi_str}{flag}')

    # ── 逐日简评 ──
    print()
    print('─' * 110)
    print('  逐日详情')
    print('─' * 110)

    for d, score, tier, details, reason in results:
        if score < 0:
            continue
        wk = '一二三四五六日'[d.weekday()]
        lbl = HOLIDAY_NAMES.get(d, '周末')
        solar = Solar.fromYmd(d.year, d.month, d.day)
        lunar = solar.getLunar()
        ln = f'{lunar.getMonth()}月{lunar.getDay()}日'
        gz = lunar.getDayInGanZhiExact()
        jc = get_jianchu(lunar)

        jishen_show = '、'.join(details.get('关键吉神', [])) or '-'
        xiong_show = '、'.join(details.get('关键凶煞', [])) or '-'
        yi_str = '、'.join(details.get('yi_marry', []) or ['(无)'])
        ji_str = '、'.join(details.get('ji_marry', [])) or '-'

        print()
        print(f'  {d.strftime("%Y-%m-%d")}  周{wk}  {lbl}  |  得分 {score}  |  {tier}')
        print(f'    农历 {ln}  日柱 {gz}  建除 {jc}  星宿 {details.get("星宿","?")}')
        print(f'    天神: {details.get("天神","?")}')
        print(f'    宜婚嫁: {yi_str}')
        print(f'    忌婚嫁: {ji_str}')
        print(f'    ▲ 关键吉神: {jishen_show}')
        print(f'    ▼ 关键凶煞: {xiong_show}')

    # ── 硬毙 ──
    if rejected:
        print()
        print('─' * 110)
        print('  已硬毙:')
        print('─' * 110)
        for d, _, _, _, reason in rejected:
            wk = '一二三四五六日'[d.weekday()]
            lbl = HOLIDAY_NAMES.get(d, '周末')
            print(f'    ❌ {d.strftime("%Y-%m-%d")} 周{wk} {lbl} → {reason}')

    # 统计
    print()
    print('=' * 110)
    print(f'  统计: 推荐 {len(passed)} 天 | 硬毙 {len(rejected)} 天 | 合计 {len(results)} 天')
    print('=' * 110)


if __name__ == '__main__':
    main()
