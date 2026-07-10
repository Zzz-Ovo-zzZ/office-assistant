#!/usr/bin/env python3
"""
健身 & 饮食助手模块
===================
提供完整的健身和饮食指导能力:

模块:
  engine      - 健身计算引擎 (BMI/BMR/TDEE/体脂/1RM/心率)
  food_db     - 中国食物营养成分数据库 (1677种食物 + GI指数)
  exercise_db - 锻炼动作数据库 (800+ 动作)
  training    - 训练计划生成器

快速使用:
  from scripts.fitness import quick_report
  report = quick_report(性别="男", 年龄=30, 身高=175, 体重=78)
"""

from .engine import (
    FitnessEngine, BodyProfile, Gender, ActivityLevel,
    Goal, MacroPreset, BodyType,
    BMIResult, BMRResult, TDEEResult, BodyFatResult,
    OneRMResult, HeartRateResult, DailyPlan,
    quick_assess,
)

from .food_db import FoodDatabase, FoodItem, FoodCategory
from .exercise_db import ExerciseDatabase, Exercise, generate_workout_plan
from .training import (
    ProgramGenerator, TrainingProgram,
    TrainingGoal, TrainingLevel, SplitType,
    print_program,
)


def quick_report(
    gender: str = "男",
    age: int = 30,
    height_cm: float = 175,
    weight_kg: float = 78,
    waist_cm: float = None,
    neck_cm: float = None,
    hip_cm: float = None,
    goal: str = "maintain",
    activity: str = "moderate",
) -> dict:
    """
    一键生成健身评估报告

    参数:
      gender: "男" / "女"
      age: 年龄
      height_cm: 身高(cm)
      weight_kg: 体重(kg)
      waist_cm: 腰围(cm), 可选
      neck_cm: 颈围(cm), 可选
      hip_cm: 臀围(cm), 可选(女性)
      goal: "cut"(减脂) / "bulk"(增肌) / "maintain"(维持) / "recomp"(塑形)
      activity: "sedentary" / "light" / "moderate" / "active" / "extreme"

    返回:
      包含 BMI/体脂/BMR/TDEE/宏量营养素/心率/饮食计划 的完整报告
    """
    return quick_assess(
        gender=gender, age=age, height_cm=height_cm, weight_kg=weight_kg,
        waist_cm=waist_cm, neck_cm=neck_cm, hip_cm=hip_cm,
        goal=goal, activity=activity,
    )


def print_quick_report(report: dict):
    """格式化打印评估报告"""
    print("=" * 60)
    print("🏋️  健身 & 饮食综合评估报告")
    print("=" * 60)

    bmi = report["bmi"]
    bf = report["body_fat"]
    print(f"\n📊 BMI: {bmi.bmi} ({bmi.category_cn})")
    print(f"💪 体脂率: {bf.body_fat_pct}% ({bf.category} — {bf.method})")
    print(f"   脂肪量: {bf.fat_mass_kg}kg | 瘦体重: {bf.lean_mass_kg}kg")
    print(f"🔥 BMR: {report['bmr']} kcal/天 | TDEE: {report['tdee']} kcal/天")
    print(f"🎯 目标: {report['goal']} | 每日摄入: {report['target_calories']} kcal")
    print(f"🍽️  蛋白: {report['macros']['protein_g']}g | "
          f"碳水: {report['macros']['carb_g']}g | 脂肪: {report['macros']['fat_g']}g")
    print(f"💓 最大心率: {report['heart_rate'].max_hr} bpm")
    print(f"⚖️  理想体重: {report['ideal_weight_range'][0]}-{report['ideal_weight_range'][1]} kg")
    print(f"\n💡 {report['bf_advice']}")
    print(f"💡 {report['weight_advice']}")

    plan = report["daily_plan"]
    print(f"\n📋 每日饮食 ({plan.target_calories} kcal, {plan.water_liters}L水):")
    for meal in plan.meals:
        print(f"   {meal['餐次']}: {meal['热量_kcal']}kcal | "
              f"P{meal['蛋白_g']}g C{meal['碳水_g']}g F{meal['脂肪_g']}g")
    for tip in plan.tips:
        print(f"   💡 {tip}")


__all__ = [
    "FitnessEngine", "BodyProfile", "Gender", "ActivityLevel",
    "Goal", "MacroPreset", "BodyType",
    "FoodDatabase", "FoodItem",
    "ExerciseDatabase", "Exercise", "generate_workout_plan",
    "ProgramGenerator", "TrainingProgram", "TrainingGoal",
    "TrainingLevel", "SplitType", "print_program",
    "quick_report", "print_quick_report",
]
