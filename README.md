# AI Drama Skills — MiniMax H3 & AVS RefMod

> **必装依赖：ComfyUI-MiniMaxH3Mod。** 本仓库的 AVS 人物库／Identity RefMod／Clothing RefMod 工作流程依赖该插件；仅安装 AVS 或导入 JSON，不能完成这条人物参考准备与视频绑定链路。请先按下方“必装：下载与安装 ComfyUI-MiniMaxH3Mod”安装，再使用工作流。单独使用 Skills 编写文本不需要运行该插件。

> **2026-10-19 工作流交付更新：** 已加入人物库优先复用与缺图提示词规则。Python 插件源码位于 [`integrations/ComfyUI-AI-Video-Studio`](integrations/ComfyUI-AI-Video-Studio)，安装顺序、空工作流与首次5秒测试见 [WORKFLOW_SETUP.md](WORKFLOW_SETUP.md)，模型清单见 [MODEL_REQUIREMENTS.md](MODEL_REQUIREMENTS.md)。五个 Skills 的原目录结构、H3 FULL 14 栏与一采/二采逻辑保持不变。此包不包含模型权重和个人素材，也未完成8GB视频生成验收。

> **中文 / English · V5.1.10 · 5 个独立 Skills · 整体一键 + 分步制作**
>
> 从小说、剧本到可导入 AI-Video-Studio 的 AI 短剧分镜、中文 H3 FULL 提示词与英文 H3 FULL 提示词。支持 MiniMax H3 的 REF2VA 工作方式，以及 AI-Video-Studio 的 **Identity RefMod / Clothing RefMod** 人物绑定方案。

**项目定位：** 这是一套供 Codex 等支持 `SKILL.md` 的智能助手调用的**制作规则、模板与生产工具**，不是 MiniMax H3 模型本体，也不是安装后自动生成视频的 ComfyUI 节点。提示词由 Skills 生成；图片与 RefMod 由用户在 AI-Video-Studio 中准备、选择并运行。

## 目录 / Contents

- [新增：Python 插件、工作流安装与使用](#新增python-插件工作流安装与使用)
- [01. 这套 Skills 能做什么](#01-这套-skills-能做什么)
- [02. 五个 Skill：00–04](#02-五个-skill0004)
- [03. 安装到 Codex](#03-安装到-codex)
- [04. 五套直接复制的调用提示词](#04-五套直接复制的调用提示词)
- [05. 实际生产流程](#05-实际生产流程)
- [06. RefMod / Picture 绑定规范](#06-refmod--picture-绑定规范)
- [07. H3 FULL 14 栏固定格式](#07-h3-full-14-栏固定格式)
- [08. 一段完整的中文 H3 示例](#08-一段完整的中文-h3-示例)
- [09. 英文版转换示例与语言规则](#09-英文版转换示例与语言规则)
- [10. 人物、造型与场景图片提示词示例](#10-人物造型与场景图片提示词示例)
- [11. 整体版 GUI / CLI 使用](#11-整体版-gui--cli-使用)
- [12. 输出清单和交付标准](#12-输出清单和交付标准)
- [13. 常见问题与故障排查](#13-常见问题与故障排查)
- [14. 限制、版本与声明](#14-限制版本与声明)

---

## 新增：Python 插件、工作流安装与使用

本仓库现在同时提供 **五个 Skills + AVS Python 插件和网页前端 + ComfyUI 工作流**。Skills 负责剧情、分镜、图片提示词与 H3 文本；AVS 负责素材绑定、人物参考准备和视频调度；ComfyUI/H3 执行视频生成。实际图片生成工具仍需自行选择，本包没有新增自动生图服务。

### 仓库里新增了什么

```text
ai-drama-skills-avs-refmod/
├── 00_整体一键版/ … 04_一句话快速单段/    # 保持原来的五个同级 Skills
├── integrations/
│   └── ComfyUI-AI-Video-Studio/
│       ├── __init__.py、nodes.py、director.py 等 Python 文件
│       ├── character_library.py、character_store.py、wardrobe_store.py
│       ├── web/                            # 必需的网页界面，不能漏复制
│       ├── requirements.txt
│       └── example_workflows/
│           ├── AI_Video_Studio_480P一采_960P潜空间二采_双节点.json
│           └── AVS_480P_960P_EMPTY.json
├── WORKFLOW_SETUP.md                       # 完整安装、迁移及首次测试说明
└── MODEL_REQUIREMENTS.md                   # 模型文件名、分类与来源
```

### 分别放到什么文件夹

| 内容 | 从哪里取 | 放到哪里 |
| --- | --- | --- |
| 五个 Skills | 根目录的 00–04 五个完整文件夹 | 技能宿主支持的 Skills 目录，例如项目中的 `.agents/skills/`；具体见第03节 |
| AVS Python 插件 | `integrations/ComfyUI-AI-Video-Studio/` 整个目录 | `ComfyUI/custom_nodes/ComfyUI-AI-Video-Studio/`，确保此目录直接包含 `__init__.py` 与 `web/` |
| RefMod 依赖插件 | [ComfyUI-MiniMaxH3Mod](https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod) | `ComfyUI/custom_nodes/ComfyUI-MiniMaxH3Mod/`，与 AVS 插件并列 |
| 工作流 JSON | AVS 插件的 `example_workflows/` | 可直接拖进 ComfyUI 画布打开；也可复制到 `ComfyUI/user/default/workflows/` 后从工作流列表打开。使用其他用户配置时放在对应用户的 workflows 目录 |
| 模型权重 | 已有模型或模型来源 | 按 [模型清单](MODEL_REQUIREMENTS.md) 放入 `diffusion_models`、`text_encoders`、`vae`、`loras` 等模型分类目录；已有共享路径可继续复用 |
| 人物和服装图片 | 自己确认好的素材 | 在 AVS 人物库/造型库界面上传和绑定，无需放进插件源码目录 |

本机仓库位置为 `E:\github\ai-drama-skills-avs-refmod`；它是源码目录，不能代替 ComfyUI 的插件安装目录。本机 ComfyUI 根目录为 `E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI`，因此插件目标位置为该目录下的 `custom_nodes\ComfyUI-AI-Video-Studio`。其他电脑使用自己的 ComfyUI 根目录。

安装时保留整个 AVS 插件目录，不能只复制几个 `.py`。已有插件先备份，再更新同名目录，避免两个目录重复加载相同节点。使用**运行 ComfyUI 的那个 Python**安装两个插件各自的 `requirements.txt`，然后重启 ComfyUI；示意命令如下，尖括号内容需替换为实际路径：

```text
"<ComfyUI Python路径>" -m pip install -r "<ComfyUI根目录>/custom_nodes/ComfyUI-AI-Video-Studio/requirements.txt"
"<ComfyUI Python路径>" -m pip install -r "<ComfyUI根目录>/custom_nodes/ComfyUI-MiniMaxH3Mod/requirements.txt"
```

已有可运行环境无需重复安装模型或更换 Python。新电脑还需支持 H3 的 ComfyUI、匹配的 PyTorch/CUDA 环境及 FFmpeg/ffprobe；本仓库不是包含这些环境的整机安装包。

### 必装：下载与安装 ComfyUI-MiniMaxH3Mod

AVS 已接入该插件的功能，**不代表 AVS 源码自带或会自动安装它**。工作流图上即使没有单独显示 RefMod 节点，人物库准备参考和视频绑定仍会在内部调用它。

**下载方式（三选一，不要重复安装）：**

1. **与本次交付配套的源码：** 使用网盘完整包中的 `03_RefMod依赖源码/ComfyUI-MiniMaxH3Mod/`，或下载 [本机所用提交的 ZIP](https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod/archive/f9462081e28794389b5a6c5067eb327412ad8ee7.zip)。该版本用于复现本次依赖快照，不代表已经完成8GB成片验收。
2. **上游下载：** 打开 [ComfyUI-MiniMaxH3Mod 作者仓库](https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod)，点击 **Code → Download ZIP**。上游节点接口仍在变化，最新版需重新检查兼容性。
3. **Git 安装：** 在 `ComfyUI/custom_nodes/` 目录打开终端，执行：

   ```text
   git clone https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod.git
   ```

ZIP 解压后，将外层目录命名为 `ComfyUI-MiniMaxH3Mod` 并放入 `custom_nodes`。最终应为：

```text
ComfyUI/
└── custom_nodes/
    ├── ComfyUI-AI-Video-Studio/
    │   └── __init__.py
    └── ComfyUI-MiniMaxH3Mod/
        ├── __init__.py
        ├── nodes.py
        ├── requirements.txt
        └── 其他原始源码文件与目录
```

不要多嵌套一层 `ComfyUI-MiniMaxH3Mod-main/ComfyUI-MiniMaxH3Mod/`，也不要只复制 `nodes.py`。在**运行 ComfyUI 的 Python 环境**安装依赖，然后完全重启 ComfyUI；PowerShell 示例（替换路径）：

```powershell
& "<ComfyUI Python路径>" -m pip install -r "<ComfyUI根目录>/custom_nodes/ComfyUI-MiniMaxH3Mod/requirements.txt"
```

**如何确认装好了：**

- 启动日志中该插件没有 `IMPORT FAILED` 或缺依赖错误。
- ComfyUI 节点搜索能找到 `Create H3 RefMod` 等该插件节点；AVS 实际要求注册 `MiniMaxH3RefModExtract`、`MiniMaxH3RefModBundleSave`、`MiniMaxH3RefModsLoader`、`MiniMaxH3RefModApply` 四个内部节点类型。
- 在 AVS 人物库选择真实图片和 H3 视频 VAE，执行“保存并准备人物参考”，队列完成后人物参考可用。仅看到节点不等于这一步已通过。

如果出现“请先安装并启用 ComfyUI-MiniMaxH3Mod，再重启 ComfyUI”，先检查目录层级、Python 环境、依赖安装和重启是否完成。若用了不同版本，检查上述四个节点类型是否仍存在。插件代码不包含 H3 模型，视频 VAE 等权重仍按 [模型清单](MODEL_REQUIREMENTS.md) 配置。

### 下载和打开工作流

- **用户提供的原始双节点工作流：** [AI_Video_Studio_480P一采_960P潜空间二采_双节点.json](integrations/ComfyUI-AI-Video-Studio/example_workflows/AI_Video_Studio_480P一采_960P潜空间二采_双节点.json)。本仓库原样收录，不改变节点连接和采样设置。GitHub 中打开文件后使用下载原始文件按钮保存 `.json`，再拖入 ComfyUI。
- **新项目空白模板：** [AVS_480P_960P_EMPTY.json](integrations/ComfyUI-AI-Video-Studio/example_workflows/AVS_480P_960P_EMPTY.json)。没有个人测试段和人物绑定，供重新导入 Skills 产出的 H3 使用。

两份文件是不同快照：本次提供的原始 JSON 含三个节点（一采模型、二采配置、导演工作台），一采为8步且未启用匹配Turbo参数；先前空白模板另含4步Turbo LoRA节点。不要把它们当成完全相同参数的“有内容/无内容”版本，应按所选文件检查模型与 LoRA。

**原始 JSON 的首次使用检查：**

1. 它包含两个测试段、旧演员 ID 和 E 盘本地图片路径，这些引用不是随文件附带的图片。其他电脑必须重新选择人物、造型和素材；即使是同一台电脑，也要确认旧记录仍存在。
2. 默认生成范围为“时间轴局部重绘”。首次生成新视频时切换为“当前视频段”，不能在没有视频结果时直接按旧的局部重绘设置运行。
3. 其中旧测试提示词使用人物 `<Picture 1>`，不是当前 Skills 的 AVS_REFMOD 正式示例。制作新剧时用 Skills 生成的 FULL 14 栏替换测试内容，重新选择已准备的演员与造型，并清除旧的人脸 Picture 绑定；场景、道具和关键帧按实际需要绑定 Picture。
4. 配置名称中保留“5090”，这不是对4060 Ti 8GB的适配证明。根据实际可用模型核对一采、文本编码器、视频/音频VAE和二采模型，先做单段测试。

### 从 Skills 到视频怎么用

1. **规划：** 整集使用00；分步使用01→02→03；首次短片测试使用04。提供真实人物、造型和场景素材位置，已有演员优先复用。
2. **补图：** 按 Skills 的缺项提示词在选定的生图工具补图。正脸确认后再派生角度和表情；新服装优先用无头正背面参考。Skills 写了提示词并不表示图片已经生成。
3. **人物参考：** 在 AVS 人物库上传正脸，按需补角度和表情；在造型区上传服装图。保存资料并执行“保存并准备人物参考”，等待 ComfyUI 队列完成，再核对可用状态。
4. **导入文本：** 把 Skills 产出的中文或英文 H3 一键文件导入导演工作台，检查每段时长、场景、演员和当前造型。人物身份与服装由 RefMod 提供，不再额外占用人物 Picture。
5. **一采：** 先选择一个5秒单人段，用“当前视频段”运行，检查脸、服装、动作和声音。一采保留 latent，供后续二采使用。
6. **二采：** 一采满意且 latent 可用后，核对 latent 放大模型与二采配置，再选择“二采当前视频段”。二采依赖一采结果，并非从空时间线直接生成960P；显存不足时不要直接扩展到整集。
7. **整集：** 单人通过后依次测试双人、换装、连续镜头，再批量生成与合成最终视频。

当前交付只完成文件/语法与工作流节点检查，没有进行 GPU 生成或8GB性能验收。更完整的安装与私人素材迁移说明见 [WORKFLOW_SETUP.md](WORKFLOW_SETUP.md)。

---

## 01. 这套 Skills 能做什么

| 能力 | 说明 |
| --- | --- |
| 小说 / 剧本改编 | 识别人物关系、核心事件、场景、道具、对白，把故事转换成可拍的镜头任务 |
| 分镜设计 | 默认每段不超过 5 秒，明确景别、机位、运动、站位、轴线、动作、对白和末态 |
| 中文 H3 | 从确认分镜生成完整 **FULL 14 栏** 中文一键导入提示词 |
| 英文 H3 | 同源转换英文镜头描述，保持中文对白、Picture、时间轴、人物及状态不变 |
| RefMod 适配 | 人物身份、服装与场景的视觉参考分工明确，人物/服装不额外占用 Picture |
| 连续性 | 包括 Hidden LOCK、人物左右/深度、门与道具状态、镜头轴线、上一段尾部 22 帧等 |
| 一句话测试 | 单句动作描述生成**一个**可复制的 ≤5 秒 H3 段，而不是重做整个项目 |
| 交付与检查 | 整体版本包含生产图、示例、验证工具及可交付文件组织规则 |

**两种生产方式：**

```text
方式 A：小说 / 剧本 ──→ 00 整体一键 ──→ 完整生产包

方式 B：小说 / 剧本 ──→ 01 只做分镜 ──→ 02 只做中文 H3 ──→ 03 只做英文 H3

快速测试：一句话 / 单镜头要求 ──→ 04 一句话快速单段 ──→ 单段 H3
```

### 生产硬规则

- 正式视频段默认 **≤5 秒**；若对白或动作塞不下，先拆段，不强行压缩。
- **近景优先**；远景和中景用于建立空间，摄影机运动不能被误当成角色走位。
- 固定人物左/右、前/后、朝向、视线、屏幕运动方向与 180° 轴线。
- 动作要有开始、过程、结束；接触类动作要有物理连续性，避免跳步和瞬移。
- 对白按真实时间分配，原台词不擅自增加，必须在本段结束前说完。
- **禁止自动加背景音乐**：`non_diegetic_music: N/A`；需要时只保留真实剧情音效。
- 短剧里的**多表情变化**通过 `shot_timeline` 文字分时描述；不假定一段生成中可以按秒切换 RefMod。
- 不编造用户未提供的图片 ID、素材文件、实际生成结果或视频质检结论。

---

## 02. 五个 Skill：00–04

本仓库的五个入口**必须是同一级文件夹**，没有额外的“模块化Skills”中间层：

```text
ai-drama-skills-avs-refmod/
├── README.md                         # 你正在看的 GitHub 完整说明
├── 00_整体一键版/
│   ├── SKILL.md
│   ├── one_click.py
│   ├── workbench.py
│   ├── pipeline_graph.json
│   ├── requirements.txt
│   ├── 00_router/ ... 12_single_segment/   # 既有完整生产链内部资源
│   ├── engine/  schemas/  scripts/ ...      # 引擎/校验/示例
│   └── ...
├── 01_只做分镜/
│   ├── SKILL.md
│   ├── references/
│   └── examples/
├── 02_只做中文H3/
│   ├── SKILL.md
│   ├── references/
│   └── examples/H3_PROMPTS_FULL_CN.md
├── 03_只做英文H3/
│   ├── SKILL.md
│   ├── references/
│   └── examples/H3_PROMPTS_FULL_EN.md
└── 04_一句话快速单段/
    ├── SKILL.md
    ├── references/
    └── ...
```

> `...` 表示该 Skill 自己随包提供的其他文件，而不是需要用户自己创建的新目录。**请保留整个 Skill 文件夹，不要只上传/复制 SKILL.md。**

| 入口 | SKILL.md 里的实际 `name` | 需要的输入 | 用户最终得到什么 |
| --- | --- | --- | --- |
| `00_整体一键版` | `ai-drama-full-pipeline` | 小说、剧本、完整项目需求 | 分镜、资产规划、中文/英文 H3 和整体交付资料 |
| `01_只做分镜` | `ai-drama-storyboard-standalone` | 小说、剧本、剧情 | **只**得到详细分镜，不生成 H3 |
| `02_只做中文H3` | `ai-drama-h3-cn-standalone` | 已确认分镜 | **只**得到中文 FULL 14 栏 H3 |
| `03_只做英文H3` | `ai-drama-h3-en-standalone` | 已有中文 H3 FULL | **只**得到英文 FULL 14 栏 H3 |
| `04_一句话快速单段` | `ai-drama-one-line-h3-standalone` | 一句话、单镜要求 | **一个** ≤5 秒的 FULL 14 栏 H3 |

**优先级：** 需要全部就调用 **00**；用户明确说“只做某一步”，应调用 **01/02/03/04**。01–04 都含各自必需的 `references/` / `examples/`，不是依赖 00 在线转接的薄壳。

---

## 03. 安装到 Codex

### 方式 A：项目级（推荐给 GitHub 协作）

将 5 个文件夹**原样复制**到当前仓库内的 `.agents/skills/`：

```text
你的项目/
└── .agents/
    └── skills/
        ├── 00_整体一键版/SKILL.md
        ├── 01_只做分镜/SKILL.md
        ├── 02_只做中文H3/SKILL.md
        ├── 03_只做英文H3/SKILL.md
        └── 04_一句话快速单段/SKILL.md
```

这种放法只对当前项目可用，适合想让团队一起维护 Skill 版本的情况。

### 方式 B：个人级（推荐给自己长期用）

**Windows**：在资源管理器地址栏输入：

```text
%USERPROFILE%\.agents\skills
```

**Linux / macOS**：

```bash
mkdir -p ~/.agents/skills
```

把五个技能文件夹放进去即可。不同 Codex 版本或宿主的技能发现路径可能有差异，应以当前宿主的 Skills 设置为准。

### 验证是否识别成功

1. 重新打开 Codex 会话，或按宿主支持的方式刷新 Skill 列表。
2. 在支持显式技能选择的界面中选择 Skill；某些 Codex 输入框可以用 `$` 搜索技能。
3. 测试：`使用 ai-drama-storyboard-standalone，只生成 2 个五秒分镜，不生成 H3 提示词。`
4. 若未识别，检查 `SKILL.md` 是否真的在每个技能目录**直接下一层**，以及 `name:` 和 YAML 头是否完整。

**不要**把这五个 `SKILL.md` 合并成一个文件；也不要把五个目录再嵌在 `模块化Skills/` 下面后期待所有宿主自动递归扫描。

---

## 04. 五套直接复制的调用提示词

以下是**发给 Codex / 智能助手的使用指令**，不是要求用户手写 H3 正文。`$` 显式技能调用是否可用依赖宿主；若界面没有技能选择器，用准确的 `name` 指定 Skill 即可。

### 00：小说 → 一键完整生产包

```text
使用 ai-drama-full-pipeline Skill。

我将提供小说/剧本全文及已有的人物、场景、道具素材。
请依据原文一次性完成完整 AI 短剧生产链：
1. 剧情改编与人物、场景、道具资产规划；
2. 完整分镜，每段默认不超过5秒；
3. 中文 H3 REF2VA FULL 14栏提示词；
4. 同源英文 H3 FULL 14栏提示词；
5. 人物站位、门/道具状态、空间锁、AddGuide连续性、对白容量检查；
6. 交付适合 AI-Video-Studio 导入的中文/英文一键 MD 文件。

项目模式：character_binding_mode=AVS_REFMOD。
身份由 Identity RefMod 控制；每段造型由 Clothing RefMod 控制。
人物和服装不得占用 Picture，Picture 仅用于场景、道具、Keyframe等。
禁止人物身份图、服装展示板作为画面背景或额外人物。
对白原文保留；英文Prompt也要用普通话逐字说中文对白。
禁止配乐：non_diegetic_music: N/A。
不要省略段落，不要只给大纲；在可用信息范围内直接交付完整最终版。
无法确认的资产路径/图片/实际验证结果必须明确标记，不要编造。
```

**输入示例：** 上传 `novel.txt`、`chapter01.docx` 等小说文件，并提供资产文件夹（如果已经有资产）。完整一键产出具体取决于实际文件、规划模型接入以及验证环境；**不能把只有 Prompt 的结果冒充已生成的视频**。

### 01：只做分镜（不输出 H3）

```text
使用 ai-drama-storyboard-standalone Skill。

请把我提供的小说或剧本拆成完整的 AI 短剧分镜。
只输出详细分镜，不生成中文H3、不生成英文H3。
每段不超过5秒，明确：
- Scene/地点/时间
- 人物与当前造型
- 景别、机位、运镜、轴线
- 站位的左右/前后/朝向/距离
- 动作0.0-5.0秒分配、眼神和表情
- 对白原文、说话人、音效
- 门/道具holder/段末状态/下一段继承
近景优先，禁止越轴、瞬移、场景乱跳。
人物通过RefMod绑定，不规划人物Picture。
一次性给全部分镜，不要问我是否继续下一段。
```

### 02：已确认分镜 → 中文 FULL 14 栏 H3

```text
使用 ai-drama-h3-cn-standalone Skill。

下面是已经确认的分镜，严格以它为准，不要自行改变剧情、人物、镜头或对白。
请为全部视频段逐段生成中文版 H3 REF2VA FULL 14栏提示词。
必须包含subject_definitions、summary、retention_analysis、spatial_state、
continuity_state、physical_continuity_locks、camera_plan、shot_timeline、
detailed_description、dialogue_and_audio、overall_soundscape、
non_diegetic_music、reference_map、negative_rules。

character_binding_mode=AVS_REFMOD；Identity RefMod=身份，Clothing RefMod=本段造型。
人物、服装不占Picture；场景MASTER、局部场景、道具等可以占Picture。
完整展开每段的入态、末态、轴线、站位和动作，不能写“同上”。
不添加原文不存在的对白；non_diegetic_music: N/A。
输出可直接复制到 AI-Video-Studio 的完整中文一键导入 MD。
```

### 03：中文 FULL 14 栏 → 英文 FULL 14 栏

```text
使用 ai-drama-h3-en-standalone Skill。

将我提供的中文 H3 FULL 14栏提示词逐段翻译为英文版。
这是同源转换，不要二次创作。
保持原有SEG/LOCK、人物、时间轴、站位、动作、Picture编号、
RefMod职责、道具holder、门状态、上一段尾22帧及其他连续性信息不变。
中文对白保留中文原文，并明确 spoken in Mandarin Chinese exactly as written。
英文输出仍保留中文导入段头及FULL14栏字段名。
禁止增删任何镜头或对白；禁止背景音乐。
直接输出完整英文一键导入 MD。
```

### 04：一句话 → 一个单段（最多 5 秒）

```text
使用 ai-drama-one-line-h3-standalone Skill。

把下面一句话变成一个完整的5秒 H3 REF2VA 视频段。
剧情：顾言川穿黑西装站在1602客厅，听到门铃后先轻微惊讶，
随后收住表情，转头看向唯一的入户门。

输出中文版FULL14栏提示词，包含0.0—5.0秒完整动作时间轴、
景别/机位/人物站位、空间锁、段末状态、音效与negative_rules。
使用AVS_REFMOD，身份=顾言川，当前造型=黑西装；人物和服装不占Picture。
如果没有提供实际场景文件名，不要杜撰Picture文件。
人物只有一位，不复制人物，不生成巨型人脸背景或服装展示板。
禁止背景音乐；没有授权对白就写N/A。
只生成这一段，不运行整集流程。
```

**更多一句话题材：**

```text
使用 ai-drama-one-line-h3-standalone：
“女主从画面左侧突入拔剑，男主回身格挡，两剑第一次硬碰，5秒，
高速但动作可读，不越轴，剑光和碰撞音效，无配乐。”
```

```text
使用 ai-drama-one-line-h3-standalone：
“雨夜的1602门外，女主站在门口，男主从屋里缓慢拉开门，
两人第一次对视，5秒，只保留门轴、门牌、雨声，不新增对白。”
```

### 修改已生成的某一段（不重跑全部）

```text
使用 ai-drama-one-line-h3-standalone Skill。
这是现有 SEG012 的单段修改，不要重做其他段，也不要改变男女主身份和场景。
保留我贴出的SEG012的入态、人物站位、门状态、道具holder、
前后续写关系及所有原对白，只调整我指出的问题：
【把第2.0—3.0秒的动作改为男主先回头、再抬剑，不允许瞬移】。
输出这一个SEG的完整中文FULL14栏。
```

> 对复杂的已有 SEG 返修，请同时提供该段原文与相邻段状态。若需要自动继承整项目依赖，可由整体工程的单段模块处理；04 的一句话入口不会凭空知道未上传的上下文。

---

## 05. 实际生产流程

### 流程 A：整体一键

```text
Step 1  上传小说/剧本 + 已有资产（可选）
Step 2  调用 00_整体一键版
Step 3  检查输出的角色/场景/道具与分镜（尤其故事事实和对白）
Step 4  取得完整中文 + 英文 H3 FULL 14栏一键导入文件
Step 5  在 AI-Video-Studio 中准备人物Identity RefMod与Clothing RefMod
Step 6  根据 Picture绑定上传场景/道具素材、为镜头选人物和造型
Step 7  一采生成 → 检查人物/动作/空间 → 必要时二采高清
```

### 流程 B：逐步控制

```text
小说 → 01（先看分镜）→ 修改/确认分镜 → 02（中文H3）
    → 03（英文H3）→ Studio绑定 → 生成视频
```

### 流程 C：最小化测试

```text
一句话 → 04（一个5秒的FULL提示词）→ Studio选人物/造型 → 一采测试
```

建议先以一个5秒镜头确认“人物是否正确 + 衣服是否正确 + 背景有没有错误复刻头像/衣服展示板”，再批量生成；生成式模型的时间、表情、构图控制不保证每个 Seed 都完全一致。

---

## 06. RefMod / Picture 绑定规范

**当前项目的核心原则：**

```text
人物身份参考图（正脸/角度）
    └─ Identity RefMod ──┐
                         ├─→ 一段H3视频
当前选定造型（无头服装正面/背面）  │
    └─ Clothing RefMod ──┤
                         │
场景MASTER / 局部场景 / 道具  │
    └─ Picture 1..9 ─────┘
```

| 资产 | 用途 | 是否自动占人物 Picture 槽 |
| --- | --- | --- |
| 人物高清正脸、角度图 | Identity RefMod：脸、身份、发型、年龄感 | **否** |
| 无头服装、造型图 | Clothing RefMod：当前衣服、鞋、材质和配饰 | **否** |
| 场景 MASTER、局部场景 | Picture：空间几何与场景外观 | 可占 Picture |
| 道具图 / Keyframe | Picture：相应道具和构图 | 可占 Picture |

### 正确的 Subject 写法

```text
subject_definitions:
<Subject 1> 是顾言川。
人物身份、脸部、发型、年龄感由 AI-Video-Studio Identity RefMod 控制；
当前穿着由本镜头选择的 Clothing RefMod 控制。
character_picture=NONE。
人物正脸、四视图、无头服装板不作为本镜头的 Picture 条目。
```

### 正确的 Picture 绑定

```text
【Picture绑定】
P1=SCN_1602_LIVING_MASTER.png；P2=PROP_MOP.png
```

上述文件名仅是**示例**；只有用户真正上传了这些文件，才能生成可执行的绑定。`Picture 1` 只代表场景，`Picture 2` 只代表拖把，不代表男主或衣服。

### 不应该出现

```text
错误：P1=男主高清正脸，P2=无头西装正反面展示板
错误：Identity, face and current wardrobe are from <Picture 1>
错误：让角色参考中的大脸作为背景海报出现在视频里
```

### RefMod 的正确使用边界

- Identity/Clothing RefMod 是**视觉参考条件**，不保证模型一定只提取“身份”或只提取“衣服”；概念标签不是严格像素级属性隔离。
- 多张脸、服装正反面等参考图片需要真实准备为 RefMod；仅在 Prompt 写“已绑定”**不会自动创建权重文件**。
- Skills 不应该擅自猜测当前 Studio 人物库已经准备好的 RefMod 名称、路径或状态。
- 5秒多表情通过文本时间轴控制，不要假设中途自动切换 RefMod。
- 如果使用的是老工作流、老 Skills 的人物 Picture 绑定，请先核对项目 `character_binding_mode`，避免混用造成巨脸背景或衣服板构图泄漏。

---

## 07. H3 FULL 14 栏固定格式

**FULL 14 栏是本项目给 AI-Video-Studio 使用的固定输出合同**，不把它误称为所有 H3 环境都强制要求的唯一格式。02 / 03 / 04 和 00 的对外一键交付必须保留全部 14 栏，禁止仅输出 Runtime 精简版。

| # | 固定字段 | 内容 |
| --- | --- | --- |
| 01 | `subject_definitions` | 谁是人物、谁是场景、身份/造型由什么参考控制 |
| 02 | `summary` | 本段画面目的 |
| 03 | `retention_analysis` | 必须保持不变的身份、造型、道具与场景 |
| 04 | `spatial_state` | 左右/前后/朝向、建筑与镜头轴线 |
| 05 | `continuity_state` | 入态、当前态、末态、上一段/下一段关系 |
| 06 | `physical_continuity_locks` | 门状态、道具位置、左右手、动作结果等 |
| 07 | `camera_plan` | 景别、机位、镜头运动、焦距 |
| 08 | `shot_timeline` | 0–5秒逐段时间线 |
| 09 | `detailed_description` | 全段画面的完整可执行描述 |
| 10 | `dialogue_and_audio` | 说话者、中文原台词、音效时间 |
| 11 | `overall_soundscape` | 环境声、脚步、雨、风、接触音等 |
| 12 | `non_diegetic_music` | `N/A`，禁止自动配乐 |
| 13 | `reference_map` | RefMod 权威、Picture → Subject 映射 |
| 14 | `negative_rules` | 禁止复刻身份板、分屏、越轴、畸变等 |

### 每段完整结构（字段顺序不变）

```text
【视频片段 N｜5秒｜标题】
【集数】EP01
【Scene】SC01
【场景】场景名称
【H3模式】REF2VA
【连续性】独立生成 / 续写上一段
【续写来源】N/A / SEG001
【继承尾音】否 / 是
【生成模式】单张生成
【Picture绑定】仅真实已上传的场景/道具/Keyframe
【Speaker绑定】N/A 或真实声音资产

subject_definitions:

summary:

retention_analysis:

spatial_state:

continuity_state:

physical_continuity_locks:

camera_plan:

shot_timeline:

detailed_description:

dialogue_and_audio:

overall_soundscape:

non_diegetic_music:
N/A

reference_map:

negative_rules:
```

---

## 08. 一段完整的中文 H3 示例

下面是**说明用的演示片段**，展示结构、RefMod 与 Picture 分工，**不是已经在 GPU 跑过的视频**。场景图片名称需替换为真实上传的文件；没有上传场景素材时，应移除 `P1` 及相应 `<Picture 1>` 引用，不可虚构路径。

```text
【视频片段 SEG001｜5秒｜雨夜听到门铃】
【集数】EP01｜第一章
【Scene】SC01_LIVING
【场景】1602客厅｜周日夜晚
【H3模式】REF2VA
【连续性】独立生成
【续写来源】N/A
【继承尾音】否
【生成模式】单张生成
【Picture绑定】P1=SCN_1602_LIVING_MASTER.png（示例占位，须实际上传）
【Speaker绑定】N/A

subject_definitions:
<Subject 1> 是成年人顾言川。脸、发型、年龄感和人物身份由
AI-Video-Studio Identity RefMod 控制，character_picture=NONE。
当前衣服来自本段选择的 Clothing RefMod（黑色西装造型）。
不得将正脸、四宫格、服装板复制成背景、海报或其他人物。
<Subject 2> 是1602客厅。建筑结构、家具、门窗的位置
参照 <Picture 1>，但人物和服装不来自该 Picture。

summary:
男主在雨夜安静的客厅里听到门铃，微微一怔，转头看向入户门。

retention_analysis:
<Subject 1>: fully_preserved。维持原身份、脸、发型、体型；
服装完整继承本镜头所选 Clothing RefMod，无换装动作。
<Subject 2>: fully_preserved。客厅门窗、沙发与家具固定，不增设第二扇入户门。

spatial_state:
顾言川位于客厅偏左前景，站姿稳定，面向画面右侧的入户玄关。
唯一入户门位于客厅右后方，处于关闭状态。
相机位于客厅中部、门口方向的同一侧，不跨越已建立的动作轴线。

continuity_state:
incoming_state: 顾言川站立、双手自然下垂、衣服干燥；入户门关闭；无道具在手。
current_state: 0—3秒保持原地，仅眼神与头部微动；门铃在指定时间响起。
end_state: 顾言川转头注视入户门，仍在原站位；门仍关闭。
from_previous: N/A（独立生成）
to_next: 下一段可从转头注视入户门的姿势继续，按需要继承尾部22帧。

physical_continuity_locks:
只有一个顾言川，只有一扇入户门。门在本段始终关闭，
双手没有拿起道具；头部转动不代表人物走位。
不新增人物、不自动开门、不重复门铃事件。

camera_plan:
眼平机位，35—50mm等效视角，中近景固定镜头；
仅随头部运动做极轻微构图调整，不做强推、绕拍或越轴。

shot_timeline:
[Shot 1 | 0.0—1.5s] 男主平静站立、自然呼吸、视线略向下。
[Shot 1 | 1.5—2.2s] 门铃响起，男主眉眼短暂一怔，眼睛轻微睁大。
[Shot 1 | 2.2—4.2s] 惊讶消退，他在原地缓慢转头看向门口。
[Shot 1 | 4.2—5.0s] 目光停在门的位置，姿势稳定，保持可续写的结束帧。

detailed_description:
半写实都市短剧，雨夜室内暖灯与窗外冷雨形成轻微反差。
顾言川穿当前 Clothing RefMod 指定的黑色西装，始终只有一个人。
镜头以中近景展示脸部微表情；门铃响起后，他先眼神反应，
再转头看向固定位置的入户门。动作清晰、连贯，无瞬移，
不出现大幅面孔背景、服装展示板或双人分屏。

dialogue_and_audio:
对白：N/A。
1.5—2.2s：一次门铃事件；无旁白，无临时新增台词。

overall_soundscape:
雨声隔着窗户轻微传入；室内空调/房间底噪；一次门铃；自然呼吸。
不自动添加对白、乐器或背景配乐。

non_diegetic_music:
N/A

reference_map:
<Subject 1>：Identity RefMod=顾言川；Clothing RefMod=本段所选黑色西装；
character_picture=NONE；不占Picture槽。
Picture 1：SCN_1602_LIVING_MASTER.png → <Subject 2>（实际上传后生效）。

negative_rules:
禁止复制高清正脸成为背景巨脸、海报或额外人物。
禁止复刻服装参考板为双人正反展示；禁止人物身份或服装占Picture。
禁止新增门、门自动打开、角色瞬移、站位交换、越轴。
禁止额外对白、字幕、水印、畸形四肢、最后一秒突变。
禁止背景音乐。
```

> 这个示例展示**完整字段**，但实际故事应由 Skills 基于用户小说、分镜和已上传资产自动生成，而不是要求用户把示例一段段手工修改。

### 真实的完整样例文件

- [中文 H3 FULL 示例](02_只做中文H3/examples/H3_PROMPTS_FULL_CN.md)
- [英文 H3 FULL 示例](03_只做英文H3/examples/H3_PROMPTS_FULL_EN.md)
- [分镜样例](01_只做分镜/examples/05_storyboard.json)

以上是包内已有的参考资料。样例中的人物、Scene、Picture 名称属于样例数据，不代表使用者已经拥有这些资产。

---

## 09. 英文版转换示例与语言规则

`03_只做英文H3` 要保留段头、14栏字段名和所有绑定关系，只翻译自然语言描述：

```text
subject_definitions:
<Subject 1> is Gu Yanchuan, an adult man. Facial identity, hairstyle,
apparent age, and body identity are controlled by the AI-Video-Studio
Identity RefMod. His wardrobe is controlled by the Clothing RefMod
selected for this shot. character_picture=NONE.
Do not reproduce reference portraits or clothing display sheets as
backgrounds, posters, split-screens, or extra people.

shot_timeline:
[Shot 1 | 0.0-1.5s] He stands calmly and breathes naturally.
[Shot 1 | 1.5-2.2s] A doorbell rings; his eyes widen briefly.
[Shot 1 | 2.2-5.0s] He turns toward the door and settles into a stable pose.

non_diegetic_music:
N/A
```

**中文对白保留原字句：**

```text
dialogue_and_audio:
Gu Yanchuan speaks in Mandarin Chinese exactly as written:
“谁啊？”
```

不能把这句对白翻成 `Who is it?` 后要求演员说英语，也不能把英文提示词本身当成人物台词念出来。无对白镜头写 `N/A`，不要擅自加戏。

---

## 10. 人物、造型与场景图片提示词示例

这些是**生成或准备参考图片时可使用的参考描述**，不是 Skill 安装的前提，也不是自动执行的图像生成任务。正式生产建议统一人物、场景和道具的已批准资产版本。

### A. 人物身份主图（Identity RefMod）

```text
同一名成年东亚男性角色的清晰正脸身份参考，正面微3/4偏转，
面部比例自然，五官真实一致，头发细节完整，柔和均匀的摄影棚布光，
干净的中性灰背景，皮肤不过度磨皮，表情中性，眼睛、眉、鼻、嘴清楚可辨。
仅一人，无字幕，无文字，无水印，无多人拼贴，不要夸张广角畸变。
```

### B. 补充角度（同一个人物，Identity RefMod）

```text
与身份主图完全同一成年角色，同一发型和面部比例，
补充三分之四面部及标准90度侧脸参考。
若制作2×2角度参考板，四格必须严格属于同一张脸，
光线与背景统一，不添加编号文字，不引入第二人。
```

### C. 无头服装正面（Clothing RefMod）

```text
一套独立的成年男性黑色修身西装服装参考，只展示衣服，不展示真人头部或脸。
包括西装外套、白衬衫、黑色西裤、黑色皮鞋以及完整搭配，
保持领口、肩线、扣位、腰线、裤型、面料与配饰的清楚结构。
单一正面视图，全套服装完整可读，干净灰背景。
不要正反面拼在同一张图，不要双人，不要额外人体头部，
不要商品文字、Logo、水印和装饰排版。
```

### D. 无头服装背面（与 C 为同一造型）

```text
与正面服装参考同一套黑色西装，单独展示完整背面视图。
西装下摆、后背省道、袖口、裤型、鞋跟、布料结构与正面严格一致。
无头、无脸，单套衣服，居中全身比例，干净灰背景。
不要并排正面、不要第二套服装、不要文字。
```

### E. 场景 MASTER（Picture）

```text
现代都市两室一厅住宅真实室内场景设定图，空间几何固定。
入户玄关、客厅沙发、餐桌、右侧开放式厨房、后方卧室走廊与窗户位置明确。
统一家具数量、门窗关系、建筑尺寸感、色彩与光照逻辑。
场景空房，无人物，无新增门，无第二套不一致平面布局。
半写实高质量场景参考，用于后续镜头保持相同建筑结构。
```

**使用要点：** 人物图属于 Identity RefMod、服装正反图属于 Clothing RefMod、场景 MASTER 才占 Picture。没有人头的服装有助于减少身份污染，但不能保证 RefMod 绝不继承参考图片的版式。

---

## 11. 整体版 GUI / CLI 使用

`00_整体一键版` 除 `SKILL.md` 入口外，也包含 `workbench.py`、`one_click.py` 等工程工具。**它们不是无需配置即可把小说变成视频的程序。**

### 环境

- Python **3.10+**；使用 `pip` 安装整体工具依赖。
- 自然语言小说的独立 GUI/CLI 规划，需要已有文本/视觉规划网关及有效配置；不配置就不能声称运行已成功。
- ComfyUI / H3 模型 / RefMod 节点与模型权重需要另行准备，Skills 负责生产资料，不提供权重。

```bash
cd 00_整体一键版
python -m pip install -r requirements.txt
```

**打开工作台：**

```bash
python workbench.py
```

Windows 也可以在该目录里运行 `启动一键生成.cmd`。

**常用 CLI（按现有代码接口）：**

```bash
# 从完整小说与真实图片目录规划项目；需要有效planner_config.json
python one_click.py source --source novel.docx --asset-root images --config planner_config.json --output production

# 已有冻结的结构化输入时导出生产工程
python one_click.py export --input project_input.json --asset-root images --output production

# 校验项目结构和依赖
python one_click.py validate --project production

# 运行项目自身测试（不等于做过真实GPU视频生成）
python one_click.py selftest --report test_report.json

# 生成示例工程
python one_click.py example --people 5 --output example_run
```

规划器配置样例见：`00_整体一键版/planner_config.example.json`。不要将 API Token、内网规划器地址、真实客户小说及未获授权的人物照片提交到公开 GitHub。

---

## 12. 输出清单和交付标准

整体工具按其现有交付规则，面向用户的资料主要包含：

1. 使用说明；
2. 中文素材 / 图片生成提示词；
3. 英文素材 / 图片生成提示词；
4. 中文分镜执行表；
5. 中文 H3 FULL 一键导入提示词；
6. 英文 H3 FULL 一键导入提示词。

真实资产图片放入独立资产目录，内部工程 JSON / 调度数据 / 验证日志与用户交付资料区分；不要将内部中间文件冒充最终生产素材。

**判定结果时明确区分：**

- **结构校验通过**：字段、引用、依赖、格式符合本工具的要求。
- **素材核验通过**：素材文件真实存在，身份、造型、场景确实对应。
- **视频生成完成**：ComfyUI/H3 实际输出了视频文件。
- **视频 QC 通过**：人工或真实工具检查过人物、服装、镜头、空间、音画连续性。

前两项不自动意味着后两项。视频未生成时，状态应为 `NOT_RUN`，不能声称已完成视频制作。

---

## 13. 常见问题与故障排查

**Q：五个 Skills 要放在两个不同的文件夹吗？**  
A：不需要。安装时是五个**同级** Skill 目录，`00_整体一键版`、`01_只做分镜`、`02_只做中文H3`、`03_只做英文H3`、`04_一句话快速单段`。

**Q：为什么调用 01 只生成分镜，不直接给 H3？**  
A：这是独立职责设计。要中文 H3 再调用 02，要英文 H3 再调用 03；想一次完成则用 00。

**Q：可以直接把小说发给 02 吗？**  
A：02 优先接收已经确认的分镜。没有分镜，先用 01 或直接用 00；不要让 02 擅自补造完整剧情而不告知。

**Q：我只选角色、造型、场景，不会写换衣服 Prompt，可以吗？**  
A：可以。Skills 应生成分镜/H3 文本，Studio 中由用户选择已准备的角色 Identity RefMod 和 Clothing RefMod。**但实际绑定是否生效取决于 Studio 已准备好相应 RefMod。**

**Q：为什么视频会出现大脸作为背景或正反服装展示板？**  
A：常见诱因是将近脸或双视图参考直接当 Picture、旧镜头缓存仍然带有旧 Picture，以及生成式模型的构图泄漏。请核查实际传入 H3 的 `Picture绑定`、`reference_map`、RefMod 列表与镜头提示词是否一致，而不要直接推断只是分辨率问题。

**Q：只给一张无头服装参考行不行？**  
A：可以作为参考起点；正反两张分别上传通常更清楚，避免把两个完整人体轮廓并排当成一个画面布局。质量仍应实际测试。

**Q：单段中有平静→惊讶→微笑三个表情怎么办？**  
A：写到 `shot_timeline`，不用假设生成到第2秒时能切换 RefMod 条件；单次生成并不保证逐帧严格表情时序。

**Q：我切换 480P / 544P，为什么生成结果和位置不同？**  
A：不同尺寸通常从不同 latent 网格重新生成，固定 Seed 也不保证构图/动作相同。需要保持既有镜头内容并提高画质时，应使用已支持的二采/超分工作流，不是重新选高一采分辨率就等于无损放大。

**Q：安装时看不到 Skill？**  
A：核对每个目录直接含 `SKILL.md`，没有多余中间层；查看实际 YAML `name:`；重新打开 Codex 会话或刷新加载器。

**Q：这套 Skills 包含 MiniMax H3 / ComfyUI 的模型权重吗？**  
A：不包含。需要自行在合规来源安装 H3、RefMod 及相关依赖。

---

## 14. 限制、版本与声明

- **Version：** V5.1.10 · Five Independent Skills Edition
- **Primary integration：** AI-Video-Studio `AVS_REFMOD`
- **Runtime model family：** MiniMax H3 / REF2VA（需外部模型与实际运行环境）
- **Skill interface：** `SKILL.md` + 对应的 `references/` / `examples/` / 内部工程文件
- **Languages：** 中文分镜 / 中文 H3 / 英文 H3（中文对白保持普通话原文）

本项目是独立的社区/个人工作流实现，**不是 MiniMax、OpenAI 或 ComfyUI 官方项目**。生成式模型存在画面、身份、服装、时序、音频的随机性；这里的提示词规则与示例不构成必然生成一致性的保证。

**公开发布前请检查：** 来源小说版权、人物参考图授权、第三方代码/模型许可证、仓库内个人路径与 API 密钥、日志和生成素材是否允许公开。若未完成许可证核查，请不要直接把全仓内容无条件声明为 MIT。

---

**Quick Start (English):** Install the five sibling skill folders into a Codex-compatible skills directory. Invoke `ai-drama-full-pipeline` for the whole workflow, `ai-drama-storyboard-standalone` for storyboarding, `ai-drama-h3-cn-standalone` / `ai-drama-h3-en-standalone` for bilingual H3 FULL prompts, or `ai-drama-one-line-h3-standalone` for a single short shot. With `AVS_REFMOD`, character identity is supplied by Identity RefMod and the selected outfit by Clothing RefMod; scene and prop images use Picture slots. Real video generation requires a separate ComfyUI/H3 setup.
