#!/usr/bin/env python3
"""
健身助手 — 命令行工具
=====================
快速访问所有健身/饮食功能。

用法:
  python cli.py assess           # 身体评估
  python cli.py bmi 75 175       # BMI 计算
  python cli.py 1rm 80 8         # 1RM 估算
  python cli.py tdee             # TDEE 计算 (交互式)
  python cli.py plan             # 生成训练计划
  python cli.py food 搜索词      # 搜索食物
  python cli.py exercise 搜索词  # 搜索锻炼动作
  python cli.py meal 食物码...   # 计算一餐营养
"""

import sys
import os
import json

# 确保可以导入 fitness 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.fitness.engine import (
    FitnessEngine, BodyProfile, Gender, ActivityLevel,
    Goal, MacroPreset, quick_assess, print as _,
)
from scripts.fitness.training import (
    ProgramGenerator, TrainingGoal, TrainingLevel,
    SplitType, print_program,
)
from scripts.fitness.food_db import FoodDatabase
from scripts.fitness.exercise_db import ExerciseDatabase


def cmd_assess():
    """交互式身体评估"""
    print("=" * 50)
    print("🏋️  身体评估")
    print("=" * 50)

    g = input("性别 (男/女) [男]: ").strip() or "男"
    a = int(input("年龄 [30]: ").strip() or "30")
    h = float(input("身高(cm) [175]: ").strip() or "175")
    w = float(input("体重(kg) [78]: ").strip() or "78")
    waist = input("腰围(cm) [可选]: ").strip()
    neck = input("颈围(cm) [可选]: ").strip()

    print("\n活动水平:")
    for al in ActivityLevel:
        print(f"  {al.name}: {al.label}")
    al_input = input("选择 [MODERATE]: ").strip().upper() or "MODERATE"
    al = getattr(ActivityLevel, al_input, ActivityLevel.MODERATE)

    print("\n目标:")
    for g_enum in Goal:
        print(f"  {g_enum.name}: {g_enum.label}")
    goal_input = input("选择 [MAINTAIN]: ").strip().upper() or "MAINTAIN"
    goal = getattr(Goal, goal_input, Goal.MAINTAIN)

    gw = Gender.MALE if g in ("男", "m", "male") else Gender.FEMALE
    profile = BodyProfile(
        gender=gw, age=a, height_cm=h, weight_kg=w,
        waist_cm=float(waist) if waist else None,
        neck_cm=float(neck) if neck else None,
        activity_level=al,
    )

    result = FitnessEngine.full_assessment(profile, goal, MacroPreset.BALANCED)

    print("\n" + "=" * 50)
    print("📊 评估结果")
    print("=" * 50)

    bmi = result["bmi"]
    bf = result["body_fat"]
    hr = result["heart_rate"]

    print(f"""
╔══════════════════════════════════════╗
║  BMI: {bmi.bmi:<5} ({bmi.category_cn:<4})               ║
║  体脂: {bf.body_fat_pct:<5}% ({bf.category:<10})  ║
║  瘦体重: {bf.lean_mass_kg:<5}kg  脂肪量: {bf.fat_mass_kg:<5}kg  ║
║  BMR: {result['bmr']:<5} kcal/天                 ║
║  TDEE: {result['tdee']:<5} kcal/天                ║
║  目标摄入: {result['target_calories']:<5} kcal/天            ║
╠══════════════════════════════════════╣
║  蛋白质: {result['macros']['protein_g']:<5}g                    ║
║  碳水:   {result['macros']['carb_g']:<5}g                    ║
║  脂肪:   {result['macros']['fat_g']:<5}g                    ║
╠══════════════════════════════════════╣
║  最大心率: {hr.max_hr} bpm                     ║
║  理想体重: {result['ideal_weight_range'][0]}-{result['ideal_weight_range'][1]} kg             ║
╚══════════════════════════════════════╝
""")

    print(f"💡 {result['bf_advice']}")
    print(f"💡 {result['weight_advice']}")

    plan = result["daily_plan"]
    print(f"\n📋 每日饮食 ({plan.target_calories} kcal, 💧{plan.water_liters}L):")
    for meal in plan.meals:
        print(f"   {meal['餐次']}: {meal['热量_kcal']}kcal | "
              f"P{meal['蛋白_g']}g C{meal['碳水_g']}g F{meal['脂肪_g']}g")


def cmd_bmi():
    """快速 BMI"""
    if len(sys.argv) < 4:
        print("用法: python cli.py bmi <体重kg> <身高cm>")
        return
    w = float(sys.argv[2])
    h = float(sys.argv[3])
    result = FitnessEngine.calc_bmi(w, h)
    print(f"BMI: {result.bmi} — {result.category_cn}")
    print(f"健康体重范围: {result.healthy_weight_min}-{result.healthy_weight_max} kg")


def cmd_1rm():
    """1RM 估算"""
    if len(sys.argv) < 4:
        print("用法: python cli.py 1rm <重量kg> <次数>")
        return
    w = float(sys.argv[2])
    r = int(sys.argv[3])
    result = FitnessEngine.calc_1rm(w, r)
    print(f"\n🏋️  1RM 估算 ({w}kg × {r}次):")
    print(f"   最佳估算: {result.best_estimate}kg")
    for formula, val in result.estimated_1rm.items():
        print(f"   {formula}: {val}kg")


def cmd_plan():
    """生成训练计划"""
    print("\n🎯 选择目标:")
    for g in TrainingGoal:
        print(f"   {g.name}: {g.label} — {g.description}")
    goal_name = input("目标 [HYPERTROPHY]: ").strip().upper() or "HYPERTROPHY"
    goal = getattr(TrainingGoal, goal_name, TrainingGoal.HYPERTROPHY)

    print("\n📊 选择水平:")
    for l in TrainingLevel:
        print(f"   {l.name}: {l.label}")
    lvl_name = input("水平 [BEGINNER]: ").strip().upper() or "BEGINNER"
    level = getattr(TrainingLevel, lvl_name, TrainingLevel.BEGINNER)

    print("\n📅 选择分化方式:")
    for s in SplitType:
        print(f"   {s.name}: {s.label} (每周{s.sessions_per_week}次)")
    split_name = input("分化 [FULL_BODY]: ").strip().upper() or "FULL_BODY"
    split = getattr(SplitType, split_name, SplitType.FULL_BODY)

    weeks = int(input("训练周期(周) [8]: ").strip() or "8")

    program = ProgramGenerator.generate(goal, level, split, weeks, seed=None)
    print_program(program)


def cmd_food():
    """搜索/分析食物"""
    if len(sys.argv) < 3:
        print("用法: python cli.py food <搜索词>")
        print("示例: python cli.py food 鸡胸")
        return

    keyword = sys.argv[2]
    db = FoodDatabase()

    # 加载数据
    data_dirs = [
        "data/nutrition/all_foods.json",
        "../data/nutrition/all_foods.json",
        "../../data/nutrition/all_foods.json",
    ]
    loaded = False
    for d in data_dirs:
        if os.path.exists(d):
            with open(d, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # 直接从 JSON 搜索
            results = []
            kw = keyword.lower()
            for item in raw_data:
                name = item.get("foodName", "")
                if kw in name.lower():
                    results.append(item)

            if results:
                print(f"\n🔍 搜索 '{keyword}' 的结果 ({len(results)} 条):\n")
                for r in results[:20]:
                    print(f"  📛 {r.get('foodName', '?')} ({r.get('foodCode', '?')})")
                    print(f"     {r.get('energyKCal', '?')}kcal | "
                          f"蛋白{r.get('protein', '?')}g | "
                          f"脂肪{r.get('fat', '?')}g | "
                          f"碳水{r.get('CHO', '?')}g | "
                          f"纤维{r.get('dietaryFiber', '?')}g")
                    print()
            else:
                print(f"未找到含 '{keyword}' 的食物")

            loaded = True
            break

    if not loaded:
        print("❌ 食物数据未找到，请先运行数据处理脚本。")


def cmd_exercise():
    """搜索锻炼动作"""
    if len(sys.argv) < 3:
        print("用法: python cli.py exercise <搜索词>")
        print("示例: python cli.py exercise chest")
        return

    keyword = sys.argv[2]
    db = ExerciseDatabase()

    data_dirs = [
        "temp/exercise-db-temp/exercises",
        "../temp/exercise-db-temp/exercises",
        "../../temp/exercise-db-temp/exercises",
    ]
    loaded = False
    for d in data_dirs:
        if os.path.exists(d):
            db.load_from_dir(d)
            loaded = True
            break

    if not loaded:
        print("❌ 锻炼数据未找到")
        return

    results = db.search(keyword)
    print(f"\n🔍 搜索 '{keyword}' 的结果 ({len(results)} 条):\n")
    for ex in results[:15]:
        print(f"  • {ex.summary()}")
        if ex.instructions:
            print(f"    → {ex.instructions[0][:100]}...")


def cmd_meal():
    """计算一餐营养 (使用食物编码)"""
    print("此功能需要先加载食物数据库")
    print("示例: python cli.py meal")
    print()
    print("交互式: 输入食物名称和克数，计算一餐总营养")

    data_dirs = [
        "data/nutrition/all_foods.json",
        "../data/nutrition/all_foods.json",
    ]
    raw_data = None
    for d in data_dirs:
        if os.path.exists(d):
            with open(d, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            break

    if not raw_data:
        print("❌ 食物数据未找到")
        return

    # 建立名称索引
    name_index = {}
    for item in raw_data:
        name = item.get("foodName", "")
        if name:
            name_index[name.lower()] = item

    total = {"energy": 0, "protein": 0, "fat": 0, "cho": 0, "fiber": 0}
    items = []

    print("输入食物名称和克数 (如 '鸡蛋 100')，输入 'done' 结束:\n")

    while True:
        inp = input("> ").strip()
        if inp.lower() == "done" or inp == "":
            break

        parts = inp.rsplit(" ", 1)
        if len(parts) != 2:
            print("  格式: 食物名称 克数")
            continue

        food_name, grams_str = parts
        try:
            grams = float(grams_str)
        except ValueError:
            print("  克数必须是数字")
            continue

        # 模糊搜索
        found = None
        for name, item in name_index.items():
            if food_name.lower() in name:
                found = item
                break

        if not found:
            print(f"  未找到 '{food_name}'")
            continue

        factor = grams / 100
        try:
            edible = float(found.get("edible", 100))
        except:
            edible = 100
        factor *= edible / 100

        e = float(found.get("energyKCal", 0) or 0) * factor
        p = float(found.get("protein", 0) or 0) * factor
        f_val = float(found.get("fat", 0) or 0) * factor
        c = float(found.get("CHO", 0) or 0) * factor
        fib = float(found.get("dietaryFiber", 0) or 0) * factor

        items.append((found["foodName"], grams, e, p, f_val, c))
        total["energy"] += e
        total["protein"] += p
        total["fat"] += f_val
        total["cho"] += c
        total["fiber"] += fib

    print("\n" + "=" * 50)
    print("🍽️  一餐营养汇总")
    print("=" * 50)
    for name, g, e, p, f_val, c in items:
        print(f"  {name} {g}g → {e:.0f}kcal | P{p:.1f}g F{f_val:.1f}g C{c:.1f}g")

    t = total
    print(f"\n  📊 总计: {t['energy']:.0f}kcal | "
          f"蛋白{t['protein']:.1f}g | 脂肪{t['fat']:.1f}g | "
          f"碳水{t['cho']:.1f}g | 纤维{t['fiber']:.1f}g")


# ============================================================
# 命令路由
# ============================================================

COMMANDS = {
    "assess": cmd_assess,
    "bmi": cmd_bmi,
    "1rm": cmd_1rm,
    "plan": cmd_plan,
    "food": cmd_food,
    "exercise": cmd_exercise,
    "meal": cmd_meal,
}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n可用命令:")
        for name, func in COMMANDS.items():
            print(f"  {name:<12} {func.__doc__ or ''}")
        return

    cmd = sys.argv[1].lower()
    if cmd in COMMANDS:
        COMMANDS[cmd]()
    else:
        print(f"未知命令: {cmd}")
        print(f"可用命令: {', '.join(COMMANDS.keys())}")


if __name__ == "__main__":
    main()
