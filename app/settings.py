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
    
    body_size = float(profile["body_font_size"].replace("pt", ""))
    body_leading = float(profile["body_leading"].replace("pt", ""))
    line_height = round(body_leading / body_size, 2)
    
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
            "body_font_size_pt": body_size,
            "font_size_pt": body_size,
            "body_leading_pt": body_leading,
            "line_height": line_height,
            "display_font_name": profile["display_font_name"],
            "display_font": profile["display_font"],
            "heading_font_name": profile["display_font_name"],
            "heading_font": profile["display_font"],
            "mono_font_name": profile.get("mono_font_name", "JetBrains Mono"),
            "mono_font": profile.get("mono_font", "'JetBrains Mono', 'Courier New', monospace"),
            "first_p_indent_in": specs["grid_rules"]["first_p_indent_in"],
            "subsequent_p_indent_in": specs["grid_rules"]["subsequent_p_indent_in"],
            "para_indent_in": specs["grid_rules"]["subsequent_p_indent_in"],
            "para_spacing_pt": 0.0,
            "letter_spacing_em": 0.0,
            "justify_text": True,
            "hyphenation": True,
            "chapter_sinkage_in": specs["grid_rules"]["chapter_sinkage_in"],
            "drop_cap_enabled": profile.get("drop_cap_type", "Plain Serif") != "None",
            "drop_cap_lines": profile.get("drop_cap_lines", 3),
            "drop_cap_style": profile.get("drop_cap_type", "Plain Serif"),
            "running_header_style": "Small Caps Centered",
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
            "include_map": False,
            "map_title": "Archival Chart & Survey Map",
            "map_caption": "Hydrographic Soundings & Survey of the Ghyll Skerries.",
            "include_acknowledgements": False,
            "acknowledgements_text": "With special gratitude to the archivists and epigraphers whose field diaries provided foundational technical references.",
            "include_appendix": False,
            "appendix_title": "Appendix: Chronometric & Forensic Telemetry",
            "appendix_text": "Calibration logs recorded at 14-minute intervals following the barometric depression.",
            "include_glossary": False,
            "glossary_title": "Glossary of Technical & In-World Terms",
            "glossary_terms": [
                {"term": "Barometer Skerry", "definition": "A sub-surface basalt reef producing localized micro-baric fluctuations."},
                {"term": "Vesper Draw", "definition": "An occult sensory distillation utilizing mercury and sea-salt."}
            ],
            "include_about_author": False,
            "about_author_text": "The authors and artists of Argon Studio specialize in archaeometric thrillers and illustrated fine book design.",
            "include_colophon": True,
            "colophon_headline": "A NOTE ON THE TYPE AND PRODUCTION",
            "colophon_text": "",
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
                
        # Synchronize typography and margin aliases
        typo = current.setdefault("typography", {})
        if "font_size_pt" in updates:
            typo["font_size_pt"] = float(updates["font_size_pt"])
            typo["body_font_size_pt"] = typo["font_size_pt"]
        elif "body_font_size_pt" in typo:
            typo["font_size_pt"] = float(typo["body_font_size_pt"])
            
        if "line_height" in updates:
            typo["line_height"] = float(updates["line_height"])
            base_size = typo.get("font_size_pt", 11.0)
            typo["body_leading_pt"] = round(base_size * typo["line_height"], 1)
        elif "body_leading_pt" in typo and "line_height" not in typo:
            base_size = typo.get("font_size_pt", 11.0)
            typo["line_height"] = round(float(typo["body_leading_pt"]) / base_size, 2)

        if "para_indent_in" in updates:
            typo["para_indent_in"] = float(updates["para_indent_in"])
            typo["subsequent_p_indent_in"] = typo["para_indent_in"]
        elif "subsequent_p_indent_in" in typo:
            typo["para_indent_in"] = float(typo["subsequent_p_indent_in"])

        # Preset sync
        if "trim_preset" in updates and updates["trim_preset"] in DEFAULT_TRIM_PRESETS:
            preset = DEFAULT_TRIM_PRESETS[updates["trim_preset"]]
            current["trim_width_in"] = preset["trim_width_in"]
            current["trim_height_in"] = preset["trim_height_in"]

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
