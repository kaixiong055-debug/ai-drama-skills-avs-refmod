# V5.1.8

- 保留原有整体 00–11 生产链。
- 新增 `12_single_segment` 单段生成 Skill。
- 单段模式只生成/重做一个 SEG/LOCK，不重跑整集。
- 单段输出保持 FULL 14栏 H3 格式。
- 与 AI-Video-Studio AVS_REFMOD 完全一致：Identity RefMod 锁人物，Clothing RefMod 控制服装，人物不占 Picture。
- 支持独立生成、续写上一段、单段测试和局部重做。
