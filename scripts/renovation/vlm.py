#!/usr/bin/env python3
"""视觉模型公共客户端（读图 / 质检用）。

支持两家 OpenAI 兼容端点，按 Key 名自动分流：
- ``DASHSCOPE_API_KEY``  → 阿里云百炼（qwen3.8-max，读图与质检默认）
- ``SILICONFLOW_API_KEY`` → 硅基流动（Qwen3-VL 系列）

Key 查找顺序：环境变量 → ``.claude/skills/interior-design/.env`` → ``config.local.json``。

用法（被其它脚本导入）::

    from scripts.renovation.vlm import chat, encode_image
    text = chat("qwen3.8-max", "描述这张图", ["照片.jpg"])
"""
from __future__ import annotations

import base64
import io
import os
import sys
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.console import force_utf8  # noqa: E402

force_utf8()

PROJECT_ROOT = ROOT
ENV_FILE = PROJECT_ROOT / ".claude" / "skills" / "interior-design" / ".env"

# 模型 → (端点, Key 名)
PROVIDERS = {
    "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "DASHSCOPE_API_KEY"),
    "siliconflow": ("https://api.siliconflow.cn/v1", "SILICONFLOW_API_KEY"),
}

DEFAULT_MODEL = "qwen3.8-max"


def _key_from_env_file(name: str) -> str:
    if not ENV_FILE.exists():
        return ""
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _key_from_config(name: str) -> str:
    """config.local.json 里只有 siliconflow_key，其余靠 .env / 环境变量。"""
    if name != "SILICONFLOW_API_KEY":
        return ""
    try:
        from scripts.project_config import get

        return get("siliconflow_key") or ""
    except Exception:
        return ""


def load_key(name: str) -> str:
    """按「环境变量 → .env → config.local.json」顺序找 Key。"""
    value = os.environ.get(name) or _key_from_env_file(name) or _key_from_config(name)
    if not value:
        raise SystemExit(
            f"未找到 {name}\n"
            f"  方式1：写进 {ENV_FILE.relative_to(PROJECT_ROOT)}（{name}=你的key）\n"
            f"  方式2：设环境变量 {name}\n"
            f"  方式3：填 config.local.json（仅 SILICONFLOW_API_KEY 支持）"
        )
    return value


def provider_of(model: str) -> tuple[str, str, str]:
    """按模型名判断端点与 Key。qwen* / *-max / *-vl → 百炼，其余 → 硅基流动。"""
    name = model.lower()
    family = "qwen" if ("qwen" in name or "qwen" in name.replace("-", "") or name.startswith("qwen")) else "siliconflow"
    # 显式补充：硅基流动上也能跑 Qwen3-VL，用 "/" 表示官方全名（如 Qwen/Qwen3-VL-32B-Instruct）
    if "/" in model:
        family = "siliconflow"
    base, key_name = PROVIDERS[family]
    return base, key_name, family


def encode_image(path: str | Path, max_edge: int = 1600) -> str:
    """把本地图片压到 max_edge 长边后编码成 data URI。"""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"图片不存在：{p}")
    with Image.open(p) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = max_edge / max(w, h)
        if scale < 1:
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def chat(
    model: str,
    prompt: str,
    images: list[str | Path] | None = None,
    *,
    temperature: float = 0.0,
    max_tokens: int = 2500,
    timeout: int = 600,
    max_edge: int = 1600,
) -> str:
    """一次性把「文字 + 若干图片」发给视觉模型，返回文本回答。"""
    base, key_name, _ = provider_of(model)
    key = load_key(key_name)
    content: list[dict] = [{"type": "text", "text": prompt}]
    for img in images or []:
        content.append({"type": "image_url", "image_url": {"url": encode_image(img, max_edge)}})
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise SystemExit(f"HTTP {resp.status_code}：{resp.text[:400]}")
    return resp.json()["choices"][0]["message"].get("content") or ""
