---
name: ai-drama-spatial-lock
description: 维护2至5人空间状态机及隐藏LOCK，阻止近景重排、换边、越轴与续写断裂。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

维护2至5人空间状态机及隐藏LOCK，阻止近景重排、换边、越轴与续写断裂。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

06_production.json。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

07_spatial_locks.json。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 读取上一末态与当前before_events，按事件演算入态/当前/末态并保留历史。
2. 核验相对/实际尺寸来源，构建左右/深度/视线/固定几何和持有关系。
3. 检测失效原因；仅需要时建独立LOCK及尾22帧续写源；正式段仍5秒。

## 关键硬规则

states表唯一保存世界状态；production只持state_id，不复制可写状态。每Scene记录variant、anchor_version、角色布局坐标、测量来源与投影左右顺序、depth、distance、facing、eyelines、dialogue_axis、camera_side、entry/exit、props、architecture、doors/windows/furniture与valid_until_changed。角色画外仍在场。completed_actions/sounds跨场景保留，衣服和携带物不因换场重置。
LOCK独立LOCK_SCxx_Axx，0.8–1.5秒，默认1秒，include_in_final=false，不占SEG、不吃正式5秒。固定群像，尽量所有在场者可见；只呼吸、微表情/头部/视线。无关键对白、剧情、走位交叉、快速摄影、越轴。
新Scene、进场、退场重构、明显换位、正式跨轴、主对话群改变、跨AREA、近景继承不可靠、Review漂移触发；只有实际失效才重LOCK，同场稳定三段只建一次。主说话人临时改变≠主群结构重组，避免每轮对白重LOCK。
LOCK尾22帧/latent→AddGuide frame_idx=0→正式完整5秒；后续SEG从上一SEG尾22帧。在24fps时引导重叠约22/24秒；请求142帧、交付120帧或由已验证工作台完成补偿，不能重复补偿/裁切。实测引导能力仍以目标工作台/模型为准。

V5.1 spatial_measurement=RELATIVE/METRIC/UNKNOWN，普通图片默认 RELATIVE。旧 x_m/y_m 字段可保留内部布局兼容，但 RELATIVE 下只是无单位排序坐标，不输出米或计算伪精确物理距离。METRIC 必须有 provenance.source_type、source_id、evidence；允许 USER_SPECIFIED、DIMENSIONED_FLOORPLAN、BLENDER_3D、CAD、VERIFIABLE_SCALE、CANONICAL_SCENE。可验证尺寸以 constraints 的 subject_id/reference_id/distance_m 保存。不得把相对布局自动升级为 METRIC。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
```

## Selftest

```text
python 07_spatial_lock/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

无依据的METRIC、瞬移/换手/换衣、无效锚点、LOCK混入SEG或正式5秒、历史声音重播。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。
