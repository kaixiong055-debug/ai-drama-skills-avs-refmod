# 模型与运行依赖清单

这里只记录本机实现引用的文件，不下载模型，也不把权重装入 GitHub 或网盘代码包。来源取自插件 `model_setup.py` 及本机依赖仓库配置；链接可用性、未来版本和许可证应以来源页面为准。

| 用途 | ComfyUI 模型类别 | 本机文件名 | 是否必须 |
| --- | --- | --- | --- |
| 多参考视频 | diffusion_models | minimax_h3_ref2va_pruned_int8_convrot.safetensors | 当前 REF2VA 路线需要 |
| H3 文本编码 | text_encoders | qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors | H3 生成需要，不是独立生图模型 |
| 视频编码/RefMod | vae | minimax_h3_video_vae_fp16.safetensors | 人物参考准备与视频生成需要 |
| 音频编码 | vae | minimax_h3_audio_vae_fp32.safetensors | H3 音视频流程需要 |
| 4步参考生成加速 | loras | minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors | 随附4步空白模板启用；用户原始8步JSON未带此节点，按所选工作流核对 |
| 首帧视频 | diffusion_models | minimax_h3_fl2va_pruned_int8_convrot.safetensors | 选择首帧路线才需要 |
| latent 二采 | latent_upscale_models | minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors | 选择随附 latent ×2 二采时需要 |
| 像素放大 | upscale_models | RealESRGAN_x2plus.pth | 选择对应像素超分时需要 |

H3 文件来源：[Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)。latent 放大来源：[LBH-123-AI/Minimax_h3_latent_Upscaler](https://huggingface.co/LBH-123-AI/Minimax_h3_latent_Upscaler)。RealESRGAN 来源：[官方发布页](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.1)。这些是现有实现记录的来源，不是本次新推荐或重新下载指令。

现有共享模型目录可继续使用；C盘/E盘都可以存放权重，前提是实际配置在 ComfyUI 模型搜索路径中。移动磁盘位置不能增加显存。不要直接改写 Desktop 自动生成的模型路径配置。本机 E 盘可用空间约33.5GB，仅作为此前观测，打包不复制几十GB权重。

RefMod 依赖需提供 `MiniMaxH3RefModExtract`、`MiniMaxH3RefModBundleSave`、`MiniMaxH3RefModsLoader`、`MiniMaxH3RefModApply`。AVS 自带人物准备节点；视频由 ComfyUI 内置 H3 实现调度。空模板不使用 AICG3D、音色扩展或 SelfLift 的独立节点，其他自定义工作流如引用它们，应另外安装其依赖。

当前环境记录：ComfyUI 源码提交 `3541246a9c997f4b8c32f9f88f3c985d02021c79`；此前运行时报告 ComfyUI 0.40.0、Python 3.13.12、PyTorch 2.12.1+cu130、RTX 4060 Ti 8GB、约32GB内存。记录不等于锁定依赖或8GB生成成功证明。
