from __future__ import annotations

import hashlib
import json
import os
import time

import folder_paths
import torch
import torch.nn.functional as F

from .nodes import _avs_node_result


def save_video(video, prefix: str, crf: int = 16):
    from comfy_extras import nodes_video

    saver = nodes_video.SaveVideo.PREPARE_CLASS_CLONE(None)
    saved = saver.execute(video=video, filename_prefix=prefix, format="mp4",
                          codec={"codec": "h264", "encoding": {"crf": int(crf)}})
    return saved.ui.as_dict()


def resize_frames(images, width: int, height: int):
    if (images.shape[2], images.shape[1]) == (width, height):
        return images
    return F.interpolate(images.movedim(-1, 1), size=(height, width), mode="bicubic",
                         align_corners=False, antialias=True).movedim(1, -1).clamp(0, 1)


def delivery_dimensions(width: int, height: int, target: str):
    if target == "同分辨率":
        return width, height
    short = {"720P": 720, "1080P": 1080}.get(target)
    if short is None:
        scale = {"1.25x": 1.25, "1.5x": 1.5, "2x": 2.0}[target]
    else:
        scale = short / min(width, height)
    return max(2, round(width * scale / 2) * 2), max(2, round(height * scale / 2) * 2)


def _face_boxes(images, interval: int = 3):
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("人脸增强需要 opencv-python-headless；请安装本插件 requirements.txt，或关闭人脸增强。") from exc

    front = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    profile = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_profileface.xml"))
    if front.empty() or profile.empty():
        raise RuntimeError("OpenCV 人脸检测文件缺失，请重新安装 opencv-python-headless。")
    height, width = images.shape[1:3]
    scale = min(1.0, 640.0 / max(height, width))
    tracks = []
    last_small = None
    misses = 0
    boxes_by_frame = []
    for index, frame in enumerate(images):
        array = (frame.float().cpu().clamp(0, 1).numpy() * 255).round().astype("uint8")
        gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
        gray = cv2.resize(gray, (round(width * scale), round(height * scale)))
        small = cv2.resize(gray, (32, 32)).astype("float32") / 255
        cut = last_small is not None and abs(small - last_small).mean() > 0.22
        last_small = small
        if cut:
            tracks = []
            misses = 0
        if index % interval == 0 or cut:
            detected = list(front.detectMultiScale(gray, 1.1, 5, minSize=(24, 24)))
            if not detected:
                detected = list(profile.detectMultiScale(gray, 1.1, 5, minSize=(24, 24)))
                if not detected:
                    mirrored = profile.detectMultiScale(cv2.flip(gray, 1), 1.1, 5, minSize=(24, 24))
                    detected = [(gray.shape[1] - x - w, y, w, h) for x, y, w, h in mirrored]
            current = []
            for x, y, w, h in sorted(detected, key=lambda box: int(box[2]) * int(box[3]), reverse=True)[:4]:
                x, y, w, h = (float(v) / scale for v in (x, y, w, h))
                if h > height * 0.4:
                    continue
                box = (x + w / 2, y + h / 2, max(w, h) * 1.65)
                nearest = min(tracks, key=lambda old: (old[0] - box[0]) ** 2 + (old[1] - box[1]) ** 2, default=None)
                if nearest and abs(nearest[0] - box[0]) + abs(nearest[1] - box[1]) < box[2] * 0.6:
                    box = tuple(0.75 * a + 0.25 * b for a, b in zip(box, nearest))
                current.append(box)
            if current:
                tracks = current
                misses = 0
            else:
                misses += interval
                if misses > interval:
                    tracks = []
        boxes = []
        for cx, cy, size in tracks:
            x0, y0 = max(0, round(cx - size / 2)), max(0, round(cy - size / 2))
            x1, y1 = min(width, round(cx + size / 2)), min(height, round(cy + size / 2))
            if x1 > x0 and y1 > y0:
                boxes.append((x0, y0, x1, y1))
        boxes_by_frame.append(boxes)
    return boxes_by_frame


def fast_upscale(images, width: int, height: int, model_name="自动检测", faces=False, strength=0.55, batch_size=2, face_only=False):
    from comfy_extras import nodes_upscale_model
    import comfy.model_management as mm
    import comfy.utils

    choices = folder_paths.get_filename_list("upscale_models")
    if model_name == "自动检测":
        model_name = next((x for x in choices if "realesrgan_x2plus" in x.lower()), choices[0] if choices else "")
    if not model_name:
        raise ValueError("快速超分需要 models/upscale_models 中的放大模型，例如 RealESRGAN_x2plus.pth。")
    model = _avs_node_result(nodes_upscale_model.UpscaleModelLoader.execute(model_name))[0]
    boxes = _face_boxes(images) if faces and strength > 0 else [[] for _ in images]
    output = torch.empty((len(images), height, width, images.shape[-1]), dtype=torch.float16, device="cpu")
    progress = comfy.utils.ProgressBar(len(images))
    face_count = 0
    for start in range(0, len(images), max(1, int(batch_size))):
        mm.throw_exception_if_processing_interrupted()
        chunk = images[start:start + max(1, int(batch_size))]
        if face_only and faces and strength > 0:
            enlarged = resize_frames(chunk, width, height).clone()
        else:
            enlarged = _avs_node_result(nodes_upscale_model.ImageUpscaleWithModel.execute(model, chunk))[0]
            enlarged = resize_frames(enlarged, width, height)
        for local, frame in enumerate(chunk):
            for x0, y0, x1, y1 in boxes[start + local]:
                crop = frame[None, y0:y1, x0:x1]
                detail = _avs_node_result(nodes_upscale_model.ImageUpscaleWithModel.execute(model, crop))[0]
                detail = _avs_node_result(nodes_upscale_model.ImageUpscaleWithModel.execute(model, detail))[0]
                tx0, ty0 = round(x0 * width / images.shape[2]), round(y0 * height / images.shape[1])
                tx1, ty1 = round(x1 * width / images.shape[2]), round(y1 * height / images.shape[1])
                detail = resize_frames(detail, tx1 - tx0, ty1 - ty0)[0].to(enlarged)
                yy = torch.linspace(-1, 1, ty1 - ty0, device=enlarged.device)
                xx = torch.linspace(-1, 1, tx1 - tx0, device=enlarged.device)
                mask = ((1 - yy.abs()).clamp(0, 1)[:, None] * (1 - xx.abs()).clamp(0, 1)[None, :])
                mask = (mask * 3).clamp(0, 1).unsqueeze(-1) * float(strength)
                region = enlarged[local, ty0:ty1, tx0:tx1]
                enlarged[local, ty0:ty1, tx0:tx1] = region + (detail - region) * mask
                face_count += 1
        output[start:start + len(chunk)].copy_(enlarged)
        progress.update(len(chunk))
    mode = "人脸优先（背景插值）" if face_only and faces and strength > 0 else "全画面学习型超分"
    return output, f"{mode}｜{model_name}｜人脸增强 {face_count} 帧区域"


def finish_video(video, target="1080P", model_name="自动检测", faces=False, strength=0.55, batch_size=2, face_only=True):
    from comfy_extras import nodes_video

    started = time.perf_counter()
    components = video.get_components()
    images = components.images
    width, height = delivery_dimensions(images.shape[2], images.shape[1], target)
    output, details = fast_upscale(images, width, height, model_name, faces, strength, batch_size, face_only)
    result = _avs_node_result(nodes_video.CreateVideo.execute(images=output, fps=float(components.frame_rate),
                              audio=components.audio, bit_depth="auto", color_space="sRGB", codec="none"))[0]
    return result, f"快速超分｜{images.shape[2]}×{images.shape[1]} → {width}×{height}｜{details}｜{time.perf_counter()-started:.1f}秒", (width, height)


def context_signature(context):
    resources = context.get("resource_context") or {}
    assets = []
    for kind in ("images", "videos", "audios"):
        for asset in resources.get(kind) or []:
            path = str(asset.get("path", ""))
            stat = os.stat(path)
            assets.append((kind, path, stat.st_size, stat.st_mtime_ns))
    project = context.get("project") or {}
    data = (context.get("prompt"), assets, context.get("seconds"), project.get("generation_mode", "自动"),
            project.get("ref_image_size", "match"), project.get("video_vae_model"), context.get("use_previous_video"))
    return hashlib.sha256(json.dumps(data, ensure_ascii=False).encode("utf-8")).hexdigest()


def save_latent(path, sampled, context, width, height, length):
    import comfy.utils
    from comfy_extras import nodes_lt

    video, audio = _avs_node_result(nodes_lt.LTXVSeparateAVLatent.execute(sampled))[:2]
    state = {"video": video["samples"].detach().cpu().contiguous(), "audio": audio["samples"].detach().cpu().contiguous()}
    for name, part in (("video_mask", video), ("audio_mask", audio)):
        if part.get("noise_mask") is not None:
            state[name] = part["noise_mask"].detach().cpu().contiguous()
    metadata = {"avs_version": "1", "signature": context_signature(context), "width": str(width),
                "height": str(height), "length": str(length), "seed": str(context.get("seed", 0))}
    temporary = path + ".tmp"
    comfy.utils.save_torch_file(state, temporary, metadata=metadata)
    os.replace(temporary, path)


def load_latent(path, context):
    import comfy.utils

    if not path or not os.path.isfile(path):
        return None
    state, metadata = comfy.utils.load_torch_file(path, safe_load=True, return_metadata=True)
    if metadata.get("avs_version") != "1" or metadata.get("signature") != context_signature(context):
        return None
    video, audio = {"samples": state["video"]}, {"samples": state["audio"]}
    if "video_mask" in state:
        video["noise_mask"] = state["video_mask"]
    if "audio_mask" in state:
        audio["noise_mask"] = state["audio_mask"]
    return (video, audio,
            {key: int(metadata[key]) for key in ("width", "height", "length", "seed")})


def neural_latent_upscale(latent, width, height, model_name="自动检测"):
    import nodes
    import comfy.model_management as mm

    upscaler = nodes.NODE_CLASS_MAPPINGS.get("AICG3D_H3LatentUpscaler3D") or nodes.NODE_CLASS_MAPPINGS.get("MiniMaxH3EasyLatentUpscaler3D")
    if upscaler is None:
        raise ValueError("H3 3D放大需要已启用的 AICG3D_H3LatentUpscaler3D 节点；可切换快速超分或 bicubic。")
    choices = folder_paths.get_filename_list("latent_upscale_models")
    if model_name == "自动检测":
        model_name = next((x for x in choices if "h3" in x.lower() and "fp16" in x.lower()), "")
    if not model_name:
        raise ValueError("没有找到 H3 latent 放大模型，请放入 models/latent_upscale_models。")
    mm.unload_all_models()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return _avs_node_result(upscaler.execute(latent=latent, model_name=model_name,
        mode={"mode": "target dimensions", "width": width, "height": height}, align=32,
        enable_chunking=True, device=device, precision="fp16" if device == "cuda" else "fp32"))[0]


class AVSFastPortraitFinish:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "视频": ("VIDEO",),
            "目标清晰度": (["1080P", "720P", "同分辨率", "1.5x", "2x"], {"default": "1080P"}),
            "超分模型": (["自动检测"] + folder_paths.get_filename_list("upscale_models"),),
            "人脸增强": ("BOOLEAN", {"default": True}),
            "增强强度": ("FLOAT", {"default": 0.55, "min": 0.0, "max": 1.0, "step": 0.05}),
            "分批帧数": ("INT", {"default": 2, "min": 1, "max": 8}),
            "仅增强人脸（更快）": ("BOOLEAN", {"default": True}),
        }}

    RETURN_TYPES = ("VIDEO", "STRING")
    RETURN_NAMES = ("高清人物视频", "处理摘要")
    FUNCTION = "finish"
    CATEGORY = "AI Video Studio/03 视频处理"
    DESCRIPTION = "学习型超分与中景人脸区域增强；不进行 H3 二次采样，保留帧数、帧率和音频。"

    def finish(self, 视频, 目标清晰度="1080P", 超分模型="自动检测", 人脸增强=True, 增强强度=0.55, 分批帧数=2, **kwargs):
        video, summary, _ = finish_video(视频, 目标清晰度, 超分模型, 人脸增强, 增强强度, 分批帧数, kwargs.get("仅增强人脸（更快）", True))
        return video, summary


NODE_CLASS_MAPPINGS = {"AVSFastPortraitFinish": AVSFastPortraitFinish}
NODE_DISPLAY_NAME_MAPPINGS = {"AVSFastPortraitFinish": "AI视频工作室｜快速人脸高清"}
