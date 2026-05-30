"""Persistent cache of YC-slug -> resolved ATS, so re-runs skip slow probing."""
import json
import os


class SlugCache:
    """Tiny JSON-backed dict: yc_slug -> {"ats", "ats_slug"} or {"ats": None}."""

    def __init__(self, path=".yc_ats_cache.json"):
        self.path = path
        self._data = {}
        self._dirty = False
        if path and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    self._data = json.load(f)
            except (ValueError, OSError):
                self._data = {}

    def get(self, slug):
        return self._data.get(slug)

    def set(self, slug, ats, ats_slug):
        self._data[slug] = {"ats": ats, "ats_slug": ats_slug}
        self._dirty = True

    def save(self):
        if not self.path or not self._dirty:
            return
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
        self._dirty = False
