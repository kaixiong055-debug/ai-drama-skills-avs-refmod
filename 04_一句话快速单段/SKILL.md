---
name: ai-drama-one-line-h3-standalone
description: 从一句话或极短镜头要求直接构造一个≤5秒、可复制导入AI-Video-Studio的FULL 14栏H3单段提示词。
metadata:
  version: "1.2"
---

# AI短剧｜一句话快速单段｜独立完整版

## 独立入口优先级

本 `SKILL.md` 是该独立 Skill 的最高优先级执行合同。`references/` 用于补充细节；若历史 reference 中仍保留 PICTURE 兼容描述、旧 Runtime 输出说明或其他与本独立入口冲突的规则，以本 `SKILL.md` 为准。默认宿主固定为 `AVS_REFMOD`。

## 必读
按需读取：
- `references/12_single_segment_SKILL.md`
- `references/05_storyboard_SKILL.md`
- `references/06_h3_runtime_SKILL.md`
- `references/refmod_identity.md`

## 输入示例
“男主推门进屋，看见女主后愣了一下。”
“女主冲刺拔剑，男主回身格挡。”
“顾言川坐在沙发上看手机，听见门铃抬头。”

## 目标
一句话直接扩成一个默认≤5秒的可执行 H3 Prompt，不启动整项目，不凭空补关键剧情事实。

## 缺失信息处理
未提供的人物资产ID、造型ID、Scene资产、上一段状态、道具ID，不得瞎编。用 N/A / unspecified / current selected wardrobe 等明确占位。

## AVS_REFMOD
若给出人物与造型：
- Identity RefMod = 人物
- Clothing RefMod = 造型
- `character_picture=NONE`
- 人物/服装不占 Picture
Picture 只用于明确提供的场景/道具/Keyframe。

## FULL 14栏
必须完整输出 14 栏，不得缩水。

## 5秒导演规则
- 简单动作不扩成一堆无关动作。
- 近景优先；动作需要空间说明时再退中景。
- 对白必须说得完；无对白不新增。
- 多表情用时间轴：平静→惊讶→微笑；不假设中途切RefMod。
- 180°轴线、动作可读、末秒不随机变形。
- `non_diegetic_music: N/A`。

## 表情调度补充

同一5秒只有一个主要表情时，可在文字描述中强化；存在两种及以上连续表情变化时，只用 `shot_timeline` / `detailed_description` 的时间顺序描述，不要求宿主在单次生成中途切换多个表情 RefMod。

## 输出边界
只给当前一个 SEG/LOCK 的完整提示词，不生成整集、不生成资产Bible、不输出内部JSON。
