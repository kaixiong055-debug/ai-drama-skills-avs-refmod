from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import mimetypes
import os
import re
import shutil
import sqlite3
import subprocess
import time
import string
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import torch

from aiohttp import web
from PIL import Image, ImageOps

import folder_paths
from server import PromptServer
from .library_folders import compatible_path, browser_directory, native_picker_available, pick_windows_directory, import_target

log = logging.getLogger("AI Video Studio")

PLUGIN_DIR = Path(__file__).resolve().parent
STATE_DIR = Path(folder_paths.get_user_directory()) / "ai_video_studio"
THUMB_DIR = STATE_DIR / "thumbnails"
CONFIG_FILE = STATE_DIR / "config.json"
DB_FILE = STATE_DIR / "resource_library.sqlite3"

IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"
}
VIDEO_EXTS = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mpg", ".mpeg", ".ts", ".mts"
}
AUDIO_EXTS = {
    ".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma"
}

AUTO_CATEGORY_HINTS = {
    "角色": {"characters", "character", "roles", "role", "人物", "角色"},
    "场景": {"scenes", "scene", "backgrounds", "background", "场景", "背景"},
    "道具": {"props", "prop", "weapons", "weapon", "items", "item", "道具", "武器"},
    "动作": {"motion", "motions", "actions", "action", "dance", "combat", "动作", "舞蹈", "打斗"},
    "声音": {"voice", "voices", "speech", "配音", "声音", "音色"},
}


def _ensure_state() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)


def _read_config() -> dict[str, Any]:
    _ensure_state()
    if not CONFIG_FILE.exists():
        return {"library_path": "", "language": "zh-CN"}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
        data.setdefault("library_path", "")
        data.setdefault("language", "zh-CN")
        if data["library_path"] and not compatible_path(data["library_path"]):
            data["library_path"] = ""
        return data
    except Exception:
        return {"library_path": "", "language": "zh-CN"}


def _write_config(data: dict[str, Any]) -> None:
    _ensure_state()
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_FILE)


def _normalise_path(value: str) -> str:
    value = (value or "").strip().strip('"')
    if not value:
        return ""
    if not compatible_path(value):
        raise ValueError("该目录属于另一台电脑，请重新选择资源库目录；云端可导入电脑文件夹或选择服务器目录。")
    return str(Path(value).expanduser().resolve())


def _media_type(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    return None


def _asset_id(path: str) -> str:
    key = os.path.normcase(os.path.abspath(path)).encode("utf-8", errors="ignore")
    return hashlib.sha1(key).hexdigest()


def _auto_category(rel_path: str, media_type: str) -> str:
    parts = [p.lower() for p in Path(rel_path).parts[:-1]]
    for category, hints in AUTO_CATEGORY_HINTS.items():
        if any(part in hints for part in parts):
            return category
    if media_type == "audio":
        return "声音"
    return "未分类"


def _ffprobe_metadata(path: Path) -> tuple[int | None, int | None, float | None]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None, None, None
    try:
        proc = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "stream=width,height:format=duration",
                "-of", "json",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
        )
        if proc.returncode != 0:
            return None, None, None
        data = json.loads(proc.stdout or "{}")
        width = height = None
        for stream in data.get("streams", []):
            if stream.get("width") and stream.get("height"):
                width = int(stream["width"])
                height = int(stream["height"])
                break
        duration = None
        try:
            duration = float(data.get("format", {}).get("duration"))
        except Exception:
            duration = None
        return width, height, duration
    except Exception:
        return None, None, None


def _image_metadata(path: Path) -> tuple[int | None, int | None]:
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            return int(img.width), int(img.height)
    except Exception:
        return None, None


def _make_image_thumb(path: Path, thumb_path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((360, 240))
            canvas = Image.new("RGB", (360, 240), (26, 26, 30))
            x = (360 - img.width) // 2
            y = (240 - img.height) // 2
            canvas.paste(img, (x, y))
            canvas.save(thumb_path, "JPEG", quality=82, optimize=True)
        return True
    except Exception:
        return False


def _make_video_thumb(path: Path, thumb_path: Path) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    try:
        proc = subprocess.run(
            [
                ffmpeg,
                "-hide_banner", "-loglevel", "error",
                "-ss", "0.5",
                "-i", str(path),
                "-frames:v", "1",
                "-vf", "scale=360:240:force_original_aspect_ratio=decrease,pad=360:240:(ow-iw)/2:(oh-ih)/2:color=0x1a1a1e",
                "-q:v", "4",
                "-y",
                str(thumb_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        return proc.returncode == 0 and thumb_path.exists()
    except Exception:
        return False


class ResourceLibraryManager:
    def __init__(self) -> None:
        _ensure_state()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    root TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    relative_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '未分类',
                    alias TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    mtime REAL NOT NULL DEFAULT 0,
                    width INTEGER,
                    height INTEGER,
                    duration REAL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_root ON assets(root)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(media_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_active ON assets(active)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS asset_groups (
                    id TEXT PRIMARY KEY,
                    root TEXT NOT NULL,
                    name TEXT NOT NULL,
                    alias TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '角色',
                    description TEXT NOT NULL DEFAULT '',
                    cover_asset_id TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS asset_group_members (
                    group_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (group_id, asset_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_asset_groups_root ON asset_groups(root)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_asset_groups_category ON asset_groups(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_group_members_asset ON asset_group_members(asset_id)")

    def get_config(self) -> dict[str, Any]:
        return _read_config()

    def set_library_path(self, path: str) -> str:
        normalized = _normalise_path(path)
        if not normalized:
            raise ValueError("资源库地址不能为空。")
        p = Path(normalized)
        if not p.exists():
            raise ValueError(f"目录不存在：{normalized}")
        if not p.is_dir():
            raise ValueError(f"不是目录：{normalized}")
        cfg = self.get_config()
        cfg["library_path"] = normalized
        _write_config(cfg)
        return normalized

    def scan(self, path: str | None = None) -> dict[str, Any]:
        if path:
            root = self.set_library_path(path)
        else:
            root = _normalise_path(self.get_config().get("library_path", ""))
        if not root:
            raise ValueError("请先设置永久资源库地址。")
        root_path = Path(root)
        if not root_path.exists() or not root_path.is_dir():
            raise ValueError(f"资源库目录不存在：{root}")

        started = time.time()
        scanned = 0
        added = 0
        updated = 0
        skipped = 0
        errors = 0
        now = time.time()

        with self._connect() as conn:
            conn.execute("UPDATE assets SET active=0 WHERE root=?", (root,))

            for dirpath, dirnames, filenames in os.walk(root):
                # 跳过常见无关目录与隐藏缓存目录
                dirnames[:] = [
                    d for d in dirnames
                    if d not in {".git", "node_modules", "__pycache__", ".h3_director", ".avs"}
                ]
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    media_type = _media_type(file_path)
                    if not media_type:
                        skipped += 1
                        continue
                    try:
                        stat = file_path.stat()
                        abs_path = str(file_path.resolve())
                        rel_path = str(file_path.resolve().relative_to(root_path.resolve()))
                        aid = _asset_id(abs_path)
                        row = conn.execute(
                            "SELECT mtime,size_bytes,display_name,category,alias,tags FROM assets WHERE id=?",
                            (aid,),
                        ).fetchone()

                        width = height = None
                        duration = None
                        if media_type == "image":
                            width, height = _image_metadata(file_path)
                        else:
                            width, height, duration = _ffprobe_metadata(file_path)

                        category = row["category"] if row else _auto_category(rel_path, media_type)
                        display_name = row["display_name"] if row else file_path.stem
                        alias = row["alias"] if row else ""
                        tags = row["tags"] if row else "[]"

                        conn.execute(
                            """
                            INSERT INTO assets (
                                id,root,path,relative_path,file_name,display_name,extension,media_type,
                                category,alias,tags,size_bytes,mtime,width,height,duration,active,created_at,updated_at
                            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)
                            ON CONFLICT(id) DO UPDATE SET
                                root=excluded.root,
                                path=excluded.path,
                                relative_path=excluded.relative_path,
                                file_name=excluded.file_name,
                                extension=excluded.extension,
                                media_type=excluded.media_type,
                                size_bytes=excluded.size_bytes,
                                mtime=excluded.mtime,
                                width=excluded.width,
                                height=excluded.height,
                                duration=excluded.duration,
                                active=1,
                                updated_at=excluded.updated_at
                            """,
                            (
                                aid, root, abs_path, rel_path, file_path.name, display_name,
                                file_path.suffix.lower(), media_type, category, alias, tags,
                                int(stat.st_size), float(stat.st_mtime), width, height, duration,
                                now, now,
                            ),
                        )
                        scanned += 1
                        if row is None:
                            added += 1
                        elif float(row["mtime"]) != float(stat.st_mtime) or int(row["size_bytes"]) != int(stat.st_size):
                            updated += 1

                        if media_type in {"image", "video"}:
                            thumb_path = THUMB_DIR / f"{aid}.jpg"
                            if (not thumb_path.exists()) or thumb_path.stat().st_mtime < stat.st_mtime:
                                if media_type == "image":
                                    _make_image_thumb(file_path, thumb_path)
                                else:
                                    _make_video_thumb(file_path, thumb_path)
                    except Exception as exc:
                        errors += 1
                        log.warning("扫描资源失败 %s: %s", file_path, exc)
            conn.commit()

        return {
            "ok": True,
            "library_path": root,
            "scanned": scanned,
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "seconds": round(time.time() - started, 2),
            "stats": self.stats(root),
        }

    def stats(self, root: str | None = None) -> dict[str, Any]:
        root = _normalise_path(root or self.get_config().get("library_path", ""))
        where = "active=1"
        params: list[Any] = []
        if root:
            where += " AND root=?"
            params.append(root)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT media_type,COUNT(*) AS n FROM assets WHERE {where} GROUP BY media_type",
                params,
            ).fetchall()
            counts = {"image": 0, "video": 0, "audio": 0}
            for row in rows:
                counts[row["media_type"]] = int(row["n"])
            categories = [
                row[0] for row in conn.execute(
                    f"SELECT DISTINCT category FROM assets WHERE {where} AND category<>'' ORDER BY category",
                    params,
                ).fetchall()
            ]
        return {
            "library_path": root,
            "image": counts["image"],
            "video": counts["video"],
            "audio": counts["audio"],
            "total": sum(counts.values()),
            "categories": categories,
        }

    def query(
        self,
        query: str = "",
        media_type: str = "all",
        category: str = "",
        limit: int = 100,
        offset: int = 0,
        root: str | None = None,
    ) -> list[dict[str, Any]]:
        root = _normalise_path(root or self.get_config().get("library_path", ""))
        clauses = ["active=1"]
        params: list[Any] = []
        if root:
            clauses.append("root=?")
            params.append(root)
        if media_type and media_type != "all":
            clauses.append("media_type=?")
            params.append(media_type)
        if category:
            clauses.append("category=?")
            params.append(category)
        q = (query or "").strip()
        if q:
            like = f"%{q}%"
            clauses.append(
                "(display_name LIKE ? OR file_name LIKE ? OR relative_path LIKE ? OR alias LIKE ? OR tags LIKE ?)"
            )
            params.extend([like, like, like, like, like])
        limit = max(1, min(int(limit), 1000))
        offset = max(0, int(offset))
        sql = f"""
            SELECT * FROM assets
            WHERE {' AND '.join(clauses)}
            ORDER BY updated_at DESC, display_name COLLATE NOCASE ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_asset(row) for row in rows]

    def query_count(
        self,
        query: str = "",
        media_type: str = "all",
        category: str = "",
        root: str | None = None,
    ) -> int:
        root = _normalise_path(root or self.get_config().get("library_path", ""))
        clauses = ["active=1"]
        params: list[Any] = []
        if root:
            clauses.append("root=?")
            params.append(root)
        if media_type and media_type != "all":
            clauses.append("media_type=?")
            params.append(media_type)
        if category:
            clauses.append("category=?")
            params.append(category)
        q = (query or "").strip()
        if q:
            like = f"%{q}%"
            clauses.append(
                "(display_name LIKE ? OR file_name LIKE ? OR relative_path LIKE ? OR alias LIKE ? OR tags LIKE ?)"
            )
            params.extend([like, like, like, like, like])
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) FROM assets WHERE {' AND '.join(clauses)}",
                params,
            ).fetchone()
        return int(row[0] if row else 0)

    def bulk_update_meta(self, asset_ids: list[str], payload: dict[str, Any]) -> int:
        ids = [str(x).strip() for x in asset_ids if str(x).strip()]
        if not ids:
            return 0
        category = str(payload.get("category", "")).strip()
        append_tags_value = payload.get("append_tags", [])
        if isinstance(append_tags_value, str):
            append_tags = [x.strip() for x in append_tags_value.replace("，", ",").split(",") if x.strip()]
        elif isinstance(append_tags_value, list):
            append_tags = [str(x).strip() for x in append_tags_value if str(x).strip()]
        else:
            append_tags = []
        now = time.time()
        changed = 0
        with self._connect() as conn:
            for asset_id in ids:
                row = conn.execute("SELECT category,tags FROM assets WHERE id=?", (asset_id,)).fetchone()
                if not row:
                    continue
                next_category = category or row["category"] or "未分类"
                try:
                    tags = json.loads(row["tags"] or "[]")
                except Exception:
                    tags = []
                for tag in append_tags:
                    if tag not in tags:
                        tags.append(tag)
                conn.execute(
                    "UPDATE assets SET category=?,tags=?,updated_at=? WHERE id=?",
                    (next_category, json.dumps(tags, ensure_ascii=False), now, asset_id),
                )
                changed += 1
            conn.commit()
        return changed

    def _current_root(self, root: str | None = None) -> str:
        return _normalise_path(root or self.get_config().get("library_path", ""))

    def list_groups(self, category: str = "", root: str | None = None) -> list[dict[str, Any]]:
        root = self._current_root(root)
        clauses = ["g.root=?"] if root else ["1=1"]
        params: list[Any] = [root] if root else []
        if category:
            clauses.append("g.category=?")
            params.append(category)
        sql = f"""
            SELECT g.*,
                   COUNT(CASE WHEN a.active=1 THEN 1 END) AS member_count,
                   COALESCE(NULLIF(g.cover_asset_id,''), MIN(CASE WHEN a.active=1 THEN a.id END)) AS effective_cover_id
            FROM asset_groups g
            LEFT JOIN asset_group_members gm ON gm.group_id=g.id
            LEFT JOIN assets a ON a.id=gm.asset_id
            WHERE {' AND '.join(clauses)}
            GROUP BY g.id
            ORDER BY g.category COLLATE NOCASE ASC, g.updated_at DESC, g.name COLLATE NOCASE ASC
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_group(row) for row in rows]

    def get_group(self, group_id: str) -> dict[str, Any] | None:
        root = self._current_root()
        clauses = ["g.id=?"]
        params: list[Any] = [group_id]
        if root:
            clauses.append("g.root=?")
            params.append(root)
        sql = f"""
            SELECT g.*,
                   COUNT(CASE WHEN a.active=1 THEN 1 END) AS member_count,
                   COALESCE(NULLIF(g.cover_asset_id,''), MIN(CASE WHEN a.active=1 THEN a.id END)) AS effective_cover_id
            FROM asset_groups g
            LEFT JOIN asset_group_members gm ON gm.group_id=g.id
            LEFT JOIN assets a ON a.id=gm.asset_id
            WHERE {' AND '.join(clauses)}
            GROUP BY g.id
        """
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return self._row_to_group(row) if row else None

    def create_group(self, payload: dict[str, Any]) -> dict[str, Any]:
        root = self._current_root()
        if not root:
            raise ValueError("请先设置永久资源库地址。")
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("资源组名称不能为空。")
        alias = str(payload.get("alias", "")).strip().lstrip("@")
        category = str(payload.get("category", "角色")).strip() or "角色"
        description = str(payload.get("description", "")).strip()
        now = time.time()
        group_id = uuid.uuid4().hex
        with self._connect() as conn:
            if alias:
                exists = conn.execute(
                    "SELECT id FROM asset_groups WHERE root=? AND lower(alias)=lower(?)",
                    (root, alias),
                ).fetchone()
                if exists:
                    raise ValueError(f"@别名已被其他资源组使用：@{alias}")
            conn.execute(
                "INSERT INTO asset_groups(id,root,name,alias,category,description,cover_asset_id,created_at,updated_at) VALUES(?,?,?,?,?,?, '',?,?)",
                (group_id, root, name, alias, category, description, now, now),
            )
            conn.commit()
        return self.get_group(group_id)  # type: ignore[return-value]

    def update_group(self, group_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_group(group_id)
        if not existing:
            raise ValueError("资源组不存在。")
        name = str(payload.get("name", existing["name"])).strip() or existing["name"]
        alias = str(payload.get("alias", existing.get("alias", ""))).strip().lstrip("@")
        category = str(payload.get("category", existing.get("category", "角色"))).strip() or "角色"
        description = str(payload.get("description", existing.get("description", ""))).strip()
        cover_asset_id = str(payload.get("cover_asset_id", existing.get("cover_asset_id", ""))).strip()
        root = existing["root"]
        with self._connect() as conn:
            if alias:
                clash = conn.execute(
                    "SELECT id FROM asset_groups WHERE root=? AND lower(alias)=lower(?) AND id<>?",
                    (root, alias, group_id),
                ).fetchone()
                if clash:
                    raise ValueError(f"@别名已被其他资源组使用：@{alias}")
            conn.execute(
                "UPDATE asset_groups SET name=?,alias=?,category=?,description=?,cover_asset_id=?,updated_at=? WHERE id=?",
                (name, alias, category, description, cover_asset_id, time.time(), group_id),
            )
            conn.commit()
        return self.get_group(group_id)  # type: ignore[return-value]

    def delete_group(self, group_id: str) -> bool:
        existing = self.get_group(group_id)
        if not existing:
            return False
        with self._connect() as conn:
            conn.execute("DELETE FROM asset_group_members WHERE group_id=?", (group_id,))
            conn.execute("DELETE FROM asset_groups WHERE id=?", (group_id,))
            conn.commit()
        return True

    def add_assets_to_group(self, group_id: str, asset_ids: list[str]) -> int:
        group = self.get_group(group_id)
        if not group:
            raise ValueError("资源组不存在。")
        ids = [str(x).strip() for x in asset_ids if str(x).strip()]
        if not ids:
            return 0
        now = time.time()
        changed = 0
        with self._connect() as conn:
            order_row = conn.execute(
                "SELECT COALESCE(MAX(sort_order),-1) FROM asset_group_members WHERE group_id=?",
                (group_id,),
            ).fetchone()
            order = int(order_row[0] if order_row else -1) + 1
            for aid in ids:
                asset = conn.execute("SELECT id,root,active FROM assets WHERE id=?", (aid,)).fetchone()
                if not asset or int(asset["active"]) != 1 or asset["root"] != group["root"]:
                    continue
                cur = conn.execute(
                    "INSERT OR IGNORE INTO asset_group_members(group_id,asset_id,sort_order,created_at) VALUES(?,?,?,?)",
                    (group_id, aid, order, now),
                )
                if cur.rowcount:
                    changed += 1
                    order += 1
            if changed and not group.get("cover_asset_id"):
                first = conn.execute(
                    "SELECT asset_id FROM asset_group_members WHERE group_id=? ORDER BY sort_order ASC, created_at ASC LIMIT 1",
                    (group_id,),
                ).fetchone()
                if first:
                    conn.execute(
                        "UPDATE asset_groups SET cover_asset_id=?,updated_at=? WHERE id=?",
                        (first[0], now, group_id),
                    )
            if changed:
                conn.execute("UPDATE asset_groups SET updated_at=? WHERE id=?", (now, group_id))
            conn.commit()
        return changed

    def remove_assets_from_group(self, group_id: str, asset_ids: list[str]) -> int:
        ids = [str(x).strip() for x in asset_ids if str(x).strip()]
        if not ids:
            return 0
        changed = 0
        with self._connect() as conn:
            for aid in ids:
                cur = conn.execute(
                    "DELETE FROM asset_group_members WHERE group_id=? AND asset_id=?",
                    (group_id, aid),
                )
                changed += max(0, int(cur.rowcount or 0))
            conn.execute("UPDATE asset_groups SET updated_at=? WHERE id=?", (time.time(), group_id))
            conn.commit()
        return changed

    def query_group_assets(
        self,
        group_id: str,
        query: str = "",
        media_type: str = "all",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = ["gm.group_id=?", "a.active=1"]
        params: list[Any] = [group_id]
        if media_type and media_type != "all":
            clauses.append("a.media_type=?")
            params.append(media_type)
        q = (query or "").strip()
        if q:
            like = f"%{q}%"
            clauses.append("(a.display_name LIKE ? OR a.file_name LIKE ? OR a.relative_path LIKE ? OR a.alias LIKE ? OR a.tags LIKE ?)")
            params.extend([like, like, like, like, like])
        limit = max(1, min(int(limit), 1000))
        offset = max(0, int(offset))
        sql = f"""
            SELECT a.* FROM asset_group_members gm
            JOIN assets a ON a.id=gm.asset_id
            WHERE {' AND '.join(clauses)}
            ORDER BY gm.sort_order ASC, a.display_name COLLATE NOCASE ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_asset(row) for row in rows]

    def query_group_assets_count(self, group_id: str, query: str = "", media_type: str = "all") -> int:
        clauses = ["gm.group_id=?", "a.active=1"]
        params: list[Any] = [group_id]
        if media_type and media_type != "all":
            clauses.append("a.media_type=?")
            params.append(media_type)
        q = (query or "").strip()
        if q:
            like = f"%{q}%"
            clauses.append("(a.display_name LIKE ? OR a.file_name LIKE ? OR a.relative_path LIKE ? OR a.alias LIKE ? OR a.tags LIKE ?)")
            params.extend([like, like, like, like, like])
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) FROM asset_group_members gm JOIN assets a ON a.id=gm.asset_id WHERE {' AND '.join(clauses)}",
                params,
            ).fetchone()
        return int(row[0] if row else 0)

    def query_unassigned(
        self,
        query: str = "",
        media_type: str = "all",
        limit: int = 100,
        offset: int = 0,
        root: str | None = None,
    ) -> list[dict[str, Any]]:
        root = self._current_root(root)
        clauses = ["a.active=1", "NOT EXISTS(SELECT 1 FROM asset_group_members gm WHERE gm.asset_id=a.id)"]
        params: list[Any] = []
        if root:
            clauses.append("a.root=?")
            params.append(root)
        if media_type and media_type != "all":
            clauses.append("a.media_type=?")
            params.append(media_type)
        q = (query or "").strip()
        if q:
            like = f"%{q}%"
            clauses.append("(a.display_name LIKE ? OR a.file_name LIKE ? OR a.relative_path LIKE ? OR a.alias LIKE ? OR a.tags LIKE ?)")
            params.extend([like, like, like, like, like])
        limit = max(1, min(int(limit), 1000))
        offset = max(0, int(offset))
        sql = f"SELECT a.* FROM assets a WHERE {' AND '.join(clauses)} ORDER BY a.updated_at DESC, a.display_name COLLATE NOCASE ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_asset(row) for row in rows]

    def query_unassigned_count(self, query: str = "", media_type: str = "all", root: str | None = None) -> int:
        root = self._current_root(root)
        clauses = ["a.active=1", "NOT EXISTS(SELECT 1 FROM asset_group_members gm WHERE gm.asset_id=a.id)"]
        params: list[Any] = []
        if root:
            clauses.append("a.root=?")
            params.append(root)
        if media_type and media_type != "all":
            clauses.append("a.media_type=?")
            params.append(media_type)
        q = (query or "").strip()
        if q:
            like = f"%{q}%"
            clauses.append("(a.display_name LIKE ? OR a.file_name LIKE ? OR a.relative_path LIKE ? OR a.alias LIKE ? OR a.tags LIKE ?)")
            params.extend([like, like, like, like, like])
        with self._connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM assets a WHERE {' AND '.join(clauses)}", params).fetchone()
        return int(row[0] if row else 0)

    def group_stats(self, root: str | None = None) -> dict[str, Any]:
        root = self._current_root(root)
        params: list[Any] = []
        where = "1=1"
        if root:
            where = "g.root=?"
            params.append(root)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT g.category,COUNT(*) FROM asset_groups g WHERE {where} GROUP BY g.category",
                params,
            ).fetchall()
            by_category = {str(r[0]): int(r[1]) for r in rows}
        return {
            "groups": sum(by_category.values()),
            "by_category": by_category,
            "unassigned": self.query_unassigned_count(root=root),
        }

    def _row_to_group(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "root": row["root"],
            "name": row["name"],
            "alias": row["alias"],
            "category": row["category"],
            "description": row["description"],
            "cover_asset_id": row["cover_asset_id"],
            "effective_cover_id": row["effective_cover_id"] if "effective_cover_id" in row.keys() else row["cover_asset_id"],
            "member_count": int(row["member_count"] if "member_count" in row.keys() else 0),
            "updated_at": float(row["updated_at"] or 0),
        }

    def get_asset(self, asset_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
        return self._row_to_asset(row) if row else None

    def update_meta(self, asset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        allowed_categories = str(payload.get("category", "")).strip() or "未分类"
        display_name = str(payload.get("display_name", "")).strip()
        alias = str(payload.get("alias", "")).strip().lstrip("@")
        tags_value = payload.get("tags", [])
        if isinstance(tags_value, str):
            tags = [x.strip() for x in tags_value.replace("，", ",").split(",") if x.strip()]
        elif isinstance(tags_value, list):
            tags = [str(x).strip() for x in tags_value if str(x).strip()]
        else:
            tags = []
        existing = self.get_asset(asset_id)
        if not existing:
            raise ValueError("素材不存在或已经被移除。")
        if not display_name:
            display_name = existing["display_name"]
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "UPDATE assets SET display_name=?,category=?,alias=?,tags=?,updated_at=? WHERE id=?",
                (display_name, allowed_categories, alias, json.dumps(tags, ensure_ascii=False), now, asset_id),
            )
            conn.commit()
        return self.get_asset(asset_id)  # type: ignore[return-value]

    def _row_to_asset(self, row: sqlite3.Row) -> dict[str, Any]:
        try:
            tags = json.loads(row["tags"] or "[]")
        except Exception:
            tags = []
        thumb = THUMB_DIR / f"{row['id']}.jpg"
        return {
            "id": row["id"],
            "path": row["path"],
            "relative_path": row["relative_path"],
            "file_name": row["file_name"],
            "display_name": row["display_name"],
            "extension": row["extension"],
            "media_type": row["media_type"],
            "category": row["category"],
            "alias": row["alias"],
            "tags": tags,
            "size_bytes": int(row["size_bytes"] or 0),
            "mtime": float(row["mtime"] or 0),
            "width": row["width"],
            "height": row["height"],
            "duration": row["duration"],
            "has_thumbnail": thumb.exists(),
        }


REFERENCE_SIMPLE_RE = re.compile(r"@([A-Za-z0-9_./\-\u3400-\u9fff]+)")
REFERENCE_BRACED_RE = re.compile(r"@\{([^{}]+)\}")

CATEGORY_ICONS = {
    "角色": "👤",
    "场景": "🏞️",
    "道具": "🧰",
    "动作": "🎬",
    "声音": "🔊",
}


def _normalize_ref_name(value: str) -> str:
    return (value or "").strip().lstrip("@").strip().casefold()


def _extract_reference_tokens(prompt: str) -> list[dict[str, str]]:
    """Return @ references in first-appearance order.

    Supports both @alias and @{alias with spaces}. Duplicate references are
    collapsed while preserving the first textual token for display.
    """
    text = prompt or ""
    matches: list[tuple[int, int, str, str]] = []
    occupied: list[tuple[int, int]] = []
    for m in REFERENCE_BRACED_RE.finditer(text):
        matches.append((m.start(), m.end(), m.group(1).strip(), m.group(0)))
        occupied.append((m.start(), m.end()))
    for m in REFERENCE_SIMPLE_RE.finditer(text):
        if any(a <= m.start() < b for a, b in occupied):
            continue
        matches.append((m.start(), m.end(), m.group(1).strip(), m.group(0)))
    matches.sort(key=lambda x: x[0])
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for _start, _end, value, raw in matches:
        key = _normalize_ref_name(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append({"raw": raw, "value": value, "key": key})
    return result


def _reference_group_map(groups: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for group in groups:
        for candidate in (group.get("alias", ""), group.get("name", "")):
            key = _normalize_ref_name(str(candidate))
            if key and key not in mapping:
                mapping[key] = group
    return mapping


def _asset_reference_rank(asset: dict[str, Any], group: dict[str, Any]) -> tuple[int, str]:
    """Stable, human-oriented first-pass asset selection.

    Cover always wins. For character groups we prefer MASTER/full-body/face/
    three-view references. For scenes we prefer MASTER/main/environment refs.
    The original group order still remains a deterministic tie-breaker.
    """
    aid = str(asset.get("id", ""))
    if aid and aid in {str(group.get("cover_asset_id", "")), str(group.get("effective_cover_id", ""))}:
        return (-1000, str(asset.get("display_name", "")).casefold())
    text = " ".join([
        str(asset.get("display_name", "")),
        str(asset.get("file_name", "")),
        str(asset.get("relative_path", "")),
        " ".join(asset.get("tags", []) if isinstance(asset.get("tags"), list) else []),
    ]).casefold()
    category = str(group.get("category", ""))
    if category == "角色":
        tiers = [
            (0, ["master", "母版", "角色母版"]),
            (10, ["fullbody", "full body", "全身", "完整角色", "角色资产"]),
            (20, ["face_master", "face master", "脸部母版", "正脸", "脸部", "face"]),
            (30, ["threeview", "three view", "三视图", "turnaround", "转面"]),
            (40, ["expression", "表情"]),
        ]
    elif category == "场景":
        tiers = [
            (0, ["master", "母版", "主场景", "主视图"]),
            (10, ["scene", "场景", "environment", "环境", "全景"]),
        ]
    elif category == "动作":
        tiers = [(0, ["master", "主动作", "motion", "动作", "dance", "combat", "舞蹈", "打斗"])]
    elif category == "声音":
        tiers = [(0, ["master", "voice", "声音", "音色", "配音"])]
    else:
        tiers = [(0, ["master", "母版", "main", "主"])]
    for score, keywords in tiers:
        if any(k in text for k in keywords):
            return (score, str(asset.get("display_name", "")).casefold())
    return (100, str(asset.get("display_name", "")).casefold())


def _find_group_asset_reference(
    value: str,
    group_map: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Resolve ``group/asset`` into one exact library asset.

    Group aliases/names may themselves contain ``/``. We therefore try the
    longest possible prefix first. The asset portion can match its @alias,
    display name, file name, file stem, or internal id.
    """
    raw = (value or "").strip()
    if "/" not in raw:
        return None
    parts = raw.split("/")
    for cut in range(len(parts) - 1, 0, -1):
        group_text = "/".join(parts[:cut]).strip()
        asset_text = "/".join(parts[cut:]).strip()
        group = group_map.get(_normalize_ref_name(group_text))
        if not group or not asset_text:
            continue
        assets = MANAGER.query_group_assets(str(group.get("id", "")), limit=1000)
        wanted = _normalize_ref_name(asset_text)
        for asset in assets:
            candidates = [
                str(asset.get("alias", "")),
                str(asset.get("display_name", "")),
                str(asset.get("file_name", "")),
                Path(str(asset.get("file_name", ""))).stem,
                str(asset.get("id", "")),
            ]
            if any(_normalize_ref_name(candidate) == wanted for candidate in candidates if candidate):
                return group, asset
    return None


def _compile_resource_references(
    resource_db: dict[str, Any] | None,
    prompt: str,
    max_images: int = 9,
    max_videos: int = 3,
    max_audios: int = 3,
) -> dict[str, Any]:
    resource_db = resource_db if isinstance(resource_db, dict) else {}
    root = _normalise_path(str(resource_db.get("root", "") or MANAGER.get_config().get("library_path", "")))
    groups = resource_db.get("groups") if isinstance(resource_db.get("groups"), list) else MANAGER.list_groups(root=root)
    group_map = _reference_group_map(groups)
    tokens = _extract_reference_tokens(prompt)

    resolved: list[dict[str, Any]] = []
    missing: list[str] = []
    seen_refs: set[str] = set()

    for ref_order, token in enumerate(tokens):
        # 1) Exact resource-group reference, e.g. @苏甜柠
        group = group_map.get(token["key"])
        if group:
            gid = str(group.get("id", ""))
            ref_id = f"group:{gid}"
            if gid and ref_id not in seen_refs:
                seen_refs.add(ref_id)
                assets = MANAGER.query_group_assets(gid, limit=1000)
                by_type: dict[str, list[dict[str, Any]]] = {"image": [], "video": [], "audio": []}
                for asset in assets:
                    media_type = str(asset.get("media_type", ""))
                    if media_type in by_type:
                        by_type[media_type].append(asset)
                for media_type in by_type:
                    by_type[media_type].sort(key=lambda a: _asset_reference_rank(a, group))
                resolved.append({
                    "kind": "group",
                    "ref_id": ref_id,
                    "ref_order": ref_order,
                    "token": token["raw"],
                    "reference": token["value"],
                    "group": group,
                    "assets_by_type": by_type,
                })
            continue

        # 2) Exact single-asset reference inside a group, e.g. @苏甜柠/正脸
        matched = _find_group_asset_reference(token["value"], group_map)
        if matched:
            parent_group, asset = matched
            aid = str(asset.get("id", ""))
            ref_id = f"asset:{aid}"
            if aid and ref_id not in seen_refs:
                seen_refs.add(ref_id)
                resolved.append({
                    "kind": "asset",
                    "ref_id": ref_id,
                    "ref_order": ref_order,
                    "token": token["raw"],
                    "reference": token["value"],
                    "group": parent_group,
                    "asset": asset,
                    "assets_by_type": {
                        "image": [asset] if asset.get("media_type") == "image" else [],
                        "video": [asset] if asset.get("media_type") == "video" else [],
                        "audio": [asset] if asset.get("media_type") == "audio" else [],
                    },
                })
            continue

        missing.append(token["raw"])

    limits = {
        "image": max(0, min(int(max_images), 9)),
        "video": max(0, min(int(max_videos), 3)),
        "audio": max(0, min(int(max_audios), 3)),
    }
    selected: dict[str, list[dict[str, Any]]] = {"image": [], "video": [], "audio": []}
    owners: dict[str, list[dict[str, Any]]] = {"image": [], "video": [], "audio": []}
    seen_assets: set[str] = set()

    def add_selected(media_type: str, asset: dict[str, Any], item: dict[str, Any]) -> bool:
        if len(selected[media_type]) >= limits[media_type]:
            return False
        aid = str(asset.get("id", ""))
        if not aid or aid in seen_assets:
            return False
        seen_assets.add(aid)
        selected[media_type].append(asset)
        group = item.get("group") or {}
        owners[media_type].append({
            "reference_id": item.get("ref_id"),
            "reference_kind": item.get("kind"),
            "reference_order": item.get("ref_order", 9999),
            "group_id": group.get("id"),
            "group_name": group.get("name"),
            "group_alias": group.get("alias"),
            "group_category": group.get("category"),
            "token": item.get("token"),
        })
        return True

    # Exact single-asset references are reservations: if a user explicitly
    # picked one image/video/audio, group auto-selection may not push it out.
    for item in resolved:
        if item.get("kind") != "asset":
            continue
        asset = item.get("asset") or {}
        media_type = str(asset.get("media_type", ""))
        if media_type in selected:
            add_selected(media_type, asset, item)

    # Resource groups fill the remaining H3 reference slots fairly.
    group_refs = [item for item in resolved if item.get("kind") == "group"]
    for media_type in ("image", "video", "audio"):
        cap = limits[media_type]
        round_index = 0
        while len(selected[media_type]) < cap:
            added_this_round = False
            for item in group_refs:
                items = item["assets_by_type"][media_type]
                if round_index >= len(items):
                    continue
                asset = items[round_index]
                if add_selected(media_type, asset, item):
                    added_this_round = True
                if len(selected[media_type]) >= cap:
                    break
            if not added_this_round and all(round_index >= len(item["assets_by_type"][media_type]) - 1 for item in group_refs):
                break
            round_index += 1
            if round_index > 1000:
                break

    # Final ordering follows prompt reference order. Within an auto-selected
    # group, use the group's human-oriented reference ranking.
    resolved_by_id = {str(item.get("ref_id")): item for item in resolved}
    for media_type in ("image", "video", "audio"):
        paired = list(zip(selected[media_type], owners[media_type]))
        paired.sort(key=lambda pair: (
            int(pair[1].get("reference_order", 9999)),
            0 if pair[1].get("reference_kind") == "asset" else _asset_reference_rank(
                pair[0], (resolved_by_id.get(str(pair[1].get("reference_id"))) or {}).get("group") or {}
            )[0],
            str(pair[0].get("display_name", "")).casefold(),
        ))
        selected[media_type] = [p[0] for p in paired]
        owners[media_type] = [p[1] for p in paired]

    clean_prompt = prompt or ""
    for item in sorted(resolved, key=lambda x: len(str(x["token"])), reverse=True):
        if item.get("kind") == "asset":
            replacement = str((item.get("asset") or {}).get("display_name") or (item.get("asset") or {}).get("file_name") or item.get("reference"))
        else:
            replacement = str((item.get("group") or {}).get("name", item.get("reference")))
        clean_prompt = clean_prompt.replace(str(item["token"]), replacement)

    mapping_lines: list[str] = []
    picture_index = 1
    for asset, owner in zip(selected["image"], owners["image"]):
        if owner.get("reference_kind") == "asset":
            mapping_lines.append(
                f"<Picture {picture_index}> = 单独引用图片：{asset.get('display_name', asset.get('file_name', ''))}（资源组：{owner.get('group_name') or '未分组'}）"
            )
        else:
            mapping_lines.append(
                f"<Picture {picture_index}> = {owner.get('group_name')}（{owner.get('group_category')}）参考图：{asset.get('display_name', asset.get('file_name', ''))}"
            )
        picture_index += 1
    for idx, (asset, owner) in enumerate(zip(selected["video"], owners["video"]), start=1):
        prefix = "单独引用视频" if owner.get("reference_kind") == "asset" else "参考视频"
        mapping_lines.append(
            f"<Video {idx}> = {prefix}：{owner.get('group_name')}：{asset.get('display_name', asset.get('file_name', ''))}"
        )
    for idx, (asset, owner) in enumerate(zip(selected["audio"], owners["audio"]), start=1):
        prefix = "单独引用音频" if owner.get("reference_kind") == "asset" else "参考音频"
        mapping_lines.append(
            f"<Audio {idx}> = {prefix}：{owner.get('group_name')}：{asset.get('display_name', asset.get('file_name', ''))}"
        )

    if mapping_lines:
        compiled_prompt = "【资源引用映射】\n" + "\n".join(mapping_lines) + "\n\n【镜头提示词】\n" + clean_prompt.strip()
    else:
        compiled_prompt = clean_prompt.strip()

    references_out: list[dict[str, Any]] = []
    for item in resolved:
        group = item.get("group") or {}
        ref_id = str(item.get("ref_id", ""))
        selected_ids = {
            mt: [
                a.get("id") for a, owner in zip(selected[mt], owners[mt])
                if str(owner.get("reference_id", "")) == ref_id
            ]
            for mt in ("image", "video", "audio")
        }
        if item.get("kind") == "asset":
            asset = item.get("asset") or {}
            references_out.append({
                "kind": "asset",
                "token": item.get("token"),
                "name": asset.get("display_name") or asset.get("file_name"),
                "alias": asset.get("alias"),
                "category": group.get("category") or asset.get("category"),
                "group_id": group.get("id"),
                "group_name": group.get("name"),
                "asset_id": asset.get("id"),
                "media_type": asset.get("media_type"),
                "selected": selected_ids,
            })
        else:
            references_out.append({
                "kind": "group",
                "token": item.get("token"),
                "name": group.get("name"),
                "alias": group.get("alias"),
                "category": group.get("category"),
                "group_id": group.get("id"),
                "selected": selected_ids,
            })

    return {
        "version": 2,
        "root": root,
        "prompt_original": prompt or "",
        "prompt_clean": clean_prompt.strip(),
        "prompt_compiled": compiled_prompt,
        "references": references_out,
        "missing": missing,
        "images": selected["image"],
        "videos": selected["video"],
        "audios": selected["audio"],
        "owners": owners,
        "limits": limits,
    }

def _reference_summary(context: dict[str, Any], language: str = "中文") -> str:
    refs = context.get("references", []) if isinstance(context, dict) else []
    missing = context.get("missing", []) if isinstance(context, dict) else []
    images = context.get("images", []) if isinstance(context, dict) else []
    videos = context.get("videos", []) if isinstance(context, dict) else []
    audios = context.get("audios", []) if isinstance(context, dict) else []
    if language == "English":
        lines = [
            f"References: {len(refs)}",
            f"Selected: {len(images)} images | {len(videos)} videos | {len(audios)} audio files",
        ]
        if refs:
            lines.append("Resources: " + ", ".join(str(r.get("token") or "@" + str(r.get("alias") or r.get("name") or "")) for r in refs))
        if missing:
            lines.append("Missing: " + ", ".join(missing))
        return "\n".join(lines)
    lines = [
        f"已引用资源：{len(refs)} 个",
        f"已选择：图片 {len(images)}｜视频 {len(videos)}｜音频 {len(audios)}",
    ]
    if refs:
        lines.append("资源：" + "、".join(str(r.get("token") or "@" + str(r.get("alias") or r.get("name") or "")) for r in refs))
    if missing:
        lines.append("未找到：" + "、".join(missing))
    return "\n".join(lines)


MANAGER = ResourceLibraryManager()


class AVSResourceLibrary:
    """AI Video Studio 永久资源库。

    这个节点只负责索引/检索资源，不会把整个资源库加载进显存。
    后续 @引用节点可以直接接收 AVS_RESOURCE_DB。v0.4 起 RESOURCE_DB 同时包含资源组信息。
    """

    @classmethod
    def INPUT_TYPES(cls):
        cfg = MANAGER.get_config()
        return {
            "required": {
                "language": (["中文", "English"], {"default": "中文" if cfg.get("language", "zh-CN") == "zh-CN" else "English"}),
                "library_path": (
                    "STRING",
                    {
                        "default": cfg.get("library_path", ""),
                        "multiline": False,
                        "tooltip": "永久资源库根目录；留空使用 ComfyUI input 目录。",
                    },
                ),
                "search": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "按名称、文件名、路径、别名或标签检索。",
                    },
                ),
                "media_type": (["all", "image", "video", "audio"], {"default": "all"}),
                "category": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "留空=全部；例如 角色、场景、道具、动作、声音。",
                    },
                ),
                "limit": ("INT", {"default": 200, "min": 1, "max": 1000, "step": 1}),
            }
        }

    RETURN_TYPES = ("AVS_RESOURCE_DB", "STRING")
    RETURN_NAMES = ("RESOURCE_DB", "摘要")
    FUNCTION = "build_resource_db"
    CATEGORY = "AI Video Studio/01 资源库"
    DESCRIPTION = "永久资源库 / Permanent Library：选择任意素材目录，建立图片/视频/音频索引，并在独立素材中心整理成角色/场景/道具/动作/声音资源组；不会把全部素材加载到显存。"

    def build_resource_db(
        self,
        language: str,
        library_path: str,
        search: str,
        media_type: str,
        category: str,
        limit: int,
    ):
        cfg = MANAGER.get_config()
        cfg["language"] = "en-US" if language == "English" else "zh-CN"
        _write_config(cfg)
        normalized = MANAGER.set_library_path(library_path or folder_paths.get_input_directory())
        stats = MANAGER.stats(normalized)
        if stats["total"] == 0:
            MANAGER.scan(normalized)
            stats = MANAGER.stats(normalized)
        assets = MANAGER.query(
            query=search,
            media_type=media_type,
            category=category.strip(),
            limit=limit,
            root=normalized,
        )
        resource_db = {
            "version": 2,
            "root": normalized,
            "query": search,
            "media_type": media_type,
            "category": category.strip(),
            "assets": assets,
            "stats": stats,
            "groups": MANAGER.list_groups(root=normalized),
            "group_stats": MANAGER.group_stats(normalized),
        }
        if language == "English":
            summary = (
                f"Library: {normalized}\n"
                f"Images {stats['image']} | Videos {stats['video']} | Audio {stats['audio']} | Total {stats['total']}\n"
                f"Current filter returned {len(assets)} assets"
            )
        else:
            summary = (
                f"资源库：{normalized}\n"
                f"图片 {stats['image']}｜视频 {stats['video']}｜音频 {stats['audio']}｜总计 {stats['total']}\n"
                f"当前筛选返回 {len(assets)} 个素材"
            )
        return (resource_db, summary)


class AVSResourceReference:
    """Resolve @resource-group references into a compact generation context.

    This node does not load the media into VRAM. It only resolves which files
    should be used later by the H3 smart-generation node.
    """

    @classmethod
    def INPUT_TYPES(cls):
        cfg = MANAGER.get_config()
        return {
            "required": {
                "resource_db": ("AVS_RESOURCE_DB",),
                "language": (["中文", "English"], {"default": "中文" if cfg.get("language", "zh-CN") == "zh-CN" else "English"}),
                "prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "dynamicPrompts": False,
                        "tooltip": "在提示词中输入 @ 即可引用永久资源库中的资源组。",
                    },
                ),
                "max_images": ("INT", {"default": 9, "min": 0, "max": 9, "step": 1}),
                "max_videos": ("INT", {"default": 3, "min": 0, "max": 3, "step": 1}),
                "max_audios": ("INT", {"default": 3, "min": 0, "max": 3, "step": 1}),
            }
        }

    RETURN_TYPES = ("AVS_RESOURCE_CONTEXT", "STRING", "STRING")
    RETURN_NAMES = ("RESOURCE_CONTEXT", "PROMPT", "引用摘要")
    FUNCTION = "resolve_references"
    CATEGORY = "AI Video Studio/02 资源引用"
    DESCRIPTION = "@资源引用 / @ Resource Reference：在提示词里输入 @角色 可引用整个资源组；输入 @角色/某张图 可只引用单个素材。自动为下一步智能生成选择最多 9 图 / 3 视频 / 3 音频，不会加载整个资源库到显存。"

    def resolve_references(
        self,
        resource_db: dict[str, Any],
        language: str,
        prompt: str,
        max_images: int,
        max_videos: int,
        max_audios: int,
    ):
        context = _compile_resource_references(
            resource_db,
            prompt,
            max_images=max_images,
            max_videos=max_videos,
            max_audios=max_audios,
        )
        return (context, context["prompt_compiled"], _reference_summary(context, language))



# -----------------------------------------------------------------------------
# H3 Smart Generation v0.6
# -----------------------------------------------------------------------------

def _avs_snap_h3_length(seconds: float) -> int:
    """Snap seconds at 24 fps to MiniMax H3's 17k+5 frame grid."""
    seconds = max(0.2, min(float(seconds), 15.1))
    target = max(5, int(round(seconds * 24.0)))
    k = max(0, int(round((target - 5) / 17.0)))
    return 17 * k + 5


def _avs_resolution(preset: str, aspect_ratio: str, custom_width: int, custom_height: int) -> tuple[int, int]:
    # Presets intentionally use H3-friendly multiples of 32.
    ratios = {
        "16:9": {
            "快速预览 480P": (864, 480),
            "快速人物 544P": (960, 544),
            "标准 720P": (1280, 736),
            "原生 768": (1344, 768),
        },
        "9:16": {
            "快速预览 480P": (480, 864),
            "快速人物 544P": (544, 960),
            "标准 720P": (736, 1280),
            "原生 768": (768, 1344),
        },
        "1:1": {
            "快速预览 480P": (480, 480),
            "快速人物 544P": (544, 544),
            "标准 720P": (736, 736),
            "原生 768": (768, 768),
        },
        "4:3": {
            "快速预览 480P": (640, 480),
            "快速人物 544P": (736, 544),
            "标准 720P": (960, 736),
            "原生 768": (1024, 768),
        },
        "3:4": {
            "快速预览 480P": (480, 640),
            "快速人物 544P": (544, 736),
            "标准 720P": (736, 960),
            "原生 768": (768, 1024),
        },
    }
    if preset == "自定义":
        w = max(32, int(round(int(custom_width) / 32.0)) * 32)
        h = max(32, int(round(int(custom_height) / 32.0)) * 32)
        return w, h
    return ratios.get(aspect_ratio, ratios["16:9"]).get(preset, (864, 480))


def _avs_load_image_tensor(path: str) -> torch.Tensor:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"参考图片不存在：{source}")
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        arr = np.asarray(img, dtype=np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


def _avs_load_video_frames(path: str, max_frames: int, target_fps: float = 24.0) -> torch.Tensor:
    """Decode a reference video to ComfyUI IMAGE batch using PyAV.

    Only the frames required by the target H3 clip are materialized. This keeps
    reference-library videos lazy until they are actually used.
    """
    try:
        import av  # ComfyUI ships PyAV with its native video system.
    except Exception as exc:
        raise RuntimeError("无法读取参考视频：当前 ComfyUI 环境缺少可用的 PyAV。") from exc

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"参考视频不存在：{source}")
    frames: list[np.ndarray] = []
    with av.open(str(source), mode="r") as container:
        if not container.streams.video:
            raise ValueError(f"文件没有视频轨道：{source.name}")
        stream = container.streams.video[0]
        next_time = 0.0
        fallback_index = 0
        for frame in container.decode(stream):
            if len(frames) >= max_frames:
                break
            timestamp = None
            if frame.pts is not None and stream.time_base is not None:
                try:
                    timestamp = float(frame.pts * stream.time_base)
                except Exception:
                    timestamp = None
            if timestamp is None:
                # If timestamps are unavailable, retain frames sequentially.
                take = True
            else:
                take = timestamp + 1e-6 >= next_time
            if not take:
                continue
            arr = frame.to_ndarray(format="rgb24")
            frames.append(arr)
            fallback_index += 1
            if timestamp is not None:
                next_time += 1.0 / float(target_fps)
        if not frames:
            raise ValueError(f"无法从视频解码画面：{source.name}")
    batch = np.stack(frames, axis=0).astype(np.float32) / 255.0
    return torch.from_numpy(batch)


def _avs_load_audio(path: str, target_rate: int = 44100) -> dict[str, Any]:
    """Decode an audio asset into ComfyUI's AUDIO dictionary."""
    try:
        import av
    except Exception as exc:
        raise RuntimeError("无法读取参考音频：当前 ComfyUI 环境缺少可用的 PyAV。") from exc

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"参考音频不存在：{source}")
    chunks: list[np.ndarray] = []
    with av.open(str(source), mode="r") as container:
        if not container.streams.audio:
            raise ValueError(f"文件没有音频轨道：{source.name}")
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(format="fltp", layout="stereo", rate=target_rate)
        for frame in container.decode(stream):
            converted = resampler.resample(frame)
            if converted is None:
                continue
            if not isinstance(converted, list):
                converted = [converted]
            for out_frame in converted:
                arr = out_frame.to_ndarray()
                arr = np.asarray(arr, dtype=np.float32)
                if arr.ndim == 1:
                    arr = arr[None, :]
                # PyAV may occasionally expose packed audio as (samples, channels).
                if arr.shape[0] > 8 and arr.shape[-1] <= 8:
                    arr = arr.T
                chunks.append(arr)
        flushed = resampler.resample(None)
        if flushed is not None:
            if not isinstance(flushed, list):
                flushed = [flushed]
            for out_frame in flushed:
                arr = np.asarray(out_frame.to_ndarray(), dtype=np.float32)
                if arr.ndim == 1:
                    arr = arr[None, :]
                if arr.shape[0] > 8 and arr.shape[-1] <= 8:
                    arr = arr.T
                chunks.append(arr)
    if not chunks:
        raise ValueError(f"无法从音频解码波形：{source.name}")
    waveform = np.concatenate(chunks, axis=1)
    return {"waveform": torch.from_numpy(waveform).unsqueeze(0), "sample_rate": target_rate}


def _avs_node_result(output: Any) -> tuple[Any, ...]:
    if hasattr(output, "result"):
        result = output.result
        if result is None:
            return tuple()
        return tuple(result)
    if isinstance(output, tuple):
        return output
    if isinstance(output, list):
        return tuple(output)
    return (output,)


def _avs_h3_plan_summary(plan: dict[str, Any], language: str) -> str:
    zh = language != "English"
    if zh:
        return (
            f"模式：{plan['mode_label']}\n"
            f"画面：{plan['width']} × {plan['height']}｜{plan['length']} 帧｜约 {plan['seconds_actual']:.2f} 秒\n"
            f"参考：图片 {plan['image_count']}｜视频 {plan['video_count']}｜音频 {plan['audio_count']}\n"
            f"参考图尺寸：{plan['ref_image_size']}"
        )
    return (
        f"Mode: {plan['mode_label']}\n"
        f"Canvas: {plan['width']} × {plan['height']} | {plan['length']} frames | ~{plan['seconds_actual']:.2f}s\n"
        f"References: {plan['image_count']} images | {plan['video_count']} videos | {plan['audio_count']} audios\n"
        f"Reference image sizing: {plan['ref_image_size']}"
    )


class AVSH3SmartGenerator:
    """Turn RESOURCE_CONTEXT into native MiniMax H3 conditioning + AV latent.

    The permanent library remains disk-backed. Only the references selected by
    @-syntax are loaded when this node executes.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "resource_context": ("AVS_RESOURCE_CONTEXT",),
                "clip": ("CLIP",),
                "video_vae": ("VAE",),
                "language": (["中文", "English"], {"default": "中文"}),
                "generation_mode": (["自动", "参考生视频", "文生视频"], {"default": "自动"}),
                "resolution": (["快速预览 480P", "快速人物 544P", "标准 720P", "原生 768", "自定义"], {"default": "快速预览 480P"}),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4"], {"default": "16:9"}),
                "seconds": ("FLOAT", {"default": 5.0, "min": 0.2, "max": 15.1, "step": 0.1}),
                "ref_image_size": (["match", "max"], {"default": "match"}),
                "custom_width": ("INT", {"default": 864, "min": 32, "max": 4096, "step": 32}),
                "custom_height": ("INT", {"default": 480, "min": 32, "max": 4096, "step": 32}),
            },
            "optional": {
                "audio_vae": ("VAE",),
                "prompt_override": ("STRING", {"default": "", "multiline": True, "dynamicPrompts": False}),
            },
        }

    RETURN_TYPES = ("CONDITIONING", "LATENT", "STRING", "AVS_H3_PLAN", "STRING")
    RETURN_NAMES = ("正向条件", "潜空间", "PROMPT", "H3_PLAN", "生成摘要")
    FUNCTION = "prepare_h3"
    CATEGORY = "AI Video Studio/03 H3智能生成"
    DESCRIPTION = (
        "H3智能生成：读取 @资源引用 的 RESOURCE_CONTEXT，只加载本次真正使用的图片/视频/音频，"
        "自动转换为 MiniMax H3 ReferenceToVideo/T2V 所需的条件与 AV Latent。"
    )

    def prepare_h3(
        self,
        resource_context: dict[str, Any],
        clip: Any,
        video_vae: Any,
        language: str,
        generation_mode: str,
        resolution: str,
        aspect_ratio: str,
        seconds: float,
        ref_image_size: str,
        custom_width: int,
        custom_height: int,
        audio_vae: Any = None,
        prompt_override: str = "",
    ):
        if not isinstance(resource_context, dict):
            raise ValueError("RESOURCE_CONTEXT 无效，请先连接 AI视频工作室｜资源引用。")

        missing = resource_context.get("missing") or []
        if missing:
            raise ValueError("存在未找到的 @引用：" + "、".join(map(str, missing)))

        images = list(resource_context.get("images") or [])
        videos = list(resource_context.get("videos") or [])
        audios = list(resource_context.get("audios") or [])
        has_refs = bool(images or videos or audios)

        requested_mode = generation_mode
        if generation_mode == "自动":
            actual_mode = "参考生视频" if has_refs else "文生视频"
        else:
            actual_mode = generation_mode
        if actual_mode == "参考生视频" and not has_refs:
            raise ValueError("当前选择“参考生视频”，但 RESOURCE_CONTEXT 没有任何实际引用素材。")

        width, height = _avs_resolution(resolution, aspect_ratio, custom_width, custom_height)
        length = _avs_snap_h3_length(seconds)
        prompt = (prompt_override or "").strip() or str(resource_context.get("prompt_compiled", "")).strip()
        if not prompt:
            prompt = str(resource_context.get("prompt_clean", "")).strip()
        if not prompt:
            raise ValueError("提示词为空。请在“资源引用”节点填写镜头提示词。")

        # Lazy import: older ComfyUI builds can still load this plugin and show a
        # clear execution error instead of crashing at startup.
        try:
            from comfy_extras import nodes_minimax_h3 as h3
        except Exception as exc:
            raise RuntimeError(
                "当前 ComfyUI 没有可用的原生 MiniMax H3 节点。请先更新 ComfyUI 到支持 H3 的版本。"
            ) from exc

        if actual_mode == "文生视频":
            output = h3.MiniMaxH3ImageToVideo.execute(
                clip=clip,
                vae=video_vae,
                prompt=prompt,
                width=width,
                height=height,
                length=length,
                first_frame=None,
                last_frame=None,
            )
            positive, latent = _avs_node_result(output)[:2]
            loaded_image_count = loaded_video_count = loaded_audio_count = 0
        else:
            ref_images: dict[str, torch.Tensor] = {}
            ref_videos: dict[str, torch.Tensor] = {}
            ref_audios: dict[str, dict[str, Any]] = {}

            for idx, asset in enumerate(images[:9]):
                ref_images[f"ref_image_{idx}"] = _avs_load_image_tensor(str(asset.get("path", "")))
            for idx, asset in enumerate(videos[:3]):
                ref_videos[f"ref_video_{idx}"] = _avs_load_video_frames(
                    str(asset.get("path", "")), max_frames=length, target_fps=24.0
                )
            if audios and audio_vae is None:
                raise ValueError("本次 @引用包含音频，请连接 Audio VAE；如果暂时不需要音频参考，请移除对应 @引用。")
            for idx, asset in enumerate(audios[:3]):
                ref_audios[f"ref_audio_{idx}"] = _avs_load_audio(str(asset.get("path", "")))

            output = h3.MiniMaxH3ReferenceToVideo.execute(
                clip=clip,
                vae=video_vae,
                audio_vae=audio_vae,
                prompt=prompt,
                width=width,
                height=height,
                length=length,
                ref_image_size=ref_image_size,
                ref_images=ref_images,
                ref_videos=ref_videos,
                ref_video_audios={},
                ref_audios=ref_audios,
            )
            positive, latent = _avs_node_result(output)[:2]
            loaded_image_count = len(ref_images)
            loaded_video_count = len(ref_videos)
            loaded_audio_count = len(ref_audios)

        plan = {
            "version": 1,
            "mode_requested": requested_mode,
            "mode": actual_mode,
            "mode_label": actual_mode,
            "width": width,
            "height": height,
            "length": length,
            "seconds_requested": float(seconds),
            "seconds_actual": float(length) / 24.0,
            "resolution_preset": resolution,
            "aspect_ratio": aspect_ratio,
            "ref_image_size": ref_image_size,
            "image_count": loaded_image_count,
            "video_count": loaded_video_count,
            "audio_count": loaded_audio_count,
            "image_assets": [
                {"id": a.get("id"), "name": a.get("display_name") or a.get("file_name"), "path": a.get("path")}
                for a in images[:loaded_image_count]
            ],
            "video_assets": [
                {"id": a.get("id"), "name": a.get("display_name") or a.get("file_name"), "path": a.get("path")}
                for a in videos[:loaded_video_count]
            ],
            "audio_assets": [
                {"id": a.get("id"), "name": a.get("display_name") or a.get("file_name"), "path": a.get("path")}
                for a in audios[:loaded_audio_count]
            ],
        }
        return (positive, latent, prompt, plan, _avs_h3_plan_summary(plan, language))

routes = PromptServer.instance.routes


def _avs_local_media_dir() -> Path:
    root = Path(folder_paths.get_input_directory()) / "AI_Video_Studio" / "local_media"
    root.mkdir(parents=True, exist_ok=True)
    return root


@routes.post("/avs/local/upload")
async def avs_local_upload(request):
    """Upload a user-picked local image/video/audio into ComfyUI input.

    The browser cannot safely expose an arbitrary Windows path to JS, so the
    native file picker sends the selected file here.  We keep a private copy in
    ComfyUI/input/AI_Video_Studio/local_media and return both a generation path
    and a normal /view URL descriptor for previews.
    """
    kind = str(request.query.get("kind", "") or "").lower().strip()
    allowed = {
        "image": IMAGE_EXTS,
        "video": VIDEO_EXTS,
        "audio": AUDIO_EXTS,
    }
    if kind not in allowed:
        return web.json_response({"ok": False, "error": "不支持的本地文件类型。"}, status=400)
    try:
        reader = await request.multipart()
        field = await reader.next()
        while field is not None and getattr(field, "name", "") != "file":
            field = await reader.next()
        if field is None or not getattr(field, "filename", None):
            return web.json_response({"ok": False, "error": "没有收到文件。"}, status=400)

        original = Path(str(field.filename)).name
        ext = Path(original).suffix.lower()
        if ext not in allowed[kind]:
            return web.json_response({"ok": False, "error": f"这个文件不是可用的{kind}格式：{ext or '无扩展名'}"}, status=400)

        safe_stem = re.sub(r"[^0-9A-Za-z_\-\u3400-\u9fff]+", "_", Path(original).stem).strip("_") or "media"
        filename = f"{uuid.uuid4().hex[:10]}_{safe_stem}{ext}"
        target_dir = _avs_local_media_dir()
        target = target_dir / filename
        with target.open("wb") as f:
            while True:
                chunk = await field.read_chunk(size=1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        subfolder = "AI_Video_Studio/local_media"
        return web.json_response({
            "ok": True,
            "kind": kind,
            "name": original,
            "filename": filename,
            "subfolder": subfolder,
            "type": "input",
            "path": str(target.resolve()),
            "size": target.stat().st_size,
        })
    except Exception as exc:
        log.exception("Local media upload failed")
        return web.json_response({"ok": False, "error": str(exc)}, status=500)


@routes.get("/avs/library/status")
async def avs_library_status(request):
    try:
        cfg = MANAGER.get_config()
        stats, groups = MANAGER.stats(), MANAGER.group_stats()
        return web.json_response({"ok": True, "config": cfg, "stats": stats, "group_stats": groups,
                                  "native_picker": native_picker_available(request.remote or ""), "platform": os.name})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=500)


@routes.post("/avs/library/config")
async def avs_library_config(request):
    try:
        payload = await request.json()
        path = MANAGER.set_library_path(str(payload.get("library_path", "")))
        return web.json_response({"ok": True, "library_path": path, "stats": MANAGER.stats(path)})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/settings/language")
async def avs_settings_language(request):
    try:
        payload = await request.json()
        language = str(payload.get("language", "zh-CN"))
        if language not in {"zh-CN", "en-US"}:
            language = "zh-CN"
        cfg = MANAGER.get_config()
        cfg["language"] = language
        _write_config(cfg)
        return web.json_response({"ok": True, "language": language})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/scan")
async def avs_library_scan(request):
    try:
        payload = await request.json()
        path = str(payload.get("library_path", "") or "")
        result = await asyncio.to_thread(MANAGER.scan, path or None)
        return web.json_response(result)
    except Exception as exc:
        log.exception("资源库扫描失败")
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.get("/avs/library/assets")
async def avs_library_assets(request):
    try:
        query = request.query.get("q", "")
        media_type = request.query.get("type", "all")
        category = request.query.get("category", "")
        group_id = request.query.get("group_id", "").strip()
        unassigned = request.query.get("unassigned", "0") in {"1", "true", "yes"}
        limit = int(request.query.get("limit", "200"))
        offset = int(request.query.get("offset", "0"))
        if group_id:
            assets = MANAGER.query_group_assets(group_id, query, media_type, limit, offset)
            total_filtered = MANAGER.query_group_assets_count(group_id, query, media_type)
        elif unassigned:
            assets = MANAGER.query_unassigned(query, media_type, limit, offset)
            total_filtered = MANAGER.query_unassigned_count(query, media_type)
        else:
            assets = MANAGER.query(query, media_type, category, limit, offset)
            total_filtered = MANAGER.query_count(query, media_type, category)
        return web.json_response({
            "ok": True,
            "assets": assets,
            "stats": MANAGER.stats(),
            "group_stats": MANAGER.group_stats(),
            "total_filtered": total_filtered,
        })
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/asset/{asset_id}/meta")
async def avs_library_asset_meta(request):
    try:
        asset_id = request.match_info["asset_id"]
        payload = await request.json()
        asset = MANAGER.update_meta(asset_id, payload)
        return web.json_response({"ok": True, "asset": asset})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/assets/bulk-meta")
async def avs_library_assets_bulk_meta(request):
    try:
        payload = await request.json()
        ids = payload.get("ids", [])
        if not isinstance(ids, list):
            raise ValueError("ids 必须是数组。")
        changed = MANAGER.bulk_update_meta(ids, payload)
        return web.json_response({"ok": True, "changed": changed})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.get("/avs/library/groups")
async def avs_library_groups(request):
    try:
        category = request.query.get("category", "").strip()
        groups = MANAGER.list_groups(category=category)
        return web.json_response({"ok": True, "groups": groups, "group_stats": MANAGER.group_stats()})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/groups")
async def avs_library_create_group(request):
    try:
        payload = await request.json()
        group = MANAGER.create_group(payload)
        ids = payload.get("asset_ids", [])
        if isinstance(ids, list) and ids:
            MANAGER.add_assets_to_group(group["id"], ids)
            group = MANAGER.get_group(group["id"])
        return web.json_response({"ok": True, "group": group})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/group/{group_id}")
async def avs_library_update_group(request):
    try:
        payload = await request.json()
        group = MANAGER.update_group(request.match_info["group_id"], payload)
        return web.json_response({"ok": True, "group": group})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.delete("/avs/library/group/{group_id}")
async def avs_library_delete_group(request):
    try:
        ok = MANAGER.delete_group(request.match_info["group_id"])
        return web.json_response({"ok": True, "deleted": ok})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/group/{group_id}/assets")
async def avs_library_add_group_assets(request):
    try:
        payload = await request.json()
        ids = payload.get("ids", [])
        if not isinstance(ids, list):
            raise ValueError("ids 必须是数组。")
        changed = MANAGER.add_assets_to_group(request.match_info["group_id"], ids)
        return web.json_response({"ok": True, "changed": changed, "group": MANAGER.get_group(request.match_info["group_id"])})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.delete("/avs/library/group/{group_id}/assets")
async def avs_library_remove_group_assets(request):
    try:
        payload = await request.json()
        ids = payload.get("ids", [])
        if not isinstance(ids, list):
            raise ValueError("ids 必须是数组。")
        changed = MANAGER.remove_assets_from_group(request.match_info["group_id"], ids)
        return web.json_response({"ok": True, "changed": changed, "group": MANAGER.get_group(request.match_info["group_id"])})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


def _read_web_text(filename: str) -> str:
    """Read bundled UI files as UTF-8 text.

    We deliberately avoid aiohttp.web.FileResponse for the embedded H5 UI.
    On some Windows + Python 3.13 + aiohttp/ComfyUI combinations, FileResponse
    can close the connection while preparing a local file, which Edge/Chrome
    reports as ERR_INVALID_RESPONSE. Returning an in-memory Response for these
    small static assets is much more robust.
    """
    path = PLUGIN_DIR / "web" / filename
    if not path.exists() or not path.is_file():
        raise web.HTTPNotFound(text=f"UI file not found: {filename}")
    return path.read_text(encoding="utf-8")


async def _stream_local_file(request, source: Path):
    """Stream a media file with basic HTTP Range support.

    This avoids relying on FileResponse for user media too, while keeping large
    video/audio files out of memory.
    """
    if not source.exists() or not source.is_file():
        raise web.HTTPNotFound(text="source file unavailable")

    size = source.stat().st_size
    content_type = mimetypes.guess_type(str(source))[0] or "application/octet-stream"
    start = 0
    end = max(0, size - 1)
    status = 200

    range_header = request.headers.get("Range", "")
    if range_header.startswith("bytes=") and size > 0:
        try:
            spec = range_header[6:].split(",", 1)[0].strip()
            left, right = spec.split("-", 1)
            if left:
                start = int(left)
                end = int(right) if right else size - 1
            else:
                suffix = int(right)
                start = max(0, size - suffix)
                end = size - 1
            if start < 0 or start >= size or end < start:
                raise ValueError
            end = min(end, size - 1)
            status = 206
        except Exception:
            raise web.HTTPRequestRangeNotSatisfiable(
                headers={"Content-Range": f"bytes */{size}"}
            )

    length = 0 if size == 0 else end - start + 1
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Cache-Control": "private, max-age=300",
    }
    if status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"

    response = web.StreamResponse(status=status, headers=headers)
    response.content_type = content_type
    await response.prepare(request)

    if request.method == "HEAD" or length <= 0:
        await response.write_eof()
        return response

    remaining = length
    with source.open("rb") as fh:
        fh.seek(start)
        while remaining > 0:
            chunk = await asyncio.to_thread(fh.read, min(1024 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            await response.write(chunk)
    await response.write_eof()
    return response




# v0.4.1 compatibility action endpoints.
# Some ComfyUI/Desktop environments or middleware stacks can return 405 for
# REST-style route method overloading. These POST-only action routes avoid
# sharing the same path across GET/POST/DELETE and are used by the v0.4.1 UI.
@routes.post("/avs/library/group/create")
async def avs_library_create_group_action(request):
    try:
        payload = await request.json()
        group = MANAGER.create_group(payload)
        ids = payload.get("asset_ids", [])
        if isinstance(ids, list) and ids:
            MANAGER.add_assets_to_group(group["id"], ids)
            group = MANAGER.get_group(group["id"])
        return web.json_response({"ok": True, "group": group})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/group/{group_id}/update")
async def avs_library_update_group_action(request):
    try:
        payload = await request.json()
        group = MANAGER.update_group(request.match_info["group_id"], payload)
        return web.json_response({"ok": True, "group": group})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/group/{group_id}/delete")
async def avs_library_delete_group_action(request):
    try:
        ok = MANAGER.delete_group(request.match_info["group_id"])
        return web.json_response({"ok": True, "deleted": ok})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/group/{group_id}/assets/add")
async def avs_library_add_group_assets_action(request):
    try:
        payload = await request.json()
        ids = payload.get("ids", [])
        if not isinstance(ids, list):
            raise ValueError("ids 必须是数组。")
        changed = MANAGER.add_assets_to_group(request.match_info["group_id"], ids)
        return web.json_response({"ok": True, "changed": changed, "group": MANAGER.get_group(request.match_info["group_id"])})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/group/{group_id}/assets/remove")
async def avs_library_remove_group_assets_action(request):
    try:
        payload = await request.json()
        ids = payload.get("ids", [])
        if not isinstance(ids, list):
            raise ValueError("ids 必须是数组。")
        changed = MANAGER.remove_assets_from_group(request.match_info["group_id"], ids)
        return web.json_response({"ok": True, "changed": changed, "group": MANAGER.get_group(request.match_info["group_id"])})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/reference/preview")
async def avs_reference_preview(request):
    try:
        payload = await request.json()
        cfg = MANAGER.get_config()
        root = _normalise_path(str(cfg.get("library_path", "")))
        resource_db = {
            "version": 2,
            "root": root,
            "groups": MANAGER.list_groups(root=root),
        }
        context = _compile_resource_references(
            resource_db,
            str(payload.get("prompt", "")),
            max_images=int(payload.get("max_images", 9)),
            max_videos=int(payload.get("max_videos", 3)),
            max_audios=int(payload.get("max_audios", 3)),
        )
        language = "English" if cfg.get("language") == "en-US" else "中文"
        return web.json_response({
            "ok": True,
            "context": context,
            "prompt": context["prompt_compiled"],
            "summary": _reference_summary(context, language),
        })
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.get("/avs/library/file/{asset_id}")
async def avs_library_file(request):
    asset_id = request.match_info["asset_id"]
    asset = MANAGER.get_asset(asset_id)
    if not asset:
        raise web.HTTPNotFound(text="asset not found")
    return await _stream_local_file(request, Path(asset["path"]))


@routes.get("/avs/library/ui")
async def avs_library_ui(request):
    try:
        return web.Response(
            text=_read_web_text("library.html"),
            content_type="text/html",
            charset="utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except web.HTTPException:
        raise
    except Exception as exc:
        log.exception("资源库 H5 页面加载失败")
        return web.Response(text=f"AI Video Studio UI load failed: {exc}", status=500)


@routes.get("/avs/library/ui.css")
async def avs_library_ui_css(request):
    return web.Response(
        text=_read_web_text("library.css"),
        content_type="text/css",
        charset="utf-8",
        headers={"Cache-Control": "no-store"},
    )


@routes.get("/avs/library/ui.js")
async def avs_library_ui_js(request):
    return web.Response(
        text=_read_web_text("library_page.js"),
        content_type="application/javascript",
        charset="utf-8",
        headers={"Cache-Control": "no-store"},
    )


@routes.get("/avs/library/health")
async def avs_library_health(request):
    return web.json_response({
        "ok": True,
        "plugin": "ComfyUI-AI-Video-Studio",
        "version": "0.11.0",
        "ui": str((PLUGIN_DIR / "web" / "library.html").exists()),
        "capabilities": {"asset_groups": True, "post_action_routes": True, "resource_references": True, "h3_smart_generator": True, "director": True, "one_click_generation": True},
    })


@routes.get("/avs/library/thumb/{asset_id}")
async def avs_library_thumb(request):
    asset_id = request.match_info["asset_id"]
    asset = MANAGER.get_asset(asset_id)
    if not asset:
        raise web.HTTPNotFound(text="asset not found")
    thumb = THUMB_DIR / f"{asset_id}.jpg"
    if not thumb.exists():
        source = Path(asset["path"])
        ok = False
        if asset["media_type"] == "image":
            ok = await asyncio.to_thread(_make_image_thumb, source, thumb)
        elif asset["media_type"] == "video":
            ok = await asyncio.to_thread(_make_video_thumb, source, thumb)
        if not ok:
            raise web.HTTPNotFound(text="thumbnail unavailable")
    try:
        return web.Response(
            body=thumb.read_bytes(),
            content_type="image/jpeg",
            headers={"Cache-Control": "private, max-age=86400"},
        )
    except Exception as exc:
        log.exception("缩略图读取失败")
        raise web.HTTPInternalServerError(text=str(exc))


@routes.get("/avs/library/dirs")
async def avs_library_dirs(request):
    """服务器侧目录浏览器。

    注意：这是查看运行 ComfyUI 的那台机器的目录，不是浏览器客户端机器。
    """
    try:
        requested = request.query.get("path", "").strip()
        current = browser_directory(requested, MANAGER.get_config().get("library_path", ""), folder_paths.get_input_directory())
        dirs = []
        try:
            for item in current.iterdir():
                try:
                    if item.is_dir():
                        dirs.append(item.name)
                except PermissionError:
                    continue
        except PermissionError:
            dirs = []
        dirs.sort(key=lambda x: x.lower())
        parent = str(current.parent) if current.parent != current else ""
        roots = []
        if os.name == "nt":
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    roots.append(drive)
        else:
            roots.append("/")
            home = str(Path.home())
            if home not in roots:
                roots.append(home)
            for common in ("/mnt", "/media", "/root", "/home"):
                if os.path.isdir(common) and common not in roots:
                    roots.append(common)
        return web.json_response({"ok": True, "path": str(current), "parent": parent, "dirs": dirs, "roots": roots})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.post("/avs/library/pick-directory")
async def avs_library_pick_directory(request):
    if not native_picker_available(request.remote or ""):
        return web.json_response({"ok": False, "error": "请使用电脑文件夹导入或服务器目录选择。"}, status=400)
    try:
        body = await request.json()
        initial = browser_directory(body.get("initial_path"), MANAGER.get_config().get("library_path"), folder_paths.get_input_directory())
        data = await asyncio.to_thread(pick_windows_directory, str(initial))
        return web.json_response({"ok": True, **data})
    except Exception as exc:
        return web.json_response({"ok": False, "error": f"无法打开文件夹选择窗口：{exc}"}, status=400)


@routes.post("/avs/library/import-folder")
async def avs_library_import_folder(request):
    target = None
    created = False
    try:
        import_id = request.query.get("import_id") or uuid.uuid4().hex
        root, target = import_target(folder_paths.get_input_directory(), import_id, request.query.get("relative_path"))
        if _media_type(target) is None:
            raise ValueError("仅支持导入图片、视频或音频。")
        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "file" or not field.filename:
            raise ValueError("没有收到素材文件。")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as destination:
            created = True
            while chunk := await field.read_chunk(size=1024 * 1024):
                destination.write(chunk)
        return web.json_response({"ok": True, "import_id": import_id, "library_path": str(root)})
    except Exception as exc:
        if created and target is not None:
            target.unlink(missing_ok=True)
        return web.json_response({"ok": False, "error": str(exc)}, status=400)


@routes.get("/avs/library/folders.js")
async def avs_library_folder_script(request):
    return web.FileResponse(PLUGIN_DIR / "web" / "library_folders.js")


NODE_CLASS_MAPPINGS = {
    "AVSResourceLibrary": AVSResourceLibrary,
    "AVSResourceReference": AVSResourceReference,
    "AVSH3SmartGenerator": AVSH3SmartGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AVSResourceLibrary": "AI Video Studio｜永久资源库",
    "AVSResourceReference": "AI Video Studio｜资源引用",
    "AVSH3SmartGenerator": "AI Video Studio｜H3智能生成",
}
