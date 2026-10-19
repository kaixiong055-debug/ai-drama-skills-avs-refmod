---
name: ai-drama-character-bible
description: 建立人物唯一身份、FACE4、BODY、服装家族与当前H3_RUNTIME引用。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

建立人物唯一身份、FACE4、BODY、服装家族与当前H3_RUNTIME引用。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

01_story.json。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

02_cast.json。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)、[资产依赖合同](../03_asset_bible/references/asset_dependencies.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 核实实际人物图、身份和每套衣服，按MASTER/FACE4/BODY/WARDROBE/RUNTIME登记。
2. 区分稳定身份、默认发型与可变化剧情状态；建立资产版本依赖。
3. 检查当前服装映射、2D/3D风格一致、实际图可用性后冻结02。

## 关键硬规则

每个主要人物分层登记：MASTER身份不与永久衣服绑定；FACE4为正面、两侧3/4、严格90°侧面且同人物/光线/背景；BODY锁身高肩宽腿长比例；每套WARDROBE独立服装结构；H3_RUNTIME为单人全身、面部可读、自然姿势、干净背景，融合身份/比例/当期服装。设计拼板不当H3运行主图。
cast独占姓名、身份、年龄感、身形、默认发型与服装家族定义；空间状态只保存当前wardrobe ID、wet/dry、衣服状态、pose。换衣需剧情原因与明确画外时间窗，不能切镜瞬换。未提供设计板但已有可用定妆图时登记existing_runtime_only及依据，不捏造素材。

V5.1 资产版本见 asset_dependencies 合同：MASTER 更新后 FACE4/BODY/WARDROBE/H3_RUNTIME 的派生版本链必须重新检查。每套 Runtime 的角色身份、MASTER 版本和当前 wardrobe 必须相符；不能把办公装与睡衣资产互换。未审核或旧包没有版本证据时保留 UNVERIFIED，不伪造已验证状态。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
```

## Selftest

```text
python 02_character_bible/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

身份/衣服不一致、缺当前Runtime、把设计拼板当人物主图、版本链不匹配。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。


## 人物 RefMod（V5.1.6）

用户要求 RefMod 或人物多角度一致性时，读取并执行[人物清晰度与 RefMod 接入规则](../02_character_bible/references/refmod_identity.md)。它约束真实资产、宿主接线和分层验收，不以提示词代替实际接入。
