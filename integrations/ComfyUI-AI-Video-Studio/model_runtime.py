"""Model ownership for one director execution (including its serial shots)."""
import gc
import logging
import time
from contextvars import ContextVar
from functools import wraps

import comfy.model_management as mm
import comfy_aimdo.host_buffer


_session = ContextVar("avs_model_session", default=None)


class ModelSession:
    def __init__(self):
        self.components = {}
        self.bundle_key = None
        self.bundle = None
        self.loads = 0

    def component(self, slot, key, load):
        previous = self.components.get(slot)
        if previous is not None and previous[0] == key:
            return previous[1]
        if previous is not None:
            unload(previous[1])
            del self.components[slot]
            del previous
            gc.collect()
        value = load()
        self.components[slot] = (key, value)
        self.loads += 1
        return value

    def release(self):
        if self.bundle is not None:
            unload(self.bundle["model"])
            unload(self.bundle["clip"])
        for _, value in self.components.values():
            unload(value)

    def close(self):
        try:
            self.release()
        finally:
            self.bundle = None
            self.components.clear()
            gc.collect()
        mm.cleanup_models()
        mm.soft_empty_cache()


def unload(value):
    # CLIP and VAE expose their ModelPatcher through .patcher.
    patcher = value.patcher if hasattr(value, "patcher") else value
    mm.unload_model_and_clones(patcher)


def current_session():
    session = _session.get()
    if session is None:
        raise RuntimeError("AVS model loading must run inside a generation session")
    return session


def model_session(function):
    @wraps(function)
    def execute(*args, **kwargs):
        if _session.get() is not None:
            return function(*args, **kwargs)
        session = ModelSession()
        token = _session.set(session)
        try:
            try:
                result = function(*args, **kwargs)
            except BaseException:
                try:
                    session.close()
                except RuntimeError as cleanup_error:
                    logging.warning("AVS cleanup failed; restart ComfyUI: %s", cleanup_error)
                raise
            session.close()
            return result
        finally:
            _session.reset(token)
    return execute


def run_stage(label, function, *args, **kwargs):
    started = time.perf_counter()
    for attempt in range(2):
        try:
            result = function(*args, **kwargs)
            logging.info("AVS %s: %.2fs", label, time.perf_counter() - started)
            return result
        except RuntimeError as exc:
            message = str(exc).lower()
            read_error = any(text in message for text in (
                "hostbuffer.read_file_slice failed", "hostbuf_file_reader_read failed",
                "getoverlappedresult failed",
            ))
            memory_error = "out of memory" in message
            if not (read_error or memory_error):
                raise
            if attempt:
                raise RuntimeError(
                    f"{label}在释放模型资源后仍失败：{exc}。"
                    "请重启 ComfyUI 释放动态加载状态；若仍是 HostBuffer 错误，"
                    "可测试启动参数 --disable-async-offload --disable-pinned-memory。"
                ) from exc
            logging.warning("AVS %s: releasing model resources and retrying once (%s)", label, exc)
        # Leave the except block first, releasing the failed call's traceback/tensors.
        session = _session.get()
        if session is not None:
            session.release()
        else:
            mm.unload_all_models()
        comfy_aimdo.host_buffer.cleanup_file_reader()
        gc.collect()
        mm.soft_empty_cache()
