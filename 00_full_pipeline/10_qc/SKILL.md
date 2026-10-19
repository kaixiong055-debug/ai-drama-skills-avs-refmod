---
name: ai-drama-qc
description: 校验生产包、记录真实视频Take的结构化拒绝原因与证据，空间漂移回流LOCK重建。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

校验生产包、记录真实视频Take的结构化拒绝原因与证据，空间漂移回流LOCK重建。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

生产包与真实生成结果。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

production_review.json + Take QC。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)、[真实回归登记](../h3_regression/README.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 先执行全部数据与Prompt确定性检查，核实 READY 含义。
2. 对实际素材和视频逐镜审查身份、空间、道具、手部、声音与末帧，记录证据。
3. 结构化拒绝或验收Take；空间漂移回状态/LOCK重建；登记真实回归指标。

## 关键硬规则

先运行schema、Script/Storyboard/state replay/Picture/双语MD验证；FAIL不能READY。再查看实际图片、逐帧视频，记录具体证据，不把结构PASS称为成片验收。
拒绝原因固定：IDENTITY_DRIFT、FACE_DRIFT、COSTUME_DRIFT、POSITION_DRIFT、LEFT_RIGHT_SWAP、AXIS_FLIP、EYELINE_ERROR、SCENE_GEOMETRY_DRIFT、PROP_DISAPPEAR、PROP_SPAWN、HAND_DEFORMATION、EXTRA_LIMB、ACTION_NOT_COMPLETED、ACTION_REPEATED、SOUND_REPEATED、END_FRAME_DEFORMATION、MOTION_BLUR_EXCESSIVE。
空间类拒绝回到新的输出包重建对应Hidden LOCK；身份/道具/声音问题修对应权威数据/素材/执行，不以再加长Prompt掩盖。ACCEPTED必须有qc_evidence，拒绝Take不能装配。

V5.1 结构审查增加 Runtime 冗余/矛盾、资产依赖、测量来源、Keyframe权限、pipeline_graph、FULL/Runtime双语同源校验。h3_regression/R01–R15 每例 A/B/C：A=V5.0无LOCK，B=V5.0有LOCK，C=V5.1有LOCK。无视频时 status=NOT_RUN、八指标全null；不能填0或声称PASS。真实结果只能通过有证据登记形成 RECORDED/PARTIAL/COMPLETED，结构PASS不代表模型质量。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
```

## Selftest

```text
python 10_qc/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

结构失败仍READY、无证据ACCEPTED、无实际视频填真实回归0/PASS、拒绝原因未结构化。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。


## 人物 RefMod（V5.1.6）

用户要求 RefMod 或人物多角度一致性时，读取并执行[人物清晰度与 RefMod 接入规则](../02_character_bible/references/refmod_identity.md)。它约束真实资产、宿主接线和分层验收，不以提示词代替实际接入。
