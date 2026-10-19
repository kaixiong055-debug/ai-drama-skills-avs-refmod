# CHANGELOG V5.1

KEEP：保留V5.0的12层目录、八份Canonical JSON及hash链、Script/Storyboard职责、2～5人/无人物、身份/服装/道具/门/声音次数与时窗、Hidden LOCK独立编号及成片排除、0.8～1.5秒预热→尾22帧/AddGuide→完整5秒SEG、多镜头时间轴、REF2VA/Picture/Subject/reference_map、CN/EN、Generation Ledger/Take/QC/Assembly、Ready Gate和原有测试行为。保留旧H3_PROMPTS与工作台兼容输出以及更细历史规则的可追溯证据。

REFACTOR：FULL与Runtime从同一Canonical状态分别确定性渲染；默认生成任务改用Runtime。12个核心SKILL补齐目的、输入、输出、必读参考、执行顺序、硬规则、validator、selftest、失败条件，Storyboard补齐H3实战取景/反打/群像/轴线/动作与镜头边界。pipeline_graph.json明确真实依赖，旧目录编号不再误导导出顺序。

MERGE：Runtime把retention_analysis/physical_continuity_locks/detailed_description的必要事实按身份、空间、连续性、摄影机、动作、声音、参考与禁止项合并；同段基线只完整声明一次，入态末态用完整可理解变化表达。FULL保留详细记录；不以截断、删剧情或“同上”减少长度。

新增：Runtime去重复/矛盾检查和软字符预算；RELATIVE/METRIC/UNKNOWN与尺寸来源；资产依赖版本及STALE级联/默认阻断/显式例外；Keyframe AUTO/ALWAYS/NEVER生产接口及参考权限；资产依赖报告；15例×A/B/C真实H3回归清单、实际视频probe/证据登记、完整生成参数、ledger双向链接与控制变量比较。

测试 PASS：未修改的 V5.0 基线 58 项；V5.1 完整测试套件 131 项（含原有 58 项行为测试，仅版本前缀断言更新）；12 个 Skill 分层自测与 Skill 格式检查；12 套原场景重建及新增资产/Keyframe 示例；Python compile；全部 JSON / JSON Schema / 本地链接；所有旧新 validator；双语一致性、Runtime / Full、Pipeline Graph、真实回归登记逻辑。详见 VALIDATION_REPORT.json 和 validation/ 日志。

真实H3 Regression：R01–R15所有A/B/C目前均NOT_RUN，八项指标均null。未运行真实H3、未调用图片生成模型、未以工程夹具模拟模型质量。自动测试中的视频probe使用明确的单元测试stub，仅证明登记逻辑。

发布补充：米制约束与可用坐标一致性、显式人物朝向不被视线自动改写、按 Canonical 状态重放 Picture 绑定均已覆盖回归测试。规划模型不能擅自放行过期资产或编造资产版本。

长度对照（同一 TEST01 双人对白首段，字符数）：中文版 6599 → 3083；英文版 18220 → 6526。这是工程示例长度比较，不代表真实 H3 视频质量已验证。

最终封包检查 PASS：ZIP CRC 全量校验、干净解压后完整自测/两类生产包 validator/compile/五人示例生成/回归比较 CLI。真实 H3 仍为 NOT_RUN。
