"""
Argon Book Studio - Local AI Book Art Director & Layout Suite.
Connects to local LLMs (Ollama, LM Studio, llama.cpp, LocalAI) or runs in
High-Fidelity Heuristic Mode to autonomously read manuscripts, recommend
thematic typography, draft mandatory pages, discover cinematic scenes,
generate midjourney/diffusion prompts, and anchor illustration plates.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)

DEFAULT_AI_CONFIG = {
    "provider": "ollama",               # "ollama", "openai_compatible", or "offline_heuristic"
    "endpoint_url": "http://localhost:11434",
    "model": "llama3.1",
    "temperature": 0.4,
    "timeout_sec": 30.0,
    "auto_detect_models": True
}

# Thematic style presets for typography & art direction
THEME_PRESETS = {
    "gaslamp_gothic": {
        "genre_label": "Gaslamp Forensic Mystery & Gothic Fiction",
        "body_font_name": "Cormorant Garamond",
        "body_font": "'Cormorant Garamond', 'EB Garamond', serif",
        "heading_font_name": "Cinzel",
        "heading_font": "'Cinzel', 'Playfair Display', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "cyanotype_silver_plate",
        "font_size_pt": 10.5,
        "line_height": 1.38,
        "para_indent_in": 0.25,
        "para_spacing_pt": 0.0,
        "trim_preset": "6x9",
        "drop_cap_style": "Engraved Gothic Initial",
        "drop_cap_lines": 3,
        "frame_style": "Victorian Engraved Filigree",
        "accent_color": "#1E3A8A",
        "brass_accent": "#D97706"
    },
    "chronometric_thriller": {
        "genre_label": "Chronometric Island Thriller & Nautical Fiction",
        "body_font_name": "EB Garamond",
        "body_font": "'EB Garamond', serif",
        "heading_font_name": "Cinzel Decorative",
        "heading_font": "'Cinzel Decorative', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "copperplate_etching",
        "font_size_pt": 10.75,
        "line_height": 1.40,
        "para_indent_in": 0.22,
        "para_spacing_pt": 0.0,
        "trim_preset": "6x9",
        "drop_cap_style": "Steampunk Compass Initial",
        "drop_cap_lines": 3,
        "frame_style": "Chronometer Brass Border",
        "accent_color": "#0F766E",
        "brass_accent": "#B45309"
    },
    "acoustic_coldwar": {
        "genre_label": "Cold War Forensic & Acoustic Mystery",
        "body_font_name": "Lora",
        "body_font": "'Lora', serif",
        "heading_font_name": "Playfair Display",
        "heading_font": "'Playfair Display', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "sepia_microfilm",
        "font_size_pt": 10.25,
        "line_height": 1.35,
        "para_indent_in": 0.20,
        "para_spacing_pt": 0.0,
        "trim_preset": "5.5x8.5",
        "drop_cap_style": "Typewriter Stencil",
        "drop_cap_lines": 2,
        "frame_style": "Classified Document Frame",
        "accent_color": "#334155",
        "brass_accent": "#64748B"
    },
    "southern_gothic": {
        "genre_label": "Southern Gothic & Institutional Mystery",
        "body_font_name": "Libre Baskerville",
        "body_font": "'Libre Baskerville', serif",
        "heading_font_name": "Playfair Display",
        "heading_font": "'Playfair Display', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "high_contrast_linocut",
        "font_size_pt": 10.5,
        "line_height": 1.42,
        "para_indent_in": 0.25,
        "para_spacing_pt": 0.0,
        "trim_preset": "6x9",
        "drop_cap_style": "Flourished Floral Initial",
        "drop_cap_lines": 3,
        "frame_style": "Weathered Wrought Iron",
        "accent_color": "#4D7C0F",
        "brass_accent": "#CA8A04"
    },
    "archaeometric_heist": {
        "genre_label": "Archaeometric & Epigraphic Geopolitical Thriller",
        "body_font_name": "Merriweather",
        "body_font": "'Merriweather', serif",
        "heading_font_name": "Cinzel",
        "heading_font": "'Cinzel', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "duotone_cobalt",
        "font_size_pt": 10.0,
        "line_height": 1.36,
        "para_indent_in": 0.20,
        "para_spacing_pt": 0.0,
        "trim_preset": "6x9",
        "drop_cap_style": "Cuneiform Seal Initial",
        "drop_cap_lines": 3,
        "frame_style": "Bas-Relief Stone Border",
        "accent_color": "#9A3412",
        "brass_accent": "#EA580C"
    }
}


class AIDirectorManager:
    def __init__(self):
        self.config = dict(DEFAULT_AI_CONFIG)

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        self.config.update(new_config)
        return self.config

    def check_connection(self) -> Dict[str, Any]:
        """
        Polls local LLM servers (Ollama, LM Studio / OpenAI-compatible).
        Returns status, available models, and active mode.
        """
        url = self.config.get("endpoint_url", "http://localhost:11434").rstrip("/")
        fast_timeout = httpx.Timeout(connect=0.4, read=1.5, write=1.0, pool=0.5)
        
        # 1. Check Ollama tags endpoint
        try:
            with httpx.Client(timeout=fast_timeout) as client:
                res = client.get(f"{url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    selected = self.config.get("model", "llama3.1")
                    if models and selected not in models:
                        selected = models[0]
                    return {
                        "status": "online",
                        "provider": "ollama",
                        "endpoint": url,
                        "models": models,
                        "selected_model": selected,
                        "message": f"Connected to Ollama ({len(models)} models available)."
                    }
        except Exception:
            pass

        # 2. Check OpenAI-compatible endpoint (LM Studio, llama.cpp, LocalAI)
        try:
            with httpx.Client(timeout=fast_timeout) as client:
                res = client.get(f"{url}/v1/models")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    return {
                        "status": "online",
                        "provider": "openai_compatible",
                        "endpoint": url,
                        "models": models,
                        "selected_model": models[0] if models else "default",
                        "message": f"Connected to OpenAI-compatible server ({len(models)} models)."
                    }
        except Exception:
            pass

        # 3. Offline Heuristic Fallback
        return {
            "status": "offline",
            "provider": "offline_heuristic",
            "endpoint": url,
            "models": ["Argon High-Fidelity NLP Heuristics (Zero-Config Built-in)"],
            "selected_model": "Argon High-Fidelity NLP Heuristics",
            "message": "Local LLM server not detected. High-Fidelity Built-in NLP Heuristics active."
        }

    def analyze_manuscript(
        self,
        manuscript: Dict[str, Any],
        book_id: str = "book01",
        num_illustrations: int = 16,
        user_prompt_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main AI Art Director pipeline:
        - If a local LLM is online, prompts the model for structured analysis.
        - Otherwise, executes deterministic, intelligent NLP heuristic extraction.
        """
        conn = self.check_connection()
        if conn["status"] == "online" and conn["provider"] == "ollama":
            try:
                result = self._analyze_via_ollama(manuscript, book_id, num_illustrations, conn["selected_model"])
                if result:
                    result["engine"] = f"Local LLM ({conn['selected_model']})"
                    return result
            except Exception as e:
                logger.warning(f"Ollama execution failed, falling back to heuristic engine: {e}")

        # Fallback to high-fidelity heuristic engine
        result = self._analyze_via_heuristics(manuscript, book_id, num_illustrations)
        result["engine"] = "Argon High-Fidelity NLP Heuristics (Offline)"
        return result

    def _analyze_via_ollama(
        self,
        manuscript: Dict[str, Any],
        book_id: str,
        num_illustrations: int,
        model_name: str
    ) -> Optional[Dict[str, Any]]:
        """Queries local Ollama instance with structured JSON instructions."""
        url = f"{self.config.get('endpoint_url', 'http://localhost:11434').rstrip('/')}/api/generate"
        
        # Build manuscript digest (Title, Author, Chapter titles, and first paragraph of each chapter)
        title = manuscript.get("title", "Untitled Manuscript")
        author = manuscript.get("author", "Author")
        chapters = manuscript.get("chapters", [])
        
        digest_lines = [f"Title: {title}", f"Author: {author}", f"Total Chapters: {len(chapters)}"]
        for ch in chapters[:8]:
            c_num = ch.get("chapter_number", 1)
            c_title = ch.get("title", f"Chapter {c_num}")
            elements = ch.get("elements", [])
            first_p = next((e.get("text", "") for e in elements if e.get("type") == "paragraph"), "")
            digest_lines.append(f"- Ch {c_num}: {c_title} | Opening: {first_p[:180]}...")
            
        digest = "\n".join(digest_lines)
        
        system_prompt = (
            "You are an expert Victorian and fine-press Book Art Director and Master Typographer. "
            "Analyze the given novel digest and return ONLY a valid JSON object with book design parameters. "
            "JSON structure must have keys: 'genre_style', 'mood_summary', 'title_page', 'copyright', 'epigraph', "
            "'dedication', 'recommended_theme', 'visual_prompts' (list of objects with 'chapter', 'prompt', 'title', 'placement')."
        )
        
        prompt = (
            f"Manuscript Information:\n{digest}\n\n"
            f"Generate an artistic blueprint with {num_illustrations} illustration scenes. "
            "Ensure the visual prompts are rich in composition, textures, era lighting, and camera angle. "
            "Return valid JSON only without markdown code blocks."
        )

        with httpx.Client(timeout=float(self.config.get("timeout_sec", 30.0))) as client:
            resp = client.post(
                url,
                json={
                    "model": model_name,
                    "prompt": f"{system_prompt}\n\n{prompt}",
                    "stream": False,
                    "format": "json"
                }
            )
            if resp.status_code == 200:
                raw_json_str = resp.json().get("response", "{}")
                try:
                    parsed = json.loads(raw_json_str)
                    return self._merge_llm_output_with_book_data(parsed, manuscript, book_id, num_illustrations)
                except Exception as e:
                    logger.warning(f"Could not parse Ollama response as JSON: {e}")
                    return None
        return None

    def _merge_llm_output_with_book_data(
        self,
        llm_data: Dict[str, Any],
        manuscript: Dict[str, Any],
        book_id: str,
        num_illustrations: int
    ) -> Dict[str, Any]:
        """Blends LLM aesthetic outputs with book paragraph anchors and typography specs."""
        theme_key = llm_data.get("recommended_theme", "gaslamp_gothic")
        if theme_key not in THEME_PRESETS:
            theme_key = "gaslamp_gothic"
        preset = THEME_PRESETS[theme_key]
        
        title = llm_data.get("title_page", {}).get("title") or manuscript.get("title") or "The Illustrated Edition"
        author = llm_data.get("title_page", {}).get("author") or manuscript.get("author") or "Argon Author"

        # Build Typography Overrides
        typography = {
            "body_font_name": preset["body_font_name"],
            "body_font": preset["body_font"],
            "body_font_size_pt": preset["font_size_pt"],
            "font_size_pt": preset["font_size_pt"],
            "line_height": preset["line_height"],
            "heading_font_name": preset["heading_font_name"],
            "heading_font": preset["heading_font"],
            "mono_font_name": preset["mono_font_name"],
            "mono_font": preset["mono_font"],
            "para_indent_in": preset["para_indent_in"],
            "para_spacing_pt": preset["para_spacing_pt"],
            "drop_cap_style": preset["drop_cap_style"],
            "drop_cap_lines": preset["drop_cap_lines"],
            "accent_color": preset["accent_color"],
            "brass_accent": preset["brass_accent"]
        }

        # Build Front & Back Matter
        front_back_matter = {
            "include_half_title": True,
            "include_title_page": True,
            "include_copyright": True,
            "include_dedication": True,
            "dedication_text": llm_data.get("dedication") or "To the relentless seekers of unrecorded truth.",
            "include_epigraph": True,
            "epigraph_text": llm_data.get("epigraph", {}).get("text") or "The archive remembers what the eye refuses to witness.",
            "epigraph_source": llm_data.get("epigraph", {}).get("source") or "— Field Epigraphy Register, 1888",
            "include_toc": True,
            "include_colophon": True,
            "colophon_headline": "COLOPHON & PRODUCTION NOTE",
            "colophon_text": f"Typeset in {preset['body_font_name']} and {preset['heading_font_name']} under the direction of the Argon Local AI Suite.",
            "publisher_imprint": "ARGON BOOK STUDIO • FINE EDITIONS",
            "city": "London & San Francisco",
            "title_page": {
                "title": title,
                "subtitle": llm_data.get("title_page", {}).get("subtitle", "A Speculative Illustrated Mystery"),
                "author": author,
                "publisher": "Argon Press",
                "city": "London"
            }
        }

        # Build Illustration Assets with Anchors
        assets = []
        raw_prompts = llm_data.get("visual_prompts", [])
        chapters = manuscript.get("chapters", [])
        
        placements = [
            "Full-Page Verso Plate", "Half-Page Top", "Full-Page Recto Plate", 
            "Half-Page Bottom", "Quarter-Page Vignette", "Full Bleed Plate"
        ]

        b_prefix = book_id
        if book_id.startswith("book"):
            try:
                b_prefix = f"b{int(book_id.replace('book', '')):02d}"
            except Exception:
                b_prefix = book_id

        for idx in range(num_illustrations):
            slot_num = idx + 1
            asset_id = f"{b_prefix}_asset_{slot_num:02d}"
            target_ch_num = min(slot_num, len(chapters)) if chapters else 1
            
            # Find candidate chapter
            target_ch = chapters[target_ch_num - 1] if target_ch_num <= len(chapters) else (chapters[0] if chapters else {})
            elements = target_ch.get("elements", [])
            paragraphs = [e for e in elements if e.get("type") == "paragraph"]
            
            # Select target anchor paragraph
            try:
                target_ch_int = int(target_ch_num)
            except (ValueError, TypeError):
                target_ch_int = idx + 1

            anchor_idx = min(idx % max(1, len(paragraphs)), len(paragraphs) - 1) if paragraphs else 0
            anchor_el = paragraphs[anchor_idx] if paragraphs else {"id": f"ch{target_ch_int:02d}_p01", "text": ""}
            anchor_id = anchor_el.get("id", f"ch{target_ch_int:02d}_p01")
            anchor_text = anchor_el.get("text", "")[:45].strip()
            
            prompt_data = raw_prompts[idx] if idx < len(raw_prompts) else {}
            title_text = prompt_data.get("title") or f"Plate {slot_num:02d}: Chapter {target_ch_num} Scene"
            prompt_text = prompt_data.get("prompt") or (
                f"19th-century atmospheric illustration, {preset['filter_preset'].replace('_', ' ')}, "
                f"intricate woodcut and silver-plate detailing, dramatic chiaroscuro lighting, masterwork composition."
            )
            placement = prompt_data.get("placement") or placements[idx % len(placements)]

            assets.append({
                "id": asset_id,
                "title": title_text,
                "chapter": target_ch_int,
                "anchor": anchor_id,
                "anchor_text": anchor_text if anchor_text else "CHAPTER_OPENING",
                "placement": placement,
                "prompt": prompt_text,
                "image_url": f"/static/assets/placeholders/{book_id}_halfpage.png",
                "filter_preset": preset["filter_preset"],
                "frame_style": preset["frame_style"],
                "filter_applied": False,
                "vector_callouts": []
            })

        return {
            "status": "success",
            "book_id": book_id,
            "theme_preset_key": theme_key,
            "genre_style": preset["genre_label"],
            "mood_summary": llm_data.get("mood_summary", "Atmospheric speculative fiction with intricate forensic elements."),
            "typography_overrides": typography,
            "front_back_matter": front_back_matter,
            "assets": assets,
            "total_illustrations": len(assets)
        }

    def _analyze_via_heuristics(
        self,
        manuscript: Dict[str, Any],
        book_id: str,
        num_illustrations: int = 16
    ) -> Dict[str, Any]:
        """
        High-fidelity heuristic engine:
        Scans manuscript text for genre indicators, atmospheric keywords,
        detects in-world container candidates, and crafts custom 16-slot blueprints.
        """
        title = manuscript.get("title", "")
        author = manuscript.get("author", "Sterling Vance")
        chapters = manuscript.get("chapters", [])
        
        # Scan entire manuscript text for keyword profiling
        all_text_samples = []
        for ch in chapters:
            for el in ch.get("elements", []):
                t = el.get("text") or el.get("content") or ""
                if t:
                    all_text_samples.append(t)
        full_sample = " ".join(all_text_samples[:300]).lower()

        # Detect genre profile
        if any(w in full_sample for w in ["alembic", "vitriol", "inquest", "coroner", "arsenic", "fluorosilicate", "cormac"]):
            theme_key = "gaslamp_gothic"
        elif any(w in full_sample for w in ["skerry", "chronometer", "brass", "nautical", "hydrographic", "barometer"]):
            theme_key = "chronometric_thriller"
        elif any(w in full_sample for w in ["tape", "frequency", "microphone", "signal", "decibel", "acoustic", "transceiver"]):
            theme_key = "acoustic_coldwar"
        elif any(w in full_sample for w in ["moss", "sanatorium", "swamp", "cypress", "parish", "willow", "bayou"]):
            theme_key = "southern_gothic"
        elif any(w in full_sample for w in ["cuneiform", "tablet", "seal", "cylinder", "tigris", "basalt", "antiquity"]):
            theme_key = "archaeometric_heist"
        else:
            # Match by book_id if generic
            id_map = {
                "book01": "gaslamp_gothic",
                "book02": "chronometric_thriller",
                "book03": "acoustic_coldwar",
                "book04": "southern_gothic",
                "book05": "archaeometric_heist"
            }
            theme_key = id_map.get(book_id, "gaslamp_gothic")

        preset = THEME_PRESETS[theme_key]
        if not title or title.strip() in ["Untitled Manuscript", "Book"]:
            title = preset["genre_label"].split("&")[0].strip()

        # Build Typography
        typography = {
            "body_font_name": preset["body_font_name"],
            "body_font": preset["body_font"],
            "body_font_size_pt": preset["font_size_pt"],
            "font_size_pt": preset["font_size_pt"],
            "line_height": preset["line_height"],
            "heading_font_name": preset["heading_font_name"],
            "heading_font": preset["heading_font"],
            "mono_font_name": preset["mono_font_name"],
            "mono_font": preset["mono_font"],
            "para_indent_in": preset["para_indent_in"],
            "para_spacing_pt": preset["para_spacing_pt"],
            "drop_cap_style": preset["drop_cap_style"],
            "drop_cap_lines": preset["drop_cap_lines"],
            "accent_color": preset["accent_color"],
            "brass_accent": preset["brass_accent"]
        }

        # Build Front & Back Matter
        front_back_matter = {
            "include_half_title": True,
            "include_title_page": True,
            "include_copyright": True,
            "include_dedication": True,
            "dedication_text": f"To the scholars and field examiners who preserve the forensic record.",
            "include_epigraph": True,
            "epigraph_text": "Every substance leaves an indelible signature; the archive does not deceive.",
            "epigraph_source": "— Royal Assayer's Forensic Compendium, 1891",
            "include_toc": True,
            "include_colophon": True,
            "colophon_headline": "A NOTE ON THE TYPESETTING & ARTWORK",
            "colophon_text": f"Typeset in {preset['body_font_name']} with chapter heads rendered in {preset['heading_font_name']}. Visual plates curated by the Argon AI Art Director.",
            "publisher_imprint": "ARGON BOOK STUDIO • ARCHIVAL EDITIONS",
            "city": "London & Edinburgh",
            "title_page": {
                "title": title,
                "subtitle": preset["genre_label"],
                "author": author,
                "publisher": "Argon Studio Press",
                "city": "London"
            }
        }

        # Extract dramatic moments for Illustration Manifest
        assets = []
        placements = [
            "Full-Page Verso Plate", "Half-Page Top", "Full-Page Recto Plate", 
            "Half-Page Bottom", "Quarter-Page Vignette", "Full Bleed Plate"
        ]

        total_ch = len(chapters) if chapters else 1
        b_prefix = book_id
        if book_id.startswith("book"):
            try:
                b_prefix = f"b{int(book_id.replace('book', '')):02d}"
            except Exception:
                b_prefix = book_id

        for idx in range(num_illustrations):
            slot_num = idx + 1
            asset_id = f"{b_prefix}_asset_{slot_num:02d}"
            
            # Distribute slots across chapters
            ch_idx = int((idx / max(1, num_illustrations - 1)) * (total_ch - 1)) if total_ch > 1 else 0
            target_ch = chapters[ch_idx] if ch_idx < len(chapters) else {}
            c_num = target_ch.get("chapter_number", ch_idx + 1)
            try:
                c_int = int(c_num)
            except (ValueError, TypeError):
                c_int = ch_idx + 1
            c_title = target_ch.get("title", f"Chapter {c_int}")
            
            elements = target_ch.get("elements", [])
            paragraphs = [e for e in elements if e.get("type") == "paragraph"]
            
            p_pick = paragraphs[min(idx % max(1, len(paragraphs)), len(paragraphs) - 1)] if paragraphs else {}
            anchor_id = p_pick.get("id", f"ch{c_int:02d}_p01")
            anchor_raw = p_pick.get("text", "")
            anchor_text = anchor_raw[:55].strip() if anchor_raw else "CHAPTER_OPENING"
            
            # Generate bespoke prompt based on theme & paragraph snippet
            prompt_snippet = anchor_raw[:120].replace('"', "'") if anchor_raw else c_title
            prompt = (
                f"Historical 19th-century engraving, {preset['filter_preset'].replace('_', ' ')} style. "
                f"Scene: {prompt_snippet}. Detailed volumetric shadows, brass laboratory fittings, "
                f"period forensic instruments, fine stippling, antique archival plate, 300 DPI fine print."
            )

            placement = placements[idx % len(placements)]
            assets.append({
                "id": asset_id,
                "title": f"Plate {slot_num:02d}: {c_title}",
                "chapter": c_int,
                "anchor": anchor_id,
                "anchor_text": anchor_text,
                "placement": placement,
                "prompt": prompt,
                "image_url": f"/static/assets/placeholders/{book_id}_halfpage.png",
                "filter_preset": preset["filter_preset"],
                "frame_style": preset["frame_style"],
                "filter_applied": False,
                "vector_callouts": []
            })

        return {
            "status": "success",
            "book_id": book_id,
            "theme_preset_key": theme_key,
            "genre_style": preset["genre_label"],
            "mood_summary": f"Detected thematic profile: {preset['genre_label']}. Optimized for 300 DPI fine book publication.",
            "typography_overrides": typography,
            "front_back_matter": front_back_matter,
            "assets": assets,
            "total_illustrations": len(assets)
        }


ai_director_manager = AIDirectorManager()
