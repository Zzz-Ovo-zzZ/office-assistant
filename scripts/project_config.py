#!/usr/bin/env python3
"""项目统一配置 —— 机器相关路径与密钥的唯一出口。

优先级：环境变量 ``OFFICE_<KEY>`` > 项目根目录 ``config.local.json`` > 内置默认值。

这样做的目的：换电脑时只改 ``config.local.json``（已被 .gitignore 忽略），
代码里不再出现任何绝对路径或明文 Key。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.console import force_utf8

# 本模块被所有业务脚本导入，在这里统一修正控制台编码（Windows 默认 GBK）
force_utf8()

# ── 路径 ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_LOCAL = PROJECT_ROOT / "config.local.json"
CONFIG_EXAMPLE = PROJECT_ROOT / "config.example.json"

# ── 默认值 ──────────────────────────────────────────────
# paths 里的相对路径都以 synology_root 为基准；也可以填绝对路径。
DEFAULTS = {
    "synology_root": r"D:\SynologyDrive",
    "amap_key": "",
    "siliconflow_key": "",
    "paths": {
        "bill": r"0资产管理录入文件\入场实施\财务数据\置业\累欠数据\调整后截止2025年底欠款明细表26.8.31.xlsx",
        "contracts": r"0资产管理录入文件\入场实施\合同情况\置业\所需合同整理\置业合同整理（调整合同顺序，相同合同放在一起）_2026.8.24.xlsx",
        "reconcile_out": r"0资产管理录入文件\入场实施\财务数据\置业\累欠数据",
        "receivable_sys": r"0资产管理录入文件\入场实施\数据核对\置业\应收\25年应收\25年系统应收数据_2026.11.3.xlsx",
        "receivable_org": r"0资产管理录入文件\入场实施\财务数据\置业\应收实收\2025年应收、实收\25年应收整理(分公司）_2026.11.3.xlsx",
        "receivable_out": r"0资产管理录入文件\入场实施\数据核对\置业\应收\25年应收",
        "huihe_plan": r"0资产管理录入文件\入场实施\资产数据\惠和资产片区划分规划表_2026.7.15.xlsx",
    },
}


def _deep_merge(base: dict, extra: dict) -> dict:
    """递归合并，extra 覆盖 base（不修改入参）。"""
    out = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _env_overrides(cfg: dict) -> dict:
    """环境变量覆盖：OFFICE_SYNOLOGY_ROOT / OFFICE_AMAP_KEY / OFFICE_PATH_BILL ..."""
    out = dict(cfg)
    for key in ("synology_root", "amap_key", "siliconflow_key"):
        env = os.environ.get(f"OFFICE_{key.upper()}")
        if env:
            out[key] = env
    for name in list(out.get("paths", {})):
        env = os.environ.get(f"OFFICE_PATH_{name.upper()}")
        if env:
            out["paths"][name] = env
    return out


def load_config() -> dict:
    """读取配置：默认值 ← config.local.json ← 环境变量。"""
    cfg = _deep_merge(DEFAULTS, {})
    if CONFIG_LOCAL.exists():
        try:
            cfg = _deep_merge(cfg, json.loads(CONFIG_LOCAL.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"config.local.json 不是合法 JSON：{exc}") from exc
    return _env_overrides(cfg)


CONFIG = load_config()


# ── 读取接口 ────────────────────────────────────────────
def get(key: str, default=None):
    """读取顶层配置项（如 synology_root / amap_key）。"""
    return CONFIG.get(key, default)


def path_of(name: str) -> Path:
    """按名字取业务文件路径；相对路径以 synology_root 为基准。"""
    raw = CONFIG.get("paths", {}).get(name)
    if not raw:
        raise KeyError(f"配置缺少 paths.{name}，请参考 config.example.json")
    p = Path(raw).expanduser()
    if p.is_absolute():
        return p
    return Path(CONFIG["synology_root"]).expanduser() / p


def require(path: Path, hint: str = "") -> Path:
    """路径不存在时给出可操作的提示，而不是抛原始异常。"""
    if not Path(path).exists():
        msg = [
            f"找不到数据文件：{path}",
            "请检查 config.local.json 里的 paths.* / synology_root（示例见 config.example.json），",
            "也可以用环境变量 OFFICE_PATH_<名字> 临时覆盖。",
        ]
        if hint:
            msg.append(hint)
        raise SystemExit("\n".join(msg))
    return Path(path)


def ensure_runtime_dirs() -> list[Path]:
    """创建运行时目录（缺失不影响首次运行，但工具会用到）。"""
    dirs = [
        PROJECT_ROOT / "temp",
        PROJECT_ROOT / "output" / "finance" / "ledger",
        PROJECT_ROOT / "output" / "fitness" / "assessments",
        PROJECT_ROOT / "output" / "kaobian" / "zengzhou",
        PROJECT_ROOT / "data" / "kaobian",
        PROJECT_ROOT / "girlfriend" / "work" / "kk_data",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return dirs
