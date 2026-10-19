# 单段生成 Skill

用于整体生产包之外的“只生成/重做一个片段”。

## 与整体 Skill 的关系

- 原 00–11 层：整体项目生产，保留不变。
- 12_single_segment：单段入口，不要求重跑整项目。

## 典型使用

- 给一段已有 SEG → 只重做这一段 FULL 14栏 Prompt。
- 给一个新5秒镜头要求 → 输出单段 FULL 14栏 Prompt。
- 人物身份/服装继续由 AI-Video-Studio Identity/Clothing RefMod 注入。
