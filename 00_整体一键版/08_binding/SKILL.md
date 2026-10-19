---
name: ai-drama-binding
description: 精确匹配真实图片、最少必要Picture绑定与Ready Gate；不推测身份或剧情。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

精确匹配真实图片、最少必要Picture绑定与Ready Gate；不推测身份或剧情。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

assets + production + spatial_locks。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

08_binding.json。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)、[资产依赖合同](../03_asset_bible/references/asset_dependencies.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 加载已核验依赖状态、当前角色衣服与状态对应必要资产。
2. 按精确路径/唯一名字/ID/别名解析真实图片，读取字节hash并拒绝歧义。
3. 为每个LOCK/SEG排P1–P9、加入有效Keyframe权限，完整核验后冻结08。

## 关键硬规则

匹配顺序：manifest精确相对路径/filename→唯一文件名→canonical asset_id规范stem→exact alias；重复文件名/ID歧义即FAIL，模糊只作建议不自动确认。读取全部真实文件，记录SHA256；输出随包复制素材，导入使用保留的相对文件名。
当 `character_binding_mode=PICTURE` 时，必要角色H3_RUNTIME、核心MASTER、动作依赖AREA、Transition/第二空间、关键道具不可被精简删除；设计FACE/BODY/WARDROBE不重复占运行Picture。
当 `character_binding_mode=AVS_REFMOD` 时，角色H3_RUNTIME只做资产/衣服variant校验，不进入P1–P9；人物身份由AI-Video-Studio Identity RefMod负责，当前造型由本段选择的Clothing RefMod负责。Picture只绑定核心MASTER、必要AREA、Transition/第二空间、关键道具和已生成Keyframe。无人物镜头不绑定人物图；声音方向不自动加AREA。
每段最多P1–P9；在PICTURE模式下Subject与Picture语义、衣服variant及资产职责严格一致；在AVS_REFMOD模式下人物Subject不对应Picture，`reference_map`必须明确 `character_picture=NONE` 与RefMod权威。必要文字资产必须命中；未知参考、缺失文件、歧义、预算超限、方向不明、HIGH跳跃、状态冲突都不能READY。目录/结构PASS与真实图片内容UNVERIFIED分开记录。

V5.1 在 Picture 排槽前检查资产依赖及当前 wardrobe，依赖状态 MISSING、错误身份、错误服装、过期 Scene AREA 均阻止 READY；STALE 只有显式 allow_stale_asset=true 可例外。已生成 Keyframe 可占参考槽并写明 reference authority；不存在的推荐 Keyframe 只作为待办，不能伪造 Picture 文件。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
python scripts/validate_asset_dependencies.py production
```

## Selftest

```text
python 08_binding/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

不存在/不可解码图片、相对路径歧义、错服装/错版本、STALE未授权、必需Keyframe缺失、Picture超9。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。


## 人物 RefMod（V5.1.6）

用户要求 RefMod 或人物多角度一致性时，读取并执行[人物清晰度与 RefMod 接入规则](../02_character_bible/references/refmod_identity.md)。它约束真实资产、宿主接线和分层验收，不以提示词代替实际接入。


## AI-Video-Studio RefMod 宿主兼容（V5.1.7）

本包用于 AI-Video-Studio 时，`project.character_binding_mode` 必须为 `AVS_REFMOD`。人物身份与服装不再占用 Picture 槽位：人物身份由 Studio 的 Identity RefMod 注入，当前造型由该镜头选择的 Clothing RefMod 注入；Picture 仅保留场景、局部场景、道具、构图/关键帧等真正需要的视觉参考。H3 提示词不得再写“人物身份/当前服装来自 <Picture N>”，不得把人物高清正脸、人物运行图或服装板自动绑定为人物 Picture。`subject_definitions` 仍保留人物 Subject，但明确 `character_picture=NONE`；`reference_map` 用 RefMod 行记录身份/服装权威。连续性中保留剧情 wardrobe ID 与衣服状态，但画面服装外观以 Studio 本段选择的 Clothing RefMod 为准。旧冻结项目未设置该字段时仍按 `PICTURE` 兼容模式处理。
