"""
Argon Book Studio - Project Settings & Geometry Configuration Manager.
Stores and persists live typesetting geometry, margins, typography,
front/back matter flags, and image lab parameters per book.
"""

import json
import os
from typing import Dict, Any, Optional
from app.profiles import BOOK_PROFILES, UNIVERSAL_PUBLISHING_SPECS

SETTINGS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "settings")
os.makedirs(SETTINGS_DIR, exist_ok=True)

DEFAULT_TRIM_PRESETS = {
    "6x9": {"trim_width_in": 6.0, "trim_height_in": 9.0, "label": "6.0\" x 9.0\" (Standard US Trade / Novel)"},
    "5.5x8.5": {"trim_width_in": 5.5, "trim_height_in": 8.5, "label": "5.5\" x 8.5\" (Digest / Compact Trade)"},
    "5x8": {"trim_width_in": 5.0, "trim_height_in": 8.0, "label": "5.0\" x 8.0\" (Pocket Fiction)"},
    "7x10": {"trim_width_in": 7.0, "trim_height_in": 10.0, "label": "7.0\" x 10.0\" (Executive / Illustrated Plate)"},
    "custom": {"trim_width_in": 6.0, "trim_height_in": 9.0, "label": "Custom Trim Size"}
}


def get_default_settings_for_book(book_id: str) -> Dict[str, Any]:
    profile = BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"])
    specs = UNIVERSAL_PUBLISHING_SPECS
    
    return {
        "book_id": book_id,
        "trim_preset": "6x9",
        "trim_width_in": specs["trim_width_in"],
        "trim_height_in": specs["trim_height_in"],
        "bleed_in": specs["bleed_in"],
        "margins": {
            "inside_gutter_in": specs["margins"]["inside_gutter_in"],
            "outside_margin_in": specs["margins"]["outside_margin_in"],
            "top_margin_in": specs["margins"]["top_margin_in"],
            "bottom_margin_in": specs["margins"]["bottom_margin_in"],
        },
        "typography": {
            "body_font_name": profile["body_font_name"],
            "body_font": profile["body_font"],
            "body_font_size_pt": float(profile["body_font_size"].replace("pt", "")),
            "body_leading_pt": float(profile["body_leading"].replace("pt", "")),
            "display_font_name": profile["display_font_name"],
            "display_font": profile["display_font"],
            "first_p_indent_in": specs["grid_rules"]["first_p_indent_in"],
            "subsequent_p_indent_in": specs["grid_rules"]["subsequent_p_indent_in"],
            "chapter_sinkage_in": specs["grid_rules"]["chapter_sinkage_in"],
            "running_header_font_size_pt": specs["grid_rules"]["running_header_font_size_pt"],
            "accent_color": profile["accent_color"],
            "brass_accent": profile["brass_accent"],
            "paper_tint": profile["paper_tint"],
            "running_header_override": "",
            "running_header_tracking_em": 0.14,
            "suppress_headers_on_openers": True
        },
        "front_back_matter": {
            "include_half_title": True,
            "include_frontispiece": True,
            "include_title_page": True,
            "include_copyright": True,
            "include_dedication": False,
            "dedication_text": "To those who seek truth in the silence between notes.",
            "include_epigraph": False,
            "epigraph_text": "The sea does not surrender its dead, nor does the stone forget.",
            "epigraph_source": "— Port Assayer's Chronicle, 1844",
            "include_toc": True,
            "include_acknowledgements": False,
            "acknowledgements_text": "With special gratitude to the archivists and epigraphers whose field diaries provided foundational technical references.",
            "include_about_author": False,
            "about_author_text": "The authors and artists of Argon Studio specialize in archaeometric thrillers and illustrated fine book design.",
            "include_colophon": True,
            "colophon_headline": "A NOTE ON THE TYPE AND PRODUCTION",
            "publisher_imprint": "THE ARGON BOOK STUDIO • PRESS",
            "city": "London & San Francisco",
            "isbn_hardcover": "978-1-954321-01-9",
            "isbn_epub": "978-1-954321-02-6"
        },
        "image_lab": {
            "filter_preset": profile.get("filter_preset", "cyanotype_silver_plate"),
            "grain_intensity": 0.08,
            "contrast": 1.35,
            "vignette_strength": 0.38,
            "brightness": 1.0,
            "target_dpi": 300
        }
    }


class ProjectSettingsManager:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}

    def _file_path(self, book_id: str) -> str:
        return os.path.join(SETTINGS_DIR, f"{book_id}_settings.json")

    def get_settings(self, book_id: str) -> Dict[str, Any]:
        if book_id in self.cache:
            return self.cache[book_id]
            
        fpath = self._file_path(book_id)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cache[book_id] = data
                    return data
            except Exception:
                pass
                
        default = get_default_settings_for_book(book_id)
        self.cache[book_id] = default
        return default

    def update_settings(self, book_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_settings(book_id)
        
        # Deep merge
        for k, v in updates.items():
            if isinstance(v, dict) and k in current and isinstance(current[k], dict):
                current[k].update(v)
            else:
                current[k] = v
                
        self.cache[book_id] = current
        
        # Save to disk
        try:
            with open(self._file_path(book_id), "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
        except Exception as e:
            print(f"Error saving settings for {book_id}: {e}")
            
        return current

    def reset_settings(self, book_id: str) -> Dict[str, Any]:
        default = get_default_settings_for_book(book_id)
        self.cache[book_id] = default
        fpath = self._file_path(book_id)
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass
        return default


settings_manager = ProjectSettingsManager()
