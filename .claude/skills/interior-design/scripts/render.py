#!/usr/bin/env python3
"""
室内设计生图脚本 —— 硅基流动 API 桥接
======================================

用硅基流动（SiliconFlow）的图像生成 API 生成照片级室内效果图。
国内直连、免翻墙，支持文生图与图生图（上传现场照，保留房间结构换风格/加家具）。

依赖:
  pip install requests

API Key:
  1. 免费注册 https://cloud.siliconflow.cn 获取 API key
  2. 写入本 skill 目录下的 .env 文件（SILICONFLOW_API_KEY=sk-xxx）
     或设置环境变量: export SILICONFLOW_API_KEY=sk-xxx

用法:
  python render.py text2img --prompt "现代简约卧室，暖木色，..." --model flux-dev
  python render.py img2img --image 现场照.jpg --prompt "保持房间结构，加入..." --model flux-dev
  python render.py models                          # 列出可用模型
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Windows 控制台默认 GBK，强制 UTF-8 输出以正确显示中文与 emoji
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─── 配置 ────────────────────────────────────────────────────────────

API_BASE = "https://api.siliconflow.cn/v1"          # 国内主域名（如失效可试 api.siliconflow.com）
ENDPOINT = f"{API_BASE}/images/generations"

# 可用模型（key -> 官方模型名）
MODELS = {
    "z-image":       "Tongyi-MAI/Z-Image",        # 通义万相 Z-Image（高质量，默认）
    "z-image-turbo": "Tongyi-MAI/Z-Image-Turbo",  # 快速版
    "qwen-image":    "Qwen/Qwen-Image",           # 通义千问生图
    "kolors":        "Kwai-Kolors/Kolors",        # 快手可图（中文理解强）
    "moss":          "OpenMOSS-Team/MOSS-Image",  # 开源多模态生图
    # 指令式图像编辑：保留原图结构，只改指定内容（室内改造首选）
    "qwen-edit":     "Qwen/Qwen-Image-Edit",
    "qwen-edit-2509": "Qwen/Qwen-Image-Edit-2509",
}

# 图片尺寸（宽x高）
IMAGE_SIZES = {
    "square": "1024x1024",
    "landscape": "1024x768",   # 横版，适合房间全景
    "portrait": "768x1024",    # 竖版，适合单面墙/床头
    "wide": "1024x576",
}

# 项目根目录（render.py → scripts → interior-design → skills → .claude → 项目根）
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "interior" / "renderings"


# ─── 工具函数 ────────────────────────────────────────────────────────

def load_api_key() -> str:
    """读取 SILICONFLOW_API_KEY：优先 .env 文件，其次环境变量。"""
    key = None
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("SILICONFLOW_API_KEY=") and not line.endswith("sk-你的key"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    break
    if not key:
        key = os.environ.get("SILICONFLOW_API_KEY")
    if not key:
        print("❌ 未找到 SILICONFLOW_API_KEY")
        print("")
        print("   方式1: 在本 skill 目录的 .env 文件写入")
        print("           SILICONFLOW_API_KEY=sk-你的key")
        print("   方式2: 设置环境变量")
        print("           export SILICONFLOW_API_KEY=sk-你的key")
        print("")
        print("   免费注册获取 key: https://cloud.siliconflow.cn")
        sys.exit(1)
    return key


def encode_image(image_path: str) -> str:
    """把本地图片编码为 base64 data URI（供图生图使用）。"""
    p = Path(image_path)
    if not p.exists():
        print(f"❌ 图片不存在: {image_path}")
        sys.exit(1)
    ext = p.suffix.lower().lstrip(".") or "jpeg"
    if ext == "jpg":
        ext = "jpeg"
    mime = f"image/{ext}"
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def download_image(url: str, output_dir: Path, prefix: str = "render", stem: str | None = None) -> str:
    """下载生成的图片到本地（硅基流动返回的 URL 仅 1 小时有效）。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    if stem:
        out_path = output_dir / f"{stem}.png"
        i = 2
        while out_path.exists():
            out_path = output_dir / f"{stem}_{i}.png"
            i += 1
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"{prefix}_{ts}.png"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    out_path.write_bytes(resp.content)
    print(f"💾 图片已保存: {out_path}")
    return str(out_path)


def call_api(payload: dict, api_key: str) -> dict:
    """调用硅基流动图片生成 API。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(ENDPOINT, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        print(f"❌ API 请求失败 (HTTP {resp.status_code}):")
        print(f"   {resp.text[:500]}")
        sys.exit(1)
    return resp.json()


def resolve_model(model_key: str) -> str:
    """把短 key 解析为官方模型名。"""
    if model_key in MODELS:
        return MODELS[model_key]
    # 也允许直接传官方模型名
    if "/" in model_key:
        return model_key
    print(f"❌ 未知模型: {model_key}")
    print(f"   可用: {', '.join(MODELS.keys())}")
    sys.exit(1)


# ─── 命令实现 ────────────────────────────────────────────────────────

def cmd_models(_args):
    """列出可用模型。"""
    print("可用生图模型:")
    for k, v in MODELS.items():
        note = {
            "z-image": "通义万相，高质量（默认）",
            "z-image-turbo": "快速版",
            "qwen-image": "通义千问生图",
            "kolors": "快手可图，中文理解强",
        }.get(k, "")
        print(f"  {k:<14} {v}   {note}")


def cmd_text2img(args):
    """文生图：根据文字描述生成效果图。"""
    api_key = load_api_key()
    model = resolve_model(args.model or "z-image")
    image_size = IMAGE_SIZES.get(args.size, args.size or "1024x768")

    payload = {
        "model": model,
        "prompt": args.prompt,
        "image_size": image_size,
        "output_format": "png",
    }
    if args.seed is not None:
        payload["seed"] = args.seed
    if args.negative_prompt:
        payload["negative_prompt"] = args.negative_prompt

    print(f"🎨 文生图 | 模型 {model} | 尺寸 {image_size}")
    print(f"   Prompt: {args.prompt[:120]}{'...' if len(args.prompt) > 120 else ''}")

    data = call_api(payload, api_key)
    _handle_result(data, args.output, stem=getattr(args, "name", None))


def cmd_img2img(args):
    """图生图：上传现场照，保留房间结构换风格/加家具。"""
    _run_img_edit(args, default_model="z-image", prefix="redesign")


def cmd_edit(args):
    """指令式编辑：保留原图结构（柜体/门窗/地板），只改指定内容。"""
    _run_img_edit(args, default_model="qwen-edit-2509", prefix="edit")


def _run_img_edit(args, default_model: str, prefix: str):
    api_key = load_api_key()
    model = resolve_model(args.model or default_model)
    image_size = IMAGE_SIZES.get(args.size, args.size or "1024x768")
    image_uri = encode_image(args.image)

    payload = {
        "model": model,
        "prompt": args.prompt,
        "image": image_uri,
        "image_size": image_size,
        "output_format": "png",
    }
    if args.seed is not None:
        payload["seed"] = args.seed
    if getattr(args, "negative_prompt", ""):
        payload["negative_prompt"] = args.negative_prompt

    print(f"🖼  图像编辑 | 模型 {model} | 参考图 {args.image} | 尺寸 {image_size}")
    print(f"   Prompt: {args.prompt[:120]}{'...' if len(args.prompt) > 120 else ''}")

    data = call_api(payload, api_key)
    _handle_result(data, args.output, prefix=prefix, stem=getattr(args, "name", None))


def _handle_result(data: dict, output: str, prefix: str = "render", stem: str | None = None):
    """处理 API 返回结果：下载图片到本地。"""
    images = data.get("images") or data.get("data") or []
    if not images:
        print("❌ 响应中没有图片数据:")
        print(f"   {json.dumps(data, ensure_ascii=False)[:500]}")
        sys.exit(1)

    out_dir = Path(output) if output else DEFAULT_OUTPUT_DIR
    for i, img in enumerate(images):
        url = img.get("url")
        this_stem = f"{stem}_{i+1}" if stem and i else stem
        if not url:
            print(f"   (第 {i+1} 张图无 url，可能是 base64)")
            b64 = img.get("b64_json")
            if b64:
                out_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                name = f"{this_stem}.png" if this_stem else f"{prefix}_{ts}_{i}.png"
                p = out_dir / name
                p.write_bytes(base64.b64decode(b64))
                print(f"💾 图片已保存: {p}")
            continue
        print(f"🌐 图片 URL 有效 1 小时，正在下载...")
        download_image(url, out_dir, prefix=f"{prefix}_{i}" if i else prefix, stem=this_stem)


# ─── 入口 ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="室内设计生图脚本（硅基流动 API）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    p_t2i = sub.add_parser("text2img", help="文生图")
    p_t2i.add_argument("--prompt", required=True, help="设计描述")
    p_t2i.add_argument("--model", default="z-image", help="模型 key 或官方名")
    p_t2i.add_argument("--size", default="landscape", help="square/landscape/portrait/wide 或 WxH")
    p_t2i.add_argument("--seed", type=int, help="随机种子（复现用）")
    p_t2i.add_argument("--negative-prompt", default="", help="负面提示词")
    p_t2i.add_argument("--name", default=None, help="输出文件名（不含扩展名）")
    p_t2i.add_argument("--output", help="输出目录")
    p_t2i.set_defaults(func=cmd_text2img)

    p_i2i = sub.add_parser("img2img", help="图生图（上传参考图）")
    p_i2i.add_argument("--image", required=True, help="参考现场照路径")
    p_i2i.add_argument("--prompt", required=True, help="改造描述")
    p_i2i.add_argument("--model", default="z-image", help="模型 key 或官方名")
    p_i2i.add_argument("--size", default="landscape", help="square/landscape/portrait/wide 或 WxH")
    p_i2i.add_argument("--seed", type=int, help="随机种子（复现用）")
    p_i2i.add_argument("--negative-prompt", default="", help="负面提示词")
    p_i2i.add_argument("--name", default=None, help="输出文件名（不含扩展名）")
    p_i2i.add_argument("--output", help="输出目录")
    p_i2i.set_defaults(func=cmd_img2img)

    p_edit = sub.add_parser("edit", help="指令式编辑（保留结构，只改指定内容）")
    p_edit.add_argument("--image", required=True, help="参考现场照路径")
    p_edit.add_argument("--prompt", required=True, help="编辑指令")
    p_edit.add_argument("--model", default="qwen-edit-2509", help="默认 qwen-edit-2509")
    p_edit.add_argument("--size", default="landscape", help="square/landscape/portrait/wide 或 WxH")
    p_edit.add_argument("--seed", type=int, help="随机种子（复现用）")
    p_edit.add_argument("--negative-prompt", default="", help="负面提示词")
    p_edit.add_argument("--name", default=None, help="输出文件名（不含扩展名）")
    p_edit.add_argument("--output", help="输出目录")
    p_edit.set_defaults(func=cmd_edit)

    p_m = sub.add_parser("models", help="列出可用模型")
    p_m.set_defaults(func=cmd_models)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
