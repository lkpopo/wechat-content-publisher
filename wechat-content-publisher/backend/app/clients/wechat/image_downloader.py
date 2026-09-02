import httpx
import asyncio
from pathlib import Path
from typing import List, Dict

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://mp.weixin.qq.com/",
}


def get_ext_from_url(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.lower()
    if path.endswith(".png"):
        return ".png"
    elif path.endswith(".gif"):
        return ".gif"
    elif path.endswith(".webp"):
        return ".webp"
    return ".jpg"


async def download_images(images: List[Dict], save_dir: Path) -> List[Dict]:
    if not images:
        return []

    save_dir.mkdir(parents=True, exist_ok=True)
    results = []

    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=60.0,
    ) as client:
        tasks = [_download_one(client, img, save_dir) for img in images]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    downloaded = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            downloaded.append({
                "index": images[i]["index"],
                "original_url": images[i]["original_url"],
                "local_path": None,
                "error": str(result),
            })
        else:
            downloaded.append(result)

    return downloaded


async def _download_one(client: httpx.AsyncClient, img: Dict, save_dir: Path) -> Dict:
    idx = img["index"]
    url = img["original_url"]
    ext = get_ext_from_url(url)
    filename = f"image_{idx:03d}{ext}"
    local_path = save_dir / filename

    resp = await client.get(url)
    resp.raise_for_status()
    local_path.write_bytes(resp.content)

    return {
        "index": idx,
        "original_url": url,
        "local_path": str(local_path),
    }
