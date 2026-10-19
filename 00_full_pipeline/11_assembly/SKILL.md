---
name: ai-drama-assembly
description: 只选已验收的正式SEG，排除Hidden LOCK，按实际引导重叠帧数形成装配清单。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

只选已验收的正式SEG，排除Hidden LOCK，按实际引导重叠帧数形成装配清单。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

已验收Take台账。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

assembly_manifest.json。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 只从ledger选取已验收的完整SEG Take，排除所有LOCK。
2. 核实每段实际120/142帧与0/22引导裁切，保持5秒交付。
3. 写装配清单及来源，已接具体编码器才执行合成与实际成片复核。

## 关键硬规则

只按正式SEG顺序使用selected ACCEPTED完整段Take。Hidden LOCK完全排除。确认每段实际帧数和已裁引导窗口：142帧需裁22、120帧已处理需裁0；缺帧/窗口未核实不得READY_TO_ASSEMBLE。正式每段交付120帧/5秒，不能把22帧续写压进5秒导致缩短。无接入具体编码器时输出精确assembly_manifest，不宣称已输出视频。

V5.1 保持输出帧窗口核验与选中Take来源，LOCK永不入片。FULL、Runtime、Keyframe、回归报告都不能代替已验收的视频Take。回归里的某项漂移为0也不自动授予 Take ACCEPTED；需要完整QC证据。没有编码器时只输出装配清单，不宣称完成编码。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
```

## Selftest

```text
python 11_assembly/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

未验收/不完整Take、LOCK混入、帧数与裁切窗口未核实、输入视频缺失。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。
