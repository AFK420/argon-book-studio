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

    def import_manifest(
        self,
        book_id: str,
        raw_data: Any,
        manuscript: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Imports and normalizes a manifest JSON file.
        Matches anchor_text against the manuscript paragraphs and supports
        typography_overrides and front_matter / back_matter settings.
        """
        assets_input = []
        typo_overrides = None
        matter_overrides = None

        if isinstance(raw_data, list):
            assets_input = raw_data
        elif isinstance(raw_data, dict):
            if book_id in raw_data and isinstance(raw_data[book_id], dict):
                sub = raw_data[book_id]
                assets_input = sub.get("assets", [])
                typo_overrides = sub.get("typography_overrides") or sub.get("typography")
                matter_overrides = sub.get("front_back_matter") or sub.get("front_matter")
            else:
                assets_input = raw_data.get("assets", [])
                typo_overrides = raw_data.get("typography_overrides") or raw_data.get("typography")
                matter_overrides = raw_data.get("front_back_matter") or raw_data.get("front_matter") or raw_data.get("back_matter")

        normalized_assets: List[Dict[str, Any]] = []
        chapters = manuscript.get("chapters", []) if manuscript else []

        for idx, a in enumerate(assets_input):
            if not isinstance(a, dict):
                continue
            asset_id = str(a.get("id") or a.get("asset_id") or f"{book_id}_asset_{idx+1:02d}")
            title = str(a.get("title") or a.get("name") or asset_id)
            placement = a.get("placement") or "Half-Page Top"
            prompt = str(a.get("prompt") or "")
            caption = str(a.get("caption") or a.get("caption_text") or "")
            caption_pos = str(a.get("caption_position") or "below")
            callouts = a.get("vector_callouts") or a.get("callouts") or []
            frame_style = str(a.get("frame_style") or "none")
            width_pct = int(a.get("width_pct", 100))
            max_height_in = float(a.get("max_height_in", 7.0))
            margin_top_pt = int(a.get("margin_top_pt", 8))
            margin_bottom_pt = int(a.get("margin_bottom_pt", 8))
            image_url = a.get("image_url") or f"/static/assets/placeholders/{asset_id}.png"
            raw_image_path = a.get("raw_image_path")

            # Smart anchor resolution
            anchor = a.get("anchor") or ""
            anchor_text = a.get("anchor_text") or ""
            if str(anchor).upper() in ["END_OF_CHAPTER", "END_OF_SCENE"]:
                anchor_text = anchor

            if anchor_text and chapters:
                clean_text = str(anchor_text).strip()
                target_chapter = a.get("chapter")
                search_chs = chapters
                if target_chapter is not None:
                    try:
                        tch_num = str(int(target_chapter))
                        matched_chs = [c for c in chapters if str(c.get("chapter_number")) == tch_num or str(c.get("chapter_index")) == tch_num]
                        if matched_chs:
                            search_chs = matched_chs
                    except Exception:
                        pass

                if clean_text.upper() in ["END_OF_CHAPTER", "END_OF_SCENE"]:
                    if search_chs and search_chs[0].get("elements"):
                        anchor = search_chs[0]["elements"][-1]["id"]
                else:
                    found_id = None
                    clean_lower = clean_text.lower()
                    for ch in search_chs:
                        for el in ch.get("elements", []):
                            txt = (el.get("text") or el.get("content") or "").lower()
                            if clean_lower in txt:
                                found_id = el.get("id")
                                break
                        if found_id:
                            break
                    if found_id:
                        anchor = found_id

            if not anchor:
                anchor = "ch01_p01"

            norm = {
                "id": asset_id,
                "title": title,
                "anchor": anchor,
                "placement": placement,
                "prompt": prompt,
                "caption": caption,
                "caption_position": caption_pos,
                "image_url": image_url,
                "raw_image_path": raw_image_path,
                "filter_applied": a.get("filter_applied", False),
                "frame_style": frame_style,
                "width_pct": width_pct,
                "max_height_in": max_height_in,
                "margin_top_pt": margin_top_pt,
                "margin_bottom_pt": margin_bottom_pt,
                "vector_callouts": callouts
            }
            normalized_assets.append(norm)

        book = self.get_book_manifest(book_id)
        book["assets"] = normalized_assets
        self.save()

        return {
            "status": "success",
            "assets": normalized_assets,
            "typography_overrides": typo_overrides,
            "front_back_matter": matter_overrides
        }

    def export_manifest(self, book_id: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exports the book manifest, typography settings, and matter configurations as JSON."""
        book = self.get_book_manifest(book_id)
        s = settings or {}
        return {
            "book_id": book_id,
            "version": "2.1",
            "assets": book.get("assets", []),
            "typography_overrides": s.get("typography", {}),
            "front_back_matter": s.get("front_back_matter", {})
        }


manifest_manager = ManifestManager()
