# KK网信息采集工具

> 龙岩本地最大社区论坛（www.0597kk.com）的定向信息采集方案
> 创建：2026-07-21

---

## 一、KK网资源价值分析

### 1.1 网站概况

| 项目 | 详情 |
|------|------|
| 域名 | www.0597kk.com |
| 类型 | Discuz! X3.2 论坛 |
| 运营方 | 龙岩市新罗区尚酷文化传媒有限公司 |
| 注册会员 | ~34万 |
| 日发帖量 | ~1.2万 |
| 分类平台 | 淘淘居 (taotaoju.vip) — 同公司旗下 |

### 1.2 对康养业务有价值的版块

| 优先级 | 版块 | fid | 价值 | 采集频率建议 |
|--------|------|-----|------|------------|
| 🔴 高 | **龙岩热点** | 2 | 本地医院讨论、民生话题、求助帖 | 每日 |
| 🔴 高 | **家政服务** | 205 | 保姆/护工需求（淘淘居 catid=232） | 每日 |
| 🟡 中 | **商家信息** | 175 | 竞品广告、同类服务推广 | 每周 |
| 🟡 中 | **谈天说地** | 19 | 生活求助、社区讨论 | 每周 |
| 🟡 中 | **东城/西陂/北城街道** | 735-737 | 社区动态、政务通知 | 每周 |
| 🟢 低 | **法律咨询** | 121 | 养老纠纷、继承等法律需求 | 每月 |
| 🟢 低 | **求职招聘** | 159 | 了解竞品招聘（判断扩张） | 每月 |

### 1.3 目标信息类型

| 信息类型 | 示例 | 业务价值 |
|----------|------|---------|
| **潜在客户** | "家里老人中风后怎么康复" | 直接线索 |
| **护工需求** | "求推荐靠谱护工/保姆" | 反向获客 |
| **医院讨论** | "XX医院骨科哪个医生好" | 了解医生口碑 |
| **竞品动态** | "XX养老院开业/搞活动" | 竞争情报 |
| **政策信息** | "龙岩养老服务补贴申请" | 政策跟进 |
| **社区动态** | "社区老年活动中心通知" | 渠道切入机会 |

---

## 二、三种采集方案

### 方案一：搜索引擎 site 查询（推荐，反爬无忧）✅

通过 Google/Bing 的 `site:0597kk.com` 语法搜索，完全绕过 KK 网反爬。

```bash
# Google 搜索示例（需在浏览器中执行）
site:0597kk.com 养老 OR 康养 OR 康复
site:0597kk.com 护工 OR 保姆 OR 陪护
site:0597kk.com 医院 骨科 OR 神经内科
site:0597kk.com "万龄"
```

**优点：** 无封禁风险，搜索结果质量高
**缺点：** 有延迟（非实时），频率受限

### 方案二：Archiver 页面定时抓取 ⚠️

Discuz! Archiver 是简化版页面（无 JS），理论上更容易抓取。

URL 格式：
```
https://www.0597kk.com/archiver/fid-{版块ID}.html?page={页码}
https://www.0597kk.com/archiver/tid-{帖子ID}.html
```

**注意：** KK 网有频率限制，触发 403 后需要更换 IP 或等待冷却。建议：
- 每次请求间隔 ≥ 3 秒
- 单次运行不超过 5 页
- 使用住宅 IP 或代理池

### 方案三：淘淘居分类信息页 ✅

淘淘居是 KK 网旗下的分类信息平台，`保姆/护工` 分类是直接线索来源。

```
http://www.taotaoju.vip/category-catid-232.html  # 保姆/护工
http://www.taotaoju.vip/category-catid-1.html    # 家政服务（全部）
```

筛选参数：
- 区域：areaid=2(新罗区) / 3(永定) / 4(上杭) / 5(长汀) / 6(武平) / 7(连城) / 8(漳平)

---

## 三、Python 采集脚本

### 3.1 基于 Google 搜索的版本（稳定方案）

```python
"""
KK网信息采集器 - Google Site Search 版本
输出：匹配康养关键词的帖子列表（JSON格式）
"""

import urllib.request
import urllib.parse
import re
import json
import time
from datetime import datetime

# ===== 配置 =====
SEARCH_QUERIES = [
    'site:0597kk.com 养老 OR 康养 OR 康复',
    'site:0597kk.com 护工 OR 保姆 OR 陪护 OR 护理',
    'site:0597kk.com 医院 骨科 OR 神经内科 OR 康复科',
    'site:0597kk.com 老人 OR 老年 OR 长者',
    'site:0597kk.com 万龄 OR 养老院 OR 福利院',
    'site:taotaoju.vip 护工 OR 老人 OR 护理',
]

BUSINESS_KEYWORDS = [
    # 高价值（直接线索）
    '养老', '康养', '康复', '护工', '保姆', '陪护', '护理',
    '失能', '卧床', '术后', '中风', '偏瘫', '不能自理',
    # 中价值（市场情报）
    '骨科', '神经内科', '康复科', '养老院', '福利院', '敬老院',
    '万龄', '同心圆', '红炭山', '晟佳园',
    # 低价值（背景信息）
    '老人', '老年', '长者', '老龄化', '退休',
]

# ===== 生成搜索 URL =====
def make_google_search_url(query, start=0):
    """生成 Google 搜索 URL（注意：频繁调用可能触发验证码）"""
    params = urllib.parse.urlencode({
        'q': query,
        'start': start,
        'num': 20,
        'hl': 'zh-CN',
    })
    return f'https://www.google.com/search?{params}'

# ===== 从搜索结果 HTML 提取链接 =====
def extract_kk_links(html):
    """从 Google 搜索结果页提取 0597kk.com 的链接和标题"""
    # 匹配 Google 搜索结果条目
    pattern = r'<a href="(https?://(?:www\.)?0597kk\.com/[^"]+)"[^>]*>\s*<h3[^>]*>(.*?)</h3>'
    matches = re.findall(pattern, html, re.DOTALL)
    
    results = []
    for url, title_raw in matches:
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        # 提取帖子ID
        tid_match = re.search(r'thread-(\d+)', url)
        results.append({
            'url': url,
            'title': title,
            'tid': tid_match.group(1) if tid_match else None,
            'source': 'google_search',
            'found_at': datetime.now().isoformat()
        })
    return results

# ===== 关键词匹配评分 =====
def score_relevance(post):
    """对帖子进行业务相关性评分"""
    title = post.get('title', '')
    score = 0
    matched = []
    
    HIGH_VALUE = ['养老', '康养', '康复', '护工', '保姆', '陪护', '护理', '卧床', '失能', '术后']
    MED_VALUE = ['骨科', '神经内科', '康复科', '养老院', '医院', '中风', '老人']
    
    for kw in HIGH_VALUE:
        if kw in title:
            score += 10
            matched.append(kw)
    for kw in MED_VALUE:
        if kw in title:
            score += 5
            matched.append(kw)
    
    post['score'] = score
    post['matched_kw'] = matched
    return post

# ===== 主采集函数 =====
def collect_kk_posts(queries=None, delay=5):
    """执行一轮 KK 网信息采集"""
    if queries is None:
        queries = SEARCH_QUERIES
    
    all_posts = []
    
    print(f"=== KK网信息采集 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")
    
    for query in queries:
        print(f"搜索: {query}")
        
        # 注意：由于 Google 有反爬，实际使用时建议：
        # 1. 在浏览器中手动搜索，复制结果页 HTML 到本地文件
        # 2. 使用 SerpAPI 等第三方搜索 API
        # 3. 使用 Bing Web Search API（Azure 免费额度）
        
        print(f"  提示: 请在浏览器中搜索后保存HTML到 temp/ 目录\n")
        time.sleep(delay)
    
    return all_posts


# ===== 从本地 HTML 文件解析（离线分析） =====
def parse_local_search_results(filepath):
    """从保存到本地的搜索结果 HTML 中提取 KK 网链接"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        html = f.read()
    
    posts = extract_kk_links(html)
    posts = [score_relevance(p) for p in posts]
    posts.sort(key=lambda x: x['score'], reverse=True)
    return posts


# ===== 生成报告 =====
def generate_report(posts, output_path):
    """生成采集报告"""
    if not posts:
        print("无数据，跳过报告生成")
        return
    
    high = [p for p in posts if p['score'] >= 10]
    med = [p for p in posts if 5 <= p['score'] < 10]
    
    report = f"""# KK网康养信息采集报告
> 采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> 总计: {len(posts)} 条 | 高价值: {len(high)} | 中价值: {len(med)}

## 高价值线索（≥10分）
"""
    for p in high:
        report += f"\n### [{p['score']}分] {p['title']}\n"
        report += f"- 链接: {p['url']}\n"
        report += f"- 匹配关键词: {', '.join(p['matched_kw'])}\n"
    
    report += "\n## 中价值信息（5-9分）\n"
    for p in med:
        report += f"- [{p['score']}分] [{p['title']}]({p['url']}) — {', '.join(p['matched_kw'])}\n"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"报告已保存: {output_path}")
    return report


# ===== CLI入口 =====
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'parse':
        # 从本地HTML解析
        filepath = sys.argv[2] if len(sys.argv) > 2 else 'temp/kk_search_result.html'
        posts = parse_local_search_results(filepath)
        generate_report(posts, 'output/kk_report.md')
    else:
        print("KK网信息采集工具")
        print("=" * 50)
        print()
        print("使用方法：")
        print("  1. 在浏览器中搜索: site:0597kk.com 养老 OR 康养 OR 康复")
        print("  2. 保存搜索结果页HTML → temp/kk_search_result.html")
        print("  3. 运行: python scripts/utils/kk_scraper.py parse")
        print()
        print("搜索查询模板（在浏览器地址栏打开）：")
        for q in SEARCH_QUERIES:
            encoded = urllib.parse.quote(q)
            print(f"  https://www.google.com/search?q={encoded}")
```

### 3.2 淘淘居护工分类采集（直接线索）

```python
"""
淘淘居分类信息采集 - 保姆/护工分类
URL: http://www.taotaoju.vip/category-catid-232.html
"""

import urllib.request
import re
import time

def fetch_nursing_posts(area_id=0, page=1):
    """
    抓取淘淘居保姆/护工分类信息
    
    area_id: 区域筛选
        0=全部, 2=新罗区, 3=永定, 4=上杭, 
        5=长汀, 6=武平, 7=连城, 8=漳平
    """
    url = f'http://www.taotaoju.vip/category-catid-232-areaid-{area_id}.html'
    if page > 1:
        url = f'http://www.taotaoju.vip/category-catid-232-areaid-{area_id}-page-{page}.html'
    
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; KKInfoBot/1.0)'}
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=15)
    html = resp.read().decode('gbk', errors='replace')
    
    # 提取信息条目
    # 淘淘居的HTML结构（需根据实际页面调整）：
    items = re.findall(
        r'<a[^>]*href="(/info-\d+\.html)"[^>]*>(.*?)</a>',
        html
    )
    
    results = []
    for link, title in items:
        title = re.sub(r'<[^>]+>', '', title).strip()
        results.append({
            'url': f'http://www.taotaoju.vip{link}',
            'title': title,
            'source': 'taotaoju_nursing'
        })
    
    return results


# 使用示例
if __name__ == '__main__':
    for area in [0, 2]:  # 全部 + 新罗区
        posts = fetch_nursing_posts(area_id=area)
        print(f'区域={area}: {len(posts)} 条护工/保姆信息')
        for p in posts[:5]:
            print(f'  {p["title"][:60]}')
            print(f'  {p["url"]}')
        time.sleep(2)
```

---

## 四、操作流程（推荐）

### 日常使用（每次 5 分钟）

```bash
# 每周执行 1-2 次

# Step 1: 在浏览器中搜索（保存HTML）
# Google: site:0597kk.com 养老 OR 康养 OR 康复 OR 护工 OR 护理
# 保存到: F:\AI\office-assistant\temp\kk_search.html

# Step 2: 运行解析脚本
python scripts/utils/kk_scraper.py parse temp/kk_search.html

# Step 3: 查看报告
# 打开 output/kk_report.md，筛选高价值线索
```

### 搜索查询清单（保存为浏览器书签）

```
1. 直接线索:
https://www.google.com/search?q=site:0597kk.com+养老+OR+康养+OR+康复+OR+护工+OR+护理+OR+保姆

2. 竞品监控:
https://www.google.com/search?q=site:0597kk.com+养老院+OR+福利院+OR+敬老院

3. 医院渠道:
https://www.google.com/search?q=site:0597kk.com+医院+骨科+OR+神经内科+OR+老人+住院

4. 万龄品牌:
https://www.google.com/search?q=site:0597kk.com+万龄

5. 淘淘居护工:
https://www.google.com/search?q=site:taotaoju.vip+护工+OR+老人+OR+护理
```

---

## 五、数据存储规范

采集结果保存在：

```
girlfriend/work/
└── kk_data/
    ├── 2026-07-21_report.md    # 单次采集报告
    ├── leads.json              # 累计线索库
    └── competitor_mentions.json # 竞品提及记录
```

### leads.json 格式

```json
[
  {
    "tid": "3177241",
    "title": "关爱老人，77岁住院后康复护理求助",
    "url": "https://www.0597kk.com/thread-3177241-1-1.html",
    "score": 15,
    "matched_kw": ["老人", "康复", "护理", "住院"],
    "found_at": "2026-07-21",
    "status": "待跟进",
    "notes": ""
  }
]
```

---

*本文档随采集经验积累持续完善。*
