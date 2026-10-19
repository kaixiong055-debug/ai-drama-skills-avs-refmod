# V5.1.1 H3 一键 FULL 格式修正

本热修复只处理用户最终 H3 Prompt 格式，不改变八份 Canonical JSON 与既有运行逻辑。

- 修复项目名 `_H3一键导入_中文版.md` / `_H3_ONE_CLICK_ENGLISH.md` 错误指向精简 Runtime 的问题。
- 一键文件现在强制来自 `H3_PROMPTS_FULL_CN/EN.md`。
- 每个 LOCK / SEG 强制完整 14 栏 H3 Prompt。
- 导演审阅稿（概要/完整描述/镜头列表/事件链）禁止冒充 H3 Runtime。
- `H3_RUNTIME_CN/EN.md` 继续保留为内部精炼视图，便于生成任务和长度诊断。
