# V5.1.7 - AI-Video-Studio RefMod Compatibility

- 新增 `project.character_binding_mode`: `PICTURE` / `AVS_REFMOD`.
- AI-Video-Studio 默认规划为 `AVS_REFMOD`.
- AVS_REFMOD 下人物 H3_RUNTIME 资产仍校验，但不进入 Picture 1-9。
- 人物 Subject 改由 Identity RefMod + shot-selected Clothing RefMod 定义。
- Picture 仅用于场景、局部场景、道具、Storyboard/Keyframe。
- 删除 H3 提示词中“identity/current wardrobe from <Picture N>”的 AVS 路径。
- continuity/physical 状态保留剧情 wardrobe ID，但画面服装外观权威交给 Studio 当前 Clothing RefMod。
- 兼容旧冻结项目：缺少 character_binding_mode 时继续走 PICTURE。
