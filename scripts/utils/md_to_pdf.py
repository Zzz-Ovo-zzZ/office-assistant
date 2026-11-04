"""Markdown → HTML → PDF（使用系统 Edge 浏览器打印）

用法:
    python scripts/utils/md_to_pdf.py [输入.md] [输出.pdf]
不传参数时，默认处理 output/wedding/八字合婚/曾周x成林_八字合婚分析报告.md
"""
import markdown
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
DEFAULT_INPUT = BASE / 'output' / 'wedding' / '八字合婚' / '曾周x成林_八字合婚分析报告.md'

INPUT = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_INPUT)
OUTPUT_HTML = INPUT.replace('.md', '_print.html')
OUTPUT_PDF = sys.argv[2] if len(sys.argv) > 2 else INPUT.replace('.md', '.pdf')

if not os.path.exists(INPUT):
    raise SystemExit(f'找不到输入文件：{INPUT}\n用法：python scripts/utils/md_to_pdf.py <输入.md> [输出.pdf]')

# Edge 需要绝对路径，否则 file:/// 会解析错
OUTPUT_HTML = os.path.abspath(OUTPUT_HTML)
OUTPUT_PDF = os.path.abspath(OUTPUT_PDF)

with open(INPUT, 'r', encoding='utf-8') as f:
    md_content = f.read()

extensions = ['tables', 'fenced_code', 'codehilite', 'nl2br', 'sane_lists']
html_body = markdown.markdown(md_content, extensions=extensions)

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 2cm 2.2cm 2cm 2.2cm; }}
  body {{
    font-family: "Microsoft YaHei", "微软雅黑", "SimSun", sans-serif;
    font-size: 11pt; line-height: 1.9; color: #333;
    max-width: 100%; padding: 0;
  }}
  h1 {{ text-align: center; font-size: 24pt; color: #B8860B; margin: 1.5cm 0 0.6cm 0; page-break-before: avoid; }}
  h2 {{ font-size: 15pt; color: #B8860B; margin: 1.2cm 0 0.5cm 0; padding-bottom: 4px; border-bottom: 2px solid #e8c876; page-break-after: avoid; }}
  h3 {{ font-size: 12pt; color: #8B6914; margin: 0.8cm 0 0.3cm 0; page-break-after: avoid; }}
  p {{ margin: 0.4em 0; widows: 2; orphans: 2; }}
  table {{ border-collapse: collapse; width: 100%; margin: 0.5cm 0; font-size: 10pt; page-break-inside: avoid; }}
  th {{ background-color: #B8860B; color: white; padding: 7px 10px; text-align: center; font-weight: bold; }}
  td {{ padding: 6px 10px; border: 1px solid #e0d5b0; text-align: center; }}
  tr:nth-child(even) td {{ background-color: #FFF9F0; }}
  code {{ background: #FFF9F0; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; color: #5a3a10; }}
  pre {{ background: #FFF9F0; border: 1px solid #e8c876; border-radius: 6px; padding: 12px 16px; line-height: 1.6; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
  pre code {{ background: none; padding: 0; font-size: 9pt; }}
  blockquote {{ border-left: 4px solid #B8860B; margin: 0.5cm 0; padding: 8px 16px; background: #FFF9F0; color: #8B6914; }}
  hr {{ border: none; border-top: 1px solid #e0d5b0; margin: 0.8cm 0; }}
  strong {{ color: #5a3a10; }}
  p[align="center"] {{ text-align: center; }}
  @media print {{ body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} }}
</style>
</head>
<body>
{html_body}
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'HTML saved: {OUTPUT_HTML}')

# 使用 Edge 打印为 PDF
edge_paths = [
    shutil.which("msedge"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
edge_exe = next((p for p in edge_paths if p and os.path.exists(p)), None)

if edge_exe:
    cmd = [
        edge_exe,
        f'--headless=new',
        f'--disable-gpu',
        f'--no-pdf-header-footer',
        f'--print-to-pdf={OUTPUT_PDF}',
        f'--print-to-pdf-no-header',
        f'file:///{OUTPUT_HTML.replace(chr(92), "/")}'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0 and os.path.exists(OUTPUT_PDF):
        print(f'PDF saved: {OUTPUT_PDF}')
        print(f'Size: {os.path.getsize(OUTPUT_PDF)} bytes')
    else:
        print(f'Edge error: {result.stderr}')
        print(f'HTML ready for manual print: {OUTPUT_HTML}')
else:
    print(f'Edge not found. Open this in browser and print to PDF: {OUTPUT_HTML}')
