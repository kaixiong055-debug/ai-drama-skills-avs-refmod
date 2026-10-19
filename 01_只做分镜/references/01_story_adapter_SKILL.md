---
name: ai-drama-story-adapter
description: 把小说或原始剧本改编为带原文Beat台账、因果与预算的故事数据；不决定镜头。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

把小说或原始剧本改编为带原文Beat台账、因果与预算的故事数据；不决定镜头。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

source。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

01_story.json。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 抽取全部原文及 Source Beat，标出关键因果、对白、保护细节与可合并内容。
2. 读取已确认预算；新改编使用目标180秒/上限240秒，短文可更短。
3. 按剧情事件规划，不机械一行一句占5秒；完整验证源Beat覆盖后冻结01。

## 关键硬规则

先完整读取源文本，登记source_beats。EXACT保留关键对白、动作、因果、人物关系、触发—反应—结果、剧情依赖次数；MERGE保留可合并信息；OMIT_OPTIONAL必须说明理由，不能省略核心剧情。按戏剧目标归组，不把每个微反应或长旁白短句扩成5秒空镜。短文可短，不凑180秒。预算不能以多集/分包重置。
选定的对白在Script冻结后下游不重译、不增删；英文版描述独立自然生成，对白原文和spoken_language作为演出合同保持一致。HIGH时间跳跃必须有明确桥接/画外时间窗；洗澡、换衣、做饭不作为5秒瞬间完成。预算超过上限返回改编；已有用户确认分镜按CONFIRMED预算不自动压缩。

V5.1 不把图片上观察到的相对关系编成米数。scene.spatial_measurement 默认 RELATIVE；METRIC 必须有用户尺寸、标注户型图、实际3D/CAD或可验证尺度等 provenance。相对布局只能用作投影/排序。规划器生成同一份双语 Canonical 数据，FULL 和 Runtime 均由确定性渲染器生成，禁止再让模型重写 Runtime。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
```

## Selftest

```text
python 01_story_adapter/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

核心Beat漏项、无理由删对白、预算超限、未解释的高强度状态跳跃、伪造尺寸。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。
