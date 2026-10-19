# ai-drama-generation · V5.1

输入：完整验证通过的生产包

输出：generation_ledger.json + generation_jobs.json

jobs按LOCK→SEG依赖排队，默认TAKE01，重试TAKE02/03…；调用模型前使用完整已验证Prompt与精确Picture，正式生成包含22帧引导时补偿帧预算。当前工具仅准备任务，不发起付费视频任务。
每个Take记录generation_id、segment_id、shot_id（完整SEG可null）、shot_ids、take_id、prompt_version（版本+内容hash）、model、mode、picture_bindings、spatial_anchor、continuation_source、output、status、结构化reject_reason。未生成不得伪造output或ACCEPTED。已有Take保留，不能覆写同一ID。

## V5.1 增强合同

V5.1 jobs 从已验证 H3_RUNTIME_CN/EN 构造任务，prompt_version=5.1:内容hash；不再把 FULL 的重复全文当成默认生成输入。Take 增加 model_version、workflow、resolution、steps、seed、hidden_lock、continuation、reference_assets、runtime_seconds、output_file；未获知字段写 null，不能填假参数。真实回归登记必须字段完整且与 ledger 一致，读取实际可解码视频并保存 hash、审查证据和 case/variant/comparison_id 链接。
