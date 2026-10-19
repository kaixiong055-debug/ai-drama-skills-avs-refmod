from __future__ import annotations

import os
import json
import random
import re
import logging
import time
from pathlib import Path
from typing import Any

import folder_paths

from .portrait import save_video, finish_video, save_latent, load_latent, neural_latent_upscale
from .model_setup import check_project, check_studio, model_state
from .model_runtime import current_session, model_session, run_stage, unload
from .character_refmod import apply_character_refmods
from .character_store import bind_shot

from .nodes import (
    MANAGER,
    _compile_resource_references,
    _avs_load_image_tensor,
    _avs_load_video_frames,
    _avs_load_audio,
    _avs_node_result,
    _avs_resolution,
    _avs_snap_h3_length,
)


def _files(kind: str) -> list[str]:
    try:
        return list(folder_paths.get_filename_list(kind))
    except Exception:
        return []


def _pick(items: list[str], includes: tuple[str, ...], excludes: tuple[str, ...] = ()) -> str:
    if not items:
        return ""
    scored = []
    for item in items:
        low = item.lower()
        score = sum(3 for x in includes if x in low) - sum(6 for x in excludes if x in low)
        scored.append((score, len(item), item))
    scored.sort(key=lambda x: (-x[0], x[1], x[2].lower()))
    return scored[0][2] if scored and scored[0][0] > 0 else items[0]


def _model_options(kind: str, auto_label: str = "自动检测") -> list[str]:
    return [auto_label] + _files(kind)


def _resolve_auto(choice: str, kind: str, includes: tuple[str, ...], excludes: tuple[str, ...] = ()) -> str:
    if choice and choice not in {"自动检测", "Auto Detect"}:
        return choice
    items = _files(kind)
    result = _pick(items, includes, excludes)
    if not result:
        raise ValueError(f"没有在 ComfyUI/models 中找到可用的 {kind} 模型。")
    return result


def _uses_reference(project, resources):
    mode = project.get("generation_mode", "自动")
    if mode == "首帧图生视频":
        if not resources.get("images"):
            raise ValueError("首帧图生视频需要在 Picture 槽位绑定一张完整镜头图片，并在提示词中引用它。")
        if resources.get("videos") or resources.get("audios"):
            raise ValueError("首帧模式不能使用视频/音频参考，请改为多素材参考模式。")
        return False
    return mode == "多素材参考" or bool(resources.get("images") or resources.get("videos") or resources.get("audios"))


def _resolve_h3_model(project, use_ref):
    task = "ref2va" if use_ref else "fl2va"
    choice = project.get(f"{task}_model", "自动检测")
    if choice in {None, "", "自动检测", "Auto Detect"}:
        candidates = [name for name in _files("diffusion_models") if "h3" in name.lower() and task in name.lower()]
        if not candidates:
            if use_ref:
                raise ValueError("没有找到 H3 REF2VA 模型。当前多素材参考任务需要 REF2VA，不能使用 FL2VA 替代。"
                                 "本机只有 FL2VA 时，请导入 AI_Video_Studio_本地8GB_快速首帧人脸1080P.json，"
                                 "使用一张清晰完整首帧；晨羽多素材版需要安装 REF2VA 后使用。")
            raise ValueError("没有找到 H3 FL2VA 模型。首帧图生视频需要 FL2VA，请检查 models/diffusion_models。")
        return _pick(candidates, ("minimax", "h3", task, "pruned"))
    low = str(choice).lower()
    other = "fl2va" if use_ref else "ref2va"
    if other in low and task not in low:
        raise ValueError(f"当前任务需要 {task.upper()}，但选择的是 {choice}。请更换模型或生成模式。")
    return choice


def _wait_for_models(plan, outputs, unique_id=None, scope="当前视频段"):
    from comfy_execution.graph import ExecutionBlocker
    payload = {**plan, "node_id": str(unique_id or ""), "scope": scope, "status": "待下载模型"}
    return {"ui": {"avs_model_setup": [payload]},
            "result": tuple(ExecutionBlocker(None) for _ in range(outputs))}


def _clean_at_refs(text: str) -> str:
    return " ".join(x for x in re.split(r"[\s,，;；]+", str(text or "").strip()) if x)


def _join_refs(*values: str) -> str:
    parts: list[str] = []
    seen = set()
    for value in values:
        for part in _clean_at_refs(value).split():
            if part and part not in seen:
                seen.add(part)
                parts.append(part)
    return " ".join(parts)


def _selected_mapping_block(ctx: dict[str, Any]) -> str:
    compiled = str(ctx.get("prompt_compiled", "") or "")
    marker = "【镜头提示词】"
    if marker in compiled:
        return compiled.split(marker, 1)[0].strip()
    return ""


def _project_summary(project: dict[str, Any], language: str) -> str:
    if language == "English":
        return (
            f"Project: {project['project_name']}\n"
            f"Type: {project['project_type']} | Style: {project['visual_style'] or 'Default'}\n"
            f"Output: {project['resolution']} {project['aspect_ratio']} | default {project['default_seconds']:.1f}s\n"
            f"Quality: {project['quality_preset']} | Audio: {project['audio_mode']}"
        )
    return (
        f"项目：{project['project_name']}\n"
        f"类型：{project['project_type']}｜风格：{project['visual_style'] or '默认'}\n"
        f"输出：{project['resolution']}｜{project['aspect_ratio']}｜默认 {project['default_seconds']:.1f} 秒\n"
        f"质量：{project['quality_preset']}｜声音：{project['audio_mode']}"
    )


def _build_director_prompt(project: dict[str, Any], shot: dict[str, Any], resource_ctx: dict[str, Any]) -> str:
    no_music = project.get("audio_mode") == "环境音（无配乐）"
    silent = project.get("audio_mode") == "完全静音"
    continuity = bool(shot.get("use_previous_video"))
    lines: list[str] = []
    mapping = _selected_mapping_block(resource_ctx)
    if mapping:
        lines.append(mapping)
        lines.append("")

    lines.extend([
        "【全局导演总控】",
        f"项目：{project.get('project_name', '未命名项目')}。",
        f"类型：{project.get('project_type', '短剧')}。",
        f"统一视觉风格：{project.get('visual_style') or '自然、电影级、画面稳定、主体清晰'}。",
        f"一致性要求：{project.get('consistency', '强')}；角色身份、脸部、发型、服装、场景结构与空间关系保持一致。",
        "",
        f"【第{shot.get('shot_number', 1)}镜｜{shot.get('shot_name') or '未命名镜头'}】",
        f"剧情目的：{shot.get('story_goal') or '清晰完成当前镜头叙事任务'}。",
        f"人物/主体：{shot.get('character_refs') or project.get('default_character_refs') or '按资源引用'}。",
        f"场景：{shot.get('scene_refs') or project.get('default_scene_refs') or '按资源引用'}。",
        f"起始状态：{shot.get('start_state') or '自然承接当前状态'}。",
        f"主要动作：{shot.get('action') or '按当前剧情自然行动'}。",
        f"情绪与表演：{shot.get('emotion') or '自然、克制、符合剧情'}。",
        f"结束状态：{shot.get('end_state') or '保留清晰结束姿态，方便下一镜衔接'}。",
        "",
        "【摄影】",
        f"景别：{shot.get('shot_size', '全景')}。",
        f"机位：{shot.get('camera_angle', '正面')}。",
        f"运镜：{shot.get('camera_move', '固定')}。",
        "保持动作方向、人物左右位置与视线关系清楚，不无理由越轴，不突然改变空间位置。",
    ])

    if continuity:
        lines.extend([
            "",
            "【连续性】",
            "严格承接上一镜结尾画面与运动趋势。上一镜尾部引导帧优先决定本镜头的起始姿势、人物位置、运动方向与摄影机连续性。",
            "禁止重新站定，禁止从静态参考图重置动作，禁止瞬移、换位或突然改变朝向。",
        ])
    else:
        lines.extend(["", "【连续性】", "本镜头为独立起始镜头，不需要承接上一段视频。"])

    if shot.get("dialogue"):
        lines.extend(["", "【对白】", str(shot.get("dialogue"))])
    if shot.get("sound_notes"):
        lines.extend(["", "【声音设计】", str(shot.get("sound_notes"))])
    if no_music:
        lines.extend(["", "【声音总控】", "禁止任何背景音乐、配乐或旋律。只保留对白、环境音、脚步、衣料、动作、武器、呼吸等符合画面的原生声音。"])
    elif silent:
        lines.extend(["", "【声音总控】", "最终输出静音视频。"])
    else:
        lines.extend(["", "【声音总控】", "声音自然匹配画面，不要出现与画面无关的音效。"])

    if shot.get("extra_prompt"):
        lines.extend(["", "【导演补充】", str(shot.get("extra_prompt"))])

    lines.extend([
        "",
        "【生成限制】",
        "人物数量正确；避免额外人物、额外肢体、手指异常、五官漂移、服装突变、场景突变、动作断裂、闪烁、重影与明显形变。",
    ])
    return "\n".join(lines).strip()


class AVSProjectDirector:
    @classmethod
    def INPUT_TYPES(cls):
        diffusion = _model_options("diffusion_models")
        clips = _model_options("text_encoders")
        vaes = _model_options("vae")
        loras = ["不使用"] + _files("loras")
        return {
            "required": {
                "resource_db": ("AVS_RESOURCE_DB",),
                "language": (["中文", "English"], {"default": "中文"}),
                "project_name": ("STRING", {"default": "我的AI视频项目"}),
                "project_type": (["短剧", "漫剧", "舞蹈", "打斗", "广告", "其他"], {"default": "短剧"}),
                "visual_style": ("STRING", {"default": "电影级画面，主体清晰，光影自然，动作稳定", "multiline": True}),
                "default_character_refs": ("STRING", {"default": "", "multiline": False}),
                "default_scene_refs": ("STRING", {"default": "", "multiline": False}),
                "default_prop_refs": ("STRING", {"default": "", "multiline": False}),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4"], {"default": "16:9"}),
                "resolution": (["快速预览 480P", "快速人物 544P", "标准 720P", "原生 768"], {"default": "快速预览 480P"}),
                "default_seconds": ("FLOAT", {"default": 5.0, "min": 0.2, "max": 15.1, "step": 0.1}),
                "consistency": (["标准", "强", "最高"], {"default": "强"}),
                "audio_mode": (["环境音（无配乐）", "完全静音", "H3原生音频"], {"default": "环境音（无配乐）"}),
                "quality_preset": (["快速预览", "标准质量", "高质量"], {"default": "快速预览"}),
                "auto_save": ("BOOLEAN", {"default": True}),
                "output_prefix": ("STRING", {"default": "AI_Video_Studio"}),
                # Advanced model/runtime settings. JS hides them by default.
                "fl2va_model": (diffusion, {"default": "自动检测"}),
                "ref2va_model": (diffusion, {"default": "自动检测"}),
                "clip_model": (clips, {"default": "自动检测"}),
                "video_vae_model": (vaes, {"default": "自动检测"}),
                "audio_vae_model": (vaes, {"default": "自动检测"}),
                "lora_name": (loras, {"default": "不使用"}),
                "lora_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05}),
                "weight_dtype": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"], {"default": "default"}),
                "steps_override": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "cfg": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1}),
                "sampler": (["res_multistep", "euler", "euler_cfg_pp", "dpmpp_2m", "dpmpp_2m_sde"], {"default": "res_multistep"}),
                "scheduler": (["simple", "beta", "normal", "sgm_uniform", "karras"], {"default": "simple"}),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "shift_video": ("FLOAT", {"default": 12.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "shift_audio": ("FLOAT", {"default": 3.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "ref_image_size": (["match", "max"], {"default": "match"}),
                "max_images": ("INT", {"default": 9, "min": 0, "max": 9}),
                "max_videos": ("INT", {"default": 3, "min": 0, "max": 3}),
                "max_audios": ("INT", {"default": 3, "min": 0, "max": 3}),
            }
        }

    RETURN_TYPES = ("AVS_PROJECT_CONTEXT", "STRING")
    RETURN_NAMES = ("PROJECT_CONTEXT", "项目摘要")
    FUNCTION = "build_project"
    CATEGORY = "AI Video Studio/03 导演台"
    DESCRIPTION = "总控导演台：设置整个项目的角色/场景默认引用、风格、比例、质量、声音和模型方案。一个项目通常只需要一个总控导演台。"

    def build_project(self, resource_db: dict[str, Any], **kwargs):
        language = str(kwargs.get("language", "中文"))
        quality = str(kwargs.get("quality_preset", "快速预览"))
        preset_steps = {"快速预览": 8, "标准质量": 12, "高质量": 20}.get(quality, 8)
        steps = int(kwargs.get("steps_override", 0) or preset_steps)
        project = {
            "version": 1,
            "resource_db": resource_db,
            **kwargs,
            "steps": steps,
        }
        return (project, _project_summary(project, language))


class AVSShotDirector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "project_context": ("AVS_PROJECT_CONTEXT",),
                "shot_number": ("INT", {"default": 1, "min": 1, "max": 999, "step": 1}),
                "shot_name": ("STRING", {"default": "镜头1"}),
                "story_goal": ("STRING", {"default": "让观众清楚理解当前动作和情绪", "multiline": True}),
                "character_refs": ("STRING", {"default": "", "multiline": False}),
                "scene_refs": ("STRING", {"default": "", "multiline": False}),
                "prop_refs": ("STRING", {"default": "", "multiline": False}),
                "motion_refs": ("STRING", {"default": "", "multiline": False}),
                "audio_refs": ("STRING", {"default": "", "multiline": False}),
                "start_state": ("STRING", {"default": "", "multiline": True}),
                "action": ("STRING", {"default": "人物完成一个清楚、可读的主要动作", "multiline": True}),
                "emotion": ("STRING", {"default": "自然", "multiline": False}),
                "end_state": ("STRING", {"default": "动作自然收住，并保留下一镜可继续的姿态", "multiline": True}),
                "shot_size": (["远景", "全景", "中景", "近景", "特写"], {"default": "全景"}),
                "camera_angle": (["正面", "侧面", "背面", "肩后", "低机位", "高机位", "俯拍", "仰拍"], {"default": "正面"}),
                "camera_move": (["固定", "推近", "拉远", "跟拍", "横移", "轻微环绕"], {"default": "固定"}),
                "continuity": (["自动", "续写上一镜", "独立镜头"], {"default": "自动"}),
                "seconds": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 15.1, "step": 0.1}),
                "dialogue": ("STRING", {"default": "", "multiline": True}),
                "sound_notes": ("STRING", {"default": "", "multiline": True}),
                "extra_prompt": ("STRING", {"default": "", "multiline": True}),
                "seed_mode": (["随机", "固定"], {"default": "随机"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "inherit_previous_audio": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "previous_video": ("VIDEO",),
            },
        }

    RETURN_TYPES = ("AVS_SHOT_CONTEXT", "STRING", "STRING")
    RETURN_NAMES = ("SHOT_CONTEXT", "最终提示词", "镜头摘要")
    FUNCTION = "build_shot"
    CATEGORY = "AI Video Studio/03 导演台"
    DESCRIPTION = "分镜导演台：一个节点负责一个镜头。可重复添加多个分镜导演台，每个镜头单独设置角色、场景、动作、摄影、声音和续写关系。"

    def build_shot(self, project_context: dict[str, Any], previous_video=None, **kwargs):
        if not isinstance(project_context, dict):
            raise ValueError("PROJECT_CONTEXT 无效，请先连接 AI视频工作室｜总控导演台。")
        resource_db = project_context.get("resource_db") or {}
        refs = _join_refs(
            project_context.get("default_character_refs", ""),
            project_context.get("default_scene_refs", ""),
            project_context.get("default_prop_refs", ""),
            kwargs.get("character_refs", ""),
            kwargs.get("scene_refs", ""),
            kwargs.get("prop_refs", ""),
            kwargs.get("motion_refs", ""),
            kwargs.get("audio_refs", ""),
        )
        resource_ctx = _compile_resource_references(
            resource_db,
            refs,
            max_images=int(project_context.get("max_images", 9)),
            max_videos=int(project_context.get("max_videos", 3)),
            max_audios=int(project_context.get("max_audios", 3)),
        )
        if resource_ctx.get("missing"):
            raise ValueError("存在未找到的 @引用：" + "、".join(resource_ctx["missing"]))

        continuity_mode = str(kwargs.get("continuity", "自动"))
        use_previous = previous_video is not None and continuity_mode != "独立镜头"
        if continuity_mode == "续写上一镜" and previous_video is None:
            raise ValueError("当前镜头设置为“续写上一镜”，但没有连接 previous_video。")
        shot = {**kwargs, "use_previous_video": use_previous}
        prompt = _build_director_prompt(project_context, shot, resource_ctx)
        resource_ctx = dict(resource_ctx)
        resource_ctx["prompt_clean"] = prompt
        mapping = _selected_mapping_block(resource_ctx)
        resource_ctx["prompt_compiled"] = (mapping + "\n\n" + prompt).strip() if mapping else prompt

        seconds = float(kwargs.get("seconds", 0.0) or project_context.get("default_seconds", 5.0))
        seed = int(kwargs.get("seed", 0))
        if kwargs.get("seed_mode") == "随机":
            seed = random.SystemRandom().randrange(0, 2**63 - 1)

        ctx = {
            "version": 1,
            "project": project_context,
            "resource_context": resource_ctx,
            "shot": shot,
            "prompt": resource_ctx["prompt_compiled"],
            "seconds": seconds,
            "seed": seed,
            "previous_video": previous_video,
            "use_previous_video": use_previous,
            "inherit_previous_audio": bool(kwargs.get("inherit_previous_audio", False)),
        }
        summary = (
            f"第{kwargs.get('shot_number', 1)}镜｜{kwargs.get('shot_name') or '未命名'}\n"
            f"资源：图片 {len(resource_ctx.get('images', []))}｜视频 {len(resource_ctx.get('videos', []))}｜音频 {len(resource_ctx.get('audios', []))}\n"
            f"摄影：{kwargs.get('shot_size')}｜{kwargs.get('camera_angle')}｜{kwargs.get('camera_move')}\n"
            f"时长：{seconds:.1f} 秒｜{'续写上一镜' if use_previous else '独立镜头'}｜Seed {seed}"
        )
        return (ctx, ctx["prompt"], summary)


def _extract_video_result(output: Any):
    result = _avs_node_result(output)
    return result[0] if result else None


def _tail_guide(images, preferred: int = 22):
    if images is None or not hasattr(images, "shape") or images.shape[0] <= 0:
        return None
    n = int(images.shape[0])
    if n >= preferred:
        length = preferred
    elif n >= 5:
        valid = [x for x in range(5, n + 1) if x % 17 == 5]
        length = valid[-1] if valid else 5
    else:
        length = 1
    return images[-length:].clone()



def _tail_audio(audio, guide_frames: int = 22, fps: float = 24.0):
    """Return the previous video's audio tail matching the visual guide window."""
    if audio is None:
        return None
    if not isinstance(audio, dict):
        return audio
    waveform = audio.get("waveform")
    sample_rate = int(audio.get("sample_rate", 0) or 0)
    if waveform is None or sample_rate <= 0 or not hasattr(waveform, "shape"):
        return audio
    try:
        seconds = max(1.0 / max(float(fps), 1.0), float(max(1, int(guide_frames))) / max(float(fps), 1.0))
        samples = max(1, int(round(seconds * sample_rate)))
        total = int(waveform.shape[-1])
        if total <= 0:
            return audio
        samples = min(samples, total)
        return {**audio, "waveform": waveform[..., -samples:].clone()}
    except Exception:
        return audio




def _avs_safe_vae_decode(vae, samples):
    """Let the native VAE manage its memory; recover transient Windows reads once."""
    import nodes
    return run_stage("视频解码", nodes.VAEDecode().decode, vae, samples)[0]


def _avs_previous_tail(video, preferred, inherit_audio):
    from comfy_api.latest import InputImpl
    # File inputs can seek to the tail instead of decoding an entire HD clip.
    if isinstance(video, InputImpl.VideoFromFile):
        fps = float(video.get_frame_rate())
        duration = video.get_duration()
        tail_seconds = min(duration, max(1, preferred) / fps)
        video = video.as_trimmed(start_time=max(0.0, duration - tail_seconds),
                                 duration=tail_seconds, strict_duration=False)
    comps = video.get_components()
    guide = _tail_guide(comps.images, preferred)
    audio = _tail_audio(comps.audio, len(guide), float(comps.frame_rate)) if inherit_audio and guide is not None else None
    return guide, audio


class AVSOneClickGenerate:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return model_state()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"shot_context": ("AVS_SHOT_CONTEXT",)}}

    RETURN_TYPES = ("VIDEO", "STRING", "STRING")
    RETURN_NAMES = ("VIDEO", "最终提示词", "生成摘要")
    FUNCTION = "generate"
    CATEGORY = "AI Video Studio/04 一键生成"
    DESCRIPTION = "一键生成：只连接分镜导演台。模型、CLIP、VAE、LoRA、H3条件、采样、上一镜尾部续写、解码和保存都在后台自动完成。"
    OUTPUT_NODE = True

    @model_session
    def generate(self, shot_context: dict[str, Any]):
        started = time.perf_counter()
        if not isinstance(shot_context, dict):
            raise ValueError("SHOT_CONTEXT 无效，请先连接 AI视频工作室｜分镜导演台。")
        project = shot_context.get("project") or {}
        resource_ctx = shot_context.get("resource_context") or {}
        images = list(resource_ctx.get("images") or [])
        videos = list(resource_ctx.get("videos") or [])
        audios = list(resource_ctx.get("audios") or [])
        use_ref = _uses_reference(project, resource_ctx)
        plan = check_project(project, resource_ctx)
        if not plan["ready"]:
            return _wait_for_models(plan, 3)
        bundle = _load_bundle(project, use_ref)

        resolution = str(project.get("resolution", "快速预览 480P"))
        aspect_ratio = str(project.get("aspect_ratio", "16:9"))
        width, height = _avs_resolution(resolution, aspect_ratio, 864, 480)
        seconds = float(shot_context.get("seconds", project.get("default_seconds", 5.0)))
        length = _avs_snap_h3_length(seconds)
        prompt = str(shot_context.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("导演台没有生成有效提示词。")

        try:
            from comfy_extras import nodes_minimax_h3 as h3
        except Exception as exc:
            raise RuntimeError("当前 ComfyUI 没有可用的原生 MiniMax H3 节点，请更新 ComfyUI。") from exc

        positive, latent = run_stage("参考与提示词编码", _conditioning_at_canvas,
                                    shot_context, project, width, height, length, bundle)
        unload(bundle["clip"])

        previous_video = shot_context.get("previous_video")
        guide_count = 0
        if shot_context.get("use_previous_video") and previous_video is not None:
            guide, guide_audio = _avs_previous_tail(previous_video,
                int(shot_context.get("guide_frames", 22) or 22), bool(shot_context.get("inherit_previous_audio")))
            if guide is not None:
                guide_count = int(guide.shape[0])
                positive = _avs_node_result(run_stage("续写引导编码", h3.MiniMaxH3AddGuide.execute,
                    positive=positive, latent=latent, frame_idx=int(shot_context.get("guide_frame_idx", 0) or 0),
                    vae=bundle["video_vae"], audio_vae=bundle["audio_vae"],
                    image=guide, audio=guide_audio,
                ))[0]
            del guide, guide_audio

        import nodes
        unload(bundle["video_vae"])
        unload(bundle["audio_vae"])
        sampled = run_stage("视频采样", nodes.KSampler().sample,
            bundle["model"],
            int(shot_context.get("seed", 0)),
            int(project.get("steps", 8)),
            float(project.get("cfg", 1.0)),
            str(project.get("sampler", "res_multistep")),
            str(project.get("scheduler", "simple")),
            positive, positive, latent,
            float(project.get("denoise", 1.0)),
        )[0]

        del positive, latent
        unload(bundle["model"])
        frames = _avs_safe_vae_decode(bundle["video_vae"], sampled)
        audio = None
        if project.get("audio_mode") != "完全静音":
            try:
                from comfy_extras import nodes_audio
                audio = _avs_node_result(nodes_audio.VAEDecodeAudio.execute(bundle["audio_vae"], sampled))[0]
            except Exception:
                audio = None

        from comfy_extras import nodes_video
        video_out = nodes_video.CreateVideo.execute(
            images=frames, fps=24.0, audio=audio,
            bit_depth="auto", color_space="sRGB", codec="none",
        )
        video = _extract_video_result(video_out)
        if video is None:
            raise RuntimeError("CreateVideo 没有返回有效 VIDEO。")

        finish_notes = []
        if project.get("fast_finish", False):
            # Legacy compatibility only. New profiles keep this off and use the
            # dedicated second-pass node for HD output.
            video, legacy_finish, _ = finish_video(video, project.get("finish_target", "1080P"),
                project.get("upscale_model", "自动检测"), bool(project.get("face_enhance", False)),
                float(project.get("face_strength", 0.0)), int(project.get("finish_batch", 2)), bool(project.get("face_only", False)))
            finish_notes.append(legacy_finish)

        # New single-source-of-truth face repair policy. Hidden spatial-lock
        # prerolls are never repaired because they do not enter the final edit.
        repair_mode = str(project.get("face_repair_mode", "关闭") or "关闭")
        if repair_mode != "关闭" and str(shot_context.get("segment_role", "content")) != "hidden_anchor":
            try:
                from .face_repair import repair_video
                video, repair_summary, _ = repair_video(
                    video, shot_context, project, _face_repair_settings(project), _second_pass_video
                )
                finish_notes.append(repair_summary)
            except ValueError as exc:
                if repair_mode == "自动":
                    finish_notes.append(f"人脸修复：自动跳过｜{exc}")
                else:
                    raise
        finish_summary = "｜".join(x for x in finish_notes if x)

        ui_data = None
        if bool(project.get("auto_save", True)):
            shot = shot_context.get("shot") or {}
            project_name = re.sub(r"[^0-9A-Za-z_\-\u3400-\u9fff]+", "_", str(project.get("project_name", "project"))).strip("_") or "project"
            shot_name = re.sub(r"[^0-9A-Za-z_\-\u3400-\u9fff]+", "_", str(shot.get("shot_name", "shot"))).strip("_") or "shot"
            prefix = f"{project.get('output_prefix', 'AI_Video_Studio')}/{project_name}/S{int(shot.get('shot_number', 1)):03d}_{shot_name}"
            ui_data = save_video(video, prefix)
            if project.get("save_first_latent", True):
                meta = _find_saved_media(ui_data)
                try:
                    save_latent(_saved_media_path(meta) + ".avs.safetensors", sampled, shot_context, width, height, length)
                except (OSError, RuntimeError) as exc:
                    logging.warning("AVS 一采 latent 保存失败，二采将使用视频编码：%s", exc)

        role_note = "隐藏空间预热｜不进成片" if str(shot_context.get("segment_role", "content")) == "hidden_anchor" else "正式视频段"
        compensation_note = "｜已补偿隐藏预热窗口" if bool(shot_context.get("hidden_anchor_compensation")) else ""
        summary = (
            f"生成完成｜{role_note}｜{width}×{height}｜{length}帧（约{length/24:.2f}秒）{compensation_note}\n"
            f"参考：图片{len(images)}｜视频{len(videos)}｜音频{len(audios)}｜续写引导{guide_count}帧\n"
            f"模型：{bundle['model_name']}｜LoRA：{(' + '.join([x['name'] for x in bundle.get('loras', [])]) if bundle.get('loras') else bundle.get('lora_name', '不使用'))}｜Steps {project.get('steps', 8)}｜CFG {project.get('cfg', 1.0)}\n"
            f"{finish_summary}｜总耗时 {time.perf_counter()-started:.1f}秒"
        )
        result = (video, prompt, summary)
        if ui_data:
            return {"ui": ui_data, "result": result}
        return result


# ---------------------------------------------------------------------------
# v0.8.0 — node-native timeline director
# ---------------------------------------------------------------------------

def _default_timeline_doc() -> dict[str, Any]:
    return {
        "version": 1,
        "shots": [
            {
                "id": "shot-1",
                "name": "镜头1",
                "duration": 5.0,
                "prompt": "描述这个镜头里真正发生的事情。可以直接输入 @角色、@场景，或 @角色/某张图。",
                "character_refs": "",
                "scene_refs": "",
                "prop_refs": "",
                "motion_refs": "",
                "audio_refs": "",
                "start_state": "",
                "action": "人物完成一个清楚、可读的主要动作",
                "emotion": "自然",
                "end_state": "动作自然收住，并保留下一镜可继续的姿态",
                "shot_size": "全景",
                "camera_angle": "正面",
                "camera_move": "固定",
                "continuity": "独立镜头",
                "dialogue": "",
                "sound_notes": "",
                "seed_mode": "随机",
                "seed": 0,
                "inherit_previous_audio": bool(index > 0),
            }
        ],
    }


def _parse_timeline_doc(raw: str) -> dict[str, Any]:
    try:
        doc = json.loads(raw) if str(raw or "").strip() else _default_timeline_doc()
    except Exception as exc:
        raise ValueError(f"导演时间线数据损坏：{exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError("导演时间线必须是 JSON 对象。")
    shots = doc.get("shots")
    if not isinstance(shots, list) or not shots:
        doc["shots"] = _default_timeline_doc()["shots"]
    return doc




class AVSTimelineDirector:
    """A resizable, node-native timeline director.

    The front-end stores the whole storyboard in ``timeline_json``. The backend
    only compiles the currently selected shot into the existing
    ``AVS_SHOT_CONTEXT`` contract, so it remains compatible with the v0.7
    one-click H3 generator while the canvas only needs one director node.
    """

    @classmethod
    def INPUT_TYPES(cls):
        diffusion = _model_options("diffusion_models")
        clips = _model_options("text_encoders")
        vaes = _model_options("vae")
        loras = ["不使用"] + _files("loras")
        default_doc = json.dumps(_default_timeline_doc(), ensure_ascii=False)
        return {
            "required": {
                "resource_db": ("AVS_RESOURCE_DB",),
                "timeline_json": ("STRING", {"default": default_doc, "multiline": True}),
                "selected_index": ("INT", {"default": 0, "min": 0, "max": 999}),
                "language": (["中文", "English"], {"default": "中文"}),
                "project_name": ("STRING", {"default": "我的AI视频项目"}),
                "project_type": (["短剧", "漫剧", "舞蹈", "打斗", "广告", "其他"], {"default": "短剧"}),
                "visual_style": ("STRING", {"default": "电影级画面，主体清晰，光影自然，动作稳定", "multiline": True}),
                "default_character_refs": ("STRING", {"default": ""}),
                "default_scene_refs": ("STRING", {"default": ""}),
                "default_prop_refs": ("STRING", {"default": ""}),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4"], {"default": "16:9"}),
                "resolution": (["快速预览 480P", "快速人物 544P", "标准 720P", "原生 768"], {"default": "快速预览 480P"}),
                "consistency": (["标准", "强", "最高"], {"default": "强"}),
                "audio_mode": (["环境音（无配乐）", "完全静音", "H3原生音频"], {"default": "环境音（无配乐）"}),
                "quality_preset": (["快速预览", "标准质量", "高质量"], {"default": "快速预览"}),
                "auto_save": ("BOOLEAN", {"default": True}),
                "output_prefix": ("STRING", {"default": "AI_Video_Studio"}),
                "fl2va_model": (diffusion, {"default": "自动检测"}),
                "ref2va_model": (diffusion, {"default": "自动检测"}),
                "clip_model": (clips, {"default": "自动检测"}),
                "video_vae_model": (vaes, {"default": "自动检测"}),
                "audio_vae_model": (vaes, {"default": "自动检测"}),
                "lora_name": (loras, {"default": "不使用"}),
                "lora_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05}),
                "weight_dtype": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"], {"default": "default"}),
                "steps_override": ("INT", {"default": 0, "min": 0, "max": 100}),
                "cfg": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1}),
                "sampler": (["res_multistep", "euler", "euler_cfg_pp", "dpmpp_2m", "dpmpp_2m_sde"], {"default": "res_multistep"}),
                "scheduler": (["simple", "beta", "normal", "sgm_uniform", "karras"], {"default": "simple"}),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "shift_video": ("FLOAT", {"default": 12.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "shift_audio": ("FLOAT", {"default": 3.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "ref_image_size": (["match", "max"], {"default": "match"}),
                "max_images": ("INT", {"default": 9, "min": 0, "max": 9}),
                "max_videos": ("INT", {"default": 3, "min": 0, "max": 3}),
                "max_audios": ("INT", {"default": 3, "min": 0, "max": 3}),
            },
            "optional": {
                "previous_video": ("VIDEO",),
            },
        }

    RETURN_TYPES = ("AVS_SHOT_CONTEXT", "STRING", "STRING")
    RETURN_NAMES = ("SHOT_CONTEXT", "最终提示词", "时间线摘要")
    FUNCTION = "compile_selected_shot"
    CATEGORY = "AI Video Studio/02 导演台"
    DESCRIPTION = "节点内导演时间线：一个节点管理多个镜头。选择一个镜头后，输出当前镜头给一键生成器。"

    def compile_selected_shot(self, resource_db: dict[str, Any], timeline_json: str, selected_index: int, previous_video=None, **kwargs):
        if not isinstance(resource_db, dict):
            raise ValueError("RESOURCE_DB 无效，请连接 AI视频工作室｜永久资源库。")
        doc = _parse_timeline_doc(timeline_json)
        shots = doc.get("shots") or []
        index = max(0, min(int(selected_index), len(shots) - 1))
        raw = shots[index] if shots else _default_timeline_doc()["shots"][0]
        shot = dict(raw)
        project = _timeline_project_from_kwargs(resource_db, kwargs)

        refs = _join_refs(
            project.get("default_character_refs", ""),
            project.get("default_scene_refs", ""),
            project.get("default_prop_refs", ""),
            shot.get("character_refs", ""),
            shot.get("scene_refs", ""),
            shot.get("prop_refs", ""),
            shot.get("motion_refs", ""),
            shot.get("audio_refs", ""),
            # @ references typed directly into the shot prompt also count.
            shot.get("prompt", ""),
        )
        resource_ctx = _compile_resource_references(
            resource_db,
            refs,
            max_images=int(project.get("max_images", 9)),
            max_videos=int(project.get("max_videos", 3)),
            max_audios=int(project.get("max_audios", 3)),
        )
        if resource_ctx.get("missing"):
            raise ValueError("存在未找到的 @引用：" + "、".join(resource_ctx["missing"]))

        continuity_mode = str(shot.get("continuity", "自动"))
        use_previous = previous_video is not None and continuity_mode != "独立镜头"
        if continuity_mode == "续写上一镜" and previous_video is None:
            raise ValueError("当前镜头设置为“续写上一镜”，但没有连接 previous_video。")

        normalized_shot = {
            "shot_number": index + 1,
            "shot_name": shot.get("name") or f"镜头{index + 1}",
            "story_goal": shot.get("story_goal") or "让观众清楚理解当前动作和情绪",
            "character_refs": shot.get("character_refs", ""),
            "scene_refs": shot.get("scene_refs", ""),
            "prop_refs": shot.get("prop_refs", ""),
            "motion_refs": shot.get("motion_refs", ""),
            "audio_refs": shot.get("audio_refs", ""),
            "start_state": shot.get("start_state", ""),
            "action": shot.get("action") or shot.get("prompt") or "人物完成一个清楚、可读的主要动作",
            "emotion": shot.get("emotion") or "自然",
            "end_state": shot.get("end_state") or "动作自然收住，并保留下一镜可继续的姿态",
            "shot_size": shot.get("shot_size") or "全景",
            "camera_angle": shot.get("camera_angle") or "正面",
            "camera_move": shot.get("camera_move") or "固定",
            "continuity": continuity_mode,
            "dialogue": shot.get("dialogue", ""),
            "sound_notes": shot.get("sound_notes", ""),
            "extra_prompt": shot.get("prompt", ""),
            "seed_mode": shot.get("seed_mode", "随机"),
            "seed": int(shot.get("seed", 0) or 0),
            "inherit_previous_audio": bool(shot.get("inherit_previous_audio", False)),
            "use_previous_video": use_previous,
        }

        prompt = _build_director_prompt(project, normalized_shot, resource_ctx)
        resource_ctx = dict(resource_ctx)
        resource_ctx["prompt_clean"] = prompt
        mapping = _selected_mapping_block(resource_ctx)
        resource_ctx["prompt_compiled"] = (mapping + "\n\n" + prompt).strip() if mapping else prompt

        seconds = max(0.2, min(float(shot.get("duration", 5.0) or 5.0), 15.1))
        seed = int(normalized_shot.get("seed", 0))
        if normalized_shot.get("seed_mode") == "随机":
            seed = random.SystemRandom().randrange(0, 2**63 - 1)

        ctx = {
            "version": 2,
            "project": project,
            "resource_context": resource_ctx,
            "shot": normalized_shot,
            "timeline": doc,
            "selected_index": index,
            "prompt": resource_ctx["prompt_compiled"],
            "seconds": seconds,
            "seed": seed,
            "previous_video": previous_video,
            "use_previous_video": use_previous,
            "inherit_previous_audio": bool(normalized_shot.get("inherit_previous_audio", False)),
        }
        total = sum(max(0.2, float(s.get("duration", 5.0) or 5.0)) for s in shots)
        summary = (
            f"时间线：{len(shots)} 个镜头｜总时长约 {total:.1f} 秒\n"
            f"当前：镜头 {index + 1}｜{normalized_shot['shot_name']}｜{seconds:.1f} 秒\n"
            f"引用：图片 {len(resource_ctx.get('images', []))}｜视频 {len(resource_ctx.get('videos', []))}｜音频 {len(resource_ctx.get('audios', []))}"
        )
        return (ctx, ctx["prompt"], summary)


NODE_CLASS_MAPPINGS = {
    "AVSTimelineDirector": AVSTimelineDirector,
    "AVSProjectDirector": AVSProjectDirector,
    "AVSShotDirector": AVSShotDirector,
    "AVSOneClickGenerate": AVSOneClickGenerate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AVSTimelineDirector": "AI视频工作室｜导演时间线",
    "AVSProjectDirector": "AI视频工作室｜总控导演台（旧版）",
    "AVSShotDirector": "AI视频工作室｜分镜导演台（旧版）",
    "AVSOneClickGenerate": "AI视频工作室｜一键生成视频",
}

# ---------------------------------------------------------------------------
# v0.11.0 — self-contained Director Workbench
# One timeline card = one effective video segment.
# Source modes:
#   1) 生成视频: paste one COMPLETE MiniMax H3 structured prompt and generate here.
#   2) 已有视频: choose a previously generated/local library video and use it directly.
# The whole flow (refs -> H3 -> continuation -> sampling -> save -> preview -> concat)
# stays inside this node. No downstream generation node is required.
# ---------------------------------------------------------------------------

def _default_full_prompt() -> str:
    return (
        "subject_definitions:\n"
        "<Subject 1> is defined by <Picture 1>.\n"
        "\n"
        "summary:\n"
        "[reference generation] Describe the complete target video segment and its internal [Shot N] sequence.\n"
        "\n"
        "retention_analysis:\n"
        "<Subject 1>: fully_preserved - keep identity, appearance, clothing and fixed design unchanged.\n"
        "\n"
        "detailed_description:\n"
        "[Shot 1] Describe the opening action, camera, spatial relationship and exact ending state.\n"
        "\n"
        "overall_soundscape:\n"
        "Diegetic sound only, synchronized to the picture.\n"
        "\n"
        "non_diegetic_music:\n"
        "N/A"
    )


def _default_image_slots() -> list[dict[str, Any]]:
    return [
        {
            "slot": i + 1, "token": "", "asset_id": "", "name": "", "group_name": "",
            "local_path": "", "local_filename": "", "local_subfolder": "", "local_type": "",
        }
        for i in range(9)
    ]


def _default_segment(index: int = 0) -> dict[str, Any]:
    return {
        "id": f"segment-{index + 1}",
        "name": f"视频段{index + 1}",
        "episode_id": "EP01",
        "episode_name": "第1集",
        "scene_id": "SC01",
        "scene_name": "未分场",
        # v0.16.9: production-only hidden spatial-lock preroll support.
        # hidden_anchor segments are generated normally and can feed AddGuide into
        # the next formal segment, but are never included in the delivered movie.
        "segment_role": "content",
        "include_in_final": True,
        "spatial_lock_id": "",
        "spatial_lock_source_id": "",
        "duration": 5.0,
        "source_mode": "生成视频",
        "full_prompt": _default_full_prompt(),
        "image_slots": _default_image_slots(),
        "video_refs": "",
        "local_video_refs": [],
        "audio_refs": "",
        "continuity": "独立生成" if index == 0 else "续写上一段",
        "guide_frames": 22,
        "guide_frame_idx": 0,
        "inherit_previous_audio": False,
        "seed_mode": "随机",
        "seed": 0,
        "existing_video_asset_id": "",
        "existing_video_name": "",
        "existing_video_path": "",
        "existing_video_filename": "",
        "existing_video_subfolder": "",
        "existing_video_type": "",
        # v0.15.5: keep the Director front-end draw/candidate state in the
        # backend timeline document.  Older versions silently dropped these
        # fields during _parse_timeline_doc(), which made a clicked
        # “开始抽卡” arrive here as generation_mode=single.
        "generation_mode": "single",
        "draw_count": 4,
        "draw_seed_mode": "random",
        "draw_rounds": [],
        "selected_candidate_id": "",
        "result_video": {},
        "refined_video": {},
        "result_status": "未生成",
        "refine_status": "未二采",
        "preview_variant": "best",
        "generation_summary": "",
        "generation_dims": [],
        "refine_summary": "",
        "refine_dims": [],
    }


def _default_timeline_doc() -> dict[str, Any]:
    return {"version": 9, "shots": [_default_segment(0), _default_segment(1)], "timeline_edits": [], "pending_edit": {}}


def _normalise_image_slots(value: Any) -> list[dict[str, Any]]:
    slots = _default_image_slots()
    if not isinstance(value, list):
        return slots
    for i, raw in enumerate(value[:9]):
        if isinstance(raw, str):
            slots[i]["token"] = raw
            continue
        if not isinstance(raw, dict):
            continue
        slots[i].update({
            "slot": i + 1,
            "token": str(raw.get("token", "") or ""),
            "asset_id": str(raw.get("asset_id", "") or ""),
            "name": str(raw.get("name", "") or ""),
            "group_name": str(raw.get("group_name", "") or ""),
            "local_path": str(raw.get("local_path", "") or ""),
            "local_filename": str(raw.get("local_filename", "") or ""),
            "local_subfolder": str(raw.get("local_subfolder", "") or ""),
            "local_type": str(raw.get("local_type", "") or ""),
        })
    return slots


def _legacy_structured_to_full(src: dict[str, Any]) -> str:
    # Preserve v0.10 structured fields when migrating to the single complete prompt editor.
    keys = (
        "subject_definitions", "summary", "retention_analysis",
        "detailed_description", "overall_soundscape", "non_diegetic_music",
    )
    if not any(str(src.get(k, "") or "").strip() for k in keys):
        prompt = str(src.get("prompt", "") or "").strip()
        return prompt or _default_full_prompt()
    return (
        "subject_definitions:\n" + str(src.get("subject_definitions", "") or "").strip() + "\n\n"
        "summary:\n" + str(src.get("summary", "") or "").strip() + "\n\n"
        "retention_analysis:\n" + str(src.get("retention_analysis", "") or "").strip() + "\n\n"
        "detailed_description:\n" + str(src.get("detailed_description", "") or "").strip() + "\n\n"
        "overall_soundscape:\n" + str(src.get("overall_soundscape", "") or "").strip() + "\n\n"
        "non_diegetic_music:\n" + (str(src.get("non_diegetic_music", "") or "N/A").strip() or "N/A")
    ).strip()


def _migrate_structured_segment(raw: dict[str, Any], index: int) -> dict[str, Any]:
    src = dict(raw or {})
    base = _default_segment(index)
    for key in base:
        if key in src and key not in {"image_slots"}:
            base[key] = src[key]
    if "character_selections" in src:
        base["character_selections"] = src["character_selections"]
    base["id"] = str(src.get("id") or base["id"])
    base["name"] = str(src.get("name") or base["name"])

    # v0.16.9 — hidden spatial preroll / scene initializer.  Accept both the
    # native Director fields and the V4.4 Skill metadata aliases so old/new MD
    # imports and exported project JSON stay interoperable.
    raw_role = str(src.get("segment_role") or src.get("segment_type") or "").strip().lower()
    editorial_visibility = str(src.get("editorial_visibility") or "").strip().lower()
    counts_runtime = src.get("counts_toward_final_runtime")
    hidden_aliases = {"hidden_anchor", "spatial_lock", "anchor", "lock", "隐藏空间预热", "空间预热", "空间锁"}
    is_hidden = raw_role in hidden_aliases or editorial_visibility in {"discard", "hidden", "production_only"} or counts_runtime is False
    base["segment_role"] = "hidden_anchor" if is_hidden else "content"
    base["include_in_final"] = False if is_hidden else bool(src.get("include_in_final", True))
    base["spatial_lock_id"] = str(src.get("spatial_lock_id") or (base["id"] if is_hidden else "") or "")
    base["spatial_lock_source_id"] = str(src.get("spatial_lock_source_id") or src.get("inherit_spatial_lock_from") or "")
    default_duration = 1.0 if is_hidden else base["duration"]
    base["duration"] = max(0.2, min(float(src.get("duration", default_duration) or default_duration), 15.1))
    base["image_slots"] = _normalise_image_slots(src.get("image_slots"))
    if not str(src.get("full_prompt", "") or "").strip():
        base["full_prompt"] = _legacy_structured_to_full(src)
    else:
        base["full_prompt"] = str(src.get("full_prompt"))
    old_continuity = str(src.get("continuity", "") or "")
    if old_continuity:
        base["continuity"] = "独立生成" if old_continuity in {"独立镜头", "独立生成"} else "续写上一段"
    source = str(src.get("source_mode", base["source_mode"]) or base["source_mode"])
    base["source_mode"] = "已有视频" if source in {"已有视频", "导入视频", "existing"} else "生成视频"
    base["guide_frames"] = int(src.get("guide_frames", 22) or 22)
    base["guide_frame_idx"] = int(src.get("guide_frame_idx", 0) or 0)
    base["inherit_previous_audio"] = bool(src.get("inherit_previous_audio", base.get("inherit_previous_audio", index > 0)))
    if base.get("segment_role") == "hidden_anchor":
        # A spatial-lock preroll is a clean scene initializer, not a visible
        # continuation clip.  It deliberately starts independently so the full
        # 22-frame budget can establish the group layout.
        base["continuity"] = "独立生成"
        base["inherit_previous_audio"] = False
        base["generation_mode"] = "single"
        base["include_in_final"] = False
    base["seed_mode"] = str(src.get("seed_mode", "随机") or "随机")
    base["seed"] = int(src.get("seed", 0) or 0)
    base["existing_video_asset_id"] = str(src.get("existing_video_asset_id", "") or "")
    base["existing_video_name"] = str(src.get("existing_video_name", "") or "")
    base["existing_video_path"] = str(src.get("existing_video_path", "") or "")
    base["existing_video_filename"] = str(src.get("existing_video_filename", "") or "")
    base["existing_video_subfolder"] = str(src.get("existing_video_subfolder", "") or "")
    base["existing_video_type"] = str(src.get("existing_video_type", "") or "")

    # v0.16.8: direct-upload H3 reference videos. These are normal ComfyUI input
    # files uploaded through /avs/local/upload?kind=video. Keep at most three,
    # matching MiniMax H3 ReferenceToVideo's ref_video capacity.
    local_video_refs: list[dict[str, Any]] = []
    raw_local_videos = src.get("local_video_refs", [])
    if isinstance(raw_local_videos, list):
        for vi, raw_video in enumerate(raw_local_videos[:3]):
            if not isinstance(raw_video, dict):
                continue
            local_video_refs.append({
                "slot": vi + 1,
                "name": str(raw_video.get("name") or raw_video.get("filename") or f"参考视频{vi + 1}"),
                "path": str(raw_video.get("path") or ""),
                "filename": str(raw_video.get("filename") or ""),
                "subfolder": str(raw_video.get("subfolder") or ""),
                "type": str(raw_video.get("type") or "input"),
                "size": int(raw_video.get("size") or 0),
            })
    base["local_video_refs"] = local_video_refs

    # Preserve and normalise draw/candidate state.  These fields live inside
    # timeline_json and must survive every backend parse; otherwise the
    # front-end can request “抽卡当前视频段” while the backend sees “single”.
    generation_mode = str(src.get("generation_mode", base.get("generation_mode", "single")) or "single")
    base["generation_mode"] = generation_mode if generation_mode in {"single", "draw"} else "single"
    if base.get("segment_role") == "hidden_anchor":
        base["generation_mode"] = "single"
    draw_count = int(src.get("draw_count", base.get("draw_count", 4)) or 4)
    base["draw_count"] = draw_count if draw_count in {2, 4, 6, 8} else 4
    draw_seed_mode = str(src.get("draw_seed_mode", base.get("draw_seed_mode", "random")) or "random")
    base["draw_seed_mode"] = draw_seed_mode if draw_seed_mode in {"random", "increment"} else "random"

    rounds_out: list[dict[str, Any]] = []
    raw_rounds = src.get("draw_rounds", [])
    if isinstance(raw_rounds, list):
        for ri, raw_round in enumerate(raw_rounds):
            if not isinstance(raw_round, dict):
                continue
            round_index = int(raw_round.get("round_index", ri + 1) or (ri + 1))
            candidates_out: list[dict[str, Any]] = []
            raw_candidates = raw_round.get("candidates", [])
            if isinstance(raw_candidates, list):
                for ci, raw_candidate in enumerate(raw_candidates):
                    if not isinstance(raw_candidate, dict):
                        continue
                    candidate_id = str(raw_candidate.get("candidate_id") or f"r{round_index}_c{ci + 1}")
                    candidates_out.append({
                        "candidate_id": candidate_id,
                        "round_index": round_index,
                        "candidate_index": int(raw_candidate.get("candidate_index", ci + 1) or (ci + 1)),
                        "seed": int(raw_candidate.get("seed", 0) or 0),
                        "result_video": dict(raw_candidate.get("result_video") or {}) if isinstance(raw_candidate.get("result_video"), dict) else {},
                        "refined_video": dict(raw_candidate.get("refined_video") or {}) if isinstance(raw_candidate.get("refined_video"), dict) else {},
                        "status": str(raw_candidate.get("status", "未生成") or "未生成"),
                        "refine_status": str(raw_candidate.get("refine_status", "未二采") or "未二采"),
                        "preview_variant": str(raw_candidate.get("preview_variant", "best") or "best"),
                        "is_selected": bool(raw_candidate.get("is_selected", False)),
                    })
            rounds_out.append({"round_index": round_index, "candidates": candidates_out})
    base["draw_rounds"] = rounds_out
    base["selected_candidate_id"] = str(src.get("selected_candidate_id", "") or "")

    # Keep the normal one-pass / two-pass state too.  This also fixes final
    # composition losing a saved refined result after timeline parsing.
    base["result_video"] = dict(src.get("result_video") or {}) if isinstance(src.get("result_video"), dict) else {}
    base["refined_video"] = dict(src.get("refined_video") or {}) if isinstance(src.get("refined_video"), dict) else {}
    base["result_status"] = str(src.get("result_status", "未生成") or "未生成")
    base["refine_status"] = str(src.get("refine_status", "未二采") or "未二采")
    preview_variant = str(src.get("preview_variant", "best") or "best")
    base["preview_variant"] = preview_variant if preview_variant in {"best", "source", "hd", "compare"} else "best"

    # Make the selected flag deterministic from selected_candidate_id.
    selected_id = base["selected_candidate_id"]
    if selected_id:
        for round_obj in base["draw_rounds"]:
            for candidate in round_obj.get("candidates", []):
                candidate["is_selected"] = str(candidate.get("candidate_id", "")) == selected_id
    return base


def _parse_timeline_doc(raw: str) -> dict[str, Any]:
    try:
        doc = json.loads(raw) if str(raw or "").strip() else _default_timeline_doc()
    except Exception as exc:
        raise ValueError(f"导演工作台数据损坏：{exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError("导演工作台必须是 JSON 对象。")
    source = doc.get("shots")
    if not isinstance(source, list) or not source:
        source = _default_timeline_doc()["shots"]
    doc["shots"] = [_migrate_structured_segment(dict(item or {}), i) for i, item in enumerate(source)]
    edits = doc.get("timeline_edits")
    doc["timeline_edits"] = [dict(x) for x in edits if isinstance(x, dict)] if isinstance(edits, list) else []
    pending = doc.get("pending_edit")
    doc["pending_edit"] = dict(pending) if isinstance(pending, dict) else {}
    doc["version"] = 9
    return doc


def _timeline_project_from_kwargs(resource_db: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    quality = str(kwargs.get("quality_preset", "快速预览"))
    preset_steps = {"快速预览": 8, "标准质量": 12, "高质量": 20}.get(quality, 8)
    steps = int(kwargs.get("steps_override", 0) or preset_steps)
    return {
        "version": 7,
        "resource_db": resource_db,
        "language": kwargs.get("language", "中文"),
        "project_name": kwargs.get("project_name", "我的AI视频项目"),
        "project_type": kwargs.get("project_type", "短剧"),
        "visual_style": kwargs.get("visual_style", "电影级画面，主体清晰，光影自然，动作稳定"),
        "aspect_ratio": kwargs.get("aspect_ratio", "16:9"),
        "resolution": kwargs.get("resolution", "快速预览 480P"),
        "default_seconds": 5.0,
        "consistency": kwargs.get("consistency", "强"),
        "audio_mode": kwargs.get("audio_mode", "环境音（无配乐）"),
        "quality_preset": quality,
        # Segment preview relies on a concrete file. Keep segment saving on in the workbench.
        "auto_save": True,
        "output_prefix": kwargs.get("output_prefix", "AI_Video_Studio"),
        "fl2va_model": kwargs.get("fl2va_model", "自动检测"),
        "ref2va_model": kwargs.get("ref2va_model", "自动检测"),
        "clip_model": kwargs.get("clip_model", "自动检测"),
        "video_vae_model": kwargs.get("video_vae_model", "自动检测"),
        "audio_vae_model": kwargs.get("audio_vae_model", "自动检测"),
        "lora_name": kwargs.get("lora_name", "不使用"),
        "lora_strength": float(kwargs.get("lora_strength", 1.0)),
        "weight_dtype": kwargs.get("weight_dtype", "default"),
        "steps_override": int(kwargs.get("steps_override", 0)),
        "steps": steps,
        "cfg": float(kwargs.get("cfg", 1.0)),
        "sampler": kwargs.get("sampler", "res_multistep"),
        "scheduler": kwargs.get("scheduler", "simple"),
        "denoise": float(kwargs.get("denoise", 1.0)),
        "shift_video": float(kwargs.get("shift_video", 12.0)),
        "shift_audio": float(kwargs.get("shift_audio", 3.0)),
        "ref_image_size": kwargs.get("ref_image_size", "match"),
        "max_images": int(kwargs.get("max_images", 9)),
        "max_videos": int(kwargs.get("max_videos", 3)),
        "max_audios": int(kwargs.get("max_audios", 3)),
        "generation_mode": kwargs.get("generation_mode", "自动"),
        "face_prompt": bool(kwargs.get("face_prompt", False)),
        "face_repair_mode": str(kwargs.get("face_repair_mode", "关闭") or "关闭"),
        "face_repair_strength": float(kwargs.get("face_repair_strength", 0.65)),
        "face_repair_crop_size": int(kwargs.get("face_repair_crop_size", 512) or 512),
        "face_repair_temporal": float(kwargs.get("face_repair_temporal", 0.25)),
        "face_detection_size": int(kwargs.get("face_detection_size", 1280) or 1280),
        "face_detection_score": float(kwargs.get("face_detection_score", 0.65)),
        "face_repair_steps": int(kwargs.get("face_repair_steps", 4) or 4),
        "face_repair_cfg": float(kwargs.get("face_repair_cfg", 1.0)),
        "face_repair_sampler": kwargs.get("face_repair_sampler", "res_multistep"),
        "face_repair_scheduler": kwargs.get("face_repair_scheduler", "simple"),
        "face_repair_denoise": float(kwargs.get("face_repair_denoise", 0.20)),
        "face_repair_context_frames": int(kwargs.get("face_repair_context_frames", 22) or 22),
        "face_repair_near_denoise": float(kwargs.get("face_repair_near_denoise", 0.06)),
        "face_repair_near_blend": float(kwargs.get("face_repair_near_blend", 0.30)),
        "face_repair_near_refmod_cap": float(kwargs.get("face_repair_near_refmod_cap", 0.25)),
        "fast_finish": bool(kwargs.get("fast_finish", False)),
        "finish_target": kwargs.get("finish_target", "1080P"),
        "upscale_model": kwargs.get("upscale_model", "自动检测"),
        "face_enhance": bool(kwargs.get("face_enhance", True)),
        "face_strength": float(kwargs.get("face_strength", 0.55)),
        "finish_batch": int(kwargs.get("finish_batch", 2)),
        "save_first_latent": bool(kwargs.get("save_first_latent", True)),
        "face_only": bool(kwargs.get("face_only", True)),
    }


def _segment_reference_text(segment: dict[str, Any]) -> str:
    tokens: list[str] = []
    for slot in _normalise_image_slots(segment.get("image_slots")):
        if str(slot.get("local_path", "") or "").strip():
            continue
        token = str(slot.get("token", "") or "").strip()
        if token:
            tokens.append(token)
    for key in ("video_refs", "audio_refs"):
        value = str(segment.get(key, "") or "").strip()
        if value:
            tokens.append(value)
    return " ".join(tokens)


def _picture_reference_indices(prompt: str) -> list[int]:
    """Return unique visible <Picture N> references in first-appearance order.

    The Director prompt is the source of truth.  A Picture slot is only sent to
    MiniMax H3 when the prompt actually references it.  Literal text typed or
    pasted by the user and rich Picture chips both compile to the same
    ``<Picture N>`` token, so both paths are handled identically.
    """
    seen: set[int] = set()
    ordered: list[int] = []
    for raw in re.findall(r"<Picture\s+(\d+)>", str(prompt or ""), flags=re.I):
        n = int(raw)
        if n not in seen:
            seen.add(n)
            ordered.append(n)
    return ordered


def _resolve_picture_slot_asset(resource_db: dict[str, Any], slot: dict[str, Any], visible_index: int) -> dict[str, Any]:
    """Resolve one Director Picture slot into a concrete H3 image asset."""
    local_path = str(slot.get("local_path", "") or "").strip()
    if local_path or slot.get("local_filename"):
        path_obj = Path(local_path)
        if not local_path or not path_obj.is_file():
            root = Path(folder_paths.get_input_directory()).resolve()
            candidate = (root / str(slot.get("local_subfolder", "")) / str(slot.get("local_filename", ""))).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file():
                raise ValueError(f"Picture {visible_index} 的参考图片不存在：{slot.get('name') or local_path}。请重新绑定图片。")
            path_obj = candidate
        return {
            "id": f"local:{path_obj}",
            "media_type": "image",
            "path": str(path_obj),
            "file_name": str(slot.get("local_filename") or path_obj.name),
            "display_name": str(slot.get("name") or path_obj.name),
            "source": "local_file",
        }

    aid = str(slot.get("asset_id", "") or "").strip()
    if aid:
        asset = MANAGER.get_asset(aid)
        if not asset:
            raise ValueError(f"Picture {visible_index} 的参考图片素材已经不存在或已从资源库移除：{slot.get('name') or aid}")
        return asset

    # Compatibility with very old timeline data that may only have a @ token.
    token = str(slot.get("token", "") or "").strip()
    if token:
        resolved = _compile_resource_references(
            resource_db, token, max_images=1, max_videos=0, max_audios=0
        )
        images = list(resolved.get("images") or [])
        if images:
            return images[0]

    raise ValueError(f"提示词引用了 Picture {visible_index}，但这个 Picture 槽位还没有绑定图片。")


def _resolve_local_video_asset(raw: dict[str, Any], visible_index: int) -> dict[str, Any]:
    """Resolve one directly uploaded local reference video safely inside ComfyUI input."""
    root = Path(folder_paths.get_input_directory()).resolve()
    local_path = str(raw.get("path", "") or "").strip()
    filename = str(raw.get("filename", "") or "").strip()
    subfolder = str(raw.get("subfolder", "") or "").strip()

    candidate: Path | None = None
    if local_path:
        p = Path(local_path).resolve()
        try:
            if p.is_relative_to(root) and p.is_file():
                candidate = p
        except Exception:
            candidate = None
    if candidate is None and filename:
        p = (root / subfolder / filename).resolve()
        try:
            if p.is_relative_to(root) and p.is_file():
                candidate = p
        except Exception:
            candidate = None
    if candidate is None:
        raise ValueError(
            f"额外参考视频 {visible_index} 不存在：{raw.get('name') or filename or local_path}。请重新点击上传。"
        )

    return {
        "id": f"local-video:{candidate}",
        "media_type": "video",
        "path": str(candidate),
        "file_name": filename or candidate.name,
        "display_name": str(raw.get("name") or filename or candidate.name),
        "source": "local_file",
    }


def _inject_continuation_rules(full_prompt: str, segment: dict[str, Any], use_previous: bool, previous_role: str = "content") -> str:
    prompt = str(full_prompt or "").strip()
    if not use_previous:
        return prompt
    gf = int(segment.get("guide_frames", 22) or 22)
    fi = int(segment.get("guide_frame_idx", 0) or 0)
    inherit_audio = bool(segment.get("inherit_previous_audio", False))
    audio_rule = (
        f" The previous video's final audio tail matching those {gf} guide frames is also used as the audio guide. Preserve speaker identity, vocal timbre, cadence, breath state, room tone and ambience continuity into the new segment. Do not replay or repeat the previous full sentence; only continue naturally from the cut, and let the current segment prompt/dialogue define the new spoken content."
        if inherit_audio else
        " Previous-segment audio is not used as an audio guide."
    )
    spatial_rule = ""
    if str(previous_role or "") == "hidden_anchor":
        spatial_rule = (
            " The previous video is a production-only hidden spatial-lock preroll. Treat its final layout as the authoritative world-space map: "
            "every on-screen and off-screen character keeps the same left/right ordering, depth, distance, facing, eyeline and dialogue-axis relationship. "
            "The current editorial shot may hard-cut immediately to a close-up; a close-up changes framing only, never character world position. "
            "Do not pull back to re-show the anchor unless the current prompt explicitly asks for it."
        )
    rule = (
        "\n\ncontinuation_rule:\n"
        f"This video segment continues directly from the previous effective video. The opening is anchored by the previous video's final {gf} guide frames at frame_idx={fi}. "
        "The previous video has priority for starting pose, spacing, motion direction, momentum and camera continuity. Picture references only lock identity, face, clothing, weapon and scene design. "
        "Do not reset to a static reference pose; no teleport, no left-right swap, no sudden direction reversal, no unexplained camera-axis reversal, and no standing reset."
        + spatial_rule + audio_rule
    )
    return (prompt + rule).strip()


def _remap_picture_tokens_for_h3(prompt: str, visible_to_packed: dict[int, int]) -> str:
    """Map visible Director Picture slots to H3's packed reference order.

    The UI intentionally allows Picture 1-9 to have gaps. H3 reference inputs are
    packed, so e.g. visible Picture 3 may become internal <Picture 1>. This helper
    rewrites only the prompt sent to H3; the user's editor text stays unchanged.
    """
    prompt = str(prompt or "")
    referenced = [int(x) for x in re.findall(r"<Picture\s+(\d+)>", prompt, flags=re.I)]
    invalid = sorted({n for n in referenced if n < 1 or n > 9})
    if invalid:
        raise ValueError("提示词里的 Picture 编号只支持 1-9：" + "、".join(f"Picture {n}" for n in invalid))
    missing = sorted({n for n in referenced if n not in visible_to_packed})
    if missing:
        raise ValueError(
            "提示词引用了尚未绑定图片的槽位：" + "、".join(f"Picture {n}" for n in missing)
            + "。请先选择对应图片，或删除该 Picture 引用。"
        )
    def repl(match):
        visible = int(match.group(1))
        packed = visible_to_packed.get(visible, visible)
        return f"<Picture {packed}>"
    return re.sub(r"<Picture\s+(\d+)>", repl, prompt, flags=re.I)


def _segment_is_hidden_anchor(segment: dict[str, Any] | None) -> bool:
    if not isinstance(segment, dict):
        return False
    return str(segment.get("segment_role", "content") or "content") == "hidden_anchor"


def _segment_in_final(segment: dict[str, Any] | None) -> bool:
    if not isinstance(segment, dict):
        return False
    if _segment_is_hidden_anchor(segment):
        return False
    return bool(segment.get("include_in_final", True))


def _previous_segment_is_hidden_anchor(shots: list[dict[str, Any]], index: int) -> bool:
    if index <= 0 or index > len(shots) - 1:
        return False
    previous = _migrate_structured_segment(dict(shots[index - 1] or {}), index - 1)
    return _segment_is_hidden_anchor(previous)


def _segment_group_value(segment: dict[str, Any], id_key: str, name_key: str) -> str:
    """Return the most stable available episode/scene grouping value."""
    return str(segment.get(id_key) or segment.get(name_key) or "").strip()


def _segment_is_group_boundary(shots: list[dict[str, Any]], index: int) -> bool:
    """New episode / new scene starts independently by default.

    Old projects that do not carry grouping fields are treated as one group, so
    existing continuation behaviour remains compatible.
    """
    if index <= 0:
        return True
    current = _migrate_structured_segment(dict(shots[index] or {}), index)
    previous = _migrate_structured_segment(dict(shots[index - 1] or {}), index - 1)
    cur_ep = _segment_group_value(current, "episode_id", "episode_name")
    prev_ep = _segment_group_value(previous, "episode_id", "episode_name")
    if cur_ep and prev_ep and cur_ep != prev_ep:
        return True
    cur_scene = _segment_group_value(current, "scene_id", "scene_name")
    prev_scene = _segment_group_value(previous, "scene_id", "scene_name")
    if cur_scene and prev_scene and cur_scene != prev_scene:
        return True
    return False


def _effective_segment_continuity(shots: list[dict[str, Any]], index: int, segment: dict[str, Any] | None = None) -> str:
    segment = segment or _migrate_structured_segment(dict(shots[index] or {}), index)
    if _segment_is_hidden_anchor(segment):
        return "独立生成"
    requested = str(segment.get("continuity", "独立生成") or "独立生成")
    # A formal segment placed directly after a same-scene hidden anchor is
    # intentionally a continuation, even though the anchor itself is not part
    # of the editorial timeline.  This is the core spatial-lock workflow.
    if index > 0 and _previous_segment_is_hidden_anchor(shots, index):
        previous = _migrate_structured_segment(dict(shots[index - 1] or {}), index - 1)
        if _segment_group_value(previous, "scene_id", "scene_name") == _segment_group_value(segment, "scene_id", "scene_name"):
            return "续写上一段"
    # A new episode / scene cannot accidentally inherit the previous group's
    # pose/camera/audio. Users can keep the timeline data as-is; generation is safe.
    if requested == "续写上一段" and _segment_is_group_boundary(shots, index):
        return "独立生成"
    return requested


def _continuation_chain_for_current(shots: list[dict[str, Any]], selected: int, doc: dict[str, Any] | None = None):
    """Find the minimal sequential generation chain needed by the selected shot.

    Returns (indices, previous_video).  If the immediate predecessor already has
    a usable approved video, only the selected shot is generated.  Otherwise we
    walk backward until a ready predecessor or an independent/group-boundary shot
    and generate only the missing chain, in order.
    """
    selected = max(0, min(int(selected), len(shots) - 1))
    current = _migrate_structured_segment(dict(shots[selected] or {}), selected)
    if current.get("source_mode") != "生成视频":
        return [selected], None
    if _effective_segment_continuity(shots, selected, current) != "续写上一段":
        return [selected], None

    immediate = _migrate_structured_segment(dict(shots[selected - 1] or {}), selected - 1)
    ready = _segment_best_video(immediate)
    if ready is not None:
        if doc is not None:
            ready = _segment_video_with_timeline_edits_for_continuation(doc, selected - 1) or ready
        return [selected], ready

    start = selected - 1
    previous_video = None
    while start >= 0:
        segment = _migrate_structured_segment(dict(shots[start] or {}), start)
        # This shot itself can start a fresh chain (first shot/new group/manual independent).
        if _effective_segment_continuity(shots, start, segment) != "续写上一段":
            break
        if start == 0:
            break
        predecessor = _migrate_structured_segment(dict(shots[start - 1] or {}), start - 1)
        ready = _segment_best_video(predecessor)
        if ready is not None:
            if doc is not None:
                ready = _segment_video_with_timeline_edits_for_continuation(doc, start - 1) or ready
            previous_video = ready
            break
        start -= 1

    start = max(0, start)
    return list(range(start, selected + 1)), previous_video


def _compile_studio_shot_context(resource_db: dict[str, Any], project: dict[str, Any], doc: dict[str, Any], index: int, previous_video=None) -> dict[str, Any]:
    shots = doc.get("shots") or []
    if not shots:
        raise ValueError("导演工作台里没有视频段。")
    index = max(0, min(int(index), len(shots) - 1))
    segment = _migrate_structured_segment(dict(shots[index] or {}), index)
    segment, selected_character_refmods = bind_shot(segment, doc)
    if selected_character_refmods and project.get("generation_mode") == "首帧图生视频":
        raise ValueError("人物库需要多素材参考模式，请在H3模型配置中切换生成模式。")
    if segment.get("source_mode") != "生成视频":
        raise ValueError("已有视频段不需要编译 H3 生成条件。")
    delivery_seconds = max(0.2, min(float(segment.get("duration", 5.0) or 5.0), 15.1))
    seconds = delivery_seconds
    refs = _segment_reference_text(segment)
    resource_ctx = _compile_resource_references(
        resource_db, refs,
        max_images=int(project.get("max_images", 9)),
        max_videos=int(project.get("max_videos", 3)),
        max_audios=int(project.get("max_audios", 3)),
    )
    if resource_ctx.get("missing"):
        raise ValueError("存在未找到的素材引用：" + "、".join(resource_ctx["missing"]))

    # v0.16.8 — Direct-upload reference videos take priority over legacy @ video
    # tokens and are sent to H3 even though they do not need a textual @ token.
    local_videos: list[dict[str, Any]] = []
    for vi, raw_video in enumerate(segment.get("local_video_refs", []) or []):
        if vi >= int(project.get("max_videos", 3)):
            break
        if isinstance(raw_video, dict):
            local_videos.append(_resolve_local_video_asset(raw_video, vi + 1))
    if local_videos:
        legacy_videos = list(resource_ctx.get("videos") or [])
        merged_videos: list[dict[str, Any]] = []
        seen_video_paths: set[str] = set()
        for asset in local_videos + legacy_videos:
            key = str(asset.get("path", "") or "")
            if not key or key in seen_video_paths:
                continue
            seen_video_paths.add(key)
            merged_videos.append(asset)
            if len(merged_videos) >= int(project.get("max_videos", 3)):
                break
        resource_ctx["videos"] = merged_videos
        resource_ctx["local_video_refs"] = [
            {"index": i + 1, "name": a.get("display_name"), "path": a.get("path")}
            for i, a in enumerate(local_videos)
        ]

    # v0.15.4 — Prompt-driven Picture collection.
    # The prompt is the source of truth: only Picture slots actually referenced
    # by <Picture N> are loaded and sent to MiniMax H3. This works for both
    # rich Picture chips and literal/pasted <Picture N> text.
    raw_prompt = str(segment.get("full_prompt", "") or "")
    referenced_visible = _picture_reference_indices(raw_prompt)
    invalid_refs = [n for n in referenced_visible if n < 1 or n > 9]
    if invalid_refs:
        raise ValueError("提示词里的 Picture 编号只支持 1-9：" + "、".join(f"Picture {n}" for n in invalid_refs))

    slots = _normalise_image_slots(segment.get("image_slots"))
    slot_images: list[dict[str, Any]] = []
    visible_to_packed: dict[int, int] = {}
    compiled_picture_refs: list[dict[str, Any]] = []
    for visible_index in referenced_visible:
        slot = slots[visible_index - 1]
        asset = _resolve_picture_slot_asset(resource_db, slot, visible_index)
        slot_images.append(asset)
        packed_index = len(slot_images)
        visible_to_packed[visible_index] = packed_index
        compiled_picture_refs.append({
            "visible_picture": visible_index,
            "packed_picture": packed_index,
            "asset_id": str(slot.get("asset_id", "") or asset.get("id", "") or ""),
            "name": str(slot.get("name", "") or asset.get("display_name", "") or asset.get("file_name", "") or ""),
            "path": str(asset.get("path", "") or ""),
        })

    # Always replace the image list. Bound-but-unreferenced Picture slots are
    # deliberately NOT sent to H3, preventing accidental identity/style bleed.
    resource_ctx["images"] = slot_images[:9]
    resource_ctx["picture_slot_map"] = visible_to_packed
    resource_ctx["compiled_picture_refs"] = compiled_picture_refs
    resource_ctx["picture_reference_mode"] = "prompt_auto_collect"

    requested_continuity = str(segment.get("continuity", "独立生成") or "独立生成")
    continuity_mode = _effective_segment_continuity(shots, index, segment)
    previous_role = "content"
    if index > 0:
        previous_role = str(_migrate_structured_segment(dict(shots[index - 1] or {}), index - 1).get("segment_role", "content") or "content")
    use_previous = previous_video is not None and continuity_mode == "续写上一段"
    # Hidden-anchor overlap is production-only and will be removed during final
    # assembly. Add an equal generation pad so a requested 5.0s formal segment
    # still delivers approximately 5.0s after its 22-frame lock window is cut.
    hidden_anchor_compensation = bool(use_previous and previous_role == "hidden_anchor" and not _segment_is_hidden_anchor(segment))
    if hidden_anchor_compensation:
        seconds = min(15.1, delivery_seconds + int(segment.get("guide_frames", 22) or 22) / 24.0)
    if continuity_mode == "续写上一段" and previous_video is None:
        raise ValueError(
            f"第{index + 1}个视频段需要续写上一段，但依赖视频仍不可用。"
            "请使用‘生成当前一采’，新版会自动补齐缺失的续写链；或将本段改为独立生成。"
        )
    base_prompt = _remap_picture_tokens_for_h3(raw_prompt, visible_to_packed)
    prompt = _inject_continuation_rules(base_prompt, segment, use_previous, previous_role=previous_role)
    if not prompt:
        raise ValueError(f"第{index + 1}个视频段的完整提示词为空。")
    if project.get("face_prompt", False):
        quality = "Keep the face in sharp optical focus throughout the shot, with readable eyes, defined facial contours and natural skin texture. Use soft motivated fill light on the face while preserving the scene's lighting mood. Keep background depth of field separate from face focus."
        audio_section = re.search(r"(?m)^overall_soundscape\s*:", prompt)
        if audio_section:
            prompt = prompt[:audio_section.start()].rstrip() + "\n\n" + quality + "\n\n" + prompt[audio_section.start():]
        else:
            prompt += "\n\n" + quality
    if any("文戏" in str(item.get("name", "")) or "realism-people" in str(item.get("name", "")).lower() for item in project.get("loras") or []):
        if "r34l1sm" not in prompt:
            prompt = "r34l1sm\n" + prompt
    resource_ctx = dict(resource_ctx)
    resource_ctx["prompt_clean"] = prompt
    resource_ctx["prompt_compiled"] = prompt
    seed = int(segment.get("seed", 0) or 0)
    if str(segment.get("seed_mode", "随机")) == "随机":
        seed = random.SystemRandom().randrange(0, 2**63 - 1)
    shot = {
        "shot_number": index + 1,
        "shot_name": segment.get("name") or f"视频段{index + 1}",
        "continuity": continuity_mode,
        "requested_continuity": requested_continuity,
        "group_boundary": _segment_is_group_boundary(shots, index),
        "use_previous_video": use_previous,
        "inherit_previous_audio": bool(segment.get("inherit_previous_audio", False)),
        "image_slots": segment.get("image_slots", []),
        "compiled_picture_refs": compiled_picture_refs,
        "selected_character_refmods": selected_character_refmods,
        "picture_reference_mode": "prompt_auto_collect",
        "structured_prompt": True,
        "segment_role": segment.get("segment_role", "content"),
        "include_in_final": _segment_in_final(segment),
        "spatial_lock_id": segment.get("spatial_lock_id", ""),
        "spatial_lock_source_id": segment.get("spatial_lock_source_id", ""),
        "previous_segment_role": previous_role,
        "hidden_anchor_compensation": hidden_anchor_compensation,
    }
    return {
        "version": 6,
        "project": project,
        "resource_context": resource_ctx,
        "shot": shot,
        "timeline": doc,
        "selected_index": index,
        "prompt": prompt,
        "seconds": seconds,
        "delivery_seconds": delivery_seconds,
        "generation_seconds": seconds,
        "segment_role": segment.get("segment_role", "content"),
        "include_in_final": _segment_in_final(segment),
        "previous_segment_role": previous_role,
        "hidden_anchor_compensation": hidden_anchor_compensation,
        "seed": seed,
        "previous_video": previous_video,
        "use_previous_video": use_previous,
        "inherit_previous_audio": bool(segment.get("inherit_previous_audio", False)),
        "guide_frames": int(segment.get("guide_frames", 22) or 22),
        "guide_frame_idx": int(segment.get("guide_frame_idx", 0) or 0),
    }


def _unwrap_generation_result(value):
    if isinstance(value, dict):
        result = value.get("result")
        if isinstance(result, (tuple, list)) and len(result) >= 3:
            return result[0], result[1], result[2], value.get("ui")
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        return value[0], value[1], value[2], None
    raise RuntimeError("一键生成器返回了无法识别的结果。")


def _find_saved_media(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict):
        if value.get("filename"):
            return {
                "filename": str(value.get("filename", "")),
                "subfolder": str(value.get("subfolder", "") or ""),
                "type": str(value.get("type", "output") or "output").split(".")[-1].lower(),
            }
        for v in value.values():
            found = _find_saved_media(v)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for v in value:
            found = _find_saved_media(v)
            if found:
                return found
    return None


def _saved_media_path(meta: dict[str, Any]) -> str:
    filename = str(meta.get("filename", "") or "")
    subfolder = str(meta.get("subfolder", "") or "")
    typ = str(meta.get("type", "output") or "output").lower()
    if not filename:
        return ""
    if "temp" in typ:
        root = folder_paths.get_temp_directory()
    elif "input" in typ:
        root = folder_paths.get_input_directory()
    else:
        root = folder_paths.get_output_directory()
    path = os.path.abspath(os.path.join(root, subfolder, filename))
    if os.path.commonpath([os.path.abspath(root), path]) != os.path.abspath(root):
        raise ValueError("视频保存路径必须位于 ComfyUI 的 input/output/temp 目录内。")
    return path


def _load_video_file(path: str):
    path = os.path.abspath(os.path.expanduser(str(path or "")))
    if not path or not os.path.isfile(path):
        raise ValueError(f"已有视频文件不存在：{path}")
    try:
        from comfy_api.latest import InputImpl
        return InputImpl.VideoFromFile(path)
    except Exception as exc:
        raise RuntimeError(f"无法读取已有视频：{exc}") from exc


def _segment_existing_video(segment: dict[str, Any]):
    asset_id = str(segment.get("existing_video_asset_id", "") or "")
    path = str(segment.get("existing_video_path", "") or "")
    name = str(segment.get("existing_video_name", "") or "")
    if asset_id:
        asset = MANAGER.get_asset(asset_id)
        if not asset:
            raise ValueError(f"已有视频素材不存在或已从资源库移除：{name or asset_id}")
        path = str(asset.get("path", "") or "")
        name = str(asset.get("display_name") or asset.get("file_name") or name or asset_id)
    if not path:
        raise ValueError("该视频段选择了“已有视频”，但尚未选择视频。")
    return _load_video_file(path), {"asset_id": asset_id, "name": name, "path": path}


def _segment_selected_candidate(segment: dict[str, Any]) -> dict[str, Any] | None:
    selected_id = str(segment.get("selected_candidate_id", "") or "")
    if not selected_id:
        return None
    for round_obj in segment.get("draw_rounds", []) or []:
        if not isinstance(round_obj, dict):
            continue
        for candidate in round_obj.get("candidates", []) or []:
            if isinstance(candidate, dict) and str(candidate.get("candidate_id", "")) == selected_id:
                return candidate
    return None


def _video_from_saved_meta(meta: Any):
    if not isinstance(meta, dict) or not meta.get("filename"):
        return None
    path = _saved_media_path(meta)
    if not path or not os.path.isfile(path):
        return None
    return _load_video_file(path)


def _segment_result_video(segment: dict[str, Any]):
    """Return the approved first-pass source. Draw mode uses the selected candidate."""
    if str(segment.get("source_mode")) == "已有视频":
        video, _ = _segment_existing_video(segment)
        return video
    candidate = _segment_selected_candidate(segment)
    if candidate is not None:
        video = _video_from_saved_meta(candidate.get("result_video") or {})
        if video is not None:
            return video
    return _video_from_saved_meta(segment.get("result_video") or {})


def _segment_refined_video(segment: dict[str, Any]):
    candidate = _segment_selected_candidate(segment)
    if candidate is not None:
        video = _video_from_saved_meta(candidate.get("refined_video") or {})
        if video is not None:
            return video
    return _video_from_saved_meta(segment.get("refined_video") or {})


def _segment_best_video(segment: dict[str, Any]):
    """Final/continuation source: approved second-pass > approved first-pass > legacy result."""
    refined = _segment_refined_video(segment)
    if refined is not None:
        return refined
    return _segment_result_video(segment)


def _trim_video_head_frames(video, frame_count: int):
    """Trim duplicated continuation guide frames from the HEAD of a video.

    H3 AddGuide uses the previous segment's tail as the opening guide of the next
    segment. Those guide frames are intentionally kept in each standalone clip so
    later continuation generation can still use the full result. Only the FINAL
    composition removes the duplicated overlap.
    """
    count = max(0, int(frame_count or 0))
    if video is None or count <= 0:
        return video, 0
    try:
        comps = video.get_components()
        images = comps.images
        total = int(images.shape[0]) if images is not None and hasattr(images, "shape") else 0
        # Never turn a segment into an empty clip.
        count = min(count, max(0, total - 1))
        if count <= 0:
            return video, 0
        trimmed_images = images[count:]

        audio = comps.audio
        if isinstance(audio, dict):
            waveform = audio.get("waveform")
            sample_rate = int(audio.get("sample_rate", 0) or 0)
            fps = float(getattr(comps, "frame_rate", 24.0) or 24.0)
            if waveform is not None and sample_rate > 0 and hasattr(waveform, "shape"):
                samples = int(round((count / max(fps, 1e-6)) * sample_rate))
                samples = min(max(0, samples), int(waveform.shape[-1]))
                audio = {**audio, "waveform": waveform[..., samples:]}

        from comfy_extras import nodes_video
        rebuilt = nodes_video.CreateVideo.execute(
            images=trimmed_images,
            fps=float(getattr(comps, "frame_rate", 24.0) or 24.0),
            audio=audio,
            bit_depth="auto", color_space="sRGB", codec="none",
        )
        result = _extract_video_result(rebuilt)
        return (result or video), count
    except Exception:
        # Final composition should remain usable on older ComfyUI builds even if
        # component reconstruction is unavailable. In that case fall back to the
        # original clip rather than failing the whole project.
        return video, 0


# -----------------------------------------------------------------------------
# v0.18.1 — CapCut/Jianying-style arbitrary timeline local redraw
# -----------------------------------------------------------------------------

def _video_frame_count(video) -> tuple[int, float]:
    if video is None:
        return 0, 24.0
    comps = video.get_components()
    images = comps.images
    total = int(images.shape[0]) if images is not None and hasattr(images, "shape") else 0
    fps = float(getattr(comps, "frame_rate", 24.0) or 24.0)
    return total, fps


def _slice_audio_frames(audio, start_frame: int, end_frame: int, fps: float):
    if not isinstance(audio, dict):
        return audio
    waveform = audio.get("waveform")
    sample_rate = int(audio.get("sample_rate", 0) or 0)
    if waveform is None or sample_rate <= 0 or not hasattr(waveform, "shape"):
        return audio
    start_sample = max(0, int(round(float(start_frame) / max(fps, 1e-6) * sample_rate)))
    end_sample = max(start_sample, int(round(float(end_frame) / max(fps, 1e-6) * sample_rate)))
    total = int(waveform.shape[-1])
    start_sample = min(start_sample, total)
    end_sample = min(end_sample, total)
    return {**audio, "waveform": waveform[..., start_sample:end_sample]}


def _slice_video_frames(video, start_frame: int, end_frame: int, *, preserve_audio: bool = True):
    """Return an in-memory VIDEO containing [start_frame, end_frame)."""
    if video is None:
        return None
    comps = video.get_components()
    images = comps.images
    if images is None or not hasattr(images, "shape"):
        raise ValueError("时间轴源视频没有可用画面帧。")
    total = int(images.shape[0])
    start = max(0, min(int(start_frame), total))
    end = max(start + 1, min(int(end_frame), total))
    frames = images[start:end]
    fps = float(getattr(comps, "frame_rate", 24.0) or 24.0)
    audio = _slice_audio_frames(comps.audio, start, end, fps) if preserve_audio else None
    from comfy_extras import nodes_video
    built = nodes_video.CreateVideo.execute(
        images=frames, fps=fps, audio=audio,
        bit_depth="auto", color_space="sRGB", codec="none",
    )
    return _extract_video_result(built)


def _resize_patch_frames(frames, target_h: int, target_w: int):
    if frames is None or not hasattr(frames, "shape"):
        return frames
    if int(frames.shape[1]) == int(target_h) and int(frames.shape[2]) == int(target_w):
        return frames
    return _resize_video_frames(frames, int(target_w), int(target_h), "bicubic")


def _replace_video_frame_range(base_video, patch_video, start_frame: int, end_frame: int):
    """Non-destructive editorial replacement. Base audio is always preserved."""
    if base_video is None or patch_video is None:
        return base_video
    import torch
    base = base_video.get_components()
    patch = patch_video.get_components()
    frames = base.images
    patch_frames = patch.images
    if frames is None or patch_frames is None:
        return base_video
    total = int(frames.shape[0])
    start = max(0, min(int(start_frame), total - 1))
    end = max(start + 1, min(int(end_frame), total))
    needed = end - start
    patch_frames = _resize_patch_frames(patch_frames, int(frames.shape[1]), int(frames.shape[2]))
    have = int(patch_frames.shape[0])
    if have <= 0:
        return base_video
    if have < needed:
        tail = patch_frames[-1:].repeat(needed - have, 1, 1, 1)
        patch_frames = torch.cat([patch_frames, tail], dim=0)
    elif have > needed:
        patch_frames = patch_frames[:needed]
    merged = torch.cat([frames[:start], patch_frames, frames[end:]], dim=0)
    from comfy_extras import nodes_video
    built = nodes_video.CreateVideo.execute(
        images=merged,
        fps=float(getattr(base, "frame_rate", 24.0) or 24.0),
        audio=base.audio,
        bit_depth="auto", color_space="sRGB", codec="none",
    )
    return _extract_video_result(built) or base_video


def _valid_timeline_edits(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for raw in doc.get("timeline_edits") or []:
        if not isinstance(raw, dict) or raw.get("enabled", True) is False:
            continue
        meta = raw.get("result_video") or {}
        if not isinstance(meta, dict) or not meta.get("filename"):
            continue
        try:
            start = float(raw.get("start", 0.0) or 0.0)
            end = float(raw.get("end", 0.0) or 0.0)
        except Exception:
            continue
        if end <= start:
            continue
        out.append({**raw, "start": start, "end": end})
    return out


def _apply_timeline_edits_to_video(video, doc: dict[str, Any]):
    """Apply saved edit patches in list order; later patches win on overlap."""
    applied = 0
    current = video
    for edit in _valid_timeline_edits(doc):
        patch = _video_from_saved_meta(edit.get("result_video") or {})
        if patch is None:
            logging.warning("AVS timeline edit patch missing: %s", edit.get("id"))
            continue
        total, fps = _video_frame_count(current)
        start = int(round(float(edit["start"]) * fps))
        end = int(round(float(edit["end"]) * fps))
        if total <= 0 or start >= total or end <= 0:
            continue
        current = _replace_video_frame_range(current, patch, start, end)
        applied += 1
    return current, applied


def _formal_runtime_spans(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Map saved formal segments to the actual delivered editorial time axis without concatenating them."""
    shots = doc.get("shots") or []
    spans: list[dict[str, Any]] = []
    previous_video = None
    cursor = 0.0
    for index, raw in enumerate(shots):
        segment = _migrate_structured_segment(dict(raw or {}), index)
        video = _segment_best_video(segment)
        if _segment_is_hidden_anchor(segment) or not _segment_in_final(segment):
            if video is not None:
                previous_video = video
            continue
        if video is None:
            break
        total, fps = _video_frame_count(video)
        if total <= 0:
            break
        removed = 0
        continuity = _effective_segment_continuity(shots, index, segment)
        if index > 0 and str(segment.get("source_mode", "生成视频")) == "生成视频" and continuity == "续写上一段":
            preferred = int(segment.get("guide_frames", 22) or 22)
            actual = preferred
            if previous_video is not None:
                try:
                    guide = _tail_guide(previous_video.get_components().images, preferred)
                    if guide is not None:
                        actual = int(guide.shape[0])
                except Exception:
                    pass
            removed = min(max(0, int(actual)), max(0, total - 1))
        delivered = max(1, total - removed)
        duration = delivered / max(fps, 1e-6)
        spans.append({
            "index": index, "start": cursor, "end": cursor + duration,
            "video": video, "fps": fps, "head_trim": removed,
            "delivered_frames": delivered,
        })
        cursor += duration
        previous_video = video
    return spans


def _segment_video_with_timeline_edits_for_continuation(doc: dict[str, Any], index: int):
    """Return a previous segment whose *tail* includes active editorial patches.

    This is what makes the workflow truly usable while generating: if S03's end
    is locally redrawn, S04 AddGuide must inherit the edited S03 tail rather than
    the obsolete raw S03 file. Hidden anchors remain production-only and are not
    affected by editorial patches.
    """
    shots = doc.get("shots") or []
    if index < 0 or index >= len(shots):
        return None
    segment = _migrate_structured_segment(dict(shots[index] or {}), index)
    raw_video = _segment_best_video(segment)
    if raw_video is None:
        return None
    if _segment_is_hidden_anchor(segment) or not _valid_timeline_edits(doc):
        return raw_video
    span = next((x for x in _formal_runtime_spans(doc) if int(x["index"]) == int(index)), None)
    if span is None:
        return raw_video
    current = raw_video
    base_fps = float(span["fps"])
    head = int(span["head_trim"])
    for edit in _valid_timeline_edits(doc):
        overlap_start = max(float(edit["start"]), float(span["start"]))
        overlap_end = min(float(edit["end"]), float(span["end"]))
        if overlap_end <= overlap_start:
            continue
        patch = _video_from_saved_meta(edit.get("result_video") or {})
        if patch is None:
            continue
        patch_total, patch_fps = _video_frame_count(patch)
        if patch_total <= 0:
            continue
        p0 = int(round((overlap_start - float(edit["start"])) * patch_fps))
        p1 = int(round((overlap_end - float(edit["start"])) * patch_fps))
        p0 = max(0, min(p0, patch_total - 1))
        p1 = max(p0 + 1, min(p1, patch_total))
        patch_piece = _slice_video_frames(patch, p0, p1, preserve_audio=False)
        raw0 = head + int(round((overlap_start - float(span["start"])) * base_fps))
        raw1 = head + int(round((overlap_end - float(span["start"])) * base_fps))
        current = _replace_video_frame_range(current, patch_piece, raw0, raw1)
    return current


def _compose_ready_timeline_video(doc: dict[str, Any]):
    """Compose the contiguous generated editorial prefix for live timeline editing.

    Hidden spatial anchors remain generation-only. Formal continuation overlaps are
    removed exactly like final composition. Stops at the first missing formal clip.
    Returns (video, spans, seconds) where spans map actual editorial time to shot index.
    """
    shots = doc.get("shots") or []
    videos = []
    spans = []
    previous_video = None
    cursor = 0.0
    for index, raw in enumerate(shots):
        segment = _migrate_structured_segment(dict(raw or {}), index)
        video = _segment_best_video(segment)
        if _segment_is_hidden_anchor(segment) or not _segment_in_final(segment):
            if video is not None:
                previous_video = video
            continue
        if video is None:
            break
        piece = video
        continuity = _effective_segment_continuity(shots, index, segment)
        if index > 0 and str(segment.get("source_mode", "生成视频")) == "生成视频" and continuity == "续写上一段":
            preferred = int(segment.get("guide_frames", 22) or 22)
            actual = preferred
            if previous_video is not None:
                try:
                    guide = _tail_guide(previous_video.get_components().images, preferred)
                    if guide is not None:
                        actual = int(guide.shape[0])
                except Exception:
                    pass
            piece, _ = _trim_video_head_frames(video, actual)
        count, fps = _video_frame_count(piece)
        if count <= 0:
            break
        duration = count / max(fps, 1e-6)
        spans.append({"index": index, "start": cursor, "end": cursor + duration})
        cursor += duration
        videos.append(piece)
        previous_video = video
    if not videos:
        raise ValueError("当前还没有从时间线开头连续生成的正式视频，无法局部重绘。")
    from comfy_extras import nodes_video
    current = videos[-1]
    if len(videos) > 1:
        joined = nodes_video.ConcatenateVideo.execute(videos={"video": videos}, codec=["auto"], complete_audio=None)
        current = _extract_video_result(joined) or current
    current, _ = _apply_timeline_edits_to_video(current, doc)
    total, fps = _video_frame_count(current)
    return current, spans, total / max(fps, 1e-6)


def _align_h3_frame_count(frame_count: int) -> int:
    # H3 accepts 17k+5 lengths; its current native node documents ~124-362
    # frames as the trained generation range. Keep local redraw inside it.
    n = max(124, int(frame_count))
    k = max(0, (n - 5 + 16) // 17)
    return 17 * k + 5


def _pad_frames_to_h3(frames, target: int):
    import torch
    n = int(frames.shape[0])
    if n == target:
        return frames
    if n > target:
        return frames[:target]
    if n <= 0:
        raise ValueError("局部重绘窗口没有有效帧。")
    return torch.cat([frames, frames[-1:].repeat(target - n, 1, 1, 1)], dim=0)


def _pad_audio_to_seconds(audio, seconds: float):
    if not isinstance(audio, dict):
        return audio
    waveform = audio.get("waveform")
    sr = int(audio.get("sample_rate", 0) or 0)
    if waveform is None or sr <= 0 or not hasattr(waveform, "shape"):
        return audio
    import torch
    target = max(1, int(round(float(seconds) * sr)))
    have = int(waveform.shape[-1])
    if have < target:
        waveform = torch.nn.functional.pad(waveform, (0, target - have))
    elif have > target:
        waveform = waveform[..., :target]
    return {**audio, "waveform": waveform}


def _h3_video_token_mask(video_latent, edit_start_frame: int, edit_end_frame: int):
    """Build MiniMax H3's temporal-token mask: 0 preserve, 1 regenerate."""
    import torch
    # Read the native mapping from the installed ComfyUI so this stays aligned
    # with MiniMax H3 core instead of hard-coding a private temporal layout.
    try:
        from comfy.ldm.minimax.model import FRAME_PER_TOKEN as frame_per_token
    except Exception:
        frame_per_token = (1, 4, 4, 4, 4)
    t = int(video_latent.shape[2])
    mask = torch.zeros(
        (1, 1, t, int(video_latent.shape[3]), int(video_latent.shape[4])),
        device=video_latent.device, dtype=torch.float32,
    )
    cursor = 0
    for token in range(t):
        width = frame_per_token[token % len(frame_per_token)]
        token_start, token_end = cursor, cursor + width
        if token_end > int(edit_start_frame) and token_start < int(edit_end_frame):
            mask[:, :, token] = 1.0
        cursor = token_end
    return mask


def _timeline_edit_segment_index(spans: list[dict[str, Any]], start: float, end: float) -> int:
    mid = (float(start) + float(end)) * 0.5
    for span in spans:
        if float(span["start"]) <= mid < float(span["end"]):
            return int(span["index"])
    return int(spans[-1]["index"]) if spans else 0


def _timeline_edit_conditioning(shot_context: dict[str, Any], project: dict[str, Any], bundle: dict[str, Any],
                                source_frames, source_audio, width: int, height: int, length: int,
                                local_start_seconds: float, local_end_seconds: float, instruction: str,
                                mode: str):
    try:
        from comfy_extras import nodes_minimax_h3 as h3
    except Exception as exc:
        raise RuntimeError("时间轴局部重绘需要最新 ComfyUI 原生 MiniMax H3 节点，请先更新 ComfyUI。") from exc
    resource_ctx = shot_context.get("resource_context") or {}
    original_prompt = str(shot_context.get("prompt", "") or "").strip()
    mode_rule = {
        "局部修补": "Keep motion, pose, camera path and timing as close to the source as possible; repair only the requested visual problem.",
        "动作重绘": "The selected interval may change action and pose, but must enter from the preserved prefix and return smoothly to the preserved suffix.",
        "剧情重生成": "The selected interval may substantially change action/story content while strictly matching the preserved boundary states.",
    }.get(str(mode), "The selected interval may be redrawn while preserving both boundary states.")

    images = list(resource_ctx.get("images") or [])
    videos = list(resource_ctx.get("videos") or [])
    audios = list(resource_ctx.get("audios") or [])
    ref_images = {f"ref_image_{i}": _avs_load_image_tensor(str(a.get("path", ""))) for i, a in enumerate(images[:9])}

    # Preserve the original shot's Video ordinals.  The source timeline window is
    # appended as the last ref video rather than inserted as Video 1; otherwise a
    # user's existing <Video 1>/<Video 2> tags would silently point at the wrong
    # material during a local edit. One of the three H3 video-reference slots is
    # reserved for this timeline source.
    ref_videos = {}
    for asset in videos[:3]:
        try:
            key = f"ref_video_{len(ref_videos)}"
            ref_videos[key] = _avs_load_video_frames(str(asset.get("path", "")), max_frames=length, target_fps=24.0)
        except Exception:
            pass
    source_video_tag = None
    if len(ref_videos) < 3:
        source_ref_index = len(ref_videos)
        ref_videos[f"ref_video_{source_ref_index}"] = source_frames
        source_video_tag = source_ref_index + 1

    # Do not attach the source soundtrack as a REF2VA audio reference: the audio
    # latent itself is hard-locked and final patching preserves the base audio.
    # Omitting it also keeps the user's existing <Audio N> ordinals unchanged.
    ref_video_audios = {}
    ref_audios = {}
    for i, asset in enumerate(audios[:3]):
        try:
            ref_audios[f"ref_audio_{i}"] = _avs_load_audio(str(asset.get("path", "")))
        except Exception:
            pass

    if source_video_tag is not None:
        source_note = (
            f"<Video {source_video_tag}> is the exact original local timeline window and is the primary continuity reference.\n"
            f"Only redesign the interval from {local_start_seconds:.3f}s to {local_end_seconds:.3f}s inside <Video {source_video_tag}>. "
        )
    else:
        source_note = (
            "The encoded source timeline latent and boundary guides are the exact primary continuity reference. "
            f"Only redesign the local interval from {local_start_seconds:.3f}s to {local_end_seconds:.3f}s. "
        )
    prompt = (
        original_prompt
        + "\n\n[TIMELINE LOCAL REDRAW]\n"
        + source_note
        + "Frames before and after that interval are locked context: preserve identity, wardrobe, scene geometry, lighting, camera axis, framing, motion trajectory and boundary pose exactly.\n"
        + mode_rule + "\n"
        + "Requested change: " + (str(instruction or "").strip() or "Improve the selected interval while preserving continuity.")
    )

    out = h3.MiniMaxH3ReferenceToVideo.execute(
        clip=bundle["clip"], vae=bundle["video_vae"], audio_vae=bundle["audio_vae"],
        prompt=prompt, width=int(width), height=int(height), length=int(length),
        ref_image_size=str(project.get("ref_image_size", "match")),
        ref_images=ref_images, ref_videos=ref_videos,
        ref_video_audios=ref_video_audios, ref_audios=ref_audios,
    )
    positive, target_latent = _avs_node_result(out)[:2]
    active = (shot_context.get("shot") or {}).get("selected_character_refmods")
    if active is not None:
        project = {**project, "selected_character_refmods": active}
    positive = apply_character_refmods(positive, project, resource_ctx, True)
    return positive, target_latent, prompt


@model_session
def _generate_timeline_local_redraw(resource_db: dict[str, Any], first_profile: dict[str, Any], timeline_json: str,
                                    project_name: str, output_prefix: str, unique_id=None, **kwargs):
    """Generate one arbitrary cross-segment timeline patch using H3 temporal inpaint."""
    import gc
    import nodes
    import torch
    doc = _parse_timeline_doc(timeline_json)
    pending = dict(doc.get("pending_edit") or {})
    try:
        start = float(pending.get("start"))
        end = float(pending.get("end"))
    except Exception as exc:
        raise ValueError("请先在剪映式时间轴上拖选需要修改的范围。") from exc
    if start < 0 or end <= start:
        raise ValueError("局部重绘时间范围无效，请重新拖选。")
    mode = str(pending.get("mode", "动作重绘") or "动作重绘")
    instruction = str(pending.get("prompt", "") or "").strip()
    context_seconds = max(0.35, min(float(pending.get("context", 0.85) or 0.85), 2.5))

    source_video, spans, ready_seconds = _compose_ready_timeline_video(doc)
    if end > ready_seconds + 1e-3:
        raise ValueError(
            f"当前从开头连续可编辑到 {ready_seconds:.2f}s，但你选择到 {end:.2f}s。"
            "请先生成缺失的视频段，再修改后面的时间。"
        )
    comps = source_video.get_components()
    frames = comps.images
    if frames is None or int(frames.shape[0]) < 5:
        raise ValueError("当前连续时间线太短，无法做 H3 局部重绘。")
    fps = float(getattr(comps, "frame_rate", 24.0) or 24.0)
    total = int(frames.shape[0])
    sel_start = max(0, min(int(round(start * fps)), total - 1))
    sel_end = max(sel_start + 1, min(int(round(end * fps)), total))
    # Keep one H3 edit window within the same 15.1s budget used by the Studio.
    max_window_frames = int(round(15.1 * fps))
    selected_frames = sel_end - sel_start
    if selected_frames > max_window_frames:
        raise ValueError(
            f"单次局部重绘最多约 15 秒；当前选择 {(selected_frames / max(fps, 1e-6)):.2f}s。"
            "请把超长范围分成两次拖选。"
        )
    ctx_frames = int(round(context_seconds * fps))
    # If selection itself is long, automatically shrink context instead of
    # rejecting a perfectly valid edit range.
    max_each_side = max(0, (max_window_frames - selected_frames) // 2)
    ctx_frames = min(ctx_frames, max_each_side)
    win_start = max(0, sel_start - ctx_frames)
    win_end = min(total, sel_end + ctx_frames)
    # H3 is most reliable in its trained >=124-frame range. Expand the clean
    # context window to ~5.17s whenever enough already-generated timeline exists.
    min_window = min(124, total)
    if win_end - win_start < min_window:
        need = min_window - (win_end - win_start)
        add_before = min(win_start, (need + 1) // 2)
        win_start -= add_before
        need -= add_before
        add_after = min(total - win_end, need)
        win_end += add_after
        need -= add_after
        if need > 0:
            extra_before = min(win_start, need)
            win_start -= extra_before
    raw_count = win_end - win_start
    valid_count = _align_h3_frame_count(raw_count)
    # Alignment may add up to 16 frames. If it crosses the 15.1s cap, trim
    # context from the end/then start until the aligned window fits.
    max_valid = 17 * max(0, (max_window_frames - 5) // 17) + 5
    if valid_count > max_valid:
        valid_count = max_valid
        raw_target = min(raw_count, valid_count)
        excess = max(0, raw_count - raw_target)
        cut_after = min(excess, max(0, win_end - sel_end))
        win_end -= cut_after
        excess -= cut_after
        win_start += min(excess, max(0, sel_start - win_start))
        raw_count = win_end - win_start

    window_frames = frames[win_start:win_end]
    window_audio = _slice_audio_frames(comps.audio, win_start, win_end, fps)
    window_frames = _pad_frames_to_h3(window_frames, valid_count)
    window_audio = _pad_audio_to_seconds(window_audio, valid_count / max(fps, 1e-6))
    local_start_frame = sel_start - win_start
    local_end_frame = sel_end - win_start
    local_start_seconds = local_start_frame / max(fps, 1e-6)
    local_end_seconds = local_end_frame / max(fps, 1e-6)

    segment_index = _timeline_edit_segment_index(spans, start, end)
    project_kwargs = {**kwargs, "project_name": project_name, "output_prefix": output_prefix}
    first_project = _project_from_external_profile(resource_db, project_kwargs, first_profile)
    # Local timeline rewrite always needs REF2VA because the original window is Video 1.
    first_project["generation_mode"] = "多素材参考"
    # Compile the selected segment's identity/reference assets without inheriting
    # its original continuation dependency. The edited source window itself is
    # the continuity authority for this operation.
    edit_doc = {**doc, "shots": [dict(x or {}) for x in (doc.get("shots") or [])]}
    if 0 <= segment_index < len(edit_doc["shots"]):
        edit_doc["shots"][segment_index]["continuity"] = "独立生成"
    shot_context = _compile_studio_shot_context(resource_db, first_project, edit_doc, segment_index, previous_video=None)
    # Cross-segment selections may touch different character/Picture bindings on
    # each side of the old segment boundary. Keep the primary segment's packed
    # Picture order intact, then append unique neighboring refs as supplemental
    # identity/scene references.
    overlap_indices = [int(sp["index"]) for sp in spans if float(sp["end"]) > start and float(sp["start"]) < end]
    primary_rc = dict(shot_context.get("resource_context") or {})
    for key, limit in (("images", 9), ("videos", 3), ("audios", 3)):
        merged = list(primary_rc.get(key) or [])
        seen = {str(x.get("path", "")) for x in merged if isinstance(x, dict)}
        for other_index in overlap_indices:
            if other_index == segment_index or len(merged) >= limit:
                continue
            try:
                neighbor_doc = {**doc, "shots": [dict(x or {}) for x in (doc.get("shots") or [])]}
                neighbor_doc["shots"][other_index]["continuity"] = "独立生成"
                neighbor = _compile_studio_shot_context(resource_db, first_project, neighbor_doc, other_index, previous_video=None)
                for asset in (neighbor.get("resource_context") or {}).get(key) or []:
                    path = str(asset.get("path", "")) if isinstance(asset, dict) else ""
                    if path and path not in seen:
                        merged.append(asset); seen.add(path)
                        if len(merged) >= limit:
                            break
            except Exception:
                continue
        primary_rc[key] = merged[:limit]
    shot_context = {**shot_context, "resource_context": primary_rc}
    bundle = _load_bundle(first_project, True)
    h, w = int(window_frames.shape[1]), int(window_frames.shape[2])

    positive, target_latent, final_prompt = run_stage(
        "时间轴局部重绘参考编码", _timeline_edit_conditioning,
        shot_context, first_project, bundle, window_frames, window_audio,
        w, h, valid_count, local_start_seconds, local_end_seconds, instruction, mode,
    )

    # Encode the exact source window into H3 AV latent, then install a two-stream
    # nested mask. Video rows in the selected range regenerate; all context and
    # the complete audio stream stay clean/frozen.
    video_latent = nodes.VAEEncode().encode(bundle["video_vae"], window_frames)[0]
    try:
        from comfy_extras import nodes_lt, nodes_audio, nodes_minimax_h3 as h3
        target_parts = _avs_node_result(nodes_lt.LTXVSeparateAVLatent.execute(target_latent))
        blank_audio_latent = target_parts[1]
        if window_audio is not None:
            try:
                audio_latent = _avs_node_result(nodes_audio.VAEEncodeAudio.execute(vae=bundle["audio_vae"], audio=window_audio))[0]
            except Exception:
                audio_latent = blank_audio_latent
        else:
            audio_latent = blank_audio_latent
        av_latent = _avs_node_result(nodes_lt.LTXVConcatAVLatent.execute(video_latent=video_latent, audio_latent=audio_latent))[0]
    except Exception as exc:
        raise RuntimeError("时间轴局部重绘需要最新 ComfyUI 的 H3 AV Latent 节点，请更新 ComfyUI。") from exc

    samples = av_latent.get("samples")
    if samples is None or not getattr(samples, "is_nested", False):
        raise RuntimeError("当前 H3 编码没有返回 Nested AV Latent；请更新 ComfyUI 到支持 H3 temporal mask 的版本。")
    try:
        parts = list(samples.unbind()) if hasattr(samples, "unbind") else list(samples.tensors)
        video_stream, audio_stream = parts[0], parts[1]
        video_mask = _h3_video_token_mask(video_stream, local_start_frame, local_end_frame)
        # Use the audio stream's exact shape; some third-party sampler hooks are
        # less tolerant of broadcast-only nested masks.
        audio_mask = torch.zeros_like(audio_stream, dtype=torch.float32)
        import comfy.nested_tensor
        av_latent = dict(av_latent)
        av_latent["noise_mask"] = comfy.nested_tensor.NestedTensor((video_mask, audio_mask))
    except Exception as exc:
        raise RuntimeError("无法建立 MiniMax H3 双流时间 Mask；请更新 ComfyUI 后再试。") from exc

    # Boundary guides reinforce the transition in addition to the clean masked
    # context. Prefer a valid 22-frame clip (or 5 / 1 when near an edge).
    def _guide_len(available: int) -> int:
        if available >= 22:
            return 22
        if available >= 5:
            return 5
        return 1 if available >= 1 else 0
    try:
        before_n = _guide_len(local_start_frame)
        if before_n > 0:
            before_at = max(0, local_start_frame - before_n)
            positive = _avs_node_result(h3.MiniMaxH3AddGuide.execute(
                positive=positive, latent=target_latent, frame_idx=before_at,
                vae=bundle["video_vae"], audio_vae=bundle["audio_vae"],
                image=window_frames[before_at:before_at + before_n], audio=None,
            ))[0]
        after_n = _guide_len(valid_count - local_end_frame)
        if after_n > 0:
            after_at = min(valid_count - after_n, local_end_frame)
            positive = _avs_node_result(h3.MiniMaxH3AddGuide.execute(
                positive=positive, latent=target_latent, frame_idx=after_at,
                vae=bundle["video_vae"], audio_vae=bundle["audio_vae"],
                image=window_frames[after_at:after_at + after_n], audio=None,
            ))[0]
    except Exception as exc:
        logging.warning("AVS timeline boundary guide skipped: %s", exc)

    unload(bundle["clip"])
    unload(bundle["video_vae"])
    unload(bundle["audio_vae"])
    gc.collect()
    try:
        import comfy.model_management as mm
        mm.soft_empty_cache()
    except Exception:
        pass
    seed = int(pending.get("seed", 0) or 0)
    if seed <= 0:
        seed = random.SystemRandom().randrange(0, 2**63 - 1)
    try:
        sampled = run_stage(
            "时间轴局部重绘采样", nodes.KSampler().sample,
            bundle["model"], seed,
            int(first_project.get("steps", 8)), float(first_project.get("cfg", 1.0)),
            str(first_project.get("sampler", "res_multistep")), str(first_project.get("scheduler", "simple")),
            positive, positive, av_latent, 1.0,
        )[0]
    except Exception as exc:
        msg = str(exc).lower()
        # A few old RNG/custom-node hooks replace ComfyUI's nested-noise path and
        # collapse H3 AV noise into a plain video tensor. Surface a useful error
        # instead of the opaque tensor-size mismatch produced by the sampler.
        if "size of tensor" in msg or "nested" in msg or "noise" in msg and "latent" in msg:
            raise RuntimeError(
                "H3 局部重绘的 Nested AV noise 采样失败。请先更新 ComfyUI；如果仍报 noise/latent 尺寸不匹配，"
                "请临时关闭会改写 prepare_noise 的旧版 smZNodes / efficiency RNG 插件后重试。"
            ) from exc
        raise
    del positive, av_latent, target_latent
    unload(bundle["model"])
    out_frames = _avs_safe_vae_decode(bundle["video_vae"], sampled)
    patch_needed = sel_end - sel_start
    patch_frames = out_frames[local_start_frame:local_start_frame + patch_needed]
    if int(patch_frames.shape[0]) <= 0:
        raise RuntimeError("局部重绘解码后没有得到选中范围的画面。")
    from comfy_extras import nodes_video
    patch_video = _extract_video_result(nodes_video.CreateVideo.execute(
        images=patch_frames, fps=fps, audio=None,
        bit_depth="auto", color_space="sRGB", codec="none",
    ))
    if patch_video is None:
        raise RuntimeError("局部重绘 CreateVideo 没有返回有效 VIDEO。")
    project_safe = re.sub(r"[^0-9A-Za-z_\-㐀-鿿]+", "_", str(project_name or "project")).strip("_") or "project"
    edit_id = str(pending.get("id") or f"edit-{int(time.time() * 1000)}")
    prefix = f"{output_prefix or 'AI_Video_Studio'}/{project_safe}/TIMELINE_EDITS/{edit_id}"
    ui_data = save_video(patch_video, prefix)
    meta = _find_saved_media(ui_data or {}) or {}
    record = {
        "id": edit_id, "start": round(start, 4), "end": round(end, 4),
        "mode": mode, "prompt": instruction, "context": context_seconds,
        "seed": seed, "result_video": meta, "enabled": True,
        "status": "完成", "segment_index": segment_index,
        "window_start": round(win_start / fps, 4), "window_end": round((win_start + valid_count) / fps, 4),
        "created_at": int(time.time()),
    }
    _send_segment_event(unique_id, -2, {
        "status": f"局部重绘完成｜{start:.2f}s–{end:.2f}s｜{mode}",
        "timeline_edit": record,
    })
    result = (patch_video,)
    if ui_data:
        return {"ui": ui_data, "result": result}
    return result


def _compose_final_video_from_doc(doc: dict[str, Any], project_name: str, output_prefix: str, unique_id=None):
    shots = doc.get("shots") or []
    if not shots:
        raise ValueError("导演工作台里没有视频段。")

    # v0.16.9 — production-only hidden spatial anchors.
    # Hidden anchors participate in the generation/continuation chain but are
    # excluded from delivery. Formal clips generated from an anchor still have
    # their AddGuide head removed, so the lock frames never leak into the movie.
    videos = []
    previous_video = None
    trimmed_total = 0
    trimmed_segments = 0
    hidden_total = 0
    hidden_ready = 0
    included_segments = 0

    for index, raw in enumerate(shots):
        segment = _migrate_structured_segment(dict(raw or {}), index)
        hidden = _segment_is_hidden_anchor(segment)
        include_final = _segment_in_final(segment)
        video = _segment_best_video(segment)

        if hidden or not include_final:
            hidden_total += 1
            if video is not None:
                hidden_ready += 1
                previous_video = video
            # Missing production-only anchors do not block delivery if all
            # formal clips are already rendered.
            continue

        if video is None:
            raise ValueError(f"视频段{index + 1}还没有可用视频，无法合成最终视频。")

        final_piece = video
        continuity = _effective_segment_continuity(shots, index, segment)
        if index > 0 and str(segment.get("source_mode", "生成视频")) == "生成视频" and continuity == "续写上一段":
            preferred = int(segment.get("guide_frames", 22) or 22)
            actual = preferred
            if previous_video is not None:
                try:
                    prev_comps = previous_video.get_components()
                    guide = _tail_guide(prev_comps.images, preferred)
                    if guide is not None:
                        actual = int(guide.shape[0])
                except Exception:
                    pass
            final_piece, removed = _trim_video_head_frames(video, actual)
            if removed > 0:
                trimmed_total += removed
                trimmed_segments += 1

        videos.append(final_piece)
        included_segments += 1
        previous_video = video

    if not videos:
        raise ValueError("时间线没有可进入成片的正式视频段。隐藏空间预热不会单独导出。")

    from comfy_extras import nodes_video
    final_video = videos[-1]
    if len(videos) > 1:
        combined = nodes_video.ConcatenateVideo.execute(videos={"video": videos}, codec=["auto"], complete_audio=None)
        final_video = _extract_video_result(combined) or final_video
    final_video, applied_edits = _apply_timeline_edits_to_video(final_video, doc)
    project_safe = re.sub(r"[^0-9A-Za-z_\-㐀-鿿]+", "_", str(project_name or "project")).strip("_") or "project"
    prefix = f"{output_prefix or 'AI_Video_Studio'}/{project_safe}/FINAL_APPROVED"
    ui_data = save_video(final_video, prefix)
    final_meta = _find_saved_media(ui_data or {})
    status = f"最终视频完成｜正式段 {included_segments}"
    if hidden_total:
        status += f"｜隐藏预热已排除 {hidden_total} 段（已生成 {hidden_ready}）"
    if trimmed_segments:
        status += f"｜续写/预热去重 {trimmed_segments} 段 / {trimmed_total} 帧"
    if applied_edits:
        status += f"｜时间轴局部重绘 {applied_edits} 处"
    _send_segment_event(unique_id, -1, {"status": status, "final_video": final_meta or {}, "hidden_anchor_count": hidden_total})
    result = (final_video,)
    if ui_data:
        return {"ui": ui_data, "result": result}
    return result


def _send_segment_event(unique_id: Any, index: int, payload: dict[str, Any]):
    if unique_id is None:
        return
    try:
        from server import PromptServer
        PromptServer.instance.send_sync("avs_segment_result", {"node_id": str(unique_id), "index": int(index), **payload})
    except Exception:
        pass


class AVSDirectorStudio:
    """Self-contained timeline workbench with complete prompt + in-card video results."""

    @classmethod
    def INPUT_TYPES(cls):
        diffusion = _model_options("diffusion_models")
        clips = _model_options("text_encoders")
        vaes = _model_options("vae")
        loras = ["不使用"] + _files("loras")
        default_doc = json.dumps(_default_timeline_doc(), ensure_ascii=False)
        return {
            "required": {
                "resource_db": ("AVS_RESOURCE_DB",),
                "timeline_json": ("STRING", {"default": default_doc, "multiline": True}),
                "selected_index": ("INT", {"default": 0, "min": 0, "max": 999}),
                "generation_scope": (["当前视频段", "生成到当前视频段", "全部时间线"], {"default": "当前视频段"}),
                "language": (["中文", "English"], {"default": "中文"}),
                "project_name": ("STRING", {"default": "我的AI视频项目"}),
                "project_type": (["短剧", "漫剧", "舞蹈", "打斗", "广告", "其他"], {"default": "短剧"}),
                "visual_style": ("STRING", {"default": "电影级画面，主体清晰，光影自然，动作稳定", "multiline": True}),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4"], {"default": "16:9"}),
                "resolution": (["快速预览 480P", "快速人物 544P", "标准 720P", "原生 768"], {"default": "快速预览 480P"}),
                "consistency": (["标准", "强", "最高"], {"default": "强"}),
                "audio_mode": (["环境音（无配乐）", "完全静音", "H3原生音频"], {"default": "环境音（无配乐）"}),
                "quality_preset": (["快速预览", "标准质量", "高质量"], {"default": "快速预览"}),
                "output_prefix": ("STRING", {"default": "AI_Video_Studio"}),
                "fl2va_model": (diffusion, {"default": "自动检测"}),
                "ref2va_model": (diffusion, {"default": "自动检测"}),
                "clip_model": (clips, {"default": "自动检测"}),
                "video_vae_model": (vaes, {"default": "自动检测"}),
                "audio_vae_model": (vaes, {"default": "自动检测"}),
                "lora_name": (loras, {"default": "不使用"}),
                "lora_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05}),
                "weight_dtype": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"], {"default": "default"}),
                "steps_override": ("INT", {"default": 0, "min": 0, "max": 100}),
                "cfg": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1}),
                "sampler": (["res_multistep", "euler", "euler_cfg_pp", "dpmpp_2m", "dpmpp_2m_sde"], {"default": "res_multistep"}),
                "scheduler": (["simple", "beta", "normal", "sgm_uniform", "karras"], {"default": "simple"}),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "shift_video": ("FLOAT", {"default": 12.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "shift_audio": ("FLOAT", {"default": 3.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "ref_image_size": (["match", "max"], {"default": "match"}),
                "max_images": ("INT", {"default": 9, "min": 0, "max": 9}),
                "max_videos": ("INT", {"default": 3, "min": 0, "max": 3}),
                "max_audios": ("INT", {"default": 3, "min": 0, "max": 3}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("最终视频（可选）",)
    FUNCTION = "generate"
    CATEGORY = "AI Video Studio/01 导演工作台"
    DESCRIPTION = (
        "完整导演工作台：每个视频段直接输入一份完整 H3 提示词；视频段可选择“生成视频”或“已有视频”。"
        "生成后视频直接回显在时间线卡片；已有视频也直接放进卡片，并可作为下一段续写来源。整个生成流程都在本节点完成。"
    )
    OUTPUT_NODE = True

    @model_session
    def generate(self, resource_db: dict[str, Any], timeline_json: str, selected_index: int, generation_scope: str, unique_id=None, **kwargs):
        if not isinstance(resource_db, dict):
            raise ValueError("RESOURCE_DB 无效，请连接 AI视频工作室｜永久资源库。")
        doc = _parse_timeline_doc(timeline_json)
        shots = doc.get("shots") or []
        if not shots:
            raise ValueError("导演工作台里没有视频段。")
        selected = max(0, min(int(selected_index), len(shots) - 1))
        project = _timeline_project_from_kwargs(resource_db, kwargs)
        scope = str(generation_scope or "当前视频段")
        if scope == "当前视频段":
            indices = [selected]
        elif scope == "生成到当前视频段":
            indices = list(range(0, selected + 1))
        else:
            indices = list(range(len(shots)))

        # v0.16.6 — smart continuation dependency resolution.
        # Clicking “生成当前一采” on a continuation shot no longer hard-fails
        # when its predecessor is missing.  We automatically generate the
        # minimal missing dependency chain in sequence, stopping at the nearest
        # approved video or an independent/new-scene/new-episode boundary.
        prev = None
        if scope == "当前视频段":
            indices, prev = _continuation_chain_for_current(shots, selected, doc)
            if len(indices) > 1:
                _send_segment_event(unique_id, selected, {
                    "status": f"自动补齐续写链：视频段{indices[0] + 1} → 视频段{selected + 1}",
                    "auto_dependency_chain": [i + 1 for i in indices],
                })
        elif indices and indices[0] > 0:
            first = _migrate_structured_segment(dict(shots[indices[0]] or {}), indices[0])
            if _effective_segment_continuity(shots, indices[0], first) == "续写上一段":
                prev = _segment_video_with_timeline_edits_for_continuation(doc, indices[0] - 1)
                if prev is None:
                    prev = _segment_best_video(_migrate_structured_segment(dict(shots[indices[0] - 1] or {}), indices[0] - 1))

        last_video = None
        generator = AVSOneClickGenerate()
        total_count = len(indices)
        batch_mode = scope in {"生成到当前视频段", "全部时间线"}
        generated_count = 0
        skipped_count = 0
        ui_data = None

        for order, index in enumerate(indices, start=1):
            segment = _migrate_structured_segment(dict(shots[index] or {}), index)
            progress_status = f"串行生成中 {order}/{total_count}"
            _send_segment_event(unique_id, index, {
                "status": progress_status,
                "batch_mode": scope,
                "batch_current": order,
                "batch_total": total_count,
            })
            try:
                if segment.get("source_mode") == "已有视频":
                    video, existing = _segment_existing_video(segment)
                    last_video = video
                    prev = _segment_video_with_timeline_edits_for_continuation(doc, index) or video
                    skipped_count += 1
                    _send_segment_event(unique_id, index, {
                        "status": "已有视频",
                        "source_mode": "已有视频",
                        "existing_video": existing,
                        "batch_mode": scope,
                        "batch_current": order,
                        "batch_total": total_count,
                    })
                    continue

                existing_video = _segment_best_video(segment) if batch_mode else None
                if batch_mode and existing_video is not None:
                    last_video = existing_video
                    prev = _segment_video_with_timeline_edits_for_continuation(doc, index) or existing_video
                    skipped_count += 1
                    _send_segment_event(unique_id, index, {
                        "status": "已存在，已跳过",
                        "source_mode": "生成视频",
                        "batch_mode": scope,
                        "batch_current": order,
                        "batch_total": total_count,
                    })
                    continue

                ctx = _compile_studio_shot_context(resource_db, project, doc, index, prev)
                raw = generator.generate(ctx)
                video, prompt, _summary, ui_data = _unwrap_generation_result(raw)
                meta = _find_saved_media(ui_data or {})
                if not meta:
                    # Ensure a preview file exists even if the normal save UI payload was unavailable.
                    try:
                        from comfy_extras import nodes_video
                        preview_ui = nodes_video.save_video_preview(video)
                        preview_data = preview_ui.as_dict() if hasattr(preview_ui, "as_dict") else preview_ui
                        meta = _find_saved_media(preview_data)
                    except Exception:
                        meta = None
                last_video = video
                prev = video
                generated_count += 1
                actual_w, actual_h = video.get_dimensions()
                event = {"status": "已生成", "source_mode": "生成视频", "generation_summary": _summary,
                         "generation_dims": [actual_w, actual_h], "seed": ctx["seed"], "seed_mode": "固定",
                         "batch_mode": scope, "batch_current": order, "batch_total": total_count}
                if meta:
                    event["result_video"] = meta
                _send_segment_event(unique_id, index, event)
                del raw, ctx, video
            except Exception as exc:
                _send_segment_event(unique_id, index, {"status": "失败", "error": str(exc),
                                                       "batch_mode": scope, "batch_current": order, "batch_total": total_count})
                raise

        if last_video is None:
            raise RuntimeError("没有可用视频。")

        final_video = last_video
        final_ui = ui_data
        # v0.16.7 optimization: batch generation no longer auto-concatenates all
        # segments into a final video. Concatenation is reserved for the explicit
        # “合成最终视频” action, which avoids unnecessary extra execution.
        final_meta = _find_saved_media(final_ui or {}) if final_ui else {}
        _send_segment_event(unique_id, -1, {
            "status": "批量串行完成" if batch_mode else "当前视频段完成",
            "final_video": final_meta or {},
            "batch_mode": scope,
            "batch_total": total_count,
            "batch_generated": generated_count,
            "batch_skipped": skipped_count,
            "batch_summary": f"{scope}完成：共{total_count}段，实际生成{generated_count}段，复用/跳过{skipped_count}段",
        })

        result = (final_video,)
        if final_ui:
            return {"ui": final_ui, "result": result}
        return result


# New primary node. Older director nodes remain registered for workflow compatibility.
NODE_CLASS_MAPPINGS["AVSDirectorStudio"] = AVSDirectorStudio
NODE_DISPLAY_NAME_MAPPINGS["AVSDirectorStudio"] = "AI视频工作室｜导演工作台"


# ---------------------------------------------------------------------------
# v0.12.0 — external model profiles + approve-first-pass -> HD second pass
# ---------------------------------------------------------------------------

class AVSH3ModelProfile:
    """External H3 model/LoRA/sampling profile used by the Director workbench."""

    @classmethod
    def INPUT_TYPES(cls):
        diffusion = _model_options("diffusion_models")
        clips = _model_options("text_encoders")
        vaes = _model_options("vae")
        loras = ["不使用"] + _files("loras")
        return {
            "required": {
                "配置名称": ("STRING", {"default": "H3 一采模型"}),
                "FL2VA模型": (diffusion, {"default": "自动检测"}),
                "REF2VA模型": (diffusion, {"default": "自动检测"}),
                "CLIP模型": (clips, {"default": "自动检测"}),
                "视频VAE": (vaes, {"default": "自动检测"}),
                "音频VAE": (vaes, {"default": "自动检测"}),
                "LoRA1": (loras, {"default": "不使用"}),
                "LoRA1强度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05}),
                "LoRA2": (loras, {"default": "不使用"}),
                "LoRA2强度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05}),
                "LoRA3": (loras, {"default": "不使用"}),
                "LoRA3强度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05}),
                "LoRA4": (loras, {"default": "不使用"}),
                "LoRA4强度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05}),
                "权重精度": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"], {"default": "default"}),
                "Steps": ("INT", {"default": 8, "min": 1, "max": 100, "step": 1}),
                "CFG": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1}),
                "采样器": (["res_multistep", "euler", "euler_cfg_pp", "dpmpp_2m", "dpmpp_2m_sde"], {"default": "res_multistep"}),
                "调度器": (["simple", "beta", "normal", "sgm_uniform", "karras"], {"default": "simple"}),
                "降噪": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "视频Shift": ("FLOAT", {"default": 12.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "音频Shift": ("FLOAT", {"default": 3.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "参考图尺寸": (["match", "max"], {"default": "match"}),
            }
        }

    RETURN_TYPES = ("AVS_H3_MODEL_PROFILE", "STRING")
    RETURN_NAMES = ("H3模型配置", "配置摘要")
    FUNCTION = "build"
    CATEGORY = "AI Video Studio/02 模型配置"
    DESCRIPTION = "外接 H3 模型配置：UNet/CLIP/VAE/多LoRA/采样参数全部在这里设置，再接进导演工作台。支持最多 4 个 LoRA 叠加，可分别放一个一采配置和一个二采配置。"

    def build(self, **kwargs):
        profile = {
            "name": str(kwargs.get("配置名称", "H3模型配置") or "H3模型配置"),
            "fl2va_model": kwargs.get("FL2VA模型", "自动检测"),
            "ref2va_model": kwargs.get("REF2VA模型", "自动检测"),
            "clip_model": kwargs.get("CLIP模型", "自动检测"),
            "video_vae_model": kwargs.get("视频VAE", "自动检测"),
            "audio_vae_model": kwargs.get("音频VAE", "自动检测"),
            "lora_name": kwargs.get("LoRA", "不使用"),
            "lora_strength": float(kwargs.get("LoRA强度", 1.0)),
            "weight_dtype": kwargs.get("权重精度", "default"),
            "steps": int(kwargs.get("Steps", 8)),
            "steps_override": int(kwargs.get("Steps", 8)),
            "cfg": float(kwargs.get("CFG", 1.0)),
            "sampler": kwargs.get("采样器", "res_multistep"),
            "scheduler": kwargs.get("调度器", "simple"),
            "denoise": float(kwargs.get("降噪", 1.0)),
            "shift_video": float(kwargs.get("视频Shift", 12.0)),
            "shift_audio": float(kwargs.get("音频Shift", 3.0)),
            "ref_image_size": kwargs.get("参考图尺寸", "match"),
            "quality_preset": "外接配置",
            "max_images": 9, "max_videos": 3, "max_audios": 3,
        }
        summary = (
            f"{profile['name']}｜FL2VA {profile.get('fl2va_model')}｜REF2VA {profile.get('ref2va_model')}\n"
            f"LoRA {profile.get('lora_name')} × {profile.get('lora_strength', 1.0):.2f}｜"
            f"Steps {profile.get('steps')}｜CFG {profile.get('cfg')}｜{profile.get('sampler')} / {profile.get('scheduler')}"
        )
        return (profile, summary)


class AVSH3RefineProfile:
    """External second-pass HD/refine settings."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模式": (["二采高清", "同分辨率精修"], {"default": "二采高清"}),
                "目标清晰度": (["720P", "1080P", "1.5x", "2x"], {"default": "1080P"}),
                "放大算法": (["bicubic", "bilinear", "nearest"], {"default": "bicubic"}),
                "二采步数": ("INT", {"default": 4, "min": 1, "max": 30, "step": 1}),
                "二采CFG": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1}),
                "二采采样器": (["euler", "res_multistep", "dpmpp_2m", "dpmpp_2m_sde"], {"default": "euler"}),
                "二采调度器": (["beta", "simple", "normal", "sgm_uniform", "karras"], {"default": "beta"}),
                "二采降噪": ("FLOAT", {"default": 0.20, "min": 0.01, "max": 1.0, "step": 0.01}),
                "保留一采声音": ("BOOLEAN", {"default": True}),
                "Seed方式": (["沿用一采", "随机", "固定"], {"default": "沿用一采"}),
                "Seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    RETURN_TYPES = ("AVS_H3_REFINE_PROFILE", "STRING")
    RETURN_NAMES = ("二采高清设置", "设置摘要")
    FUNCTION = "build"
    CATEGORY = "AI Video Studio/02 模型配置"
    DESCRIPTION = "二采高清设置：一采视频满意后再点导演台里的“二采高清”。默认走内置像素/VAE重编码 + H3低降噪二采，并保留一采声音。"

    def build(self, **kwargs):
        profile = {
            "mode": kwargs.get("模式", "二采高清"),
            "target": kwargs.get("目标清晰度", "1080P"),
            "upscale_method": kwargs.get("放大算法", "bicubic"),
            "steps": int(kwargs.get("二采步数", 4)),
            "cfg": float(kwargs.get("二采CFG", 1.0)),
            "sampler": kwargs.get("二采采样器", "euler"),
            "scheduler": kwargs.get("二采调度器", "beta"),
            "denoise": float(kwargs.get("二采降噪", 0.20)),
            "preserve_audio": bool(kwargs.get("保留一采声音", True)),
            "seed_mode": kwargs.get("Seed方式", "沿用一采"),
            "seed": int(kwargs.get("Seed", 0)),
        }
        summary = (
            f"{profile['mode']}｜目标 {profile['target']}｜{profile['upscale_method']}｜"
            f"{profile['steps']}步｜denoise {profile['denoise']:.2f}｜{profile['sampler']} / {profile['scheduler']}"
        )
        return (profile, summary)


def _project_from_external_profile(resource_db: dict[str, Any], kwargs: dict[str, Any], model_profile: dict[str, Any]) -> dict[str, Any]:
    p = dict(model_profile or {})
    if not p:
        raise ValueError("没有连接一采 H3模型配置。请添加“AI视频工作室｜H3模型配置”并连接到导演工作台。")
    return {
        "version": 6,
        "resource_db": resource_db,
        "language": kwargs.get("language", "中文"),
        "project_name": kwargs.get("project_name", "我的AI视频项目"),
        "project_type": kwargs.get("project_type", "短剧"),
        "visual_style": kwargs.get("visual_style", "电影级画面，主体清晰，光影自然，动作稳定"),
        "aspect_ratio": kwargs.get("aspect_ratio", "16:9"),
        "resolution": kwargs.get("resolution", "快速预览 480P"),
        "default_seconds": 5.0,
        "consistency": kwargs.get("consistency", "强"),
        "audio_mode": kwargs.get("audio_mode", "环境音（无配乐）"),
        "quality_preset": "外接配置",
        "auto_save": True,
        "output_prefix": kwargs.get("output_prefix", "AI_Video_Studio"),
        "fl2va_model": p.get("fl2va_model", "自动检测"),
        "ref2va_model": p.get("ref2va_model", "自动检测"),
        "clip_model": p.get("clip_model", "自动检测"),
        "video_vae_model": p.get("video_vae_model", "自动检测"),
        "audio_vae_model": p.get("audio_vae_model", "自动检测"),
        "lora_name": p.get("lora_name", "不使用"),
        "lora_strength": float(p.get("lora_strength", 1.0)),
        "loras": p.get("loras", []),
        "character_refmods": p.get("character_refmods", []),
        "character_refmod_max_tokens": p.get("character_refmod_max_tokens", 32768),
        "weight_dtype": p.get("weight_dtype", "default"),
        "steps_override": int(p.get("steps", p.get("steps_override", 8)) or 8),
        "steps": int(p.get("steps", p.get("steps_override", 8)) or 8),
        "cfg": float(p.get("cfg", 1.0)),
        "sampler": p.get("sampler", "res_multistep"),
        "scheduler": p.get("scheduler", "simple"),
        "denoise": float(p.get("denoise", 1.0)),
        "shift_video": float(p.get("shift_video", 12.0)),
        "shift_audio": float(p.get("shift_audio", 3.0)),
        "ref_image_size": p.get("ref_image_size", "match"),
        "max_images": 9,
        "max_videos": 3,
        "max_audios": 3,
        "generation_mode": p.get("generation_mode", "自动"),
        "face_prompt": bool(p.get("face_prompt", False)),
        "face_repair_mode": str(p.get("face_repair_mode", "关闭") or "关闭"),
        "face_repair_strength": float(p.get("face_repair_strength", 0.65)),
        "face_repair_crop_size": int(p.get("face_repair_crop_size", 512) or 512),
        "face_repair_temporal": float(p.get("face_repair_temporal", 0.25)),
        "face_detection_size": int(p.get("face_detection_size", 1280) or 1280),
        "face_detection_score": float(p.get("face_detection_score", 0.65)),
        "face_repair_steps": int(p.get("face_repair_steps", 4) or 4),
        "face_repair_cfg": float(p.get("face_repair_cfg", 1.0)),
        "face_repair_sampler": p.get("face_repair_sampler", "res_multistep"),
        "face_repair_scheduler": p.get("face_repair_scheduler", "simple"),
        "face_repair_denoise": float(p.get("face_repair_denoise", 0.20)),
        "face_repair_context_frames": int(p.get("face_repair_context_frames", 22) or 22),
        "face_repair_near_denoise": float(p.get("face_repair_near_denoise", 0.06)),
        "face_repair_near_blend": float(p.get("face_repair_near_blend", 0.30)),
        "face_repair_near_refmod_cap": float(p.get("face_repair_near_refmod_cap", 0.25)),
        "fast_finish": bool(p.get("fast_finish", False)),
        "finish_target": p.get("finish_target", "1080P"),
        "upscale_model": p.get("upscale_model", "自动检测"),
        "face_enhance": bool(p.get("face_enhance", True)),
        "face_strength": float(p.get("face_strength", 0.55)),
        "finish_batch": int(p.get("finish_batch", 2)),
        "save_first_latent": bool(p.get("save_first_latent", True)),
        "face_only": bool(p.get("face_only", True)),
    }


def _snap32(v: float) -> int:
    return max(32, int(round(float(v) / 32.0) * 32))




def _resize_video_frames(images, width: int, height: int, mode: str):
    import torch.nn.functional as F
    if images is None or not hasattr(images, "shape") or len(images.shape) != 4:
        raise ValueError("二采源视频没有可用画面帧。")
    x = images.movedim(-1, 1)
    mode = str(mode or "bicubic")
    if mode == "nearest":
        y = F.interpolate(x, size=(int(height), int(width)), mode="nearest")
    else:
        y = F.interpolate(x, size=(int(height), int(width)), mode=mode, align_corners=False, antialias=True)
    return y.movedim(1, -1).clamp(0.0, 1.0)


def _conditioning_at_canvas(shot_context: dict[str, Any], project: dict[str, Any], width: int, height: int, length: int, bundle: dict[str, Any]):
    try:
        from comfy_extras import nodes_minimax_h3 as h3
    except Exception as exc:
        raise RuntimeError("当前 ComfyUI 没有可用的原生 MiniMax H3 节点，请更新 ComfyUI。") from exc
    resource_ctx = shot_context.get("resource_context") or {}
    images = list(resource_ctx.get("images") or [])
    videos = list(resource_ctx.get("videos") or [])
    audios = list(resource_ctx.get("audios") or [])
    prompt = str(shot_context.get("prompt", "") or "").strip()
    use_ref = _uses_reference(project, resource_ctx)
    if use_ref:
        ref_images = {f"ref_image_{i}": _avs_load_image_tensor(str(a.get("path", ""))) for i, a in enumerate(images[:9])}
        ref_videos = {f"ref_video_{i}": _avs_load_video_frames(str(a.get("path", "")), max_frames=length, target_fps=24.0) for i, a in enumerate(videos[:3])}
        ref_audios = {f"ref_audio_{i}": _avs_load_audio(str(a.get("path", ""))) for i, a in enumerate(audios[:3])}
        out = h3.MiniMaxH3ReferenceToVideo.execute(
            clip=bundle["clip"], vae=bundle["video_vae"], audio_vae=bundle["audio_vae"],
            prompt=prompt, width=width, height=height, length=length,
            ref_image_size=str(project.get("ref_image_size", "match")),
            ref_images=ref_images, ref_videos=ref_videos, ref_video_audios={}, ref_audios=ref_audios,
        )
    else:
        first_frame = None
        if project.get("generation_mode") == "首帧图生视频":
            first_frame = _avs_load_image_tensor(str(images[0].get("path", "")))
            prompt = re.sub(r"<Picture\s+\d+>", "the input image", prompt, flags=re.I)
        out = h3.MiniMaxH3ImageToVideo.execute(
            clip=bundle["clip"], vae=bundle["video_vae"], prompt=prompt,
            width=width, height=height, length=length, first_frame=first_frame, last_frame=None,
        )
    positive, latent = _avs_node_result(out)[:2]
    active = (shot_context.get("shot") or {}).get("selected_character_refmods")
    if active is not None:
        project = {**project, "selected_character_refmods": active}
    positive = apply_character_refmods(positive, project, resource_ctx, use_ref)
    return positive, latent




class AVSDirectorStudioV12(AVSDirectorStudio):
    @classmethod
    def INPUT_TYPES(cls):
        default_doc = json.dumps(_default_timeline_doc(), ensure_ascii=False)
        return {
            "required": {
                "resource_db": ("AVS_RESOURCE_DB",),
                "一采模型配置": ("AVS_H3_MODEL_PROFILE",),
                "timeline_json": ("STRING", {"default": default_doc, "multiline": True}),
                "selected_index": ("INT", {"default": 0, "min": 0, "max": 999}),
                "generation_scope": (["当前视频段", "二采当前视频段", "生成到当前视频段", "全部时间线", "合成最终视频"], {"default": "当前视频段"}),
                "language": (["中文", "English"], {"default": "中文"}),
                "project_name": ("STRING", {"default": "我的AI视频项目"}),
                "project_type": (["短剧", "漫剧", "舞蹈", "打斗", "广告", "其他"], {"default": "短剧"}),
                "visual_style": ("STRING", {"default": "电影级画面，主体清晰，光影自然，动作稳定", "multiline": True}),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4"], {"default": "16:9"}),
                "resolution": (["快速预览 480P", "快速人物 544P", "标准 720P", "原生 768"], {"default": "快速预览 480P"}),
                "consistency": (["标准", "强", "最高"], {"default": "强"}),
                "audio_mode": (["环境音（无配乐）", "完全静音", "H3原生音频"], {"default": "环境音（无配乐）"}),
                "output_prefix": ("STRING", {"default": "AI_Video_Studio"}),
            },
            "optional": {
                "二采模型配置": ("AVS_H3_MODEL_PROFILE",),
                "二采高清设置": ("AVS_H3_REFINE_PROFILE",),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    DESCRIPTION = (
        "导演工作台 v0.12：资源、完整H3提示词、一采预览、已有视频、续写都在本节点完成。"
        "模型/LoRA/采样参数从外部 H3模型配置接入；一采满意后可直接在卡片里点“二采高清”。"
    )

    def generate(self, 一采模型配置: dict[str, Any], timeline_json: str,
                 selected_index: int, generation_scope: str, language="中文", project_name="我的AI视频项目",
                 project_type="短剧", visual_style="电影级画面，主体清晰，光影自然，动作稳定",
                 aspect_ratio="16:9", resolution="快速预览 480P", consistency="强",
                 audio_mode="环境音（无配乐）", output_prefix="AI_Video_Studio",
                 二采模型配置=None, 二采高清设置=None, unique_id=None, resource_db=None):
        resource_db = resource_db or {"assets": [], "root": "", "version": 2}
        kwargs = {
            "language": language, "project_name": project_name, "project_type": project_type,
            "visual_style": visual_style, "aspect_ratio": aspect_ratio, "resolution": resolution,
            "consistency": consistency, "audio_mode": audio_mode, "output_prefix": output_prefix,
        }
        scope = str(generation_scope or "当前视频段")
        if scope == "合成最终视频":
            doc = _parse_timeline_doc(timeline_json)
            return _compose_final_video_from_doc(doc, project_name, output_prefix, unique_id=unique_id)
        if scope != "二采当前视频段":
            profile = dict(一采模型配置 or {})
            merged = {**kwargs, **profile}
            # Base workbench expects steps_override/quality_preset style fields.
            merged["steps_override"] = int(profile.get("steps", profile.get("steps_override", 8)) or 8)
            merged["quality_preset"] = "快速预览"
            return super().generate(
                resource_db=resource_db, timeline_json=timeline_json, selected_index=selected_index,
                generation_scope=scope, unique_id=unique_id, **merged,
            )

        if not isinstance(二采高清设置, dict):
            raise ValueError("没有连接“AI视频工作室｜二采高清设置”。")
        doc = _parse_timeline_doc(timeline_json)
        shots = doc.get("shots") or []
        if not shots:
            raise ValueError("导演工作台里没有视频段。")
        index = max(0, min(int(selected_index), len(shots) - 1))
        segment = _migrate_structured_segment(dict(shots[index] or {}), index)
        if _segment_is_hidden_anchor(segment):
            raise ValueError("隐藏空间预热是生产用定位段，不需要二采高清。请二采正式视频段。")
        source_video = _segment_result_video(segment)
        if source_video is None:
            raise ValueError("当前视频段还没有一采完成的视频。请先生成当前视频，满意后再点“二采高清”。")

        first_project = _project_from_external_profile(resource_db, kwargs, 一采模型配置)
        face_repair = 二采高清设置.get("mode") == "人脸局部修复（参考头像）"
        # Reuse the known first-pass loader choices, especially the quantized CLIP.
        second_profile = dict((一采模型配置 if face_repair else (二采模型配置 or 一采模型配置)) or {})
        second_project = _project_from_external_profile(resource_db, kwargs, second_profile)
        if face_repair:
            second_project["generation_mode"] = "多素材参考"
        prev = None
        if _effective_segment_continuity(shots, index, segment) == "续写上一段" and index > 0:
            try:
                prev = _segment_best_video(_migrate_structured_segment(dict(shots[index - 1] or {}), index - 1))
            except Exception:
                prev = None
        # 二采既支持“一采生成视频”，也支持“已有视频”。
        # _compile_studio_shot_context() 原本只允许 source_mode=生成视频，
        # 因此已有视频直接二采时会被错误拦截。这里仅为二采条件编译创建一个临时副本，
        # 不改变时间线里的真实 source_mode，也不会触发一采；只复用当前段的完整提示词、
        # Picture 引用、Seed 与续写设置来建立 H3 二采条件。
        compile_doc = dict(doc)
        compile_shots = list(shots)
        compile_segment = dict(segment)
        compile_segment["source_mode"] = "生成视频"
        compile_shots[index] = compile_segment
        compile_doc["shots"] = compile_shots
        ctx = _compile_studio_shot_context(resource_db, first_project, compile_doc, index, prev)
        selected_candidate = _segment_selected_candidate(segment)
        source_meta = (selected_candidate or segment).get("result_video") or {}
        if source_meta.get("filename"):
            ctx["first_latent_path"] = _saved_media_path(source_meta) + ".avs.safetensors"
        _send_segment_event(unique_id, index, {"status": "二采处理中"})
        try:
            hd_video, summary, dims = _second_pass_video(source_video, ctx, second_project, 二采高清设置)

            # Face repair is selected once in the first-pass profile. When a
            # second pass is requested, re-check the *final HD video* after the
            # second pass so the user never has to configure face repair twice.
            repair_mode = str(first_project.get("face_repair_mode", "关闭") or "关闭")
            if not face_repair and repair_mode != "关闭":
                try:
                    from .face_repair import repair_video
                    hd_video, face_summary, dims = repair_video(
                        hd_video, ctx, first_project, _face_repair_settings(first_project), _second_pass_video
                    )
                    summary = f"{summary}｜{face_summary}"
                except ValueError as exc:
                    if repair_mode == "自动":
                        summary = f"{summary}｜人脸修复：自动跳过｜{exc}"
                    else:
                        raise
            from comfy_extras import nodes_video
            project_safe = re.sub(r"[^0-9A-Za-z_\-\u3400-\u9fff]+", "_", str(project_name)).strip("_") or "project"
            seg_safe = re.sub(r"[^0-9A-Za-z_\-\u3400-\u9fff]+", "_", str(segment.get("name") or f"segment{index+1}")).strip("_") or f"segment{index+1}"
            prefix = f"{output_prefix}/{project_safe}/S{index+1:03d}_{seg_safe}_HD"
            ui_data = save_video(hd_video, prefix)
            meta = _find_saved_media(ui_data)
            event = {"status": "二采完成", "refine_status": "二采完成", "refine_summary": summary, "refine_dims": list(dims)}
            if meta:
                event["refined_video"] = meta
            _send_segment_event(unique_id, index, event)
            result = (hd_video,)
            if ui_data:
                return {"ui": ui_data, "result": result}
            return result
        except Exception as exc:
            _send_segment_event(unique_id, index, {"status": "二采失败", "error": str(exc)})
            raise


NODE_CLASS_MAPPINGS["AVSH3ModelProfile"] = AVSH3ModelProfile
NODE_DISPLAY_NAME_MAPPINGS["AVSH3ModelProfile"] = "AI视频工作室｜H3模型配置"
NODE_CLASS_MAPPINGS["AVSH3RefineProfile"] = AVSH3RefineProfile
NODE_DISPLAY_NAME_MAPPINGS["AVSH3RefineProfile"] = "AI视频工作室｜二采高清设置"
NODE_CLASS_MAPPINGS["AVSDirectorStudio"] = AVSDirectorStudioV12
NODE_DISPLAY_NAME_MAPPINGS["AVSDirectorStudio"] = "AI视频工作室｜导演工作台"

# ============================================================================
# v0.13.0 — Chainable LoRA + VRAM Auto Adapter
# ============================================================================


def _avs_lora_items(stack: Any) -> list[dict[str, Any]]:
    if not isinstance(stack, dict):
        return []
    raw = stack.get("items") or stack.get("loras") or []
    out = []
    if isinstance(raw, (list, tuple)):
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "") or "").strip()
            if name in {"", "不使用", "None", "none"} or not bool(item.get("enabled", True)):
                continue
            try:
                ms = float(item.get("model_strength", item.get("strength", 1.0)))
            except Exception:
                ms = 1.0
            try:
                cs = float(item.get("clip_strength", 1.0))
            except Exception:
                cs = 1.0
            out.append({"name": name, "model_strength": ms, "clip_strength": cs, "enabled": True})
    return out


class AVSLoRAUnit:
    """One LoRA per node. Chain as many nodes as desired using 上一个LoRA -> LoRA堆栈."""

    @classmethod
    def INPUT_TYPES(cls):
        loras = ["不使用"] + _files("loras")
        return {
            "required": {
                "LoRA": (loras, {"default": "不使用"}),
                "模型强度": ("FLOAT", {"default": 1.0, "min": -3.0, "max": 3.0, "step": 0.05}),
                "CLIP强度": ("FLOAT", {"default": 1.0, "min": -3.0, "max": 3.0, "step": 0.05}),
                "启用": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "上一个LoRA": ("AVS_LORA_STACK",),
            },
        }

    RETURN_TYPES = ("AVS_LORA_STACK", "STRING")
    RETURN_NAMES = ("LoRA堆栈", "LoRA摘要")
    FUNCTION = "build"
    CATEGORY = "AI Video Studio/02 模型配置"
    DESCRIPTION = "一个节点只配置一个 LoRA。需要多个就复制本节点并串联“上一个LoRA → LoRA堆栈”，数量不写死。"

    def build(self, LoRA="不使用", 模型强度=1.0, CLIP强度=1.0, 启用=True, 上一个LoRA=None):
        items = _avs_lora_items(上一个LoRA)
        name = str(LoRA or "不使用")
        if bool(启用) and name not in {"", "不使用", "None", "none"}:
            items.append({
                "name": name,
                "model_strength": float(模型强度),
                "clip_strength": float(CLIP强度),
                "enabled": True,
            })
        stack = {"version": 1, "items": items}
        summary = "未使用 LoRA" if not items else "\n".join(
            f"{i+1}. {x['name']}｜Model {x['model_strength']:.2f}｜CLIP {x['clip_strength']:.2f}"
            for i, x in enumerate(items)
        )
        return (stack, summary)



class AVSH3ModelProfileV13:
    """Clean first-pass H3 profile.

    Face repair is intentionally a *policy* selected here (关闭/自动/强制),
    while the repair itself runs after the generated video exists. This keeps
    the UI simple and lets 自动 judge the real face size/sharpness in the video.
    """

    @classmethod
    def INPUT_TYPES(cls):
        diffusion = _model_options("diffusion_models")
        clips = _model_options("text_encoders")
        vaes = _model_options("vae")
        return {
            "required": {
                "配置名称": ("STRING", {"default": "H3 一采模型"}),
                "FL2VA模型": (diffusion, {"default": "自动检测"}),
                "REF2VA模型": (diffusion, {"default": "自动检测"}),
                "CLIP模型": (clips, {"default": "自动检测"}),
                "视频VAE": (vaes, {"default": "自动检测"}),
                "音频VAE": (vaes, {"default": "自动检测"}),
                "权重精度": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"], {"default": "default"}),
                "Steps": ("INT", {"default": 8, "min": 1, "max": 100, "step": 1}),
                "CFG": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1}),
                "采样器": (["res_multistep", "euler", "euler_cfg_pp", "dpmpp_2m", "dpmpp_2m_sde"], {"default": "res_multistep"}),
                "调度器": (["simple", "beta", "normal", "sgm_uniform", "karras"], {"default": "simple"}),
                "降噪": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "视频Shift": ("FLOAT", {"default": 12.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "音频Shift": ("FLOAT", {"default": 3.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "参考图尺寸": (["match", "max"], {"default": "match"}),
            },
            "optional": {
                "LoRA堆栈": ("AVS_LORA_STACK",),
                "生成模式": (["自动", "首帧图生视频", "多素材参考"], {"default": "自动"}),
                "人脸修复": (["关闭", "自动", "近景稳定", "中远景重建", "强制"], {
                    "default": "自动",
                    "tooltip": "自动：近景清晰脸跳过，中远景按实际大小/清晰度修复；近景稳定：大脸也修，但只补细节（768、实际denoise约0.06、低融合、22帧连续上下文）；中远景重建：用于小脸；强制：按实际脸大小自动选稳定/重建档。",
                }),
                "保留一采latent": ("BOOLEAN", {"default": True}),
                "匹配Turbo参数": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("AVS_H3_MODEL_PROFILE", "STRING")
    RETURN_NAMES = ("H3模型配置", "配置摘要")
    FUNCTION = "build"
    CATEGORY = "AI Video Studio/02 模型配置"
    DESCRIPTION = "一采 H3 模型配置。人脸修复统一在这里选择：关闭 / 自动 / 近景稳定 / 中远景重建 / 强制；二采仍只负责高清。"

    def build(self, **kwargs):
        loras = _avs_lora_items(kwargs.get("LoRA堆栈"))
        steps = int(kwargs.get("Steps", 8))
        cfg = float(kwargs.get("CFG", 1.0))
        sampler = str(kwargs.get("采样器", "res_multistep"))
        scheduler = str(kwargs.get("调度器", "simple"))
        denoise = float(kwargs.get("降噪", 1.0))
        video_shift = float(kwargs.get("视频Shift", 12.0))
        audio_shift = float(kwargs.get("音频Shift", 3.0))
        if kwargs.get("匹配Turbo参数", False):
            turbo = next((x["name"].lower() for x in loras if "turbo" in x["name"].lower()), "")
            if turbo and ("8step" in turbo or "4step" in turbo):
                steps = 8 if "8step" in turbo else 4
                sampler, scheduler, denoise = "euler", "simple", 1.0
                video_shift = 6.0 if "768" in turbo else 12.0
                audio_shift = 3.0
        repair_mode = str(kwargs.get("人脸修复", "自动") or "自动")
        profile = {
            "name": str(kwargs.get("配置名称", "H3 一采模型") or "H3 一采模型"),
            "fl2va_model": kwargs.get("FL2VA模型", "自动检测"),
            "ref2va_model": kwargs.get("REF2VA模型", "自动检测"),
            "clip_model": kwargs.get("CLIP模型", "自动检测"),
            "video_vae_model": kwargs.get("视频VAE", "自动检测"),
            "audio_vae_model": kwargs.get("音频VAE", "自动检测"),
            "loras": loras,
            "lora_name": loras[0]["name"] if loras else "不使用",
            "lora_strength": float(loras[0]["model_strength"]) if loras else 1.0,
            "weight_dtype": kwargs.get("权重精度", "default"),
            "steps": steps,
            "steps_override": steps,
            "cfg": cfg,
            "sampler": sampler,
            "scheduler": scheduler,
            "denoise": denoise,
            "shift_video": video_shift,
            "shift_audio": audio_shift,
            "ref_image_size": kwargs.get("参考图尺寸", "match"),
            "quality_preset": "手动配置",
            "max_images": 9,
            "max_videos": 3,
            "max_audios": 3,
            "generation_mode": kwargs.get("生成模式", "自动"),
            # Legacy prompt-only face sharpening is hidden from the UI and disabled.
            "face_prompt": False,
            # Face repair keeps the RAW first-pass latent so an optional HD
            # second pass can start from the pre-repair source and avoid repairing
            # the same face twice.  Without face repair the user's toggle applies.
            "save_first_latent": True if repair_mode != "关闭" else bool(kwargs.get("保留一采latent", True)),
            # Single source of truth for post-generation face repair.
            "face_repair_mode": repair_mode,
            # Internal production defaults; intentionally hidden from the normal UI.
            "face_repair_strength": 0.65,
            "face_repair_crop_size": 512,
            "face_repair_temporal": 0.25,
            # v0.18.2 stable-face repair internals. Near profile overrides these
            # to 768 / ~0.06 denoise / 0.30 blend and 22-frame continuity.
            "face_repair_context_frames": 22,
            "face_repair_near_denoise": 0.06,
            "face_repair_near_blend": 0.30,
            "face_repair_near_refmod_cap": 0.25,
            "face_detection_size": 1280,
            "face_detection_score": 0.65,
            "face_repair_steps": 4,
            "face_repair_cfg": 1.0,
            "face_repair_sampler": "res_multistep",
            "face_repair_scheduler": "simple",
            "face_repair_denoise": 0.20,
            # Legacy keys are kept off so older runtime branches remain harmless.
            "fast_finish": False,
            "finish_target": "同分辨率",
            "upscale_model": "自动检测",
            "face_enhance": False,
            "face_strength": 0.0,
            "finish_batch": 2,
            "face_only": False,
        }
        lora_text = "未使用" if not loras else " + ".join(
            f"{x['name']}({x['model_strength']:.2f}/{x['clip_strength']:.2f})" for x in loras
        )
        summary = (
            f"{profile['name']}｜FL2VA {profile['fl2va_model']}｜REF2VA {profile['ref2va_model']}\n"
            f"LoRA×{len(loras)}：{lora_text}｜Steps {steps}｜CFG {cfg}｜{sampler} / {scheduler}\n"
            f"{profile['generation_mode']}｜人脸修复 {repair_mode}｜一采latent {'保留' if profile['save_first_latent'] else '不保留'}"
        )
        return (profile, summary)


class AVSH3SecondModelProfileV13(AVSH3ModelProfileV13):
    """Optional second-pass model profile with no face-repair controls."""

    @classmethod
    def INPUT_TYPES(cls):
        diffusion = _model_options("diffusion_models")
        clips = _model_options("text_encoders")
        vaes = _model_options("vae")
        return {
            "required": {
                "配置名称": ("STRING", {"default": "H3 二采模型"}),
                "FL2VA模型": (diffusion, {"default": "自动检测"}),
                "REF2VA模型": (diffusion, {"default": "自动检测"}),
                "CLIP模型": (clips, {"default": "自动检测"}),
                "视频VAE": (vaes, {"default": "自动检测"}),
                "音频VAE": (vaes, {"default": "自动检测"}),
                "权重精度": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"], {"default": "default"}),
                "Steps": ("INT", {"default": 20, "min": 1, "max": 100, "step": 1}),
                "CFG": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1}),
                "采样器": (["res_multistep", "euler", "euler_cfg_pp", "dpmpp_2m", "dpmpp_2m_sde"], {"default": "res_multistep"}),
                "调度器": (["simple", "beta", "normal", "sgm_uniform", "karras"], {"default": "simple"}),
                "降噪": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "视频Shift": ("FLOAT", {"default": 12.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "音频Shift": ("FLOAT", {"default": 3.0, "min": 0.01, "max": 100.0, "step": 0.1}),
                "参考图尺寸": (["match", "max"], {"default": "match"}),
            },
            "optional": {
                "LoRA堆栈": ("AVS_LORA_STACK",),
                "匹配Turbo参数": ("BOOLEAN", {"default": False}),
            },
        }

    DESCRIPTION = "可选二采 H3 模型。只负责二采模型/采样参数，不再显示或执行任何人脸增强开关。"

    def build(self, **kwargs):
        kwargs = dict(kwargs)
        kwargs["人脸修复"] = "关闭"
        kwargs["生成模式"] = "自动"
        kwargs["保留一采latent"] = False
        profile, _ = super().build(**kwargs)
        profile["name"] = str(kwargs.get("配置名称", "H3 二采模型") or "H3 二采模型")
        profile["face_repair_mode"] = "关闭"
        summary = (
            f"{profile['name']}｜FL2VA {profile['fl2va_model']}｜REF2VA {profile['ref2va_model']}｜"
            f"Steps {profile['steps']}｜CFG {profile['cfg']}｜{profile['sampler']} / {profile['scheduler']}"
        )
        return (profile, summary)


class AVSH3RefineProfileV13:
    """Second-pass image/video refinement only. Face repair lives in first-pass policy."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模式": (["自动适配", "二采高清", "同分辨率精修", "快速超分（免二采）"], {"default": "自动适配"}),
                "目标清晰度": (["自动适配", "同分辨率", "1.25x", "1.5x", "720P", "1080P", "2x"], {"default": "自动适配"}),
                "放大算法": (["bicubic", "bilinear", "nearest", "H3 3D latent", "学习型像素超分"], {"default": "bicubic"}),
                "二采步数": ("INT", {"default": 4, "min": 1, "max": 30, "step": 1}),
                "二采CFG": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1}),
                "二采采样器": (["euler", "res_multistep", "dpmpp_2m", "dpmpp_2m_sde"], {"default": "euler"}),
                "二采调度器": (["beta", "simple", "normal", "sgm_uniform", "karras"], {"default": "beta"}),
                "二采降噪": ("FLOAT", {"default": 0.20, "min": 0.01, "max": 1.0, "step": 0.01}),
                "显存自动保护": ("BOOLEAN", {"default": True}),
                "保留一采声音": ("BOOLEAN", {"default": True}),
                "Seed方式": (["沿用一采", "随机", "固定"], {"default": "沿用一采"}),
                "Seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            },
            "optional": {
                "超分模型": (_model_options("upscale_models"), {"default": "自动检测"}),
                "latent放大模型": (_model_options("latent_upscale_models"), {"default": "自动检测"}),
                "保持一采参考尺寸": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("AVS_H3_REFINE_PROFILE", "STRING")
    RETURN_NAMES = ("二采高清设置", "设置摘要")
    FUNCTION = "build"
    CATEGORY = "AI Video Studio/02 模型配置"
    DESCRIPTION = "二采只负责高清/精修。人脸修复策略由一采 H3 模型配置统一控制，并在最终输出前自动检查。"

    def build(self, **kwargs):
        guard = bool(kwargs.get("显存自动保护", True))
        mode = str(kwargs.get("模式", "自动适配"))
        target = str(kwargs.get("目标清晰度", "自动适配"))
        if mode == "自动适配":
            mode = "同分辨率精修" if guard else "二采高清"
        if target == "自动适配":
            target = "1080P" if mode == "快速超分（免二采）" else ("同分辨率" if guard else "1080P")
        profile = {
            "mode": mode,
            "target": target,
            "upscale_method": kwargs.get("放大算法", "bicubic"),
            "steps": int(kwargs.get("二采步数", 4)),
            "cfg": float(kwargs.get("二采CFG", 1.0)),
            "sampler": str(kwargs.get("二采采样器", "euler")),
            "scheduler": str(kwargs.get("二采调度器", "beta")),
            "denoise": float(kwargs.get("二采降噪", 0.20)),
            "vram_guard": guard,
            "preserve_audio": bool(kwargs.get("保留一采声音", True)),
            "seed_mode": kwargs.get("Seed方式", "沿用一采"),
            "seed": int(kwargs.get("Seed", 0)),
            "upscale_model": kwargs.get("超分模型", "自动检测"),
            "latent_upscale_model": kwargs.get("latent放大模型", "自动检测"),
            "keep_ref_size": bool(kwargs.get("保持一采参考尺寸", True)),
            # Legacy/internal defaults. They are no longer user-facing.
            "face_enhance": False,
            "face_strength": 0.0,
            "batch_size": 2,
            "face_only": False,
        }
        summary = (
            f"{mode}｜目标 {target}｜{profile['steps']}步｜denoise {profile['denoise']:.2f}｜"
            f"{profile['sampler']} / {profile['scheduler']}｜显存保护 {'开' if guard else '关'}"
        )
        return (profile, summary)


def _face_repair_settings(project: dict[str, Any]) -> dict[str, Any]:
    """Build the hidden production settings for the single user-facing policy."""
    return {
        "face_repair_mode": str(project.get("face_repair_mode", "关闭") or "关闭"),
        "face_crop_size": int(project.get("face_repair_crop_size", 512) or 512),
        "face_repair_strength": float(project.get("face_repair_strength", 0.65)),
        "face_temporal": float(project.get("face_repair_temporal", 0.25)),
        "face_detection_size": int(project.get("face_detection_size", 1280) or 1280),
        "face_detection_score": float(project.get("face_detection_score", 0.65)),
        "steps": int(project.get("face_repair_steps", 4) or 4),
        "cfg": float(project.get("face_repair_cfg", 1.0)),
        "sampler": str(project.get("face_repair_sampler", "res_multistep")),
        "scheduler": str(project.get("face_repair_scheduler", "simple")),
        "denoise": float(project.get("face_repair_denoise", 0.20)),
        "context_frames": int(project.get("face_repair_context_frames", 22) or 22),
        "near_denoise": float(project.get("face_repair_near_denoise", 0.06)),
        "near_blend": float(project.get("face_repair_near_blend", 0.30)),
        "near_refmod_cap": float(project.get("face_repair_near_refmod_cap", 0.25)),
        "vram_guard": True,
        "preserve_audio": True,
        "seed_mode": "沿用一采",
        "target": "同分辨率",
        "upscale_method": "bicubic",
        "keep_ref_size": True,
        "upscale_model": "自动检测",
        "latent_upscale_model": "自动检测",
        "face_enhance": False,
        "face_strength": 0.0,
        "batch_size": 2,
        "face_only": False,
    }


def _avs_gpu_memory_info() -> dict[str, Any]:
    """Read-only GPU memory info for internal safety/error messages. Never changes generation settings."""
    info = {"gpu_name": "GPU", "total_gb": 0.0}
    try:
        import torch
        if torch.cuda.is_available():
            idx = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(idx)
            info["gpu_name"] = str(props.name)
            info["total_gb"] = round(float(props.total_memory) / (1024 ** 3), 2)
    except Exception:
        pass
    return info


def _avs_model_identity(kind, name):
    path = folder_paths.get_full_path_or_raise(kind, name)
    stat = os.stat(path)
    return (path, stat.st_size, stat.st_mtime_ns)


# Reuse base components within a generation; LoRA/Shift changes only rebuild patches.
def _load_bundle(project: dict[str, Any], use_ref: bool) -> dict[str, Any]:
    import nodes
    model_name = _resolve_h3_model(project, use_ref)
    clip_name = _resolve_auto(str(project.get("clip_model", "自动检测")), "text_encoders", ("minimax", "h3", "qwen3vl"))
    video_vae_name = _resolve_auto(str(project.get("video_vae_model", "自动检测")), "vae", ("minimax", "h3", "video", "vae"), ("audio",))
    audio_vae_name = _resolve_auto(str(project.get("audio_vae_model", "自动检测")), "vae", ("minimax", "h3", "audio", "vae"))
    loras = _avs_lora_items({"items": project.get("loras") or []})
    for lora in loras:
        low = lora["name"].lower()
        if "turbo" in low and ((use_ref and ("fl2v" in low or "t2v" in low)) or (not use_ref and "ref2v" in low)):
            raise ValueError(f"Turbo LoRA 与任务不匹配：{lora['name']}。REF2VA 需要参考专用 Turbo，首帧模式需要 FL2VA Turbo。")
    # Legacy single-LoRA compatibility.
    if not loras:
        legacy = str(project.get("lora_name", "不使用") or "不使用")
        if legacy not in {"", "不使用", "None", "none"}:
            loras = [{"name": legacy, "model_strength": float(project.get("lora_strength", 1.0)), "clip_strength": 1.0, "enabled": True}]
    session = current_session()
    dtype = str(project.get("weight_dtype", "default"))
    model_key = (_avs_model_identity("diffusion_models", model_name), dtype)
    clip_key = _avs_model_identity("text_encoders", clip_name)
    video_key = _avs_model_identity("vae", video_vae_name)
    audio_key = _avs_model_identity("vae", audio_vae_name)
    lora_key = tuple((_avs_model_identity("loras", x["name"]), float(x["model_strength"]), float(x["clip_strength"])) for x in loras)
    key = (
        model_key, clip_key, video_key, audio_key, lora_key,
        float(project.get("shift_video", 12.0)), float(project.get("shift_audio", 3.0)),
    )
    if session.bundle_key == key and session.bundle is not None:
        return session.bundle
    if session.bundle is not None:
        unload(session.bundle["model"])
        unload(session.bundle["clip"])
        session.bundle = None

    model = session.component("model", model_key, lambda: nodes.UNETLoader().load_unet(model_name, dtype)[0])
    clip = session.component("clip", clip_key, lambda: nodes.CLIPLoader().load_clip(clip_name, "minimax", "default")[0])
    for lora in loras:
        try:
            model, clip = nodes.LoraLoader().load_lora(
                model, clip, lora["name"], float(lora["model_strength"]), float(lora["clip_strength"])
            )
        except Exception:
            # H3 motion LoRAs are often model-only. Keep them usable even if no CLIP keys exist.
            model = nodes.LoraLoaderModelOnly().load_lora_model_only(model, lora["name"], float(lora["model_strength"]))[0]

    try:
        from comfy_extras import nodes_minimax_h3 as h3
        model = _avs_node_result(h3.MiniMaxH3SigmaShift.execute(
            model=model, shift_video=float(project.get("shift_video", 12.0)), shift_audio=float(project.get("shift_audio", 3.0)),
        ))[0]
    except Exception:
        pass

    video_vae = session.component("video_vae", video_key, lambda: nodes.VAELoader().load_vae(video_vae_name)[0])
    audio_vae = session.component("audio_vae", audio_key, lambda: nodes.VAELoader().load_vae(audio_vae_name)[0])
    bundle = {
        "model": model, "clip": clip, "video_vae": video_vae, "audio_vae": audio_vae,
        "model_name": model_name, "clip_name": clip_name, "video_vae_name": video_vae_name, "audio_vae_name": audio_vae_name,
        "lora_name": loras[0]["name"] if loras else "不使用", "loras": loras,
    }
    session.bundle_key = key
    session.bundle = bundle
    return bundle


def _refine_dimensions(first_w: int, first_h: int, target: str, mode: str) -> tuple[int, int]:
    if mode == "同分辨率精修" or str(target) in {"同分辨率", "same"}:
        return int(first_w), int(first_h)
    target = str(target or "1080P")
    if target in {"1.25x", "1.5x", "2x"}:
        scale = {"1.25x": 1.25, "1.5x": 1.5, "2x": 2.0}[target]
        return _snap32(first_w * scale), _snap32(first_h * scale)
    short = 704 if target == "720P" else 1088
    if first_w >= first_h:
        h = short; w = _snap32(short * first_w / max(1, first_h))
    else:
        w = short; h = _snap32(short * first_h / max(1, first_w))
    return int(w), int(h)


def _avs_guard_refine_profile(refine: dict[str, Any]) -> dict[str, Any]:
    r = dict(refine or {})
    if r.get("mode") == "快速超分（免二采）":
        return r
    if not bool(r.get("vram_guard", True)):
        return r
    total = float(_avs_gpu_memory_info().get("total_gb", 0.0) or 0.0)
    # Only the explicit second-pass safety switch can apply these caps.
    if total and total < 9.5:
        r.update(mode="同分辨率精修", target="同分辨率", steps=min(int(r.get("steps", 4)), 4))
    elif total and total < 13.5:
        if str(r.get("target")) in {"1.5x", "2x", "720P", "1080P"}:
            r["target"] = "1.25x"
    elif total and total < 20.0:
        if str(r.get("target")) in {"2x", "1080P"}:
            r["target"] = "1.5x"
    return r


# Memory-aware replacement for second pass.
@model_session
def _second_pass_video(source_video, shot_context: dict[str, Any], second_project: dict[str, Any], refine: dict[str, Any]):
    import gc
    import nodes
    started = time.perf_counter()
    if refine.get("mode") == "人脸局部修复（参考头像）":
        from .face_repair import repair_video
        return repair_video(source_video, shot_context, second_project, refine, _second_pass_video)
    if refine.get("mode") == "快速超分（免二采）":
        return finish_video(source_video, refine.get("target", "1080P"), refine.get("upscale_model", "自动检测"),
                            bool(refine.get("face_enhance", False)), float(refine.get("face_strength", 0.55)),
                            int(refine.get("batch_size", 2)), bool(refine.get("face_only", True)))
    requested = dict(refine)
    refine = _avs_guard_refine_profile(refine)
    protection_note = ""
    if any(requested.get(key) != refine.get(key) for key in ("target", "steps", "mode")):
        protection_note = f"｜显存保护调整：{requested.get('target')} → {refine.get('target')}，{refine.get('steps')}步"
        logging.warning("AVS%s；关闭显存自动保护可保持手动目标。", protection_note)
    comps = source_video.get_components()
    frames = comps.images
    source_audio = comps.audio
    if frames is None or not hasattr(frames, "shape") or int(frames.shape[0]) <= 0:
        raise ValueError("二采源视频没有可用帧。")
    first_h, first_w = int(frames.shape[1]), int(frames.shape[2])
    target_w, target_h = _refine_dimensions(first_w, first_h, str(refine.get("target", "同分辨率")), str(refine.get("mode", "同分辨率精修")))
    resource_ctx = shot_context.get("resource_context") or {}
    use_ref = _uses_reference(second_project, resource_ctx)
    bundle = _load_bundle(second_project, use_ref)
    length = int(frames.shape[0])
    cached = load_latent(shot_context.get("first_latent_path"), shot_context)
    source_w, source_h = first_w, first_h
    if cached:
        video_latent, audio_latent, original = cached
        source_w, source_h = original["width"], original["height"]
    condition_w, condition_h = (source_w, source_h) if refine.get("keep_ref_size", True) else (target_w, target_h)
    positive, target_latent = run_stage("二采参考与提示词编码", _conditioning_at_canvas,
                                      shot_context, second_project, condition_w, condition_h, length, bundle)
    unload(bundle["clip"])
    method = str(refine.get("upscale_method", "bicubic"))
    if method == "H3 3D latent":
        if not cached:
            video_latent = nodes.VAEEncode().encode(bundle["video_vae"], frames)[0]
        if (source_w, source_h) != (target_w, target_h):
            video_latent = neural_latent_upscale(video_latent, target_w, target_h, refine.get("latent_upscale_model", "自动检测"))
        latent_note = "一采原始latent" if cached else "视频重新编码latent"
    elif cached and (source_w, source_h) == (target_w, target_h):
        latent_note = "一采原始latent"
    else:
        # If the first-pass latent exists, rebuild the RAW first-pass frames from
        # that latent before pixel upscaling.  The visible first-pass MP4 may
        # already contain a face-repair pass; using it here would repair the same
        # face twice.  The saved latent is captured before post face repair, so it
        # is the clean source for HD second pass.
        pixel_source = frames
        raw_from_latent = False
        if cached:
            try:
                pixel_source = _avs_safe_vae_decode(bundle["video_vae"], video_latent)
                raw_from_latent = True
            except Exception as exc:
                logging.warning("AVS 二采无法从一采原始latent恢复RAW帧，将回退到当前视频：%s", exc)
                pixel_source = frames
        if method == "学习型像素超分":
            from .portrait import fast_upscale
            up_frames, _ = fast_upscale(pixel_source, target_w, target_h, refine.get("upscale_model", "自动检测"),
                bool(refine.get("face_enhance", False)), float(refine.get("face_strength", 0.55)), int(refine.get("batch_size", 2)))
        else:
            up_frames = _resize_video_frames(pixel_source, target_w, target_h, method)
        video_latent = nodes.VAEEncode().encode(bundle["video_vae"], up_frames)[0]
        del up_frames
        if raw_from_latent:
            del pixel_source
        latent_note = "一采原始latent解码后放大（避免重复修脸）" if raw_from_latent else "像素放大后编码"
    try:
        from comfy_extras import nodes_lt, nodes_audio
        target_parts = _avs_node_result(nodes_lt.LTXVSeparateAVLatent.execute(target_latent))
        blank_audio_latent = target_parts[1]
        if cached:
            pass
        elif source_audio is not None:
            try:
                audio_latent = _avs_node_result(nodes_audio.VAEEncodeAudio.execute(vae=bundle["audio_vae"], audio=source_audio))[0]
            except Exception:
                audio_latent = blank_audio_latent
        else:
            audio_latent = blank_audio_latent
        if refine.get("preserve_audio", True):
            import torch
            audio_latent["noise_mask"] = torch.zeros_like(audio_latent["samples"])
        av_latent = _avs_node_result(nodes_lt.LTXVConcatAVLatent.execute(video_latent=video_latent, audio_latent=audio_latent))[0]
    except Exception as exc:
        raise RuntimeError(f"二采需要当前 ComfyUI 的 AV Latent 分离/拼接节点，请更新 ComfyUI。原始错误：{exc}") from exc

    seed_mode = str(refine.get("seed_mode", "沿用一采"))
    if seed_mode == "随机":
        seed = random.SystemRandom().randrange(0, 2**63 - 1)
    elif seed_mode == "固定":
        seed = int(refine.get("seed", 0) or 0)
    else:
        seed = original["seed"] if cached else int(shot_context.get("seed", 0) or 0)

    # Release temporary tensors/caches before the peak-memory diffusion step.
    gc.collect()
    try:
        import comfy.model_management as mm
        mm.soft_empty_cache()
    except Exception:
        pass

    unload(bundle["video_vae"])
    unload(bundle["audio_vae"])
    try:
        sampled = run_stage("二采视频采样", nodes.KSampler().sample,
            bundle["model"], seed, int(refine.get("steps", 2)), float(refine.get("cfg", 1.0)),
            str(refine.get("sampler", "euler")), str(refine.get("scheduler", "simple")),
            positive, positive, av_latent, float(refine.get("denoise", 0.15)),
        )[0]
    except Exception as exc:
        # Turn opaque CUDA OOMs into a Director-friendly message while preserving other errors.
        if exc.__class__.__name__ == "OutOfMemoryError" or "out of memory" in str(exc).lower():
            try:
                import comfy.model_management as mm
                mm.soft_empty_cache()
            except Exception:
                pass
            p = _avs_gpu_memory_info()
            raise RuntimeError(
                f"二采显存不足。检测到 {p.get('gpu_name','GPU')} / {p.get('total_gb',0)}GB。"
                "请降低二采目标清晰度，或关闭高倍率放大；如果源视频本身分辨率很高，"
                "8GB 显卡仍可能无法做同分辨率 H3 二采，可先使用 480P 源视频二采。"
            ) from exc
        raise
    del positive, target_latent, av_latent
    unload(bundle["model"])
    out_frames = _avs_safe_vae_decode(bundle["video_vae"], sampled)
    out_audio = source_audio if bool(refine.get("preserve_audio", True)) else None
    if out_audio is None and second_project.get("audio_mode") != "完全静音":
        try:
            from comfy_extras import nodes_audio
            out_audio = _avs_node_result(nodes_audio.VAEDecodeAudio.execute(vae=bundle["audio_vae"], samples=sampled))[0]
        except Exception:
            out_audio = None
    from comfy_extras import nodes_video
    video = _extract_video_result(nodes_video.CreateVideo.execute(images=out_frames, fps=24.0, audio=out_audio, bit_depth="auto", color_space="sRGB", codec="none"))
    if video is None:
        raise RuntimeError("二采 CreateVideo 没有返回有效 VIDEO。")
    p = _avs_gpu_memory_info()
    summary = (
        f"二采完成｜{first_w}×{first_h} → {target_w}×{target_h}｜{refine.get('steps',4)}步｜denoise {refine.get('denoise',0.20)}"
        f"｜{method}｜{latent_note}｜参考尺寸 {condition_w}×{condition_h}｜耗时 {time.perf_counter()-started:.1f}秒"
        f"｜显存保护 {'开' if refine.get('vram_guard', True) else '关'}｜{p.get('total_gb',0)}GB{protection_note}"
    )
    return video, summary, (target_w, target_h)


class AVSDirectorStudioV13(AVSDirectorStudioV12):
    """LoRA-era director compatibility layer. No GPU-auto ports or parameter rewriting."""
    DESCRIPTION = (
        "导演工作台：完整 H3 Prompt / Picture 真引用 / 一采预览 / 续写 / 手动二采 / A-B 对比 / 最终合成。"
        "一采参数完全来自 H3模型配置。"
    )



NODE_CLASS_MAPPINGS["AVSLoRAUnit"] = AVSLoRAUnit
NODE_DISPLAY_NAME_MAPPINGS["AVSLoRAUnit"] = "AI视频工作室｜LoRA"
NODE_CLASS_MAPPINGS["AVSH3ModelProfile"] = AVSH3ModelProfileV13
NODE_DISPLAY_NAME_MAPPINGS["AVSH3ModelProfile"] = "AI视频工作室｜一采 H3模型配置"
NODE_CLASS_MAPPINGS["AVSH3SecondModelProfile"] = AVSH3SecondModelProfileV13
NODE_DISPLAY_NAME_MAPPINGS["AVSH3SecondModelProfile"] = "AI视频工作室｜二采可选模型（兼容旧工作流）"
NODE_CLASS_MAPPINGS["AVSH3RefineProfile"] = AVSH3RefineProfileV13
NODE_DISPLAY_NAME_MAPPINGS["AVSH3RefineProfile"] = "AI视频工作室｜二采高清设置"
NODE_CLASS_MAPPINGS["AVSDirectorStudio"] = AVSDirectorStudioV13
NODE_DISPLAY_NAME_MAPPINGS["AVSDirectorStudio"] = "AI视频工作室｜导演工作台"

# ============================================================================
# v0.15.3 — Draw / Candidate mode
# ============================================================================


def _avs_candidate_round(segment: dict[str, Any]) -> dict[str, Any] | None:
    rounds = segment.get("draw_rounds", []) or []
    if not rounds:
        return None
    round_obj = rounds[-1]
    return round_obj if isinstance(round_obj, dict) else None


def _avs_candidate_seed(segment: dict[str, Any], candidate: dict[str, Any], candidate_index: int) -> int:
    mode = str(segment.get("draw_seed_mode", "random") or "random")
    base_seed = int(segment.get("seed", 0) or 0)
    existing = int(candidate.get("seed", 0) or 0)
    if mode == "increment":
        return existing if existing else base_seed + int(candidate_index)
    return existing if existing else random.SystemRandom().randrange(0, 2**63 - 1)


@model_session
def _avs_generate_draw_candidates(resource_db: dict[str, Any], first_profile: dict[str, Any], timeline_json: str,
                                  selected_index: int, unique_id=None, **kwargs):
    doc = _parse_timeline_doc(timeline_json)
    shots = doc.get("shots") or []
    if not shots:
        raise ValueError("导演工作台里没有视频段。")
    index = max(0, min(int(selected_index), len(shots) - 1))
    segment = _migrate_structured_segment(dict(shots[index] or {}), index)
    if segment.get("source_mode") != "生成视频":
        raise ValueError("已有视频不需要抽卡生成。")

    # v0.15.6: “抽卡当前视频段”这个 generation_scope 本身就是明确的抽卡指令。
    # 不再依赖 timeline_json 里的 generation_mode 是否及时同步。ComfyUI 前端的 DOM
    # Widget 在极少数情况下会把 generation_scope 更新成功、但 timeline_json 仍提交上一帧的值，
    # 于是旧版本会错误地看到 single 并报“没有开启抽卡生成”。
    # 这里以后端收到抽卡 scope 为准，强制当前段进入 draw，并在必要时补建候选轮。
    segment["generation_mode"] = "draw"

    round_obj = _avs_candidate_round(segment)
    candidates = list((round_obj or {}).get("candidates") or [])
    if not candidates:
        draw_count = int(segment.get("draw_count", 4) or 4)
        if draw_count not in {2, 4, 6, 8}:
            draw_count = 4
        round_index = len(segment.get("draw_rounds", []) or []) + 1
        base_seed = int(segment.get("seed", 0) or 0)
        seed_mode = str(segment.get("draw_seed_mode", "random") or "random")
        candidates = []
        for ci in range(draw_count):
            candidates.append({
                "candidate_id": f"r{round_index}_c{ci + 1}",
                "round_index": round_index,
                "candidate_index": ci + 1,
                "seed": (base_seed + ci) if seed_mode == "increment" else 0,
                "result_video": {},
                "refined_video": {},
                "status": "等待生成",
                "refine_status": "未二采",
                "preview_variant": "best",
                "is_selected": False,
            })
        round_obj = {"round_index": round_index, "candidates": candidates}
        segment["draw_rounds"] = [*(segment.get("draw_rounds", []) or []), round_obj]

    # 把后端修正后的抽卡状态写回本次工作文档，后续每个候选都基于同一份完整配置编译。
    shots[index] = segment
    doc["shots"] = shots

    project = _project_from_external_profile(resource_db, kwargs, first_profile)
    previous_video = None
    if _effective_segment_continuity(shots, index, segment) == "续写上一段" and index > 0:
        previous_segment = _migrate_structured_segment(dict(shots[index - 1] or {}), index - 1)
        previous_video = _segment_video_with_timeline_edits_for_continuation(doc, index - 1)
        if previous_video is None:
            previous_video = _segment_best_video(previous_segment)
        if previous_video is None:
            raise ValueError(
                "当前段使用抽卡并需要续写上一段，但上一段还没有正式版/可用视频。"
                "抽卡需要明确的上一段正式版，请先完成上一段并选定正式版，或把当前段改为独立生成。"
            )

    generator = AVSOneClickGenerate()
    last_video = None
    last_ui = None
    success_count = 0
    last_error: Exception | None = None

    for ci, raw_candidate in enumerate(candidates):
        candidate = dict(raw_candidate or {})
        candidate_id = str(candidate.get("candidate_id") or f"r{(round_obj or {}).get('round_index', 1)}_c{ci + 1}")
        seed = _avs_candidate_seed(segment, candidate, ci)
        _send_segment_event(unique_id, index, {
            "candidate_id": candidate_id,
            "seed": seed,
            "status": f"候选 {ci + 1}/{len(candidates)} 处理中",
        })
        try:
            candidate_doc = json.loads(json.dumps(doc, ensure_ascii=False))
            candidate_segment = _migrate_structured_segment(dict(candidate_doc["shots"][index] or {}), index)
            candidate_segment["seed_mode"] = "固定"
            candidate_segment["seed"] = int(seed)
            candidate_doc["shots"][index] = candidate_segment

            ctx = _compile_studio_shot_context(resource_db, project, candidate_doc, index, previous_video)
            raw = generator.generate(ctx)
            video, _prompt, _summary, ui_data = _unwrap_generation_result(raw)
            meta = _find_saved_media(ui_data or {})
            if not meta:
                try:
                    from comfy_extras import nodes_video
                    preview_ui = nodes_video.save_video_preview(video)
                    preview_data = preview_ui.as_dict() if hasattr(preview_ui, "as_dict") else preview_ui
                    meta = _find_saved_media(preview_data)
                except Exception:
                    meta = None
            event = {
                "candidate_id": candidate_id,
                "seed": int(seed),
                "status": "一采完成",
                "source_mode": "生成视频",
            }
            if meta:
                event["result_video"] = meta
            _send_segment_event(unique_id, index, event)
            last_video = video
            last_ui = ui_data
            success_count += 1
        except Exception as exc:
            last_error = exc
            _send_segment_event(unique_id, index, {
                "candidate_id": candidate_id,
                "seed": int(seed),
                "status": "生成失败",
                "error": str(exc),
            })
            # A failed candidate should not destroy the rest of the draw round.
            try:
                import comfy.model_management as mm
                mm.soft_empty_cache()
            except Exception:
                pass
            continue

    if success_count <= 0 or last_video is None:
        raise RuntimeError(f"本轮抽卡全部失败：{last_error or '未知错误'}")

    _send_segment_event(unique_id, index, {
        "status": f"抽卡完成｜{success_count}/{len(candidates)} 个候选成功",
        "draw_complete": True,
    })
    result = (last_video,)
    if last_ui:
        return {"ui": last_ui, "result": result}
    return result


class AVSDirectorStudioV153(AVSDirectorStudioV13):
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return model_state()

    @classmethod
    def INPUT_TYPES(cls):
        base = AVSDirectorStudioV13.INPUT_TYPES()
        base = {k: dict(v) if isinstance(v, dict) else v for k, v in base.items()}
        required = base.setdefault("required", {})
        legacy_resource = required.pop("resource_db", ("AVS_RESOURCE_DB",))
        base.setdefault("optional", {})["resource_db"] = legacy_resource
        required["generation_scope"] = ([
            "当前视频段", "抽卡当前视频段", "二采当前视频段", "时间轴局部重绘",
            "生成到当前视频段", "全部时间线", "合成最终视频"
        ], {"default": "当前视频段"})
        return base

    DESCRIPTION = (
        "导演工作台 v0.18.2：时间轴局部重绘 + 近景稳定人脸修复（支持跨视频段、H3 temporal mask、前后边界锚定、非破坏补丁）；保留抽卡状态同步；抽卡按钮本身即为权威指令，并自动补建候选轮。保留 Picture 真引用自动收集。"
        "同一视频段可以按相同 Prompt / Picture / 模型参数生成 2/4/6/8 个不同 Seed 候选，"
        "手动选择正式版；二采、续写和最终合成均优先使用正式版。"
    )

    def generate(self, 一采模型配置: dict[str, Any], timeline_json: str,
                 selected_index: int, generation_scope: str, language="中文", project_name="我的AI视频项目",
                 project_type="短剧", visual_style="电影级画面，主体清晰，光影自然，动作稳定",
                 aspect_ratio="16:9", resolution="快速预览 480P", consistency="强",
                 audio_mode="环境音（无配乐）", output_prefix="AI_Video_Studio",
                 二采模型配置=None, 二采高清设置=None, unique_id=None, resource_db=None):
        resource_db = resource_db or {"assets": [], "root": "", "version": 2}
        scope = str(generation_scope or "当前视频段")
        plan = check_studio(一采模型配置 or {}, timeline_json, selected_index, scope,
                            二采模型配置, 二采高清设置)
        if not plan["ready"]:
            return _wait_for_models(plan, 1, unique_id, scope)
        if scope == "时间轴局部重绘":
            kwargs = {
                "language": language, "project_type": project_type,
                "visual_style": visual_style, "aspect_ratio": aspect_ratio, "resolution": resolution,
                "consistency": consistency, "audio_mode": audio_mode,
            }
            return _generate_timeline_local_redraw(
                resource_db=resource_db, first_profile=dict(一采模型配置 or {}),
                timeline_json=timeline_json, project_name=project_name, output_prefix=output_prefix,
                unique_id=unique_id, **kwargs,
            )
        if scope != "抽卡当前视频段":
            return super().generate(
                resource_db=resource_db, 一采模型配置=一采模型配置, timeline_json=timeline_json,
                selected_index=selected_index, generation_scope=scope, language=language,
                project_name=project_name, project_type=project_type, visual_style=visual_style,
                aspect_ratio=aspect_ratio, resolution=resolution, consistency=consistency,
                audio_mode=audio_mode, output_prefix=output_prefix, 二采模型配置=二采模型配置,
                二采高清设置=二采高清设置, unique_id=unique_id,
            )

        first_profile = dict(一采模型配置 or {})
        kwargs = {
            "language": language,
            "project_name": project_name,
            "project_type": project_type,
            "visual_style": visual_style,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "consistency": consistency,
            "audio_mode": audio_mode,
            "output_prefix": output_prefix,
        }
        return _avs_generate_draw_candidates(
            resource_db=resource_db,
            first_profile=first_profile,
            timeline_json=timeline_json,
            selected_index=selected_index,
            unique_id=unique_id,
            **kwargs,
        )


NODE_CLASS_MAPPINGS["AVSDirectorStudio"] = AVSDirectorStudioV153
NODE_DISPLAY_NAME_MAPPINGS["AVSDirectorStudio"] = "AI视频工作室｜导演工作台"


def _profile_from_graph(graph, link, refine=False):
    if isinstance(link, dict):
        return link
    if not isinstance(link, list) or len(link) != 2:
        return {}
    node = graph.get(str(link[0]), {})
    expected = {"AVSH3RefineProfile"} if refine else {"AVSH3ModelProfile", "AVSH3SecondModelProfile"}
    if node.get("class_type") not in expected:
        return {}
    inputs = dict(node.get("inputs") or {})
    if refine:
        return AVSH3RefineProfileV13().build(**inputs)[0]
    stack = []
    previous = inputs.get("LoRA堆栈")
    visited = set()
    while isinstance(previous, list) and len(previous) == 2 and str(previous[0]) not in visited:
        visited.add(str(previous[0]))
        unit = graph.get(str(previous[0]), {})
        if unit.get("class_type") != "AVSLoRAUnit":
            break
        values = unit.get("inputs") or {}
        if values.get("启用", True) and values.get("LoRA") not in (None, "", "不使用"):
            stack.insert(0, {"name": values["LoRA"], "model_strength": values.get("模型强度", 1),
                             "clip_strength": values.get("CLIP强度", 1), "enabled": True})
        previous = values.get("上一个LoRA")
    inputs["LoRA堆栈"] = {"items": stack}
    if node.get("class_type") == "AVSH3SecondModelProfile":
        return AVSH3SecondModelProfileV13().build(**inputs)[0]
    return AVSH3ModelProfileV13().build(**inputs)[0]


def _model_preflight_graph(graph, node_id=None):
    plans = []
    for key, node in graph.items():
        if node.get("class_type") != "AVSDirectorStudio" or (node_id is not None and str(key) != str(node_id)):
            continue
        inputs = node.get("inputs") or {}
        first = _profile_from_graph(graph, inputs.get("一采模型配置"))
        second = _profile_from_graph(graph, inputs.get("二采模型配置"))
        refine = _profile_from_graph(graph, inputs.get("二采高清设置"), True)
        scope = inputs.get("generation_scope", "当前视频段")
        plan = check_studio(first, inputs.get("timeline_json", "{}"), inputs.get("selected_index", 0), scope, second, refine)
        plans.append({**plan, "node_id": str(key), "scope": scope})
    return {"ready": all(p["ready"] for p in plans), "nodes": plans}


from aiohttp import web
from server import PromptServer


@PromptServer.instance.routes.post("/avs/models/preflight")
async def _model_preflight_route(request):
    body = await request.json()
    return web.json_response(_model_preflight_graph(body.get("prompt") or {}, body.get("node_id")))


# ============================================================================
# v0.16.9 — Hidden spatial-lock preroll / production-only scene initializer
# ============================================================================
# A hidden_anchor is a real generated H3 segment used only to establish 2–5
# person world-space placement. It feeds the next formal segment through the
# existing 22-frame AddGuide chain, is omitted from final assembly, and the
# following formal segment receives a guide-duration generation pad so trimming
# the hidden overlap does not steal its requested editorial runtime.

# ============================================================================
# v0.15.8 — Clean GPU-auto removal + safe H3→VAE handoff
# ============================================================================

AVSDirectorStudioV153.DESCRIPTION = (
    "导演工作台 v0.18.2：剪映式连续时间轴局部重绘 + 近景稳定人脸修复。已生成到哪里就能编辑到哪里，可鼠标拖选任意时间范围并跨越原始5秒段；"
    "后台使用 MiniMax H3 temporal denoise mask，只重采选中时间 token，并自动加入前后 AddGuide 锚点。修改结果作为非破坏 patch 保存，可撤销/恢复，最终合成自动应用。"
    "如果局部修改覆盖某个已生成段的尾部，后续续写会自动使用打过 patch 的新版尾帧，而不是旧段尾帧。"
    "同时保留隐藏空间预热、22帧续写、抽卡正式版、二采、人脸修复自动策略、Picture引用和最终合成。"
)



def _avs_runtime_recovery(message: str) -> tuple[str, str]:
    """Return (recovery_code, friendly_hint) for AVS UI runtime errors."""
    text = str(message or "")
    if "还没有一采完成" in text or "没有可用于二采的源视频" in text or "正式版候选可用于二采" in text:
        return "generate_first_pass", "请先生成当前视频的一采；一采完成后，再点击“二采高清”。"
    if "Turbo LoRA 与任务不匹配" in text:
        return "fix_turbo_lora", "当前任务使用 REF2VA 参考模式，但加载了不匹配的 Turbo LoRA。请关闭“匹配Turbo参数”，或改用 REF2VA 专用 Turbo。"
    if "没有连接“AI视频工作室｜二采高清设置”" in text or "没有连接【二采高清设置】" in text:
        return "connect_refine", "请先把“AI视频工作室｜二采高清设置”连接到导演工作台。"
    if "没有连接一采 H3模型配置" in text:
        return "connect_first_model", "请先连接“一采 H3模型配置”。"
    if "Picture" in text and ("未绑定" in text or "没有选择" in text):
        return "bind_picture", "请检查当前视频段的 Picture 引用，并把缺失的参考图绑定完整。"
    low = text.lower()
    if "cuda" in low and ("out of memory" in low or "oom" in low):
        return "oom", "显存不足。请降低分辨率/参考精度/批量大小，或关闭不必要的高显存模型。"
    return "", "请根据上面的错误信息修改设置后重试。完整 Traceback 仍保留在 ComfyUI 日志中。"


def _send_runtime_error(unique_id: Any, selected_index: int, scope: str, exc: Exception):
    if unique_id is None:
        return
    message = str(exc) or exc.__class__.__name__
    recovery, hint = _avs_runtime_recovery(message)
    try:
        from server import PromptServer
        PromptServer.instance.send_sync("avs_runtime_error", {
            "node_id": str(unique_id),
            "index": int(selected_index or 0),
            "scope": str(scope or ""),
            "exception_type": exc.__class__.__name__,
            "message": message,
            "recovery": recovery,
            "hint": hint,
        })
    except Exception:
        pass


class AVSDirectorStudioV154(AVSDirectorStudioV153):
    """v0.18.3: surface backend failures directly in the Studio UI."""

    DESCRIPTION = (
        "导演工作台 v0.18.3：运行错误会直接显示在工作台，不再要求用户翻后台日志；"
        "可提前判断的二采/素材/模型问题在提交前拦截，运行中的模型/LoRA/显存错误会回传中文错误卡片。"
    )

    def generate(self, 一采模型配置: dict[str, Any], timeline_json: str,
                 selected_index: int, generation_scope: str, language="中文", project_name="我的AI视频项目",
                 project_type="短剧", visual_style="电影级画面，主体清晰，光影自然，动作稳定",
                 aspect_ratio="16:9", resolution="快速预览 480P", consistency="强",
                 audio_mode="环境音（无配乐）", output_prefix="AI_Video_Studio",
                 二采模型配置=None, 二采高清设置=None, unique_id=None, resource_db=None):
        scope = str(generation_scope or "当前视频段")
        try:
            return super().generate(
                一采模型配置=一采模型配置,
                timeline_json=timeline_json,
                selected_index=selected_index,
                generation_scope=scope,
                language=language,
                project_name=project_name,
                project_type=project_type,
                visual_style=visual_style,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                consistency=consistency,
                audio_mode=audio_mode,
                output_prefix=output_prefix,
                二采模型配置=二采模型配置,
                二采高清设置=二采高清设置,
                unique_id=unique_id,
                resource_db=resource_db,
            )
        except Exception as exc:
            _send_runtime_error(unique_id, selected_index, scope, exc)
            raise



class AVSH3SecondPassCombinedV184:
    """v0.18.4 — merge second-pass model + refine settings into one visible node.

    The node reuses the first-pass H3 model choices by default and emits the two
    objects the Director already understands: AVS_H3_MODEL_PROFILE and
    AVS_H3_REFINE_PROFILE.  This keeps the workflow visually at two configuration
    nodes: 一采 + 二采.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "一采模型配置": ("AVS_H3_MODEL_PROFILE",),
                "二采方式": (["H3潜空间×2（推荐）", "同分辨率精修", "快速超分×2（免二采）"], {"default": "H3潜空间×2（推荐）"}),
                "二采步数": ("INT", {"default": 4, "min": 1, "max": 30, "step": 1}),
                "二采CFG": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 20.0, "step": 0.1}),
                "二采采样器": (["res_multistep", "euler", "dpmpp_2m", "dpmpp_2m_sde"], {"default": "res_multistep"}),
                "二采调度器": (["simple", "beta", "normal", "sgm_uniform", "karras"], {"default": "simple"}),
                "二采降噪": ("FLOAT", {"default": 0.12, "min": 0.01, "max": 1.0, "step": 0.01}),
                "显存自动保护": ("BOOLEAN", {"default": True}),
                "保留一采声音": ("BOOLEAN", {"default": True}),
                "Seed方式": (["沿用一采", "随机", "固定"], {"default": "沿用一采"}),
                "Seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "latent放大模型": (_model_options("latent_upscale_models"), {"default": "自动检测"}),
                "超分模型": (_model_options("upscale_models"), {"default": "自动检测"}),
                "保持一采参考尺寸": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("AVS_H3_MODEL_PROFILE", "AVS_H3_REFINE_PROFILE", "STRING")
    RETURN_NAMES = ("二采模型配置", "二采高清设置", "配置摘要")
    FUNCTION = "build"
    CATEGORY = "AI Video Studio/02 模型配置"
    DESCRIPTION = (
        "二采一体化配置。默认沿用一采模型，480P 使用 H3 潜空间×2 到约960P，"
        "再以4步/denoise 0.12低强度精修；不再需要单独的“二采可选模型”和“二采高清设置”两个节点。"
    )

    def build(self, **kwargs):
        first = dict(kwargs.get("一采模型配置") or {})
        if not first:
            raise ValueError("请先连接“一采：H3多素材参考”。")

        # Reuse first-pass model selections.  For the low-denoise second pass,
        # strip Turbo LoRAs so a first-pass 4-step Turbo choice cannot conflict
        # with REF2VA refinement or force the wrong schedule.
        second = dict(first)
        loras = [dict(x) for x in (first.get("loras") or []) if "turbo" not in str(x.get("name", "")).lower()]
        second["loras"] = loras
        second["lora_name"] = loras[0]["name"] if loras else "不使用"
        second["lora_strength"] = float(loras[0].get("model_strength", 1.0)) if loras else 1.0
        second["name"] = "二采：沿用一采模型"
        second["steps"] = int(kwargs.get("二采步数", 4))
        second["steps_override"] = second["steps"]
        second["cfg"] = float(kwargs.get("二采CFG", 1.0))
        second["sampler"] = str(kwargs.get("二采采样器", "res_multistep"))
        second["scheduler"] = str(kwargs.get("二采调度器", "simple"))
        second["denoise"] = float(kwargs.get("二采降噪", 0.12))
        second["face_repair_mode"] = "关闭"
        second["face_prompt"] = False
        second["save_first_latent"] = False

        mode = str(kwargs.get("二采方式", "H3潜空间×2（推荐）"))
        if mode == "H3潜空间×2（推荐）":
            refine_mode = "二采高清"
            target = "2x"
            upscale_method = "H3 3D latent"
        elif mode == "同分辨率精修":
            refine_mode = "同分辨率精修"
            target = "同分辨率"
            upscale_method = "bicubic"
        else:
            refine_mode = "快速超分（免二采）"
            target = "2x"
            upscale_method = "学习型像素超分"

        refine = {
            "mode": refine_mode,
            "target": target,
            "upscale_method": upscale_method,
            "steps": int(kwargs.get("二采步数", 4)),
            "cfg": float(kwargs.get("二采CFG", 1.0)),
            "sampler": str(kwargs.get("二采采样器", "res_multistep")),
            "scheduler": str(kwargs.get("二采调度器", "simple")),
            "denoise": float(kwargs.get("二采降噪", 0.12)),
            "vram_guard": bool(kwargs.get("显存自动保护", True)),
            "preserve_audio": bool(kwargs.get("保留一采声音", True)),
            "seed_mode": str(kwargs.get("Seed方式", "沿用一采")),
            "seed": int(kwargs.get("Seed", 0)),
            "upscale_model": kwargs.get("超分模型", "自动检测"),
            "latent_upscale_model": kwargs.get("latent放大模型", "自动检测"),
            "keep_ref_size": bool(kwargs.get("保持一采参考尺寸", True)),
            "face_enhance": False,
            "face_strength": 0.0,
            "batch_size": 2,
            "face_only": False,
        }
        summary = (
            f"{mode}｜480P→约960P(2×)｜{refine['steps']}步｜denoise {refine['denoise']:.2f}｜"
            f"{refine['sampler']} / {refine['scheduler']}｜声音 {'保留' if refine['preserve_audio'] else '重生成'}"
        )
        return (second, refine, summary)


NODE_CLASS_MAPPINGS["AVSLoRAUnit"] = AVSLoRAUnit
NODE_DISPLAY_NAME_MAPPINGS["AVSLoRAUnit"] = "AI视频工作室｜LoRA"
NODE_CLASS_MAPPINGS["AVSH3ModelProfile"] = AVSH3ModelProfileV13
NODE_DISPLAY_NAME_MAPPINGS["AVSH3ModelProfile"] = "AI视频工作室｜一采 H3模型配置"
NODE_CLASS_MAPPINGS["AVSH3SecondModelProfile"] = AVSH3SecondModelProfileV13
NODE_CLASS_MAPPINGS["AVSH3SecondPassProfile"] = AVSH3SecondPassCombinedV184
NODE_DISPLAY_NAME_MAPPINGS["AVSH3SecondModelProfile"] = "AI视频工作室｜二采可选模型（兼容旧工作流）"
NODE_DISPLAY_NAME_MAPPINGS["AVSH3SecondPassProfile"] = "AI视频工作室｜二采 H3潜空间高清"
NODE_CLASS_MAPPINGS["AVSH3RefineProfile"] = AVSH3RefineProfileV13
NODE_DISPLAY_NAME_MAPPINGS["AVSH3RefineProfile"] = "AI视频工作室｜二采高清设置"
NODE_CLASS_MAPPINGS["AVSDirectorStudio"] = AVSDirectorStudioV154
NODE_DISPLAY_NAME_MAPPINGS["AVSDirectorStudio"] = "AI视频工作室｜导演工作台"
