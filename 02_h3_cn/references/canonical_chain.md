# 单一权威数据与字段所有权

| 文件 | 唯一负责 | 禁止写入/猜测 |
|---|---|---|
| 01_story.json | 原文、Source Beat、项目预算、场景定义及首次几何计划 | 后续运行状态 |
| 02_cast.json | 人物姓名、身份、发型、服装家族 | 段内位置 |
| 03_assets.json | 素材ID、文件名、职责、Scene Family | 随机剧情或镜头 |
| 04_script.json | Beat、原文对白、情绪、因果、剧情道具事件 | 摄影与屏幕投影 |
| 05_storyboard.json | 全局SH、段内时间、Beat覆盖、摄影、明确状态事件 | 改原文台词/身份 |
| 06_production.json | 执行单元、state_id、shot_id、continuation、锚点引用 | 复制可编辑世界状态 |
| 07_spatial_locks.json | 世界快照、事件前后态、Hidden LOCK | 重写Beat |
| 08_binding.json | 精确Picture槽位/文件/hash | 重设计相机或造型 |

initial_state是首次规划种子；07状态表是运行时权威，后续镜头不得再次用初始种子重置。所有中间文件有父级内容SHA256，修改上游后必须重新编译整个依赖链。原文/旧manifest仅可作为provenance，不作为第二套可编辑生产事实。MD/TXT/DOCX与镜头表从JSON渲染，编辑视图不会反向生效。多语言字段为同一语义的cn/en表达；两个exporter读同一冻结JSON，不各自规划时间/状态。
