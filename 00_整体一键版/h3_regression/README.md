# 真实 H3 回归登记

当前15例×A/B/C共45个实验全部NOT_RUN，八项指标全null。没有推理、视频或人工评估证据，不能填0、PASS或声称更稳定。tests里的模拟probe只测登记逻辑，不是实机结果。

cases/R01–R15定义场景。A使用保留V5.0 Runtime（原包导出的完整运行Prompt）且关闭Hidden LOCK；B使用相同V5.0 Prompt并启用LOCK；C使用V5.1 Runtime并启用LOCK。A为实验性无LOCK对照，不能通过删除生产包LOCK绕过正式V5.1门；在独立实验工作流生成并保留对应真实ledger。R15用于突出A与B/C的无LOCK对照。三个variant共享剧本、人物素材、正式镜头、模型、workflow、分辨率、steps、seed；只有Prompt版本/LOCK为实验变量。

每例protocol记录参与人数、实际执行步骤和专项观察点，R01/R11/R12/R13/R15指定至少3个连续正式段，R02指定8轮完整问答。`scenario_review=NOT_RUN`表示这些场景要求尚未由真实视频逐项复核；登记一段不能修改该字段来冒充场景已验收。

先按场景完整拍完需要的连续段/对白轮次，再逐段登记并以comparison_id配对（例如R01_scene01_seg02_seed17）；病例指标从这些有证据条目统计，不能用一个已测片段冒充整条连续性场景已测。八指标是观察错误率[0,1]，必须说明审查方法、样本分母与时间戳证据；null表示未评估，0仅在实际审查无该错误时填写。整体case的metrics保留null，避免把不同实验条件混成单个得分；数据位于各variant的runs，variant.metrics是最新条目快照。

安装系统ffprobe后，复制record_template.json并填写真实值。先在原production的generation_ledger.json保存真实Take和model/model_version/workflow/resolution（[宽,高]）/steps/seed/prompt_version/hidden_lock/continuation/reference_assets/runtime_seconds/output_file；不得从模板生成假参数。登记脚本要求参数与既有Take逐项一致，检查非空文件、ffprobe可读视频与实际分辨率，保存SHA256及双向ledger链接。该检查证明有视频，画面质量仍由evidence中的实际审查负责。

```text
python scripts/register_h3_regression.py init --output regression_runs.json
python scripts/register_h3_regression.py validate --manifest regression_runs.json
python scripts/register_h3_regression.py register --manifest regression_runs.json --ledger production/generation_ledger.json --record real_result.json
python scripts/register_h3_regression.py compare --manifest regression_runs.json --output comparison.json
```

未跑结果为NOT_RUN；登记后为RECORDED，部分病例为PARTIAL，各variant有记录为COMPLETED（登记覆盖状态，不等于画面验收或完整场景已满足）。比较器只对同comparison_id、同模型/版本/workflow/分辨率/steps/seed/参考资产的A/B/C计算差值；不齐为INCOMPLETE，控制变量不同为CONTROL_MISMATCH，不输出可比差值。需要多个种子和完整场景人工确认才能得出稳健性结论。

V5.0基线原包保存在 `legacy/V5.0_original.zip`。V5.1任务自动登记 `scenario_signature`（冻结Beat和正式分镜的SHA256），A/B旧ledger可用 `engine.regression.scenario_signature(project)` 计算并补记真实基线值；对照必须一致。比较也检查实际视频时长（1ms容差），故事或时长不同显示CONTROL_MISMATCH，不能当作Prompt效果差异。
