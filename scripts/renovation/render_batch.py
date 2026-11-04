#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量出图：读任务清单 → 调 render.py → 落盘 + 记录 manifest

任务清单示例（JSON）:
{
  "project": "婚房翻新_2026",
  "tasks": [
    {"id": "A_master_01", "scheme": "A_米杏原木", "room": "主卧",
     "mode": "edit", "image": "output/renovation/照片/主卧/01.jpg",
     "prompt": "保留原有柜体与门窗…", "seed": 101, "size": "landscape",
     "model": "qwen-edit-2509",
     "output": "output/renovation/效果图/A_米杏原木"}
  ]
}

用法:
    python scripts/renovation/render_batch.py --tasks <json> [--only ID] [--force]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.console import force_utf8  # noqa: E402

force_utf8()

RENDER = ROOT / ".claude" / "skills" / "interior-design" / "scripts" / "render.py"


def load_tasks(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"找不到任务清单：{path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not data.get("tasks"):
        raise SystemExit("任务清单里没有 tasks")
    return data


def run_one(task: dict) -> tuple[bool, str]:
    """执行单个任务；成功返回 (True, 文件路径)。"""
    mode = task.get("mode", "edit")
    image = Path(task["image"])
    if not image.is_absolute():
        image = ROOT / image
    if not image.exists():
        return False, f"参考图不存在：{image}"

    out_dir = Path(task.get("output") or "output/renovation/效果图")
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    expected = out_dir / f'{task["id"]}.png'
    if expected.exists() and not task.get("_force"):
        return True, str(expected)

    cmd = [sys.executable, str(RENDER), mode,
           "--image", str(image),
           "--prompt", task["prompt"],
           "--size", task.get("size", "landscape"),
           "--model", task.get("model", "qwen-edit-2509" if mode == "edit" else "z-image"),
           "--name", task["id"],
           "--output", str(out_dir)]
    if task.get("seed") is not None:
        cmd += ["--seed", str(task["seed"])]
    if task.get("negative_prompt"):
        cmd += ["--negative-prompt", task["negative_prompt"]]

    for attempt in (1, 2):
        print(f'→ {task["id"]}（{mode}，第 {attempt} 次）')
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                              encoding="utf-8", errors="replace")
        if proc.returncode == 0 and expected.exists():
            return True, str(expected)
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        print("   失败：" + " | ".join(tail))
    return False, "重试后仍失败"


def main() -> int:
    ap = argparse.ArgumentParser(description="批量生成室内效果图")
    ap.add_argument("--tasks", required=True, help="任务清单 JSON")
    ap.add_argument("--only", default=None, help="只跑某个 id")
    ap.add_argument("--force", action="store_true", help="已存在也重跑")
    ap.add_argument("--manifest", default=None, help="记录文件（默认 效果图_生成记录.json）")
    args = ap.parse_args()

    data = load_tasks(Path(args.tasks))
    tasks = data["tasks"]
    if args.only:
        tasks = [t for t in tasks if t.get("id") == args.only]
        if not tasks:
            raise SystemExit(f"没有 id 为 {args.only} 的任务")

    manifest_path = Path(args.manifest) if args.manifest else (
        ROOT / "output" / "renovation" / "效果图_生成记录.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = []
    if manifest_path.exists():
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = raw.get("items", []) if isinstance(raw, dict) else raw
        except json.JSONDecodeError:
            manifest = []

    ok = fail = 0
    for task in tasks:
        task["_force"] = args.force
        success, info = run_one(task)
        record = {
            "id": task["id"], "scheme": task.get("scheme"), "room": task.get("room"),
            "mode": task.get("mode"), "model": task.get("model"),
            "seed": task.get("seed"), "prompt": task.get("prompt"),
            "file": info if success else None, "status": "ok" if success else "failed",
            "time": dt.datetime.now().isoformat(timespec="seconds"),
        }
        manifest = [m for m in manifest if m.get("id") != task["id"]] + [record]
        if success:
            ok += 1
            print(f"   ✓ {info}")
        else:
            fail += 1
            print(f"   ✗ {info}")

        manifest_path.write_text(json.dumps(
            {"project": data.get("project"), "updated": record["time"], "items": manifest},
            ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n完成：成功 {ok}，失败 {fail}｜记录 {manifest_path}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
