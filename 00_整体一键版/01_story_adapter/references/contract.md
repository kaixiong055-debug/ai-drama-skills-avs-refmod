# ai-drama-story-adapter · V5.1

输入：source

输出：01_story.json

先完整读取源文本，登记source_beats。EXACT保留关键对白、动作、因果、人物关系、触发—反应—结果、剧情依赖次数；MERGE保留可合并信息；OMIT_OPTIONAL必须说明理由，不能省略核心剧情。按戏剧目标归组，不把每个微反应或长旁白短句扩成5秒空镜。短文可短，不凑180秒。预算不能以多集/分包重置。
选定的对白在Script冻结后下游不重译、不增删；英文版描述独立自然生成，对白原文和spoken_language作为演出合同保持一致。HIGH时间跳跃必须有明确桥接/画外时间窗；洗澡、换衣、做饭不作为5秒瞬间完成。预算超过上限返回改编；已有用户确认分镜按CONFIRMED预算不自动压缩。

## V5.1 增强合同

V5.1 不把图片上观察到的相对关系编成米数。scene.spatial_measurement 默认 RELATIVE；METRIC 必须有用户尺寸、标注户型图、实际3D/CAD或可验证尺度等 provenance。相对布局只能用作投影/排序。规划器生成同一份双语 Canonical 数据，FULL 和 Runtime 均由确定性渲染器生成，禁止再让模型重写 Runtime。
