# ai-drama-spatial-lock · V5.1

输入：06_production.json

输出：07_spatial_locks.json

states表唯一保存世界状态；production只持state_id，不复制可写状态。每Scene记录variant、anchor_version、角色布局坐标、测量来源与投影左右顺序、depth、distance、facing、eyelines、dialogue_axis、camera_side、entry/exit、props、architecture、doors/windows/furniture与valid_until_changed。角色画外仍在场。completed_actions/sounds跨场景保留，衣服和携带物不因换场重置。
LOCK独立LOCK_SCxx_Axx，0.8–1.5秒，默认1秒，include_in_final=false，不占SEG、不吃正式5秒。固定群像，尽量所有在场者可见；只呼吸、微表情/头部/视线。无关键对白、剧情、走位交叉、快速摄影、越轴。
新Scene、进场、退场重构、明显换位、正式跨轴、主对话群改变、跨AREA、近景继承不可靠、Review漂移触发；只有实际失效才重LOCK，同场稳定三段只建一次。主说话人临时改变≠主群结构重组，避免每轮对白重LOCK。
LOCK尾22帧/latent→AddGuide frame_idx=0→正式完整5秒；后续SEG从上一SEG尾22帧。在24fps时引导重叠约22/24秒；请求142帧、交付120帧或由已验证工作台完成补偿，不能重复补偿/裁切。实测引导能力仍以目标工作台/模型为准。

## V5.1 增强合同

V5.1 spatial_measurement=RELATIVE/METRIC/UNKNOWN，普通图片默认 RELATIVE。旧 x_m/y_m 字段可保留内部布局兼容，但 RELATIVE 下只是无单位排序坐标，不输出米或计算伪精确物理距离。METRIC 必须有 provenance.source_type、source_id、evidence；允许 USER_SPECIFIED、DIMENSIONED_FLOORPLAN、BLENDER_3D、CAD、VERIFIABLE_SCALE、CANONICAL_SCENE。可验证尺寸以 constraints 的 subject_id/reference_id/distance_m 保存。不得把相对布局自动升级为 METRIC。
