"""Local model checks and download instructions. Never downloads or loads weights."""
import json
import os
import re

import folder_paths

H3 = "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/"
CATALOG = {
    "fl2va": ("diffusion_models", "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "FL2VA 首帧主模型"),
    "ref2va": ("diffusion_models", "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "REF2VA 多素材主模型"),
    "clip": ("text_encoders", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "H3 文本编码器"),
    "video_vae": ("vae", "minimax_h3_video_vae_fp16.safetensors", "H3 视频 VAE"),
    "audio_vae": ("vae", "minimax_h3_audio_vae_fp32.safetensors", "H3 音频 VAE"),
    "upscale": ("upscale_models", "RealESRGAN_x2plus.pth", "快速高清放大模型"),
    "latent": ("latent_upscale_models", "minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors", "H3 latent 放大模型"),
}
SPECIAL_URLS = {
    "RealESRGAN_x2plus.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
    "minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors": "https://huggingface.co/LBH-123-AI/Minimax_h3_latent_Upscaler/resolve/main/minimax_h3_latent_upscaler_3d_conv_v1/minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors",
    "文戏.safetensors": "https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA/resolve/main/h3-realism-people-t2v-i2v-r2v.safetensors",
    "h3-realism-people-t2v-i2v-r2v.safetensors": "https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA/resolve/main/h3-realism-people-t2v-i2v-r2v.safetensors",
}
H3_LORAS = {
    "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
    "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
    "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors",
}


def files(kind):
    try:
        return folder_paths.get_filename_list(kind)
    except KeyError:
        return []


def install_directory(kind):
    directories = folder_paths.get_folder_paths(kind) if kind in folder_paths.folder_names_and_paths else []
    # Prefer the configured directory which already contains this user's models.
    for name in files(kind):
        full = folder_paths.get_full_path(kind, name)
        if full:
            for directory in directories:
                try:
                    if os.path.commonpath((os.path.abspath(full), os.path.abspath(directory))) == os.path.abspath(directory):
                        return os.path.abspath(directory)
                except ValueError:
                    continue
    default = next((p for p in directories if os.path.basename(os.path.normpath(p)) == kind), None)
    return os.path.abspath(default or (directories[0] if directories else os.path.join(folder_paths.models_dir, kind)))


def model_state():
    # ComfyUI supplies None for connected inputs during IS_CHANGED. Check the
    # inventory directly so a newly installed model invalidates a waiting result.
    kinds = {spec[0] for spec in CATALOG.values()} | {"loras"}
    return json.dumps({kind: sorted(files(kind)) for kind in sorted(kinds)}, ensure_ascii=False)


def missing_model(kind, filename, label, selected=""):
    known = {spec[1] for spec in CATALOG.values()}
    url = SPECIAL_URLS.get(filename)
    if filename in known or filename in H3_LORAS:
        url = url or H3 + kind + "/" + filename
    return {"kind": kind, "filename": filename, "label": label, "download_url": url,
            "directory": install_directory(kind), "selected": selected,
            "size_hint": "约21GB" if filename.startswith("minimax_h3_ref2va_pruned_int8") else "",
            "note": "下载推荐文件后，在模型配置中选择该文件或自动检测。" if selected and selected != filename else "保留上面的文件名。"}


def check_project(project, resources, refine=None):
    missing, issues = [], []

    def require(key, choice="自动检测", predicate=lambda name: True):
        kind, filename, label = CATALOG[key]
        available = files(kind)
        if choice not in (None, "", "自动检测", "Auto Detect"):
            if choice in available:
                return
            missing.append(missing_model(kind, filename if choice not in SPECIAL_URLS else choice, label, str(choice)))
        elif not any(predicate(name.lower()) for name in available):
            missing.append(missing_model(kind, filename, label))

    quick = refine and refine.get("mode") == "快速超分（免二采）"
    if not quick:
        mode = project.get("generation_mode", "自动")
        use_ref = mode == "多素材参考" or (mode != "首帧图生视频" and any(resources.get(k) for k in ("images", "videos", "audios")))
        task, other = ("ref2va", "fl2va") if use_ref else ("fl2va", "ref2va")
        choice = project.get(task + "_model", "自动检测")
        if other in str(choice).lower() and task not in str(choice).lower():
            issues.append(f"当前模式需要 {task.upper()}，请将主模型改为对应任务模型。")
            choice = "自动检测"
        require(task, choice, lambda name: "h3" in name and task in name)
        require("clip", project.get("clip_model", "自动检测"), lambda name: "minimax" in name or "qwen3vl" in name)
        require("video_vae", project.get("video_vae_model", "自动检测"), lambda name: "h3" in name and "video" in name and "audio" not in name)
        require("audio_vae", project.get("audio_vae_model", "自动检测"), lambda name: "h3" in name and "audio" in name)
        loras = project.get("loras") or []
        if not loras and project.get("lora_name") not in (None, "", "不使用", "None", "none"):
            loras = [{"name": project["lora_name"]}]
        for item in loras:
            if not item.get("enabled", True):
                continue
            name = item.get("name", "")
            if name and name != "不使用" and name not in files("loras"):
                missing.append(missing_model("loras", name, "所选 LoRA", name))
            low = name.lower()
            if "turbo" in low and ((use_ref and ("fl2v" in low or "t2v" in low)) or (not use_ref and "ref2v" in low)):
                issues.append("所选Turbo LoRA与生成模式不匹配，请使用对应任务的Turbo或关闭该LoRA。")
    if quick or (not refine and project.get("fast_finish")) or (refine and refine.get("upscale_method") == "学习型像素超分"):
        require("upscale", (refine or project).get("upscale_model", "自动检测"))
    if (refine and not quick and refine.get("upscale_method") == "H3 3D latent"
            and refine.get("mode") != "同分辨率精修" and refine.get("target") not in ("同分辨率", "same")):
        require("latent", refine.get("latent_upscale_model", "自动检测"), lambda name: "h3" in name and "fp16" in name)
    return {"ready": not missing and not issues, "missing": missing, "issues": issues}


def check_studio(first, timeline_json, selected_index, scope, second=None, refine=None):
    if scope == "合成最终视频":
        return {"ready": True, "missing": [], "issues": []}
    doc = json.loads(timeline_json) if isinstance(timeline_json, str) else timeline_json
    shots = (doc or {}).get("shots") or []
    selected = max(0, min(int(selected_index), len(shots) - 1))
    indices = range(len(shots)) if scope == "全部时间线" else range(selected + 1) if scope == "生成到当前视频段" else [selected]
    combined = {"ready": True, "missing": [], "issues": []}
    for index in indices:
        if not shots:
            break
        shot = shots[index]
        refining = scope == "二采当前视频段"
        if scope != "时间轴局部重绘" and not refining and shot.get("source_mode") in ("已有视频", "导入视频", "existing"):
            continue
        resources = {"images": re.findall(r"<Picture\s+\d+>", shot.get("full_prompt", ""), flags=re.I),
                     "videos": shot.get("video_refs"), "audios": shot.get("audio_refs")}
        project = (second or first) if refining else first
        effective_refine = refine if refining else None
        if scope == "时间轴局部重绘":
            project = {**(first or {}), "generation_mode": "多素材参考", "fast_finish": False}
            resources = {**resources, "videos": "timeline_source_window"}
        if refining and (refine or {}).get("mode") == "人脸局部修复（参考头像）":
            project = {**first, "generation_mode": "多素材参考", "fast_finish": False}
            effective_refine = {**refine, "upscale_method": "bicubic", "target": "同分辨率"}
        plan = check_project(project, resources, effective_refine)
        combined["missing"].extend(plan["missing"])
        combined["issues"].extend(plan["issues"])
    combined["missing"] = list({(m["kind"], m["filename"]): m for m in combined["missing"]}.values())
    combined["issues"] = list(dict.fromkeys(combined["issues"]))
    combined["ready"] = not combined["missing"] and not combined["issues"]
    return combined
