"""
Argon Book Studio - Main FastAPI Application.
Desktop publishing server for illustrated novel typesetting and multi-format publication.
Supports live typesetting geometry inspection, inline text editing,
visual pin-dropper vector callouts, image print lab with split before/after,
bird's-eye filmstrip, and extended front/back matter.
"""

import json
import io
import os
import shutil
import zipfile
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Body, Response, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pymupdf
from PIL import Image

from app.profiles import BOOK_PROFILES, UNIVERSAL_PUBLISHING_SPECS
from app.settings import settings_manager, DEFAULT_TRIM_PRESETS
from app.parser import parse_markdown_manuscript, parse_docx_manuscript
from app.manifest import manifest_manager
from app.filters import (
    process_image,
    generate_procedural_placeholder,
    generate_preview_base64
)
from app.paginator import paginate_manuscript
from app.front_back_matter import generate_front_matter_data
from app.ai_director import ai_director_manager
from app.exporters.pdf_exporter import export_pdf
from app.exporters.docx_exporter import export_docx
from app.exporters.epub_exporter import export_epub

app = FastAPI(
    title="Argon Book Studio Pro",
    description="Drag-and-Drop Illustrated Novel Typesetting & Publishing Engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "..", "uploads")
EXPORTS_DIR = os.path.join(BASE_DIR, "..", "exports")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")

STATE = {
    "active_book_id": "book01",
    "custom_manuscripts": {},
    "auto_tailpieces": {
        "book01": {},
        "book02": {},
        "book03": {},
        "book04": {},
        "book05": {}
    }
}


def invalidate_pdf_cache(book_id: str):
    """Deletes cached print PDF file so preview and exports are always fresh."""
    pdf_path = os.path.join(EXPORTS_DIR, f"{book_id}_print_edition.pdf")
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception:
            pass


def load_book_manuscript(book_id: str) -> Dict[str, Any]:
    if book_id in STATE["custom_manuscripts"]:
        return STATE["custom_manuscripts"][book_id]
        
    sample_files = {
        "book01": "book01_cormac_vane.md",
        "book02": "book02_fourteen_hour_barometer.md",
        "book03": "book03_dead_room_transcripts.md",
        "book04": "book04_salt_orchard.md",
        "book05": "book05_provenance_of_ashes.md"
    }
    fname = sample_files.get(book_id, "book01_cormac_vane.md")
    path = os.path.join(BASE_DIR, "sample_data", fname)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = parse_markdown_manuscript(content)
        # Store a working copy so inline edits can be performed
        STATE["custom_manuscripts"][book_id] = parsed
        return parsed
        
    return parse_markdown_manuscript("# Empty Manuscript\n\n## Chapter 1\n\nNo text available.")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(BASE_DIR, "templates", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Argon Book Studio is running. Index template pending.</h1>"


@app.get("/api/profiles")
async def get_profiles():
    return {
        "profiles": BOOK_PROFILES,
        "specs": UNIVERSAL_PUBLISHING_SPECS,
        "trim_presets": DEFAULT_TRIM_PRESETS
    }


@app.get("/api/books")
async def get_books():
    books_list = []
    for bid, p in BOOK_PROFILES.items():
        books_list.append({
            "id": bid,
            "title": p["title"],
            "short_title": p["short_title"],
            "genre": p["genre"],
            "author": p["author"],
            "filter_name": p["filter_name"],
            "scene_break_name": p["scene_break_name"],
            "accent_color": p["accent_color"]
        })
    return {"books": books_list, "active_book_id": STATE["active_book_id"]}


@app.get("/api/book/{book_id}")
async def get_book_details(book_id: str):
    if book_id not in BOOK_PROFILES and book_id not in STATE["custom_manuscripts"]:
        book_id = "book01"
    STATE["active_book_id"] = book_id
    
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    
    # Load dynamic project settings
    settings = settings_manager.get_settings(book_id)
    
    pagination = paginate_manuscript(
        parsed,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    front_matter = generate_front_matter_data(book_id, parsed, settings.get("front_back_matter"))
    
    return {
        "book_id": book_id,
        "profile": BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"]),
        "manuscript": parsed,
        "manifest": manifest,
        "settings": settings,
        "pagination": pagination,
        "front_matter": front_matter
    }


# ======================================================================
# 1. LIVE TYPESETTING GEOMETRY & SETTINGS APIS
# ======================================================================

@app.get("/api/project/{book_id}/settings")
async def get_project_settings(book_id: str):
    return settings_manager.get_settings(book_id)


@app.post("/api/project/{book_id}/settings")
async def update_project_settings(book_id: str, updates: Dict[str, Any] = Body(...)):
    new_settings = settings_manager.update_settings(book_id, updates)
    invalidate_pdf_cache(book_id)
    
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    
    pagination = paginate_manuscript(
        parsed,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=new_settings,
        custom_matter=new_settings.get("front_back_matter")
    )
    front_matter = generate_front_matter_data(book_id, parsed, new_settings.get("front_back_matter"))
    
    return {
        "status": "success",
        "settings": new_settings,
        "pagination": pagination,
        "front_matter": front_matter
    }


@app.post("/api/project/{book_id}/reset-settings")
async def reset_project_settings(book_id: str):
    settings = settings_manager.reset_settings(book_id)
    invalidate_pdf_cache(book_id)
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, manifest, book_id, auto_tailpieces=tailpieces, custom_specs=settings)
    return {"status": "success", "settings": settings, "pagination": pagination}


# ======================================================================
# 2. INLINE MANUSCRIPT EDITING APIS
# ======================================================================

@app.post("/api/manuscript/{book_id}/edit-element")
async def edit_manuscript_element(book_id: str, payload: Dict[str, Any] = Body(...)):
    element_id = payload.get("element_id")
    new_text = payload.get("text", "")
    
    if not element_id:
        raise HTTPException(status_code=400, detail="Missing element_id")
        
    manuscript = load_book_manuscript(book_id)
    found = False
    
    for ch in manuscript.get("chapters", []):
        for el in ch.get("elements", []):
            if el.get("id") == element_id:
                if el.get("type") == "paragraph":
                    el["text"] = new_text.strip()
                    el["word_count"] = len(el["text"].split())
                elif el.get("type") == "container":
                    el["content"] = new_text.strip()
                found = True
                break
        if found:
            break
            
    if not found:
        raise HTTPException(status_code=404, detail="Element not found in manuscript")
        
    STATE["custom_manuscripts"][book_id] = manuscript
    invalidate_pdf_cache(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    
    pagination = paginate_manuscript(
        manuscript,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "element_id": element_id,
        "pagination": pagination
    }


@app.post("/api/manuscript/{book_id}/update-paragraph")
async def update_paragraph(book_id: str, payload: Dict[str, Any] = Body(...)):
    element_id = payload.get("element_id")
    new_text = payload.get("text")
    new_block_type = payload.get("block_type")
    page_break_before = payload.get("page_break_before")
    keep_with_next = payload.get("keep_with_next")
    scene_break_after = payload.get("scene_break_after")
    
    if not element_id:
        raise HTTPException(status_code=400, detail="Missing element_id")
        
    manuscript = load_book_manuscript(book_id)
    found = False
    
    for ch in manuscript.get("chapters", []):
        for el in ch.get("elements", []):
            if el.get("id") == element_id:
                if new_text is not None:
                    el["text"] = str(new_text).strip()
                    el["content"] = str(new_text).strip()
                    el["word_count"] = len(el["text"].split())
                if new_block_type:
                    el["block_type"] = new_block_type
                    if new_block_type in ["inworld_writ", "welsh_slate", "audio_transcript", "archival_journal", "scientific_formula", "cuneiform_clause"]:
                        el["type"] = "container"
                        el["tag"] = new_block_type.replace("_", "-")
                    elif new_block_type == "scene_break":
                        el["type"] = "scene_break"
                    else:
                        el["type"] = "paragraph"
                if page_break_before is not None:
                    el["page_break_before"] = bool(page_break_before)
                if keep_with_next is not None:
                    el["keep_with_next"] = bool(keep_with_next)
                if scene_break_after is not None:
                    el["scene_break_after"] = str(scene_break_after)
                found = True
                break
        if found:
            break
            
    if not found:
        raise HTTPException(status_code=404, detail="Element not found")
        
    STATE["custom_manuscripts"][book_id] = manuscript
    invalidate_pdf_cache(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    
    pagination = paginate_manuscript(
        manuscript,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "element_id": element_id,
        "pagination": pagination
    }


@app.post("/api/manuscript/{book_id}/insert-element")
async def insert_manuscript_element(book_id: str, payload: Dict[str, Any] = Body(...)):
    target_id = payload.get("target_id")
    elem_type = payload.get("element_type", "paragraph") # paragraph, scene_break, container
    content = payload.get("content", "")
    tag = payload.get("tag", "inquest-writ")
    
    manuscript = load_book_manuscript(book_id)
    inserted = False
    new_id = None
    
    for ch in manuscript.get("chapters", []):
        elements = ch.get("elements", [])
        for idx, el in enumerate(elements):
            if el.get("id") == target_id:
                ch_idx = ch.get("chapter_index", 1)
                existing_nums = []
                for e in elements:
                    eid = e.get("id", "")
                    if eid.startswith(f"ch{ch_idx:02d}_p"):
                        try:
                            existing_nums.append(int(eid.split("_p")[1]))
                        except Exception:
                            pass
                next_num = (max(existing_nums) + 1) if existing_nums else (len(elements) + 1)
                new_id = f"ch{ch_idx:02d}_p{next_num:02d}"
                
                if elem_type == "paragraph":
                    new_elem = {
                        "id": new_id,
                        "type": "paragraph",
                        "text": content,
                        "is_first_after_break": False,
                        "word_count": len(content.split())
                    }
                elif elem_type == "scene_break":
                    new_elem = {
                        "id": new_id,
                        "type": "scene_break",
                        "content": "***"
                    }
                elif elem_type == "container":
                    new_elem = {
                        "id": new_id,
                        "type": "container",
                        "tag": tag,
                        "content": content
                    }
                    
                elements.insert(idx + 1, new_elem)
                inserted = True
                break
        if inserted:
            break
            
    if not inserted:
        raise HTTPException(status_code=404, detail="Target anchor not found")
        
    STATE["custom_manuscripts"][book_id] = manuscript
    invalidate_pdf_cache(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    
    pagination = paginate_manuscript(
        manuscript,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "new_id": new_id,
        "manuscript": manuscript,
        "pagination": pagination
    }


@app.post("/api/manuscript/{book_id}/wrap-container")
async def wrap_element_in_container(book_id: str, payload: Dict[str, Any] = Body(...)):
    element_id = payload.get("element_id")
    container_tag = payload.get("container_tag", "inquest-writ")
    
    manuscript = load_book_manuscript(book_id)
    converted = False
    
    for ch in manuscript.get("chapters", []):
        for el in ch.get("elements", []):
            if el.get("id") == element_id:
                content = el.get("text", el.get("content", ""))
                el["type"] = "container"
                el["tag"] = container_tag
                el["content"] = content
                if "text" in el:
                    del el["text"]
                converted = True
                break
        if converted:
            break
            
    if not converted:
        raise HTTPException(status_code=404, detail="Element not found")
        
    STATE["custom_manuscripts"][book_id] = manuscript
    invalidate_pdf_cache(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    
    pagination = paginate_manuscript(
        manuscript,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "element_id": element_id,
        "pagination": pagination
    }


@app.post("/api/manuscript/{book_id}/merge-element")
async def merge_manuscript_element(book_id: str, payload: Dict[str, Any] = Body(...)):
    element_id = payload.get("element_id")
    if not element_id:
        raise HTTPException(status_code=400, detail="Missing element_id")
        
    manuscript = load_book_manuscript(book_id)
    merged = False
    
    for ch in manuscript.get("chapters", []):
        elements = ch.get("elements", [])
        for idx, el in enumerate(elements):
            if el.get("id") == element_id:
                if idx == 0:
                    raise HTTPException(status_code=400, detail="Cannot merge first element of chapter with previous")
                prev_el = elements[idx - 1]
                prev_text = prev_el.get("text", prev_el.get("content", ""))
                curr_text = el.get("text", el.get("content", ""))
                combined_text = f"{prev_text}\n\n{curr_text}".strip()
                
                prev_html = prev_el.get("formatted_html")
                curr_html = el.get("formatted_html")
                if prev_html or curr_html:
                    prev_el["formatted_html"] = f"{prev_html or prev_text}<br><br>{curr_html or curr_text}"
                
                if prev_el.get("type") == "container":
                    prev_el["content"] = combined_text
                else:
                    prev_el["text"] = combined_text
                    prev_el["word_count"] = len(combined_text.split())
                    
                elements.pop(idx)
                merged = True
                break
        if merged:
            break
            
    if not merged:
        raise HTTPException(status_code=404, detail="Element not found")
        
    STATE["custom_manuscripts"][book_id] = manuscript
    invalidate_pdf_cache(book_id)
    
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(
        manuscript,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "merged_element_id": element_id,
        "manuscript": manuscript,
        "pagination": pagination
    }


@app.delete("/api/manuscript/{book_id}/delete-element/{element_id}")
async def delete_manuscript_element(book_id: str, element_id: str):
    manuscript = load_book_manuscript(book_id)
    deleted = False
    
    for ch in manuscript.get("chapters", []):
        elements = ch.get("elements", [])
        for idx, el in enumerate(elements):
            if el.get("id") == element_id:
                elements.pop(idx)
                deleted = True
                break
        if deleted:
            break
            
    if not deleted:
        raise HTTPException(status_code=404, detail="Element not found")
        
    STATE["custom_manuscripts"][book_id] = manuscript
    invalidate_pdf_cache(book_id)
    
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(
        manuscript,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "deleted_element_id": element_id,
        "manuscript": manuscript,
        "pagination": pagination
    }


@app.post("/api/manuscript/{book_id}/auto-style")
async def auto_style_manuscript(book_id: str):
    """
    1-Click Auto-Styler & Blueprint Locker:
    - Merges consecutive multi-line container paragraphs.
    - Styles Vesper sensory trace in Chapters 2, 10, 20 for book01.
    - Sets flush-left indent (is_first_after_break = True) on first paragraphs & post-break blocks.
    - Populates Front & Back Matter defaults.
    - Invalidates PDF cache & repaginates.
    """
    import copy
    from app.parser import merge_consecutive_containers
    
    manuscript = load_book_manuscript(book_id)
    manuscript = copy.deepcopy(manuscript)
    
    detected_containers = {
        "inworld_writ": 0,
        "welsh_slate": 0,
        "audio_transcript": 0,
        "archival_journal": 0,
        "scientific_formula": 0,
        "cuneiform_clause": 0,
        "sensory_draw": 0
    }
    
    vesper_keywords = [
        "vesper draw", "sensory draw", "sensory trace",
        "alembic in the shadows", "alembic", "vitriol",
        "copper fluorosilicate", "arsenic trioxide", "raw marrow", "soft palate"
    ]
    
    for ch in manuscript.get("chapters", []):
        ch_num = ch.get("chapter_number", 1)
        elements = ch.get("elements", [])
        
        # 1. Merge consecutive containers
        merged_elements = merge_consecutive_containers(elements)
        
        # 2. For book01: auto-style Vesper sensory trace in chapters 2, 10, 20 or matching keywords
        if book_id == "book01":
            for el in merged_elements:
                txt = (el.get("text") or el.get("content") or "").lower()
                if el.get("tag") == "inquest-writ" or "coroner's inquest writ" in txt:
                    el["type"] = "container"
                    el["block_type"] = "inworld_writ"
                    el["tag"] = "inquest-writ"
                elif el.get("tag") == "sensory-draw" or any(k in txt for k in ["vesper draw", "sensory draw", "sensory trace"]):
                    el["type"] = "container"
                    el["block_type"] = "inworld_writ"
                    el["tag"] = "sensory-draw"
                elif ch_num in [2, 10, 20] and any(k in txt for k in ["vesper", "sensory", "alembic in the shadows", "raw marrow"]):
                    el["type"] = "container"
                    el["block_type"] = "inworld_writ"
                    el["tag"] = "sensory-draw"
        
        # 3. Indentation logic: first paragraph after chapter opening, scene break, or container is flush-left
        prev_was_break_or_container = True  # Start of chapter: first paragraph is always first after break
        for el in merged_elements:
            btype = el.get("block_type", "body")
            etype = el.get("type", "paragraph")
            
            # Count detected containers
            if etype == "container" or btype in detected_containers or el.get("tag") in ["sensory-draw", "inquest-writ"]:
                if el.get("tag") == "sensory-draw":
                    detected_containers["sensory_draw"] += 1
                elif el.get("tag") == "inquest-writ" or btype == "inworld_writ":
                    detected_containers["inworld_writ"] += 1
                elif btype in detected_containers:
                    detected_containers[btype] += 1
                    
            if etype == "paragraph":
                if prev_was_break_or_container:
                    el["is_first_after_break"] = True
                    if btype == "body":
                        el["block_type"] = "body_first"
                else:
                    el["is_first_after_break"] = False
                    if btype == "body_first":
                        el["block_type"] = "body"
                        
            # Determine if this element acts as a break/container for the next element
            if etype in ["scene_break", "container", "illustration"] or el.get("scene_break_after", "none") != "none" or el.get("page_break_before", False):
                prev_was_break_or_container = True
            elif btype in ["inworld_writ", "welsh_slate", "audio_transcript", "archival_journal", "scientific_formula", "cuneiform_clause"]:
                prev_was_break_or_container = True
            else:
                prev_was_break_or_container = False
                
        ch["elements"] = merged_elements
        
    STATE["custom_manuscripts"][book_id] = manuscript
    invalidate_pdf_cache(book_id)
    
    # 4. Populate Front Matter & Back Matter defaults for this book
    default_matter = generate_front_matter_data(book_id, manuscript_meta=manuscript)
    settings_manager.update_settings(book_id, {"front_back_matter": default_matter})
    
    # 5. Bind manifest anchors against the styled manuscript
    manifest_manager.bind_anchors_to_manuscript(book_id, manuscript)
    
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(
        manuscript,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=default_matter
    )
    
    return {
        "status": "success",
        "book_id": book_id,
        "manuscript": manuscript,
        "pagination": pagination,
        "front_matter": default_matter,
        "detected_containers": detected_containers,
        "total_chapters": manuscript.get("total_chapters", len(manuscript.get("chapters", []))),
        "total_words": manuscript.get("total_words", 0)
    }


# ======================================================================
# LOCAL AI BOOK ART DIRECTOR & AUTONOMOUS LAYOUT SUITE
# ======================================================================

@app.get("/api/ai/status")
async def get_ai_status():
    """Checks connection to local LLM server (Ollama / OpenAI-compatible) and returns status."""
    conn = ai_director_manager.check_connection()
    config = ai_director_manager.get_config()
    return {
        "status": "success",
        "connection": conn,
        "config": config
    }


@app.post("/api/ai/configure")
async def configure_ai_director(payload: Dict[str, Any] = Body(...)):
    """Updates Local AI Director settings (endpoint URL, selected model, timeout)."""
    updated = ai_director_manager.update_config(payload)
    conn = ai_director_manager.check_connection()
    return {
        "status": "success",
        "config": updated,
        "connection": conn
    }


@app.post("/api/ai/analyze/{book_id}")
async def analyze_manuscript_ai(
    book_id: str,
    payload: Optional[Dict[str, Any]] = Body(None)
):
    """
    Runs the Local AI Art Director:
    - Scans manuscript chapters and themes.
    - Generates complete typography, mandatory pages, and 16 illustration scene prompts anchored to paragraphs.
    """
    p = payload or {}
    num_illustrations = int(p.get("num_illustrations", 16))
    user_prompt_override = p.get("prompt_override")
    
    manuscript = load_book_manuscript(book_id)
    blueprint = ai_director_manager.analyze_manuscript(
        manuscript=manuscript,
        book_id=book_id,
        num_illustrations=num_illustrations,
        user_prompt_override=user_prompt_override
    )
    
    return {
        "status": "success",
        "book_id": book_id,
        "blueprint": blueprint
    }


@app.post("/api/ai/apply/{book_id}")
async def apply_ai_blueprint(
    book_id: str,
    payload: Optional[Dict[str, Any]] = Body(None)
):
    """
    Applies the proposed AI Blueprint to the book:
    1. Updates typography & geometry settings.
    2. Updates front/back matter (mandatory pages).
    3. Replaces / synchronizes manifest assets with AI-discovered visual anchors.
    4. Invalidates PDF cache & repaginates.
    """
    p = payload or {}
    blueprint = p.get("blueprint")
    manuscript = load_book_manuscript(book_id)
    
    # If no blueprint supplied in payload, analyze live
    if not blueprint:
        blueprint = ai_director_manager.analyze_manuscript(
            manuscript=manuscript,
            book_id=book_id,
            num_illustrations=int(p.get("num_illustrations", 16))
        )
        
    # 1. Apply Typography Overrides & Front/Back Matter to settings
    settings_updates = {}
    if "typography_overrides" in blueprint:
        settings_updates["typography"] = blueprint["typography_overrides"]
    if "front_back_matter" in blueprint:
        settings_updates["front_back_matter"] = blueprint["front_back_matter"]
    if settings_updates:
        settings_manager.update_settings(book_id, settings_updates)
        
    # 2. Update Book Manifest with AI Illustration Assets
    if "assets" in blueprint and blueprint["assets"]:
        manifest_manager.import_manifest(book_id, {"assets": blueprint["assets"]}, manuscript)
        manifest_manager.bind_anchors_to_manuscript(book_id, manuscript)
        
    invalidate_pdf_cache(book_id)
    
    updated_manifest = manifest_manager.get_book_manifest(book_id)
    updated_settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(
        manuscript,
        updated_manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=updated_settings,
        custom_matter=updated_settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "book_id": book_id,
        "blueprint": blueprint,
        "manifest": updated_manifest,
        "settings": updated_settings,
        "pagination": pagination
    }


# ======================================================================
# 3. IMAGE PRINT LAB (SPLIT BEFORE/AFTER & SLIDERS)
# ======================================================================

@app.post("/api/image-lab/preview")
async def preview_image_filter(payload: Dict[str, Any] = Body(...)):
    book_id = payload.get("book_id", STATE["active_book_id"])
    asset_id = payload.get("asset_id")
    filter_preset = payload.get("filter_preset", "cyanotype_silver_plate")
    contrast = float(payload.get("contrast", 1.35))
    grain = float(payload.get("grain", 0.08))
    vignette = float(payload.get("vignette", 0.38))
    brightness = float(payload.get("brightness", 1.0))
    
    manifest = manifest_manager.get_book_manifest(book_id)
    asset = next((a for a in manifest.get("assets", []) if a.get("id") == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    raw_path = asset.get("raw_image_path")
    frame_style = asset.get("frame_style", "none")
    if raw_path and os.path.exists(raw_path):
        local_path = raw_path
    else:
        img_url = asset.get("image_url", "")
        local_path = None
        if img_url.startswith("/static/"):
            local_path = os.path.join(BASE_DIR, img_url.lstrip("/"))
        elif os.path.exists(img_url):
            local_path = img_url
            
    if not local_path or not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Image file not found on disk")
        
    data_uri = generate_preview_base64(
        image_path=local_path,
        filter_preset=filter_preset,
        contrast=contrast,
        grain=grain,
        vignette=vignette,
        brightness=brightness,
        callouts=asset.get("vector_callouts", []),
        profile_id=book_id,
        frame_style=frame_style
    )
    
    return {"status": "success", "preview_data_uri": data_uri}


@app.post("/api/image-lab/apply")
async def apply_image_lab_settings(payload: Dict[str, Any] = Body(...)):
    book_id = payload.get("book_id", STATE["active_book_id"])
    asset_id = payload.get("asset_id")
    filter_preset = payload.get("filter_preset", "cyanotype_silver_plate")
    contrast = float(payload.get("contrast", 1.35))
    grain = float(payload.get("grain", 0.08))
    vignette = float(payload.get("vignette", 0.38))
    brightness = float(payload.get("brightness", 1.0))
    target_dpi = int(payload.get("target_dpi", 300))
    
    manifest = manifest_manager.get_book_manifest(book_id)
    asset = next((a for a in manifest.get("assets", []) if a.get("id") == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    img_name = f"{asset_id}_custom_filtered.png"
    out_disk_path = os.path.join(STATIC_DIR, "assets", "placeholders", img_name)
    raw_path = asset.get("raw_image_path")
    frame_style = asset.get("frame_style", "none")
    callouts = asset.get("vector_callouts", [])
    
    if raw_path and os.path.exists(raw_path):
        process_image(
            input_image_path=raw_path,
            output_image_path=out_disk_path,
            filter_preset=filter_preset,
            placement_type=asset.get("placement", "Half-Page Top"),
            callouts=callouts,
            profile_id=book_id,
            target_dpi=target_dpi,
            contrast=contrast,
            grain=grain,
            vignette=vignette,
            brightness=brightness,
            frame_style=frame_style
        )
    else:
        generate_procedural_placeholder(
            output_path=out_disk_path,
            title=asset.get("title", ""),
            prompt=asset.get("prompt", ""),
            placement_type=asset.get("placement", "Half-Page Top"),
            filter_preset=filter_preset,
            profile_id=book_id,
            callouts=callouts,
            contrast=contrast,
            grain=grain,
            vignette=vignette,
            frame_style=frame_style
        )
    
    new_url = f"/static/assets/placeholders/{img_name}"
    manifest_manager.update_asset(book_id, asset_id, {
        "image_url": new_url,
        "filter_applied": True
    })
    
    # Update settings image_lab cache
    settings_manager.update_settings(book_id, {
        "image_lab": {
            "filter_preset": filter_preset,
            "grain_intensity": grain,
            "contrast": contrast,
            "vignette_strength": vignette,
            "brightness": brightness,
            "target_dpi": target_dpi
        }
    })
    invalidate_pdf_cache(book_id)
    
    parsed = load_book_manuscript(book_id)
    updated_manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    
    pagination = paginate_manuscript(
        parsed,
        updated_manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "asset_id": asset_id,
        "image_url": new_url,
        "pagination": pagination
    }


# ======================================================================
# 4. MANUSCRIPT & ASSET MANAGEMENT
# ======================================================================

@app.post("/api/manuscript/upload")
async def upload_manuscript(
    book_id: str = Form("book01"),
    file: UploadFile = File(...)
):
    filename = file.filename or "upload.md"
    ext = os.path.splitext(filename)[1].lower()
    
    upload_path = os.path.join(UPLOADS_DIR, f"{book_id}_{filename}")
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    if ext == ".docx":
        parsed = parse_docx_manuscript(upload_path)
    else:
        with open(upload_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        parsed = parse_markdown_manuscript(content)
        
    STATE["custom_manuscripts"][book_id] = parsed
    STATE["active_book_id"] = book_id
    invalidate_pdf_cache(book_id)
    
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    pagination = paginate_manuscript(parsed, manifest, book_id, custom_specs=settings)
    
    return {
        "status": "success",
        "book_id": book_id,
        "filename": filename,
        "parsed": parsed,
        "pagination": pagination
    }


@app.post("/api/manifest/{book_id}/update-anchor")
async def update_asset_anchor(book_id: str, payload: Dict[str, Any] = Body(...)):
    asset_id = payload.get("asset_id")
    new_anchor = payload.get("new_anchor")
    if not asset_id or not new_anchor:
        raise HTTPException(status_code=400, detail="Missing asset_id or new_anchor")
        
    updated = manifest_manager.update_anchor(book_id, asset_id, new_anchor)
    if not updated:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    invalidate_pdf_cache(book_id)
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, manifest, book_id, auto_tailpieces=tailpieces, custom_specs=settings)
    
    return {
        "status": "success",
        "asset_id": asset_id,
        "new_anchor": new_anchor,
        "pagination": pagination
    }


@app.post("/api/manifest/{book_id}/add-slot")
async def add_illustration_slot(book_id: str, payload: Dict[str, Any] = Body(...)):
    title = payload.get("title", "New Planned Illustration")
    anchor = payload.get("anchor", "ch01_p01")
    placement = payload.get("placement", "Half-Page Top")
    prompt = payload.get("prompt", "Atmospheric etching matching book theme")
    caption = payload.get("caption", f"Plate: {title}")
    
    profile = BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"])
    asset_id = f"{book_id}_asset_{len(manifest_manager.get_book_manifest(book_id).get('assets', [])) + 1:02d}"
    
    img_name = f"{asset_id}.png"
    target_img_path = os.path.join(STATIC_DIR, "assets", "placeholders", img_name)
    generate_procedural_placeholder(
        output_path=target_img_path,
        title=title,
        prompt=prompt,
        placement_type=placement,
        filter_preset=profile.get("filter_preset", "cyanotype_silver_plate"),
        profile_id=book_id,
        callouts=[]
    )
    
    slot_data = {
        "id": asset_id,
        "title": title,
        "anchor": anchor,
        "placement": placement,
        "prompt": prompt,
        "caption": caption,
        "image_url": f"/static/assets/placeholders/{img_name}",
        "filter_applied": True,
        "vector_callouts": []
    }
    
    manifest_manager.add_asset(book_id, slot_data)
    invalidate_pdf_cache(book_id)
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, manifest, book_id, auto_tailpieces=tailpieces, custom_specs=settings)
    
    return {
        "status": "success",
        "slot": slot_data,
        "pagination": pagination
    }


@app.delete("/api/manifest/{book_id}/delete-slot/{asset_id}")
async def delete_slot(book_id: str, asset_id: str):
    res = manifest_manager.delete_asset(book_id, asset_id)
    invalidate_pdf_cache(book_id)
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, manifest, book_id, auto_tailpieces=tailpieces, custom_specs=settings)
    return {"status": "success", "deleted": res, "pagination": pagination}


@app.post("/api/manifest/{book_id}/update-callouts")
async def update_callouts(book_id: str, payload: Dict[str, Any] = Body(...)):
    asset_id = payload.get("asset_id")
    callouts = payload.get("callouts", [])
    
    asset = manifest_manager.update_asset(book_id, asset_id, {"vector_callouts": callouts})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    raw_path = asset.get("raw_image_path")
    frame_style = asset.get("frame_style", "none")
    img_url = asset.get("image_url", "")
    disk_path = None
    if img_url.startswith("/static/"):
        disk_path = os.path.join(BASE_DIR, img_url.lstrip("/"))
    elif os.path.isabs(img_url):
        disk_path = img_url

    if raw_path and os.path.exists(raw_path):
        if not disk_path:
            disk_path = os.path.join(STATIC_DIR, "assets", "placeholders", f"{asset_id}_custom_filtered.png")
        process_image(
            input_image_path=raw_path,
            output_image_path=disk_path,
            filter_preset=asset.get("filter_preset") or BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"]).get("filter_preset", "cyanotype_silver_plate"),
            placement_type=asset.get("placement", "Half-Page Top"),
            callouts=callouts,
            profile_id=book_id,
            frame_style=frame_style
        )
    elif disk_path and os.path.exists(disk_path):
        profile = BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"])
        generate_procedural_placeholder(
            output_path=disk_path,
            title=asset.get("title", ""),
            prompt=asset.get("prompt", ""),
            placement_type=asset.get("placement", "Half-Page Top"),
            filter_preset=profile.get("filter_preset", "cyanotype_silver_plate"),
            profile_id=book_id,
            callouts=callouts,
            frame_style=frame_style
        )
    invalidate_pdf_cache(book_id)
            
    return {"status": "success", "asset": asset}


@app.post("/api/manifest/{book_id}/update-asset")
async def update_manifest_asset(book_id: str, payload: Dict[str, Any] = Body(...)):
    asset_id = payload.get("asset_id")
    updates = payload.get("updates", {})
    if not asset_id:
        raise HTTPException(status_code=400, detail="Missing asset_id")
        
    updated = manifest_manager.update_asset(book_id, asset_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    invalidate_pdf_cache(book_id)
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    
    pagination = paginate_manuscript(
        parsed,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    return {"status": "success", "asset": updated, "pagination": pagination}


@app.post("/api/manifest/{book_id}/import")
async def import_manifest_endpoint(
    book_id: str,
    request: Request
):
    manuscript = load_book_manuscript(book_id)
    raw_data = None
    content_type = request.headers.get("content-type", "")
    
    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("file")
        if file_obj and hasattr(file_obj, "read"):
            content = await file_obj.read()
            try:
                raw_data = json.loads(content.decode("utf-8"))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}")
        elif "data" in form:
            try:
                raw_data = json.loads(form["data"])
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON in form data: {e}")
    else:
        try:
            body_json = await request.json()
            raw_data = body_json.get("data", body_json)
        except Exception:
            raw_data = None
        
    if not raw_data or (isinstance(raw_data, dict) and raw_data.get("use_builtin")) or raw_data == "builtin":
        # Automatically load the built-in 16-asset blueprint for the selected book
        raw_data = manifest_manager.get_book_manifest(book_id)
    elif isinstance(raw_data, dict):
        settings_updates = {}
        if "typography_overrides" in raw_data and isinstance(raw_data["typography_overrides"], dict):
            settings_updates["typography_overrides"] = raw_data["typography_overrides"]
        if any(k in raw_data for k in ["front_matter", "back_matter", "front_back_matter"]):
            fbm = dict(raw_data.get("front_back_matter", {}))
            if "front_matter" in raw_data and isinstance(raw_data["front_matter"], dict):
                fbm.update(raw_data["front_matter"])
            if "back_matter" in raw_data and isinstance(raw_data["back_matter"], dict):
                fbm.update(raw_data["back_matter"])
            settings_updates["front_back_matter"] = fbm
        if settings_updates:
            settings_manager.update_settings(book_id, settings_updates)
        
    updated_manifest = manifest_manager.import_manifest(book_id, raw_data, manuscript)
    invalidate_pdf_cache(book_id)
    
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(
        manuscript,
        updated_manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "manifest": updated_manifest,
        "pagination": pagination
    }


@app.get("/api/manifest/{book_id}/export")
async def export_manifest_endpoint(book_id: str):
    settings = settings_manager.get_settings(book_id)
    exported_data = manifest_manager.export_manifest(book_id, settings)
    
    content_str = json.dumps(exported_data, indent=2, ensure_ascii=False)
    return Response(
        content=content_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{book_id}_manifest.json"'
        }
    )


@app.post("/api/manifest/{book_id}/bind-anchors")
async def bind_anchors_endpoint(book_id: str):
    manuscript = load_book_manuscript(book_id)
    bound_count = manifest_manager.bind_anchors_to_manuscript(book_id, manuscript)
    invalidate_pdf_cache(book_id)
    updated_manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(
        manuscript,
        updated_manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    return {
        "status": "success",
        "bound_count": bound_count,
        "manifest": updated_manifest,
        "pagination": pagination
    }


# ======================================================================
# LIVE PRINT PDF RASTER PREVIEW (PYMUPDF)
# ======================================================================

@app.get("/api/pdf-info/{book_id}")
async def get_pdf_info(book_id: str):
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    pdf_path = os.path.join(EXPORTS_DIR, f"{book_id}_print_edition.pdf")
    
    if not os.path.exists(pdf_path):
        export_pdf(parsed, manifest, book_id, pdf_path, custom_specs=settings, custom_matter=settings.get("front_back_matter"))
        
    try:
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        total_pages = 1
        
    return {"book_id": book_id, "total_pages": total_pages}


@app.get("/api/pdf-preview/{book_id}/{page_num}")
@app.get("/api/pdf-page/{book_id}/{page_num}")
async def get_pdf_page_preview(book_id: str, page_num: int, dpi: int = 150):
    pdf_path = os.path.join(EXPORTS_DIR, f"{book_id}_print_edition.pdf")
    
    if not os.path.exists(pdf_path):
        parsed = load_book_manuscript(book_id)
        manifest = manifest_manager.get_book_manifest(book_id)
        settings = settings_manager.get_settings(book_id)
        export_pdf(parsed, manifest, book_id, pdf_path, custom_specs=settings, custom_matter=settings.get("front_back_matter"))
        
    try:
        doc = pymupdf.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            blank = Image.new("RGB", (int(6.0 * dpi), int(9.0 * dpi)), (255, 255, 255))
            buf = io.BytesIO()
            blank.save(buf, format="PNG")
            doc.close()
            return Response(content=buf.getvalue(), media_type="image/png")
            
        page = doc.load_page(page_num - 1)
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        doc.close()
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering PDF page: {e}")


@app.post("/api/assets/upload/{book_id}/{asset_id}")
async def upload_asset_image(
    book_id: str,
    asset_id: str,
    file: UploadFile = File(...)
):
    profile = BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"])
    manifest = manifest_manager.get_book_manifest(book_id)
    asset = next((a for a in manifest.get("assets", []) if a.get("id") == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset slot not found")
        
    filename = file.filename or f"{asset_id}.png"
    temp_upload_path = os.path.join(UPLOADS_DIR, f"raw_{book_id}_{filename}")
    with open(temp_upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    filtered_name = f"{asset_id}_print300.png"
    out_path = os.path.join(STATIC_DIR, "assets", "placeholders", filtered_name)
    frame_style = asset.get("frame_style", "none")
    
    process_image(
        input_image_path=temp_upload_path,
        output_image_path=out_path,
        filter_preset=profile.get("filter_preset", "cyanotype_silver_plate"),
        placement_type=asset.get("placement", "Half-Page Top"),
        callouts=asset.get("vector_callouts", []),
        profile_id=book_id,
        frame_style=frame_style
    )
    
    web_url = f"/static/assets/placeholders/{filtered_name}"
    manifest_manager.update_asset(book_id, asset_id, {
        "image_url": web_url,
        "raw_image_path": temp_upload_path,
        "filter_applied": True
    })
    invalidate_pdf_cache(book_id)
    
    parsed = load_book_manuscript(book_id)
    updated_manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, updated_manifest, book_id, auto_tailpieces=tailpieces, custom_specs=settings)
    
    return {
        "status": "success",
        "asset_id": asset_id,
        "image_url": web_url,
        "raw_image_path": temp_upload_path,
        "pagination": pagination
    }


@app.post("/api/assets/batch-upload/{book_id}")
async def batch_upload_assets(
    book_id: str,
    files: List[UploadFile] = File(...)
):
    """
    Batch Image Uploader for Step 3:
    Uploads multiple image files at once. Matches each filename to an asset slot:
    - If filename contains "frontispiece": saves frontispiece, updates front matter & processes 300 DPI raster.
    - If filename contains "map": saves map, updates front matter & processes 300 DPI raster.
    - Matches asset_id directly (e.g. "b01_asset_01", "asset_01")
    - Matches slot number (e.g. 01..16, "plate_01", "slot_02", "ch03")
    - Matches asset title substring
    - If unmatched, assigns to next available unfilled asset slot in manifest.
    For each matched asset, saves raw_image_path, runs process_image at 300 DPI with profile filter and frame style,
    updates manifest, invalidates PDF cache, and returns summary + updated pagination.
    """
    import re
    profile = BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"])
    manifest = manifest_manager.get_book_manifest(book_id)
    assets = manifest.get("assets", [])
    
    processed = []
    unmatched = []
    assigned_asset_ids = set()
    
    for f in files:
        filename = f.filename or "uploaded_image.png"
        fn_lower = filename.lower()
        fn_stem = os.path.splitext(fn_lower)[0]
        
        # Check if frontispiece
        if "frontispiece" in fn_stem:
            disk_path = os.path.join(UPLOADS_DIR, f"{book_id}_frontispiece_{filename}")
            with open(disk_path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            web_url = f"/uploads/{book_id}_frontispiece_{filename}"
            dpi300_path = os.path.join(STATIC_DIR, "assets", "placeholders", f"{book_id}_frontispiece_300dpi.png")
            try:
                process_image(
                    input_image_path=disk_path,
                    output_image_path=dpi300_path,
                    filter_preset=profile.get("filter_preset", "cyanotype_silver_plate"),
                    placement_type="Full Bleed Plate",
                    profile_id=book_id,
                    target_dpi=300
                )
            except Exception:
                pass
            settings = settings_manager.get_settings(book_id)
            fbm = settings.get("front_back_matter", {})
            fbm["frontispiece_image_url"] = web_url
            fbm["include_frontispiece"] = True
            settings_manager.update_settings(book_id, {"front_back_matter": fbm})
            processed.append({"filename": filename, "type": "frontispiece", "image_url": web_url})
            continue

        # Check if map
        if "map" in fn_stem:
            disk_path = os.path.join(UPLOADS_DIR, f"{book_id}_map_{filename}")
            with open(disk_path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            web_url = f"/uploads/{book_id}_map_{filename}"
            dpi300_path = os.path.join(STATIC_DIR, "assets", "placeholders", f"{book_id}_map_300dpi.png")
            try:
                process_image(
                    input_image_path=disk_path,
                    output_image_path=dpi300_path,
                    filter_preset=profile.get("filter_preset", "cyanotype_silver_plate"),
                    placement_type="Full Bleed Plate",
                    profile_id=book_id,
                    target_dpi=300
                )
            except Exception:
                pass
            settings = settings_manager.get_settings(book_id)
            fbm = settings.get("front_back_matter", {})
            fbm["map_image_url"] = web_url
            fbm["include_map"] = True
            settings_manager.update_settings(book_id, {"front_back_matter": fbm})
            processed.append({"filename": filename, "type": "map", "image_url": web_url})
            continue

        # Match to asset slot
        target_asset = None
        # 1. Exact or substring asset id
        for a in assets:
            aid = a.get("id", "").lower()
            if aid and (aid == fn_stem or aid in fn_stem):
                target_asset = a
                break

        # 2. Number pattern: e.g. "asset_01", "01", "slot_2", "plate-03", "ch04"
        if not target_asset:
            nums = re.findall(r'(\d+)', fn_stem)
            if nums:
                for n_str in nums:
                    num_val = int(n_str)
                    for idx, a in enumerate(assets, 1):
                        aid = a.get("id", "").lower()
                        aid_nums = re.findall(r'(\d+)$', aid)
                        if (aid_nums and int(aid_nums[0]) == num_val) or idx == num_val:
                            if a.get("id") not in assigned_asset_ids:
                                target_asset = a
                                break
                    if target_asset:
                        break

        # 3. Title substring
        if not target_asset:
            for a in assets:
                t = a.get("title", "").lower()
                if len(t) > 3 and t in fn_stem:
                    if a.get("id") not in assigned_asset_ids:
                        target_asset = a
                        break

        # 4. Fallback: first unassigned asset slot
        if not target_asset:
            for a in assets:
                aid = a.get("id")
                if aid not in assigned_asset_ids and not a.get("raw_image_path"):
                    target_asset = a
                    break

        if target_asset:
            aid = target_asset["id"]
            assigned_asset_ids.add(aid)
            temp_upload_path = os.path.join(UPLOADS_DIR, f"raw_{book_id}_{aid}_{filename}")
            with open(temp_upload_path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)

            filtered_name = f"{aid}_print300.png"
            out_path = os.path.join(STATIC_DIR, "assets", "placeholders", filtered_name)
            frame_style = target_asset.get("frame_style", "none")
            
            process_image(
                input_image_path=temp_upload_path,
                output_image_path=out_path,
                filter_preset=profile.get("filter_preset", "cyanotype_silver_plate"),
                placement_type=target_asset.get("placement", "Half-Page Top"),
                callouts=target_asset.get("vector_callouts", []),
                profile_id=book_id,
                frame_style=frame_style,
                target_dpi=300
            )

            web_url = f"/static/assets/placeholders/{filtered_name}"
            manifest_manager.update_asset(book_id, aid, {
                "image_url": web_url,
                "raw_image_path": temp_upload_path,
                "filter_applied": True
            })
            processed.append({
                "filename": filename,
                "asset_id": aid,
                "image_url": web_url,
                "raw_image_path": temp_upload_path
            })
        else:
            unmatched.append(filename)

    invalidate_pdf_cache(book_id)
    parsed = load_book_manuscript(book_id)
    updated_manifest = manifest_manager.get_book_manifest(book_id)
    updated_settings = settings_manager.get_settings(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(
        parsed,
        updated_manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=updated_settings,
        custom_matter=updated_settings.get("front_back_matter")
    )

    return {
        "status": "success",
        "processed_count": len(processed),
        "unmatched_count": len(unmatched),
        "processed": processed,
        "unmatched": unmatched,
        "manifest": updated_manifest,
        "pagination": pagination
    }


@app.post("/api/matter/upload-image/{book_id}/{image_type}")
async def upload_matter_image(
    book_id: str,
    image_type: str,
    file: UploadFile = File(...)
):
    if image_type not in ["frontispiece", "map"]:
        raise HTTPException(status_code=400, detail="image_type must be 'frontispiece' or 'map'")
        
    filename = file.filename or f"{image_type}.png"
    disk_path = os.path.join(UPLOADS_DIR, f"{book_id}_{image_type}_{filename}")
    with open(disk_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    web_url = f"/uploads/{book_id}_{image_type}_{filename}"
    
    # Process 300 DPI version for high-res print export
    dpi300_path = os.path.join(STATIC_DIR, "assets", "placeholders", f"{book_id}_{image_type}_300dpi.png")
    profile = BOOK_PROFILES.get(book_id, BOOK_PROFILES.get("book01", {}))
    try:
        process_image(
            input_image_path=disk_path,
            output_image_path=dpi300_path,
            filter_preset=profile.get("filter_preset", "cyanotype_silver_plate"),
            placement_type="Full Bleed Plate",
            profile_id=book_id,
            target_dpi=300
        )
    except Exception as e:
        print(f"Warning: could not process 300 DPI matter image: {e}")
    
    settings = settings_manager.get_settings(book_id)
    fbm = settings.get("front_back_matter", {})
    if image_type == "frontispiece":
        fbm["frontispiece_image_url"] = web_url
        fbm["include_frontispiece"] = True
    elif image_type == "map":
        fbm["map_image_url"] = web_url
        fbm["include_map"] = True
        
    settings_manager.update_settings(book_id, {"front_back_matter": fbm})
    invalidate_pdf_cache(book_id)
    
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    new_settings = settings_manager.get_settings(book_id)
    pagination = paginate_manuscript(
        parsed,
        manifest,
        book_id,
        auto_tailpieces=tailpieces,
        custom_specs=new_settings,
        custom_matter=new_settings.get("front_back_matter")
    )
    front_matter = generate_front_matter_data(book_id, parsed, new_settings.get("front_back_matter"))
    
    return {
        "status": "success",
        "image_type": image_type,
        "image_url": web_url,
        "settings": new_settings,
        "pagination": pagination,
        "front_matter": front_matter
    }


@app.post("/api/tailpiece/auto-insert")
async def auto_insert_tailpiece(payload: Dict[str, Any] = Body(...)):
    book_id = payload.get("book_id", STATE["active_book_id"])
    page_number = int(payload.get("page_number", 0))
    enable = bool(payload.get("enable", True))
    
    if book_id not in STATE["auto_tailpieces"]:
        STATE["auto_tailpieces"][book_id] = {}
        
    STATE["auto_tailpieces"][book_id][page_number] = enable
    invalidate_pdf_cache(book_id)
    
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    pagination = paginate_manuscript(
        parsed,
        manifest,
        book_id,
        auto_tailpieces=STATE["auto_tailpieces"][book_id],
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "book_id": book_id,
        "page_number": page_number,
        "pagination": pagination
    }


@app.post("/api/tailpiece/auto-balance-all")
async def auto_balance_all_short_endings(payload: Optional[Dict[str, Any]] = Body(None)):
    """
    1-Click Whitespace Balancer:
    Finds every chapter-ending page with < 18 lines of text and activates
    the book profile's thematic tailpiece ornament.
    """
    book_id = payload.get("book_id", STATE["active_book_id"]) if payload else STATE["active_book_id"]
    if book_id not in STATE["auto_tailpieces"]:
        STATE["auto_tailpieces"][book_id] = {}
        
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    
    # Pass 1: detect short chapter endings
    p1 = paginate_manuscript(
        parsed,
        manifest,
        book_id,
        auto_tailpieces=STATE["auto_tailpieces"][book_id],
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    balanced_pages = []
    for page in p1.get("pages", []):
        if page.get("short_ending"):
            pnum = page["page_number"]
            STATE["auto_tailpieces"][book_id][pnum] = True
            balanced_pages.append(pnum)
            
    invalidate_pdf_cache(book_id)
    
    # Pass 2: repaginate with all tailpieces applied
    final_pagination = paginate_manuscript(
        parsed,
        manifest,
        book_id,
        auto_tailpieces=STATE["auto_tailpieces"][book_id],
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    
    return {
        "status": "success",
        "book_id": book_id,
        "balanced_pages": balanced_pages,
        "balanced_count": len(balanced_pages),
        "pagination": final_pagination
    }


# ======================================================================
# 5. MULTI-FORMAT EXPORTERS (CUSTOM SPECS & MATTER SYNCED)
# ======================================================================

@app.post("/api/export/pdf")
async def export_pdf_endpoint(payload: Dict[str, Any] = Body(...)):
    book_id = payload.get("book_id", STATE["active_book_id"])
    bleed = bool(payload.get("bleed", False))
    
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    
    pdf_filename = f"{book_id}_print_edition.pdf"
    output_path = os.path.join(EXPORTS_DIR, pdf_filename)
    
    export_pdf(
        parsed,
        manifest,
        book_id,
        output_path,
        bleed=bleed,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=pdf_filename,
        headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'}
    )


@app.post("/api/export/docx")
async def export_docx_endpoint(payload: Dict[str, Any] = Body(...)):
    book_id = payload.get("book_id", STATE["active_book_id"])
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    
    docx_filename = f"{book_id}_styled_edition.docx"
    output_path = os.path.join(EXPORTS_DIR, docx_filename)
    
    export_docx(
        parsed,
        manifest,
        book_id,
        output_path,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=docx_filename,
        headers={"Content-Disposition": f'attachment; filename="{docx_filename}"'}
    )


@app.post("/api/export/epub")
async def export_epub_endpoint(payload: Dict[str, Any] = Body(...)):
    book_id = payload.get("book_id", STATE["active_book_id"])
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    
    epub_filename = f"{book_id}_reflowable_edition.epub"
    output_path = os.path.join(EXPORTS_DIR, epub_filename)
    
    export_epub(
        parsed,
        manifest,
        book_id,
        output_path,
        custom_specs=settings,
        custom_matter=settings.get("front_back_matter")
    )
    return FileResponse(
        output_path,
        media_type="application/epub+zip",
        filename=epub_filename,
        headers={"Content-Disposition": f'attachment; filename="{epub_filename}"'}
    )


@app.post("/api/export/all")
async def export_all_endpoint(payload: Dict[str, Any] = Body(...)):
    book_id = payload.get("book_id", STATE["active_book_id"])
    bleed = bool(payload.get("bleed", False))
    
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    settings = settings_manager.get_settings(book_id)
    
    pdf_path = os.path.join(EXPORTS_DIR, f"{book_id}_print_edition.pdf")
    docx_path = os.path.join(EXPORTS_DIR, f"{book_id}_styled_edition.docx")
    epub_path = os.path.join(EXPORTS_DIR, f"{book_id}_reflowable_edition.epub")
    
    export_pdf(parsed, manifest, book_id, pdf_path, bleed=bleed, custom_specs=settings, custom_matter=settings.get("front_back_matter"))
    export_docx(parsed, manifest, book_id, docx_path, custom_specs=settings, custom_matter=settings.get("front_back_matter"))
    export_epub(parsed, manifest, book_id, epub_path, custom_specs=settings, custom_matter=settings.get("front_back_matter"))
    
    zip_filename = f"{book_id}_ArgonPublishingPackage.zip"
    zip_path = os.path.join(EXPORTS_DIR, zip_filename)
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        if os.path.exists(pdf_path):
            zipf.write(pdf_path, arcname=os.path.basename(pdf_path))
        if os.path.exists(docx_path):
            zipf.write(docx_path, arcname=os.path.basename(docx_path))
        if os.path.exists(epub_path):
            zipf.write(epub_path, arcname=os.path.basename(epub_path))
            
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_filename,
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )
