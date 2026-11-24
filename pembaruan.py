"""Cek versi terbaru di GitHub Releases (hanya pustaka standar, aman bila offline)."""

import json
import urllib.request

from versi import __versi__, REPO_GITHUB


def _ke_tuple(teks):
    bagian = []
    for p in str(teks).strip().lstrip("vV").split("."):
        digit = "".join(c for c in p if c.isdigit())
        bagian.append(int(digit) if digit else 0)
    return tuple(bagian)


def cek_versi_terbaru(timeout=5):
    """Kembalikan (tag_terbaru, ada_update). (None, False) bila gagal/offline."""
    try:
        url = f"https://api.github.com/repos/{REPO_GITHUB}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "AutomasiNota"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            tag = json.load(r).get("tag_name", "")
        if not tag:
            return None, False
        return tag, _ke_tuple(tag) > _ke_tuple(__versi__)
    except Exception:
        return None, False
