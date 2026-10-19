本包 JSON 是生产权威；双语 MD 从同一数据渲染。
实际复制给 H3：H3_RUNTIME_CN.md / H3_RUNTIME_EN.md；每个 SEG 含完整上下文。
审计调试：H3_PROMPTS_FULL_CN.md / H3_PROMPTS_FULL_EN.md；旧 H3_PROMPTS 文件为 FULL 兼容别名。
执行依赖以 pipeline_graph.json 为准，按 LOCK → SEG 链生成。
LOCK 不进成片；AddGuide 使用尾22帧，禁止继承已经结束的尾音。
每个正式段交付120帧；含引导的生成需142帧并裁22帧重叠，避免吃掉正式5秒。
不要同时让工作台和装配器重复补偿或重复裁切；以实际生成帧数与帧窗口为准。
READY 只代表提示词/数据/本地素材检查通过，视频仍需 Take/QC。
无尺寸证据的空间为 RELATIVE；资产版本未登记为 UNVERIFIED，详见依赖报告。
AUTO Keyframe 建议可保持 MISSING；显式 required / ALWAYS 缺失会阻止导出。
真实 H3 Regression 全部 NOT_RUN，指标为 null；使用软件包的回归登记脚本登记真实结果。
