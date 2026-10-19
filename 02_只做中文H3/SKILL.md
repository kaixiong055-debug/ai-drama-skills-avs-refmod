---
name: ai-drama-h3-cn-standalone
description: 将已确认分镜独立转换成可直接导入AI-Video-Studio的中文FULL 14栏H3提示词；严格保持剧情、镜头、对白和连续性。
metadata:
  version: "1.2"
---

# AI短剧｜只做中文 H3｜独立完整版

## 独立入口优先级

本 `SKILL.md` 是该独立 Skill 的最高优先级执行合同。`references/` 用于补充细节；若历史 reference 中仍保留 PICTURE 兼容描述、旧 Runtime 输出说明或其他与本独立入口冲突的规则，以本 `SKILL.md` 为准。默认宿主固定为 `AVS_REFMOD`。

## 必读
按需读取：
- `references/06_h3_runtime_SKILL.md`
- `references/07_spatial_lock_SKILL.md`
- `references/08_binding_SKILL.md`
- `references/refmod_identity.md`
- `references/canonical_chain.md`
示例见 `examples/H3_PROMPTS_FULL_CN.md`。

## 输入
优先接受已确认分镜。也可接受单个SEG/LOCK及其上下文。不得擅自重做已确认镜头。

## 目标
只输出中文正式 H3 一键导入内容。每段独立完整，复制单段也能运行。

## FULL 14栏（一个都不能少）
subject_definitions
summary
retention_analysis
spatial_state
continuity_state
physical_continuity_locks
camera_plan
shot_timeline
detailed_description
dialogue_and_audio
overall_soundscape
non_diegetic_music
reference_map
negative_rules

## 段头
必须保留：视频片段、集数、Scene、场景、H3模式、连续性、续写来源、继承尾音、生成模式、Picture绑定、Speaker绑定。

## AVS_REFMOD 强规则
- `character_binding_mode = AVS_REFMOD`
- Identity RefMod 控制身份；Clothing RefMod 控制本段服装。
- 人物与服装不占 Picture。
- 人物 Subject 保留语义，但写 `character_picture=NONE`。
- 禁止出现 `identity/face/current wardrobe from <Picture N>`。
- 禁止人物高清正脸、人物Runtime、无头服装板作为人物 Picture。
- Picture 只用于场景MASTER、局部场景、道具、Transition、Keyframe/构图参考。
- `reference_map` 对人物记录 Identity RefMod/Clothing RefMod 权威，不分配 Picture。
- continuity 中可保留剧情 wardrobe ID/状态，但视觉服装以 Studio 当前选择的 Clothing RefMod 为准。

## 连续性
完整展开：人物位置、左右/深度/朝向、视线、axis、camera_side、衣服状态、干湿、门、holder、道具、已完成动作/声音、入态/末态、AddGuide tail22。
不得用“同上”“沿用上一段”代替当前段必要状态。

## 多表情
单一主表情可强化；同一5秒多表情按 `shot_timeline` 分时描述，不假设中途切换多个RefMod。

## 声音
- 原对白逐字保留。
- 中文对白明确普通话逐字说出。
- 无对白写 N/A。
- `non_diegetic_music: N/A`。
- 禁止自动背景音乐。

## FULL 14 栏输出优先规则

即使 `references/06_h3_runtime_SKILL.md` 中保留历史 Runtime 9栏/内部 jobs 说明，本独立 Skill 的用户可见输出始终只交付 **FULL 14栏中文 H3**；不得改成交付 Runtime 9栏，也不得同时输出两套重复 Prompt。

## 输出边界
只输出中文 H3，不输出英文，不重新写分镜，不输出内部JSON。
