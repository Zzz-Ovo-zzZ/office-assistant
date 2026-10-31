"""结婚择日 — 周末日历视图 + 宜嫁娶清单  2027-02-21 ~ 06-30  (自包含)"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from lunar_python import Solar

START = datetime(2027, 2, 21)
END = datetime(2027, 6, 30)

MARRIAGE_YI = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']
MARRIAGE_JI = ['嫁娶', '结婚姻', '纳采', '订婚', '婚姻', '纳征', '订盟']
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

QINGMING_DATES = set()
_tmp = Solar.fromYmd(2027, 3, 1).getLunar().getJieQiTable()
for _name, _solar in _tmp.items():
    if _name == '清明':
        QINGMING_DATES.add(datetime(_solar.getYear(), _solar.getMonth(), _solar.getDay()))

FIXED_HOLIDAYS = {datetime(2027,5,1):'劳动节', datetime(2027,5,4):'青年节', datetime(2027,6,1):'儿童节'}


def get_jianchu(lunar):
    m_idx = DIZHI.index(lunar.getMonthInGanZhiExact()[-1])
    d_idx = DIZHI.index(lunar.getDayInGanZhiExact()[-1])
    return JIANCHU[(d_idx - m_idx + 12) % 12]


def hard_reject(d, lunar):
    lm, ld = lunar.getMonth(), lunar.getDay()
    dz = lunar.getDayInGanZhiExact()[-1]
    if ld == 1: return True, '朔日'
    if ld == 15: return True, '望日'
    if ld in (5,14,23): return True, f'月忌初{ld}'
    if (lm,ld) in YANG_GONG: return True, '杨公忌'
    if dz == '午': return True, '冲鼠午日'
    if dz == '未': return True, '冲牛未日'
    if get_jianchu(lunar) == '破': return True, '破日'
    if d in QINGMING_DATES: return True, '清明'
    if (d+timedelta(days=1)) in QINGMING_DATES: return True, '清明前日'
    nj = lunar.getNextJieQi()
    if nj:
        nj_name = nj.getName() if hasattr(nj,'getName') else str(nj)
        if nj_name in EIGHT_JIEQI:
            nj_s = nj.getSolar() if hasattr(nj,'getSolar') else None
            if nj_s:
                nj_d = datetime(nj_s.getYear(), nj_s.getMonth(), nj_s.getDay())
                dl = (nj_d - d).days
                if dl == 0: return True, f'{nj_name}'
                if dl == 1: return True, f'{"四绝" if nj_name in ("立春","立夏","立秋","立冬") else "四离"}·{nj_name}前'
    jq = lunar.getJieQi()
    if jq:
        for j in jq:
            jn = j.getName() if hasattr(j,'getName') else str(j)
            if jn in EIGHT_JIEQI: return True, f'{jn}'
    return False, None


def score_day(d, lunar):
    score = 50
    yi = list(lunar.getDayYi()); ji = list(lunar.getDayJi())
    yi_marry = [x for x in yi if any(k in x for k in MARRIAGE_YI)]
    ji_marry = [x for x in ji if any(k in x for k in MARRIAGE_JI)]
    if yi_marry:
        if any('嫁娶' in x for x in yi_marry): score += 25
        elif any(x in ('纳采','订婚','订盟') for x in yi_marry): score += 15
        else: score += 10
    if ji_marry: score -= 25
    top_ji = [s for s in lunar.getDayJiShen() if s in TOP_LUCKY]; score += len(top_ji)*5
    top_xiong = [s for s in lunar.getDayXiongSha() if s in TOP_UNLUCKY]; score -= len(top_xiong)*5
    if lunar.getDayTianShenType() == '黄道': score += 8
    elif lunar.getDayTianShenType() == '黑道': score -= 8
    if lunar.getXiu() in GOOD_XIU: score += 5
    jc = get_jianchu(lunar)
    score += {'成':10,'定':8,'开':8,'除':5,'执':2,'危':-5,'闭':-5,'满':-3,'建':0,'平':0,'收':0}.get(jc,0)
    return max(0,min(100,score)), {
        '农历': f'{lunar.getMonth()}月{lunar.getDay()}日',
        '日柱': lunar.getDayInGanZhiExact(), '宜': yi_marry, '忌': ji_marry,
        '吉神': top_ji, '凶煞': top_xiong, '建除': jc, '星宿': lunar.getXiu(),
        '天神': f'{lunar.getDayTianShen()}({lunar.getDayTianShenType()})',
    }


def holiday_note(d, lunar):
    n = []
    if d in FIXED_HOLIDAYS: n.append(FIXED_HOLIDAYS[d])
    if lunar.getMonth() == 5 and lunar.getDay() == 5: n.append('端午节')
    return '·'.join(n)


def wk(d): return '一二三四五六日'[d.weekday()]


rows = []
d = START
while d <= END:
    if d.weekday() >= 5:
        solar = Solar.fromYmd(d.year, d.month, d.day)
        lunar = solar.getLunar()
        rej, reason = hard_reject(d, lunar)
        if rej: rows.append((d, '毙', reason, None, None))
        else:
            s, det = score_day(d, lunar); rows.append((d, '可', None, s, det))
    d += timedelta(days=1)

out = []
def w(s=''): out.append(s)

w('=' * 150)
w('结婚择日 周末日历  2027-02-21 ~ 06-30   (男鼠女牛, 无父母忌日)')
w('图例: ✅宜嫁娶(首选)  🔸宜纳采(次选)  ○无条目  ⚠忌嫁娶   ❌硬毙(冲煞/朔望/破日/四绝四离/清明等)')
w('=' * 150)

d = START
while d <= END:
    if d.weekday() == 5:
        sun = d + timedelta(days=1)
        def cell(dd):
            m = [r for r in rows if r[0] == dd]
            if not m: return ''
            dd_, status, reason, s, det = m[0]
            if status == '毙':
                return f'{dd_.strftime("%m-%d")} ❌{reason}'
            yi = det['宜']
            tag = '✅宜嫁娶' if any('嫁娶' in x for x in yi) else ('🔸宜纳采' if yi else '○无条目')
            if det['忌'] and any('嫁娶' in x for x in det['忌']): tag = '⚠忌嫁娶'
            hn = holiday_note(dd_, Solar.fromYmd(dd_.year, dd_.month, dd_.day).getLunar())
            return f'{dd_.strftime("%m-%d")} {s:>3}分 {tag}' + (f'[{hn}]' if hn else '')
        w(f'{d.strftime("%m-%d")}(六) {cell(d):<34}   {sun.strftime("%m-%d")}(日) {cell(sun)}')
        d += timedelta(days=7)
    else:
        d += timedelta(days=1)

w()
w('=' * 150)
w('一、宜嫁娶 的周末日 (龙岩正式场优先)')
w('=' * 150)
w(f'{"日期":<12}{"周":<3}{"得分":<5}{"农历":<9}{"日柱":<7}{"建除":<4}{"星宿":<4}{"吉神":<28}{"凶煞"}')
w('-' * 150)
for d, status, reason, s, det in rows:
    if status == '可' and det['宜'] and any('嫁娶' in x for x in det['宜']):
        w(f'{d.strftime("%Y-%m-%d"):<12}周{wk(d):<2}{s:<5}{det["农历"]:<9}{det["日柱"]:<7}{det["建除"]:<4}{det["星宿"]:<4}{",".join(det["吉神"]) or "-":<28}{",".join(det["凶煞"]) or "-"}')

w()
w('=' * 150)
w('二、宜纳采/订盟 的周末日 (江西两场可用)')
w('=' * 150)
w(f'{"日期":<12}{"周":<3}{"得分":<5}{"农历":<9}{"日柱":<7}{"建除":<4}{"星宿":<4}{"宜":<18}{"忌"}')
w('-' * 150)
for d, status, reason, s, det in rows:
    if status == '可' and det['宜'] and not any('嫁娶' in x for x in det['宜']):
        w(f'{d.strftime("%Y-%m-%d"):<12}周{wk(d):<2}{s:<5}{det["农历"]:<9}{det["日柱"]:<7}{det["建除"]:<4}{det["星宿"]:<4}{",".join(det["宜"]) or "-":<18}{",".join(det["忌"]) or "-"}')

w()
w('=' * 150)
w('三、可办但黄历"忌嫁娶" 的周末日 (不建议, 仅兜底)')
w('=' * 150)
w(f'{"日期":<12}{"周":<3}{"得分":<5}{"农历":<9}{"日柱":<7}{"建除":<4}{"星宿":<4}{"忌"}')
w('-' * 150)
for d, status, reason, s, det in rows:
    if status == '可' and det['忌'] and any('嫁娶' in x for x in det['忌']):
        w(f'{d.strftime("%Y-%m-%d"):<12}周{wk(d):<2}{s:<5}{det["农历"]:<9}{det["日柱"]:<7}{det["建除"]:<4}{det["星宿"]:<4}{",".join(det["忌"]) or "-"}')

w()
print('\n'.join(out))
