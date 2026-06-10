"""
订婚吉日扫描 — 基于 lunar-python (寿星天文历)
================================================
数据源: lunar-python (通胜/协纪辨方书底层算法)
扫描范围: 2026年9-12月 休息日 (周末+节假日, 排除补班)
排序: 按订婚适合度从高到低
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from lunar_python import Solar

# ═══════════════════════════════
# 配置
# ═══════════════════════════════

# 订婚相关条目关键词
ENGAGEMENT_YI = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']
ENGAGEMENT_JI = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']

# 男方: 1996 丙子鼠 → 冲午日
# 女方: 1997 丁丑牛 → 冲未日
CLASH_DZ = {'午', '未'}

# 杨公忌日 (农历月, 农历日)
YANG_GONG = {
    (1,13), (2,11), (3,9), (4,7), (5,5), (6,3),
    (7,1), (7,29), (8,27), (9,25), (10,23), (11,21), (12,19)
}

# 嫁娶关键吉神 (来自协纪辨方书)
TOP_LUCKY = {'天德', '月德', '天德合', '月德合', '天赦', '不将', '天喜', '红鸾',
             '母仓', '续世', '益后', '三合', '六合', '五合', '天恩', '天贵',
             '凤凰日', '麒麟日', '圣心', '福厚', '吉庆', '时德', '相日', '民日',
             '月恩', '四相', '岁德', '岁德合', '六仪', '要安', '金堂', '玉宇'}

# 嫁娶关键凶神 (来自协纪辨方书)
TOP_UNLUCKY = {'月厌', '厌对', '四废', '五虚', '四穷', '劫煞', '灾煞', '月煞',
               '天吏', '致死', '死气', '月破', '月刑', '月害', '重丧', '天狗',
               '天罡', '河魁', '大耗', '小耗', '官符', '白虎', '朱雀'}

# 二十八宿 — 宜嫁娶的
GOOD_XIU = {'房', '心', '尾', '斗', '牛', '室', '壁', '箕', '女'}

# 十二建除名称
JIANCHU = ['建', '除', '满', '平', '定', '执', '破', '危', '成', '收', '开', '闭']

# 地支序列
DIZHI = '子丑寅卯辰巳午未申酉戌亥'

# 2026年放假安排
HOLIDAY_NAMES = {
    **{datetime(2026,9,25): '中秋假期', datetime(2026,9,26): '中秋假期', datetime(2026,9,27): '中秋假期'},
    **{datetime(2026,10,i): '国庆假期' for i in range(1,8)},
}
# 补班日 (不列入)
WORKDAYS = {datetime(2026,9,20), datetime(2026,10,10)}

# 八节 (二分二至四立)
EIGHT_JIEQI = {'立春', '立夏', '立秋', '立冬', '春分', '秋分', '夏至', '冬至'}


# ═══════════════════════════════
# 辅助函数
# ═══════════════════════════════

def is_rest_day(d):
    """判断是否为休息日(周末/节假日, 排除补班)"""
    if d in WORKDAYS:
        return False
    if d in HOLIDAY_NAMES:
        return True
    if d.weekday() >= 5:  # 周六日
        return True
    return False


def get_jianchu(lunar):
    """从月支和日支推算十二建除"""
    month_ganzhi = lunar.getMonthInGanZhiExact()  # e.g. '丁酉'
    day_ganzhi = lunar.getDayInGanZhiExact()      # e.g. '戊戌'

    month_zhi = month_ganzhi[-1]  # '酉'
    day_zhi = day_ganzhi[-1]      # '戌'

    m_idx = DIZHI.index(month_zhi)  # 酉 = 9
    d_idx = DIZHI.index(day_zhi)    # 戌 = 10

    # 正月建寅, 二月建卯...
    # 十二月 = 丑(1), 正月 = 寅(2)...
    # lunar month 1 → 寅 (idx 2), formula: (lunar_month + 1) % 12 → zhi index
    # But we already have month_zhi, so:
    # jianchu index = (day_zhi_index - month_zhi_index + 12) % 12
    jc_idx = (d_idx - m_idx + 12) % 12
    return JIANCHU[jc_idx]


def get_chong(day_zhi):
    """返回冲的生肖"""
    idx = DIZHI.index(day_zhi)
    chong_idx = (idx + 6) % 12
    return DIZHI[chong_idx]


def check_hard_reject(d, lunar):
    """硬毙检查, 返回 (是否毙, 原因)"""
    lm = lunar.getMonth()
    ld = lunar.getDay()
    day_ganzhi = lunar.getDayInGanZhiExact()
    day_zhi = day_ganzhi[-1]

    # 朔日/望日
    if ld == 1:
        return True, '朔日(初一)'
    if ld == 15:
        return True, '望日(十五)'

    # 杨公忌
    if (lm, ld) in YANG_GONG:
        return True, '杨公忌日'

    # 冲煞
    if day_zhi in CLASH_DZ:
        animal = '鼠' if day_zhi == '午' else '牛'
        return True, f'冲{animal}({day_zhi}日)'

    # 破日
    jc = get_jianchu(lunar)
    if jc == '破':
        return True, '破日'

    # 四绝/四离 (八节当天及前一日) + 节气当天
    # 先检查当天是否为八节
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

    # 检查 nextJieQi 与 prevJieQi (四绝四离)
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
    """
    对一天进行评分 (仅用于通过硬毙检查的日期)
    返回: (score, details_dict)
    """
    score = 50  # 基础分
    details = {}

    day_ganzhi = lunar.getDayInGanZhiExact()
    day_zhi = day_ganzhi[-1]
    details['日柱'] = day_ganzhi

    # ── 宜忌条目 (最直接) ──
    yi = list(lunar.getDayYi())
    ji = list(lunar.getDayJi())

    yi_marry = [x for x in yi if any(k in x for k in ENGAGEMENT_YI)]
    ji_marry = [x for x in ji if any(k in x for k in ENGAGEMENT_JI)]

    if yi_marry:
        # 有嫁娶最直接
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

    # ── 吉神 ──
    jishen = list(lunar.getDayJiShen())
    details['jishen'] = jishen
    top_ji = [s for s in jishen if s in TOP_LUCKY]
    score += len(top_ji) * 5
    if top_ji:
        details['关键吉神'] = top_ji

    # ── 凶煞 ──
    xiongsha = list(lunar.getDayXiongSha())
    details['xiongsha'] = xiongsha
    top_xiong = [s for s in xiongsha if s in TOP_UNLUCKY]
    score -= len(top_xiong) * 5
    if top_xiong:
        details['关键凶煞'] = top_xiong

    # ── 黄道/黑道 ──
    tianshen_type = lunar.getDayTianShenType()
    tianshen = lunar.getDayTianShen()
    tianshen_luck = lunar.getDayTianShenLuck()
    details['天神'] = f'{tianshen}({tianshen_type}, {tianshen_luck})'

    if tianshen_type == '黄道':
        score += 8
    elif tianshen_type == '黑道':
        score -= 8

    # ── 二十八宿 ──
    xiu = lunar.getXiu()
    details['星宿'] = xiu
    if xiu in GOOD_XIU:
        score += 5

    # ── 建除 ──
    jc = get_jianchu(lunar)
    details['建除'] = jc
    jc_bonus = {'成': 10, '定': 8, '开': 8, '除': 5, '执': 2,
                '危': -5, '闭': -5, '满': -3, '建': 0, '平': 0, '收': 0}
    score += jc_bonus.get(jc, 0)

    # ── 冲煞 ──
    chong = get_chong(day_zhi)
    details['冲'] = chong
    # 冲鼠/冲牛已在硬毙中处理, 这里只是额外信息

    # 封顶
    score = max(0, min(100, score))
    return score, details


def make_tier(score):
    """得分 → 推荐等级"""
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


# ═══════════════════════════════
# 主扫描
# ═══════════════════════════════

def main():
    results = []  # (date, label, score, tier, details, reject_reason)

    d = datetime(2026, 9, 1)
    while d <= datetime(2026, 12, 31):
        if is_rest_day(d):
            solar = Solar.fromYmd(d.year, d.month, d.day)
            lunar = solar.getLunar()

            is_reject, reject_reason = check_hard_reject(d, lunar)
            if is_reject:
                results.append((d, None, -1, '硬毙', {}, reject_reason))
            else:
                score, details = score_day(d, lunar)
                label = HOLIDAY_NAMES.get(d, '周末')
                tier = make_tier(score)
                results.append((d, label, score, tier, details, None))
        d += timedelta(days=1)

    # 排序: 硬毙排最后, 其余按得分降序
    results.sort(key=lambda r: (1 if r[2] < 0 else 0, -r[2]))

    # ═══ 输出报告 ═══
    out = []
    def w(s=''):
        out.append(s)

    w('=' * 120)
    w('订婚吉日扫描报告  2026年9-12月')
    w('数据源: lunar-python (寿星天文历) — 底层算法源自《协纪辨方书》《通胜》')
    w(f'男方: 1996丙子鼠(冲午) | 女方: 1997丁丑牛(冲未) | 禁忌: 朔望/杨公忌/破日/四绝四离')
    w('=' * 120)
    w()
    w('【排序规则】')
    w('  硬毙 → 剔除; 宜嫁娶/纳采/订婚条目 → 吉神数量/质量 → 黄道 > 黑道 → 建除/星宿辅助')
    w('  得分 = 50(基础) + 宜项分 + 吉神加分 + 黄道加分 + 星宿加分 + 建除调整 - 忌项分 - 凶煞扣分')
    w()

    # ── 推荐区 ──
    recommended = [r for r in results if r[2] >= 0]
    rejected = [r for r in results if r[2] < 0]

    w('─' * 120)
    w('一、推荐日期 (按适合度从高到低)')
    w('─' * 120)
    w()
    w(f'{"排名":<5} {"日期":<14} {"周几":<4} {"类型":<10} {"得分":<5} {"等级":<18} {"宜忌 (lunar-python)":<50}')
    w('-' * 120)

    for i, (d, label, score, tier, details, _) in enumerate(recommended, 1):
        wk = '一二三四五六日'[d.weekday()]
        yi_str = '、'.join(details.get('yi_marry', [])) or '(无婚嫁条目)'
        ji_str = '、'.join(details.get('ji_marry', []))
        if ji_str:
            yi_str += f'  忌: {ji_str}'
        w(f'{i:<5} {d.strftime("%Y-%m-%d"):<14} 周{wk:<3} {label:<10} {score:>3}  {tier:<18} {yi_str:<50}')

    w()
    w()

    # ── 逐日详情 ──
    w('─' * 120)
    w('二、逐日详情')
    w('─' * 120)

    for d, label, score, tier, details, _ in recommended:
        wk = '一二三四五六日'[d.weekday()]
        w()
        w(f'  {d.strftime("%Y-%m-%d")} 周{wk} {label}  |  得分 {score}  |  {tier}')
        w(f'    农历: {lunar_from_solar(d)}')
        w(f'    日柱: {details.get("日柱", "?")}  建除: {details.get("建除", "?")}  星宿: {details.get("星宿", "?")}')
        w(f'    天神: {details.get("天神", "?")}')
        w(f'    宜婚嫁: {details.get("yi_marry", [])}')
        w(f'    忌婚嫁: {details.get("ji_marry", [])}')
        w(f'    吉神: {details.get("jishen", [])}')
        w(f'    凶煞: {details.get("xiongsha", [])}')
        if '关键吉神' in details:
            w(f'    ▲ 关键吉神: {details["关键吉神"]}')
        if '关键凶煞' in details:
            w(f'    ▼ 关键凶煞: {details["关键凶煞"]}')

    # ── 硬毙区 ──
    w()
    w('─' * 120)
    w('三、已排除 (硬毙)')
    w('─' * 120)
    w()
    w(f'{"日期":<14} {"周几":<4} {"类型":<10} {"排除原因"}')
    w('-' * 80)
    for d, _, _, _, _, reason in rejected:
        wk = '一二三四五六日'[d.weekday()]
        label = HOLIDAY_NAMES.get(d, '周末')
        w(f'{d.strftime("%Y-%m-%d"):<14} 周{wk:<3} {label:<10} {reason}')

    # ── 月分布 ──
    w()
    w('─' * 120)
    w('四、月份分布')
    w('─' * 120)
    for m in [9, 10, 11, 12]:
        month_rec = [r for r in recommended if r[0].month == m]
        month_rej = [r for r in rejected if r[0].month == m]
        w(f'\n  {m}月: 推荐 {len(month_rec)}天 / 排除 {len(month_rej)}天')
        if month_rec:
            for r in month_rec:
                d = r[0]
                wk = '一二三四五六日'[d.weekday()]
                w(f'    {d.strftime("%Y-%m-%d")} 周{wk} {r[1]} 得分{r[2]} {r[3]}')

    # 统计
    w()
    w('─' * 120)
    w('五、统计')
    w('─' * 120)
    star5 = [r for r in recommended if r[2] >= 75]
    star4 = [r for r in recommended if 65 <= r[2] < 75]
    star3 = [r for r in recommended if 55 <= r[2] < 65]
    star2 = [r for r in recommended if 45 <= r[2] < 55]
    star1 = [r for r in recommended if r[2] < 45]

    w(f'  强烈推荐 (≥75): {len(star5)}天')
    w(f'  推荐 (65-74):   {len(star4)}天')
    w(f'  可选 (55-64):   {len(star3)}天')
    w(f'  勉强 (45-54):   {len(star2)}天')
    w(f'  不建议 (<45):   {len(star1)}天')
    w(f'  硬毙:           {len(rejected)}天')
    w(f'  合计:           {len(results)}天')

    # 休息日日历
    w()
    w('─' * 120)
    w('六、休息日日历 (9-12月)')
    w('─' * 120)
    for m in [9, 10, 11, 12]:
        w(f'\n  【{m}月】')
        d = datetime(2026, m, 1)
        while d.month == m:
            if d.weekday() >= 5 or d in HOLIDAY_NAMES:
                is_wd = d in WORKDAYS
                if is_wd:
                    tag = ' [补班-不列入]'
                else:
                    # 查找该日期结果
                    match = [r for r in results if r[0] == d]
                    if match:
                        r = match[0]
                        if r[2] >= 0:
                            tag = f' 得分{r[2]} {r[3][:8]}'
                        else:
                            tag = f' {r[5]}'
                    else:
                        tag = ''
                label = HOLIDAY_NAMES.get(d, '周末')
                wk = '一二三四五六日'[d.weekday()]
                w(f'    {d.strftime("%Y-%m-%d")} 周{wk} {label}{tag}')
            d += timedelta(days=1)

    w()
    w('=' * 120)
    w('报告生成完毕')
    w('=' * 120)

    return '\n'.join(out)


def lunar_from_solar(d):
    """获取农历日期字符串"""
    solar = Solar.fromYmd(d.year, d.month, d.day)
    lunar = solar.getLunar()
    m = lunar.getMonth()
    day = lunar.getDay()
    return f'{m}月{day}日'


# ═══════════════════════════════
# 也生成简化版 (只有排序列表)
# ═══════════════════════════════

def main_compact():
    """紧凑版输出"""
    results = []

    d = datetime(2026, 9, 1)
    while d <= datetime(2026, 12, 31):
        if is_rest_day(d):
            solar = Solar.fromYmd(d.year, d.month, d.day)
            lunar = solar.getLunar()

            is_reject, reject_reason = check_hard_reject(d, lunar)
            if is_reject:
                results.append((d, None, -1, '硬毙', {}, reject_reason))
            else:
                score, details = score_day(d, lunar)
                label = HOLIDAY_NAMES.get(d, '周末')
                tier = make_tier(score)
                results.append((d, label, score, tier, details, None))
        d += timedelta(days=1)

    results.sort(key=lambda r: (1 if r[2] < 0 else 0, -r[2]))

    out = []
    def w(s=''): out.append(s)

    w('=' * 100)
    w('订婚吉日扫描 v2  2026年9-12月  数据源: lunar-python')
    w('=' * 100)
    w()

    recommended = [r for r in results if r[2] >= 0]
    rejected = [r for r in results if r[2] < 0]

    w(f'{"排名":<4} {"日期":<12} {"周":<3} {"类型":<8} {"得分":<5} {"等级":<15} {"吉神":<20} {"凶煞":<15} {"建除":<4} {"星宿":<6} {"宜忌"}')
    w('-' * 100)

    for i, (d, label, score, tier, details, _) in enumerate(recommended, 1):
        wk = '一二三四五六日'[d.weekday()]
        jishen_short = ','.join(details.get('jishen', [])[:4])
        xiong_short = ','.join(details.get('xiongsha', [])[:3])
        jc = details.get('建除', '?')
        xiu = details.get('星宿', '?')
        yi_str = '宜:' + ','.join(details.get('yi_marry', []) or ['无'])
        ji_str = '忌:' + ','.join(details.get('ji_marry', [])) if details.get('ji_marry') else ''
        yiji = yi_str + ('  ' + ji_str if ji_str else '')
        w(f'{i:<4} {d.strftime("%Y-%m-%d"):<12} 周{wk:<2} {label:<8} {score:>3}  {tier:<15} {jishen_short:<20} {xiong_short:<15} {jc:<4} {xiu:<6} {yiji}')

    w()
    w('─' * 100)
    w(f'推荐({len(recommended)}天) | 硬毙({len(rejected)}天)')
    w()
    w('硬毙列表:')
    for d, _, _, _, _, reason in rejected:
        wk = '一二三四五六日'[d.weekday()]
        label = HOLIDAY_NAMES.get(d, '周末')
        w(f'  {d.strftime("%Y-%m-%d")} 周{wk} {label} → {reason}')

    return '\n'.join(out)


if __name__ == '__main__':
    # 生成详细报告
    report = main()

    # 保存
    report_path = r'D:\Code Files\Cursor\办公助手\output\订婚吉日扫描_lunar-python_2026年9-12月_20260610.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'详细报告已保存: {report_path}')

    print()
    print()

    # 也打印紧凑版
    compact = main_compact()
    print(compact)
