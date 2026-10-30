# ARGON BOOK STUDIO
### Drag-and-Drop Illustrated Novel Typesetting & Publishing Engine

**Argon Book Studio** is a local, desktop publishing application engineered with **Python FastAPI** and a modern **HTML5 Drag-and-Drop Live 2-Page Spread Preview** frontend. It transforms manuscripts into print-ready 6x9" illustrated editions, styled editable Microsoft Word (`.docx`) files, and reflowable EPUB 3 publications.

---

## 1. Universal Publishing Engine (Hardcoded Production Rules)
All books conform to standard physical book production rules:
- **Trim Size:** 6.0 in x 9.0 in (with optional `+0.125 in` bleed toggle for full-bleed illustration plates).
- **Mirrored Print Margins:**
  - **Inside Gutter:** `0.875 in` (toward book spine).
  - **Outside Margin:** `0.625 in`.
  - **Top Margin:** `0.75 in`.
  - **Bottom Margin:** `0.875 in`.
- **Grid & Pagination Rules:**
  - Strict widow and orphan suppression (`orphans: 3; widows: 3;`).
  - First paragraph after chapter openings, subheaders, scene breaks, or inline illustrations has `text-indent: 0`; all subsequent body paragraphs have `text-indent: 0.25 in; margin-bottom: 0;`.
  - Optical margin alignment (`hanging-punctuation: first last`).
  - **Running Headers:** Verso (even pages) displays the Book Title in tracked small-caps (`8.5pt`); Recto (odd pages) displays the Chapter Number & Title in tracked small-caps (`8.5pt`).
  - **Automatic Header/Footer Suppression:** Running headers and page numbers are suppressed on `@page :first`, Front Matter pages, Part Dividers, Chapter Opening pages, Full-Page Illustration Plates, and trailing blank pages.
  - **Chapter Openings:** Always break to a fresh page (`page-break-before: always`) with a `1.75 in` top sinkage.

---

## 2. Five Selectable Book Theme Profiles
Switchable via the UI dropdown or API, automatically swapping typography, ornaments, and containers:

| Profile | Book Title & Genre | Typography (Body / Display) | Custom Containers | Scene Break & Tailpiece | Image Filter Preset (300 DPI) |
|---|---|---|---|---|---|
| **01** | *Cormac Vane: The Alchemical Inquest* (Gaslamp Forensic) | EB Garamond / Cinzel | `.inquest-writ`, `.sensory-draw` | Brass Caliper & Gear Diamond | Cyanotype / 19th-Century Silver-Plate Etching |
| **02** | *The Fourteen-Hour Barometer* (Chronometric Island Thriller) | Lora / Oswald Bold | `.welsh-slate`, `.telemetry-equation` | Split Piezoelectric Wave-Fault Line | Charcoal & Hebridean Lithograph Wash |
| **03** | *Dead-Room Transcripts* (Acoustic Locked-Room) | Source Serif 4 / JetBrains Mono | `.audio-transcript`, `.fsk-payload` | 42.4 Hz Sine-Wave Dampening Pulse | High-Contrast Oscilloscope & Blueprint Halftone |
| **04** | *The Salt Orchard of Saint Jude* (Ecological Southern Gothic) | Cormorant Garamond / Garamond Italic | `.pelham-journal`, `.oscilloscope-readout` | Intertwined Sea-Fig Root & Seahorse Vignette | 1928 Sepia & Bioluminescent Amber Botanical Plate |
| **05** | *Provenance of Ashes* (Archaeometric Thriller) | Crimson Pro / Trajan Decorative | `.cuneiform-tablet`, `.cedar-sliver` | Triple Cuneiform Wedge Divider | Desert Ochre & UV-Fluorescence Micro-Grain |

---

## 3. Visual Workspace & Drag-and-Drop Features

### Panel 1: Manuscript & Anchor Tree (Left)
- Deconstructs `.docx` and `.md` manuscripts into structured Chapters and numbered Paragraphs (`ch01_p01`, `ch01_p02`, etc.).
- Pre-populates planned illustration slots from `book_layout_manifest.json`.
- Displays asset cards with Title, Placement Badge (`Full-Page Recto Plate`, `Half-Page Top`, `Inline Archival Insert`, `Chapter Opener Vignette`, `Chapter End Tailpiece`), Ready-to-Copy Image Prompt, and Vector Callout Chips.
- Drag handle allows moving slots directly between paragraphs.

### Panel 2: Live 2-Page Spread Preview & Drag-and-Drop Canvas (Center)
- True 6x9" Verso (left/even) and Recto (right/odd) spread visualization with book fold gutter shadows.
- Toggleable **Mirrored Margins & Gutter Overlay** and **0.125" Bleed Zone Guide**.
- Live running headers, page numbers, and chapter opening sinkage with ornamental drop caps.
- Users can drag illustration files from their desktop directly onto slots, or drag slots between paragraphs to dynamically re-paginate.
- **Short Chapter Ending Detection:** Detects pages with `< 18` lines of text and shows a 1-click **"Auto-Insert Tailpiece Ornament"** banner to balance whitespace.

### Panel 3: Post-Processing & One-Click Export Suite (Right)
- **Apply Book Print Texture Filter:** Executes Python Pillow algorithms to match the book's artistic medium at 300 DPI.
- **Vector Text Callout Overlay:** Overlays crisp, non-hallucinated vector labels, boxes, and arrows over maps and diagrams.
- **Front & Back Matter Generator:** Produces Half-Title, Frontispiece, Title Page, Copyright, Table of Contents, and Colophon.
- **Export All Formats:** One-click downloads for:
  - `PDF` (Print-Ready 6x9" with mirrored margins and bleed options)
  - `DOCX` (Fully styled editable Word document)
  - `EPUB 3` (Reflowable EPUB with embedded CSS)
  - `ZIP` (Complete Publishing Release Package)

---

## 4. Quick Start

### 1. Launch the Application
```powershell
python run.py
```
Open your browser to: **`http://127.0.0.1:8000`**

### 2. Run the Automated Test Suite
```powershell
python -m pytest tests/ --basetemp="D:\The Argon Book Studio\tmp_test" -v
```

---

## 5. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web publishing studio UI |
| `GET` | `/api/profiles` | Returns all 5 Book Theme Profiles & universal specs |
| `GET` | `/api/books` | Returns bundled book list |
| `GET` | `/api/book/{book_id}` | Loads parsed chapters, manifest, and live pagination |
| `POST` | `/api/manuscript/upload` | Upload custom `.docx` or `.md` manuscript |
| `POST` | `/api/manifest/{book_id}/update-anchor` | Move slot anchor (`ch01_p02` -> `ch01_p05`) |
| `POST` | `/api/manifest/{book_id}/add-slot` | Add planned illustration slot |
| `POST` | `/api/manifest/{book_id}/update-callouts`| Save vector text callouts |
| `POST` | `/api/assets/upload/{book_id}/{asset_id}` | Upload illustration image (applies 300 DPI filter) |
| `POST` | `/api/assets/apply-filter/{book_id}/{asset_id}` | Switch medium texture filter |
| `POST` | `/api/tailpiece/auto-insert` | 1-click auto-insert tailpiece ornament |
| `POST` | `/api/export/pdf` | Download print-ready 6x9" PDF |
| `POST` | `/api/export/docx` | Download styled 6x9" DOCX |
| `POST` | `/api/export/epub` | Download reflowable EPUB 3 |
| `POST` | `/api/export/all` | Download complete release ZIP |
