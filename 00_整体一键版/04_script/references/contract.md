# ai-drama-script · V5.1

输入：story + cast + assets

输出：04_script.json

仅保存scene_id、时间、参与人物、Action Beat、Dialogue Beat、情绪、剧情因果、道具剧情状态与原文映射。禁止lens、close-up、camera height、push-in、screen-left/right、机位、运镜等摄影字段。剧情入退场/拿放事件是因果；具体投影坐标、镜头与秒级执行移交Storyboard。
每句对白为独立Beat/occurrence；确需重复相同句子时不同source occurrence。中文默认3.5字/秒，悬疑3.0、快语4.0；≤4.2秒常规，4.2–4.6只允许近静态，>4.6压缩非关键对白或在总预算内拆段。默认最多5个短句，极短单字回应且估时PASS可例外。问答链不能无因果拆断，不靠加速解决。

## V5.1 增强合同

V5.1 保持 Script / Storyboard 的字段边界。关键对白不因 Runtime 字数预算被删减，原话、语言、先后顺序和出现次数由同一 Beat 合同控制。已有计数动作、声音窗口与道具原因仍由事件数据驱动，不能在 Prompt 临时猜测补写。
