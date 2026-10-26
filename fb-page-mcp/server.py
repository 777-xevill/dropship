"""Facebook Page MCP (local files -> Page posts). Needs FACEBOOK_PAGE_TOKEN and FACEBOOK_PAGE_ID in .env next to this file."""
import os
from pathlib import Path

import requests
from mcp.server.fastmcp import FastMCP

HERE = Path(__file__).parent
for line in (HERE / ".env").read_text(encoding="utf-8").splitlines() if (HERE / ".env").exists() else []:
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

V = "v21.0"
G = f"https://graph.facebook.com/{V}"
GV = f"https://graph-video.facebook.com/{V}"
mcp = FastMCP("facebook-page")


def _cfg():
    t, p = os.environ.get("FACEBOOK_PAGE_TOKEN"), os.environ.get("FACEBOOK_PAGE_ID")
    if not t or not p:
        raise RuntimeError("Set FACEBOOK_PAGE_TOKEN and FACEBOOK_PAGE_ID in fb-page-mcp/.env")
    return t, p


def _out(r):
    j = r.json()
    if r.status_code >= 400 or "error" in j:
        raise RuntimeError(str(j.get("error", j))[:500])
    return j


@mcp.tool()
def post_text(message: str, link: str = "") -> dict:
    """Publish a text post (optional link) to the Page."""
    t, p = _cfg()
    d = {"message": message, "access_token": t}
    if link:
        d["link"] = link
    return _out(requests.post(f"{G}/{p}/feed", data=d, timeout=60))


@mcp.tool()
def post_photo(file_path: str, caption: str = "", published: bool = True) -> dict:
    """Publish a local image file to the Page with a caption. published=false uploads without posting (use for multi-photo posts)."""
    t, p = _cfg()
    with open(file_path, "rb") as f:
        return _out(requests.post(f"{G}/{p}/photos", data={"caption": caption, "published": str(published).lower(), "access_token": t},
                                  files={"source": f}, timeout=300))


@mcp.tool()
def post_photos(file_paths: list[str], message: str = "") -> dict:
    """Publish several local images as ONE post."""
    t, p = _cfg()
    ids = []
    for fp in file_paths:
        ids.append(post_photo(fp, published=False)["id"])
    import json
    d = {"message": message, "access_token": t}
    for i, pid in enumerate(ids):
        d[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    return _out(requests.post(f"{G}/{p}/feed", data=d, timeout=60))


@mcp.tool()
def post_video(file_path: str, description: str = "", title: str = "") -> dict:
    """Publish a local video file (mp4) to the Page."""
    t, p = _cfg()
    with open(file_path, "rb") as f:
        return _out(requests.post(f"{GV}/{p}/videos", data={"description": description, "title": title, "access_token": t},
                                  files={"source": f}, timeout=1800))


@mcp.tool()
def get_posts(limit: int = 10) -> dict:
    """Recent Page posts with ids, time, text and permalinks."""
    t, p = _cfg()
    return _out(requests.get(f"{G}/{p}/posts", params={"limit": limit, "fields": "id,created_time,message,permalink_url", "access_token": t}, timeout=60))


@mcp.tool()
def edit_post(post_id: str, message: str) -> dict:
    """Change the text/caption of a post."""
    t, _ = _cfg()
    return _out(requests.post(f"{G}/{post_id}", data={"message": message, "access_token": t}, timeout=60))


@mcp.tool()
def delete_post(post_id: str) -> dict:
    """Delete a post (cannot be undone)."""
    t, _ = _cfg()
    return _out(requests.delete(f"{G}/{post_id}", params={"access_token": t}, timeout=60))


@mcp.tool()
def get_comments(post_id: str, limit: int = 25) -> dict:
    """Comments on a post."""
    t, _ = _cfg()
    return _out(requests.get(f"{G}/{post_id}/comments", params={"limit": limit, "fields": "id,from,message,created_time", "access_token": t}, timeout=60))


@mcp.tool()
def reply_comment(comment_id: str, message: str) -> dict:
    """Reply to a comment as the Page."""
    t, _ = _cfg()
    return _out(requests.post(f"{G}/{comment_id}/comments", data={"message": message, "access_token": t}, timeout=60))


@mcp.tool()
def page_info() -> dict:
    """Page name, followers and fan count (also checks that the token works)."""
    t, p = _cfg()
    return _out(requests.get(f"{G}/{p}", params={"fields": "id,name,fan_count,followers_count,link", "access_token": t}, timeout=60))


if __name__ == "__main__":
    mcp.run()
