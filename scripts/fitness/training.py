#!/usr/bin/env python3
"""
训练计划生成器
=============
基于运动科学周期化训练理论，支持：
- 线性周期 (Linear Periodization)
- 波浪周期 (Undulating Periodization)
- 增肌/力量/减脂/耐力四种目标
- 自动生成 4-12 周训练计划

参考:
- streprogen (Python, MIT): https://github.com/tommyod/streprogen
- STMr (R): https://github.com/mladenjovanovic/STMr
- ACSM 训练指南
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math
import random
from datetime import date, timedelta


# ============================================================
# 枚举和常量
# ============================================================

class TrainingGoal(Enum):
    STRENGTH = ("力量", "以1RM提升为目标, 大重量低次数 (1-5 reps)")
    HYPERTROPHY = ("增肌", "以肌肉增长为目标, 中等重量 (6-12 reps)")
    ENDURANCE = ("耐力", "以肌耐力提升为目标, 轻重量高次数 (12-20 reps)")
    FAT_LOSS = ("减脂", "以减脂为目标, 中高次数 + 有氧 + 热量缺口")
    GENERAL = ("综合体能", "均衡发展, 多种训练方式结合")

    def __init__(self, label: str, description: str):
        self.label = label
        self.description = description


class TrainingLevel(Enum):
    BEGINNER = ("初级", "训练经验 < 6个月")
    INTERMEDIATE = ("中级", "训练经验 6个月-2年")
    ADVANCED = ("高级", "训练经验 > 2年")

    def __init__(self, label: str, description: str):
        self.label = label
        self.description = description


class SplitType(Enum):
    FULL_BODY = ("全身训练", 3)       # 每周3次
    UPPER_LOWER = ("上下肢分化", 4)    # 每周4次
    PPL = ("推拉腿", 6)               # 每周6次
    BRO_SPLIT = ("五分化", 5)         # 每周5次
    THREE_DAY = ("三分化", 3)         # 每周3次

    def __init__(self, label: str, sessions_per_week: int):
        self.label = label
        self.sessions_per_week = sessions_per_week


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ExercisePrescription:
    """单个动作处方"""
    name: str
    sets: int
    reps: str           # "8-12" 或 "5" 等
    rpe: str            # RPE (自感用力等级) "7-8" 或 "8-9"
    rest_seconds: int   # 组间休息(秒)
    notes: str = ""

@dataclass
class WorkoutSession:
    """单次训练课"""
    day_name: str
    focus: str
    exercises: list[ExercisePrescription]
    warmup: list[str]
    cooldown: list[str]
    duration_min: int
    estimated_calories: int

@dataclass
class WeeklyPlan:
    """周训练计划"""
    week_number: int
    phase: str
    sessions: list[WorkoutSession]
    weekly_volume_note: str

@dataclass
class TrainingProgram:
    """完整训练计划"""
    name: str
    goal: TrainingGoal
    level: TrainingLevel
    split: SplitType
    duration_weeks: int
    weekly_plans: list[WeeklyPlan]
    progression_scheme: str
    notes: list[str]


# ============================================================
# 训练计划生成引擎
# ============================================================

class ProgramGenerator:
    """训练计划生成器"""

    # 目标对应的训练参数
    GOAL_PARAMS = {
        TrainingGoal.STRENGTH: {
            "reps_range": (1, 6),
            "sets_range": (3, 6),
            "rest_range": (120, 300),
            "rpe": "7-9",
            "compound_ratio": 0.8,    # 80%复合动作
        },
        TrainingGoal.HYPERTROPHY: {
            "reps_range": (6, 12),
            "sets_range": (3, 4),
            "rest_range": (60, 120),
            "rpe": "7-9",
            "compound_ratio": 0.6,
        },
        TrainingGoal.ENDURANCE: {
            "reps_range": (12, 20),
            "sets_range": (2, 3),
            "rest_range": (30, 60),
            "rpe": "6-8",
            "compound_ratio": 0.5,
        },
        TrainingGoal.FAT_LOSS: {
            "reps_range": (8, 15),
            "sets_range": (3, 4),
            "rest_range": (45, 90),
            "rpe": "7-8",
            "compound_ratio": 0.6,
        },
        TrainingGoal.GENERAL: {
            "reps_range": (6, 15),
            "sets_range": (3, 4),
            "rest_range": (60, 120),
            "rpe": "7-8",
            "compound_ratio": 0.65,
        },
    }

    # 经典动作库 (后续由 exercise_db 提供)
    EXERCISE_LIBRARY = {
        "胸": {
            "compound": ["杠铃卧推", "哑铃卧推", "上斜杠铃卧推", "双杠臂屈伸"],
            "isolation": ["哑铃飞鸟", "龙门架夹胸", "上斜哑铃飞鸟", "器械推胸"],
        },
        "背": {
            "compound": ["杠铃划船", "引体向上", "高位下拉", "T杆划船", "哑铃单臂划船"],
            "isolation": ["直臂下压", "面拉", "坐姿划船", "山羊挺身"],
        },
        "肩": {
            "compound": ["杠铃推举", "哑铃推举", "阿诺德推举"],
            "isolation": ["侧平举", "前平举", "俯身飞鸟", "直立划船"],
        },
        "腿": {
            "compound": ["杠铃深蹲", "罗马尼亚硬拉", "保加利亚分腿蹲", "腿举", "传统硬拉"],
            "isolation": ["腿屈伸", "腿弯举", "提踵", "臀推", "髋外展"],
        },
        "手臂": {
            "compound": ["窄距卧推", "反握引体向上"],
            "isolation": ["杠铃弯举", "哑铃弯举", "锤式弯举", "绳索下压",
                       "臂屈伸", "集中弯举", "牧师凳弯举"],
        },
        "核心": {
            "compound": ["悬垂举腿", "负重卷腹"],
            "isolation": ["平板支撑", "卷腹", "俄罗斯转体", "死虫式", "鸟狗式"],
        },
    }

    # 分化训练模板
    SPLIT_TEMPLATES = {
        SplitType.FULL_BODY: {
            "全身A": ["腿", "胸", "背", "肩", "核心"],
            "全身B": ["腿", "背", "胸", "手臂", "核心"],
            "全身C": ["腿", "肩", "胸", "背", "核心"],
        },
        SplitType.UPPER_LOWER: {
            "上肢-力量": ["胸", "背", "肩"],
            "下肢-力量": ["腿", "核心"],
            "上肢-肌肥大": ["胸", "手臂", "肩"],
            "下肢-肌肥大": ["腿", "核心"],
        },
        SplitType.PPL: {
            "推日-1": ["胸", "肩", "手臂"],  # 推: 胸+肩前束+三头
            "拉日-1": ["背", "手臂"],        # 拉: 背+二头+后束
            "腿日-1": ["腿", "核心"],
            "推日-2": ["肩", "胸", "手臂"],
            "拉日-2": ["背", "手臂"],
            "腿日-2": ["腿", "核心"],
        },
        SplitType.BRO_SPLIT: {
            "胸日": ["胸"],
            "背日": ["背"],
            "肩日": ["肩"],
            "腿日": ["腿"],
            "臂日": ["手臂"],
        },
        SplitType.THREE_DAY: {
            "上身": ["胸", "背", "肩", "手臂"],
            "下身": ["腿", "核心"],
            "全身": ["腿", "胸", "背", "肩", "核心"],
        },
    }

    @staticmethod
    def generate(
        goal: TrainingGoal = TrainingGoal.HYPERTROPHY,
        level: TrainingLevel = TrainingLevel.BEGINNER,
        split: SplitType = SplitType.FULL_BODY,
        duration_weeks: int = 8,
        seed: int = None,
    ) -> TrainingProgram:
        """生成完整训练计划"""
        if seed is not None:
            random.seed(seed)

        params = ProgramGenerator.GOAL_PARAMS[goal]
        template = ProgramGenerator.SPLIT_TEMPLATES[split]

        # 根据水平调整
        if level == TrainingLevel.BEGINNER:
            exercises_per_session = 5
            duration_weeks = min(duration_weeks, 8)
        elif level == TrainingLevel.INTERMEDIATE:
            exercises_per_session = 7
            duration_weeks = min(duration_weeks, 12)
        else:
            exercises_per_session = 9
            duration_weeks = min(duration_weeks, 16)

        # 周期化阶段
        if goal == TrainingGoal.STRENGTH:
            phases = [
                ("基础适应期", 1, 3, "中等重量, 建立动作模式"),
                ("力量积累期", 4, max(5, duration_weeks - 3), "逐步增加重量, 降低次数"),
                ("峰值期", max(6, duration_weeks - 2), duration_weeks, "冲击大重量, 测试1RM"),
            ]
        elif goal == TrainingGoal.HYPERTROPHY:
            phases = [
                ("适应期", 1, 2, "学习动作, 建立神经连接"),
                ("增肌期-1", 3, max(4, duration_weeks // 2), "中等重量, 8-12次, 追求泵感"),
                ("增肌期-2", max(5, duration_weeks // 2 + 1), duration_weeks, "增加训练量, 加入强度技巧"),
            ]
        else:
            phases = [
                ("适应期", 1, 2, "建立基础"),
                ("主训练期", 3, duration_weeks, "常规训练"),
            ]

        # 生成每周计划
        weekly_plans = []
        for week_num in range(1, duration_weeks + 1):
            phase_name = "主训练期"
            phase_note = ""
            for p_name, p_start, p_end, p_note in phases:
                if p_start <= week_num <= p_end:
                    phase_name = p_name
                    phase_note = p_note
                    break

            sessions = ProgramGenerator._generate_week(
                week_num, goal, level, template, params,
                exercises_per_session, phase_name
            )
            weekly_plans.append(WeeklyPlan(
                week_number=week_num,
                phase=phase_name,
                sessions=sessions,
                weekly_volume_note=phase_note,
            ))

        # 渐进超负荷策略
        if goal == TrainingGoal.STRENGTH:
            progression = "每周增加 2.5-5kg 主要动作重量, 或增加 1 组"
        elif goal == TrainingGoal.HYPERTROPHY:
            progression = "每周在保持次数的前提下增加重量, 或增加训练量"
        elif goal == TrainingGoal.ENDURANCE:
            progression = "每周增加 2 次重复或减少 15 秒休息"
        else:
            progression = "保持训练强度, 结合有氧逐步增加消耗"

        notes = [
            f"目标: {goal.label} — {goal.description}",
            f"水平: {level.label} — {level.description}",
            f"分化: {split.label}, 每周 {split.sessions_per_week} 次训练",
            f"渐进策略: {progression}",
            "每个训练日先做复合动作, 再做孤立动作",
            "每次训练前热身 5-10 分钟, 训练后拉伸 5-10 分钟",
            "保证每天 7-8 小时睡眠, 蛋白质摄入 1.6-2.2g/kg体重",
        ]

        return TrainingProgram(
            name=f"{goal.label}训练计划 — {split.label} ({duration_weeks}周)",
            goal=goal,
            level=level,
            split=split,
            duration_weeks=duration_weeks,
            weekly_plans=weekly_plans,
            progression_scheme=progression,
            notes=notes,
        )

    @staticmethod
    def _generate_week(
        week_num: int,
        goal: TrainingGoal,
        level: TrainingLevel,
        template: dict[str, list[str]],
        params: dict,
        exercises_per_session: int,
        phase: str,
    ) -> list[WorkoutSession]:
        """生成一周的训练课表"""
        sessions = []
        reps_lo, reps_hi = params["reps_range"]
        sets_lo, sets_hi = params["sets_range"]
        rest_lo, rest_hi = params["rest_range"]
        rpe = params["rpe"]
        compound_ratio = params["compound_ratio"]

        # 根据周期调整
        if "力量" in phase:
            reps_lo = max(1, reps_lo - 2)
            reps_hi = max(2, reps_hi - 4)
        elif "峰值" in phase:
            reps_lo = 1
            reps_hi = 3
            sets_lo += 1

        for day_name, muscle_groups in template.items():
            exercises = []

            for mg in muscle_groups:
                lib = ProgramGenerator.EXERCISE_LIBRARY.get(mg, {})
                compounds = lib.get("compound", [])
                isolations = lib.get("isolation", [])

                n_compound = max(1, int(exercises_per_session * compound_ratio / len(muscle_groups)))
                n_isolation = max(0, int(exercises_per_session * (1 - compound_ratio) / len(muscle_groups)))

                if compounds:
                    chosen_c = random.sample(compounds, min(n_compound, len(compounds)))
                    for name in chosen_c:
                        exercises.append(ExercisePrescription(
                            name=name,
                            sets=random.randint(sets_lo, sets_hi),
                            reps=f"{reps_lo}-{reps_hi}",
                            rpe=rpe,
                            rest_seconds=random.randint(rest_lo, rest_hi),
                            notes="核心动作, 注意动作质量",
                        ))

                if isolations and n_isolation > 0:
                    chosen_i = random.sample(isolations, min(n_isolation, len(isolations)))
                    for name in chosen_i:
                        exercises.append(ExercisePrescription(
                            name=name,
                            sets=random.randint(max(2, sets_lo - 1), sets_hi),
                            reps=f"{reps_lo}-{reps_hi}",
                            rpe=rpe,
                            rest_seconds=random.randint(max(45, rest_lo - 15), rest_hi),
                            notes="感受肌肉发力",
                        ))

            # 热身和放松
            warmup = [
                "关节环绕 (5分钟)",
                "动态拉伸: 开合跳/高抬腿/侧弓步",
                "轻重量动作热身 (2组 × 15次)",
            ]
            cooldown = [
                "静态拉伸目标肌群 (每动作20-30秒)",
                "泡沫轴放松 (可选)",
                "深呼吸恢复",
            ]

            sessions.append(WorkoutSession(
                day_name=day_name,
                focus="、".join(muscle_groups),
                exercises=exercises[:exercises_per_session],
                warmup=warmup,
                cooldown=cooldown,
                duration_min=45 + len(exercises) * 5,
                estimated_calories=300 + len(exercises) * 50,
            ))

        return sessions

    @staticmethod
    def generate_cutting_program(body_weight_kg: float, weeks: int = 8) -> TrainingProgram:
        """生成减脂专项计划 (力量训练 + 有氧 + 饮食建议)"""
        program = ProgramGenerator.generate(
            goal=TrainingGoal.FAT_LOSS,
            level=TrainingLevel.INTERMEDIATE,
            split=SplitType.UPPER_LOWER,
            duration_weeks=weeks,
        )

        # 附加有氧建议
        program.notes.append(f"每日步数目标: 10,000-12,000 步")
        program.notes.append(f"每周 2-3 次空腹有氧 (快走30分钟) 或 HIIT (15分钟)")
        program.notes.append(f"每日热量摄入: BMR × 1.2 (约 {round(body_weight_kg * 24, 0)} kcal)")

        return program


# ============================================================
# 命令行展示
# ============================================================

def print_program(program: TrainingProgram):
    """打印训练计划"""
    print("=" * 70)
    print(f"🏋️  {program.name}")
    print("=" * 70)
    print(f"🎯 目标: {program.goal.label} | 📊 水平: {program.level.label}")
    print(f"📅 分化: {program.split.label} | ⏱️  周期: {program.duration_weeks} 周")
    print(f"📈 渐进策略: {program.progression_scheme}")
    print()

    for wp in program.weekly_plans:
        print(f"--- 第 {wp.week_number} 周 ({wp.phase}): {wp.weekly_volume_note} ---")
        for session in wp.sessions:
            print(f"\n  📅 {session.day_name} (主攻: {session.focus}) "
                  f"[约{session.duration_min}分钟, ~{session.estimated_calories}kcal]")

            print("  🔥 热身:")
            for w in session.warmup[:2]:
                print(f"     - {w}")

            print("  💪 正式训练:")
            for i, ex in enumerate(session.exercises, 1):
                print(f"     {i}. {ex.name}: {ex.sets}组 × {ex.reps}次 | "
                      f"RPE {ex.rpe} | 休息{ex.rest_seconds}秒")
                if ex.notes:
                    print(f"        ↳ {ex.notes}")

            print("  🧊 放松:")
            for c in session.cooldown[:2]:
                print(f"     - {c}")
        print()

    print("📝 注意事项:")
    for note in program.notes:
        print(f"  • {note}")


if __name__ == "__main__":
    # 示例1: 新手增肌计划
    print("示例1: 新手增肌 — 全身训练 8周")
    program1 = ProgramGenerator.generate(
        goal=TrainingGoal.HYPERTROPHY,
        level=TrainingLevel.BEGINNER,
        split=SplitType.FULL_BODY,
        duration_weeks=8,
        seed=42,
    )
    # 只打印首周
    p1_short = TrainingProgram(
        name=program1.name, goal=program1.goal, level=program1.level,
        split=program1.split, duration_weeks=program1.duration_weeks,
        weekly_plans=[program1.weekly_plans[0]],
        progression_scheme=program1.progression_scheme,
        notes=program1.notes,
    )
    print_program(p1_short)

    print("\n" + "=" * 70)
    print("示例2: 中级力量训练 — 推拉腿 12周")
    program2 = ProgramGenerator.generate(
        goal=TrainingGoal.STRENGTH,
        level=TrainingLevel.INTERMEDIATE,
        split=SplitType.PPL,
        duration_weeks=12,
        seed=7,
    )
    p2_short = TrainingProgram(
        name=program2.name, goal=program2.goal, level=program2.level,
        split=program2.split, duration_weeks=program2.duration_weeks,
        weekly_plans=[program2.weekly_plans[0]],
        progression_scheme=program2.progression_scheme,
        notes=program2.notes,
    )
    print_program(p2_short)
