"""
Argon Book Studio - Manifest Manager.
Manages book_layout_manifest.json and illustration slots anchored to paragraph IDs.
Supports live drag-and-drop re-anchoring, prompt copying, vector callout editing,
and placement configuration.
"""

import json
import os
from typing import Dict, Any, List, Optional

MANIFEST_FILE = os.path.join(os.path.dirname(__file__), "sample_data", "default_manifests.json")
CUSTOM_MANIFEST_FILE = os.path.join(os.path.dirname(__file__), "..", "uploads", "book_layout_manifest.json")


class ManifestManager:
    def __init__(self):
        self.manifest_path = CUSTOM_MANIFEST_FILE if os.path.exists(CUSTOM_MANIFEST_FILE) else MANIFEST_FILE
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # Fallback to default
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(CUSTOM_MANIFEST_FILE), exist_ok=True)
        with open(CUSTOM_MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        self.manifest_path = CUSTOM_MANIFEST_FILE

    def get_book_manifest(self, book_id: str) -> Dict[str, Any]:
        if book_id not in self.data:
            self.data[book_id] = {"book_id": book_id, "assets": []}
        return self.data[book_id]

    def update_anchor(self, book_id: str, asset_id: str, new_anchor: str) -> bool:
        book = self.get_book_manifest(book_id)
        for asset in book.get("assets", []):
            if asset.get("id") == asset_id:
                asset["anchor"] = new_anchor
                self.save()
                return True
        return False

    def update_asset(self, book_id: str, asset_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        book = self.get_book_manifest(book_id)
        for asset in book.get("assets", []):
            if asset.get("id") == asset_id:
                asset.update(updates)
                self.save()
                return asset
        return None

    def add_asset(self, book_id: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        book = self.get_book_manifest(book_id)
        if "id" not in asset_data or not asset_data["id"]:
            asset_data["id"] = f"{book_id}_asset_{len(book.get('assets', [])) + 1:02d}"
        book.setdefault("assets", []).append(asset_data)
        self.save()
        return asset_data

    def delete_asset(self, book_id: str, asset_id: str) -> bool:
        book = self.get_book_manifest(book_id)
        orig_len = len(book.get("assets", []))
        book["assets"] = [a for a in book.get("assets", []) if a.get("id") != asset_id]
        if len(book["assets"]) < orig_len:
            self.save()
            return True
        return False


manifest_manager = ManifestManager()
