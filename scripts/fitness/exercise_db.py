#!/usr/bin/env python3
"""
锻炼动作数据库
==============
基于 free-exercise-db (800+ 动作, Public Domain)
提供中文翻译、搜索、按肌肉群/器械/难度筛选功能。

数据来源: https://github.com/yuhonas/free-exercise-db
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
import random

# ============================================================
# 中文翻译对照表
# ============================================================

# 肌肉群翻译
MUSCLE_CN = {
    "abdominals": "腹肌",
    "abductors": "外展肌",
    "adductors": "内收肌",
    "biceps": "肱二头肌",
    "calves": "小腿肌",
    "chest": "胸肌",
    "forearms": "前臂",
    "glutes": "臀肌",
    "hamstrings": "腘绳肌",
    "lats": "背阔肌",
    "lower back": "下背/竖脊肌",
    "middle back": "中背/菱形肌",
    "neck": "颈部",
    "quadriceps": "股四头肌",
    "shoulders": "三角肌/肩部",
    "traps": "斜方肌",
    "triceps": "肱三头肌",
}

# 力学类型翻译
FORCE_CN = {
    "push": "推",
    "pull": "拉",
    "static": "静态",
}

# 难度翻译
LEVEL_CN = {
    "beginner": "初级",
    "intermediate": "中级",
    "expert": "高级",
}

# 动作类型翻译
MECHANIC_CN = {
    "compound": "复合动作",
    "isolation": "孤立动作",
}

# 器械翻译
EQUIPMENT_CN = {
    "body only": "自重",
    "barbell": "杠铃",
    "dumbbell": "哑铃",
    "kettlebells": "壶铃",
    "cable": "龙门架/绳索",
    "machine": "固定器械",
    "bands": "弹力带",
    "medicine ball": "药球",
    "exercise ball": "健身球",
    "foam roll": "泡沫轴",
    "e-z curl bar": "曲杠",
    "other": "其他",
}

# 类别翻译
CATEGORY_CN = {
    "strength": "力量训练",
    "cardio": "有氧训练",
    "stretching": "拉伸",
    "powerlifting": "力量举",
    "strongman": "壮汉",
    "plyometrics": "爆发力训练",
    "olympic weightlifting": "奥林匹克举重",
}

# ============================================================
# 锻炼动作数据结构
# ============================================================

@dataclass
class Exercise:
    """锻炼动作"""
    id: str
    name: str
    name_cn: str                # 中文名（需要后续补全，目前用英文原名）
    force: str                  # push / pull / static
    force_cn: str
    level: str
    level_cn: str
    mechanic: str               # compound / isolation
    mechanic_cn: str
    equipment: str
    equipment_cn: str
    primary_muscles: list[str]
    primary_muscles_cn: list[str]
    secondary_muscles: list[str]
    secondary_muscles_cn: list[str]
    instructions: list[str]
    category: str
    category_cn: str
    images: list[str]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_cn": self.name_cn,
            "force": self.force_cn,
            "level": self.level_cn,
            "mechanic": self.mechanic_cn,
            "equipment": self.equipment_cn,
            "primary_muscles": self.primary_muscles_cn,
            "secondary_muscles": self.secondary_muscles_cn,
            "instructions": self.instructions,
            "category": self.category_cn,
        }

    def summary(self) -> str:
        """单行摘要"""
        primary = "、".join(self.primary_muscles_cn) if self.primary_muscles_cn else "—"
        secondary = "、".join(self.secondary_muscles_cn) if self.secondary_muscles_cn else "无"
        return (f"{self.id}: {self.name} | {self.mechanic_cn}({self.force_cn}) | "
                f"主: {primary} | 辅: {secondary} | "
                f"{self.equipment_cn} | {self.level_cn} | {self.category_cn}")


class ExerciseDatabase:
    """锻炼动作数据库"""

    def __init__(self, data_dir: str = None):
        """
        初始化数据库
        data_dir: free-exercise-db 的 exercises 目录路径
        """
        self._exercises: dict[str, Exercise] = {}
        self._by_muscle: dict[str, list[str]] = {}       # muscle -> [exercise_ids]
        self._by_equipment: dict[str, list[str]] = {}     # equipment -> [exercise_ids]
        self._by_level: dict[str, list[str]] = {}         # level -> [exercise_ids]
        self._by_category: dict[str, list[str]] = {}      # category -> [exercise_ids]
        self._by_mechanic: dict[str, list[str]] = {}      # mechanic -> [exercise_ids]

    def load_from_dir(self, data_dir: str):
        """从 free-exercise-db 的 exercises 目录加载"""
        data_path = Path(data_dir)
        for json_file in data_path.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ex = self._parse_exercise(data)
                self._exercises[ex.id] = ex
                self._index(ex)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  跳过 {json_file.name}: {e}")

        print(f"✅ 加载了 {len(self._exercises)} 个锻炼动作")

    def load_from_json(self, filepath: str):
        """从单个合并的 JSON 文件加载"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            ex = self._parse_exercise(item)
            self._exercises[ex.id] = ex
            self._index(ex)
        print(f"✅ 加载了 {len(self._exercises)} 个锻炼动作")

    def _parse_exercise(self, data: dict) -> Exercise:
        """将原始 JSON 数据转为 Exercise 对象"""
        force = data.get("force") or "push"
        mechanic = data.get("mechanic") or "compound"
        equipment = data.get("equipment") or "other"
        category = data.get("category") or "strength"
        primary = data.get("primaryMuscles") or []
        secondary = data.get("secondaryMuscles") or []

        return Exercise(
            id=data["id"],
            name=data["name"],
            name_cn=data["name"],  # 中文名待补全
            force=force,
            force_cn=FORCE_CN.get(force, force),
            level=data.get("level", "intermediate"),
            level_cn=LEVEL_CN.get(data.get("level", ""), "中级"),
            mechanic=mechanic,
            mechanic_cn=MECHANIC_CN.get(mechanic, mechanic),
            equipment=equipment,
            equipment_cn=EQUIPMENT_CN.get(equipment, equipment),
            primary_muscles=primary,
            primary_muscles_cn=[MUSCLE_CN.get(m, m) for m in primary],
            secondary_muscles=secondary,
            secondary_muscles_cn=[MUSCLE_CN.get(m, m) for m in secondary],
            instructions=data.get("instructions", []),
            category=category,
            category_cn=CATEGORY_CN.get(category, category),
            images=data.get("images", []),
        )

    def _index(self, ex: Exercise):
        """建立索引"""
        for m in ex.primary_muscles_cn:
            self._by_muscle.setdefault(m, []).append(ex.id)
        self._by_equipment.setdefault(ex.equipment_cn, []).append(ex.id)
        self._by_level.setdefault(ex.level_cn, []).append(ex.id)
        self._by_category.setdefault(ex.category_cn, []).append(ex.id)
        self._by_mechanic.setdefault(ex.mechanic_cn, []).append(ex.id)

    # ---- 查询接口 ----

    def get(self, ex_id: str) -> Optional[Exercise]:
        return self._exercises.get(ex_id)

    def search(self, keyword: str) -> list[Exercise]:
        """按关键词搜索 (名称/肌肉/器械)"""
        kw = keyword.lower()
        results = []
        for ex in self._exercises.values():
            if (kw in ex.name.lower() or
                kw in ex.equipment_cn or
                any(kw in m for m in ex.primary_muscles_cn) or
                any(kw in m for m in ex.secondary_muscles_cn) or
                kw in ex.category_cn or
                kw in ex.mechanic_cn):
                results.append(ex)
        return results

    def filter(
        self,
        muscle: str = None,
        equipment: str = None,
        level: str = None,
        category: str = None,
        mechanic: str = None,
        force: str = None,
    ) -> list[Exercise]:
        """多条件筛选"""
        ids = set(self._exercises.keys())

        if muscle:
            ids &= set(self._by_muscle.get(muscle, []))
        if equipment:
            ids &= set(self._by_equipment.get(equipment, []))
        if level:
            ids &= set(self._by_level.get(level, []))
        if category:
            ids &= set(self._by_category.get(category, []))
        if mechanic:
            ids &= set(self._by_mechanic.get(mechanic, []))

        results = [self._exercises[eid] for eid in ids]
        if force:
            results = [e for e in results if e.force_cn == force]
        return results

    def list_muscles(self) -> list[str]:
        """列出所有肌肉群"""
        return sorted(self._by_muscle.keys())

    def list_equipment(self) -> list[str]:
        """列出所有器械类型"""
        return sorted(self._by_equipment.keys())

    def list_levels(self) -> list[str]:
        """列出所有难度级别"""
        return sorted(self._by_level.keys())

    def random_workout(self, target_muscle: str, count: int = 4) -> list[Exercise]:
        """为指定肌肉群随机选 N 个动作"""
        ids = self._by_muscle.get(target_muscle, [])
        if len(ids) < count:
            count = len(ids)
        chosen = random.sample(ids, count) if count > 0 else []
        return [self._exercises[eid] for eid in chosen]

    def get_all(self) -> list[Exercise]:
        return list(self._exercises.values())

    def stats(self) -> dict:
        """数据库统计"""
        return {
            "total_exercises": len(self._exercises),
            "muscles": len(self._by_muscle),
            "equipment_types": len(self._by_equipment),
            "levels": self.list_levels(),
            "categories": list(self._by_category.keys()),
        }


# ============================================================
# 常用训练计划模板
# ============================================================

# 经典五分化训练
BRO_SPLIT = {
    "周一-胸": ["chest", "triceps"],
    "周二-背": ["lats", "middle back", "biceps"],
    "周三-肩": ["shoulders", "traps"],
    "周四-腿": ["quadriceps", "hamstrings", "glutes", "calves"],
    "周五-臂": ["biceps", "triceps", "forearms"],
}

# 推拉腿 (PPL)
PPL_SPLIT = {
    "推日": ["chest", "shoulders", "triceps"],
    "拉日": ["lats", "middle back", "biceps", "traps"],
    "腿日": ["quadriceps", "hamstrings", "glutes", "calves"],
}

# 全身训练 (新手推荐)
FULL_BODY = {
    "全身A": ["chest", "lats", "quadriceps", "shoulders", "abdominals"],
    "全身B": ["middle back", "hamstrings", "glutes", "triceps", "biceps"],
}

# 上肢/下肢二分
UPPER_LOWER = {
    "上肢": ["chest", "lats", "shoulders", "biceps", "triceps", "traps"],
    "下肢": ["quadriceps", "hamstrings", "glutes", "calves", "abdominals"],
}

TRAINING_TEMPLATES = {
    "五分化 (Bro Split)": BRO_SPLIT,
    "推拉腿 (PPL)": PPL_SPLIT,
    "全身训练 (Full Body)": FULL_BODY,
    "上下肢二分 (Upper/Lower)": UPPER_LOWER,
}


def generate_workout_plan(db: ExerciseDatabase, template_name: str = "推拉腿 (PPL)",
                          exercises_per_day: int = 6) -> dict:
    """根据模板生成训练计划"""
    template = TRAINING_TEMPLATES.get(template_name)
    if not template:
        return {"error": f"未知模板: {template_name}, 可选: {list(TRAINING_TEMPLATES.keys())}"}

    plan = {}
    for day_name, muscles in template.items():
        day_exercises = []
        # 从每个肌肉群选动作
        per_muscle = max(1, exercises_per_day // len(muscles))
        for m_en in muscles:
            m_cn = MUSCLE_CN.get(m_en, m_en)
            candidates = db.filter(muscle=m_cn)
            if candidates:
                # 优先复合动作
                compounds = [e for e in candidates if e.mechanic_cn == "复合动作"]
                isolations = [e for e in candidates if e.mechanic_cn == "孤立动作"]
                chosen = (compounds[:per_muscle] + isolations[:per_muscle])[:per_muscle]
                day_exercises.extend(chosen)

        plan[day_name] = day_exercises[:exercises_per_day]

    return plan


# ============================================================
# 命令行工具
# ============================================================

if __name__ == "__main__":
    import sys

    db = ExerciseDatabase()

    # 尝试从默认路径加载
    default_paths = [
        "temp/exercise-db-temp/exercises",
        "../temp/exercise-db-temp/exercises",
        "../../temp/exercise-db-temp/exercises",
    ]
    loaded = False
    for p in default_paths:
        if os.path.exists(p):
            db.load_from_dir(p)
            loaded = True
            break

    if not loaded:
        print("❌ 找不到锻炼数据库，请先运行: git clone https://github.com/yuhonas/free-exercise-db.git temp/exercise-db-temp")
        sys.exit(1)

    stats = db.stats()
    print(f"\n📊 数据库统计: {stats['total_exercises']} 个动作, "
          f"{stats['muscles']} 个肌肉群, {stats['equipment_types']} 种器械")

    print(f"\n💪 肌肉群: {', '.join(db.list_muscles())}")

    # 示例: 搜索胸肌动作
    print("\n" + "=" * 60)
    print("🔍 示例: 搜索'胸肌' + 杠铃 + 复合动作")
    chest_ex = db.filter(muscle="胸肌", equipment="杠铃", mechanic="复合动作")
    for ex in chest_ex[:5]:
        print(f"  • {ex.summary()}")

    # 示例: 生成推拉腿训练计划
    print("\n" + "=" * 60)
    print("📋 示例: 推拉腿 (PPL) 训练计划")
    plan = generate_workout_plan(db, "推拉腿 (PPL)", exercises_per_day=6)
    for day, exercises in plan.items():
        print(f"\n  【{day}】")
        for ex in exercises:
            print(f"    • {ex.summary()}")
            if ex.instructions:
                print(f"      → {ex.instructions[0][:80]}...")
