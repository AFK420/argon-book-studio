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

PLACEMENT_NORM_MAP = {
    "full_page_verso": "Full-Page Verso Plate",
    "full_page_recto": "Full-Page Recto Plate",
    "full_bleed_plate": "Full Bleed Plate",
    "half_page_top": "Half-Page Top",
    "half_page_bottom": "Half-Page Bottom",
    "inline_centered": "Inline Archival Insert",
    "inline_archival_insert": "Inline Archival Insert",
    "chapter_header_vignette": "Chapter Opener Vignette",
    "chapter_tailpiece": "Chapter End Tailpiece"
}

FILTER_PRESET_NORM_MAP = {
    "cyanotype_etching": "cyanotype_silver_plate",
    "oscilloscope_phosphor": "blueprint_halftone",
    "sepia_copperplate": "sepia_bioluminescent_amber",
    "terracotta_cuneiform": "desert_ochre_uv"
}

BOOK_DEFAULT_PRESETS = {
    "book01": "cyanotype_silver_plate",
    "book02": "charcoal_lithograph",
    "book03": "blueprint_halftone",
    "book04": "sepia_bioluminescent_amber",
    "book05": "desert_ochre_uv"
}


def normalize_manifest_dict(raw_data: Any, default_book_id: str = "book01") -> Dict[str, Any]:
    """
    Normalizes any manifest structure (dict or malformed list) into a valid dict
    keyed by 'book01'..'book05', and ensures each asset has both naming conventions
    and valid attributes.
    """
    book_dict: Dict[str, Any] = {}

    if isinstance(raw_data, list):
        for item in raw_data:
            if isinstance(item, dict) and item.get("book_id"):
                b_id = item["book_id"]
                book_dict[b_id] = item
    elif isinstance(raw_data, dict):
        if any(k in raw_data for k in ["book01", "book02", "book03", "book04", "book05"]):
            for k, v in raw_data.items():
                if isinstance(v, dict):
                    book_dict[k] = v
        elif "book_id" in raw_data:
            book_dict[raw_data["book_id"]] = raw_data
        elif "assets" in raw_data:
            book_dict[default_book_id] = raw_data

    # Ensure all 5 book keys exist
    for b_id in ["book01", "book02", "book03", "book04", "book05"]:
        if b_id not in book_dict:
            book_dict[b_id] = {"book_id": b_id, "assets": []}

    # Normalize every asset across all books
    for b_id, b_data in book_dict.items():
        if not isinstance(b_data, dict):
            continue
        b_data["book_id"] = b_id
        assets = b_data.get("assets", [])
        if not isinstance(assets, list):
            assets = []
            b_data["assets"] = assets

        norm_assets = []
        for idx, asset in enumerate(assets):
            if not isinstance(asset, dict):
                continue

            # 1. ID normalization (ensure both "id" and "asset_id")
            a_id = str(asset.get("id") or asset.get("asset_id") or f"{b_id}_asset_{idx+1:02d}")
            asset["id"] = a_id
            asset["asset_id"] = a_id

            # 2. Title
            asset["title"] = str(asset.get("title") or asset.get("name") or a_id)

            # 3. Chapter & Anchor
            anchor_text = str(asset.get("anchor_text") or asset.get("anchor") or "ch01_p01")
            asset["anchor_text"] = anchor_text
            raw_anc = asset.get("anchor")
            if raw_anc and str(raw_anc).startswith("ch"):
                asset["anchor"] = str(raw_anc)
            elif anchor_text.startswith("ch"):
                asset["anchor"] = anchor_text
            else:
                asset["anchor"] = "ch01_p01"

            ch_val = asset.get("chapter")
            if ch_val is not None:
                try:
                    asset["chapter"] = int(ch_val)
                except Exception:
                    asset["chapter"] = 1
            else:
                if any(x in anchor_text.upper() for x in ["FRONTISPIECE", "FRONT_MAP"]):
                    asset["chapter"] = 0
                elif asset["anchor"].startswith("ch"):
                    try:
                        asset["chapter"] = int(asset["anchor"].split("_")[0].replace("ch", ""))
                    except Exception:
                        asset["chapter"] = 1
                else:
                    asset["chapter"] = 1

            # 4. Placement normalization
            raw_placement = str(asset.get("placement") or "Half-Page Top").strip()
            placement = PLACEMENT_NORM_MAP.get(raw_placement.lower(), raw_placement)
            if "full-page verso" in placement.lower():
                placement = "Full-Page Verso Plate"
            elif "full-page recto" in placement.lower():
                placement = "Full-Page Recto Plate"
            elif "full bleed" in placement.lower():
                placement = "Full Bleed Plate"
            elif "half-page top" in placement.lower():
                placement = "Half-Page Top"
            elif "half-page bottom" in placement.lower():
                placement = "Half-Page Bottom"
            elif "archival" in placement.lower() or "inline" in placement.lower():
                placement = "Inline Archival Insert"
            elif "opener" in placement.lower() or "vignette" in placement.lower():
                placement = "Chapter Opener Vignette"
            elif "tailpiece" in placement.lower():
                placement = "Chapter End Tailpiece"
            asset["placement"] = placement

            # 5. Caption & Caption Position
            cap = asset.get("caption") if asset.get("caption") is not None else asset.get("caption_text", "")
            asset["caption"] = str(cap)
            asset["caption_text"] = str(cap)
            cap_pos = asset.get("caption_position")
            if not cap_pos:
                cap_pos = "hidden" if "Tailpiece" in placement else "below"
            asset["caption_position"] = str(cap_pos)

            # 6. Frame style
            frame = str(asset.get("frame_style") or "none")
            asset["frame_style"] = frame

            # 7. Width & Max Height
            if "Full" in placement:
                default_w = 100
                default_h = 7.0
            elif "Tailpiece" in placement:
                default_w = 40
                default_h = 2.0
            else:
                default_w = 90
                default_h = 4.0

            asset["width_pct"] = int(asset.get("width_pct") or default_w)
            asset["max_height_in"] = float(asset.get("max_height_in") or default_h)

            # 8. Image URL
            img_url = asset.get("image_url")
            if not img_url:
                if "Vignette" in placement:
                    img_url = f"/static/assets/placeholders/{b_id}_vignette.png"
                elif "Full" in placement:
                    img_url = f"/static/assets/placeholders/{b_id}_fullplate.png"
                elif "Tailpiece" in placement:
                    img_url = f"/static/assets/placeholders/{b_id}_tailpiece.png"
                else:
                    img_url = f"/static/assets/placeholders/{b_id}_halfpage.png"
            asset["image_url"] = img_url

            # 9. Filter preset
            raw_filter = str(asset.get("filter_preset") or BOOK_DEFAULT_PRESETS.get(b_id, "cyanotype_silver_plate"))
            asset["filter_preset"] = FILTER_PRESET_NORM_MAP.get(raw_filter, raw_filter)

            # 10. Vector callouts normalization
            raw_callouts = asset.get("vector_callouts") or asset.get("callouts") or []
            norm_callouts = []
            for c in raw_callouts:
                if isinstance(c, dict):
                    x_val = float(c.get("x_pct", c.get("x", 50.0)))
                    y_val = float(c.get("y_pct", c.get("y", 50.0)))
                    tx_raw = c.get("target_x_pct", c.get("target_x"))
                    ty_raw = c.get("target_y_pct", c.get("target_y"))
                    target_x = float(tx_raw) if tx_raw is not None else None
                    target_y = float(ty_raw) if ty_raw is not None else None
                    lbl = str(c.get("text", c.get("label", "")))
                    c_type = str(c.get("style", c.get("type", "box")))
                    norm_callouts.append({
                        "x": x_val,
                        "y": y_val,
                        "target_x": target_x,
                        "target_y": target_y,
                        "label": lbl,
                        "type": c_type
                    })
            asset["vector_callouts"] = norm_callouts
            asset["callouts"] = norm_callouts

            norm_assets.append(asset)

        b_data["assets"] = norm_assets

    return book_dict


class ManifestManager:
    def __init__(self):
        self.manifest_path = CUSTOM_MANIFEST_FILE if os.path.exists(CUSTOM_MANIFEST_FILE) else MANIFEST_FILE
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        data = None
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        if data is None:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        return normalize_manifest_dict(data, default_book_id="book01")

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
            if asset.get("id") == asset_id or asset.get("asset_id") == asset_id:
                asset["anchor"] = new_anchor
                asset["anchor_text"] = new_anchor
                self.save()
                return True
        return False

    def update_asset(self, book_id: str, asset_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        book = self.get_book_manifest(book_id)
        for asset in book.get("assets", []):
            if asset.get("id") == asset_id or asset.get("asset_id") == asset_id:
                asset.update(updates)
                # Keep both naming conventions aligned
                if "id" in updates:
                    asset["asset_id"] = updates["id"]
                if "asset_id" in updates:
                    asset["id"] = updates["asset_id"]
                if "caption" in updates:
                    asset["caption_text"] = updates["caption"]
                if "caption_text" in updates:
                    asset["caption"] = updates["caption_text"]
                if "vector_callouts" in updates:
                    asset["callouts"] = updates["vector_callouts"]
                if "callouts" in updates:
                    asset["vector_callouts"] = updates["callouts"]
                if "anchor" in updates:
                    asset["anchor_text"] = updates["anchor"]
                self.save()
                return asset
        return None

    def add_asset(self, book_id: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        book = self.get_book_manifest(book_id)
        if "id" not in asset_data or not asset_data["id"]:
            asset_data["id"] = f"{book_id}_asset_{len(book.get('assets', [])) + 1:02d}"
        asset_data["asset_id"] = asset_data["id"]
        book.setdefault("assets", []).append(asset_data)
        self.save()
        return asset_data

    def delete_asset(self, book_id: str, asset_id: str) -> bool:
        book = self.get_book_manifest(book_id)
        orig_len = len(book.get("assets", []))
        book["assets"] = [a for a in book.get("assets", []) if a.get("id") != asset_id and a.get("asset_id") != asset_id]
        if len(book["assets"]) < orig_len:
            self.save()
            return True
        return False

    def bind_anchors_to_manuscript(self, book_id: str, parsed_book: Dict[str, Any]) -> int:
        """
        Iterates over all assets in self.get_book_manifest(book_id)["assets"].
        - If anchor_text is "FRONTISPIECE" or "FRONT_MAP", binds it to "ch01_p01".
        - If anchor_text == "END_OF_CHAPTER", finds the chapter matching asset.get("chapter")
          (or defaults to chapter index) and sets asset["anchor"] to the id of the last paragraph element in that chapter.
        - Otherwise, searches target chapter first (and then all chapters as fallback) for a paragraph
          whose text contains anchor_text (case-insensitive substring match). When found, sets asset["anchor"] = elem["id"].
        - Saves the manifest and returns the number of bound assets.
        """
        book = self.get_book_manifest(book_id)
        assets = book.get("assets", [])
        chapters = parsed_book.get("chapters", []) if parsed_book else []
        if not chapters:
            return 0

        bound_count = 0
        for asset in assets:
            atxt = str(asset.get("anchor_text") or asset.get("anchor") or "").strip()
            ch_target = asset.get("chapter", 1)

            if atxt.upper() in ["FRONTISPIECE", "FRONT_MAP"]:
                asset["anchor"] = "ch01_p01"
                bound_count += 1
                continue

            # Find target chapter
            target_ch = None
            for ch in chapters:
                if ch.get("chapter_number") == ch_target or str(ch.get("chapter_number")) == str(ch_target):
                    target_ch = ch
                    break
            if not target_ch and chapters:
                target_ch = chapters[min(max(0, (ch_target or 1) - 1), len(chapters) - 1)]

            if atxt.upper() in ["END_OF_CHAPTER", "END_OF_SCENE"]:
                if target_ch and target_ch.get("elements"):
                    p_elems = [e for e in target_ch["elements"] if e.get("type") in ["paragraph", "container"]]
                    if p_elems:
                        asset["anchor"] = p_elems[-1]["id"]
                    else:
                        asset["anchor"] = target_ch["elements"][-1]["id"]
                    bound_count += 1
                continue

            # Substring search in target chapter first, then across all chapters
            found_id = None
            clean_lower = atxt.lower()

            if target_ch:
                for el in target_ch.get("elements", []):
                    txt = (el.get("text") or el.get("content") or "").lower()
                    if clean_lower in txt:
                        found_id = el.get("id")
                        break

            if not found_id:
                for ch in chapters:
                    for el in ch.get("elements", []):
                        txt = (el.get("text") or el.get("content") or "").lower()
                        if clean_lower in txt:
                            found_id = el.get("id")
                            break
                    if found_id:
                        break

            if found_id:
                asset["anchor"] = found_id
                bound_count += 1
            else:
                cur_anc = str(asset.get("anchor") or "")
                if not cur_anc.startswith("ch"):
                    fallback_id = None
                    if target_ch and target_ch.get("elements"):
                        p_elems = [e for e in target_ch["elements"] if e.get("type") in ["paragraph", "container"]]
                        fallback_id = p_elems[0]["id"] if p_elems else target_ch["elements"][0]["id"]
                    asset["anchor"] = fallback_id or "ch01_p01"
                    bound_count += 1

        self.save()
        return bound_count

    def import_manifest(
        self,
        book_id: str,
        raw_data: Any,
        manuscript: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Imports and normalizes a manifest JSON file.
        Matches anchor_text against manuscript paragraphs and preserves overrides.
        """
        normalized_data = normalize_manifest_dict(raw_data, default_book_id=book_id)
        imported_book = normalized_data.get(book_id, {"book_id": book_id, "assets": []})

        target_book = self.get_book_manifest(book_id)
        target_book["assets"] = imported_book.get("assets", [])
        self.save()

        if manuscript:
            self.bind_anchors_to_manuscript(book_id, manuscript)

        return {
            "status": "success",
            "assets": target_book.get("assets", []),
            "typography_overrides": imported_book.get("typography_overrides") or imported_book.get("typography"),
            "front_back_matter": imported_book.get("front_back_matter") or imported_book.get("front_matter")
        }

    def export_manifest(self, book_id: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exports the book manifest, typography settings, and matter configurations as JSON."""
        book = self.get_book_manifest(book_id)
        s = settings or {}
        return {
            "book_id": book_id,
            "version": "2.3",
            "assets": book.get("assets", []),
            "typography_overrides": s.get("typography", {}),
            "front_back_matter": s.get("front_back_matter", {})
        }


manifest_manager = ManifestManager()
