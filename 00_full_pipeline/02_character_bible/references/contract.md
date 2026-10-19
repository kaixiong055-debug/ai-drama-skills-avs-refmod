# ai-drama-character-bible · V5.1

输入：01_story.json

输出：02_cast.json

每个主要人物分层登记：MASTER身份不与永久衣服绑定；FACE4为正面、两侧3/4、严格90°侧面且同人物/光线/背景；BODY锁身高肩宽腿长比例；每套WARDROBE独立服装结构；H3_RUNTIME为单人全身、面部可读、自然姿势、干净背景，融合身份/比例/当期服装。设计拼板不当H3运行主图。
cast独占姓名、身份、年龄感、身形、默认发型与服装家族定义；空间状态只保存当前wardrobe ID、wet/dry、衣服状态、pose。换衣需剧情原因与明确画外时间窗，不能切镜瞬换。未提供设计板但已有可用定妆图时登记existing_runtime_only及依据，不捏造素材。

## V5.1 增强合同

V5.1 资产版本见 asset_dependencies 合同：MASTER 更新后 FACE4/BODY/WARDROBE/H3_RUNTIME 的派生版本链必须重新检查。每套 Runtime 的角色身份、MASTER 版本和当前 wardrobe 必须相符；不能把办公装与睡衣资产互换。未审核或旧包没有版本证据时保留 UNVERIFIED，不伪造已验证状态。
