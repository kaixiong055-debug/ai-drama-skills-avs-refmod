---
name: ai-drama-h3-runtime
description: 从权威生产、空间、绑定JSON完整渲染独立中文版与英文版H3导入MD。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

从权威生产、空间、绑定JSON完整渲染独立中文版与英文版H3导入MD。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

storyboard + spatial_locks + binding。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

同源 FULL_CN/EN 与 RUNTIME_CN/EN 四份主MD；06_production.json由production_state阶段产生。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 确认图依赖的production、spatial_locks、binding已全部有效。
2. 从同一Canonical分别渲染FULL及Runtime，按信息所有权合并完整细节。
3. 检查每段独立复制、双语一致、冗余与软预算，再原子导出四份主文件。

## 关键硬规则

仅用当前权威JSON渲染。FULL 使用 HEADER加十四个正文栏：subject_definitions、summary、retention_analysis、spatial_state、continuity_state、physical_continuity_locks、camera_plan、shot_timeline、detailed_description、dialogue_and_audio、overall_soundscape、non_diegetic_music、reference_map、negative_rules。旧六栏限制被V5明确替换。字段名及ID可英文，中文正文完整中文，英文正文自然英文；原文对白通过<d>[Chinese]…</d>保存相同演出合同，不能当作中文描述残留。
FULL与Runtime每个SEG均独立完整，不用同上/沿用上一段/same as above。空间、人数、衣服、干湿发、道具holder、门、家具、道路、动作声音历史、入态当前末态、Picture和续写来源明确展开。
Subject人物明确姓名、面部、发型、年龄、身体比例与当前服装职责。`PICTURE`模式允许人物Picture控制身份/服装；`AVS_REFMOD`模式严禁人物身份图、人物运行图、服装板占用Picture：Identity RefMod控制人物身份，镜头所选Clothing RefMod控制当前服装，人物Subject仍保留但标记`character_picture=NONE`。场景参考控制固定几何但不锁原图摄影机，允许剧情光线/天气/已授权临时道具。retention中Subject职责不换成Picture。镜头裁切≠物理移动；画外人物原位。所有实际Picture每段全量且有明确职责，无冗余板。
non_diegetic_music=N/A；禁止自动音乐。negatives必须含脸/年龄/换衣/换边/瞬移/画外重排/越轴/镜像/道路倒转/门与家具重造/道具增删换手/多手额外肢体/重复声音动作/末秒变形。

V5.1 同一份八个 Canonical JSON 输出 H3_PROMPTS_FULL_CN/EN.md 与 H3_RUNTIME_CN/EN.md。FULL 保留14栏审计细节；Runtime 使用 HEADER + subject_definitions、summary、spatial_state、continuity_state、camera_plan、shot_timeline、dialogue_and_audio、reference_map、negative_rules。保留旧 H3_PROMPTS_CN/EN 作为 FULL 兼容别名，jobs 默认使用 Runtime。

**V5.1.1 强制兼容规则：用户最终可复制的一键提示词不再指向精简 Runtime。** 项目名 `_H3一键导入_中文版.md` 与 `_H3_ONE_CLICK_ENGLISH.md` 必须从 `H3_PROMPTS_FULL_CN.md` / `H3_PROMPTS_FULL_EN.md` 经 engine.delivery 导出：保留FULL正文、英文稿使用中文导入段头，并补齐普通话对白约束，不能直接复制旧英文段头文件。FULL 14 栏是用户要求的正式交付格式；精简 Runtime 仅作为内部执行/诊断视图，不得冒充一键最终提示词。严禁用“概要 / 完整描述 / 镜头列表 / 事件链”式导演稿替代 H3 Prompt。

信息归属：身份/当前衣服职责在 subject_definitions；AVS_REFMOD下身份外观由Identity RefMod、服装外观由本段Clothing RefMod提供，Prompt只保留人物语义、剧情wardrobe ID与状态，不绑定人物Picture；当前位置/深度/朝向/视线/固定几何在 spatial_state；持有物/门状态/已完成动作声音/入态末态变化在 continuity_state；axis/camera_side/镜头参数在 camera_plan；0–5秒动作在 shot_timeline；对白及声音次数/窗口/终止在 dialogue_and_audio；Picture、Keyframe、LOCK与 previous tail22/AddGuide 在 reference_map；禁止事项在 negative_rules。其他字段只表达必要执行关系，不重复整个快照。当前完整基线与入态末态差异都写在本段，绝不要求读其他 SEG。

runtime_prompt_budget 为软目标：CN约2500–5000字、EN约3500–8000字符；普通双人英文达到15000触发 RUNTIME_PROMPT_OVERVERBOSE 并尝试确定性去重，不能截断或删核心状态。冗余检查同时发现左右、facing、camera_side、axis、geometry 冲突及重复negative；双语比较必须同段数、Picture、时间、对白原文、LOCK、续写与末态。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
python scripts/validate_prompt_redundancy.py production
```

## Selftest

```text
python 06_h3_runtime/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

引用外段才能理解、FULL/Runtime关键状态不一致、双语漂移、空间冲突、自动截断或删核心事实。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。

## 镜头内人物表演

在每个有人物表演的镜头shots中填写performance.cn/en，逐镜指明谁、对什么刺激、在原动作/台词前后作何可见反应。用眼神目标、眼睑/眉尾、唇角/下颌、说话前备气和句后放松等具体动作表现原情绪，不能只写“自然、有呼吸感”。听者要有克制的无声反应，不能跟读或抢话。不同人物、镜头和情绪不得套用同一句表演。

眨眼只放在已有且足够长的停顿或反应窗口，不每镜强制一次，不多人同步，不在不足一秒的快切里堆叠眨眼、点头、吸气。呼吸以微弱胸肩起伏呈现，切镜延续状态；普通生活镜头不加喘息、叹气、吸鼻或笑声音效。保持原台词、发声语言、时间窗、动作次数、视线方向、站位和持有物；不为表情新增特写、越轴或改脸。

道具、文字、无人场景特写设置face_visible=false，performance只写该镜头应保留的物件表现，不虚构脸或人体倒影。远景/背影以可见姿态和呼吸为主，不要求不可见的眼球细节。隐藏LOCK保持原空间预热要求，不增剧情表演。

engine.performance把performance确定性写入FULL和Runtime的shot_timeline，也用于旧工程交付。新增表演是14栏中的内容，不新增顶层栏位或另交一套剧本。没有performance的旧工程只提供中性的呼吸/眼睑兼容提示，不能把这种兜底当作完整导演表演；正式新任务应逐镜编写。


## 人物 RefMod（V5.1.6）

用户要求 RefMod 或人物多角度一致性时，读取并执行[人物清晰度与 RefMod 接入规则](../02_character_bible/references/refmod_identity.md)。它约束真实资产、宿主接线和分层验收，不以提示词代替实际接入。


## AI-Video-Studio RefMod 宿主兼容（V5.1.7）

本包用于 AI-Video-Studio 时，`project.character_binding_mode` 必须为 `AVS_REFMOD`。人物身份与服装不再占用 Picture 槽位：人物身份由 Studio 的 Identity RefMod 注入，当前造型由该镜头选择的 Clothing RefMod 注入；Picture 仅保留场景、局部场景、道具、构图/关键帧等真正需要的视觉参考。H3 提示词不得再写“人物身份/当前服装来自 <Picture N>”，不得把人物高清正脸、人物运行图或服装板自动绑定为人物 Picture。`subject_definitions` 仍保留人物 Subject，但明确 `character_picture=NONE`；`reference_map` 用 RefMod 行记录身份/服装权威。连续性中保留剧情 wardrobe ID 与衣服状态，但画面服装外观以 Studio 本段选择的 Clothing RefMod 为准。旧冻结项目未设置该字段时仍按 `PICTURE` 兼容模式处理。
