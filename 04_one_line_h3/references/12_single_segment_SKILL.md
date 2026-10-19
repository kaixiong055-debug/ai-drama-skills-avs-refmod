---
name: ai-drama-single-segment
version: "1.0"
description: 单独生成一个H3视频片段/镜头的完整可复制提示词；复用AI-Video-Studio RefMod人物/服装绑定，不触发整项目重编。
---

# AI短剧 H3 单段生成 Skill｜AVS RefMod

## 目的

当用户只需要重新生成、补生成、测试或临时新增 **一个视频片段（通常≤5秒）** 时使用本 Skill。

它与整体生产 Skill 并存：
- 整体项目、整章、整集、批量分镜 → 继续使用原 V5.1.7/V5.1.8 全链路。
- 明确只要一个片段、一个镜头、一个测试段、一个补段 → 使用本 Skill。

本 Skill **不得为了一个片段重写整集、重建全部资产或重新规划全部分镜**。

## 宿主固定规则

默认宿主为 AI-Video-Studio V0.18.10+，人物绑定模式固定为：

```text
character_binding_mode = AVS_REFMOD
```

人物视觉条件职责：

```text
Identity RefMod  = 人物是谁、脸、发型、年龄、身体身份
Clothing RefMod  = 本段人物穿什么
Picture          = 仅用于场景、局部场景、道具、构图/关键帧等视觉资产
```

### 强制禁止

在 AVS_REFMOD 模式下：
- 不把人物高清正脸作为 `<Picture N>`。
- 不把人物 runtime 全身图作为人物身份 Picture。
- 不把服装板/无头造型图作为人物 Picture。
- 不写“identity/face/current wardrobe from <Picture N>”。
- 不要求用户手写“换衣服”提示词。
- 不让人物/服装占用 Picture 槽位。

Studio 中用户只负责选择：

```text
人物 + 本段造型
```

后台由 Identity RefMod + Clothing RefMod 注入。

## 触发条件

用户出现以下意图时使用本 Skill：
- “单独生成这一段”
- “只生成这个5秒”
- “这个镜头重做”
- “给我一个测试段”
- “只补SEG012”
- “这一段单独给H3提示词”
- “不要整套，只要这一条”

如果用户要求“整章/整集/全部分镜/一键完整生成”，不得切到本 Skill。

## 输入优先级

### A. 已有项目片段

如果用户提供整体 Skills 已生成的某个 SEG/LOCK：
1. 复用该段人物、场景、道具、空间、对白、连续性、轴线、门状态、holder、完成动作/声音状态。
2. 只修改用户明确要求修改的内容。
3. 不重新猜人物衣服；Studio 本段选择的 Clothing RefMod 为画面服装权威。
4. 不修改原项目其它片段。

### B. 新建单段

若没有既有 SEG，只根据用户本次明确提供的信息构造该段。
缺失而会影响正确性的内容必须保持 `N/A`、`none`、`unspecified` 或明确“未提供”，不得凭空补剧情事实。

## 单段输出格式

最终必须输出一个可以直接导入/复制的 **FULL 14栏 H3 Prompt**。字段不得缺失：

```text
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
reference_map:
negative_rules:
```

段头必须保留：

```text
【视频片段 N｜≤5秒｜名称】
【集数】...
【Scene】...
【场景】...
【H3模式】REF2VA
【连续性】独立生成 / 续写上一段
【续写来源】...
【继承尾音】是 / 否
【生成模式】单张生成 / 抽卡生成
【Picture绑定】...
【Speaker绑定】...
```

## 人物与服装写法

### subject_definitions

人物 Subject 必须保留，但人物视觉权威写为 RefMod，不写人物 Picture：

```text
<Subject 1> is [人物语义描述].
Identity, face, hairstyle, apparent age and body identity are controlled by AI-Video-Studio Identity RefMod.
The current wardrobe appearance is controlled by the Clothing RefMod selected for this shot in AI-Video-Studio.
character_picture=NONE.
```

如果本段未选择造型：

```text
The wardrobe follows the shot's declared story wardrobe state; no character Picture is used.
```

### retention_analysis

人物可写：

```text
<Subject 1>: fully_preserved - preserve character identity, face, hairstyle, age, body proportions and the currently selected wardrobe.
```

不得写：

```text
current wardrobe from <Picture 1>
```

## Picture绑定规则

Picture 只放：
- 场景 MASTER
- 局部场景
- 道具
- 必需的构图/关键帧
- 明确要求的其他非人物视觉参考

例如：

```text
【Picture绑定】P1=SCN_MASTER.png；P2=SCN_LAUNDRY.png；P3=PROP_SHIRT.png
```

注意：用户项目中的旧编号可保留语义，但最终导入若由 Studio 重新打包，按 Studio 实际 Picture 顺序为准。

## 单段连续性模式

### 独立生成

- 不读取不存在的上一段。
- 空间、人物站位、道具状态必须在本段完整说明。
- `续写来源=无`。

### 续写上一段

只有在用户明确提供上一段或 Studio 已知上一段时使用：

```text
【连续性】续写上一段
【续写来源】SEGxxx last 22 frames
```

必须继承：
- 上一段最后22帧姿态/位置/朝向
- 摄影机侧
- 持有物
- 门状态
- 已完成动作
- 已发生声音
- 用户选择时的尾音

不得重复已完成事件。

## 5秒内部多表情

若同一5秒存在多种表情变化，不为每个表情切换 RefMod。
使用 `shot_timeline` / `detailed_description` 做时间轴表情调度，例如：

```text
0.0-1.5s: neutral
1.5-3.0s: brief surprise
3.0-5.0s: restrained smile
```

人物 Identity RefMod 与 Clothing RefMod 整段固定。

若整段只有一种主表情，可在提示词中强化该表情；不要自动增加新的表情 Picture。

## 镜头硬规则

- 默认每段≤5秒。
- 近景优先；只有建立空间时才使用中远景。
- 对话“谁说话切谁”。
- 保持180°轴线。
- 镜头运动≠人物走位。
- 最后一秒禁止随机变形。
- 高速动作必须可读，不能用运动模糊掩盖动作。
- 禁止自动背景音乐。
- 无对白写 `N/A`，不得自行新增对白。

## 声音规则

`non_diegetic_music` 固定：

```text
N/A
```

只保留剧情需要的对白、环境声、脚步、接触、武器、雨风、门铃、呼吸等。
中文对白必须明确为普通话逐字说出，不翻译成英文配音。

## 输出边界

本 Skill 只交付当前单段内容，不额外输出：
- 整集重新规划
- 新人物Bible
- 全资产清单
- 全集 storyboard
- 与当前段无关的批量 Prompt

除非用户明确要求。

## 自检

输出前检查：
1. 是否只生成用户要求的一个 SEG/LOCK。
2. 是否 FULL 14栏完整。
3. 是否人物身份/衣服都没有绑定到 Picture。
4. 是否 Picture 只剩场景/道具/关键帧等。
5. 是否 Studio 造型选择可直接覆盖画面服装。
6. 是否没有改写用户未要求修改的剧情/对白/空间状态。
7. 是否≤5秒或明确说明用户要求的特殊长度。
8. 是否 `non_diegetic_music=N/A`。

