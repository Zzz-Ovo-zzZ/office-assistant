# 考编工具脚本

> 为曾周备考定制的4个辅助脚本

## 快速使用

```bash
# 1. 岗位监控 — 检查龙岩新岗位
python scripts/kaobian/job_monitor.py

# 2. 时政收集 — 生成每日时政速览
python scripts/kaobian/daily_shizheng.py

# 3. 进度追踪 — 记录学习 + 生成报告
python scripts/kaobian/progress_tracker.py --log 公基 90
python scripts/kaobian/progress_tracker.py --report

# 4. 错题管理 — 录入错题 + 智能组卷
python scripts/kaobian/question_bank.py --add
python scripts/kaobian/question_bank.py --quiz 公基 10
```

详细用法见各脚本 `--help`。
