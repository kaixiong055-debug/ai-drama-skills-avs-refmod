"""Director actor-library endpoints and its queued, local-only preparation node."""
from __future__ import annotations

import json
from pathlib import Path
from aiohttp import web
import folder_paths
from . import character_store as store
from . import wardrobe_store


def plugin_nodes():
    import nodes
    required = ("MiniMaxH3RefModExtract", "MiniMaxH3RefModBundleSave", "MiniMaxH3RefModsLoader", "MiniMaxH3RefModApply")
    if any(name not in nodes.NODE_CLASS_MAPPINGS for name in required):
        raise ValueError("请先安装并启用 ComfyUI-MiniMaxH3Mod，再重启 ComfyUI。")
    return nodes.NODE_CLASS_MAPPINGS


def preparation_graph(cid, vae_name, force_rebuild=False):
    plugin_nodes()
    c = store.get_character(cid)
    store.component_signature(c, "identity", vae_name)
    expected = {key: store.component_signature(c, key, vae_name) for key, refs in store.components(c) if refs}
    if not force_rebuild and all((store.prepared_component(c, key) or {}).get("signature") == sig for key, sig in expected.items()):
        return {"cached": True, "character": store.public_character(c)}
    return {"cached": False, "prompt": {
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": vae_name}},
        "prepare": {"class_type": "AVSPrepareCharacter", "inputs": {
            "vae": ["vae", 0], "character_id": cid, "vae_name": vae_name,
            "expected": json.dumps(expected), "force_rebuild": force_rebuild}}}}


class AVSPrepareCharacter:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"vae": ("VAE",), "character_id": ("STRING",),
                             "vae_name": ("STRING",), "expected": ("STRING",)},
                "optional": {"force_rebuild": ("BOOLEAN", {"default": False})}}

    RETURN_TYPES = ("STRING",)
    FUNCTION = "prepare"
    OUTPUT_NODE = True
    CATEGORY = "AI Video Studio/内部任务"
    DESCRIPTION = "由导演工作台人物库排队执行；使用本地H3 VAE编码用户上传的参考图片。"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def prepare(self, vae, character_id, vae_name, expected, force_rebuild=False):
        import numpy as np
        import torch
        from PIL import Image, ImageOps
        from comfy.ldm.minimax.vae import MiniMaxH3VideoVAE
        import comfy.model_management
        if not isinstance(vae.first_stage_model, MiniMaxH3VideoVAE):
            raise ValueError("人物参考需要H3视频VAE，不能使用音频或其他模型VAE。")
        registry = plugin_nodes()
        extract = registry["MiniMaxH3RefModExtract"]
        save = registry["MiniMaxH3RefModBundleSave"]()
        signatures = json.loads(expected)
        removed = 0
        if force_rebuild:
            comfy.model_management.throw_exception_if_processing_interrupted()
            removed = store.clear_prepared(character_id, signatures, vae_name)
        snapshot = store.get_character(character_id)
        for key, refs in store.components(snapshot):
            if not refs:
                continue
            signature = store.component_signature(snapshot, key, vae_name)
            if signatures.get(key) != signature:
                raise ValueError("人物图片在排队后发生变化，请重新点击准备。")
            cached = store.prepared_component(snapshot, key)
            if cached and cached["signature"] == signature:
                continue
            mods = []
            for index, ref in enumerate(refs):
                comfy.model_management.throw_exception_if_processing_interrupted()
                # Each image retains its own aspect ratio; no cover-cropping a
                # multi-view sheet into the portrait's canvas.
                with Image.open(store.image_path(ref)) as opened:
                    im = ImageOps.exif_transpose(opened).convert("RGB")
                    edge = snapshot["resolution"]
                    scale = min(1.0, edge / min(im.size), edge * 2 / max(im.size))
                    im = im.resize((max(32, round(im.width * scale)), max(32, round(im.height * scale))), Image.Resampling.LANCZOS)
                    pixels = torch.from_numpy(np.array(im, dtype=np.float32) / 255.0).unsqueeze(0)
                out = extract.execute(name=f"ref_{index}", mode="Full Reference", vae=vae,
                    refs_image={"ref_image_1": pixels}, ref_resolution=edge,
                    pool_h=64, pool_w=64, latent_frames=1, identity=0, merge=False,
                    multiplier=1, max_tokens=4096, budget_policy="error", save=False,
                    concept_type="identity" if key == "identity" else "clothing",
                    description=f"{snapshot['name']} / {key}", extraction_preset="manual")
                mods.extend(out.result[0])
                del pixels, out
            tokens = sum(m.token_count for m, _ in mods)
            if tokens > 4096:
                raise ValueError("这组参考图过多，请减少角度或降低参考精度。")
            name = f"{key}_{signature[:20]}"
            subfolder = f"AVS_Characters/{character_id}"
            saved = save.save(mods=mods, name=name, subfolder=subfolder)
            path = saved["result"][1]
            store.publish_component(character_id, key, signature, {
                "vae": vae_name, "mod_name": f"{subfolder}/{name}",
                "path": path, "tokens": tokens})
            del mods, saved
        message = f"已删除 {removed} 个旧参考文件，人物参考已重新生成。" if force_rebuild else "人物参考已准备，可以在导演工作台选择使用。"
        return {"ui": {"text": [message]},
                "result": (character_id,)}


def register_routes(server):
    def failure(exc):
        return web.json_response({"ok": False, "error": str(exc)}, status=400)

    @server.routes.get("/avs/characters")
    async def list_characters(request):
        try:
            with store.LOCK:
                records = store.read_library()["characters"]
            vaes = [x for x in folder_paths.get_filename_list("vae") if "h3" in x.lower() and "audio" not in x.lower()]
            available = True
            try:
                plugin_nodes()
            except ValueError:
                available = False
            return web.json_response({"ok": True, "characters": [store.public_character(c) for c in records],
                                      "vaes": vaes, "refmod_available": available})
        except Exception as exc:
            return failure(exc)

    @server.routes.post("/avs/characters")
    async def save_character(request):
        try:
            return web.json_response({"ok": True, "character": store.public_character(store.save_character(await request.json()))})
        except Exception as exc:
            return failure(exc)

    @server.routes.post("/avs/characters/prepare")
    async def prepare_character(request):
        try:
            raw = await request.json()
            return web.json_response({"ok": True, **preparation_graph(raw.get("character_id"), raw.get("vae_name", ""), raw.get("force_rebuild") is True)})
        except Exception as exc:
            return failure(exc)

    @server.routes.get("/avs/wardrobes")
    async def list_global_wardrobes(request):
        try:
            return web.json_response({"ok": True, "status": wardrobe_store.status(),
                                      "wardrobes": wardrobe_store.list_wardrobes()})
        except Exception as exc:
            return failure(exc)

    @server.routes.post("/avs/wardrobes/root")
    async def set_global_wardrobe_root(request):
        try:
            raw = await request.json()
            wardrobe_store.set_root(str(raw.get("path", "")))
            return web.json_response({"ok": True, "status": wardrobe_store.status(),
                                      "wardrobes": wardrobe_store.list_wardrobes()})
        except Exception as exc:
            return failure(exc)

    @server.routes.post("/avs/wardrobes/use-resource-library")
    async def use_resource_library_for_wardrobes(request):
        try:
            wardrobe_store.use_permanent_library()
            return web.json_response({"ok": True, "status": wardrobe_store.status(),
                                      "wardrobes": wardrobe_store.list_wardrobes()})
        except Exception as exc:
            return failure(exc)

    @server.routes.post("/avs/wardrobes/save")
    async def save_global_wardrobe(request):
        try:
            record = wardrobe_store.save_wardrobe(await request.json())
            return web.json_response({"ok": True, "wardrobe": record, "status": wardrobe_store.status()})
        except Exception as exc:
            return failure(exc)

    @server.routes.post("/avs/wardrobes/materialize")
    async def materialize_global_wardrobe(request):
        try:
            raw = await request.json()
            return web.json_response({"ok": True, **wardrobe_store.materialize(str(raw.get("id", "")))})
        except Exception as exc:
            return failure(exc)

    @server.routes.delete("/avs/wardrobes/{wardrobe_id}")
    async def delete_global_wardrobe(request):
        try:
            wardrobe_store.delete_wardrobe(str(request.match_info["wardrobe_id"]))
            return web.json_response({"ok": True, "status": wardrobe_store.status(),
                                      "wardrobes": wardrobe_store.list_wardrobes()})
        except Exception as exc:
            return failure(exc)

    @server.routes.get("/avs/wardrobes/image/{wardrobe_id}/{index}")
    async def global_wardrobe_image(request):
        try:
            index = int(request.match_info["index"])
            return web.FileResponse(wardrobe_store.image_path(str(request.match_info["wardrobe_id"]), index))
        except Exception as exc:
            return failure(exc)


NODE_CLASS_MAPPINGS = {"AVSPrepareCharacter": AVSPrepareCharacter}
NODE_DISPLAY_NAME_MAPPINGS = {"AVSPrepareCharacter": "AI视频工作室｜准备人物参考（内部）"}
