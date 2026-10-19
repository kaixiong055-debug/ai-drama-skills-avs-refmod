【空间预热 LOCK_SC01_A01｜1秒｜隐藏空间预热】
【Scene】SCN_LIVING_NIGHT｜夜晚客厅
【集数】EP01｜第一章
【H3模式】REF2VA
【最终成片】否
【连续性】独立生成

subject_definitions:
<Subject 1> 是顾言川 (CHAR_A); 约28岁的成年人，保持原面部和身材比例; 发型=整齐的黑发; wardrobe=AI-Video-Studio本段选择的Clothing RefMod; hair_state=干燥; clothing_state=干燥、完整; pose=自然站立. 身份由Identity RefMod控制；人物不占Picture槽位。
<Subject 2> 是林晚晴 (CHAR_B); 约28岁的成年人，保持原面部和身材比例; 发型=整齐的黑发; wardrobe=AI-Video-Studio本段选择的Clothing RefMod; hair_state=干燥; clothing_state=干燥、完整; pose=自然站立. 身份由Identity RefMod控制；人物不占Picture槽位。
<Subject 3>: 夜晚客厅; 场景参考属于同一环境主体。

summary:
自然写实漫剧，稳定人物与室内光线
建立空间锚点，不执行正式剧情。
spatial_state:
spatial_measurement: RELATIVE; confidence=UNKNOWN
area=主区域; scene_variant=主场景; 在场人数=2
顾言川 (CHAR_A): screen_position=左侧; depth=前景; facing=右侧; eyeline=林晚晴.
林晚晴 (CHAR_B): screen_position=右侧; depth=前景; facing=左侧; eyeline=顾言川.
顾言川、林晚晴: 相邻，保持已建立的相对间隔；未提供米制尺度
geometry.fixed_architecture.walls=矩形客厅；北墙固定
geometry.door_positions.ENTRY_DOOR=后方左侧
geometry.window_positions.WINDOW=后方右侧
geometry.furniture_positions.SOFA=位于角色右侧后方
geometry.furniture_positions.TABLE=前景中央
geometry.furniture_positions.CHAIR=左侧中景
geometry.entrance_positions.ENTRY_DOOR=后方左侧进场
geometry.exit_positions.ENTRY_DOOR=后方左侧离场
dialogue_group=顾言川、林晚晴

continuity_state:
incoming_state: 独立初始化当前声明的场景。
current_state:
valid_until_changed=true; 以下基线在无明确事件时持续至5秒末。
当前无持有或登记道具。
door_states: ENTRY_DOOR=关闭
completed_actions: 无
completed_sounds: 无
end_state: 保持基线，结束于稳定姿态；不完成任何剧情动作或声音事件。
from_previous: 无外部动态输入。
to_next: SEG001

camera_plan:
camera_side=南侧; dialogue_axis=东西方向锁定轴线
镜头从群像切为单人近景时，仅改变摄影机裁切、焦距与构图；角色在真实场景中的物理位置不发生变化。画外人物仍保持上一空间锚点中的原位置。
稳定全景；固定摄影机；所有在场人物和关键固定结构可见。

shot_timeline:
[Shot 1 | 0.000–1.000s]
仅自然呼吸和微小头部动作；不走位、不交叉、不换边、不执行复杂动作；结束于清晰稳定末帧。

dialogue_and_audio:
无对白或关键声音事件。
环境声：低声室内环境底声和轻微呼吸
non_diegetic_music=N/A

reference_map:
RefMod → <Subject 1>; identity=AI-Video-Studio Identity RefMod; wardrobe=shot-selected Clothing RefMod; character_picture=NONE.
RefMod → <Subject 2>; identity=AI-Video-Studio Identity RefMod; wardrobe=shot-selected Clothing RefMod; character_picture=NONE.
P1=SCN_LIVING_MASTER.png; <Picture 1> → <Subject 3>; asset_id=SCN_LIVING_MASTER; 控制固定建筑、门窗、家具与真实空间几何；不锁原图机位，剧情灯光/昼夜/天气优先。
Hidden LOCK: LOCK_SC01_A01; 提供稳定空间锚点，绝不计入正式5秒或最终成片。
continuation_source=NONE; 输出尾22帧供下一正式段AddGuide。

negative_rules:
禁止人物换脸、改变年龄、身份或身体比例。
禁止无剧情原因换衣、改变发型、湿发或干发状态。
禁止随机交换人物左右位置、近景传送、将画外人物重新安排到新位置。
禁止随机越轴、镜像翻转、道路左右反转。
禁止移动门窗、添加新门、删除固定家具或重新设计场景。
禁止道具凭空出现、消失、擅自换手或改变持有人。
禁止多手、额外手臂、肢体融合和手部变形；每人恰好两只手。
禁止重复已完成动作或重新播放已结束的声音事件。
禁止最后一秒随机变形、过度运动模糊、文字、水印；剧情文字只能严格复制绑定素材。
禁止自动加入背景音乐。

【视频片段 1｜5秒｜晚上｜室友短句对白】
【Scene】SCN_LIVING_NIGHT｜夜晚客厅
【集数】EP01｜第一章
【H3模式】REF2VA
【最终成片】是
【连续性】续写

subject_definitions:
<Subject 1> 是顾言川 (CHAR_A); 约28岁的成年人，保持原面部和身材比例; 发型=整齐的黑发; wardrobe=AI-Video-Studio本段选择的Clothing RefMod; hair_state=干燥; clothing_state=干燥、完整; pose=自然站立. 身份由Identity RefMod控制；人物不占Picture槽位。
<Subject 2> 是林晚晴 (CHAR_B); 约28岁的成年人，保持原面部和身材比例; 发型=整齐的黑发; wardrobe=AI-Video-Studio本段选择的Clothing RefMod; hair_state=干燥; clothing_state=干燥、完整; pose=自然站立. 身份由Identity RefMod控制；人物不占Picture槽位。
<Subject 3>: 夜晚客厅; 场景参考属于同一环境主体。

summary:
自然写实漫剧，稳定人物与室内光线
角色在固定客厅位置完成一问一答
spatial_state:
spatial_measurement: RELATIVE; confidence=UNKNOWN
area=主区域; scene_variant=主场景; 在场人数=2
顾言川 (CHAR_A): screen_position=左侧; depth=前景; facing=右侧; eyeline=林晚晴.
林晚晴 (CHAR_B): screen_position=右侧; depth=前景; facing=左侧; eyeline=顾言川.
顾言川、林晚晴: 相邻，保持已建立的相对间隔；未提供米制尺度
geometry.fixed_architecture.walls=矩形客厅；北墙固定
geometry.door_positions.ENTRY_DOOR=后方左侧
geometry.window_positions.WINDOW=后方右侧
geometry.furniture_positions.SOFA=位于角色右侧后方
geometry.furniture_positions.TABLE=前景中央
geometry.furniture_positions.CHAIR=左侧中景
geometry.entrance_positions.ENTRY_DOOR=后方左侧进场
geometry.exit_positions.ENTRY_DOOR=后方左侧离场
dialogue_group=顾言川、林晚晴
primary_listener=无; secondary_listeners=无

continuity_state:
incoming_state: SEG001_INCOMING
入态与本段声明的当前基线一致；无待补的状态变更。
current_state: SEG001_CURRENT
valid_until_changed=true; 以下基线在无明确事件时持续至5秒末。
当前无持有或登记道具。
door_states: ENTRY_DOOR=关闭
completed_actions: 无
completed_sounds: 无
end_state: SEG001_END
5秒末无状态变更，当前基线的全部字段继续有效。
from_previous: 只接续视觉运动，不继承已经结束的尾音。
to_next: 本段收尾。

camera_plan:
camera_side=南侧; dialogue_axis=东西方向锁定轴线
镜头从群像切为单人近景时，仅改变摄影机裁切、焦距与构图；角色在真实场景中的物理位置不发生变化。画外人物仍保持上一空间锚点中的原位置。
全段镜头共同设置：shot_scale=近景; lens=85mm; 规划摄影机高度=1.5m; camera_movement=固定摄影机; camera_angle=同轴线侧的侧前方反打; composition=当前说话人的面部与肩部可见，其他人仍在原位画外; lighting=窗侧柔光，室内补光，方向保持稳定; depth_of_field=浅景深但面部清晰
Shot 1 (SH001): 应用本段共同镜头设置。 剪切目的：呈现当前说话人的细微反应
Shot 2 (SH002): 应用本段共同镜头设置。 剪切目的：呈现当前说话人的细微反应

shot_timeline:
表演连续性：可见人物以轻微胸肩起伏保持安静呼吸，切镜延续呼吸和表情，不每次重新起拍。眼神目标遵守本镜站位与构图；按下列镜头表演，不强制每镜眨眼、不让多人同步眨眼。说话口型遵守原台词的发声语言与时间窗；听者不跟读。不可把呼吸变成新增喘息或叹气音效，不增加时长、位移或夸张脸部变形。
[Shot 1 | 0.000–2.500s]
人物表演 (SH001): 保持安静呼吸、自然眼睑张力和已建立的视线；停顿时可自然眨眼，不规定频率或新增情绪。嘴唇只随原台词活动，听者保持自然闭口。
SH001: 说话人轻微呼吸，视线保持指向听者
执行节拍：B001 (顾言川)
B001: 保持原位，说完短句
[Shot 2 | 2.500–5.000s]
人物表演 (SH002): 保持安静呼吸、自然眼睑张力和已建立的视线；停顿时可自然眨眼，不规定频率或新增情绪。嘴唇只随原台词活动，听者保持自然闭口。
SH002: 说话人轻微呼吸，视线保持指向听者
执行节拍：B002 (林晚晴)
B002: 保持原位，说完短句
表情自然克制，动作保持轻微；画外人物不移动。

dialogue_and_audio:
对白语言要求：标记为中文的原台词必须用普通话逐字说出，不翻译、不改写、不使用英文配音；口型对应中文发音，按原时间窗每句只说一次。人物名、时间码、语言标签及画面动作指令不得朗读，不新增旁白或对白。明确标记为其他语言的台词仍遵守各自语言。
B001 | 0.200–2.200s | 顾言川 | 克制、自然: <d>[Chinese] 你笑了？</d>
B002 | 2.700–4.500s | 林晚晴 | 克制、自然: <d>[Chinese] 没有。</d>
环境声：低声室内环境底声和轻微呼吸
non_diegetic_music=N/A

reference_map:
RefMod → <Subject 1>; identity=AI-Video-Studio Identity RefMod; wardrobe=shot-selected Clothing RefMod; character_picture=NONE.
RefMod → <Subject 2>; identity=AI-Video-Studio Identity RefMod; wardrobe=shot-selected Clothing RefMod; character_picture=NONE.
P1=SCN_LIVING_MASTER.png; <Picture 1> → <Subject 3>; asset_id=SCN_LIVING_MASTER; 控制固定建筑、门窗、家具与真实空间几何；不锁原图机位，剧情灯光/昼夜/天气优先。
Hidden LOCK: LOCK_SC01_A01; 提供稳定空间锚点，绝不计入正式5秒或最终成片。
continuation_source=LOCK_SC01_A01; tail_frames=22; fps=24; AddGuide.frame_idx=0; inherit_audio=false; 正式内容仍为完整5秒；生成142帧仅裁22帧重叠。

negative_rules:
禁止人物换脸、改变年龄、身份或身体比例。
禁止无剧情原因换衣、改变发型、湿发或干发状态。
禁止随机交换人物左右位置、近景传送、将画外人物重新安排到新位置。
禁止随机越轴、镜像翻转、道路左右反转。
禁止移动门窗、添加新门、删除固定家具或重新设计场景。
禁止道具凭空出现、消失、擅自换手或改变持有人。
禁止多手、额外手臂、肢体融合和手部变形；每人恰好两只手。
禁止重复已完成动作或重新播放已结束的声音事件。
禁止最后一秒随机变形、过度运动模糊、文字、水印；剧情文字只能严格复制绑定素材。
禁止自动加入背景音乐。

