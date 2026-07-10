#!/usr/bin/env python3
"""
健身 & 饮食计算引擎
====================
基于运动科学标准公式，提供完整的身体指标计算、营养规划、训练负荷评估。

参考来源:
- @finegym/fitness-calc (TypeScript 库, MIT)
- streprogen (Python 训练计划生成器, MIT)
- ACSM 运动科学指南
- Mifflin-St Jeor / Harris-Benedict / Katch-McArdle 公式
- U.S. Navy 体脂估算方法
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# ============================================================
# 枚举定义
# ============================================================

class Gender(Enum):
    MALE = "male"
    FEMALE = "female"

class ActivityLevel(Enum):
    """活动水平 (用于 TDEE 计算)"""
    SEDENTARY = ("久坐不动", 1.2)           # 几乎不运动
    LIGHT = ("轻度活动", 1.375)              # 每周 1-3 天轻度运动
    MODERATE = ("中度活动", 1.55)            # 每周 3-5 天中等强度运动
    ACTIVE = ("高度活动", 1.725)             # 每周 6-7 天高强度运动
    EXTREME = ("极高活动", 1.9)              # 每天高强度运动 + 体力劳动

    def __init__(self, label: str, multiplier: float):
        self.label = label
        self.multiplier = multiplier

class Goal(Enum):
    CUT = ("减脂", -500)       # 每日热量缺口 500kcal
    MAINTAIN = ("维持", 0)
    BULK = ("增肌", 500)       # 每日热量盈余 500kcal
    RECOMP = ("身体重塑", -200) # 轻微缺口 + 高蛋白

    def __init__(self, label: str, calorie_adjust: int):
        self.label = label
        self.calorie_adjust = calorie_adjust

class MacroPreset(Enum):
    """宏量营养素预设比例"""
    BALANCED = ("均衡", 0.30, 0.40, 0.30)     # 蛋白30% 碳水40% 脂肪30%
    LOW_CARB = ("低碳水", 0.40, 0.20, 0.40)    # 蛋白40% 碳水20% 脂肪40%
    HIGH_CARB = ("高碳水", 0.20, 0.60, 0.20)   # 蛋白20% 碳水60% 脂肪20%
    KETO = ("生酮", 0.25, 0.05, 0.70)          # 蛋白25% 碳水5% 脂肪70%
    HIGH_PROTEIN = ("高蛋白", 0.40, 0.35, 0.25) # 蛋白40% 碳水35% 脂肪25%

    def __init__(self, label: str, protein_ratio: float, carb_ratio: float, fat_ratio: float):
        self.label = label
        self.protein_ratio = protein_ratio
        self.carb_ratio = carb_ratio
        self.fat_ratio = fat_ratio

class BodyType(Enum):
    ECTOMORPH = ("外胚型", "偏瘦，增肌较慢，代谢高")
    MESOMORPH = ("中胚型", "天生运动型，增肌减脂都较快")
    ENDOMORPH = ("内胚型", "偏胖，易增肌但也易囤脂")

    def __init__(self, label: str, description: str):
        self.label = label
        self.description = description

# ============================================================
# 用户身体数据
# ============================================================

@dataclass
class BodyProfile:
    """用户身体档案"""
    gender: Gender
    age: int                      # 岁
    height_cm: float              # 身高 (cm)
    weight_kg: float              # 体重 (kg)
    neck_cm: Optional[float] = None    # 颈围 (cm) - Navy 体脂法
    waist_cm: Optional[float] = None   # 腰围 (cm) - Navy 体脂法
    hip_cm: Optional[float] = None     # 臀围 (cm) - Navy 体脂法(女性)
    body_fat_pct: Optional[float] = None  # 已知体脂率时可直接输入
    activity_level: ActivityLevel = ActivityLevel.MODERATE

    @property
    def height_m(self) -> float:
        return self.height_cm / 100

# ============================================================
# 输出数据结构
# ============================================================

@dataclass
class BMIResult:
    bmi: float
    category: str
    category_cn: str
    healthy_weight_min: float
    healthy_weight_max: float
    prime: float  # BMI / 理想BMI上限

@dataclass
class BMRResult:
    bmr: float
    formula: str

@dataclass
class TDEEResult:
    tdee: float
    bmr: float
    activity_level: ActivityLevel
    goal: Goal
    target_calories: float      # 目标每日热量
    protein_g: float
    carb_g: float
    fat_g: float

@dataclass
class BodyFatResult:
    body_fat_pct: float
    fat_mass_kg: float
    lean_mass_kg: float
    method: str
    category: str

@dataclass
class OneRMResult:
    weight: float
    reps: int
    estimated_1rm: dict[str, float]  # 各公式结果
    best_estimate: float             # 平均

@dataclass
class HeartRateResult:
    max_hr: int
    resting_hr: int
    zones: dict[str, tuple[int, int]]

@dataclass
class DailyPlan:
    """每日饮食与训练计划"""
    target_calories: int
    protein_g: int
    carb_g: int
    fat_g: int
    meals: list[dict]
    water_liters: float
    tips: list[str]

# ============================================================
# 核心计算函数
# ============================================================

class FitnessEngine:
    """健身计算引擎"""

    # ---------------------------- BMI ----------------------------

    @staticmethod
    def calc_bmi(weight_kg: float, height_cm: float) -> BMIResult:
        """计算 BMI 及分级"""
        h = height_cm / 100
        bmi = weight_kg / (h * h)

        # 中国 BMI 标准 (比 WHO 更严格)
        if bmi < 18.5:
            category, cn = "underweight", "偏瘦"
        elif bmi < 24.0:
            category, cn = "normal", "正常"
        elif bmi < 28.0:
            category, cn = "overweight", "偏胖"
        else:
            category, cn = "obese", "肥胖"

        healthy_min = 18.5 * h * h
        healthy_max = 24.0 * h * h
        prime = bmi / 24.0

        return BMIResult(
            bmi=round(bmi, 1),
            category=category,
            category_cn=cn,
            healthy_weight_min=round(healthy_min, 1),
            healthy_weight_max=round(healthy_max, 1),
            prime=round(prime, 2)
        )

    # ---------------------------- BMR ----------------------------

    @staticmethod
    def calc_bmr_mifflin_st_jeor(profile: BodyProfile) -> float:
        """Mifflin-St Jeor 公式 (1990) — 公认最准确"""
        w, h, a = profile.weight_kg, profile.height_cm, profile.age
        if profile.gender == Gender.MALE:
            return 10 * w + 6.25 * h - 5 * a + 5
        else:
            return 10 * w + 6.25 * h - 5 * a - 161

    @staticmethod
    def calc_bmr_harris_benedict(profile: BodyProfile) -> float:
        """Harris-Benedict 公式 (1919, 1984修订)"""
        w, h, a = profile.weight_kg, profile.height_cm, profile.age
        if profile.gender == Gender.MALE:
            return 88.362 + 13.397 * w + 4.799 * h - 5.677 * a
        else:
            return 447.593 + 9.247 * w + 3.098 * h - 4.330 * a

    @staticmethod
    def calc_bmr_katch_mcardle(profile: BodyProfile) -> Optional[float]:
        """Katch-McArdle 公式 (基于瘦体重, 最精确但需体脂率)"""
        bf = profile.body_fat_pct
        if bf is None:
            bf_result = FitnessEngine.calc_body_fat_navy(profile)
            if bf_result is None:
                return None
            bf = bf_result.body_fat_pct
        lbm = profile.weight_kg * (1 - bf / 100)
        return 370 + 21.6 * lbm

    @staticmethod
    def calc_bmr(profile: BodyProfile) -> BMRResult:
        """综合 BMR 计算 (优先 Katch-McArdle，其次 Mifflin-St Jeor)"""
        km = FitnessEngine.calc_bmr_katch_mcardle(profile)
        if km is not None:
            return BMRResult(bmr=round(km, 0), formula="Katch-McArdle (基于瘦体重)")
        msj = FitnessEngine.calc_bmr_mifflin_st_jeor(profile)
        return BMRResult(bmr=round(msj, 0), formula="Mifflin-St Jeor")

    # ---------------------------- TDEE & 宏量营养素 ----------------------------

    @staticmethod
    def calc_tdee(profile: BodyProfile, goal: Goal = Goal.MAINTAIN,
                  macro: MacroPreset = MacroPreset.BALANCED) -> TDEEResult:
        """计算 TDEE + 目标热量 + 宏量营养素分配"""
        bmr_result = FitnessEngine.calc_bmr(profile)
        bmr = bmr_result.bmr
        tdee = bmr * profile.activity_level.multiplier
        target = tdee + goal.calorie_adjust

        # 下限保护
        if profile.gender == Gender.MALE:
            target = max(target, 1500)
        else:
            target = max(target, 1200)

        protein_kcal = target * macro.protein_ratio
        carb_kcal = target * macro.carb_ratio
        fat_kcal = target * macro.fat_ratio

        return TDEEResult(
            tdee=round(tdee, 0),
            bmr=round(bmr, 0),
            activity_level=profile.activity_level,
            goal=goal,
            target_calories=round(target, 0),
            protein_g=round(protein_kcal / 4, 1),   # 1g蛋白 = 4kcal
            carb_g=round(carb_kcal / 4, 1),          # 1g碳水 = 4kcal
            fat_g=round(fat_kcal / 9, 1),            # 1g脂肪 = 9kcal
        )

    # ---------------------------- 体脂率 ----------------------------

    @staticmethod
    def calc_body_fat_navy(profile: BodyProfile) -> Optional[BodyFatResult]:
        """U.S. Navy 体脂估算方法"""
        if profile.neck_cm is None or profile.waist_cm is None:
            return None
        h = profile.height_cm
        n = profile.neck_cm
        w = profile.waist_cm

        if profile.gender == Gender.MALE:
            bf = 86.010 * math.log10(w - n) - 70.041 * math.log10(h) + 36.76
        else:
            if profile.hip_cm is None:
                return None
            hp = profile.hip_cm
            bf = 163.205 * math.log10(w + hp - n) - 97.684 * math.log10(h) - 78.387

        bf = max(2.0, min(bf, 60.0))  # 约束范围
        fat_mass = profile.weight_kg * bf / 100
        lean_mass = profile.weight_kg - fat_mass

        if profile.gender == Gender.MALE:
            if bf < 6: cat = "必需脂肪"
            elif bf < 14: cat = "运动员"
            elif bf < 18: cat = "健壮"
            elif bf < 25: cat = "正常"
            else: cat = "肥胖"
        else:
            if bf < 14: cat = "必需脂肪"
            elif bf < 21: cat = "运动员"
            elif bf < 25: cat = "健壮"
            elif bf < 32: cat = "正常"
            else: cat = "肥胖"

        return BodyFatResult(
            body_fat_pct=round(bf, 1),
            fat_mass_kg=round(fat_mass, 1),
            lean_mass_kg=round(lean_mass, 1),
            method="U.S. Navy",
            category=cat,
        )

    @staticmethod
    def calc_body_fat_bmi(profile: BodyProfile) -> BodyFatResult:
        """BMI 推估体脂率 (Deurenberg 公式, 1991)"""
        bmi = profile.weight_kg / ((profile.height_cm / 100) ** 2)
        a = profile.age
        if profile.gender == Gender.MALE:
            bf = 1.20 * bmi + 0.23 * a - 10.8 * 1 - 5.4
        else:
            bf = 1.20 * bmi + 0.23 * a - 10.8 * 0 - 5.4
        bf = max(2.0, min(bf, 60.0))
        fat_mass = profile.weight_kg * bf / 100
        lean_mass = profile.weight_kg - fat_mass
        return BodyFatResult(
            body_fat_pct=round(bf, 1),
            fat_mass_kg=round(fat_mass, 1),
            lean_mass_kg=round(lean_mass, 1),
            method="BMI 推估 (Deurenberg)",
            category="估算值",
        )

    # ---------------------------- 1RM (单次最大重量) ----------------------------

    @staticmethod
    def calc_1rm(weight_kg: float, reps: int) -> OneRMResult:
        """用 7 种公式估算 1RM"""
        w, r = weight_kg, reps
        formulas = {}

        if r == 1:
            formulas["实际"] = w
        else:
            formulas["Epley"] = w * (1 + r / 30)
            formulas["Brzycki"] = w * (36 / (37 - r)) if r < 37 else w
            formulas["Lombardi"] = w * (r ** 0.10)
            formulas["Mayhew"] = w / (0.522 + 0.419 * math.exp(-0.055 * r)) if r <= 10 else w
            formulas["O'Conner"] = w * (1 + r / 40)
            formulas["Wathan"] = w / (0.488 + 0.538 * math.exp(-0.075 * r))
            formulas["Lander"] = w / (1.013 - 0.0267123 * r) if r < 38 else w

        valid = [v for v in formulas.values()]
        best = sum(valid) / len(valid) if valid else w

        return OneRMResult(
            weight=w,
            reps=r,
            estimated_1rm={k: round(v, 1) for k, v in formulas.items()},
            best_estimate=round(best, 1),
        )

    # ---------------------------- 心率区间 ----------------------------

    @staticmethod
    def calc_heart_rate_zones(age: int, resting_hr: int = 70) -> HeartRateResult:
        """Karovonen 心率储备法计算训练区间"""
        max_hr = 220 - age
        hrr = max_hr - resting_hr  # 心率储备

        zones = {
            "热身/恢复": (
                round(resting_hr + hrr * 0.50),
                round(resting_hr + hrr * 0.60),
            ),
            "燃脂/有氧基础": (
                round(resting_hr + hrr * 0.60),
                round(resting_hr + hrr * 0.70),
            ),
            "有氧耐力": (
                round(resting_hr + hrr * 0.70),
                round(resting_hr + hrr * 0.80),
            ),
            "无氧阈值": (
                round(resting_hr + hrr * 0.80),
                round(resting_hr + hrr * 0.90),
            ),
            "极限冲刺": (
                round(resting_hr + hrr * 0.90),
                max_hr,
            ),
        }

        return HeartRateResult(
            max_hr=max_hr,
            resting_hr=resting_hr,
            zones=zones,
        )

    # ---------------------------- 卡路里消耗估算 (MET) ----------------------------

    # 常见运动的 MET 值 (Compendium of Physical Activities)
    MET_VALUES = {
        "跑步(8km/h)": 8.0,
        "跑步(10km/h)": 10.0,
        "跑步(12km/h)": 12.5,
        "快走(6km/h)": 5.0,
        "散步(4km/h)": 3.0,
        "骑行(20km/h)": 8.0,
        "骑行(25km/h)": 10.0,
        "游泳(自由泳)": 8.0,
        "游泳(蛙泳)": 10.0,
        "跳绳(中速)": 10.0,
        "跳绳(快速)": 12.0,
        "HIIT": 12.0,
        "深蹲": 5.0,
        "硬拉": 6.0,
        "卧推": 6.0,
        "引体向上": 8.0,
        "俯卧撑": 8.0,
        "仰卧起坐": 7.0,
        "瑜伽": 3.0,
        "普拉提": 3.5,
        "太极": 4.0,
        "篮球": 8.0,
        "足球": 9.0,
        "羽毛球": 5.5,
        "乒乓球": 4.0,
        "登山": 7.0,
        "爬楼梯": 8.0,
        "划船机(中速)": 7.0,
        "椭圆机": 5.0,
    }

    @staticmethod
    def calc_calorie_burn(profile: BodyProfile, activity: str, duration_min: int) -> float:
        """计算某项运动的热量消耗 (kcal)"""
        met = FitnessEngine.MET_VALUES.get(activity, 5.0)
        return met * profile.weight_kg * duration_min / 60

    # ---------------------------- 理想体重 ----------------------------

    @staticmethod
    def ideal_weight(height_cm: float, gender: Gender) -> tuple[float, float]:
        """
        理想体重范围 (基于 BMI 22 和多种公式)
        返回 (下限, 上限)
        """
        h = height_cm / 100

        # Hamwi 公式 (1964)
        if gender == Gender.MALE:
            hamwi = 48.0 + 2.7 * (height_cm - 152.4) / 2.54
        else:
            hamwi = 45.5 + 2.2 * (height_cm - 152.4) / 2.54

        # Devine 公式 (1974)
        if gender == Gender.MALE:
            devine = 50.0 + 2.3 * (height_cm - 152.4) / 2.54
        else:
            devine = 45.5 + 2.3 * (height_cm - 152.4) / 2.54

        # BMI 22 理想体重
        bmi22 = 22 * h * h

        ideal_low = min(hamwi, devine, bmi22)
        ideal_high = max(hamwi, devine, bmi22)

        return round(ideal_low, 1), round(ideal_high, 1)

    # ============================================================
    # 综合评估
    # ============================================================

    @staticmethod
    def full_assessment(profile: BodyProfile, goal: Goal = Goal.MAINTAIN,
                        macro: MacroPreset = MacroPreset.BALANCED) -> dict:
        """生成完整的身体评估报告"""
        bmi = FitnessEngine.calc_bmi(profile.weight_kg, profile.height_cm)
        tdee = FitnessEngine.calc_tdee(profile, goal, macro)
        hr = FitnessEngine.calc_heart_rate_zones(profile.age)
        ideal_low, ideal_high = FitnessEngine.ideal_weight(profile.height_cm, profile.gender)

        bf = FitnessEngine.calc_body_fat_navy(profile)
        if bf is None:
            bf = FitnessEngine.calc_body_fat_bmi(profile)

        # 体型判断
        if bmi.bmi < 18.5:
            body_type_hint = BodyType.ECTOMORPH
        elif bmi.bmi < 24:
            body_type_hint = BodyType.MESOMORPH if bf.body_fat_pct < 20 else BodyType.ENDOMORPH
        else:
            body_type_hint = BodyType.ENDOMORPH

        # 体脂评估
        if profile.gender == Gender.MALE:
            bf_advice = "体脂率偏低，建议增肌" if bf.body_fat_pct < 10 else (
                "体脂率健康" if bf.body_fat_pct < 20 else "体脂率偏高，建议减脂"
            )
        else:
            bf_advice = "体脂率偏低，建议增肌" if bf.body_fat_pct < 18 else (
                "体脂率健康" if bf.body_fat_pct < 28 else "体脂率偏高，建议减脂"
            )

        # 体重差
        weight_diff = profile.weight_kg - ideal_high
        if weight_diff > 0:
            weight_advice = f"超出理想体重上限 {weight_diff:.1f}kg，建议减重"
        elif profile.weight_kg < ideal_low:
            weight_advice = f"低于理想体重下限 {ideal_low - profile.weight_kg:.1f}kg，建议增重"
        else:
            weight_advice = "体重在理想范围内"

        return {
            "bmi": bmi,
            "body_fat": bf,
            "bmr": tdee.bmr,
            "tdee": tdee.tdee,
            "target_calories": tdee.target_calories,
            "macros": {
                "protein_g": tdee.protein_g,
                "carb_g": tdee.carb_g,
                "fat_g": tdee.fat_g,
            },
            "heart_rate": hr,
            "ideal_weight_range": (ideal_low, ideal_high),
            "body_type": body_type_hint,
            "bf_advice": bf_advice,
            "weight_advice": weight_advice,
            "goal": goal.label,
            "macro_preset": macro.label,
            "activity_level": profile.activity_level.label,
            "daily_plan": FitnessEngine._build_daily_plan(tdee),
        }

    # ---------------------------- 每日饮食计划 ----------------------------

    @staticmethod
    def _build_daily_plan(tdee: TDEEResult) -> DailyPlan:
        """生成每日饮食框架"""
        cal = int(tdee.target_calories)
        p = int(tdee.protein_g)
        c = int(tdee.carb_g)
        f = int(tdee.fat_g)
        water = round(FitnessEngine._calc_water(cal), 1)

        # 三餐分配 (30% / 40% / 30%)
        meals = [
            {
                "餐次": "早餐 (30%)",
                "热量_kcal": int(cal * 0.30),
                "蛋白_g": int(p * 0.30),
                "碳水_g": int(c * 0.30),
                "脂肪_g": int(f * 0.30),
                "建议": "高蛋白+复合碳水, 如: 鸡蛋2个+燕麦50g+牛奶250ml",
            },
            {
                "餐次": "午餐 (40%)",
                "热量_kcal": int(cal * 0.40),
                "蛋白_g": int(p * 0.40),
                "碳水_g": int(c * 0.40),
                "脂肪_g": int(f * 0.40),
                "建议": "瘦肉+杂粮饭+蔬菜, 如: 鸡胸肉150g+糙米饭200g+西兰花",
            },
            {
                "餐次": "晚餐 (30%)",
                "热量_kcal": int(cal * 0.30),
                "蛋白_g": int(p * 0.30),
                "碳水_g": int(c * 0.30),
                "脂肪_g": int(f * 0.30),
                "建议": "鱼类/豆腐+蔬菜+少量主食, 如: 三文鱼120g+藜麦100g+时蔬",
            },
        ]

        tips = []
        if tdee.goal == Goal.CUT:
            tips = [
                "每餐先吃蔬菜增加饱腹感",
                "蛋白质摄入充足以保护肌肉",
                "训练安排在餐前或餐后2小时",
                "每天保证7-8小时睡眠帮助减脂",
            ]
        elif tdee.goal == Goal.BULK:
            tips = [
                "可增加1-2次加餐(坚果/希腊酸奶/蛋白粉)",
                "训练后30分钟内补充快碳+蛋白",
                "优先复合动作(深蹲/硬拉/卧推)刺激全身增长",
                "每周增重控制在0.25-0.5kg",
            ]
        else:
            tips = [
                "保持规律进食, 不要跳过早餐",
                "训练日可适当增加碳水",
                "注意食物多样性, 摄入足够微量元素",
            ]

        return DailyPlan(
            target_calories=cal,
            protein_g=p,
            carb_g=c,
            fat_g=f,
            meals=meals,
            water_liters=water,
            tips=tips,
        )

    @staticmethod
    def _calc_water(daily_calories: int) -> float:
        """估算每日饮水量 (升)"""
        # 每千卡约需 1-1.5ml 水
        # 基础 2000ml + 热量补偿
        return max(2.0, daily_calories / 1000 + 1.0)


# ============================================================
# 命令行快速评估
# ============================================================

def quick_assess(gender: str, age: int, height_cm: float, weight_kg: float,
                 waist_cm: float = None, neck_cm: float = None,
                 hip_cm: float = None, goal: str = "maintain",
                 activity: str = "moderate"):
    """快速体检 - 命令行友好"""
    g = Gender.MALE if gender.lower() in ("m", "male", "男") else Gender.FEMALE
    al_map = {
        "sedentary": ActivityLevel.SEDENTARY,
        "light": ActivityLevel.LIGHT,
        "moderate": ActivityLevel.MODERATE,
        "active": ActivityLevel.ACTIVE,
        "extreme": ActivityLevel.EXTREME,
    }
    goal_map = {
        "cut": Goal.CUT,
        "maintain": Goal.MAINTAIN,
        "bulk": Goal.BULK,
        "recomp": Goal.RECOMP,
    }

    profile = BodyProfile(
        gender=g, age=age, height_cm=height_cm, weight_kg=weight_kg,
        waist_cm=waist_cm, neck_cm=neck_cm, hip_cm=hip_cm,
        activity_level=al_map.get(activity, ActivityLevel.MODERATE),
    )

    result = FitnessEngine.full_assessment(profile, goal_map.get(goal, Goal.MAINTAIN))
    return result


# ============================================================
# 自测
# ============================================================

if __name__ == "__main__":
    # 示例: 30岁男性, 175cm, 78kg
    profile = BodyProfile(
        gender=Gender.MALE,
        age=30,
        height_cm=175,
        weight_kg=78,
        waist_cm=82,
        neck_cm=38,
        activity_level=ActivityLevel.MODERATE,
    )

    print("=" * 60)
    print("🏋️  健身 & 饮食综合评估报告")
    print("=" * 60)

    result = FitnessEngine.full_assessment(profile, Goal.CUT, MacroPreset.HIGH_PROTEIN)

    print(f"\n📊 BMI: {result['bmi'].bmi} ({result['bmi'].category_cn})")
    print(f"💪 体脂率: {result['body_fat'].body_fat_pct}% ({result['body_fat'].category})")
    print(f"   - 脂肪量: {result['body_fat'].fat_mass_kg}kg")
    print(f"   - 瘦体重: {result['body_fat'].lean_mass_kg}kg")
    print(f"🔥 BMR: {result['bmr']} kcal/天")
    print(f"🏃 TDEE: {result['tdee']} kcal/天 (活动水平: {result['activity_level']})")
    print(f"🎯 目标: {result['goal']}, 目标热量: {result['target_calories']} kcal/天")
    print(f"\n🍽️  宏量营养素分配 ({result['macro_preset']}):")
    print(f"   蛋白质: {result['macros']['protein_g']}g")
    print(f"   碳水:   {result['macros']['carb_g']}g")
    print(f"   脂肪:   {result['macros']['fat_g']}g")

    print(f"\n💓 心率区间:")
    for zone, (lo, hi) in result['heart_rate'].zones.items():
        print(f"   {zone}: {lo}-{hi} bpm")

    print(f"\n⚖️  理想体重范围: {result['ideal_weight_range'][0]}-{result['ideal_weight_range'][1]} kg")
    print(f"   体型倾向: {result['body_type'].label} ({result['body_type'].description})")
    print(f"   {result['weight_advice']}")
    print(f"   {result['bf_advice']}")

    plan = result['daily_plan']
    print(f"\n📋 每日饮食计划 ({plan.target_calories} kcal):")
    print(f"   饮水量: {plan.water_liters}升")
    for meal in plan.meals:
        print(f"   {meal['餐次']}: {meal['热量_kcal']}kcal | "
              f"蛋白{meal['蛋白_g']}g 碳水{meal['碳水_g']}g 脂肪{meal['脂肪_g']}g")
        print(f"     → {meal['建议']}")

    print(f"\n💡 小贴士:")
    for t in plan.tips:
        print(f"   • {t}")

    # 测试 1RM
    print(f"\n🏋️  1RM 估算测试 (卧推 80kg × 8次):")
    rm = FitnessEngine.calc_1rm(80, 8)
    for formula, val in rm.estimated_1rm.items():
        print(f"   {formula}: {val}kg")
    print(f"   最佳估算: {rm.best_estimate}kg")

    # 测试热量消耗
    print(f"\n🏃 运动热量消耗 (30分钟):")
    for activity in ["跑步(10km/h)", "游泳(自由泳)", "HIIT", "跳绳(中速)"]:
        burn = FitnessEngine.calc_calorie_burn(profile, activity, 30)
        print(f"   {activity}: {burn:.0f} kcal")
