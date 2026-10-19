# ai-drama-storyboard · V5.1

输入：04_script.json

输出：05_storyboard.json

production_profile路由：DRAMA_DIALOGUE自适应1–3镜，ACTION优先完整路径/接触动作1–2镜，TRANSFORMATION默认一个连续镜头，2D_COMIC剧情驱动1–2镜，CINEMATIC_MULTI_SHOT自适应1–3镜。数目是上限，不是配额；multi_shot_required禁止以单镜替代。已确认单镜/多镜与切点不自动重写。
每镜全局SH编号、段内start/end（毫秒）、beat_ids、景别、镜头高度、角度、焦距、运镜、构图、主补光、景深、动作与切换理由完整。时间无缝覆盖0–5秒，无重播对白、道具或声音。推近/人物转头不算新切镜。
景别按剧情任务：空间/走位/距离信息足够远；表演/对白/微反应适当近；听者真正有戏时可切反应；不按近景比例分配。构图写清必须可见与允许画外，手部接触必须可读，不为保留素材要求近景看全身鞋与全房间。普通室内不无故倾斜构图或炫技环绕。
相邻镜头读取同一状态快照。动作/声音为events，秒级阶段可以prepare但只complete/action事件计入次数。动作有接触物来源、active hand、inactive hand、动作后持有人；手部高风险至少MEDIUM。画外目标登记唯一screen-left/right，方向不明报错。段间before_events明确迁移路径/画外时间窗；段内events保留时点，换位/进场后下一生产边界建立LOCK，不把隐藏LOCK塞进正式5秒内。

## V5.1 增强合同

V5.1 H3 稳定优先级：人物身份 → 空间 → 可执行动作 → 对白容量 → 镜头清楚 → 电影感。双人对白以近景为优先，通常谁说话切谁；问答双方、表情变化和明确反应才是切点，不为短应答强行切镜。听者反应只有承担戏剧落点时才占镜，不能遮掉必须看清的说话口型或接触动作。双人镜头用于关系、共同动作、可读交接；回群像用于多人反应或人物关系/位置变化，不按固定周期回全景。第一次进入空间先生成独立 Hidden LOCK，正式 SEG 可从 0.0 秒直接近景，不能把可见1秒建立塞进正式5秒。

保持180°轴和 screen direction；镜头运动不等于人物走位，近景只改裁切/焦距/构图，画外人物仍在原位。空间、手部、走位更重要时选最小但足够说明关系的中/远景；手部高风险不使用遮挡接触过程的极近景。持续接触、单个动作、完整语句、停顿或变身优先连续镜头；镜头数是上限，不是配额。禁止用运镜条目冒充真实切镜。

shot_keyframes 是生产接口，不假装已调用图片模型。支持 SPATIAL_ANCHOR_KEYFRAME、SHOT_KEYFRAME、ACTION_KEYFRAME、END_STATE_KEYFRAME。keyframe_policy=AUTO/ALWAYS/NEVER；AUTO 对复杂多人、特殊机位、场景几何易漂、固定道具交互、历史 POSITION_DRIFT/SCENE_GEOMETRY_DRIFT、机甲/武器/特殊动作、首次复杂场景提出优先任务；简单单人近景可跳过。推荐但未生成可为 MISSING 且 keyframe_required=false；明确必需或 ALWAYS 缺图则阻止 READY。已有 Keyframe 必须进入 reference_map，只控制当前构图、站位、景别和空间关系，不能覆盖人物身份、衣服或 Scene MASTER 几何。
