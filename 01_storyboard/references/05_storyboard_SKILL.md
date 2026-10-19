---
name: ai-drama-storyboard
description: 把冻结Beat映射到5秒段与真实镜头，设计景别、机位、运镜、动作时间与状态事件。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

把冻结Beat映射到5秒段与真实镜头，设计景别、机位、运镜、动作时间与状态事件。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

04_script.json。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

05_storyboard.json。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)、[Keyframe合同](references/keyframe_policy.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 读取每个Beat的戏剧任务、场景关系和当前人物资产；先确保人物与空间稳定。
2. 按H3实战规则选择最小充分景别、说话人反打、动作与镜头数。
3. 建立全局SH号、0–5秒连续时间轴、事件时点、画外目标、Keyframe任务与切换理由。
4. 校验Beat只出现一次、说得完、动作可执行、轴线可解释，再交状态/LOCK层。

## 关键硬规则

production_profile路由：DRAMA_DIALOGUE自适应1–3镜，ACTION优先完整路径/接触动作1–2镜，TRANSFORMATION默认一个连续镜头，2D_COMIC剧情驱动1–2镜，CINEMATIC_MULTI_SHOT自适应1–3镜。数目是上限，不是配额；multi_shot_required禁止以单镜替代。已确认单镜/多镜与切点不自动重写。
每镜全局SH编号、段内start/end（毫秒）、beat_ids、景别、镜头高度、角度、焦距、运镜、构图、主补光、景深、动作与切换理由完整。时间无缝覆盖0–5秒，无重播对白、道具或声音。推近/人物转头不算新切镜。
景别按剧情任务：空间/走位/距离信息足够远；表演/对白/微反应适当近；听者真正有戏时可切反应；不按近景比例分配。构图写清必须可见与允许画外，手部接触必须可读，不为保留素材要求近景看全身鞋与全房间。普通室内不无故倾斜构图或炫技环绕。
相邻镜头读取同一状态快照。动作/声音为events，秒级阶段可以prepare但只complete/action事件计入次数。动作有接触物来源、active hand、inactive hand、动作后持有人；手部高风险至少MEDIUM。画外目标登记唯一screen-left/right，方向不明报错。段间before_events明确迁移路径/画外时间窗；段内events保留时点，换位/进场后下一生产边界建立LOCK，不把隐藏LOCK塞进正式5秒内。

V5.1 H3 稳定优先级：人物身份 → 空间 → 可执行动作 → 对白容量 → 镜头清楚 → 电影感。双人对白以近景为优先，通常谁说话切谁；问答双方、表情变化和明确反应才是切点，不为短应答强行切镜。听者反应只有承担戏剧落点时才占镜，不能遮掉必须看清的说话口型或接触动作。双人镜头用于关系、共同动作、可读交接；回群像用于多人反应或人物关系/位置变化，不按固定周期回全景。第一次进入空间先生成独立 Hidden LOCK，正式 SEG 可从 0.0 秒直接近景，不能把可见1秒建立塞进正式5秒。

保持180°轴和 screen direction；镜头运动不等于人物走位，近景只改裁切/焦距/构图，画外人物仍在原位。空间、手部、走位更重要时选最小但足够说明关系的中/远景；手部高风险不使用遮挡接触过程的极近景。持续接触、单个动作、完整语句、停顿或变身优先连续镜头；镜头数是上限，不是配额。禁止用运镜条目冒充真实切镜。

shot_keyframes 是生产接口，不假装已调用图片模型。支持 SPATIAL_ANCHOR_KEYFRAME、SHOT_KEYFRAME、ACTION_KEYFRAME、END_STATE_KEYFRAME。keyframe_policy=AUTO/ALWAYS/NEVER；AUTO 对复杂多人、特殊机位、场景几何易漂、固定道具交互、历史 POSITION_DRIFT/SCENE_GEOMETRY_DRIFT、机甲/武器/特殊动作、首次复杂场景提出优先任务；简单单人近景可跳过。推荐但未生成可为 MISSING 且 keyframe_required=false；明确必需或 ALWAYS 缺图则阻止 READY。已有 Keyframe 必须进入 reference_map，只控制当前构图、站位、景别和空间关系，不能覆盖人物身份、衣服或 Scene MASTER 几何。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
```

## Selftest

```text
python 05_storyboard/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

切点漂移/时间缺口、5秒内对白或动作不可能完成、未授权越轴、方向未知、必需Keyframe缺失。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。

## 镜头内人物表演

在每个有人物表演的镜头shots中填写performance.cn/en，逐镜指明谁、对什么刺激、在原动作/台词前后作何可见反应。用眼神目标、眼睑/眉尾、唇角/下颌、说话前备气和句后放松等具体动作表现原情绪，不能只写“自然、有呼吸感”。听者要有克制的无声反应，不能跟读或抢话。不同人物、镜头和情绪不得套用同一句表演。

眨眼只放在已有且足够长的停顿或反应窗口，不每镜强制一次，不多人同步，不在不足一秒的快切里堆叠眨眼、点头、吸气。呼吸以微弱胸肩起伏呈现，切镜延续状态；普通生活镜头不加喘息、叹气、吸鼻或笑声音效。保持原台词、发声语言、时间窗、动作次数、视线方向、站位和持有物；不为表情新增特写、越轴或改脸。

道具、文字、无人场景特写设置face_visible=false，performance只写该镜头应保留的物件表现，不虚构脸或人体倒影。远景/背影以可见姿态和呼吸为主，不要求不可见的眼球细节。隐藏LOCK保持原空间预热要求，不增剧情表演。

engine.performance把performance确定性写入FULL和Runtime的shot_timeline，也用于旧工程交付。新增表演是14栏中的内容，不新增顶层栏位或另交一套剧本。没有performance的旧工程只提供中性的呼吸/眼睑兼容提示，不能把这种兜底当作完整导演表演；正式新任务应逐镜编写。
