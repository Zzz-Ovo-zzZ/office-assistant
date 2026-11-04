# 办公助手

> 办公效率 + 生活规划工具集。用一套规则（`CLAUDE.md`）、一组脚本（`scripts/`）、
> 一堆知识（`knowledge/`）和历史结论（`output/`），把「问 AI 一个生活问题」
> 变成「有一套可复用的规则、数据、脚本和历史结论」。

初始化：2026-06-05 · 主分支：`master` · 默认中文

---

## 能力一览

| 域 | 能做什么 | 入口 |
|----|----------|------|
| 💍 婚嫁 | 八字合婚、订婚/结婚择日（双源黄历交叉验证）、五金与聘礼测算、求婚方案 | `scripts/wedding/`、`output/wedding/` |
| 🏋️ 健身 | BMI/体脂/BMR/TDEE/1RM 计算、1677 种食物 + 873 个动作库、周期化训练计划 | `scripts/fitness/` |
| 💰 理财 | 复利/定存/国债/定投/贷款/台账、72 法则、4% 法则、理财指数 | `scripts/finance/` |
| 📚 考编 | 龙岩考情全景、岗位监控、每日时政、进度追踪、错题组卷 | `scripts/kaobian/`、`knowledge/kaobian/` |
| 🏢 资产 | 财务累欠 vs 合同对账、应收对比、片区划分、地理编码出图 | `scripts/asset_reconcile/`、`scripts/receivable_compare/` |
| 🛋️ 室内 | 读图分析、色彩/灯光/空间/风格、效果图生成、家具选购 | `.claude/skills/interior-design/`、`knowledge/interior/` |
| 🧰 工具 | 置顶番茄钟、悬浮记事本、md→html/pdf、WPS COM 桥接 | `scripts/focus/`、`scripts/notepad_app/`、`scripts/utils/` |
| 👩‍💼 女友工作 | 万龄康养获客方法论、医生库、话术、KK 网线索采集 | `girlfriend/` |

## 快速开始（换电脑只需三步）

```bash
git clone https://github.com/Zzz-Ovo-zzZ/office-assistant.git
cd office-assistant
python -m pip install -r requirements.txt
python scripts/bootstrap.py --init-config   # 生成 config.local.json
python scripts/bootstrap.py                 # 自检：依赖 / 目录 / 引擎冒烟
```

`bootstrap.py` 通过后会打印 `环境就绪 ✅`。若提示缺少依赖，按提示装即可。

### 配置说明

机器相关的路径与密钥**不进 Git**，只写在 `config.local.json`（由 `config.example.json` 复制而来）：

| 键 | 用途 |
|----|------|
| `synology_root` | SynologyDrive 根目录（资产/合同/应收等业务数据） |
| `paths.*` | 各业务表的具体相对路径，可按机器不同 |
| `amap_key` | 高德地图 Web 服务 Key（地理编码） |
| `siliconflow_key` | 硅基流动 Key（室内效果图），也可写入 `.claude/skills/interior-design/.env` |

也可用环境变量覆盖：`OFFICE_SYNOLOGY_ROOT`、`OFFICE_AMAP_KEY`、`OFFICE_PATH_BILL` 等。

## 目录结构

```
├── CLAUDE.md          # 规则书（harness 无关，Claude Code 自动读）
├── AGENTS.md          # 其他 AI 助手的入口（能力路由表）
├── config.example.json# 配置模板（复制为 config.local.json）
├── requirements.txt   # 依赖清单
├── memory/            # 跨会话记忆（人物/时间线/方案）
├── knowledge/         # 领域知识库：fitness / finance / kaobian / wedding / interior
├── data/              # 静态数据：873 动作 / 1677 食物 / GI
├── scripts/           # 可执行脚本（见下表）
├── output/            # 历史产出（按域分目录，命名规范见 output/README.md）
├── girlfriend/        # 曾周的万龄康养工作专区
└── temp/              # 临时文件（gitignore）
```

## 常用命令

```bash
# 健身
python scripts/fitness/cli.py assess          # 交互式身体评估
python scripts/fitness/cli.py food 鸡胸        # 搜食物
python scripts/fitness/cli.py plan            # 生成训练计划

# 理财
python scripts/finance/cli.py compare 100000 1.9 2.2 3   # 定存 vs 国债
python scripts/finance/cli.py loan 1000000 3.5 360
python scripts/finance/cli.py rule72 10

# 工具
python scripts/focus/pomodoro.py              # 番茄钟
python scripts/utils/md_to_html.py <in.md> [out.html]
python scripts/utils/md_to_pdf.py  <in.md>

# 资产对账（需先配好 config.local.json）
python scripts/asset_reconcile/step1_extract.py && python scripts/asset_reconcile/step2_match.py
```

## 在两种 AI 助手里使用

- **Claude Code**：直接打开项目，`CLAUDE.md` 自动生效，`/理财` 等 skill 可用。
- **DeepSeek Harness / 其他**：先读 `AGENTS.md`，按其中的「能力路由表」到对应文件。
  DSH 没有 skill 自动发现机制，路由表就是替代方案，能力不打折。

## 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| `python` 报 `UnicodeEncodeError: 'gbk'` | Windows 控制台默认 GBK | 已内置 `scripts/console.py`，脚本会自动切 UTF-8；自写脚本请 `from scripts.console import force_utf8; force_utf8()` |
| DSH 里命令全部报 `grantWrite(...)` | 工作区文件夹的 Windows 权限不属于当前用户 | 把会话切到「完全权限」，或对该文件夹取得所有权后再修复权限 |
| 对账/应收脚本提示"找不到数据文件" | `config.local.json` 未指向本机数据盘 | 改 `synology_root` / `paths.*`，或设 `OFFICE_PATH_*` |
| 择日脚本报 `No module named lunar_python` | 没装依赖 | `python -m pip install -r requirements.txt` |
| 番茄钟没有托盘图标 | 缺可选依赖 | `python -m pip install pystray pillow` |

## 数据与隐私

⚠️ 本仓库包含生辰八字、家庭财务、婚期安排，以及公司资产/合同/应收数据。
**建议保持私有仓库**；如需分享，先删除 `output/`、`memory/` 与 `girlfriend/`。

`config.local.json`、`.env`、`temp/`、番茄钟统计（`focus_data.json`）已被 `.gitignore` 排除。
`output/float_notepad.txt`（记事本内容）仍被跟踪，但**建议不要把本机笔记提交**——两台机器各写各的，提交后再 pull 会冲突。

## 许可

个人自用项目，未授权对外分发。
