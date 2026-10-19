# ai-drama-h3-runtime · V5.1

输入：storyboard + spatial_locks + binding

输出：同源 FULL_CN/EN 与 RUNTIME_CN/EN 四份主MD；06_production.json由production_state阶段产生

仅用当前权威JSON渲染。FULL 使用 HEADER加十四个正文栏：subject_definitions、summary、retention_analysis、spatial_state、continuity_state、physical_continuity_locks、camera_plan、shot_timeline、detailed_description、dialogue_and_audio、overall_soundscape、non_diegetic_music、reference_map、negative_rules。旧六栏限制被V5明确替换。字段名及ID可英文，中文正文完整中文，英文正文自然英文；原文对白通过<d>[Chinese]…</d>保存相同演出合同，不能当作中文描述残留。
FULL与Runtime每个SEG均独立完整，不用同上/沿用上一段/same as above。空间、人数、衣服、干湿发、道具holder、门、家具、道路、动作声音历史、入态当前末态、Picture和续写来源明确展开。
Subject人物明确姓名、面部、发型、年龄、身体比例与当前服装职责。`PICTURE`模式允许人物Picture控制身份/服装；`AVS_REFMOD`模式严禁人物身份图、人物运行图、服装板占用Picture：Identity RefMod控制人物身份，镜头所选Clothing RefMod控制当前服装，人物Subject仍保留但标记`character_picture=NONE`。场景参考控制固定几何但不锁原图摄影机，允许剧情光线/天气/已授权临时道具。retention中Subject职责不换成Picture。镜头裁切≠物理移动；画外人物原位。所有实际Picture每段全量且有明确职责，无冗余板。
non_diegetic_music=N/A；禁止自动音乐。negatives必须含脸/年龄/换衣/换边/瞬移/画外重排/越轴/镜像/道路倒转/门与家具重造/道具增删换手/多手额外肢体/重复声音动作/末秒变形。

## V5.1 增强合同

V5.1 同一份八个 Canonical JSON 输出 H3_PROMPTS_FULL_CN/EN.md 与 H3_RUNTIME_CN/EN.md。FULL 保留14栏审计细节；Runtime 使用 HEADER + subject_definitions、summary、spatial_state、continuity_state、camera_plan、shot_timeline、dialogue_and_audio、reference_map、negative_rules。保留旧 H3_PROMPTS_CN/EN 作为 FULL 兼容别名，jobs 默认使用 Runtime。

### V5.1.1 一键 H3 正式交付格式

项目名 `_H3一键导入_中文版.md` / `_H3_ONE_CLICK_ENGLISH.md` 必须从 `H3_PROMPTS_FULL_CN.md` / `H3_PROMPTS_FULL_EN.md` 生成，不得从精简 Runtime 生成。最终一键文件每个 LOCK/SEG 必须具备完整 14 栏：subject_definitions、summary、retention_analysis、spatial_state、continuity_state、physical_continuity_locks、camera_plan、shot_timeline、detailed_description、dialogue_and_audio、overall_soundscape、non_diegetic_music、reference_map、negative_rules。

若用户提供或系统生成的所谓 `H3_RUNTIME_CN.md` 只有“概要 / 完整描述 / 镜头列表 / 事件链”等导演稿字段，则它不是合法 H3 Runtime/Prompt，必须回到 Canonical JSON 重新渲染，禁止在错误 Markdown 上补丁式修复。

信息归属：身份/当前衣服职责在 subject_definitions；AVS_REFMOD下身份外观由Identity RefMod、服装外观由本段Clothing RefMod提供，Prompt只保留人物语义、剧情wardrobe ID与状态，不绑定人物Picture；当前位置/深度/朝向/视线/固定几何在 spatial_state；持有物/门状态/已完成动作声音/入态末态变化在 continuity_state；axis/camera_side/镜头参数在 camera_plan；0–5秒动作在 shot_timeline；对白及声音次数/窗口/终止在 dialogue_and_audio；Picture、Keyframe、LOCK与 previous tail22/AddGuide 在 reference_map；禁止事项在 negative_rules。其他字段只表达必要执行关系，不重复整个快照。当前完整基线与入态末态差异都写在本段，绝不要求读其他 SEG。

runtime_prompt_budget 为软目标：CN约2500–5000字、EN约3500–8000字符；普通双人英文达到15000触发 RUNTIME_PROMPT_OVERVERBOSE 并尝试确定性去重，不能截断或删核心状态。冗余检查同时发现左右、facing、camera_side、axis、geometry 冲突及重复negative；双语比较必须同段数、Picture、时间、对白原文、LOCK、续写与末态。
