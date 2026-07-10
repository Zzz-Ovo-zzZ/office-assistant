"""
订婚吉日扫描 v9 —— 协纪辨方书 + 通胜 融合引擎
==============================================
数据源:
  1. cnlunar (农历数据) — 神煞/建除/二十八宿/日等级
  2. lunar-python (寿星天文历) — 宜忌交叉验证

融合逻辑:
  - 协纪辨方书: 神煞体系量化打分 (不将日/天德月德/天赦/建除吉日)
  - 通胜实战: 黄道黑道判断 + 民间经验法则
  - 双源黄历: 宜忌条目交叉验证

评分体系:
  基础分 50 分
  吉神加分最高 +50 (不将+30, 天德/月德+20, 天赦+25, 天喜+15, 三合六合+10...)
  凶神扣分最高 -50 (月厌-25, 四废五虚-20, 月煞-15, 死气-10...)
  建除调整 ±10
  黄道黑道 ±5
  双源一致性 ±10
  最终得分 0-100

置信度:
  ≥80: 强烈推荐 ★★★★★
  ≥65: 推荐 ★★★★
  ≥50: 可选 ★★★
  ≥35: 勉强可选 ★★
  <35: 不建议 ★
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from cnlunar import Lunar as CLunar
from lunar_python import Solar

# ═══════════════════════════════════════════════════════════
# 配置区
# ═══════════════════════════════════════════════════════════

FORBIDDEN_DZ = {'午', '未'}  # 午冲鼠(男方 1996丙子), 未冲牛(女方 1997丁丑)
MARRIAGE_KEYS = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']

# 协纪辨方书: 嫁娶吉神 (按权重分级)
LUCKY_GODS_TIER1 = {  # 顶级吉神
    '天赦': 25,
    '不将': 30,  # 嫁娶第一吉神
}
LUCKY_GODS_TIER2 = {  # 一级吉神
    '天德': 20, '月德': 20, '天德合': 20, '月德合': 20,
}
LUCKY_GODS_TIER3 = {  # 二级吉神
    '天喜': 15, '红鸾': 15,
    '三合': 10, '六合': 10, '五合': 8,
    '母仓': 8, '续世': 8, '益后': 8,
}
LUCKY_GODS_TIER4 = {  # 三级吉神
    '凤凰日': 6, '麒麟日': 6,
    '天贵': 5, '天富': 5, '天恩': 5,
    '圣心': 5, '福厚': 5, '吉庆': 5,
    '时德': 5, '相日': 5, '民日': 5,
    '月恩': 5, '四相': 5,
}

# 协纪辨方书: 嫁娶凶神 (按严重度分级)
UNLUCKY_GODS_TIER1 = {  # 严重凶神
    '月厌': -25, '厌对': -20,
    '四废': -20, '五虚': -20, '四穷': -20,
    '劫煞': -15, '灾煞': -15, '月煞': -15,
}
UNLUCKY_GODS_TIER2 = {  # 中等级凶神
    '天吏': -12, '致死': -12,
    '死气': -10, '官符': -10,
    '大耗': -10, '小耗': -8,
    '月破': -15, '月刑': -12, '月害': -12,
}
UNLUCKY_GODS_TIER3 = {  # 一般凶神
    '天瘟': -8, '白虎': -8, '朱雀': -8,
    '天棒': -6, '殃败': -6, '雷公': -6,
    '五离': -8, '四离': -8,
    '血支': -5, '游祸': -5,
    '重丧': -10, '天狗': -8,
}

# 协纪辨方书: 建除十二神对嫁娶的影响
JIANCHU_MARRIAGE = {
    '除': 10,   # 除旧布新，宜嫁娶
    '定': 10,   # 安定，宜嫁娶
    '执': 5,    # 可嫁娶
    '成': 12,   # 万事成就，上吉
    '开': 10,   # 开枝散叶，宜嫁娶
    '建': 0,    # 中性
    '满': -5,   # 满则溢
    '平': 0,    # 中性
    '破': -999, # 大凶，硬毙
    '危': -5,   # 危则不安
    '收': 0,    # 中性偏可
    '闭': -8,   # 闭则不通
}

# 黄道黑道 (值日神)
HUANGDAO_GODS = {'青龙', '明堂', '金匮', '天德', '玉堂', '司命', '金贵'}
HEIDAO_GODS = {'白虎', '天刑', '朱雀', '玄武', '天牢', '勾陈'}

# 二十八宿对嫁娶的影响
XIU_MARRIAGE = {
    '角木蛟': 5, '亢金龙': 3, '氐土貉': 5, '房日兔': 10,  # 东方青龙 - 房日兔上吉
    '心月狐': 10, '尾火虎': 8, '箕水豹': 5,              # 心月狐嫁娶吉
    '斗木獬': 8, '牛金牛': 8, '女士蝠': 3,               # 北方玄武 - 斗牛吉
    '虚日鼠': -3, '危月燕': -5, '室火猪': 8, '壁水貐': 6,
    '奎木狼': 3, '娄金狗': 5, '胃土雉': -2, '昴日鸡': -3,  # 西方白虎
    '毕月乌': 3, '觜火猴': -3, '参水猿': -2,
    '井木犴': 3, '鬼金羊': -5, '柳土獐': -5,               # 南方朱雀
    '星日马': 5, '张月鹿': 3, '翼火蛇': -2, '轸水蚓': 3,
}

# 杨公忌日 (来自民间通胜)
YANG_GONG = [
    (1,13),(2,11),(3,9),(4,7),(5,5),(6,3),
    (7,1),(7,29),(8,27),(9,25),(10,23),(11,21),(12,19)
]

# 2026年放假
HOLIDAYS = {
    datetime(2026,9,25): '中秋假期', datetime(2026,9,26): '中秋假期', datetime(2026,9,27): '中秋假期',
    **{datetime(2026,10,i): '国庆假期' for i in range(1,8)},
}
WORK_SATURDAYS = {datetime(2026,9,20): '国庆调班', datetime(2026,10,10): '国庆调班'}


# ═══════════════════════════════════════════════════════════
# 核心判断函数
# ═══════════════════════════════════════════════════════════

def day_type(d):
    """判断日期类型"""
    if d in HOLIDAYS:
        return HOLIDAYS[d], True
    if d in WORK_SATURDAYS:
        return '调休上班日', False
    if d.weekday() >= 5:
        return '周末', True
    return '工作日', False


def check_traditional(L, d):
    """
    传统硬禁忌检查 (协纪辨方书 + 通胜)
    返回: (level, reason)
      'hard' = 硬毙, 'soft' = 警告, None = 无禁忌
    """
    lm = L.lunarMonth
    ld = L.lunarDay
    dz = L.day8Char[-1]
    jc = getattr(L, 'today12DayOfficer', '')

    # ── 硬毙规则 ──
    if ld == 1:
        return 'hard', '朔日(初一)'
    if ld == 15:
        return 'hard', '望日(十五)'
    if (lm, ld) in YANG_GONG:
        return 'hard', '杨公忌日'
    if dz in FORBIDDEN_DZ:
        animal = '鼠' if dz == '午' else '牛'
        return 'hard', f'冲{animal}({dz}日)'
    if jc == '破':
        return 'hard', '破日'

    # 节气当天
    jq = getattr(L, 'todaySolarTerms', '') or ''
    for term in ['立春','立夏','立秋','立冬','春分','秋分','夏至','冬至']:
        if term in jq:
            return 'hard', f'{term}当天'

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
                    if term in nj_name:
                        return 'hard', f'四绝日({term}前日)'
                for term in ['春分','秋分','夏至','冬至']:
                    if term in nj_name:
                        return 'hard', f'四离日({term}前日)'

    # ── 软警告 ──
    if ld in (5, 14, 23):
        return 'soft', f'月忌(初{ld})'

    return None, None


def compute_shensha_score(L):
    """
    协纪辨方书神煞评分
    返回: (吉神分, 凶神分, 总神煞分, 吉神列表, 凶神列表, 详情)
    """
    lucky_score = 0
    unlucky_score = 0
    lucky_gods_found = []
    unlucky_gods_found = []

    gn = L.goodGodName  # 吉神列表
    bn = L.badGodName   # 凶神列表

    # 合并所有吉神权重
    all_lucky_weights = {}
    all_lucky_weights.update(LUCKY_GODS_TIER1)
    all_lucky_weights.update(LUCKY_GODS_TIER2)
    all_lucky_weights.update(LUCKY_GODS_TIER3)
    all_lucky_weights.update(LUCKY_GODS_TIER4)

    all_unlucky_weights = {}
    all_unlucky_weights.update(UNLUCKY_GODS_TIER1)
    all_unlucky_weights.update(UNLUCKY_GODS_TIER2)
    all_unlucky_weights.update(UNLUCKY_GODS_TIER3)

    # 吉神评分 (+)
    for god in gn:
        for key, weight in all_lucky_weights.items():
            if key in god or god in key:
                lucky_score += weight
                lucky_gods_found.append(f'{god}({weight:+d})')
                break

    # 凶神评分 (-)
    for god in bn:
        for key, weight in all_unlucky_weights.items():
            if key in god or god in key:
                unlucky_score += weight
                unlucky_gods_found.append(f'{god}({weight})')
                break

    # 三合/六合加分 (从 zodiacMark3/6)
    m3 = L.zodiacMark3List
    m6 = L.zodiacMark6
    if m3:
        lucky_score += 10
        lucky_gods_found.append(f'三合({"+10"})')
    if m6:
        lucky_score += 10
        lucky_gods_found.append(f'六合({"+10"})')

    total = lucky_score + unlucky_score
    return lucky_score, unlucky_score, total, lucky_gods_found, unlucky_gods_found


def compute_jianchu_score(L):
    """建除十二神评分"""
    jc = getattr(L, 'today12DayOfficer', '')
    return JIANCHU_MARRIAGE.get(jc, 0), jc


def compute_xiu_score(L):
    """二十八宿评分"""
    xiu = L.today28Star
    return XIU_MARRIAGE.get(xiu, 0), xiu


def compute_huangdao_score(L):
    """黄道黑道评分"""
    god = getattr(L, 'today12DayGod', '')
    if god in HUANGDAO_GODS:
        return 5, f'黄道({god})'
    elif god in HEIDAO_GODS:
        return -5, f'黑道({god})'
    return 0, f'中性({god})'


def check_cnlunar_v9(d):
    """获取 cnlunar 完整数据"""
    L = CLunar(datetime(d.year, d.month, d.day))
    good = [x.strip() for x in (L.goodThing or [])]
    bad = [x.strip() for x in (L.badThing or [])]

    return L, {
        'dz': L.day8Char[-1],
        'ganzhi': L.day8Char,
        'lm': L.lunarMonth,
        'ld': L.lunarDay,
        'all_yi': good,
        'all_ji': bad,
        'marriage_yi': [x for x in good if any(k in x for k in MARRIAGE_KEYS)],
        'marriage_ji': [x for x in bad if any(k in x for k in MARRIAGE_KEYS)],
        'all_bad': '诸事不宜' in ' '.join(good),
        'jianchu': getattr(L, 'today12DayOfficer', '?'),
        'xiu': L.today28Star,
        'level': L.todayLevel,
        'level_name': L.todayLevelName,
        'good_gods': L.goodGodName,
        'bad_gods': L.badGodName,
        'jianchu_god': getattr(L, 'today12DayGod', '?'),
        'clash': L.chineseZodiacClash,
    }


def check_lp_v9(d):
    """获取 lunar-python 完整数据"""
    s = Solar.fromYmd(d.year, d.month, d.day)
    l = s.getLunar()
    yi = list(l.getDayYi())
    ji = list(l.getDayJi())
    return {
        'dz': l.getDayInGanZhiExact()[-1],
        'ganzhi': l.getDayInGanZhiExact(),
        'all_yi': yi,
        'all_ji': ji,
        'marriage_yi': [x for x in yi if any(k in x for k in MARRIAGE_KEYS)],
        'marriage_ji': [x for x in ji if any(k in x for k in MARRIAGE_KEYS)],
    }


def judge_v9(cn, lp, L, d):
    """
    v9 融合判决
    返回: (verdict, score, reason, details_dict)
    """
    # ── 第零关: 硬禁忌 ──
    level, taboo_reason = check_traditional(L, d)
    if level == 'hard':
        return 'hard_reject', 0, f'硬禁忌: {taboo_reason}', {
            'taboo': taboo_reason, 'score': 0
        }

    # 软警告
    soft_warn = taboo_reason if level == 'soft' else None

    # 日支一致性
    dz = cn['dz']
    if dz != lp['dz']:
        return 'hard_reject', 0, '日支双源不一致', {
            'taboo': f'cn={dz} lp={lp["dz"]}', 'score': 0
        }

    # ── 第一关: 神煞评分 (协纪辨方书核心) ──
    lucky, unlucky, shensha_total, lucky_list, unlucky_list = compute_shensha_score(L)

    # ── 第二关: 建除评分 ──
    jc_score, jc_name = compute_jianchu_score(L)
    if jc_score <= -999:  # 破日已在硬禁忌中处理，此处兜底
        return 'hard_reject', 0, '建除: 破日', {'score': 0}

    # ── 第三关: 二十八宿评分 ──
    xiu_score, xiu_name = compute_xiu_score(L)

    # ── 第四关: 黄道黑道 ──
    hd_score, hd_desc = compute_huangdao_score(L)

    # ── 第五关: 日等级 (cnlunar 内置综合) ──
    lvl = cn['level']
    # lv1/lv-1 = 上吉, lv2 = 吉, lv3 = 中, lv4 = 次, lv5 = 凶
    if lvl == 1 or lvl == -1:
        lvl_score = 10
    elif lvl == 2:
        lvl_score = 5
    elif lvl == 3:
        lvl_score = 0
    elif lvl == 4:
        lvl_score = -8
    else:
        lvl_score = -15

    # ── 第六关: 双源黄历一致性 ──
    cn_yi = cn['marriage_yi']
    cn_ji = cn['marriage_ji']
    lp_yi = lp['marriage_yi']
    lp_ji = lp['marriage_ji']

    cn_self_conflict = bool(cn_yi and cn_ji)
    lp_self_conflict = bool(lp_yi and lp_ji)

    dual_source_score = 0
    dual_source_detail = ''

    if cn['all_bad'] and lp_yi:
        dual_source_score = -20
        dual_source_detail = '冲突:cn诸事不宜 vs lp宜嫁娶'
    elif cn_yi and lp_ji:
        dual_source_score = -20
        dual_source_detail = '冲突:cn宜 vs lp忌'
    elif lp_yi and cn_ji:
        dual_source_score = -20
        dual_source_detail = '冲突:lp宜 vs cn忌'
    elif cn_yi and lp_yi and not cn_ji and not lp_ji:
        dual_source_score = 15
        dual_source_detail = '双源一致宜嫁娶'
    elif cn_yi and not lp_yi and not lp_ji:
        dual_source_score = 8
        if cn_self_conflict:
            dual_source_detail = 'cn宜+同源矛盾,lp无'
            dual_source_score = 3
        else:
            dual_source_detail = 'cn宜,lp无'
    elif lp_yi and not cn_yi and not cn_ji:
        dual_source_score = 8
        if lp_self_conflict:
            dual_source_detail = 'lp宜+同源矛盾,cn无'
            dual_source_score = 3
        else:
            dual_source_detail = 'lp宜,cn无'
    elif cn['all_bad']:
        dual_source_score = -15
        dual_source_detail = 'cn诸事不宜'
    elif cn_ji and lp_ji:
        dual_source_score = -15
        dual_source_detail = '双源一致忌嫁娶'
    elif cn_ji and not lp_ji and not lp_yi:
        dual_source_score = -10
        dual_source_detail = 'cn忌,lp无'
    elif lp_ji and not cn_yi and not cn_ji:
        dual_source_score = -10
        dual_source_detail = 'lp忌,cn无'
    elif not cn_yi and not cn_ji and not lp_yi and not lp_ji:
        dual_source_score = 0
        dual_source_detail = '双源无嫁娶条目'
    else:
        dual_source_score = 0
        dual_source_detail = '其他'

    # ── 第七关: 自矛盾扣分 ──
    self_conflict_score = 0
    if cn_self_conflict:
        self_conflict_score -= 5
    if lp_self_conflict:
        self_conflict_score -= 5

    # ── 总分计算 ──
    base_score = 50
    total_score = (
        base_score
        + shensha_total
        + jc_score
        + xiu_score
        + hd_score
        + lvl_score
        + dual_source_score
        + self_conflict_score
    )
    total_score = max(0, min(100, total_score))

    # ── 置信度分级 ──
    if total_score >= 80:
        verdict = 'strongly_recommended'
        stars = '★★★★★'
    elif total_score >= 65:
        verdict = 'recommended'
        stars = '★★★★'
    elif total_score >= 50:
        verdict = 'acceptable'
        stars = '★★★'
    elif total_score >= 35:
        verdict = 'marginal'
        stars = '★★'
    else:
        verdict = 'not_recommended'
        stars = '★'

    # ── 组装原因 ──
    reason_parts = []
    if soft_warn:
        reason_parts.append(f'⚠{soft_warn}')
    if lucky_list:
        reason_parts.append(f'吉:{",".join([g.split("(")[0] for g in lucky_list[:5]])}')
    if unlucky_list:
        reason_parts.append(f'凶:{",".join([g.split("(")[0] for g in unlucky_list[:5]])}')
    reason_parts.append(f'建除:{jc_name}({jc_score:+d})')
    reason_parts.append(f'宿:{xiu_name}({xiu_score:+d})')
    reason_parts.append(f'{hd_desc}')
    reason_parts.append(dual_source_detail)

    reason = ' | '.join(reason_parts)

    detail = {
        'score': total_score,
        'stars': stars,
        'shensha': f'吉{shensha_total:+d}',
        'jc': jc_name,
        'xiu': xiu_name,
        'huangdao': hd_desc,
        'dual_source': dual_source_detail,
        'level': cn['level'],
        'level_name': cn['level_name'][:80],
        'lucky_gods': lucky_list,
        'unlucky_gods': unlucky_list,
        'soft_warn': soft_warn,
        'cn_yi': cn['marriage_yi'],
        'cn_ji': cn['marriage_ji'],
        'lp_yi': lp['marriage_yi'],
        'lp_ji': lp['marriage_ji'],
        'lucky_total': lucky,
        'unlucky_total': unlucky,
        'jc_score': jc_score,
        'xiu_score': xiu_score,
        'hd_score': hd_score,
        'lvl_score': lvl_score,
        'dual_score': dual_source_score,
        'self_conflict_score': self_conflict_score,
    }

    return verdict, total_score, reason, detail


# ═══════════════════════════════════════════════════════════
# 主扫描
# ═══════════════════════════════════════════════════════════

def main():
    results = []
    d = datetime(2026, 9, 1)
    while d <= datetime(2026, 10, 31):
        label, is_rest = day_type(d)
        if is_rest:
            L_obj, cn = check_cnlunar_v9(d)
            lp = check_lp_v9(d)
            verdict, score, reason, detail = judge_v9(cn, lp, L_obj, d)
            results.append((d, label, verdict, score, reason, cn, lp, detail))
        d += timedelta(days=1)

    # 按得分排序
    results.sort(key=lambda r: (r[3], r[2] not in ('hard_reject', 'not_recommended')), reverse=True)

    # ── 输出 ──
    print('=' * 140)
    print('订婚吉日扫描 v9  2026年9-10月')
    print('融合引擎: 协纪辨方书神煞体系 + 通胜实战经验 + 双源黄历交叉验证')
    print('=' * 140)
    print()

    # ── 综合排名 ──
    print('【一、综合排名 (按融合得分从高到低)】')
    print(f'{"排名":<4} {"日期":<12} {"周":<3} {"类型":<8} {"得分":<5} {"置信度":<10} {"建除":<4} {"宿":<8} {"关键神煞"}')
    print('-' * 140)

    rank = 1
    for d, label, verdict, score, reason, cn, lp, detail in results:
        wk = '一二三四五六日'[d.weekday()]
        dz = cn['dz']
        jc = detail['jc']
        xiu = detail['xiu']
        stars = detail['stars']

        # 关键神煞摘要
        key_gods = []
        lucky_gods = detail['lucky_gods']
        for g in lucky_gods[:3]:
            gname = g.split('(')[0]
            if gname in ['不将','天德','月德','天德合','月德合','天赦','天喜','红鸾','三合','六合']:
                key_gods.append(f'✓{gname}')
        unlucky_gods = detail['unlucky_gods']
        for g in unlucky_gods[:2]:
            gname = g.split('(')[0]
            if gname in ['月厌','厌对','四废','五虚','劫煞','灾煞','月煞','天吏']:
                key_gods.append(f'✗{gname}')

        soft = detail['soft_warn']
        if soft:
            key_gods.append(f'⚠{soft}')

        key_str = ' '.join(key_gods) if key_gods else '-'

        print(f'{rank:<4} {d.strftime("%Y-%m-%d"):<12} 周{wk:<2} {label:<8} {score:>3}  {stars:<10} {jc:<4} {xiu:<8} {key_str}')
        rank += 1

    print()
    print('=' * 140)
    print('【二、详细分析 (逐日)】')
    print('=' * 140)

    for d, label, verdict, score, reason, cn, lp, detail in results:
        wk = '一二三四五六日'[d.weekday()]
        stars = detail['stars']

        print(f'\n{"─"*120}')
        print(f'{d.strftime("%Y-%m-%d")} 周{wk} {label}  综合得分: {score}/100  {stars}  {verdict}')
        print(f'{"─"*120}')

        # 神煞详情
        print(f'  【协纪辨方书 神煞分析】')
        print(f'  吉神 ({detail["lucky_total"]:+d}分): {detail["lucky_gods"]}')
        print(f'  凶神 ({detail["unlucky_total"]:+d}分): {detail["unlucky_gods"]}')

        # 建除 + 星宿 + 黄道
        print(f'  【建除/星宿/黄道】')
        print(f'  建除: {detail["jc"]} ({detail["jc_score"]:+d}) | 二十八宿: {detail["xiu"]} ({detail["xiu_score"]:+d}) | {detail["huangdao"]} ({detail["hd_score"]:+d})')

        # 日等级
        print(f'  【日等级】 lv{detail["level"]} | {detail["level_name"]}')
        if detail['level'] is not None:
            lvl = detail['level']
            if lvl == 1 or lvl == -1:
                lvl_desc = '上吉'
            elif lvl == 2:
                lvl_desc = '吉'
            elif lvl == 3:
                lvl_desc = '中平'
            elif lvl == 4:
                lvl_desc = '次吉'
            else:
                lvl_desc = '凶'
            print(f'  日等级分: {detail["lvl_score"]:+d} ({lvl_desc})')

        # 双源黄历
        print(f'  【双源黄历一致性】')
        print(f'  cnlunar: 宜={" ".join(detail["cn_yi"]) if detail["cn_yi"] else "(无嫁娶条目)"}  忌={" ".join(detail["cn_ji"]) if detail["cn_ji"] else "(无)"}')
        print(f'  lunar-py: 宜={" ".join(detail["lp_yi"]) if detail["lp_yi"] else "(无嫁娶条目)"}  忌={" ".join(detail["lp_ji"]) if detail["lp_ji"] else "(无)"}')
        print(f'  双源分: {detail["dual_score"]:+d} | {detail["dual_source"]}')

        if detail['soft_warn']:
            print(f'  ⚠ 软警告: {detail["soft_warn"]}')

    # ── 汇总 ──
    print()
    print('=' * 140)
    print('【三、汇总统计】')
    print('=' * 140)

    strongly = [r for r in results if r[2] == 'strongly_recommended']
    recommended = [r for r in results if r[2] == 'recommended']
    acceptable = [r for r in results if r[2] == 'acceptable']
    marginal = [r for r in results if r[2] == 'marginal']
    not_rec = [r for r in results if r[2] == 'not_recommended']
    rejected = [r for r in results if r[2] == 'hard_reject']

    print(f'\n★★★★★ 强烈推荐 (≥80分): {len(strongly)}天')
    for r in strongly:
        print(f'  {r[0].strftime("%Y-%m-%d")} 周{"一二三四五六日"[r[0].weekday()]} {r[1]} 得分{r[3]}')

    print(f'\n★★★★ 推荐 (65-79分): {len(recommended)}天')
    for r in recommended:
        print(f'  {r[0].strftime("%Y-%m-%d")} 周{"一二三四五六日"[r[0].weekday()]} {r[1]} 得分{r[3]}')

    print(f'\n★★★ 可选 (50-64分): {len(acceptable)}天')
    for r in acceptable:
        print(f'  {r[0].strftime("%Y-%m-%d")} 周{"一二三四五六日"[r[0].weekday()]} {r[1]} 得分{r[3]}')

    print(f'\n★★ 勉强可选 (35-49分): {len(marginal)}天')
    for r in marginal:
        print(f'  {r[0].strftime("%Y-%m-%d")} 周{"一二三四五六日"[r[0].weekday()]} {r[1]} 得分{r[3]}')

    print(f'\n★ 不建议 (<35分): {len(not_rec)}天')
    for r in not_rec:
        print(f'  {r[0].strftime("%Y-%m-%d")} 周{"一二三四五六日"[r[0].weekday()]} {r[1]} 得分{r[3]}')

    print(f'\n✗ 硬毙: {len(rejected)}天')
    for r in rejected:
        print(f'  {r[0].strftime("%Y-%m-%d")} 周{"一二三四五六日"[r[0].weekday()]} {r[1]} -> {r[4][:60]}')

    print(f'\n调休上班日(不列入): 9/20(日)国庆调班, 10/10(六)国庆调班')

    return results


if __name__ == '__main__':
    results = main()
