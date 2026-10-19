---
name: ai-drama-generation
description: 准备H3生成任务、AddGuide依赖、Take编号及不可变提示词版本台账；不自动提交视频。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

准备H3生成任务、AddGuide依赖、Take编号及不可变提示词版本台账；不自动提交视频。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

完整验证通过的生产包。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

generation_ledger.json + generation_jobs.json。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)、[真实回归登记](../h3_regression/README.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 运行完整生产包验证后，用Runtime生成按LOCK→SEG依赖排序的任务。
2. 实际模型完成后记录真实参数/耗时/视频路径和不可复用的generation_id/take_id。
3. 保留失败/重试记录；真实A/B/C回归额外运行证据登记，不自动提交生成。

## 关键硬规则

jobs按LOCK→SEG依赖排队，默认TAKE01，重试TAKE02/03…；调用模型前使用完整已验证Prompt与精确Picture，正式生成包含22帧引导时补偿帧预算。当前工具仅准备任务，不发起付费视频任务。
每个Take记录generation_id、segment_id、shot_id（完整SEG可null）、shot_ids、take_id、prompt_version（版本+内容hash）、model、mode、picture_bindings、spatial_anchor、continuation_source、output、status、结构化reject_reason。未生成不得伪造output或ACCEPTED。已有Take保留，不能覆写同一ID。

V5.1 jobs 从已验证 H3_RUNTIME_CN/EN 构造任务，prompt_version=5.1:内容hash；不再把 FULL 的重复全文当成默认生成输入。Take 增加 model_version、workflow、resolution、steps、seed、hidden_lock、continuation、reference_assets、runtime_seconds、output_file；未获知字段写 null，不能填假参数。真实回归登记必须字段完整且与 ledger 一致，读取实际可解码视频并保存 hash、审查证据和 case/variant/comparison_id 链接。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
```

## Selftest

```text
python 09_generation/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

Prompt版本不匹配、TakeID重复、伪造模型参数或视频文件、把PENDING当GENERATED/ACCEPTED。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。
