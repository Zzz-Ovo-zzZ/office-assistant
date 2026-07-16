"""
惠和资产 - 片区划分 v3（最终版）
规则：一片区一业主（多业主房源除外）| 同业主+同管理员+邻近→合并 | 片区数不限
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from collections import defaultdict
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

# ════════════════════════════════════════════════════════
# 片区映射
# ════════════════════════════════════════════════════════

SECTOR_MAP = {
    # ═══════ 陈晓芳 · 片区 ═══════

    # ── 新罗国资 ──
    '中山路3期（糖酒）':          '新罗国资-中山路',
    '凯丰商厦（国资）':           '新罗国资-中山路',
    '老百货食堂大楼':            '新罗国资-中山路',
    '老百货食堂宿舍':            '新罗国资-中山路',
    '银河商业城A幢（糖酒）':      '新罗国资-中山路',
    '银河商业城B幢（糖酒）':      '新罗国资-中山路',
    '北环西路23号':              '新罗国资-北环解放',
    '北环西路66号':              '新罗国资-北环解放',
    '北环西路67号':              '新罗国资-北环解放',
    '挺秀花园2#楼':              '新罗国资-北环解放',
    '九一南路3号':               '新罗国资-九一南莲新',
    '九一南路3号二层':           '新罗国资-九一南莲新',
    '九一南路3号地下室':         '新罗国资-九一南莲新',
    '工业大厦':                  '新罗国资-九一南莲新',
    '西安南路26-17号（国资）':   '新罗国资-九一南莲新',
    '原交通大楼':                '新罗国资-罗龙交易城',
    '原交通大楼外墙':            '新罗国资-罗龙交易城',
    '罗龙东路220号':             '新罗国资-罗龙交易城',
    '罗龙东路222号':             '新罗国资-罗龙交易城',
    '罗龙东路（糖酒）':          '新罗国资-罗龙交易城',
    '曹溪管理站':                '新罗国资-曹溪',
    '沁芳轩':                    '新罗国资-龙岩大道',

    # ── 混合业主（多业主房源，保持合并）──
    '凯丰商厦（国资、惠和）':     '凯丰商厦（国资×五交化）',
    '凯丰商厦':                  '凯丰商厦（国资×五交化×饮食×果品）',

    # ── 惠成资产 ──
    '兴晖社区':                  '惠成资产-登高东',
    '挺秀路（惠发）':            '惠成资产-登高东',
    '登高东路（惠发）':          '惠成资产-登高东',
    '登高中路108-1号':           '惠成资产-登高东',
    '登高中路108-2号':           '惠成资产-登高东',
    '矿管大楼一层（惠发）':      '惠成资产-登高东',
    '龙岩图书馆（新华书吧）':    '惠成资产-登高东',
    '莲新南路4-2号':             '惠成资产-莲新',
    '莲新南路4-3号':             '惠成资产-莲新',
    '莲新南路4-4号':             '惠成资产-莲新',
    '莲新南路4-5号':             '惠成资产-莲新',
    '莲新南路（惠发）':          '惠成资产-莲新',
    '莲花大厦七层':              '惠成资产-莲新',
    '龙川中路（惠发）':          '惠成资产-龙川中路',

    # ── 惠和五交化 ──
    '中山路（五交化）':          '惠和五交化-中城',
    '龙川中路（五交化）':        '惠和五交化-中城',
    '登高西路（五交化）':        '惠和五交化-登高西路',
    '闽西交易城（五交化）':      '惠和五交化-交易城',

    # ── 惠华糖酒 ──
    '和平路49号':                '惠华糖酒-中城',
    '龙川中路（糖酒）':          '惠华糖酒-中城',

    # ── 其余陈晓芳业主 ──
    '中山东路（商总）':          '惠和商管-中山路',
    '双泉路（酒厂）':            '陈缸酿酒-双泉路',
    '原龙港公司':                '腾龙公路-登高东',
    '工业中路（糖酒）':          '糖酒公司-工业中路',
    '工农路D14#店':              '惠和农机-北环',
    '解放北路（农机）':          '惠和农机-北环',
    '西安南路（食品）':          '惠翔食品-西安南路（陈）',

    # ═══════ 李美清 · 片区 ═══════

    # ── 惠翔食品 ──
    '中山路（食品）':            '惠翔食品-中城',
    '龙川中路（食品）':          '惠翔食品-中城',
    '工业西路（食品）':          '惠翔食品-北城',
    '罗龙西路（食品）':          '惠翔食品-北城',
    '小池食品站':                '惠翔食品-小池大池',
    '大池食品站':                '惠翔食品-小池大池',
    '东肖食品站':                '惠翔食品-东肖',
    '东肖食品老站':              '惠翔食品-东肖',
    '南环中路（食品）':          '惠翔食品-南城登高',
    '登高中路（食品）':          '惠翔食品-南城登高',
    '龙门食品站':                '惠翔食品-龙门',

    # ── 惠和化肥 ──
    '工业西路(氨厂）':           '惠和化肥-北城',
    '谢氨路（氨厂）':            '惠和化肥-北城',
    '祥和家苑（化肥）':          '惠和化肥-西陂北',

    # ── 惠和燃料 ──
    '溪畔路（燃料）':            '惠和燃料-溪畔路',
    '登高西路（燃料）':          '惠和燃料-登高西路',
    '龙铁名苑（燃料）':          '惠和燃料-西陂北',

    # ── 其余李美清业主 ──
    '塔泉商厦（翔丰）':          '翔丰实业-塔泉西安',
    '塔泉大厦（翔丰）':          '翔丰实业-塔泉西安',
    '塔泉大厦（翔丰）龙津':      '龙津信用-塔泉西安',
    '曹溪中路（液压）':          '惠华液压-曹溪',
    '凤凰北路（棉纺）':          '惠和纺织-凤凰路',
    '凤凰北路（粮油）':          '粮油加工厂-凤凰路',
    '凤凰路（二被）':            '第二被单厂-凤凰路',
    '凤凰路（矿产）':            '矿产工业-凤凰路',
    '九一北路（面粉加工厂）':    '面粉加工厂-中山路',
    '解放南路（商总）':          '惠和商管-龙川解放',
    '龙川中路（商总）':          '惠和商管-龙川解放',
    '龙门镇（丝钉厂）':          '丝钉厂-龙门',

    # ═══════ 谢德胜 ──
    '登高东美食广场':            '新罗国资-美食广场',

    # ═══════ 暂无 ──
    '东宝路（矿产）':            '矿产工业-东宝路',
}

# 跨管理员覆写
ADMIN_SECTOR_OVERRIDE = {
    ('西安南路（食品）', '李美清'): '惠翔食品-西安南路（李）',
}

# ════════════════════════════════════════════════════════
# 片区信息
# ════════════════════════════════════════════════════════
SECTOR_INFO = {
    # 陈晓芳
    '新罗国资-中山路':                       {'admin': '陈晓芳', 'area': '新罗区·中城街道（中山路/中山东路/九一北路）'},
    '新罗国资-北环解放':                     {'admin': '陈晓芳', 'area': '新罗区·中城街道/东城街道（北环西路/解放路/和平路）'},
    '新罗国资-九一南莲新':                   {'admin': '陈晓芳', 'area': '新罗区·西城街道（九一南路/莲新南路）'},
    '新罗国资-罗龙交易城':                   {'admin': '陈晓芳', 'area': '新罗区·西城街道/北城街道（罗龙东路/交易城）'},
    '新罗国资-曹溪':                         {'admin': '陈晓芳', 'area': '新罗区·曹溪街道'},
    '新罗国资-龙岩大道':                     {'admin': '陈晓芳', 'area': '新罗区·西陂街道（龙岩大道交发沁芳轩）'},
    '凯丰商厦（国资×五交化）':               {'admin': '陈晓芳', 'area': '新罗区·中城街道（中山路凯丰商厦7层）'},
    '凯丰商厦（国资×五交化×饮食×果品）':     {'admin': '陈晓芳', 'area': '新罗区·中城街道（中山路凯丰商厦）'},
    '惠成资产-登高东':                       {'admin': '陈晓芳', 'area': '新罗区·南城街道（登高东路/挺秀路）'},
    '惠成资产-莲新':                         {'admin': '陈晓芳', 'area': '新罗区·西城街道（莲新南路/莲花大厦）'},
    '惠成资产-龙川中路':                     {'admin': '陈晓芳', 'area': '新罗区·中城街道（龙川中路）'},
    '惠和五交化-中城':                       {'admin': '陈晓芳', 'area': '新罗区·中城街道（中山路/龙川中路）'},
    '惠和五交化-登高西路':                   {'admin': '陈晓芳', 'area': '新罗区·西城街道（登高西路）'},
    '惠和五交化-交易城':                     {'admin': '陈晓芳', 'area': '新罗区·北城街道（闽西交易城）'},
    '惠华糖酒-中城':                         {'admin': '陈晓芳', 'area': '新罗区·中城街道（龙川中路/和平路）'},
    '惠和商管-中山路':                       {'admin': '陈晓芳', 'area': '新罗区·中城街道（中山东路）'},
    '陈缸酿酒-双泉路':                       {'admin': '陈晓芳', 'area': '新罗区·南城街道（双泉路）'},
    '腾龙公路-登高东':                       {'admin': '陈晓芳', 'area': '新罗区·南城街道（登高东路）'},
    '糖酒公司-工业中路':                     {'admin': '陈晓芳', 'area': '新罗区·中城街道（工业中路）'},
    '惠和农机-北环':                         {'admin': '陈晓芳', 'area': '新罗区·中城街道（北环西路/解放北路）'},
    '惠翔食品-西安南路（陈）':               {'admin': '陈晓芳', 'area': '新罗区·西城街道（西安南路）'},

    # 李美清
    '惠翔食品-中城':                         {'admin': '李美清', 'area': '新罗区·中城街道（中山路/龙川中路）'},
    '惠翔食品-北城':                         {'admin': '李美清', 'area': '新罗区·北城街道（工业西路/罗龙西路）'},
    '惠翔食品-小池大池':                     {'admin': '李美清', 'area': '新罗区·小池镇/大池镇'},
    '惠翔食品-东肖':                         {'admin': '李美清', 'area': '新罗区·东肖镇'},
    '惠翔食品-南城登高':                     {'admin': '李美清', 'area': '新罗区·南城街道（登高中路/南环中路）'},
    '惠翔食品-龙门':                         {'admin': '李美清', 'area': '新罗区·龙门镇'},
    '惠翔食品-西安南路（李）':               {'admin': '李美清', 'area': '新罗区·西城街道（西安南路）'},
    '惠和化肥-北城':                         {'admin': '李美清', 'area': '新罗区·北城街道（工业西路/谢氨路）'},
    '惠和化肥-西陂北':                       {'admin': '李美清', 'area': '新罗区·西陂街道（小洋祥和家苑）'},
    '惠和燃料-溪畔路':                       {'admin': '李美清', 'area': '新罗区·南城街道（溪畔路）'},
    '惠和燃料-登高西路':                     {'admin': '李美清', 'area': '新罗区·西城街道（登高西路）'},
    '惠和燃料-西陂北':                       {'admin': '李美清', 'area': '新罗区·西陂街道（双洋路龙铁名苑）'},
    '翔丰实业-塔泉西安':                     {'admin': '李美清', 'area': '新罗区·西城街道（西安南路塔泉大厦）'},
    '龙津信用-塔泉西安':                     {'admin': '李美清', 'area': '新罗区·西城街道（西安南路塔泉大厦）'},
    '惠华液压-曹溪':                         {'admin': '李美清', 'area': '新罗区·曹溪街道'},
    '惠和纺织-凤凰路':                       {'admin': '李美清', 'area': '新罗区·中城街道（凤凰北路）'},
    '粮油加工厂-凤凰路':                     {'admin': '李美清', 'area': '新罗区·中城街道（凤凰北路）'},
    '第二被单厂-凤凰路':                     {'admin': '李美清', 'area': '新罗区·中城街道（凤凰路）'},
    '矿产工业-凤凰路':                       {'admin': '李美清', 'area': '新罗区·中城街道（凤凰路）'},
    '惠和商管-龙川解放':                     {'admin': '李美清', 'area': '新罗区·中城街道（龙川中路/解放南路）'},
    '面粉加工厂-中山路':                     {'admin': '李美清', 'area': '新罗区·中城街道（九一北路）'},
    '丝钉厂-龙门':                           {'admin': '李美清', 'area': '新罗区·龙门镇'},

    # 谢德胜
    '新罗国资-美食广场':                     {'admin': '谢德胜', 'area': '新罗区·东城街道（登高东路美食广场）'},

    # 暂无
    '矿产工业-东宝路':                       {'admin': '暂无',   'area': '新罗区·东城街道（东宝路）'},
}

# 管理员色系
ADMIN_COLORS = {
    '陈晓芳': ['DBE9FA','D6E4F0','BDD7EE','B4C6E7','C5D9F1','D2DEEE','DAE3F0',
               'C9DAF3','D0E0F5','B8CAE8','CCD8EE','D4DFF2','C0D0E9','D8E4F6',
               'CEE0F8','D2E2F4','BED2EC','D6E2F0','CAE0F5','C4D4E8'],
    '李美清': ['E2EFDA','D9EAD3','C6EFCE','D4EDDA','E0F0D8','DAEDD2','D0E8C0',
               'C8E6C9','D2E9D5','CBE0D0','C8E0CC','D5E8D8','CDE4CE','D8ECD5',
               'C4E2C6','DCEED8','CCE5CA','D0E6CC','D6EAD2','CAE3CB','DEEED9',
               'C2E0C4'],
    '谢德胜': ['FFF2CC'],
    '暂无':   ['F2DCDB'],
}


def main():
    INPUT = r'd:\SynologyDrive\0资产管理录入文件\入场实施\资产数据\惠和资产片区划分规划表_2026.7.15.xlsx'
    OUTPUT = str(Path(__file__).parent.parent / 'output' / 'office' / '惠和资产片区划分结果_v3_2026.7.15.xlsx')

    wb = openpyxl.load_workbook(INPUT, data_only=True)
    ws = wb['Sheet1']
    out_wb = openpyxl.Workbook()

    hdr_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
    hdr_fill = PatternFill(start_color='2F5496', end_color='2F5496', fill_type='solid')
    hdr_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    dt_font = Font(name='微软雅黑', size=10)
    dt_align = Alignment(vertical='center', wrap_text=True)
    ct_align = Alignment(horizontal='center', vertical='center')
    border = Border(left=Side('thin','B4C6E7'),right=Side('thin','B4C6E7'),
                    top=Side('thin','B4C6E7'),bottom=Side('thin','B4C6E7'))

    admin_color_idx = defaultdict(int)
    sector_fills = {}
    for s_name, info in SECTOR_INFO.items():
        a = info['admin']
        p = ADMIN_COLORS[a]
        i = admin_color_idx[a] % len(p)
        admin_color_idx[a] += 1
        sector_fills[s_name] = PatternFill(start_color=p[i], end_color=p[i], fill_type='solid')

    # ── Sheet1 ──
    out_ws = out_wb.active
    out_ws.title = '片区划分结果'
    for col, h in enumerate(['序号','原项目名称','管理员','地址','业主名称','新片区','行政区划'], 1):
        c = out_ws.cell(row=1, column=col, value=h)
        c.font, c.fill, c.alignment, c.border = hdr_font, hdr_fill, hdr_align, border

    for i, w in enumerate([6,30,9,56,42,34,48], 1):
        out_ws.column_dimensions[chr(64+i)].width = w

    stats = defaultdict(lambda: {'count': 0, 'projects': set(), 'admin': '', 'area': ''})
    row_idx, unmatched = 2, 0

    for src_row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
        proj = str(src_row[0]).strip() if src_row[0] else ''
        admin = str(src_row[1]).strip() if src_row[1] else ''
        addr = str(src_row[2]).strip() if src_row[2] else ''
        owner = str(src_row[3]).strip() if src_row[3] else ''
        if 'XLOOKUP' in addr or addr == '0': addr = ''

        sector = ADMIN_SECTOR_OVERRIDE.get((proj, admin))
        if sector is None:
            sector = SECTOR_MAP.get(proj)
            if sector is None:
                sector = SECTOR_MAP.get(proj.replace('(','（').replace(')','）'), '【未分类】')

        if sector == '【未分类】': unmatched += 1

        info = SECTOR_INFO.get(sector, {'admin':'','area':''})
        stats[sector]['count'] += 1
        stats[sector]['projects'].add(proj)
        stats[sector]['admin'] = info['admin']
        stats[sector]['area'] = info['area']

        for col, val in enumerate([row_idx-1, proj, admin, addr, owner, sector, info['area']], 1):
            c = out_ws.cell(row=row_idx, column=col, value=val)
            c.font, c.border = dt_font, border
            c.alignment = ct_align if col in (1,3,6,7) else dt_align
            if sector_fills.get(sector): c.fill = sector_fills[sector]
        row_idx += 1

    out_ws.freeze_panes = 'A2'
    out_ws.auto_filter.ref = f'A1:G{row_idx-1}'

    # ── Sheet2: 片区统计 ──
    stat_ws = out_wb.create_sheet('片区统计')
    for col, h in enumerate(['序号','片区名称','负责管理员','行政区划','项目数','记录数'], 1):
        c = stat_ws.cell(row=1, column=col, value=h)
        c.font, c.fill, c.alignment, c.border = hdr_font, hdr_fill, hdr_align, border

    for i, w in enumerate([6,34,10,52,10,10], 1):
        stat_ws.column_dimensions[chr(64+i)].width = w

    admin_order = {'陈晓芳':1,'李美清':2,'谢德胜':3,'暂无':4}
    sorted_sectors = sorted(stats.items(), key=lambda x: (admin_order.get(x[1]['admin'],99), -x[1]['count']))
    total_records, total_projects = 0, set()

    for i, (sn, si) in enumerate(sorted_sectors, 1):
        for col, val in enumerate([i, sn, si['admin'], si['area'], len(si['projects']), si['count']], 1):
            c = stat_ws.cell(row=i+1, column=col, value=val)
            c.font, c.border = dt_font, border
            c.alignment = ct_align
            if sector_fills.get(sn): c.fill = sector_fills[sn]
        total_records += si['count']
        total_projects.update(si['projects'])

    sr = len(sorted_sectors) + 2
    for col, val in enumerate(['', f'合计（{len(stats)}个片区）','','',len(total_projects),total_records], 1):
        c = stat_ws.cell(row=sr, column=col, value=val)
        c.font = Font(name='微软雅黑', size=10, bold=True)
        c.border, c.alignment = border, ct_align
    stat_ws.freeze_panes = 'A2'

    # ── Sheet3: 管理员总览 ──
    admin_ws = out_wb.create_sheet('管理员总览')
    for col, h in enumerate(['管理员','片区数','记录总数'], 1):
        c = admin_ws.cell(row=1, column=col, value=h)
        c.font, c.fill, c.alignment, c.border = hdr_font, hdr_fill, hdr_align, border

    for i, w in enumerate([12,10,12], 1):
        admin_ws.column_dimensions[chr(64+i)].width = w

    admin_stats = defaultdict(lambda: {'sectors':0,'records':0})
    for sn, si in sorted_sectors:
        admin_stats[si['admin']]['sectors'] += 1
        admin_stats[si['admin']]['records'] += si['count']

    for i, (a, ai) in enumerate(sorted(admin_stats.items(), key=lambda x: -x[1]['records']), 1):
        for col, val in enumerate([a, ai['sectors'], ai['records']], 1):
            c = admin_ws.cell(row=i+1, column=col, value=val)
            c.font, c.border, c.alignment = dt_font, border, ct_align
    admin_ws.freeze_panes = 'A2'

    # ── Sheet4: 业主片区对照 ──
    import pandas as pd
    src_df = pd.read_excel(INPUT)
    src_df.columns = ['原项目名称','管理员','地址','业主名称']

    def get_sector(row):
        p, a = str(row['原项目名称']).strip(), str(row['管理员']).strip()
        return (ADMIN_SECTOR_OVERRIDE.get((p, a)) or
                SECTOR_MAP.get(p) or
                SECTOR_MAP.get(p.replace('(','（').replace(')','）'), '?'))

    src_df['新片区'] = src_df.apply(get_sector, axis=1)
    own_ws = out_wb.create_sheet('业主片区对照')
    for col, h in enumerate(['序号','业主名称','涉及片区数','涉及片区列表','项目数','记录数'], 1):
        c = own_ws.cell(row=1, column=col, value=h)
        c.font, c.fill, c.alignment, c.border = hdr_font, hdr_fill, hdr_align, border

    for i, w in enumerate([6,44,12,80,10,10], 1):
        own_ws.column_dimensions[chr(64+i)].width = w

    own_stats = src_df.groupby('业主名称').agg(
        涉及片区=('新片区',lambda x: ', '.join(sorted(x.unique()))),
        片区数=('新片区','nunique'), 项目数=('原项目名称','nunique'),
        记录数=('原项目名称','count')).reset_index().sort_values('记录数', ascending=False)

    for i, (_, row) in enumerate(own_stats.iterrows(), 1):
        for col, val in enumerate([i, row['业主名称'], row['片区数'], row['涉及片区'], row['项目数'], row['记录数']], 1):
            c = own_ws.cell(row=i+1, column=col, value=val)
            c.font, c.border = dt_font, border
            c.alignment = ct_align if col in (1,3,5,6) else dt_align
    own_ws.freeze_panes = 'A2'

    out_wb.save(OUTPUT)

    n = len(stats)
    print(f'\n{"="*85}')
    print(f'{"片区名称":　<34s} {"管理员":　<6s} {"记录":>4s}  {"行政区划"}')
    print(f'{"="*85}')
    for sn, si in sorted_sectors:
        fg = '⚠' if sn == '【未分类】' else '  '
        print(f'{fg}{sn:　<32s} {si["admin"]:　<6s} {si["count"]:>4d}  {si["area"]}')
    print(f'{"="*85}')
    print(f'合计: {total_records}条记录, {n}个片区, {len(total_projects)}个项目')
    print(f'\n{"✅" if unmatched==0 else f"⚠ 未分类:{unmatched}条"} 每片区仅一位业主（多业主房源除外）')

    # 验证多业主
    multi = src_df.groupby('新片区')['业主名称'].nunique()
    bad = multi[multi > 1]
    for sec in bad.index:
        owners = src_df[src_df['新片区']==sec]['业主名称'].unique()
        is_mixed_property = any('、' in o for o in owners)
        if not is_mixed_property:
            print(f'  ⚠ 非多业主房源却有多业主: [{sec}] → {list(owners)}')


if __name__ == '__main__':
    main()
