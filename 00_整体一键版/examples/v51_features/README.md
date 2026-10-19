# V5.1 资产依赖与关键帧工程示例

这里的所有 PNG 都由测试工具创建为单色小图，**不是人物、场景或关键帧的真实生产图**。资产 `VALID` 仅表示此合成样例声明的版本依赖一致，图片语义内容仍为 `UNVERIFIED`，真实 H3 Regression 为 `NOT_RUN`。不要把本例当作视频稳定性的实测证据。

在包根执行：

```powershell
python -m examples.fixtures_v51 --output examples/v51_features/input
python one_click.py export --input examples/v51_features/input/project_input.json --asset-root examples/v51_features/input/assets --output examples/v51_features/production
python scripts/validate_asset_dependencies.py examples/v51_features/production
```

如 `production` 已存在且非空，请选择一个新的输出目录；导出器不会覆盖已有完整包。

本例包含人物 `MASTER → FACE4 → BODY → WARDROBE → H3_RUNTIME`，Runtime 同时显式依赖对应身份 MASTER；场景 `MASTER → ENTRY AREA`；道具 `MASTER → OPEN / CLOSED`。当前人物右手持续持有关闭的行李箱，门保持半开。第一正式镜头绑定 `SHOT_KEYFRAME`，单独 Hidden LOCK 仅使用 `SPATIAL_ANCHOR_KEYFRAME`，两者均不能覆盖人物身份、当前服装与 Scene MASTER 几何。其他简单近景在 AUTO 策略下无需额外图片。

验证版本更新：在输入 JSON 中只把 `CHAR_A_MASTER.version` 从 3 改为 4，保留下游原来的 `source_versions`。重新执行资产依赖 validator 会显示 FACE4、BODY、WARDROBE、Runtime 及依赖它们的关键帧为 `STALE`。输入阶段没有 Picture 绑定，因此报告可以列出 STALE 而不把未绑定资产当成生产错误；再次导出时实际绑定 STALE Runtime 会被 READY Gate 拒绝。只有显式设置 `project.allow_stale_asset=true` 才能以警告方式继续；缺失资产、错误身份/服装依赖及图结构错误仍然失败。

真实项目应替换成已审阅的真实图片、真实版本和生成来源；没有来源记录的旧资产会保留为 `UNVERIFIED`，不会自动补出虚假的生成历史。本例不提供虚构的物理尺寸，普通图像空间默认 RELATIVE。
