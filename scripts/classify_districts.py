"""
惠和资产 - 片区划分 v2：每片区仅一位管理员
基于精确地址 + 高德坐标 + 管理员归属
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from collections import defaultdict
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 片区划分方案 - 核心原则：每个片区只有一位管理员
# ============================================================

SECTOR_MAP = {
    # ═══════════════ 陈晓芳 · 片区 ═══════════════

    # 1. 中山路商圈（中城核心）
    '中山路（五交化）':       '中山路商圈',
    '中山东路（商总）':       '中山路商圈',
    '中山路3期（糖酒）':      '中山路商圈',
    '凯丰商厦':              '中山路商圈',
    '凯丰商厦（国资、惠和）':  '中山路商圈',
    '凯丰商厦（国资）':       '中山路商圈',
    '老百货食堂大楼':         '中山路商圈',
    '老百货食堂宿舍':         '中山路商圈',
    '银河商业城A幢（糖酒）':  '中山路商圈',
    '银河商业城B幢（糖酒）':  '中山路商圈',

    # 2. 龙川中路片区（中城沿河）
    '龙川中路（五交化）':     '龙川中路片区',
    '龙川中路（惠发）':       '龙川中路片区',
    '龙川中路（糖酒）':       '龙川中路片区',

    # 3. 北环-解放片区（中城北）
    '北环西路23号':          '北环-解放片区',
    '北环西路66号':          '北环-解放片区',
    '北环西路67号':          '北环-解放片区',
    '解放北路（农机）':       '北环-解放片区',
    '和平路49号':            '北环-解放片区',
    '工农路D14#店':           '北环-解放片区',
    '挺秀花园2#楼':          '北环-解放片区',

    # 4. 罗龙-交易城片区（西城/北城结合部）
    '原交通大楼':            '罗龙-交易城片区',
    '原交通大楼外墙':         '罗龙-交易城片区',
    '罗龙东路220号':         '罗龙-交易城片区',
    '罗龙东路222号':         '罗龙-交易城片区',
    '罗龙东路（糖酒）':       '罗龙-交易城片区',
    '工业中路（糖酒）':       '罗龙-交易城片区',
    '闽西交易城（五交化）':   '罗龙-交易城片区',

    # 5. 九一南-莲新片区（西城）
    '九一南路3号':           '九一南-莲新片区',
    '九一南路3号二层':        '九一南-莲新片区',
    '九一南路3号地下室':      '九一南-莲新片区',
    '莲新南路4-2号':         '九一南-莲新片区',
    '莲新南路4-3号':         '九一南-莲新片区',
    '莲新南路4-4号':         '九一南-莲新片区',
    '莲新南路4-5号':         '九一南-莲新片区',
    '莲新南路（惠发）':       '九一南-莲新片区',
    '莲花大厦七层':          '九一南-莲新片区',
    '西安南路26-17号（国资）':'九一南-莲新片区',
    '登高西路（五交化）':     '九一南-莲新片区',
    '工业大厦':              '九一南-莲新片区',

    # 6. 登高东-溪南片区（南城）
    '兴晖社区':              '登高东-溪南片区',
    '原龙港公司':            '登高东-溪南片区',
    '登高东路（惠发）':       '登高东-溪南片区',
    '登高中路108-1号':       '登高东-溪南片区',
    '登高中路108-2号':       '登高东-溪南片区',
    '双泉路（酒厂）':         '登高东-溪南片区',
    '矿管大楼一层（惠发）':   '登高东-溪南片区',
    '挺秀路（惠发）':         '登高东-溪南片区',
    '龙岩图书馆（新华书吧）': '登高东-溪南片区',
    '曹溪管理站':            '登高东-溪南片区',

    # 7. 沁芳轩（西陂龙岩大道 单独片区）
    '沁芳轩':               '龙岩大道片区',

    # ═══════════════ 李美清 · 片区 ═══════════════

    # 8. 凤凰路片区（中城/西陂北部）
    '凤凰北路（棉纺）':       '凤凰路片区',
    '凤凰北路（粮油）':       '凤凰路片区',
    '凤凰路（二被）':         '凤凰路片区',
    '凤凰路（矿产）':         '凤凰路片区',

    # 9. 中山-龙川-解放片区（中城 李美清部分）
    '中山路（食品）':         '中山-龙川-解放片区',
    '九一北路（面粉加工厂）':  '中山-龙川-解放片区',
    '解放南路（商总）':       '中山-龙川-解放片区',
    '龙川中路（商总）':       '中山-龙川-解放片区',
    '龙川中路（食品）':       '中山-龙川-解放片区',

    # 10. 工业西-谢氨片区（北城）
    '工业西路(氨厂）':        '工业西-谢氨片区',
    '工业西路（食品）':       '工业西-谢氨片区',
    '谢氨路（氨厂）':         '工业西-谢氨片区',
    '罗龙西路（食品）':       '工业西-谢氨片区',

    # 11. 西安-塔泉片区（西城 李美清部分）
    '塔泉商厦（翔丰）':       '西安-塔泉片区',
    '塔泉大厦（翔丰）':       '西安-塔泉片区',
    '塔泉大厦（翔丰）龙津':   '西安-塔泉片区',
    '西安南路（食品）':       '西安-塔泉片区',
    '登高西路（燃料）':       '西安-塔泉片区',

    # 12. 西陂北片区（小洋-龙铁）
    '祥和家苑（化肥）':       '西陂北片区',
    '龙铁名苑（燃料）':       '西陂北片区',

    # 13. 溪畔-南环片区（南城 李美清部分）
    '南环中路（食品）':       '溪畔-南环片区',
    '溪畔路（燃料）':         '溪畔-南环片区',
    '登高中路（食品）':       '溪畔-南环片区',

    # 14. 曹溪片区
    '曹溪中路（液压）':       '曹溪片区',

    # 15. 东肖片区
    '东肖食品站':            '东肖片区',
    '东肖食品老站':          '东肖片区',

    # 16. 龙门片区
    '龙门镇（丝钉厂）':       '龙门片区',
    '龙门食品站':            '龙门片区',

    # 17. 小池-大池片区（远郊）
    '小池食品站':            '小池-大池片区',
    '大池食品站':            '小池-大池片区',

    # ═══════════════ 谢德胜 · 片区 ═══════════════

    # 18. 登高东美食广场
    '登高东美食广场':         '登高东美食广场片区',

    # ═══════════════ 暂无 · 片区 ═══════════════

    # 19. 东宝路
    '东宝路（矿产）':         '东宝路片区',
}

# 片区 → 管理员 + 行政区划
SECTOR_INFO = {
    '中山路商圈':         {'admin': '陈晓芳', 'area': '新罗区·中城街道'},
    '龙川中路片区':       {'admin': '陈晓芳', 'area': '新罗区·中城街道'},
    '北环-解放片区':      {'admin': '陈晓芳', 'area': '新罗区·中城街道/东城街道'},
    '罗龙-交易城片区':    {'admin': '陈晓芳', 'area': '新罗区·西城街道/北城街道'},
    '九一南-莲新片区':    {'admin': '陈晓芳', 'area': '新罗区·西城街道'},
    '登高东-溪南片区':    {'admin': '陈晓芳', 'area': '新罗区·南城街道/曹溪街道'},
    '龙岩大道片区':       {'admin': '陈晓芳', 'area': '新罗区·西陂街道'},
    '凤凰路片区':         {'admin': '李美清', 'area': '新罗区·中城街道/西陂街道'},
    '中山-龙川-解放片区': {'admin': '李美清', 'area': '新罗区·中城街道'},
    '工业西-谢氨片区':    {'admin': '李美清', 'area': '新罗区·北城街道'},
    '西安-塔泉片区':      {'admin': '李美清', 'area': '新罗区·西城街道'},
    '西陂北片区':         {'admin': '李美清', 'area': '新罗区·西陂街道'},
    '溪畔-南环片区':      {'admin': '李美清', 'area': '新罗区·南城街道'},
    '曹溪片区':           {'admin': '李美清', 'area': '新罗区·曹溪街道'},
    '东肖片区':           {'admin': '李美清', 'area': '新罗区·东肖镇'},
    '龙门片区':           {'admin': '李美清', 'area': '新罗区·龙门镇'},
    '小池-大池片区':      {'admin': '李美清', 'area': '新罗区·小池镇/大池镇'},
    '登高东美食广场片区': {'admin': '谢德胜', 'area': '新罗区·东城街道'},
    '东宝路片区':         {'admin': '暂无',   'area': '新罗区·东城街道'},
}

# 为每个管理员分配不同色系
ADMIN_COLORS = {
    '陈晓芳': ['DBE9FA', 'D6E4F0', 'BDD7EE', 'B4C6E7', 'C5D9F1', 'D2DEEE', 'DAE3F0'],
    '李美清': ['E2EFDA', 'D9EAD3', 'C6EFCE', 'D4EDDA', 'E0F0D8', 'DAEDD2', 'D0E8C0', 'C8E6C9', 'D2E9D5', 'CBE0D0'],
    '谢德胜': ['FFF2CC'],
    '暂无':   ['F2DCDB'],
}


def main():
    INPUT = r'd:\SynologyDrive\0资产管理录入文件\入场实施\资产数据\惠和资产片区划分规划表_2026.7.15.xlsx'
    OUTPUT = str(Path(__file__).parent.parent / 'output' / 'office' / '惠和资产片区划分结果_v2_2026.7.15.xlsx')

    wb = openpyxl.load_workbook(INPUT, data_only=True)
    ws = wb['Sheet1']

    out_wb = openpyxl.Workbook()

    # ── 样式 ──
    hdr_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
    hdr_fill = PatternFill(start_color='2F5496', end_color='2F5496', fill_type='solid')
    hdr_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    dt_font = Font(name='微软雅黑', size=10)
    dt_align = Alignment(vertical='center', wrap_text=True)
    ct_align = Alignment(horizontal='center', vertical='center')
    border = Border(
        left=Side(style='thin', color='B4C6E7'),
        right=Side(style='thin', color='B4C6E7'),
        top=Side(style='thin', color='B4C6E7'),
        bottom=Side(style='thin', color='B4C6E7'),
    )

    # 为每个片区预分配颜色
    admin_color_idx = defaultdict(int)
    sector_fills = {}
    for s_name, info in SECTOR_INFO.items():
        a = info['admin']
        palette = ADMIN_COLORS[a]
        idx = admin_color_idx[a] % len(palette)
        color = palette[idx]
        admin_color_idx[a] += 1
        sector_fills[s_name] = PatternFill(start_color=color, end_color=color, fill_type='solid')
        # 管理员颜色标记（片区名列背景）
        # 不额外处理，通过行底色区分管理员即可

    # ── Sheet1: 片区划分结果 ──
    out_ws = out_wb.active
    out_ws.title = '片区划分结果'

    headers = ['序号', '原项目名称', '管理员', '地址', '业主名称', '新片区', '行政区划']
    for col, h in enumerate(headers, 1):
        cell = out_ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = hdr_align
        cell.border = border

    widths = [6, 30, 9, 56, 42, 24, 30]
    for i, w in enumerate(widths, 1):
        out_ws.column_dimensions[chr(64 + i)].width = w

    stats = defaultdict(lambda: {'count': 0, 'admin': '', 'area': ''})
    row_idx = 2
    unmatched = 0

    for src_row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
        proj = str(src_row[0]).strip() if src_row[0] else ''
        admin = str(src_row[1]).strip() if src_row[1] else ''
        addr = str(src_row[2]).strip() if src_row[2] else ''
        owner = str(src_row[3]).strip() if src_row[3] else ''
        if 'XLOOKUP' in addr or addr == '0':
            addr = ''

        # 括号归一化匹配
        sector = SECTOR_MAP.get(proj)
        if sector is None:
            normalized = proj.replace('(', '（').replace(')', '）')
            sector = SECTOR_MAP.get(normalized, '【未分类】')

        if sector == '【未分类】':
            unmatched += 1

        info = SECTOR_INFO.get(sector, {'admin': '', 'area': ''})
        stats[sector]['count'] += 1
        stats[sector]['admin'] = info['admin']
        stats[sector]['area'] = info['area']

        row_data = [row_idx - 1, proj, admin, addr, owner, sector, info['area']]
        for col, val in enumerate(row_data, 1):
            cell = out_ws.cell(row=row_idx, column=col, value=val)
            cell.font = dt_font
            cell.border = border
            cell.alignment = ct_align if col in (1, 3, 6, 7) else dt_align
            # 片区底色
            fill = sector_fills.get(sector)
            if fill:
                cell.fill = fill

        row_idx += 1

    out_ws.freeze_panes = 'A2'
    # 自动筛选
    out_ws.auto_filter.ref = f'A1:G{row_idx - 1}'

    # ── Sheet2: 片区统计 ──
    stat_ws = out_wb.create_sheet('片区统计')
    stat_headers = ['序号', '片区名称', '负责管理员', '行政区划', '项目数']
    for col, h in enumerate(stat_headers, 1):
        cell = stat_ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = hdr_align
        cell.border = border

    stat_ws.column_dimensions['A'].width = 6
    stat_ws.column_dimensions['B'].width = 24
    stat_ws.column_dimensions['C'].width = 10
    stat_ws.column_dimensions['D'].width = 32
    stat_ws.column_dimensions['E'].width = 10

    # 按管理员分组排序
    admin_order = {'陈晓芳': 1, '李美清': 2, '谢德胜': 3, '暂无': 4}
    sorted_sectors = sorted(stats.items(),
                           key=lambda x: (admin_order.get(x[1]['admin'], 99), -x[1]['count']))

    total = 0
    for i, (s_name, s_info) in enumerate(sorted_sectors, 1):
        row_data = [i, s_name, s_info['admin'], s_info['area'], s_info['count']]
        for col, val in enumerate(row_data, 1):
            cell = stat_ws.cell(row=i + 1, column=col, value=val)
            cell.font = dt_font
            cell.border = border
            cell.alignment = ct_align
            fill = sector_fills.get(s_name)
            if fill:
                cell.fill = fill
        total += s_info['count']

    # 汇总行
    sr = len(sorted_sectors) + 2
    for col, val in enumerate(['', '合计（19个片区）', '', '', total], 1):
        cell = stat_ws.cell(row=sr, column=col, value=val)
        cell.font = Font(name='微软雅黑', size=10, bold=True)
        cell.border = border
        cell.alignment = ct_align

    stat_ws.freeze_panes = 'A2'

    # ── Sheet3: 管理员总览 ──
    admin_ws = out_wb.create_sheet('管理员总览')
    admin_headers = ['管理员', '片区数', '项目总数']
    for col, h in enumerate(admin_headers, 1):
        cell = admin_ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = hdr_align
        cell.border = border

    admin_ws.column_dimensions['A'].width = 12
    admin_ws.column_dimensions['B'].width = 10
    admin_ws.column_dimensions['C'].width = 12

    admin_stats = defaultdict(lambda: {'sectors': 0, 'projects': 0})
    for s_name, s_info in sorted_sectors:
        a = s_info['admin']
        admin_stats[a]['sectors'] += 1
        admin_stats[a]['projects'] += s_info['count']

    for i, (a, a_info) in enumerate(sorted(admin_stats.items(),
                                           key=lambda x: -x[1]['projects']), 1):
        for col, val in enumerate([a, a_info['sectors'], a_info['projects']], 1):
            cell = admin_ws.cell(row=i + 1, column=col, value=val)
            cell.font = dt_font
            cell.border = border
            cell.alignment = ct_align

    admin_ws.freeze_panes = 'A2'

    # ── 保存 ──
    out_wb.save(OUTPUT)

    # ── 打印报告 ──
    print(f'\n输出文件: {OUTPUT}')
    print(f'总记录: {row_idx - 2} 条 | 总项目: 82 个 | 片区: {len(stats)} 个')
    print(f'\n{"="*70}')
    print(f'{"片区名称":　<20s} {"管理员":　<6s} {"项目数":>5s}  {"行政区划"}')
    print(f'{"="*70}')
    for s_name, s_info in sorted_sectors:
        flag = '⚠' if s_name == '【未分类】' else '  '
        print(f'{flag}{s_name:　<18s} {s_info["admin"]:　<6s} {s_info["count"]:>5d}  {s_info["area"]}')
    print(f'{"="*70}')
    print(f'合计: {total} 个项目, {len(stats)} 个片区')

    if unmatched > 0:
        print(f'\n⚠ 未分类: {unmatched} 条记录')
    else:
        print(f'\n✅ 全部项目已分类，每片区仅一位管理员')


if __name__ == '__main__':
    main()
