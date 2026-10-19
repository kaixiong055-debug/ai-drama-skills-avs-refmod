# ai-drama-asset-bible · V5.1

输入：01_story.json + 02_cast.json

输出：03_assets.json

MASTER负责长期建筑、装修、固定几何与基础光线；SHEET4/9只负责同空间不同机位的理解，一张拼板算一个图片文件；AREA仅在固定设施局部几何不可由MASTER充分表达且镜头依赖时建立。每个Scene Family最多9个图片文件；C级1–2、B级3–5、A级6–9为规划倾向。超限先复用/合并SHEET/删低频区域，不删核心MASTER，不因天气昼夜重造装修；真正独立空间才能拆家族。
洗衣取衣需要MASTER+LAUNDRY_AREA；纯画外门铃不触发ENTRY AREA。门槛卡箱、开冰箱、沙发起身等依赖设施时注册局部AREA。AREA继承MASTER的门窗柜体及第二锚点方向，不锁某一镜头焦距/人物站位。
道具只为剧情长期外观/尺度/交互需要注册。默认authorized_support_objects=[]；不擅加衣架、衣篮、夹子、托盘、推车。跨段包/手机/钥匙应有PROP资产。
Transition锁门框、方向、开合轴和内外两侧，门内外分别有MASTER；缺任一必需连接参考不得READY。
需要准确可读的门牌、工牌、纸箱字、手机界面、时钟数值绑定专用素材；不要求可读时明确不可依赖临时文字，不为文字堆图。正式Storyboard仅在必要基础素材READY后绘制；参考视频截图只解析动作节奏/攻防因果，不作身份或正式板。板负责构图/动作阶段/武器轨迹，不复制板中人物身份。

## V5.1 增强合同

V5.1 每个资产支持 version、derived_from、source_versions、generated_from_version、status（VALID/STALE/MISSING/UNVERIFIED）。MASTER 变化沿依赖图传播 STALE；Scene AREA 和 Prop 状态变体同样处理。依赖丢失、环或错版本由 validate_asset_dependencies 拦截；绑定 STALE 默认阻止 READY，只有明确记录用户 allow_stale_asset=true 才允许该例外，不能自动替用户开启。
