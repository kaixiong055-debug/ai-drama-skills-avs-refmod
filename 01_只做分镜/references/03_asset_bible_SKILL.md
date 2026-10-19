---
name: ai-drama-asset-bible
description: 维护MASTER、AREA、场景家族、道具、Transition与文字资产职责，复用真实素材。
metadata:
  version: "5.1"
---

## 用户交付规则（V5.1.6）

英文描述与对白语言分开：中文台词必须明确以普通话逐字说出，禁止翻译成英文配音或朗读提示词；无对白片段不新增说话。英文H3最终文件保留中文段头和导入字段。

按[用户交付边界](../00_router/references/user_delivery.md)执行。本层JSON、校验、运行与中间视图仅存内部工程；最终用户资料中不得出现JSON或重复H3文件。用 `engine.delivery` 白名单导出用户资料，不打包整个工程。


## 目的

维护MASTER、AREA、场景家族、道具、Transition与文字资产职责，复用真实素材。 沿用V5.0完整生产链，只增强当前层职责。

## 输入

01_story.json + 02_cast.json。上游信息已冻结时复用，不由下游另猜人物、剧情、尺寸或文件。

## 输出

03_assets.json。JSON是字段所有者，Markdown/导演视图是确定性输出，不是第二套可写状态。

## 必读 references

读取[本层合同](references/contract.md)、[字段所有权](../00_router/references/canonical_chain.md)、[历史细则索引](../00_router/references/retained_rules_index.md)、[资产依赖合同](../03_asset_bible/references/asset_dependencies.md)。根据实际任务查阅本层 retained_details.json（若存在），保留更细且不冲突的技巧；历史确认流程、旧单镜默认、旧六字段限制不能覆盖用户已授权任务与V5.1合同。执行依赖只以[pipeline_graph.json](../pipeline_graph.json)为准，目录数字不是先后顺序。

## 核心执行顺序

1. 扫描全素材目录并逐图核实角色/场景/道具职责与真实文件。
2. 固定MASTER几何，再按实际交互需要建AREA、Transition、道具状态与文字资产。
3. 登记版本图并传播过期状态，检查Scene Family≤9与路径/图片解码后冻结03。

## 关键硬规则

MASTER负责长期建筑、装修、固定几何与基础光线；SHEET4/9只负责同空间不同机位的理解，一张拼板算一个图片文件；AREA仅在固定设施局部几何不可由MASTER充分表达且镜头依赖时建立。每个Scene Family最多9个图片文件；C级1–2、B级3–5、A级6–9为规划倾向。超限先复用/合并SHEET/删低频区域，不删核心MASTER，不因天气昼夜重造装修；真正独立空间才能拆家族。
洗衣取衣需要MASTER+LAUNDRY_AREA；纯画外门铃不触发ENTRY AREA。门槛卡箱、开冰箱、沙发起身等依赖设施时注册局部AREA。AREA继承MASTER的门窗柜体及第二锚点方向，不锁某一镜头焦距/人物站位。
道具只为剧情长期外观/尺度/交互需要注册。默认authorized_support_objects=[]；不擅加衣架、衣篮、夹子、托盘、推车。跨段包/手机/钥匙应有PROP资产。
Transition锁门框、方向、开合轴和内外两侧，门内外分别有MASTER；缺任一必需连接参考不得READY。
需要准确可读的门牌、工牌、纸箱字、手机界面、时钟数值绑定专用素材；不要求可读时明确不可依赖临时文字，不为文字堆图。正式Storyboard仅在必要基础素材READY后绘制；参考视频截图只解析动作节奏/攻防因果，不作身份或正式板。板负责构图/动作阶段/武器轨迹，不复制板中人物身份。

V5.1 每个资产支持 version、derived_from、source_versions、generated_from_version、status（VALID/STALE/MISSING/UNVERIFIED）。MASTER 变化沿依赖图传播 STALE；Scene AREA 和 Prop 状态变体同样处理。依赖丢失、环或错版本由 validate_asset_dependencies 拦截；绑定 STALE 默认阻止 READY，只有明确记录用户 allow_stale_asset=true 才允许该例外，不能自动替用户开启。

## Validator

在包根运行，FAIL必须回到对应权威字段修复并重编译，不直接修Markdown掩盖问题：

```text
python one_click.py validate --project production
python scripts/validate_asset_dependencies.py production
```

## Selftest

```text
python 03_asset_bible/tests/selftest.py
python one_click.py selftest
```

本层 examples、tests 与共享 engine 一并交付，禁止只复制 SKILL.md。自动测试的PASS只描述结构/逻辑；没有H3视频则真实回归仍为NOT_RUN。

## 失败条件

参考缺失/歧义、依赖环或未知源、STALE生产绑定、必要AREA/PROP缺失、Scene Family超9。 失败必须保留具体字段、ID和证据；不得生成假的READY、图片验证或视频验收状态。


## 人物 RefMod（V5.1.6）

用户要求 RefMod 或人物多角度一致性时，读取并执行[人物清晰度与 RefMod 接入规则](../02_character_bible/references/refmod_identity.md)。它约束真实资产、宿主接线和分层验收，不以提示词代替实际接入。
