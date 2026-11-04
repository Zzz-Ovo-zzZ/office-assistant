---
name: interior-design
description: >
  室内软装设计与效果图生成。当用户上传房间照片/户型图、要装修设计、软装搭配、
  家具选购、房间改造、看室内效果图时使用。覆盖书房/卧室/餐厅/客厅等空间的
  色彩、灯光、空间规划、风格搭配与家具尺寸，可调用硅基流动 API 生成照片级效果图。
  触发词：装修设计、软装、家具搭配、房间设计、效果图、户型、改造、布置。
---

# 室内软装设计

为用户的房间做整体软装设计：读图分析 → 定方案 → 生成效果图 → 输出家具购物清单。

## 能力与边界（先诚实）

- ✅ **读图**：用 Read 工具读房间照片/户型图，识别尺寸、门窗、硬装、现有家具。
- ✅ **程序化设计图**：SVG/HTML 平面布局图、配色卡（精确、可打印）。
- ✅ **照片级效果图**：调用 `scripts/render.py`（硅基流动 API），需用户已配置 API key。
- ❌ 无内置图像模型，效果图必须走 API；无 key 时引导用户去 cloud.siliconflow.cn 免费注册。

## 知识库（先读，再设计）

设计前按需读 `knowledge/interior/` 下的参考文件：
- `design-guide.md` —— 执行流程、房间分析 12 项、失败模式、质量验收门
- `color-science.md` —— 色彩（孟塞尔 + 60-30-10 + 光色交互）
- `lighting-design.md` —— 灯光（照度 + 四层布光 + 色温）
- `space-planning.md` —— 空间（动线 + 家具间隙 + 人体工学）
- `style-guide.md` —— 风格（现代简约/原木/奶油/北欧/轻奢/中古）
- `furniture-spec.md` —— 中国家具国标尺寸 + 板材材质
- `shopping-guide.md` —— 家具软装选购避坑

## 执行流程

```
STEP 1 读图：Read 房间照片 → 输出「房间分析 12 项」（见 design-guide.md）
STEP 2 对齐：问清风格/预算/功能（若用户未说明），套用风格决策树
STEP 3 方案：定配色 + 家具布局 + 灯光（引用知识库数值标准）
STEP 4 可视化：render.py 生成效果图 + 输出平面布局图/配色卡
STEP 5 交付：过「质量验收门」，输出家具清单（含尺寸/材质/选购建议）
```

## 生图脚本用法

```bash
# 文生图
python .claude/skills/interior-design/scripts/render.py text2img \
  --prompt "现代简约主卧，暖白墙面，1.8米原木床..." --model flux-dev

# 图生图（推荐：上传现场照，保留结构换风格/加家具）
python .claude/skills/interior-design/scripts/render.py img2img \
  --image <现场照路径> \
  --prompt "保持房间原有地板/门窗/硬装不变，加入..." --model flux-dev

# 列模型
python .claude/skills/interior-design/scripts/render.py models
```

图生图后，用 Read 读回生成的图，检查是否符合预期，再迭代 prompt。

## Prompt 写作规则（生图关键）

公式：`房间现状 + 设计意图 + 具体家具(材质/颜色/尺寸) + 风格 + 拍摄质量`

要求：
- 明确保留的固定元素（地板/门窗/硬装）
- 具体到每件家具的材质、颜色、尺寸（如「1.8 米原木色橡木床，白色亚麻床品」）
- 指定风格 + 采光 + 拍摄角度
- ≥80 词；禁止「nice/lovely/cozy」这类空泛词

## 失败模式（设计前自查，详见 design-guide.md）

1. 盲目跟风硬套风格 2. 单一顶灯 3. 家具尺寸失配 4. 颜色不试 5. 全套同款

## 交付前质量门

- 主通道 ≥900mm，家具间隙符合 space-planning.md
- 灯光至少 2 层（卧室/书房/餐厅各自优先级见 design-guide.md）
- 60-30-10 配色已应用
- 家具尺寸符合国标 + 房间实测
- 输出购物清单按「刚需大件 → 收纳 → 灯光 → 软装」排序
