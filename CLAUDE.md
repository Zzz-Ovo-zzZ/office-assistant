# 办公助手 CLAUDE.md

## 语言偏好

永远使用中文回复用户。所有对话、解释、代码注释都应使用中文。

## 项目定位

办公效率 + 生活规划工具集，涵盖：

| 模块 | 说明 |
|------|------|
| 办公自动化 | 日常工作流程自动化脚本 |
| 生活规划 | 婚嫁择日、事件筹备、室内设计、预算管理、行程安排 |
| 知识管理 | 备忘录、决策记录、经验沉淀 |

## 目录结构

```
办公助手/
├── scripts/                    # 可执行脚本
│   ├── wedding/                # 婚嫁择日脚本
│   ├── fitness/                # 健身饮食助手
│   ├── finance/                # 理财助手 (收益计算/记账/贷款)
│   ├── utils/                  # 通用工具 (md转html/pdf等)
│   └── notepad_app/            # 记事本应用
├── output/                     # 输出文件（按领域分目录）
│   ├── wedding/                # 婚嫁报告 (八字合婚/订婚择日/综合规划)
│   ├── fitness/                # 健身输出 (评估/计划/日志)
│   ├── finance/                # 理财输出 (对比报告/计划/台账)
│   ├── interior/               # 室内设计输出 (效果图/方案/购物清单)
│   └── README.md               # 输出规范说明
├── data/                       # 静态数据资源
│   ├── exercises/              # 锻炼动作库
│   └── nutrition/              # 食物成分数据
├── knowledge/                  # 知识库文档
│   ├── fitness/                # 健身指南
│   ├── finance/                # 理财指南
│   ├── interior/               # 室内设计 (色彩/灯光/空间/风格/家具)
│   └── wedding/                # 婚嫁知识
├── temp/                       # 临时文件（用完即删）
├── memory/                     # 跨会话记忆
└── README.md
```

> 输出文件须遵循命名规范：`{主题}_{内容描述}_{版本/日期}.{扩展名}`，详见 `output/README.md`

## Git 版本

- 主分支：master
- 功能开发使用独立分支
- 提交信息使用中文

## 婚嫁择日规则库

### 必须避开的日期（17类）

| 类别 | 说明 |
|------|------|
| 朔日 | 每月初一 |
| 望日 | 每月十五 |
| 月忌 | 每月初五、十四、二十三 |
| 四绝日 | 立春/立夏/立秋/立冬 前一日 |
| 四离日 | 春分/秋分/夏至/冬至 前一日 |
| 杨公忌 | 正月十三/二月十一/三月初九/四月初七/五月初五/六月初三/七月初一/七月初二九/八月廿七/九月廿五/十月廿三/冬月廿一/腊月十九 |
| 破日 | 黄历标注破日/大耗 |
| 清明 | 4月4-5日前后 |
| 中元节 | 农历七月十五，整个农历七月忌婚嫁 |
| 寒衣节 | 农历十月初一 |
| 下元节 | 农历十月十五 |
| 除夕春节 | 除夕至正月十五 |
| 午日 | 冲鼠日（男方生肖） |
| 未日 | 冲牛日（女方生肖） |
| 父母忌日 | 长辈忌日（如适用） |

### 可借势的好日子

节假日、周末、七夕(仅求婚)、520/521(领证)、元宵、中秋、国庆、五一、元旦、端午、双十一(领证)

### 天气窗口（福建/江西）

10-11月最佳(20-28°C)，3-5月次之(15-25°C)，7-8月太热，12-2月太冷

## 健身 & 饮食助手

### 能力范围

作为健身饮食助手，能够提供：

| 能力 | 说明 |
|------|------|
| 身体评估 | BMI/体脂率/BMR/TDEE/1RM/心率区间 计算 |
| 营养分析 | 宏量营养素分配、中国食物成分查询、GI指数、一餐营养计算 |
| 训练计划 | 5种分化方式 × 4种目标 × 3个水平的周期化训练计划 |
| 动作指导 | 873个锻炼动作的搜索和筛选（按肌肉群/器械/难度） |
| 饮食建议 | 减脂/增肌/维持的完整饮食方案 |

### 工具模块 (`scripts/fitness/`)

| 文件 | 功能 |
|------|------|
| `engine.py` | 核心计算引擎 (BMI/BMR/TDEE/体脂/1RM/心率/热量消耗) |
| `food_db.py` | 中国食物成分数据库 (1677种食物 + GI指数) |
| `exercise_db.py` | 锻炼动作数据库 (873个动作, 中英文搜索) |
| `training.py` | 训练计划生成器 (周期化, 增肌/力量/减脂/耐力) |
| `cli.py` | 命令行工具 (assess/bmi/1rm/plan/food/exercise/meal) |

### 数据资源

| 数据 | 位置 | 来源 |
|------|------|------|
| 锻炼动作库 | `data/exercises/all_exercises.json` | free-exercise-db (Public Domain) |
| 中国食物成分 | `data/nutrition/all_foods.json` | 《中国食物成分表第6版》 |
| GI指数 | `data/nutrition/gi_index.json` | 中国食物成分表 |
| 知识库 | `knowledge/fitness/guide.md` | 运动科学综合 |

### 使用示例

```python
from scripts.fitness import quick_report, print_quick_report

# 快速评估
report = quick_report(gender="男", age=30, height_cm=175, weight_kg=78,
                      waist_cm=82, neck_cm=38, goal="cut")
print_quick_report(report)
```

```bash
# 命令行
python scripts/fitness/cli.py assess    # 交互式评估
python scripts/fitness/cli.py food 鸡胸  # 搜索食物
python scripts/fitness/cli.py plan      # 生成训练计划
```

### 运动科学参考

- ACSM 运动测试与处方指南
- Mifflin-St Jeor BMR 公式 (1990)
- U.S. Navy 体脂估算法
- Karvonen 心率储备法
- 周期化训练理论 (线性/波浪/板块)
- 渐进超负荷原则

## 理财助手

### 能力范围

| 能力 | 说明 |
|------|------|
| 收益计算 | 复利/单利/定存/国债/定投/年化收益率/多方案对比 |
| 记账台账 | CSV 流水记账 + 分类/月度/结余汇总 |
| 贷款计算 | 等额本息/等额本金/提前还款省息测算 |
| 财富规划 | 72法则/4%法则/财务自由年限/理财指数/机会成本 |
| 知识库 | 理财指南 (保本类产品 + 增值类定投/FIRE/资产配置全谱系) |
| 智能定投(择时) | 主动投资资金的择时定投增强，引用 stock-value-analyzer 的指数黄金坑「定投系数」，详见 `knowledge/finance/dca-smart.md` |

### 工具模块 (`scripts/finance/`)

| 文件 | 功能 |
|------|------|
| `engine.py` | 收益计算引擎 (复利/定存/国债/定投/年化/对比) |
| `wealth.py` | 财富规划引擎 (72法则/4%法则/理财指数/机会成本/财务自由年限) |
| `loan.py` | 贷款计算 (等额本息/等额本金/提前还款) |
| `ledger.py` | 记账台账 (CSV 流水 + 汇总) |
| `cli.py` | 命令行工具 (compound/deposit/bond/compare/invest/loan/ledger/report/rule72/fire/score/cost/multiple) |

> 资产对账归属本板块：`scripts/asset_reconcile/`（置业财务累欠 vs 合同对账，工作性质）代码保留在原位置，作为「资产对账」子模块。

### 数据资源

- 起步无静态数据，利率/产品参数由用户输入；记账流水为 `output/finance/ledger/*.csv`（Excel/WPS 可编辑）。
- 知识库 `knowledge/finance/`：`guide.md`（保本/基础主线）+ 10 个增值类专题（dca/fire/allocation/withdraw/math/funds/score/psychology/opportunity-cost）+ `rates-2026.md`（2026 最新利率，含来源）。
- 本地化 skill `.claude/skills/wealth-shortcut/`：可用 `/wealth-shortcut`、`/理财` 触发全谱系理财顾问。

### 使用示例

```python
from scripts.finance import compare_deposit_vs_bond
compare_deposit_vs_bond(本金=100000, 定存利率=1.9, 国债利率=2.2, 年限=3)

from scripts.finance import Ledger
Ledger().add_entry("2026-09-22", "收入", "工资", 15000, "9月工资")

from scripts.finance import WealthEngine
WealthEngine.fire_assets(年开支=100000)      # 4%法则: 需 250 万
WealthEngine.wealth_score(净资产=1000000, 平均年龄=30, 年工资=200000)
```

```bash
python scripts/finance/cli.py compare 100000 1.9 2.2 3   # 定存 vs 国债
python scripts/finance/cli.py loan 1000000 3.5 360        # 贷款对比
python scripts/finance/cli.py report                      # 台账汇总
python scripts/finance/cli.py rule72 10                   # 72法则: 7.2 年翻倍
python scripts/finance/cli.py fire 100000                 # 财务自由所需资产
python scripts/finance/cli.py score 1000000 30 200000     # 理财指数
```

### 参考来源

- 复利终值公式 FV = P(1+r/n)^(nt)
- 等额本息/等额本金标准公式
- 72法则 / 4%法则 / 理财指数 (源自《财富捷径》投资理念)
- Estrada (2015) 退休取款率历史验证论文
- 《存款保险条例》(50 万本息保障)
- 资管新规 (银行理财净值化、不保本)
- 2026 最新利率数据见 `knowledge/finance/rates-2026.md`

## 室内软装设计

### 能力范围

| 能力 | 说明 |
|------|------|
| 读图分析 | 读房间照片/户型图，识别尺寸/门窗/硬装/现有家具，输出 12 项分析 |
| 专业设计 | 色彩(孟塞尔+60-30-10)、灯光(四层布光+色温)、空间(动线+家具间隙)、风格(6大风格) |
| 效果图生成 | 硅基流动 API (FLUX 模型)，支持文生图 + 图生图(现场照换风格/加家具) |
| 家具选购 | 中国家具国标尺寸 + 板材材质辨别 + 选购避坑 |

### 工具模块

| 位置 | 功能 |
|------|------|
| `.claude/skills/interior-design/` | 室内设计 skill (`SKILL.md` 方法论 + `scripts/render.py` 生图脚本) |
| `knowledge/interior/` | 知识库 (design-guide/color-science/lighting-design/space-planning/style-guide/furniture-spec/shopping-guide) |
| `output/interior/` | 输出 (renderings 效果图 / plans 方案 / shopping 购物清单) |

### 生图脚本用法

```bash
python .claude/skills/interior-design/scripts/render.py text2img --prompt "..." --model flux-dev
python .claude/skills/interior-design/scripts/render.py img2img --image 房间.jpg --prompt "..." --model flux-dev
python .claude/skills/interior-design/scripts/render.py models   # 列出可用模型
```

> 依赖 `pip install requests`；API key 免费注册 cloud.siliconflow.cn，写入 skill 目录 `.env` 文件。

### 参考来源

- interior-vibing (GitHub) — 生图流程方法论 (房间分析/prompt/deck)
- interior-design-expert (GitHub, Apache-2.0) — 色彩/灯光/空间/风格专业内核
- zhuangxiu-skills (GitHub, 西安装修课堂) — 中文家具软装选购实战
- GB/T 3326/3327/3328 + QB/T 1952.1 — 中国家具国标尺寸
