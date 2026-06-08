"""MD → HTML 浏览器精确渲染"""
import markdown
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, 'output', '八字合婚分析报告_20260608.md')
OUTPUT = os.path.join(BASE, 'output', '八字合婚分析报告_20260608.html')

with open(INPUT, 'r', encoding='utf-8') as f:
    md = f.read()

# Python markdown 精确转换
extensions = ['tables', 'fenced_code', 'codehilite', 'nl2br', 'sane_lists']
body = markdown.markdown(md, extensions=extensions)

# 修正 align 属性
body = body.replace('<p align="center">', '<p class="ac">')
body = re.sub(r'<td[^>]*align="center"[^>]*>', '<td>', body)

html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>八字合婚分析报告</title>
<style>
  *,*::before,*::after{box-sizing:border-box}
  body{
    margin:0;padding:10px;font-family:-apple-system,"Microsoft YaHei","PingFang SC","SimSun",sans-serif;
    font-size:15px;line-height:1.85;color:#1f2328;background:#f6f8fa;
  }
  .md{
    max-width:880px;margin:0 auto;background:#fff;border-radius:6px;
    padding:36px 44px;border:1px solid #d0d7de;
  }
  @media(max-width:640px){body{padding:4px}.md{padding:18px 14px;border-radius:0;font-size:14px}}

  .md h1{font-size:1.9em;border-bottom:1px solid #d8dee4;padding-bottom:.3em;margin:20px 0 14px}
  .md h2{font-size:1.4em;border-bottom:1px solid #d8dee4;padding-bottom:.25em;margin:30px 0 14px}
  .md h3{font-size:1.15em;margin:22px 0 12px}
  .md h4{font-size:1.05em;margin:16px 0 8px}

  .md p{margin:0 0 14px}
  .md p.ac{text-align:center}

  .md table{border-collapse:collapse;width:100%;margin:14px 0;font-size:.92em;display:block;overflow-x:auto}
  .md th,.md td{padding:7px 12px;border:1px solid #d0d7de;text-align:center}
  .md th{background:#f6f8fa;font-weight:600}
  .md tr:nth-child(even) td{background:#fafbfc}

  .md code{background:rgba(175,184,193,.2);padding:2px 5px;border-radius:3px;font-family:"Cascadia Code",Consolas,"SimSun",monospace;font-size:.88em}
  .md pre{background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;padding:14px 16px;overflow-x:auto;line-height:1.55;margin:14px 0}
  .md pre code{background:none;padding:0;font-size:.82em;white-space:pre}

  .md blockquote{border-left:3px solid #d0d7de;margin:0 0 14px;padding:2px 14px;color:#656d76}
  .md blockquote p{margin:8px 0}

  .md hr{border:0;border-bottom:1px solid #d8dee4;margin:28px 0}
  .md strong{font-weight:600}
  .md a{color:#0969da}

  @media print{
    body{background:#fff;padding:0}
    .md{border:none;border-radius:0;max-width:100%;padding:0 1cm}
    @page{margin:1.2cm}
  }
</style>
</head>
<body>
<div class="md">
''' + body + '''
</div>
</body>
</html>'''

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

sz = os.path.getsize(OUTPUT) / 1024
print(f'HTML: {OUTPUT}')
print(f'Size: {sz:.1f} KB')
