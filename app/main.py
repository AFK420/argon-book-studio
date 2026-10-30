"""
Argon Book Studio - Main FastAPI Application.
Desktop publishing server for illustrated novel typesetting and multi-format publication.
"""

import json
import os
import shutil
import zipfile
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.profiles import BOOK_PROFILES, UNIVERSAL_PUBLISHING_SPECS
from app.parser import parse_markdown_manuscript, parse_docx_manuscript
from app.manifest import manifest_manager
from app.filters import process_image, generate_procedural_placeholder
from app.paginator import paginate_manuscript
from app.front_back_matter import generate_front_matter_data
from app.exporters.pdf_exporter import export_pdf
from app.exporters.docx_exporter import export_docx
from app.exporters.epub_exporter import export_epub

app = FastAPI(
    title="Argon Book Studio",
    description="Drag-and-Drop Illustrated Novel Typesetting & Publishing Engine",
    version="1.0.0"
)

# CORS configuration
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

# In-memory session state for active books & auto-tailpieces
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
        return parse_markdown_manuscript(content)
        
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
        "specs": UNIVERSAL_PUBLISHING_SPECS
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
    pagination = paginate_manuscript(parsed, manifest, book_id, auto_tailpieces=tailpieces)
    front_matter = generate_front_matter_data(book_id, parsed)
    
    return {
        "book_id": book_id,
        "profile": BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"]),
        "manuscript": parsed,
        "manifest": manifest,
        "pagination": pagination,
        "front_matter": front_matter
    }


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
    
    manifest = manifest_manager.get_book_manifest(book_id)
    pagination = paginate_manuscript(parsed, manifest, book_id)
    
    return {
        "status": "success",
        "book_id": book_id,
        "filename": filename,
        "parsed": parsed,
        "pagination": pagination
    }


@app.post("/api/manifest/{book_id}/update-anchor")
async def update_asset_anchor(
    book_id: str,
    payload: Dict[str, Any] = Body(...)
):
    asset_id = payload.get("asset_id")
    new_anchor = payload.get("new_anchor")
    if not asset_id or not new_anchor:
        raise HTTPException(status_code=400, detail="Missing asset_id or new_anchor")
        
    updated = manifest_manager.update_anchor(book_id, asset_id, new_anchor)
    if not updated:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, manifest, book_id, auto_tailpieces=tailpieces)
    
    return {
        "status": "success",
        "asset_id": asset_id,
        "new_anchor": new_anchor,
        "pagination": pagination
    }


@app.post("/api/manifest/{book_id}/add-slot")
async def add_illustration_slot(
    book_id: str,
    payload: Dict[str, Any] = Body(...)
):
    title = payload.get("title", "New Planned Illustration")
    anchor = payload.get("anchor", "ch01_p01")
    placement = payload.get("placement", "Half-Page Top")
    prompt = payload.get("prompt", "Atmospheric etching matching book theme")
    caption = payload.get("caption", f"Plate: {title}")
    
    profile = BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"])
    asset_id = f"{book_id}_asset_{len(manifest_manager.get_book_manifest(book_id).get('assets', [])) + 1:02d}"
    
    # Generate procedural base plate
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
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, manifest, book_id, auto_tailpieces=tailpieces)
    
    return {
        "status": "success",
        "slot": slot_data,
        "pagination": pagination
    }


@app.delete("/api/manifest/{book_id}/delete-slot/{asset_id}")
async def delete_slot(book_id: str, asset_id: str):
    res = manifest_manager.delete_asset(book_id, asset_id)
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, manifest, book_id, auto_tailpieces=tailpieces)
    return {"status": "success", "deleted": res, "pagination": pagination}


@app.post("/api/manifest/{book_id}/update-callouts")
async def update_callouts(
    book_id: str,
    payload: Dict[str, Any] = Body(...)
):
    asset_id = payload.get("asset_id")
    callouts = payload.get("callouts", [])
    
    asset = manifest_manager.update_asset(book_id, asset_id, {"vector_callouts": callouts})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    # Re-apply filter and vector callouts to image
    img_url = asset.get("image_url", "")
    if img_url.startswith("/static/"):
        disk_path = os.path.join(BASE_DIR, img_url.lstrip("/"))
        if os.path.exists(disk_path):
            profile = BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"])
            generate_procedural_placeholder(
                output_path=disk_path,
                title=asset.get("title", ""),
                prompt=asset.get("prompt", ""),
                placement_type=asset.get("placement", "Half-Page Top"),
                filter_preset=profile.get("filter_preset", "cyanotype_silver_plate"),
                profile_id=book_id,
                callouts=callouts
            )
            
    return {"status": "success", "asset": asset}


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
        
    # Output filtered 300 DPI image
    filtered_name = f"{asset_id}_print300.png"
    out_path = os.path.join(STATIC_DIR, "assets", "placeholders", filtered_name)
    
    process_image(
        input_image_path=temp_upload_path,
        output_image_path=out_path,
        filter_preset=profile.get("filter_preset", "cyanotype_silver_plate"),
        placement_type=asset.get("placement", "Half-Page Top"),
        callouts=asset.get("vector_callouts", []),
        profile_id=book_id
    )
    
    web_url = f"/static/assets/placeholders/{filtered_name}"
    manifest_manager.update_asset(book_id, asset_id, {
        "image_url": web_url,
        "filter_applied": True
    })
    
    parsed = load_book_manuscript(book_id)
    updated_manifest = manifest_manager.get_book_manifest(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, updated_manifest, book_id, auto_tailpieces=tailpieces)
    
    return {
        "status": "success",
        "asset_id": asset_id,
        "image_url": web_url,
        "pagination": pagination
    }


@app.post("/api/assets/apply-filter/{book_id}/{asset_id}")
async def apply_filter(
    book_id: str,
    asset_id: str,
    payload: Dict[str, Any] = Body(...)
):
    filter_preset = payload.get("filter_preset")
    profile = BOOK_PROFILES.get(book_id, BOOK_PROFILES["book01"])
    if not filter_preset:
        filter_preset = profile.get("filter_preset", "cyanotype_silver_plate")
        
    manifest = manifest_manager.get_book_manifest(book_id)
    asset = next((a for a in manifest.get("assets", []) if a.get("id") == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset slot not found")
        
    img_url = asset.get("image_url", "")
    target_disk_path = os.path.join(STATIC_DIR, "assets", "placeholders", f"{asset_id}_custom_filtered.png")
    
    # Re-process either existing image or re-generate procedural plate
    generate_procedural_placeholder(
        output_path=target_disk_path,
        title=asset.get("title", ""),
        prompt=asset.get("prompt", ""),
        placement_type=asset.get("placement", "Half-Page Top"),
        filter_preset=filter_preset,
        profile_id=book_id,
        callouts=asset.get("vector_callouts", [])
    )
    
    new_url = f"/static/assets/placeholders/{asset_id}_custom_filtered.png"
    manifest_manager.update_asset(book_id, asset_id, {
        "image_url": new_url,
        "filter_applied": True
    })
    
    parsed = load_book_manuscript(book_id)
    updated_manifest = manifest_manager.get_book_manifest(book_id)
    tailpieces = STATE["auto_tailpieces"].get(book_id, {})
    pagination = paginate_manuscript(parsed, updated_manifest, book_id, auto_tailpieces=tailpieces)
    
    return {
        "status": "success",
        "asset_id": asset_id,
        "filter_preset": filter_preset,
        "image_url": new_url,
        "pagination": pagination
    }


@app.post("/api/tailpiece/auto-insert")
async def auto_insert_tailpiece(payload: Dict[str, Any] = Body(...)):
    book_id = payload.get("book_id", STATE["active_book_id"])
    page_number = int(payload.get("page_number", 0))
    enable = bool(payload.get("enable", True))
    
    if book_id not in STATE["auto_tailpieces"]:
        STATE["auto_tailpieces"][book_id] = {}
        
    STATE["auto_tailpieces"][book_id][page_number] = enable
    
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    pagination = paginate_manuscript(parsed, manifest, book_id, auto_tailpieces=STATE["auto_tailpieces"][book_id])
    
    return {
        "status": "success",
        "book_id": book_id,
        "page_number": page_number,
        "pagination": pagination
    }


@app.post("/api/export/pdf")
async def export_pdf_endpoint(payload: Dict[str, Any] = Body(...)):
    book_id = payload.get("book_id", STATE["active_book_id"])
    bleed = bool(payload.get("bleed", False))
    
    parsed = load_book_manuscript(book_id)
    manifest = manifest_manager.get_book_manifest(book_id)
    
    pdf_filename = f"{book_id}_print_6x9_{'bleed' if bleed else 'standard'}.pdf"
    output_path = os.path.join(EXPORTS_DIR, pdf_filename)
    
    export_pdf(parsed, manifest, book_id, output_path, bleed=bleed)
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
    
    docx_filename = f"{book_id}_styled_6x9.docx"
    output_path = os.path.join(EXPORTS_DIR, docx_filename)
    
    export_docx(parsed, manifest, book_id, output_path)
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
    
    epub_filename = f"{book_id}_reflowable_epub3.epub"
    output_path = os.path.join(EXPORTS_DIR, epub_filename)
    
    export_epub(parsed, manifest, book_id, output_path)
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
    
    pdf_path = os.path.join(EXPORTS_DIR, f"{book_id}_print_6x9.pdf")
    docx_path = os.path.join(EXPORTS_DIR, f"{book_id}_styled_6x9.docx")
    epub_path = os.path.join(EXPORTS_DIR, f"{book_id}_reflowable.epub")
    
    export_pdf(parsed, manifest, book_id, pdf_path, bleed=bleed)
    export_docx(parsed, manifest, book_id, docx_path)
    export_epub(parsed, manifest, book_id, epub_path)
    
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
