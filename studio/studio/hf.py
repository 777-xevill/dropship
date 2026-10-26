"""Calling free Hugging Face Spaces (ZeroGPU) from Python.

Quota (checked 2026-10-15, huggingface.co/docs/hub/spaces-zerogpu):
  no token   -> 2 GPU-minutes per day
  free token -> 5 GPU-minutes per day   (big Spaces on 'xlarge' GPUs count double)
Quota resets 24 h after your first GPU use of the day.
"""
import re
import shutil
from pathlib import Path

from . import config
from .util import StudioError

_clients: dict = {}


class QuotaError(StudioError):
    def __init__(self, msg: str, retry_in: str = ""):
        super().__init__(msg)
        self.retry_in = retry_in


def client(space: str):
    if space not in _clients:
        try:
            from gradio_client import Client
        except ImportError as e:
            raise StudioError("gradio_client missing: run  studio setup") from e
        try:
            _clients[space] = Client(space, token=config.HF_TOKEN, verbose=False, httpx_kwargs={"timeout": 900},
                                     download_files=str(config.CACHE / "gradio"), analytics_enabled=False)
        except Exception as e:  # noqa: BLE001
            raise StudioError(f"Could not reach the free Space '{space}' ({str(e)[:200]}). "
                              "It may be sleeping/rebuilding: try again in a few minutes.") from e
    return _clients[space]


def reset(space: str) -> None:
    _clients.pop(space, None)


_NETWORK_HINTS = ("getaddrinfo", "ConnectError", "ConnectTimeout", "ReadTimeout", "timed out", "Connection reset",
                  "RemoteProtocolError", "Server disconnected", "Connection aborted", "EOF occurred", "SSL")


def call(space: str, fn, tries: int = 4):
    """Run fn(client) against a Space. Retries brief network drops (~1 min); turns quota and other failures
    into clear StudioErrors."""
    import time
    from .util import say
    for i in range(tries):
        try:
            return fn(client(space))
        except QuotaError:
            raise
        except Exception as e:  # noqa: BLE001
            text = f"{type(e).__name__}: {e}"
            network = any(h in text for h in _NETWORK_HINTS)
            if network and i < tries - 1:
                wait = 10 * (i + 1)
                say(f"network hiccup reaching {space} ({text[:60]}), retrying in {wait}s", kind="warn")
                reset(space)
                time.sleep(wait)
                continue
            if network:
                raise StudioError(f"Network problem reaching {space}: {text[:120]}. Check the internet connection "
                                  "and run the same command again (finished work is kept).") from e
            if isinstance(e, StudioError):
                raise
            raise explain(e, space) from e


def explain(e: Exception, space: str) -> StudioError:
    msg = str(e)
    m = re.search(r"exceeded your (?:ZeroGPU|GPU) quota \((\d+)s requested vs\. (\d+)s left\)\.?\s*Try again in ([\d:]+)", msg)
    if m or "quota" in msg.lower():
        retry = m.group(3) if m else ""
        hint = "" if config.HF_TOKEN else " Add a free HF_TOKEN to studio/.env to get 5 min/day instead of 2."
        return QuotaError(f"Free GPU quota for today is used up ({m.group(2) + 's left, ' + m.group(1) + 's needed' if m else msg[:120]}). "
                          f"Try again in {retry or 'a few hours'}.{hint}", retry)
    if "sleeping" in msg.lower() or "building" in msg.lower() or "503" in msg:
        return StudioError(f"The Space '{space}' is waking up or rebuilding. Try again in 5-10 minutes.")
    return StudioError(f"Space '{space}' failed: {msg[:500]}")


def save_output(result, out: Path) -> Path:
    """Copy a gradio_client result (path / dict / tuple / gallery) to `out`."""
    def first_path(r):
        if r is None:
            return None
        if isinstance(r, (str, Path)):
            return Path(r) if Path(r).exists() else None
        if isinstance(r, dict):
            for k in ("video", "image", "path", "name"):
                p = first_path(r.get(k))
                if p:
                    return p
            return None
        if isinstance(r, (list, tuple)):
            for x in r:
                p = first_path(x)
                if p:
                    return p
        return None
    p = first_path(result)
    if not p:
        raise StudioError(f"The Space returned no file: {str(result)[:300]}")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".png" and p.suffix.lower() not in (".png",):
        from PIL import Image
        Image.open(p).convert("RGB").save(out)
    else:
        shutil.copy2(p, out)
    return out
