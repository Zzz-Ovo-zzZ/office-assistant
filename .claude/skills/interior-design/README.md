# 室内软装设计 Skill

上传房间照片，获得整体软装设计方案 + 照片级室内效果图 + 家具购物清单。

## 能力

- **读图分析**：识别房间尺寸、门窗、硬装、现有家具，输出 12 项分析。
- **专业设计**：色彩（孟塞尔 + 60-30-10）、灯光（四层布光 + 色温）、空间（动线 + 家具间隙）、风格（6 大风格 DNA）、中国家具国标尺寸 + 板材材质。
- **效果图生成**：调用硅基流动 API（FLUX 模型）生成照片级效果图，支持文生图 + 图生图（现场照换风格/加家具）。

## 安装

1. 安装依赖：

```bash
pip install requests
```

2. 配置 API key（免费注册 [cloud.siliconflow.cn](https://cloud.siliconflow.cn) 获取）：

```bash
cp .env.example .env
# 编辑 .env，把 sk-你的key 换成真实 key
```

## 使用

在对话中直接说「帮我设计这个房间」，并上传房间照片；或手动调用生图脚本：

```bash
python .claude/skills/interior-design/scripts/render.py text2img --prompt "..." --model flux-dev
python .claude/skills/interior-design/scripts/render.py img2img --image 房间.jpg --prompt "..." --model flux-dev
```

生成的效果图保存在 `output/interior/renderings/`。

## 目录结构

```
interior-design/
├── SKILL.md               # 设计方法论（Claude 读取）
├── scripts/render.py      # 硅基流动生图脚本
├── .env.example           # API key 模板
└── README.md              # 本文件
```

配套知识库：`knowledge/interior/`（色彩/灯光/空间/风格/家具尺寸/选购）。
