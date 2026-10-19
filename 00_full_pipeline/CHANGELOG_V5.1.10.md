# V5.1.10 复检修正

- 新增 `00_full_pipeline/SKILL.md` 根入口，使 00 真正可作为单个 Skill 添加。
- 01–04 独立 Skill 的 frontmatter 统一为 `metadata.version`。
- 清理 RefMod 规则中“普通人物 Picture 主图”的历史歧义；AVS_REFMOD 下人物/服装不占 Picture。
- 02/03 明确用户可见输出始终为 FULL 14栏，不受内部 Runtime 9栏历史说明影响。
- 修复 Windows 一键启动 `.cmd` 文件名乱码。
- 不改整体 engine 行为；保留 PICTURE 老项目兼容模式。
