# AI Drama Skills — MiniMax H3 & AVS RefMod

**Modular AI Drama Production Skills for MiniMax H3, ComfyUI and AI-Video-Studio.**

一套面向 AI 短剧、AI 漫剧和 AI 视频生产的模块化 Skills 系统，支持从小说或剧本出发，自动完成分镜设计、H3 视频提示词生成及人物参考绑定规则适配。

## Features / 核心功能

- **00 — Full Pipeline / 整体一键生成：** 小说或剧本 → 完整短剧生产资料
- **01 — Storyboard / 分镜生成：** 小说或剧本 → 完整分镜
- **02 — Chinese H3 Prompts / 中文提示词：** 分镜 → 中文 H3 FULL 提示词
- **03 — English H3 Prompts / 英文提示词：** 中文 H3 → 英文 H3 提示词
- **04 — One-Line Generation / 一句话生成：** 一句话 → 单段 H3 视频提示词

## RefMod Support / 人物一致性

面向 AI-Video-Studio 的 RefMod 工作流设计：

- Identity RefMod：人物身份与面部参考
- Clothing RefMod：服装造型参考
- Picture：场景、道具及其他需要的视觉参考

人物身份与服装不强制占用 Picture 槽位，减少重复参考带来的构图干扰。

## Production Rules / 生产规则

- 单段视频默认不超过 5 秒
- 中文、英文 H3 FULL 14 栏结构
- 人物与空间连续性约束
- 镜头、动作与对白时间轴管理
- 支持独立调用各模块
- 默认禁止自动添加背景音乐

## Usage / 使用方式

将需要的 Skill 文件夹安装到支持 `SKILL.md` 的 Skills 环境中，并按实际任务调用对应模块。

例如：

**完整制作：** 使用 00 Skill，将小说生成完整短剧生产包。

**只生成分镜：** 使用 01 Skill，根据剧本生成详细分镜。

**测试一个镜头：** 使用 04 Skill，根据一句话生成一个 5 秒 H3 提示词。

## Version

V5.1.10 — Five Modular Skills Edition

*This is an independent workflow project intended for use with MiniMax H3 and compatible ComfyUI tooling. It is not an official MiniMax project.*
