# ai-drama-assembly · V5.1

输入：已验收Take台账

输出：assembly_manifest.json

只按正式SEG顺序使用selected ACCEPTED完整段Take。Hidden LOCK完全排除。确认每段实际帧数和已裁引导窗口：142帧需裁22、120帧已处理需裁0；缺帧/窗口未核实不得READY_TO_ASSEMBLE。正式每段交付120帧/5秒，不能把22帧续写压进5秒导致缩短。无接入具体编码器时输出精确assembly_manifest，不宣称已输出视频。

## V5.1 增强合同

V5.1 保持输出帧窗口核验与选中Take来源，LOCK永不入片。FULL、Runtime、Keyframe、回归报告都不能代替已验收的视频Take。回归里的某项漂移为0也不自动授予 Take ACCEPTED；需要完整QC证据。没有编码器时只输出装配清单，不宣称完成编码。
