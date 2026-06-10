"""探索 cnlunar 和 lunar-python 的神煞数据"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from cnlunar import Lunar as CLunar
from lunar_python import Solar

HOLIDAYS = {
    datetime(2026,9,25): '中秋假期', datetime(2026,9,26): '中秋假期', datetime(2026,9,27): '中秋假期',
}
for i in range(1,8):
    HOLIDAYS[datetime(2026,10,i)] = '国庆假期'
WORK_SATURDAYS = {datetime(2026,9,20): '国庆调班', datetime(2026,10,10): '国庆调班'}

MARRIAGE_KEYS = ['嫁娶','结婚姻','纳采','订婚','婚姻','纳征','订盟']

d = datetime(2026, 9, 1)
while d <= datetime(2026, 10, 31):
    if d in HOLIDAYS or (d.weekday() >= 5 and d not in WORK_SATURDAYS):
        L = CLunar(datetime(d.year, d.month, d.day))
        s = Solar.fromYmd(d.year, d.month, d.day)
        lp = s.getLunar()

        wk = '一二三四五六日'[d.weekday()]
        label = HOLIDAYS.get(d, '周末')

        gn = L.goodGodName
        bn = L.badGodName
        lvl = L.todayLevel
        lvl_name = L.todayLevelName[:80]
        jc = L.today12DayOfficer
        jc_god = L.today12DayGod
        xiu = L.today28Star
        m3 = L.zodiacMark3List
        m6 = L.zodiacMark6
        clash = L.chineseZodiacClash

        cn_yi = [x.strip() for x in (L.goodThing or [])]
        cn_ji = [x.strip() for x in (L.badThing or [])]
        m_yi = [x for x in cn_yi if any(k in x for k in MARRIAGE_KEYS)]
        m_ji = [x for x in cn_ji if any(k in x for k in MARRIAGE_KEYS)]

        lp_yi = list(lp.getDayYi())
        lp_ji = list(lp.getDayJi())
        lp_m_yi = [x for x in lp_yi if any(k in x for k in MARRIAGE_KEYS)]
        lp_m_ji = [x for x in lp_ji if any(k in x for k in MARRIAGE_KEYS)]

        dz = L.day8Char[-1]

        print(f'{d.strftime("%Y-%m-%d")} | {wk} | {label:<6} | {dz} | lv{lvl} | {jc}({jc_god}) | {xiu} | '
              f'J吉:{len(gn)}={gn[:5]} | J凶:{len(bn)}={bn[:5]} | '
              f'cn宜婚:{m_yi} cn忌婚:{m_ji} | lp宜婚:{lp_m_yi} lp忌婚:{lp_m_ji} | '
              f'冲:{clash} | m3:{m3} m6:{m6}')
    d += timedelta(days=1)
