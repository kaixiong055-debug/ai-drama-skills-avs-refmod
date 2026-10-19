"""Optional RefMod binding for the director's internal H3 sampler.

Profiles store names only, never model tensors. A binding is loaded only when
an actual image reference matches its character keywords.
"""
from __future__ import annotations

import logging
import math
import re


def _registry():
    import nodes
    return nodes.NODE_CLASS_MAPPINGS


def _options():
    loader = _registry().get("MiniMaxH3RefModsLoader")
    if loader is None:
        return ["(none)"]
    return list(loader.INPUT_TYPES()["required"]["mod_1"][0])


def matching_bindings(bindings, resources):
    # Only inspect selected image assets, not free prose or unrelated library entries.
    texts = [" ".join(str(a.get(k, "")) for k in
             ("path", "file_name", "name", "display_name", "asset_id", "local_path"))
             for a in resources.get("images", [])]
    selected, seen = [], set()
    for item in bindings or []:
        if not item.get("enabled", True) or float(item.get("strength", 1)) <= 0:
            continue
        keywords = [s.strip() for s in str(item.get("keywords", "")).split("|") if s.strip()]
        def matches(keyword, text):
            # ASCII IDs need boundaries: CHAR_GYC must not select CHAR_GYC2.
            return bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(keyword) +
                                  r"(?![A-Za-z0-9])", text, re.I))
        if not any(matches(k, t) for k in keywords for t in texts):
            continue
        name = item.get("name", "")
        if name and name != "(none)" and name not in seen:
            selected.append(dict(item))
            seen.add(name)
    return selected


def apply_character_refmods(conditioning, project, resources, use_ref):
    selected = project.get("selected_character_refmods")
    auto_selected = selected is not None
    if selected is None:
        selected = matching_bindings(project.get("character_refmods", []), resources)
    if not selected:
        return conditioning
    if not use_ref:
        raise ValueError("人物 RefMod 需要多素材参考（REF2VA）模式；请关闭绑定或切换生成模式。")
    registry = _registry()
    loader = registry.get("MiniMaxH3RefModsLoader")
    apply = registry.get("MiniMaxH3RefModApply")
    if loader is None or apply is None:
        raise RuntimeError("人物 RefMod 已启用，但 ComfyUI-MiniMaxH3Mod 未成功加载。")
    if len(selected) > 8:
        raise ValueError("当前镜头匹配了超过 8 个 RefMod，请减少人物参考。")
    budget = int(project.get("character_refmod_max_tokens", 32768))
    # 人物库自动绑定由 bind_shot 统一控制镜头总预算。旧工作流可能仍保存 4096，
    # 自动绑定时至少提升到当前镜头实际所需 token，且绝不超过 32768。
    if auto_selected:
        required = sum(int(item.get("tokens", 0) or 0) for item in selected)
        budget = max(budget, required)
        budget = min(budget, 32768)
    if budget <= 0:
        raise ValueError("人物 RefMod token 上限必须大于 0。")
    kwargs = {}
    for i, item in enumerate(selected, 1):
        kwargs.update({f"mod_{i}": item["name"],
                       f"strength_{i}": float(item["strength"]), f"copies_{i}": 1})
    mods, _ = loader().load(show_info=False, max_total_tokens=budget, **kwargs)
    if any(getattr(mod, "kind", "") == "audio" for mod, _ in mods):
        raise ValueError("人物 RefMod 只接受图像/视频参考，请勿选择音频或含音频的合集。")
    out = apply.execute(conditioning=conditioning, mods=mods, retention=1.0,
                        curve_direction="constant", curve_shape="linear", curve_value=1.0,
                        scramble_seed=-1, override=False, max_total_tokens=budget)
    result = getattr(out, "result", out)
    logging.info("AVS 人物 RefMod：%s", ", ".join(x["name"] for x in selected))
    return result[0]


class AVSCharacterRefModProfile:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "H3模型配置": ("AVS_H3_MODEL_PROFILE",),
            "人物素材关键词": ("STRING", {"default": "CHAR_GYC|顾言川",
                "tooltip": "按本镜头 Picture 素材名称/路径匹配，多个别名用 | 分开。"}),
            "RefMod名称": (_options(),),
            "参考强度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05}),
            "启用": ("BOOLEAN", {"default": True}),
            "总参考token上限": ("INT", {"default": 32768, "min": 256, "max": 32768, "step": 256}),
        }}

    RETURN_TYPES = ("AVS_H3_MODEL_PROFILE", "STRING")
    RETURN_NAMES = ("H3模型配置", "绑定摘要")
    FUNCTION = "bind"
    CATEGORY = "AI Video Studio/02 模型配置"
    DESCRIPTION = "串在 H3模型配置和导演工作台之间。只加载当前镜头匹配的人物 RefMod；多个角色可串联。不会自动创建 RefMod。"

    def bind(self, H3模型配置, 人物素材关键词, RefMod名称, 参考强度=1.0, 启用=True, 总参考token上限=32768):
        strength = float(参考强度)
        if not math.isfinite(strength) or not 0 <= strength <= 1:
            raise ValueError("参考强度必须在 0 到 1 之间。")
        if 启用 and RefMod名称 != "(none)" and not 人物素材关键词.strip():
            raise ValueError("请填写人物素材关键词，避免将人物加载到所有镜头。")
        profile = dict(H3模型配置)
        items = [dict(x) for x in profile.get("character_refmods", [])]
        if 启用 and RefMod名称 != "(none)":
            items.append({"keywords": 人物素材关键词, "name": RefMod名称,
                          "strength": strength, "enabled": True})
        profile["character_refmods"] = items
        # A later binding cannot silently relax an earlier node's limit.
        profile["character_refmod_max_tokens"] = min(int(总参考token上限),
            int(profile.get("character_refmod_max_tokens", 总参考token上限)))
        return profile, "人物 RefMod：" + ("、".join(x["name"] for x in items) or "未启用")


NODE_CLASS_MAPPINGS = {"AVSCharacterRefModProfile": AVSCharacterRefModProfile}
NODE_DISPLAY_NAME_MAPPINGS = {"AVSCharacterRefModProfile": "AI视频工作室｜人物RefMod配置"}
