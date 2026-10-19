---
name: ai-drama-script
description: 冻结剧情Action Beat、Dialogue Beat、情绪、因果与剧情道具状态，禁止摄影字段。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

冻结剧情Action Beat、Dialogue Beat、情绪、因果与剧情道具状态，禁止摄影字段。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

story + cast + assets。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

04_script.json。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 读取故事、人物、素材的已冻结语义。
2. 用唯一Beat登记对白原文、动作、情绪、原因、道具状态与source映射。
3. 按真实语速/窗口检查容量及计数，拒绝摄影字段后冻结04。

## 关键硬规则

仅保存scene_id、时间、参与人物、Action Beat、Dialogue Beat、情绪、剧情因果、道具剧情状态与原文映射。禁止lens、close-up、camera height、push-in、screen-left/right、机位、运镜等摄影字段。剧情入退场/拿放事件是因果；具体投影坐标、镜头与秒级执行移交Storyboard。
每句对白为独立Beat/occurrence；确需重复相同句子时不同source occurrence。中文默认3.5字/秒，悬疑3.0、快语4.0；≤4.2秒常规，4.2–4.6只允许近静态，>4.6压缩非关键对白或在总预算内拆段。默认最多5个短句，极短单字回应且估时PASS可例外。问答链不能无因果拆断，不靠加速解决。

V5.1 保持 Script / Storyboard 的字段边界。关键对白不因 Runtime 字数预算被删减，原话、语言、先后顺序和出现次数由同一 Beat 合同控制。已有计数动作、声音窗口与道具原因仍由事件数据驱动，不能在 Prompt 临时猜测补写。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
```

## Selftest

```text
python 04_script/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

Script含镜头字段、重复/漏Beat、对白超过真实窗口、声音动作次数或因果不明确。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。
