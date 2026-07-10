# 办公助手 CLAUDE.md

## 语言偏好

永远使用中文回复用户。所有对话、解释、代码注释都应使用中文。

## 项目定位

办公效率 + 生活规划工具集，涵盖：

| 模块 | 说明 |
|------|------|
| 办公自动化 | 日常工作流程自动化脚本 |
| 生活规划 | 婚嫁择日、事件筹备、预算管理、行程安排 |
| 知识管理 | 备忘录、决策记录、经验沉淀 |

## 目录结构

```
办公助手/
├── scripts/                    # 可执行脚本
│   ├── wedding/                # 婚嫁择日脚本
│   ├── fitness/                # 健身饮食助手
│   ├── utils/                  # 通用工具 (md转html/pdf等)
│   └── notepad_app/            # 记事本应用
├── output/                     # 输出文件（按领域分目录）
│   ├── wedding/                # 婚嫁报告 (八字合婚/订婚择日/综合规划)
│   ├── fitness/                # 健身输出 (评估/计划/日志)
│   └── README.md               # 输出规范说明
├── data/                       # 静态数据资源
│   ├── exercises/              # 锻炼动作库
│   └── nutrition/              # 食物成分数据
├── knowledge/                  # 知识库文档
│   ├── fitness/                # 健身指南
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
