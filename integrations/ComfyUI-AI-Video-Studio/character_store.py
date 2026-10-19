"""Disk-backed actor records. Names are labels; all relationships use stable IDs."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import uuid

LOCK = threading.RLock()
FORMAT = 1


def library_path():
    import folder_paths
    return Path(folder_paths.get_user_directory()) / "ai_video_studio" / "characters" / "library.json"


def read_library():
    p = library_path()
    if not p.exists():
        return {"version": FORMAT, "characters": []}
    data = json.loads(p.read_text("utf-8"))
    if not isinstance(data.get("characters"), list):
        raise ValueError("人物库数据损坏，请保留文件并检查备份。")
    return data


def write_library(data):
    p = library_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    temporary = p.with_name(p.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, p)
    finally:
        temporary.unlink(missing_ok=True)


def get_character(character_id):
    with LOCK:
        for c in read_library()["characters"]:
            if c["id"] == character_id:
                return copy.deepcopy(c)
    raise ValueError("人物不存在，请在人物库重新选择。")


def image_path(ref):
    import folder_paths
    root = Path(folder_paths.get_input_directory()).resolve()
    p = Path(str(ref.get("path", ""))).resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise ValueError("人物参考图片不存在，请从电脑重新上传。")
    if p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        raise ValueError("人物参考只支持静态图片。")
    return p


def _refs(refs):
    if not isinstance(refs, list) or len(refs) > 4:
        raise ValueError("每组人物/造型最多使用4张参考图。")
    result = []
    for r in refs:
        p = image_path(r)
        result.append({"path": str(p), "name": str(r.get("name") or p.name)[:160],
                       "filename": p.name, "subfolder": str(p.parent.relative_to(
                           Path(__import__("folder_paths").get_input_directory()).resolve())).replace("\\", "/"),
                       "type": "input"})
    return result


def save_character(raw):
    with LOCK:
        data = read_library()
        cid = str(raw.get("id") or uuid.uuid4().hex)
        if not re.fullmatch(r"[a-f0-9]{32}", cid):
            raise ValueError("人物ID无效。")
        old = next((x for x in data["characters"] if x["id"] == cid), None)
        if old and raw.get("revision") != old["revision"]:
            raise ValueError("人物资料已在其他窗口更新，请刷新后重试。")
        name = str(raw.get("name", "")).strip()[:80]
        if not name:
            raise ValueError("请填写人物姓名。")
        resolution = int(raw.get("resolution", 512))
        if resolution not in (512, 768, 1024):
            raise ValueError("参考精度只支持512、768或1024。")
        wardrobes, seen = [], set()
        for w in raw.get("wardrobes", []):
            wid = str(w.get("id") or uuid.uuid4().hex)
            if not re.fullmatch(r"[a-f0-9]{32}", wid) or wid in seen:
                raise ValueError("造型ID重复或无效。")
            seen.add(wid)
            wardrobes.append({"id": wid, "name": str(w.get("name") or "未命名造型")[:80],
                              "refs": _refs(w.get("refs", [])),
                              "global_wardrobe_id": str(w.get("global_wardrobe_id") or "")[:32],
                              "global_revision": int(w.get("global_revision") or 0)})
        if len(wardrobes) > 24:
            raise ValueError("单个人物最多保存24套造型。")
        c = {"id": cid, "name": name, "revision": (old or {}).get("revision", 0) + 1,
             "resolution": resolution, "refs": _refs(raw.get("refs", [])), "wardrobes": wardrobes,
             "prepared": copy.deepcopy((old or {}).get("prepared", {}))}
        data["characters"] = [x for x in data["characters"] if x["id"] != cid] + [c]
        write_library(data)
        return c


def components(c):
    return [("identity", c.get("refs", []))] + [(w["id"], w.get("refs", [])) for w in c.get("wardrobes", [])]


def clear_prepared(character_id, expected, vae_name):
    """Called by the queued preparation job, never by the HTTP request."""
    import folder_paths
    if not re.fullmatch(r"[a-f0-9]{32}", str(character_id)):
        raise ValueError("人物ID无效。")
    with LOCK:
        data = read_library()
        c = next((x for x in data["characters"] if x["id"] == character_id), None)
        if c is None:
            raise ValueError("人物不存在，请重新选择。")
        actual = {key: component_signature(c, key, vae_name) for key, refs in components(c) if refs}
        if not c.get("refs") or actual != expected:
            raise ValueError("人物图片在排队后发生变化，请重新点击准备。")
        paths = set()
        for registered in folder_paths.get_folder_paths("refmods"):
            root = Path(registered).resolve()
            relative = Path("AVS_Characters") / character_id
            directory = (root / relative).resolve()
            if not directory.is_relative_to(root) or directory.relative_to(root) != relative:
                raise ValueError("人物参考目录指向其他位置，已停止清理。")
            if not directory.is_dir():
                continue
            for path in directory.iterdir():
                if not re.fullmatch(r"(?:identity|[a-f0-9]{32})_[a-f0-9]{20}\.safetensors", path.name):
                    continue
                if path.is_symlink() or path.resolve().parent != directory or not path.is_file():
                    raise ValueError("人物参考文件路径异常，已停止清理。")
                paths.add(path)
        # Clear readiness before deletion so a failed rebuild cannot use old metadata.
        c["prepared"] = {}
        write_library(data)
        for path in paths:
            path.unlink()
        return len(paths)


def vae_signature(name):
    import folder_paths
    p = folder_paths.get_full_path("vae", name)
    if not p or not Path(p).is_file():
        raise ValueError("找不到H3视频VAE，请先安装或选择有效模型。")
    stat = Path(p).stat()
    return [name, stat.st_size, stat.st_mtime_ns]


def component_signature(c, key, vae_name):
    refs = dict(components(c)).get(key)
    if not refs:
        raise ValueError("缺少清晰正脸或所选造型图片，请先上传。")
    hashes = [hashlib.sha256(image_path(r).read_bytes()).hexdigest() for r in refs]
    payload = [FORMAT, "full-reference-independent-images", c["resolution"], vae_signature(vae_name), hashes]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def prepared_component(c, key):
    p = c.get("prepared", {}).get(key, {})
    try:
        if p.get("signature") == component_signature(c, key, p.get("vae", "")) and Path(p.get("path", "")).is_file():
            return p
    except (ValueError, OSError):
        pass
    return None


def public_character(c):
    c = copy.deepcopy(c)
    c["component_status"] = {key: ("ready" if prepared_component(c, key) else "stale" if key in c.get("prepared", {}) else "empty" if not refs else "pending")
                             for key, refs in components(c)}
    c["status"] = "ready" if c["component_status"]["identity"] == "ready" else c["component_status"]["identity"]
    return c


def publish_component(cid, key, signature, prepared):
    with LOCK:
        data = read_library()
        c = next((x for x in data["characters"] if x["id"] == cid), None)
        if c is None or component_signature(c, key, prepared["vae"]) != signature:
            raise ValueError("准备期间参考图发生变化，请使用最新资料重新准备。")
        c.setdefault("prepared", {})[key] = {**prepared, "signature": signature}
        write_library(data)


def bind_shot(segment, document):
    """Compile explicit actor choices into a temporary shot; never rewrite user's text on disk."""
    if "character_selections" not in segment:
        return segment, None
    selected = segment.get("character_selections") or []
    if len(selected) > 4:
        raise ValueError("当前镜头最多选择4名人物，请拆分镜头。")
    shot = copy.deepcopy(segment)
    cast = {x["character_id"] for x in document.get("character_cast", [])}
    slots = shot.setdefault("image_slots", [])
    while len(slots) < 9:
        slots.append({"slot": len(slots) + 1})
    used_slots, used_ids, mods, lines = set(), set(), [], []
    # When an explicit wardrobe is selected, identity and clothing are already
    # provided by RefMod. Any actor Picture slot left over from an imported
    # Skills prompt or an older AVS version must be suppressed at runtime, or
    # REF2VA may reproduce the portrait as a giant background face / reference
    # board. Mapping: visible Picture slot -> character name.
    suppressed_actor_pictures = {}
    for row in selected:
        cid = row.get("character_id")
        if cid not in cast or cid in used_ids:
            raise ValueError("镜头人物重复或不在本剧演员中，请重新选择。")
        used_ids.add(cid)
        c = get_character(cid)
        has_wardrobe = bool(row.get("wardrobe_id"))

        # RefMod remains the authoritative character/wardrobe binding.
        # When a wardrobe is selected we deliberately do NOT auto-inject the
        # character face into a Picture slot. This avoids portrait/layout
        # leakage (giant face, duplicated character, reference-board framing)
        # and prevents a character Picture's clothes from competing with the
        # selected Clothing RefMod.
        for key in ["identity"] + ([row["wardrobe_id"]] if has_wardrobe else []):
            p = prepared_component(c, key)
            if not p:
                raise ValueError(f"{c['name']}的人物或造型参考尚未准备/已更新，请到人物库点击‘准备人物参考’。")
            mods.append({"name": p["mod_name"], "strength": 1.0, "tokens": p["tokens"]})

        wardrobe = next((w["name"] for w in c["wardrobes"] if w["id"] == row.get("wardrobe_id")), "as described in this shot")

        if has_wardrobe:
            # The character selection owns this Picture slot.  Older imported
            # prompts may already have placed a portrait there, so merely
            # stopping new auto-injection is not enough. Clear that actor slot
            # in the temporary runtime copy and later remove its <Picture N>
            # references from the runtime prompt. Scene/prop Pictures in all
            # other slots are untouched.
            actor_slot = int(row.get("picture_slot", 0) or 0)
            if actor_slot in range(1, 10):
                suppressed_actor_pictures[actor_slot] = c["name"]
                slots[actor_slot - 1] = {"slot": actor_slot}
            lines.append(
                f"Character identity: {c['name']} is controlled by the character Identity RefMod; "
                f"wardrobe: {wardrobe} is controlled by the selected Clothing RefMod. "
                f"Do not use or reproduce an identity portrait/reference board for this character. "
                f"Keep the shot's existing actions and spoken dialogue."
            )
        else:
            # Preserve the old behavior only when no explicit wardrobe is selected.
            slot = int(row.get("picture_slot", 0))
            if slot not in range(1, 10) or slot in used_slots:
                raise ValueError("每位人物需要独立的Picture槽位（1–9）。")
            used_slots.add(slot)
            face = c["refs"][0]
            slots[slot-1] = {"slot": slot, "token": "", "asset_id": "", "name": c["name"] + "｜脸部身份",
                            "local_path": face["path"], "local_filename": face["filename"],
                            "local_subfolder": face["subfolder"], "local_type": "input"}
            lines.append(
                f"Character identity: {c['name']} uses <Picture {slot}> for the same face and age; "
                f"wardrobe: {wardrobe}. Supplementary turnarounds are views of this same person, "
                f"not extra people or a split-screen layout. Keep the shot's existing actions and spoken dialogue."
            )
    total_refmod_tokens = sum(int(x.get("tokens", 0) or 0) for x in mods)
    if total_refmod_tokens > 32768:
        raise ValueError(
            f"本镜头人物 RefMod 总参考达到 {total_refmod_tokens} tokens，超过 32768 的镜头总预算。"
            "请减少同镜人物/造型参考后重新生成。"
        )
    if lines:
        text = str(shot.get("full_prompt", ""))

        # Runtime-only sanitisation.  Do not rewrite the user's saved Skills
        # prompt; only the temporary shot sent to H3 is changed.  This removes
        # actor Picture references that would otherwise make Director collect
        # and send the stale portrait to REF2VA.
        for picture_slot, character_name in suppressed_actor_pictures.items():
            replacement = f"the Identity RefMod for {character_name}"
            text = re.sub(
                rf"<Picture\s+{picture_slot}>", replacement, text, flags=re.I
            )
            # Remove the corresponding human-readable Picture binding entry.
            text = re.sub(
                rf"(?i)\bP{picture_slot}\s*=\s*[^；;\n]+[；;]?", "", text
            )
            # Remove a stale reference_map line such as 'Picture 1: ...'.
            text = re.sub(
                rf"(?mi)^\s*Picture\s+{picture_slot}\s*:.*(?:\n|$)", "", text
            )

        match = re.search(r"(?m)^subject_definitions\s*:\s*\n", text)
        if match:
            shot["full_prompt"] = text[:match.end()] + "\n".join(lines) + "\n" + text[match.end():]
        else:
            raise ValueError("人物库用于H3多素材参考，请使用含subject_definitions的REF2VA提示词。")
    return shot, mods
