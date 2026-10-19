# ai-drama-qc · V5.1

输入：生产包与真实生成结果

输出：production_review.json + Take QC

先运行schema、Script/Storyboard/state replay/Picture/双语MD验证；FAIL不能READY。再查看实际图片、逐帧视频，记录具体证据，不把结构PASS称为成片验收。
拒绝原因固定：IDENTITY_DRIFT、FACE_DRIFT、COSTUME_DRIFT、POSITION_DRIFT、LEFT_RIGHT_SWAP、AXIS_FLIP、EYELINE_ERROR、SCENE_GEOMETRY_DRIFT、PROP_DISAPPEAR、PROP_SPAWN、HAND_DEFORMATION、EXTRA_LIMB、ACTION_NOT_COMPLETED、ACTION_REPEATED、SOUND_REPEATED、END_FRAME_DEFORMATION、MOTION_BLUR_EXCESSIVE。
空间类拒绝回到新的输出包重建对应Hidden LOCK；身份/道具/声音问题修对应权威数据/素材/执行，不以再加长Prompt掩盖。ACCEPTED必须有qc_evidence，拒绝Take不能装配。

## V5.1 增强合同

V5.1 结构审查增加 Runtime 冗余/矛盾、资产依赖、测量来源、Keyframe权限、pipeline_graph、FULL/Runtime双语同源校验。h3_regression/R01–R15 每例 A/B/C：A=V5.0无LOCK，B=V5.0有LOCK，C=V5.1有LOCK。无视频时 status=NOT_RUN、八指标全null；不能填0或声称PASS。真实结果只能通过有证据登记形成 RECORDED/PARTIAL/COMPLETED，结构PASS不代表模型质量。
