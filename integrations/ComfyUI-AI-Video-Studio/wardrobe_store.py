"""Portable global wardrobe library.

The wardrobe library is intentionally independent from character records.  Its
metadata and source images live *inside the selected library folder*, so the
folder can be placed on OneDrive/Dropbox/NAS/a removable disk and reused by a
second ComfyUI installation.  Character binding materializes a local input
cache, keeping the existing RefMod preparation pipeline unchanged.
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import threading
import uuid
from pathlib import Path

import folder_paths

LOCK = threading.RLock()
FORMAT = 1
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
STATE_DIR = Path(folder_paths.get_user_directory()) / "ai_video_studio"
LOCAL_CONFIG = STATE_DIR / "global_wardrobe_config.json"
MAIN_CONFIG = STATE_DIR / "config.json"
META_DIR = ".avs_wardrobes"
META_FILE = "library.json"
ASSET_DIR = "assets"


def _read_json(path: Path, fallback):
    try:
        data = json.loads(path.read_text("utf-8"))
        return data
    except Exception:
        return copy.deepcopy(fallback)


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _valid_dir(value: str) -> Path | None:
    value = str(value or "").strip().strip('"')
    if not value:
        return None
    try:
        p = Path(value).expanduser().resolve()
    except Exception:
        return None
    return p if p.is_dir() else None


def _local_config() -> dict:
    return _read_json(LOCAL_CONFIG, {"root": ""}) if LOCAL_CONFIG.exists() else {"root": ""}


def _main_library_path() -> Path | None:
    if not MAIN_CONFIG.exists():
        return None
    data = _read_json(MAIN_CONFIG, {})
    root = _valid_dir(data.get("library_path", ""))
    return root


def configured_root() -> tuple[Path, str]:
    """Return root and source label.

    Priority: env -> explicitly selected root -> permanent resource library ->
    local input fallback.  Only the first three are intended for portable use.
    """
    env = _valid_dir(os.environ.get("AVS_GLOBAL_WARDROBE_LIBRARY", ""))
    if env:
        return env, "environment"
    local = _valid_dir(_local_config().get("root", ""))
    if local:
        return local, "configured"
    permanent = _main_library_path()
    if permanent:
        root = permanent / "AVS_Global_Wardrobes"
        root.mkdir(parents=True, exist_ok=True)
        return root.resolve(), "permanent_library"
    root = Path(folder_paths.get_input_directory()).resolve() / "AI_Video_Studio" / "GlobalWardrobes"
    root.mkdir(parents=True, exist_ok=True)
    return root, "local_fallback"


def set_root(value: str) -> Path:
    raw = str(value or "").strip().strip('"')
    if not raw:
        raise ValueError("全局造型库目录不能为空。")
    p = Path(raw).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    if not p.is_dir():
        raise ValueError("全局造型库路径不是文件夹。")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(LOCAL_CONFIG, {"root": str(p)})
    _ensure_library(p)
    return p


def use_permanent_library() -> Path:
    permanent = _main_library_path()
    if not permanent:
        raise ValueError("还没有设置永久资源库目录，请先在【永久资源库】节点选择目录。")
    return set_root(str(permanent / "AVS_Global_Wardrobes"))


def _meta_path(root: Path | None = None) -> Path:
    root = root or configured_root()[0]
    return root / META_DIR / META_FILE


def _asset_root(root: Path | None = None) -> Path:
    root = root or configured_root()[0]
    return root / META_DIR / ASSET_DIR


def _ensure_library(root: Path | None = None):
    root = root or configured_root()[0]
    (root / META_DIR).mkdir(parents=True, exist_ok=True)
    _asset_root(root).mkdir(parents=True, exist_ok=True)
    p = _meta_path(root)
    if not p.exists():
        _write_json(p, {"version": FORMAT, "wardrobes": []})


def read_library() -> dict:
    root, _ = configured_root()
    _ensure_library(root)
    data = _read_json(_meta_path(root), {"version": FORMAT, "wardrobes": []})
    if not isinstance(data, dict) or not isinstance(data.get("wardrobes"), list):
        raise ValueError("全局造型库索引损坏，请备份目录后检查 .avs_wardrobes/library.json。")
    return data


def write_library(data: dict):
    root, _ = configured_root()
    _ensure_library(root)
    _write_json(_meta_path(root), data)


def _input_image(ref: dict) -> Path:
    root = Path(folder_paths.get_input_directory()).resolve()
    p = Path(str((ref or {}).get("path", ""))).resolve()
    if not p.is_file() or not p.is_relative_to(root):
        raise ValueError("保存到全局造型库的图片必须来自当前 ComfyUI input。")
    if p.suffix.lower() not in IMAGE_EXTS:
        raise ValueError("全局造型库只支持静态图片。")
    return p


def _public_record(record: dict) -> dict:
    return {
        "id": record["id"],
        "name": record.get("name", "未命名造型"),
        "revision": int(record.get("revision", 1)),
        "ref_count": len(record.get("refs", [])),
        "refs": copy.deepcopy(record.get("refs", [])),
    }


def list_wardrobes() -> list[dict]:
    with LOCK:
        return [_public_record(x) for x in read_library()["wardrobes"]]


def get_wardrobe(wardrobe_id: str) -> dict:
    with LOCK:
        record = next((x for x in read_library()["wardrobes"] if x.get("id") == wardrobe_id), None)
        if not record:
            raise ValueError("全局造型不存在或已被删除。")
        return copy.deepcopy(record)


def _record_image_path(record: dict, index: int) -> Path:
    refs = record.get("refs", [])
    if index < 0 or index >= len(refs):
        raise ValueError("造型图片序号无效。")
    root, _ = configured_root()
    rel = str(refs[index].get("relative_path", "")).replace("\\", "/")
    if not rel or rel.startswith("/") or ".." in Path(rel).parts:
        raise ValueError("全局造型图片路径无效。")
    p = (root / rel).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file() or p.suffix.lower() not in IMAGE_EXTS:
        raise ValueError("全局造型图片不存在。")
    return p


def image_path(wardrobe_id: str, index: int) -> Path:
    return _record_image_path(get_wardrobe(wardrobe_id), index)


def save_wardrobe(raw: dict) -> dict:
    refs = raw.get("refs", [])
    if not isinstance(refs, list) or not refs or len(refs) > 4:
        raise ValueError("全局造型需要1–4张参考图。")
    name = str(raw.get("name") or "").strip()[:80]
    if not name:
        raise ValueError("请填写造型名称。")
    with LOCK:
        data = read_library()
        wid = str(raw.get("id") or uuid.uuid4().hex)
        if not re.fullmatch(r"[a-f0-9]{32}", wid):
            raise ValueError("全局造型ID无效。")
        old = next((x for x in data["wardrobes"] if x.get("id") == wid), None)
        root, _ = configured_root()
        target_dir = _asset_root(root) / wid
        tmp_dir = _asset_root(root) / (wid + "." + uuid.uuid4().hex + ".tmp")
        tmp_dir.mkdir(parents=True, exist_ok=False)
        new_refs = []
        try:
            for i, ref in enumerate(refs, start=1):
                src = _input_image(ref)
                ext = src.suffix.lower() if src.suffix.lower() in IMAGE_EXTS else ".png"
                filename = f"ref_{i}{ext}"
                dst = tmp_dir / filename
                shutil.copy2(src, dst)
                rel = dst.relative_to(root).as_posix()
                # rel changes when temp directory is renamed; store final relative path.
                final_rel = (_asset_root(root) / wid / filename).relative_to(root).as_posix()
                new_refs.append({"relative_path": final_rel, "name": str(ref.get("name") or src.name)[:160], "filename": filename})
            if target_dir.exists():
                shutil.rmtree(target_dir)
            os.replace(tmp_dir, target_dir)
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
        record = {"id": wid, "name": name, "revision": int((old or {}).get("revision", 0)) + 1, "refs": new_refs}
        data["wardrobes"] = [x for x in data["wardrobes"] if x.get("id") != wid] + [record]
        write_library(data)
        return _public_record(record)


def delete_wardrobe(wardrobe_id: str):
    with LOCK:
        data = read_library()
        record = next((x for x in data["wardrobes"] if x.get("id") == wardrobe_id), None)
        if not record:
            return False
        data["wardrobes"] = [x for x in data["wardrobes"] if x.get("id") != wardrobe_id]
        write_library(data)
        root, _ = configured_root()
        shutil.rmtree(_asset_root(root) / wardrobe_id, ignore_errors=True)
        return True


def materialize(wardrobe_id: str) -> dict:
    """Copy the portable wardrobe into ComfyUI input and return normal AVS refs."""
    record = get_wardrobe(wardrobe_id)
    input_root = Path(folder_paths.get_input_directory()).resolve()
    target_dir = input_root / "AI_Video_Studio" / "global_wardrobe_cache" / wardrobe_id / f"r{int(record.get('revision', 1))}"
    target_dir.mkdir(parents=True, exist_ok=True)
    refs = []
    for index, meta in enumerate(record.get("refs", [])):
        src = _record_image_path(record, index)
        ext = src.suffix.lower()
        dst = target_dir / f"ref_{index + 1}{ext}"
        if not dst.exists() or dst.stat().st_size != src.stat().st_size or dst.stat().st_mtime_ns < src.stat().st_mtime_ns:
            shutil.copy2(src, dst)
        refs.append({
            "path": str(dst.resolve()),
            "name": str(meta.get("name") or dst.name)[:160],
            "filename": dst.name,
            "subfolder": str(dst.parent.relative_to(input_root)).replace("\\", "/"),
            "type": "input",
        })
    return {"wardrobe": _public_record(record), "refs": refs}


def status() -> dict:
    root, source = configured_root()
    _ensure_library(root)
    portable = source in {"environment", "configured", "permanent_library"}
    return {
        "root": str(root),
        "source": source,
        "portable": portable,
        "count": len(read_library()["wardrobes"]),
    }
