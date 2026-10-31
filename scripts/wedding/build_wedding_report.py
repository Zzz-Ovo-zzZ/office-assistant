"""结婚择日报告 MD → HTML(屏幕版) + PDF(打印版)"""
import markdown, os, re, subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'F:\AI\office-assistant\output\wedding\结婚择日'
MD = os.path.join(BASE, '结婚三场连排方案_2027年5月.md')
HTML = os.path.join(BASE, '结婚三场连排方案_2027年5月.html')
PRINT_HTML = MD.replace('.md', '_print.html')
PDF = MD.replace('.md', '.pdf')

with open(MD, encoding='utf-8') as f:
    md = f.read()

extensions = ['tables', 'fenced_code', 'codehilite', 'nl2br', 'sane_lists']
body = markdown.markdown(md, extensions=extensions)
body = body.replace('<p align="center">', '<p class="ac">')
body = re.sub(r'<td[^>]*align="center"[^>]*>', '<td>', body)

TITLE = '结婚三场连排方案'

# ── 屏幕版 HTML ──
screen_css = """
  *,*::before,*::after{box-sizing:border-box}
  body{margin:0;padding:10px;font-family:-apple-system,"Microsoft YaHei","PingFang SC","SimSun",sans-serif;
    font-size:15px;line-height:1.85;color:#1f2328;background:#f6f8fa}
  .md{max-width:880px;margin:0 auto;background:#fff;border-radius:6px;padding:36px 44px;border:1px solid #d0d7de}
  @media(max-width:640px){body{padding:4px}.md{padding:18px 14px;border-radius:0;font-size:14px}}
  .md h1{font-size:1.9em;border-bottom:1px solid #d8dee4;padding-bottom:.3em;margin:20px 0 14px}
  .md h2{font-size:1.4em;border-bottom:1px solid #d8dee4;padding-bottom:.25em;margin:30px 0 14px}
  .md h3{font-size:1.15em;margin:22px 0 12px}
  .md p{margin:0 0 14px}.md p.ac{text-align:center}
  .md table{border-collapse:collapse;width:100%;margin:14px 0;font-size:.92em;display:block;overflow-x:auto}
  .md th,.md td{padding:7px 12px;border:1px solid #d0d7de;text-align:center}
  .md th{background:#f6f8fa;font-weight:600}
  .md tr:nth-child(even) td{background:#fafbfc}
  .md code{background:rgba(175,184,193,.2);padding:2px 5px;border-radius:3px;font-family:Consolas,"SimSun",monospace;font-size:.88em}
  .md pre{background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;padding:14px 16px;overflow-x:auto;line-height:1.55;margin:14px 0}
  .md pre code{background:none;padding:0;font-size:.82em;white-space:pre}
  .md blockquote{border-left:3px solid #d0d7de;margin:0 0 14px;padding:2px 14px;color:#656d76}
  .md hr{border:0;border-bottom:1px solid #d8dee4;margin:28px 0}
  .md strong{font-weight:600}
  @media print{body{background:#fff;padding:0}.md{border:none;border-radius:0;max-width:100%;padding:0 1cm}@page{margin:1.2cm}}
"""

screen_html = ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
               '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
               f'<title>{TITLE}</title><style>{screen_css}</style></head>'
               f'<body><div class="md">{body}</div></body></html>')

with open(HTML, 'w', encoding='utf-8') as f:
    f.write(screen_html)
print(f'HTML: {HTML}  ({os.path.getsize(HTML)/1024:.1f} KB)')

# ── 打印版 HTML + PDF ──
print_css = """
  @page{size:A4;margin:2cm 2.2cm}
  body{font-family:"Microsoft YaHei","微软雅黑","SimSun",sans-serif;font-size:11pt;line-height:1.9;color:#333;max-width:100%}
  h1{text-align:center;font-size:24pt;color:#B8860B;margin:1.5cm 0 .6cm;page-break-before:avoid}
  h2{font-size:15pt;color:#B8860B;margin:1.2cm 0 .5cm;padding-bottom:4px;border-bottom:2px solid #e8c876;page-break-after:avoid}
  h3{font-size:12pt;color:#8B6914;margin:.8cm 0 .3cm;page-break-after:avoid}
  p{margin:.4em 0;widows:2;orphans:2}
  table{border-collapse:collapse;width:100%;margin:.5cm 0;font-size:10pt;page-break-inside:avoid}
  th{background:#B8860B;color:#fff;padding:7px 10px;text-align:center;font-weight:bold}
  td{padding:6px 10px;border:1px solid #e0d5b0;text-align:center}
  tr:nth-child(even) td{background:#FFF9F0}
  code{background:#FFF9F0;padding:1px 4px;border-radius:3px;font-size:9.5pt;color:#5a3a10}
  pre{background:#FFF9F0;border:1px solid #e8c876;border-radius:6px;padding:12px 16px;line-height:1.6;overflow-x:auto;white-space:pre-wrap;word-wrap:break-word}
  pre code{background:none;padding:0;font-size:9pt}
  blockquote{border-left:4px solid #B8860B;margin:.5cm 0;padding:8px 16px;background:#FFF9F0;color:#8B6914}
  hr{border:none;border-top:1px solid #e0d5b0;margin:.8cm 0}
  strong{color:#5a3a10}
  @media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

print_html = (f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
              f'<title>{TITLE}</title><style>{print_css}</style></head>'
              f'<body>{body}</body></html>')

with open(PRINT_HTML, 'w', encoding='utf-8') as f:
    f.write(print_html)
print(f'PRINT_HTML: {PRINT_HTML}')

# ── Edge 打印为 PDF ──
edge_paths = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
edge_exe = next((p for p in edge_paths if os.path.exists(p)), None)

if edge_exe:
    cmd = [edge_exe, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
           f'--print-to-pdf={PDF}', '--print-to-pdf-no-header',
           'file:///' + PRINT_HTML.replace(chr(92), '/')]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode == 0 and os.path.exists(PDF):
        print(f'PDF: {PDF}  ({os.path.getsize(PDF)} bytes)')
    else:
        print(f'Edge 打印失败: {r.stderr}')
        print(f'可手动用浏览器打开 {PRINT_HTML} 打印为 PDF')
else:
    print('未找到 Edge,请用浏览器打开 print html 手动打印为 PDF')
