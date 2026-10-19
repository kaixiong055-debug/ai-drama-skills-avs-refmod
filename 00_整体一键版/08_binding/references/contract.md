# ai-drama-binding · V5.1

输入：assets + production + spatial_locks

输出：08_binding.json

匹配顺序：manifest精确相对路径/filename→唯一文件名→canonical asset_id规范stem→exact alias；重复文件名/ID歧义即FAIL，模糊只作建议不自动确认。读取全部真实文件，记录SHA256；输出随包复制素材，导入使用保留的相对文件名。
当 `character_binding_mode=PICTURE` 时，必要角色H3_RUNTIME、核心MASTER、动作依赖AREA、Transition/第二空间、关键道具不可被精简删除；设计FACE/BODY/WARDROBE不重复占运行Picture。
当 `character_binding_mode=AVS_REFMOD` 时，角色H3_RUNTIME只做资产/衣服variant校验，不进入P1–P9；人物身份由AI-Video-Studio Identity RefMod负责，当前造型由本段选择的Clothing RefMod负责。Picture只绑定核心MASTER、必要AREA、Transition/第二空间、关键道具和已生成Keyframe。无人物镜头不绑定人物图；声音方向不自动加AREA。
每段最多P1–P9；在PICTURE模式下Subject与Picture语义、衣服variant及资产职责严格一致；在AVS_REFMOD模式下人物Subject不对应Picture，`reference_map`必须明确 `character_picture=NONE` 与RefMod权威。必要文字资产必须命中；未知参考、缺失文件、歧义、预算超限、方向不明、HIGH跳跃、状态冲突都不能READY。目录/结构PASS与真实图片内容UNVERIFIED分开记录。

## V5.1 增强合同

V5.1 在 Picture 排槽前检查资产依赖及当前 wardrobe，依赖状态 MISSING、错误身份、错误服装、过期 Scene AREA 均阻止 READY；STALE 只有显式 allow_stale_asset=true 可例外。已生成 Keyframe 可占参考槽并写明 reference authority；不存在的推荐 Keyframe 只作为待办，不能伪造 Picture 文件。
