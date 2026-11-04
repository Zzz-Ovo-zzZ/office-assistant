# AGENTS.md

> 给非 Claude Code 的 AI 助手（DeepSeek Harness、Cursor、Copilot 等）读的入口文件。
> **唯一事实来源是 [CLAUDE.md](CLAUDE.md)**，本文件只补充「怎么在别的 harness 里等价使用」。

## 1. 必须遵守

- **永远用中文**回复、写解释与代码注释。
- 输出文件按 `output/README.md` 的命名规范：`{主题}_{内容描述}_{版本/日期}.{扩展名}`。
- 改动代码前先看 `CLAUDE.md`，那里有择日规则库、健身/理财口径等硬约束。
- 本仓库含个人（生辰、家庭财务、婚期）与公司（资产、合同、应收）数据，**不要建议公开仓库**。

## 2. 能力路由（等价于 Claude Code 的 skill）

Claude Code 里可用 `/wealth-shortcut`、`/理财` 触发 skill；别的 harness 没有这个机制，
**按下表直接读对应文件即可，效果等价**：

| 用户说 | 先读 | 再用 |
|--------|------|------|
| 理财 / 定投 / 国债 / 财务自由 | [.claude/skills/wealth-shortcut/SKILL.md](.claude/skills/wealth-shortcut/SKILL.md) | `scripts/finance/` 计算 |
| 室内设计 / 软装 / 效果图 | [.claude/skills/interior-design/SKILL.md](.claude/skills/interior-design/SKILL.md) | `knowledge/interior/`、`render.py` |
| 装修 / 局部翻新 / 平面图 | [output/renovation/README.md](output/renovation/README.md) | `scripts/renovation/`（floorplan / render_batch） |
| 婚嫁 / 择日 / 八字 | `CLAUDE.md` 择日规则库 + [scripts/wedding/](scripts/wedding/) | `lunar-python` + `cnlunar` 双源 |
| 健身 / 减脂 / 吃多少 | [knowledge/fitness/guide.md](knowledge/fitness/guide.md) | `scripts/fitness/` |
| 考编 / 岗位 / 备考 | [knowledge/kaobian/README.md](knowledge/kaobian/README.md) | `scripts/kaobian/` |
| 资产对账 / 应收 / 合同 | [scripts/asset_reconcile/README.md](scripts/asset_reconcile/README.md) | 6 步流水线 |
| 康养 / 获客 / 拜访 | [girlfriend/work/工作策略.md](girlfriend/work/工作策略.md) | `scripts/utils/kk_scraper.py` |

## 3. 环境（与 Claude Code 完全共用）

```bash
python -m pip install -r requirements.txt   # 依赖
python scripts/bootstrap.py --init-config    # 生成 config.local.json（每台机器一次）
python scripts/bootstrap.py                  # 自检：依赖 / 目录 / 两个引擎冒烟
```

- 机器相关路径与密钥只放 `config.local.json`（已 gitignore），代码里不再有绝对路径。
- 修改路径：`config.local.json` 的 `paths.*`，或环境变量 `OFFICE_PATH_<名字>`。
- 数据源缺失时脚本会给出中文提示，而不是抛 traceback。

## 4. 与 Claude Code 的差异（迁移须知）

| 项 | Claude Code | 其他 harness |
|----|-------------|--------------|
| 规则文件 | `CLAUDE.md` 自动加载 | 本文件 + `CLAUDE.md`（建议一并读） |
| skill | `.claude/skills/` 自动发现，可斜杠触发 | 无 skill 机制，按第 2 节路由手动读 |
| 权限 | 一次性确认 | 取决于 harness（DSH 有 workspace 沙箱，Windows 上偶发文件夹权限问题） |
| 定时任务 | 无内置 | DSH 可用 `schedule`；Claude Code 靠系统计划任务 |

## 5. 常用命令速查

```bash
python scripts/fitness/cli.py assess         # 身体评估（交互）
python scripts/finance/cli.py rule72 10      # 72 法则
python scripts/finance/cli.py loan 1000000 3.5 360
python scripts/focus/pomodoro.py             # 番茄钟
python scripts/notepad_app/main.py           # 记事本（需 PyQt6）
python .claude/skills/interior-design/scripts/render.py models
```
