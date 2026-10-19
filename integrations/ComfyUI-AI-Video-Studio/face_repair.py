"""Reference-guided H3 temporal face refinement.

V4 goals (v0.18.2):
- Keep the simple user policy, while adding an explicit "近景稳定" mode.
- Close faces use low-denoise / low-blend detail refinement instead of identity reconstruction.
- Medium / distant faces keep stronger reference-guided reconstruction.
- All H3 face chunks in one repair task use ONE seed.
- Chunks are generated sequentially with 22-frame carry-over context instead of independent overlaps.
- Crop boxes and paste-back transforms are temporally smoothed.
- If a character RefMod is already bound, reuse it at a conservative capped strength.
"""
from __future__ import annotations

import logging
from pathlib import Path
import time

import cv2
import numpy as np
import torch

MODE = "人脸局部修复（参考头像）"
DETECTOR = Path(__file__).parent / "models/face_detection/face_detection_yunet_2023mar.onnx"


class FaceDetector:
    def __init__(self, max_edge=1280, score_threshold=0.65):
        if not DETECTOR.is_file():
            raise ValueError("缺少人脸检测文件，请完整上传新版插件的 models/face_detection 文件夹。")
        self.max_edge = int(max(640, max_edge))
        self.model = cv2.FaceDetectorYN.create(
            str(DETECTOR), "", (320, 320), float(score_threshold), 0.3, 5000
        )

    def detect(self, rgb):
        h, w = rgb.shape[:2]
        scale = min(1.0, self.max_edge / max(h, w))
        iw, ih = max(1, round(w * scale)), max(1, round(h * scale))
        image = cv2.resize(
            np.uint8(np.clip(rgb, 0, 1) * 255),
            (iw, ih),
            interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
        )
        self.model.setInputSize((image.shape[1], image.shape[0]))
        _, faces = self.model.detect(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if faces is None:
            return []
        result = []
        for face in faces:
            face = face.copy()
            face[:14] /= scale
            result.append(face)
        return result


def crop_box(face, width, height, previous_state=None, center_prev=0.35, size_prev=0.70):
    """Return a temporally stable square around one face.

    center_prev / size_prev express how much the previous crop state is retained.
    Near-face stable repair uses 0.85/0.85; distant repair stays more responsive.
    """
    x, y, w, h = map(float, face[:4])
    cx, cy = x + w / 2, y + h / 2
    size = max(w, h) * 2.0
    if previous_state is not None:
        pcx, pcy, psize = previous_state
        cp = float(np.clip(center_prev, 0.0, 0.98))
        sp = float(np.clip(size_prev, 0.0, 0.98))
        cx = cp * pcx + (1.0 - cp) * cx
        cy = cp * pcy + (1.0 - cp) * cy
        size = sp * psize + (1.0 - sp) * size
    side = max(1, min(round(size), width, height))
    left = min(max(round(cx - side / 2), 0), width - side)
    top = min(max(round(cy - side / 2), 0), height - side)
    return (left, top, left + side, top + side), (cx, cy, size)


def _face_sharpness(frame, face):
    x, y, w, h = [int(round(v)) for v in face[:4]]
    height, width = frame.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(width, x + max(1, w)), min(height, y + max(1, h))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return 0.0
    crop = np.uint8(np.clip(frame[y0:y1, x0:x1], 0, 1) * 255)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_32F).var())


def _auto_should_repair(frame, face):
    """Automatic policy remains conservative for close faces.

    Users who *do* want a close face refined can explicitly choose 近景稳定.
    """
    h = max(float(face[3]), 1.0)
    ratio = h / max(1.0, float(frame.shape[0]))
    sharpness = _face_sharpness(frame, face)
    if ratio <= 0.16:
        return True, ratio, sharpness
    if ratio < 0.24 and sharpness < 75.0:
        return True, ratio, sharpness
    return False, ratio, sharpness


def _repair_profile(ratio: float, policy: str) -> dict:
    """Choose a stable-detail or reconstruction profile for one contiguous face run."""
    if policy == "近景稳定":
        tier = "近景稳定"
    elif policy == "中远景重建":
        tier = "中远景重建" if ratio > 0.04 else "远景身份重建"
    elif ratio >= 0.15:
        tier = "近景稳定"
    elif ratio >= 0.08:
        tier = "中景修复"
    elif ratio >= 0.04:
        tier = "中远景重建"
    else:
        tier = "远景身份重建"

    # Values are deliberately conservative for near faces.  The near profile
    # matches the production values requested for the jittering 480p test clip.
    profiles = {
        "近景稳定": {
            "edge": 768,
            "strength": 0.30,
            "blend": 0.30,
            "landmark_prev": 0.80,
            "crop_center_prev": 0.85,
            "crop_size_prev": 0.85,
            "color_prev": 0.45,
            "refmod_cap": 0.25,
        },
        "中景修复": {
            "edge": 512,
            "strength": 0.48,
            "blend": 0.48,
            "landmark_prev": 0.68,
            "crop_center_prev": 0.65,
            "crop_size_prev": 0.78,
            "color_prev": 0.35,
            "refmod_cap": 0.30,
        },
        "中远景重建": {
            "edge": 768,
            "strength": 0.68,
            "blend": 0.68,
            "landmark_prev": 0.55,
            "crop_center_prev": 0.50,
            "crop_size_prev": 0.72,
            "color_prev": 0.30,
            "refmod_cap": 0.35,
        },
        "远景身份重建": {
            "edge": 768,
            "strength": 0.82,
            "blend": 0.78,
            "landmark_prev": 0.45,
            "crop_center_prev": 0.40,
            "crop_size_prev": 0.68,
            "color_prev": 0.25,
            "refmod_cap": 0.45,
        },
    }
    result = dict(profiles[tier])
    result["tier"] = tier
    return result


def face_mask(face, box, edge):
    x0, y0, x1, y1 = box
    x, y, w, h = map(float, face[:4])
    scale = edge / max(1, (x1 - x0))
    yy, xx = np.mgrid[:edge, :edge].astype(np.float32)
    cx, cy = (x + w / 2 - x0) * scale, (y + h * 0.53 - y0) * scale
    radius = ((xx - cx) / max(1, w * 0.57 * scale)) ** 2 + ((yy - cy) / max(1, h * 0.64 * scale)) ** 2
    return np.clip((1 - radius) / 0.35, 0, 1)[..., None]


def estimate_face_transform(points, target_points):
    transform, _ = cv2.estimateAffinePartial2D(points, target_points, method=cv2.LMEDS)
    if transform is None or not np.isfinite(transform).all():
        return None
    scale = np.linalg.norm(transform[0, :2])
    projected = cv2.transform(points[None].astype(np.float32), transform)[0]
    error = np.linalg.norm(projected - target_points, axis=1)
    eye_distance = np.linalg.norm(target_points[0] - target_points[1])
    if not 0.8 <= scale <= 1.25 or error.max() > max(1.0, eye_distance * 0.03):
        return None
    return transform.astype(np.float32)


def smooth_transform(current, previous, previous_weight):
    if previous is None:
        return current
    w = float(np.clip(previous_weight, 0.0, 0.95))
    return (previous * w + current * (1.0 - w)).astype(np.float32)


def warp_face(generated, transform):
    edge = generated.shape[0]
    return cv2.warpAffine(generated, transform, (edge, edge), borderMode=cv2.BORDER_REFLECT_101)


def match_face_color(original, generated, mask, previous_offset, amount):
    region = mask[..., 0] > 0.5
    offset = original[region].mean(0) - generated[region].mean(0) if region.any() else np.zeros(3, np.float32)
    if previous_offset is not None:
        amount = float(np.clip(amount, 0.0, 0.95))
        offset = offset * (1 - amount) + previous_offset * amount
    return np.clip(generated + offset, 0, 1), offset


def composite_face(original, generated, mask, blend_strength=1.0):
    height, width = original.shape[:2]
    restored = cv2.resize(generated, (width, height), interpolation=cv2.INTER_AREA)
    alpha = cv2.resize(mask, (width, height), interpolation=cv2.INTER_AREA)[..., None]
    alpha = np.clip(alpha * float(np.clip(blend_strength, 0.0, 1.0)), 0.0, 1.0)
    return original * (1 - alpha) + restored * alpha


def _stable_boxes(group, tracks, width, height, profile):
    boxes = {}
    state = None
    for index in group:
        face = tracks[index]
        if face is None:
            state = None
            continue
        box, state = crop_box(
            face, width, height, state,
            center_prev=profile["crop_center_prev"],
            size_prev=profile["crop_size_prev"],
        )
        boxes[index] = box
    return boxes


def repair_context(context, refmod_cap=0.0):
    # Context may contain a VIDEO object; do not duplicate its decoded frames.
    ctx = dict(context)
    index = ctx.get("selected_index", 0)
    shots = ctx.get("timeline", {}).get("shots", [])
    selected = shots[index].get("character_selections", []) if index < len(shots) else []
    if len(selected) > 1:
        raise ValueError("自动人脸修复目前只锁定单一人物身份；多人镜头将跳过修复。")
    if selected:
        from .character_store import get_character, image_path
        person = get_character(selected[0]["character_id"])
        if not person.get("refs"):
            raise ValueError("请在人物库上传单独的清晰正脸。")
        path = str(image_path(person["refs"][0]))
    else:
        pics = ctx.get("shot", {}).get("compiled_picture_refs", [])
        path = next((p["path"] for p in pics if p["visible_picture"] == 1), "")
        if not path:
            raise ValueError("人脸修复需要人物库正脸，或 Picture 1 中的单独清晰正脸。")

    ctx.pop("first_latent_path", None)
    ctx["resource_context"] = {"images": [{"path": path}], "videos": [], "audios": []}
    shot = dict(ctx.get("shot", {}))
    active = shot.get("selected_character_refmods") or []
    limited = []
    if refmod_cap > 0:
        for item in active:
            item = dict(item)
            item["strength"] = min(float(item.get("strength", 1.0)), float(refmod_cap))
            if item["strength"] > 0:
                limited.append(item)
    shot["selected_character_refmods"] = limited
    shot["use_previous_video"] = False
    ctx["shot"] = shot
    ctx["use_previous_video"] = False
    ctx["prompt"] = (
        "subject_definitions:\n<Subject 1> is the same adult person as <Picture 1>.\n\n"
        "summary:\nA continuous face close-up. Preserve the source person's exact pose, expression and motion. "
        "Restore only missing facial detail with strong temporal consistency.\n\n"
        "retention_analysis:\n<Subject 1>: fully_preserved - identity, eye shape, nose, lips, jaw and age must stay stable. "
        "Keep head angle, gaze, mouth movement, lighting, hairstyle and source timing.\n\n"
        "detailed_description:\n[Shot 1] Preserve the input video's composition and motion frame by frame. "
        "For close faces, add only subtle eye-edge, eyelash, lip-edge, skin and hairline detail; do not redesign facial geometry. "
        "For distant faces, reconstruct missing detail from Picture 1 while preserving motion. "
        "No face morphing, no beauty filter, no new gestures, no cuts, no identity drift.\n\n"
        "overall_soundscape:\nNo new speech.\n\nnon_diegetic_music:\nN/A"
    )
    return ctx, path, bool(limited)


def _make_clip(images, fps):
    from comfy_extras import nodes_video
    from .nodes import _avs_node_result
    return _avs_node_result(
        nodes_video.CreateVideo.execute(
            images=torch.from_numpy(np.stack(images)),
            fps=float(fps), audio=None, bit_depth="auto", color_space="sRGB", codec="none",
        )
    )[0]


def _run_sequential_h3(group, boxes, frames, edge, ctx, render_project, render_settings,
                       refine_clip, fps, task_seed, progress):
    """Generate a face run with 22 generated frames carried into every next H3 window.

    H3 still receives 39 frames per call, but only the first call is standalone.
    Every subsequent call is [22 frames from previous generated result] + [up to 17 new source frames].
    This removes the hard A/B face switch that the old 34-frame stepped windows produced.
    """
    import comfy.model_management as mm

    window = 39
    carry = 22
    new_per_call = window - carry
    generated_by_index = {}
    cursor = 0
    previous_context = []
    chunk_count = 0

    while cursor < len(group):
        mm.throw_exception_if_processing_interrupted()
        if not previous_context:
            ids = group[cursor:cursor + window]
            source_crops = []
            for index in ids:
                x0, y0, x1, y1 = boxes[index]
                source_crops.append(cv2.resize(frames[index, y0:y1, x0:x1].numpy(), (edge, edge)))
            valid_count = len(source_crops)
            if not source_crops:
                break
            inputs = list(source_crops)
            inputs += [inputs[-1]] * (window - len(inputs))
            new_offset = 0
            new_ids = ids
        else:
            new_ids = group[cursor:cursor + new_per_call]
            source_crops = []
            for index in new_ids:
                x0, y0, x1, y1 = boxes[index]
                source_crops.append(cv2.resize(frames[index, y0:y1, x0:x1].numpy(), (edge, edge)))
            if not source_crops:
                break
            inputs = list(previous_context[-carry:]) + source_crops
            valid_count = len(inputs)
            inputs += [inputs[-1]] * (window - len(inputs))
            new_offset = carry

        clip = _make_clip(inputs, fps)
        local = {**ctx, "seconds": window / float(fps), "seed": int(task_seed)}
        logging.info(
            "AVS 人脸修复连续窗：新帧 %s–%s，carry=%s，edge=%s，seed=%s",
            new_ids[0] + 1, new_ids[-1] + 1, 0 if not previous_context else carry, edge, task_seed,
        )
        generated, _, _ = refine_clip(clip, local, render_project, render_settings)
        result = generated.get_components().images.detach().cpu().float().numpy()
        if len(result) < window:
            raise ValueError("人脸修复模型返回帧数不足，已停止合成；原视频仍保留。")

        # Store only genuinely new frames. Context frames are continuity guides, not replacements.
        for j, index in enumerate(new_ids):
            generated_by_index[index] = cv2.resize(result[new_offset + j], (edge, edge))

        # Carry the last 22 *valid* generated positions into the next call.
        valid_end = min(window, valid_count)
        valid_start = max(0, valid_end - carry)
        previous_context = [cv2.resize(x, (edge, edge)) for x in result[valid_start:valid_end]]
        if len(previous_context) < carry:
            previous_context = ([previous_context[0]] * (carry - len(previous_context)) + previous_context) if previous_context else []

        cursor += len(new_ids)
        chunk_count += 1
        progress.update_absolute(min(group[-1] + 1, int(group[min(cursor - 1, len(group)-1)]) + 1))
        del clip, generated, result

    return generated_by_index, chunk_count


def repair_video(source_video, context, project, settings, refine_clip):
    from PIL import Image, ImageOps
    from comfy_extras import nodes_video
    from .nodes import _avs_node_result
    import comfy.model_management as mm
    import comfy.utils

    started = time.perf_counter()
    policy = str(settings.get("face_repair_mode", settings.get("repair_policy", "强制")) or "强制")
    legacy = {"强制重建": "中远景重建"}
    policy = legacy.get(policy, policy)
    allowed = {"关闭", "自动", "近景稳定", "中远景重建", "强制"}
    if policy not in allowed:
        policy = "自动"
    if policy == "关闭":
        comps = source_video.get_components()
        return source_video, "人脸修复：关闭", (int(comps.images.shape[2]), int(comps.images.shape[1]))

    components = source_video.get_components()
    frames = components.images.detach().cpu().float()
    count, height, width, _ = frames.shape
    fps = float(components.frame_rate or 24.0)
    if count <= 0:
        raise ValueError("人脸修复没有收到有效视频帧。")

    detector = FaceDetector(
        max_edge=int(settings.get("face_detection_size", 1280)),
        score_threshold=float(settings.get("face_detection_score", 0.65)),
    )

    # Identity reference is resolved once. RefMod strength is selected later per group;
    # we initially validate the portrait without enabling a mod.
    try:
        base_ctx, reference, _ = repair_context(context, 0.0)
    except ValueError as exc:
        if policy == "自动":
            return source_video, f"人脸修复：自动跳过｜{exc}", (width, height)
        raise

    with Image.open(reference) as im:
        reference_rgb = np.array(ImageOps.exif_transpose(im).convert("RGB"), dtype=np.float32) / 255
    if len(detector.detect(reference_rgb)) != 1:
        if policy == "自动":
            return source_video, "人脸修复：自动跳过｜参考图没有检测到唯一人脸", (width, height)
        raise ValueError("参考图没有检测到唯一人脸，请使用单独的清晰正脸，不要用四视拼图。")

    output = frames.clone()
    tracks = []              # one detected face or None for every source frame
    groups, group = [], []
    previous_gray = None
    detected_count = eligible_count = multi_face_frames = 0
    ratios, sharpness_values = [], []

    for i in range(count):
        mm.throw_exception_if_processing_interrupted()
        frame = frames[i].numpy()
        gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), (48, 48))
        cut = previous_gray is not None and np.abs(gray - previous_gray).mean() > 0.2
        previous_gray = gray
        faces = detector.detect(frame)

        if len(faces) != 1:
            if group:
                groups.append(group)
            group = []
            tracks.append(None)
            if len(faces) > 1:
                multi_face_frames += 1
            continue

        detected_count += 1
        face = faces[0]
        tracks.append(face)
        ratio = max(float(face[3]), 1.0) / max(1.0, float(height))
        sharpness = _face_sharpness(frame, face)
        ratios.append(ratio)
        sharpness_values.append(sharpness)

        if cut:
            if group:
                groups.append(group)
            group = []

        if policy == "自动":
            needs_repair, _, _ = _auto_should_repair(frame, face)
        else:
            needs_repair = True
        if needs_repair:
            eligible_count += 1
            group.append(i)
        else:
            if group:
                groups.append(group)
            group = []

    if group:
        groups.append(group)
    groups = [g for g in groups if len(g) >= 5]

    if not groups:
        if policy == "自动":
            ratio_note = f"｜中位脸高占比 {np.median(ratios)*100:.1f}%" if ratios else ""
            sharp_note = f"｜中位清晰度 {np.median(sharpness_values):.0f}" if sharpness_values else ""
            reason = "检测到的近景脸已足够清晰；如仍想补细节请选择【近景稳定】" if detected_count else "没有检测到可处理的人脸"
            if multi_face_frames:
                reason += f"；多人帧 {multi_face_frames} 已保护性跳过"
            return source_video, f"人脸修复：自动判定无需修复｜{reason}{ratio_note}{sharp_note}", (width, height)
        raise ValueError("没有检测到连续可修复的单人人脸；原视频已保留。")

    progress = comfy.utils.ProgressBar(count)
    repaired_count = chunk_count = 0
    tier_counts = {}
    task_seed = int(base_ctx.get("seed", context.get("seed", 0)) or 0)  # ONE seed for the whole repair task

    for group in groups:
        mm.throw_exception_if_processing_interrupted()
        group_ratios = [max(float(tracks[i][3]), 1.0) / max(1.0, float(height)) for i in group if tracks[i] is not None]
        ratio = float(np.median(group_ratios)) if group_ratios else 0.1
        profile = _repair_profile(ratio, policy)
        tier_counts[profile["tier"]] = tier_counts.get(profile["tier"], 0) + 1
        edge = int(profile["edge"])

        # Explicit near repair values: 0.20 * 0.30 = 0.06 actual denoise.
        base_denoise = float(settings.get("denoise", 0.20))
        effective_denoise = base_denoise * float(profile["strength"])
        render_settings = {
            **settings,
            "mode": "同分辨率精修",
            "target": "同分辨率",
            "upscale_method": "bicubic",
            "keep_ref_size": True,
            "preserve_audio": True,
            "face_enhance": False,
            "denoise": effective_denoise,
            "seed_mode": "固定",
            "seed": task_seed,
        }
        render_project = {
            **project,
            "generation_mode": "多素材参考",
            "audio_mode": "完全静音",
            "ref_image_size": "match",
            "face_repair_mode": "关闭",
        }

        ctx, _, refmod_used = repair_context(context, profile["refmod_cap"])
        boxes = _stable_boxes(group, tracks, width, height, profile)
        generated_by_index, used_chunks = _run_sequential_h3(
            group, boxes, frames, edge, ctx, render_project, render_settings,
            refine_clip, fps, task_seed, progress,
        )
        chunk_count += used_chunks

        previous_offset = None
        previous_transform = None
        for index in group:
            mm.throw_exception_if_processing_interrupted()
            if index not in generated_by_index or tracks[index] is None or index not in boxes:
                previous_offset = None
                previous_transform = None
                continue
            face = tracks[index]
            box = boxes[index]
            x0, y0, x1, y1 = box
            original = cv2.resize(frames[index, y0:y1, x0:x1].numpy(), (edge, edge))
            generated = generated_by_index.pop(index)
            generated_faces = detector.detect(generated)
            original_faces = detector.detect(original)
            if len(generated_faces) != 1 or len(original_faces) != 1:
                previous_offset = None
                previous_transform = None
                continue
            target_points = original_faces[0][4:14].reshape(5, 2)
            points = generated_faces[0][4:14].reshape(5, 2)
            if np.linalg.norm(points - target_points, axis=1).mean() > edge * 0.2:
                previous_offset = None
                previous_transform = None
                continue
            transform = estimate_face_transform(points, target_points)
            if transform is None:
                previous_offset = None
                previous_transform = None
                continue
            transform = smooth_transform(transform, previous_transform, profile["landmark_prev"])
            previous_transform = transform
            generated = warp_face(generated, transform)
            mask = face_mask(face, box, edge)
            generated, previous_offset = match_face_color(
                original, generated, mask, previous_offset, profile["color_prev"]
            )
            composite = composite_face(
                frames[index, y0:y1, x0:x1].numpy(), generated, mask, profile["blend"]
            )
            output[index, y0:y1, x0:x1] = torch.from_numpy(composite).clamp(0, 1)
            repaired_count += 1
            progress.update_absolute(index + 1)

    if repaired_count == 0:
        if policy == "自动":
            return source_video, "人脸修复：自动尝试后未通过五官位置检查，已安全保留原片", (width, height)
        raise ValueError("修复结果未通过人脸位置检查，已保留原片；请更换清晰参考头像。")

    progress.update_absolute(count)
    video = _avs_node_result(
        nodes_video.CreateVideo.execute(
            images=output, fps=fps, audio=components.audio,
            bit_depth="auto", color_space="sRGB", codec="none",
        )
    )[0]
    ratio_note = f"｜中位脸高 {np.median(ratios)*100:.1f}%" if ratios else ""
    tiers = "、".join(f"{k}×{v}" for k, v in tier_counts.items())
    summary = (
        f"人脸修复：{policy}｜{tiers}｜修复 {repaired_count}/{count} 帧｜候选 {eligible_count} 帧"
        f"｜22帧连续上下文｜整段固定Seed {task_seed}｜{chunk_count}个H3连续窗"
        f"｜Landmark时序平滑｜裁剪框时序平滑{ratio_note}"
        f"｜多人帧跳过 {multi_face_frames}｜{time.perf_counter()-started:.1f}秒"
    )
    return video, summary, (width, height)
