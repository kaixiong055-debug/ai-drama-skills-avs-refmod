---
name: ai-drama-h3-en-standalone
description: 将中文FULL 14栏H3提示词严格转换为同源英文版；保持段数、镜头时间、Picture、RefMod、对白、空间和连续性完全一致。
metadata:
  version: "1.2"
---

# AI短剧｜只做英文 H3｜独立完整版

## 独立入口优先级

本 `SKILL.md` 是该独立 Skill 的最高优先级执行合同。`references/` 用于补充细节；若历史 reference 中仍保留 PICTURE 兼容描述、旧 Runtime 输出说明或其他与本独立入口冲突的规则，以本 `SKILL.md` 为准。默认宿主固定为 `AVS_REFMOD`。

## 必读
按需读取：
- `references/06_h3_runtime_SKILL.md`
- `references/07_spatial_lock_SKILL.md`
- `references/08_binding_SKILL.md`
- `references/refmod_identity.md`
- `references/canonical_chain.md`
示例见 `examples/H3_PROMPTS_FULL_EN.md`。

## 输入
完整中文 FULL 14栏 H3 Prompt。

## 这是同源渲染，不是二次创作
不得改变：段数、SEG/LOCK ID、时长、切点、人物数量、人物位置、动作次数、对白原文、Picture绑定、RefMod职责、道具holder、门状态、续写来源、22帧继承、末态。

## 输出结构
仍然完整保留 FULL 14栏与中文导入段头。正文自然英文。

## 中文对白
- 中文对白保持中文原文。
- 明确 `spoken in Mandarin Chinese exactly as written`。
- 不翻译成英文配音，不把提示词文字当台词朗读。

## AVS_REFMOD
必须保持：
- `character_picture=NONE`
- Identity RefMod = identity authority
- Clothing RefMod = wardrobe authority
- 人物/服装不占 Picture
不得在英文版重新引入人物 `<Picture N>`。

## Picture
场景、道具、Keyframe 的 Picture 关系与中文稿完全一致。

## 声音
`non_diegetic_music: N/A`；禁止新增对白和背景音乐。

## FULL 14 栏输出优先规则

即使 `references/06_h3_runtime_SKILL.md` 中保留历史 Runtime 9栏/内部 jobs 说明，本独立 Skill 的用户可见输出始终只交付 **FULL 14栏英文 H3**；不得改成交付 Runtime 9栏，也不得同时输出两套重复 Prompt。

## 输出边界
只输出英文 H3，不解释、不重新生成分镜、不改剧情。
