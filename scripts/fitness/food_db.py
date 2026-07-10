#!/usr/bin/env python3
"""
中国食物营养成分数据库
=======================
基于《中国食物成分表标准版(第6版)》视觉大模型识别数据 + 食物GI指数
共计 1677 条食物数据 + GI 指数

数据来源: https://github.com/Sanotsu/china-food-composition-data
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# 数据模型
# ============================================================

class FoodCategory(Enum):
    """食物分类"""
    GRAINS = "谷类及其制品"
    TUBERS = "薯类/淀粉类"
    BEANS = "干豆类及其制品"
    VEGETABLES = "蔬菜类"
    FRUITS = "水果类"
    NUTS = "坚果/种子"
    MEAT_POULTRY = "畜肉类及其制品"
    POULTRY = "禽肉类及其制品"
    EGGS = "蛋类及其制品"
    FISH = "鱼类"
    SEAFOOD = "虾蟹贝类"
    MILK = "乳类及其制品"
    OILS = "油脂类"
    BEVERAGES = "饮料类"
    SEASONING = "调味品类"
    SNACKS = "小吃/零食"
    FAST_FOOD = "快餐食品"
    ALCOHOL = "酒精饮料"


@dataclass
class FoodItem:
    """食物营养成分条目"""
    food_code: str          # 食物编码
    food_name: str          # 食物名称
    category: str           # 食物分类
    edible: float           # 可食部(%)
    water: float            # 水分(g/100g)
    energy_kcal: float      # 能量(kcal/100g)
    energy_kj: float        # 能量(kJ/100g)
    protein: float          # 蛋白质(g/100g)
    fat: float              # 脂肪(g/100g)
    cho: float              # 碳水化合物(g/100g)
    dietary_fiber: float    # 膳食纤维(g/100g)
    cholesterol: float      # 胆固醇(mg/100g)
    vitamin_a: float        # 维生素A(μg/100g)
    carotene: float         # 胡萝卜素(μg/100g)
    thiamin: float          # 硫胺素B1(mg/100g)
    riboflavin: float       # 核黄素B2(mg/100g)
    niacin: float           # 烟酸(mg/100g)
    vitamin_c: float        # 维生素C(mg/100g)
    vitamin_e: float        # 维生素E(mg/100g)
    calcium: float          # 钙(mg/100g)
    phosphorus: float       # 磷(mg/100g)
    potassium: float        # 钾(mg/100g)
    sodium: float           # 钠(mg/100g)
    magnesium: float        # 镁(mg/100g)
    iron: float             # 铁(mg/100g)
    zinc: float             # 锌(mg/100g)
    selenium: float         # 硒(μg/100g)
    copper: float           # 铜(mg/100g)
    manganese: float        # 锰(mg/100g)
    gi: Optional[float] = None  # 血糖生成指数
    gl: Optional[float] = None  # 血糖负荷 (per 100g)

    def to_dict(self) -> dict:
        return {
            "food_code": self.food_code,
            "food_name": self.food_name,
            "category": self.category,
            "edible": self.edible,
            "energy_kcal": self.energy_kcal,
            "energy_kj": self.energy_kj,
            "protein": self.protein,
            "fat": self.fat,
            "cho": self.cho,
            "dietary_fiber": self.dietary_fiber,
            "cholesterol": self.cholesterol,
            "calcium": self.calcium,
            "iron": self.iron,
            "zinc": self.zinc,
            "sodium": self.sodium,
            "potassium": self.potassium,
            "magnesium": self.magnesium,
            "vitamin_c": self.vitamin_c,
            "gi": self.gi,
        }

    def macro_summary(self) -> str:
        """宏量营养素摘要"""
        return (f"{self.food_name} (每100g): "
                f"{self.energy_kcal:.0f}kcal | "
                f"蛋白{self.protein:.1f}g | "
                f"脂肪{self.fat:.1f}g | "
                f"碳水{self.cho:.1f}g | "
                f"纤维{self.dietary_fiber:.1f}g")

    def is_low_gi(self) -> bool:
        return self.gi is not None and self.gi <= 55

    def is_medium_gi(self) -> bool:
        return self.gi is not None and 56 <= self.gi <= 69

    def is_high_gi(self) -> bool:
        return self.gi is not None and self.gi >= 70

    def protein_density(self) -> float:
        """蛋白密度 (g/100kcal) — 越高越适合减脂"""
        if self.energy_kcal == 0:
            return 0
        return self.protein / self.energy_kcal * 100


class FoodDatabase:
    """食物营养成分数据库"""

    def __init__(self):
        self._foods: dict[str, FoodItem] = {}  # food_code -> FoodItem
        self._by_name: dict[str, list[str]] = {}  # food_name_lower -> [food_codes]
        self._by_category: dict[str, list[str]] = {}
        self._gi_map: dict[str, float] = {}  # food_name -> GI

    def load_food_data(self, data_dir: str):
        """加载中国食物成分表 JSON 数据"""
        data_path = Path(data_dir)
        count = 0
        for json_file in data_path.glob("*.json"):
            category = self._extract_category(json_file.stem)
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    items = json.load(f)
                for item in items:
                    if not item.get("foodName"):
                        continue
                    food = self._parse_food(item, category)
                    self._foods[food.food_code] = food
                    name_key = food.food_name.lower()
                    self._by_name.setdefault(name_key, []).append(food.food_code)
                    self._by_category.setdefault(category, []).append(food.food_code)
                    count += 1
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  跳过 {json_file.name}: {e}")

        print(f"✅ 加载了 {count} 种食物 (来自 {len(self._by_category)} 个分类)")

    def load_gi_data(self, gi_file: str):
        """加载血糖生成指数数据"""
        with open(gi_file, "r", encoding="utf-8") as f:
            gi_data = json.load(f)

        for group in gi_data:
            for item in group.get("list", []):
                name = item.get("foodName", "")
                gi_val = item.get("GI")
                if name and gi_val is not None:
                    self._gi_map[name] = float(gi_val)
                    # 同时存关联名称
                    self._gi_map[name.strip()] = float(gi_val)

        # 将 GI 数据匹配到食物
        matched = 0
        for food in self._foods.values():
            if food.food_name in self._gi_map:
                food.gi = self._gi_map[food.food_name]
                if food.cho > 0:
                    food.gl = food.gi * food.cho / 100
                matched += 1

        print(f"✅ 加载了 {len(gi_data)} 组 GI 数据, 成功匹配 {matched} 种食物")

    def _parse_food(self, item: dict, category: str) -> FoodItem:
        """解析单条食物数据"""
        def _f(key: str, default: float = 0.0) -> float:
            try:
                v = item.get(key)
                if v is None or v == "" or v == "—" or v == "…" or v == "Tr" or v == "tr":
                    return default
                return float(v)
            except (ValueError, TypeError):
                return default

        return FoodItem(
            food_code=item.get("foodCode", ""),
            food_name=item.get("foodName", ""),
            category=category,
            edible=_f("edible", 100),
            water=_f("water"),
            energy_kcal=_f("energyKCal"),
            energy_kj=_f("energyKJ"),
            protein=_f("protein"),
            fat=_f("fat"),
            cho=_f("CHO"),
            dietary_fiber=_f("dietaryFiber"),
            cholesterol=_f("cholesterol"),
            vitamin_a=_f("vitaminA"),
            carotene=_f("carotene"),
            thiamin=_f("thiamin"),
            riboflavin=_f("riboflavin"),
            niacin=_f("niacin"),
            vitamin_c=_f("vitaminC"),
            vitamin_e=_f("vitaminETotal"),
            calcium=_f("Ca"),
            phosphorus=_f("P"),
            potassium=_f("K"),
            sodium=_f("Na"),
            magnesium=_f("Mg"),
            iron=_f("Fe"),
            zinc=_f("Zn"),
            selenium=_f("Se"),
            copper=_f("Cu"),
            manganese=_f("Mn"),
        )

    def _extract_category(self, filename: str) -> str:
        """从文件名提取分类"""
        # merged_畜肉类及其制品-猪.json -> 畜肉类及其制品
        name = filename.replace("merged_", "").replace("merged-", "")
        parts = name.rsplit("-", 1)
        return parts[0] if len(parts) > 1 else name

    # ---- 查询接口 ----

    def search(self, keyword: str, limit: int = 20) -> list[FoodItem]:
        """搜索食物 (名称模糊匹配)"""
        kw = keyword.lower()
        results = []
        for food in self._foods.values():
            if kw in food.food_name.lower() or kw in food.category.lower():
                results.append(food)
        return results[:limit]

    def get_by_code(self, code: str) -> Optional[FoodItem]:
        return self._foods.get(code)

    def get_by_category(self, category: str) -> list[FoodItem]:
        codes = self._by_category.get(category, [])
        return [self._foods[c] for c in codes if c in self._foods]

    def list_categories(self) -> list[str]:
        return sorted(self._by_category.keys())

    def count(self) -> int:
        return len(self._foods)

    # ---- 高级查询 ----

    def top_protein_density(self, min_protein: float = 10, limit: int = 20) -> list[FoodItem]:
        """高蛋白密度食物排名 (减脂友好)"""
        candidates = [f for f in self._foods.values()
                      if f.protein >= min_protein and f.energy_kcal > 0]
        candidates.sort(key=lambda f: f.protein_density(), reverse=True)
        return candidates[:limit]

    def low_gi_foods(self, category: str = None, limit: int = 30) -> list[FoodItem]:
        """低GI食物列表"""
        results = [f for f in self._foods.values() if f.is_low_gi()]
        if category:
            results = [f for f in results if f.category == category]
        results.sort(key=lambda f: f.gi or 100)
        return results[:limit]

    def high_potassium_foods(self, limit: int = 20) -> list[FoodItem]:
        """高钾食物 (>300mg/100g)"""
        results = [f for f in self._foods.values() if f.potassium >= 300]
        results.sort(key=lambda f: f.potassium, reverse=True)
        return results[:limit]

    def high_calcium_foods(self, limit: int = 20) -> list[FoodItem]:
        """高钙食物 (>150mg/100g)"""
        results = [f for f in self._foods.values() if f.calcium >= 150]
        results.sort(key=lambda f: f.calcium, reverse=True)
        return results[:limit]

    def high_iron_foods(self, limit: int = 20) -> list[FoodItem]:
        """富铁食物 (>5mg/100g)"""
        results = [f for f in self._foods.values() if f.iron >= 5]
        results.sort(key=lambda f: f.iron, reverse=True)
        return results[:limit]

    def compare_foods(self, codes: list[str]) -> list[FoodItem]:
        """对比多种食物"""
        return [self._foods[c] for c in codes if c in self._foods]

    def meal_nutrition(self, items: list[tuple[str, float]]) -> dict:
        """
        计算一餐的总营养
        items: [(food_code, grams), ...]
        """
        total = {
            "energy_kcal": 0, "protein": 0, "fat": 0, "cho": 0,
            "dietary_fiber": 0, "calcium": 0, "iron": 0, "zinc": 0,
            "sodium": 0, "potassium": 0, "vitamin_c": 0,
        }
        details = []

        for code, grams in items:
            food = self._foods.get(code)
            if not food:
                continue
            factor = grams / 100 * (food.edible / 100)
            total["energy_kcal"] += food.energy_kcal * factor
            total["protein"] += food.protein * factor
            total["fat"] += food.fat * factor
            total["cho"] += food.cho * factor
            total["dietary_fiber"] += food.dietary_fiber * factor
            total["calcium"] += food.calcium * factor
            total["iron"] += food.iron * factor
            total["zinc"] += food.zinc * factor
            total["sodium"] += food.sodium * factor
            total["potassium"] += food.potassium * factor
            total["vitamin_c"] += food.vitamin_c * factor
            details.append({
                "name": food.food_name,
                "grams": grams,
                "energy_kcal": round(food.energy_kcal * factor, 0),
                "protein": round(food.protein * factor, 1),
            })

        return {
            "total": {k: round(v, 1) for k, v in total.items()},
            "items": details,
        }


# ============================================================
# 营养目标计算辅助
# ============================================================

def recommend_foods_for_goal(db: FoodDatabase, goal: str) -> dict:
    """根据目标推荐食物"""
    recommendations = {
        "减脂": {
            "explanation": "选择高蛋白密度、低GI、高纤维食物，增加饱腹感",
            "proteins": db.top_protein_density(min_protein=15, limit=10),
            "carbs": db.low_gi_foods(limit=10),
            "tips": [
                "每餐先吃蔬菜，增加膳食纤维摄入",
                "主食换为低GI的粗粮",
                "蛋白质每公斤体重摄入 1.6-2.2g",
            ],
        },
        "增肌": {
            "explanation": "需要充足蛋白质+碳水化合物，支持训练和肌肉生长",
            "proteins": db.search("牛肉 鸡胸 鸡蛋 鱼 虾", limit=15),
            "carbs": db.search("米饭 面条 燕麦 红薯 土豆", limit=10),
            "tips": [
                "训练后30分钟内补充快碳+优质蛋白",
                "每日蛋白质摄入 1.6-2.2g/kg体重",
                "保证热量盈余 300-500kcal/天",
            ],
        },
        "增重": {
            "explanation": "选择高热量密度食物，少量多餐",
            "foods": db.search("坚果 花生酱 牛油果 全脂奶 奶酪", limit=15),
            "tips": [
                "每日进食5-6餐",
                "可在餐间增加坚果/奶昔等高热量加餐",
                "训练以复合动作为主，刺激全身生长",
            ],
        },
    }
    return recommendations.get(goal, {})


# ============================================================
# 命令行工具
# ============================================================

if __name__ == "__main__":
    db = FoodDatabase()

    # 尝试从默认路径加载
    data_dir = "temp/china-food-temp/json_data_vision_251206_Qwen2-5-VL-72B-Instruct"
    if not os.path.exists(data_dir):
        data_dir = "../" + data_dir
    if not os.path.exists(data_dir):
        data_dir = "../../" + data_dir

    if os.path.exists(data_dir):
        db.load_food_data(data_dir)

        # 加载 GI 数据
        gi_path = "temp/china-food-temp/json_gi_of_foods/glycemic_index_of_foods.json"
        if not os.path.exists(gi_path):
            gi_path = "../" + gi_path
        if os.path.exists(gi_path):
            db.load_gi_data(gi_path)
    else:
        print("⚠️  未找到食物数据目录")
        print("请先从 https://github.com/Sanotsu/china-food-composition-data 下载数据")

    print(f"\n📊 数据库共 {db.count()} 种食物")
    print(f"📂 分类: {', '.join(db.list_categories())}")

    # 示例搜索
    print("\n" + "=" * 60)
    print("🔍 搜索: 鸡胸肉")
    for f in db.search("鸡胸"):
        print(f"  • {f.macro_summary()}")

    print("\n🔍 搜索: 鸡蛋")
    for f in db.search("鸡蛋"):
        print(f"  • {f.macro_summary()}")

    print("\n" + "=" * 60)
    print("🏆 高蛋白密度食物 (减脂友好) Top 10:")
    for f in db.top_protein_density(min_protein=10, limit=10):
        pd = f.protein_density()
        gi_str = f" GI={f.gi}" if f.gi else ""
        print(f"  • {f.food_name}: {f.protein:.1f}g蛋白/100g, "
              f"{f.energy_kcal:.0f}kcal, 密度={pd:.1f}g/100kcal{gi_str}")
