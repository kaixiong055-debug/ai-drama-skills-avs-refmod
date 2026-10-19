---
name: ai-drama-storyboard-standalone
description: 从小说、剧本或剧情梗概独立完成剧情理解、人物/场景状态整理、可拍摄脚本化与5秒分镜设计；最终只交付分镜，不生成H3提示词。
metadata:
  version: "1.2"
---

# AI短剧｜只做分镜｜独立完整版

本 Skill 不是薄封装。它需要独立承担“原文理解 → 人物/场景状态 → 脚本化 → 分镜”的必要内部步骤，但最终只把分镜交给用户。

## 独立入口优先级

本 `SKILL.md` 是该独立 Skill 的最高优先级执行合同。`references/` 用于补充细节；若历史 reference 中仍保留 PICTURE 兼容描述、旧 Runtime 输出说明或其他与本独立入口冲突的规则，以本 `SKILL.md` 为准。默认宿主固定为 `AVS_REFMOD`。

## 必读
执行前按需读取：
- `references/01_story_adapter_SKILL.md`
- `references/02_character_bible_SKILL.md`
- `references/03_asset_bible_SKILL.md`
- `references/04_script_SKILL.md`
- `references/05_storyboard_SKILL.md`
- `references/keyframe_policy.md`
- `references/refmod_identity.md`

这些文件是本 Skill 的规则库，不是额外输出。

## 输入
可接受：完整小说、某章小说、剧本、剧情梗概、已有段落、已确认人物/场景资产说明。

## 内部执行链
1. 提取剧情事件、人物关系、场景、道具、对白，不擅自增写关键剧情。
2. 建立人物/场景/道具连续状态，只作为分镜设计依据。
3. 将剧情压成可在视频中执行的 beat。
4. 按 H3 生产实际拆成默认≤5秒的视频段。
5. 对每段设计真实镜头、站位、轴线、动作时间、对白容量、声音与末态。
6. 只交付分镜稿；不继续生成中文/英文 H3 Prompt。

## AVS RefMod 固定前提
后续宿主为 AI-Video-Studio：
- Identity RefMod = 人物身份、脸、发型、年龄感、身体身份。
- Clothing RefMod = 本段当前造型。
- 人物和服装不占 Picture。
- 分镜阶段只记录人物名/ID + 当前造型名/ID；不设计人物 Picture 槽。
- Picture 预留给场景、局部场景、道具、Keyframe/构图参考。

## 分镜硬规则
- 每段默认≤5秒；对白必须能说完，否则拆段。
- 近景优先；对话通常谁说话切谁，但只在真实戏剧落点时切反应。
- 180°轴线、screen direction、人物左右/前后、距离、道具 holder、门状态连续。
- 镜头运动不等于人物位移；裁切不等于人物瞬移。
- 动作必须有起点、过程、结果；接触动作需可读。
- Hidden LOCK 仅用于空间预热，不塞进正式5秒剧情动作。
- 多人/复杂动作可提出 Keyframe 任务，但不要假装已经生成图片。
- 无对白写 N/A；不自动新增对白；禁止自动背景音乐。

## 每段输出字段
必须至少包含：
【视频片段N｜时长｜名称】
【Scene】
【场景】
【人物】
【当前造型】
【连续性】
【站位】左右/前后/距离/朝向/道具依附
【景别/机位/焦距/运镜】
【0–5秒时间轴】
【动作】
【对白】
【音效】
【段末状态】
【下一段继承】
【Keyframe需求】如无则N/A

## 禁止输出
- 不输出 FULL 14栏 H3。
- 不输出英文 H3。
- 不输出人物 `<Picture N>`。
- 不把内部 JSON/状态库当作用户交付物。
