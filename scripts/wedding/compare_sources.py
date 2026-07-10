"""对比 cnlunar vs lunar-python 神煞数据，评估与协纪辨方书/通胜的一致程度"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from cnlunar import Lunar as CLunar
from lunar_python import Solar

MARRIAGE_KEYS = ['嫁娶','结婚姻','纳采','订婚','婚姻','纳征','订盟']

# 选取有代表性的一天深入对比
d = datetime(2026, 10, 3)
L = CLunar(datetime(d.year, d.month, d.day))
s = Solar.fromYmd(d.year, d.month, d.day)
lp = s.getLunar()

print("=" * 80)
print(f"深度对比: {d.strftime('%Y-%m-%d')} (国庆假期 周{'一二三四五六日'[d.weekday()]})")
print("=" * 80)

dz_cn = L.day8Char[-1]
dz_lp = lp.getDayInGanZhiExact()[-1]
print(f"\n日支: cnlunar={dz_cn} lunar-python={dz_lp} {'✓一致' if dz_cn==dz_lp else '✗不一致'}")

# ── 神煞对比 ──
print("\n── 吉神对比 ──")
cn_lucky = set(L.goodGodName)
lp_lucky = set(lp.getDayJiShen())
print(f"cnlunar ({len(cn_lucky)}个): {sorted(cn_lucky)}")
print(f"lunar-py ({len(lp_lucky)}个): {sorted(lp_lucky)}")
shared_lucky = cn_lucky & lp_lucky
print(f"交集 ({len(shared_lucky)}个): {sorted(shared_lucky)}")
print(f"仅cn: {sorted(cn_lucky - lp_lucky)}")
print(f"仅lp: {sorted(lp_lucky - cn_lucky)}")

print("\n── 凶神对比 ──")
cn_unlucky = set(L.badGodName)
lp_unlucky = set(lp.getDayXiongSha())
print(f"cnlunar ({len(cn_unlucky)}个): {sorted(cn_unlucky)}")
print(f"lunar-py ({len(lp_unlucky)}个): {sorted(lp_unlucky)}")
shared_unlucky = cn_unlucky & lp_unlucky
print(f"交集 ({len(shared_unlucky)}个): {sorted(shared_unlucky)}")
print(f"仅cn: {sorted(cn_unlucky - lp_unlucky)}")
print(f"仅lp: {sorted(lp_unlucky - cn_unlucky)}")

# ── 宜忌对比 ──
print("\n── 嫁娶宜忌对比 ──")
cn_yi = [x.strip() for x in (L.goodThing or [])]
cn_ji = [x.strip() for x in (L.badThing or [])]
cn_marry_yi = [x for x in cn_yi if any(k in x for k in MARRIAGE_KEYS)]
cn_marry_ji = [x for x in cn_ji if any(k in x for k in MARRIAGE_KEYS)]

lp_yi = list(lp.getDayYi())
lp_ji = list(lp.getDayJi())
lp_marry_yi = [x for x in lp_yi if any(k in x for k in MARRIAGE_KEYS)]
lp_marry_ji = [x for x in lp_ji if any(k in x for k in MARRIAGE_KEYS)]

print(f"cnlunar 宜: {cn_marry_yi}  忌: {cn_marry_ji}")
print(f"lunar-py 宜: {lp_marry_yi}  忌: {lp_marry_ji}")

# ── 建除/星宿/天神 ──
print("\n── 建除/星宿/天神/九星 ──")
print(f"cnlunar 建除: {L.today12DayOfficer} | 值神: {L.today12DayGod}")
print(f"cnlunar 星宿: {L.today28Star}")
print(f"lunar-py 星宿: {lp.getXiu()}")
print(f"lunar-py 天神: {lp.getDayTianShen()} type={lp.getDayTianShenType()} luck={lp.getDayTianShenLuck()}")
print(f"lunar-py 九星: {lp.getDayNineStar()}")

# ── 日等级 ──
print("\n── 综合等级 ──")
print(f"cnlunar: level={L.todayLevel} | {L.todayLevelName}")
print(f"lunar-py: 无直接日等级概念(通过天神luck判断: {lp.getDayTianShenLuck()})")

# ═══ 批量对比 9-10月所有休息日 ═══
print("\n" + "=" * 80)
print("批量对比：9-10月所有休息日的神煞重叠率")
print("=" * 80)

HOLIDAYS = {
    datetime(2026,9,25): '中秋', datetime(2026,9,26): '中秋', datetime(2026,9,27): '中秋',
}
for i in range(1,8):
    HOLIDAYS[datetime(2026,10,i)] = '国庆'
WORK_SATURDAYS = {datetime(2026,9,20): '', datetime(2026,10,10): ''}

cn_lucky_total = 0
lp_lucky_total = 0
shared_lucky_total = 0
cn_unlucky_total = 0
lp_unlucky_total = 0
shared_unlucky_total = 0
cn_yi_match = 0
cn_ji_match = 0
tot = 0

d2 = datetime(2026, 9, 1)
while d2 <= datetime(2026, 10, 31):
    if d2 in HOLIDAYS or (d2.weekday() >= 5 and d2 not in WORK_SATURDAYS):
        L2 = CLunar(datetime(d2.year, d2.month, d2.day))
        s2 = Solar.fromYmd(d2.year, d2.month, d2.day)
        lp2 = s2.getLunar()

        cn_g = set(L2.goodGodName)
        lp_g = set(lp2.getDayJiShen())
        cn_b = set(L2.badGodName)
        lp_b = set(lp2.getDayXiongSha())

        cn_lucky_total += len(cn_g)
        lp_lucky_total += len(lp_g)
        shared_lucky_total += len(cn_g & lp_g)
        cn_unlucky_total += len(cn_b)
        lp_unlucky_total += len(lp_b)
        shared_unlucky_total += len(cn_b & lp_b)

        # 嫁娶条目一致
        cn_m_yi = [x.strip() for x in (L2.goodThing or []) if any(k in x for k in MARRIAGE_KEYS)]
        lp_m_yi = [x for x in list(lp2.getDayYi()) if any(k in x for k in MARRIAGE_KEYS)]
        cn_m_ji = [x.strip() for x in (L2.badThing or []) if any(k in x for k in MARRIAGE_KEYS)]
        lp_m_ji = [x for x in list(lp2.getDayJi()) if any(k in x for k in MARRIAGE_KEYS)]

        if bool(cn_m_yi) == bool(lp_m_yi):
            cn_yi_match += 1  # 双方一致认为宜/不宜
        if bool(cn_m_ji) == bool(lp_m_ji):
            cn_ji_match += 1  # 双方一致认为忌/不忌

        tot += 1
    d2 += timedelta(days=1)

print(f"\n样本天数: {tot}")
print(f"\n吉神: cn总计{cn_lucky_total}个 lp总计{lp_lucky_total}个 交集{shared_lucky_total}个")
if cn_lucky_total > 0:
    print(f"  重叠率: cn视角 {shared_lucky_total/cn_lucky_total*100:.0f}% | lp视角 {shared_lucky_total/lp_lucky_total*100:.0f}%")
print(f"\n凶神: cn总计{cn_unlucky_total}个 lp总计{lp_unlucky_total}个 交集{shared_unlucky_total}个")
if cn_unlucky_total > 0:
    print(f"  重叠率: cn视角 {shared_unlucky_total/cn_unlucky_total*100:.0f}% | lp视角 {shared_unlucky_total/lp_unlucky_total*100:.0f}%")

print(f"\n嫁娶宜 一致性: {cn_yi_match}/{tot} ({cn_yi_match/tot*100:.0f}%)")
print(f"嫁娶忌 一致性: {cn_ji_match}/{tot} ({cn_ji_match/tot*100:.0f}%)")

print("\n" + "=" * 80)
print("结论")
print("=" * 80)
