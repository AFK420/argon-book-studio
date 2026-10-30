# ARGON BOOK STUDIO PRO
### Drag-and-Drop Illustrated Novel Typesetting & Publishing Engine

**Argon Book Studio Pro** is an advanced, local desktop publishing application engineered with **Python FastAPI**, **WeasyPrint / Chromium CSS Paged Media**, **python-docx**, and **ebooklib**, featuring a real-time **HTML5 Drag-and-Drop Live 2-Page Spread Preview** frontend.

It provides complete control over book geometry, margins, typography, vector callouts, print texture filters, and front/back matter to generate print-ready collector's editions, styled Microsoft Word (`.docx`) manuscripts, and reflowable EPUB 3 publications.

---

## 1. Core Architectural Pillars

### I. Live Typesetting Geometry & Margin Inspector
Adjust your publication's physical dimensions and margins on the fly with live mathematical recalculation of line capacities:
* **Trim Size Presets:** `6.0 × 9.0"` (Standard US Trade), `5.5 × 8.5"` (Digest), `5.0 × 8.0"` (Pocket Fiction), `7.0 × 10.0"` (Executive Plate), or Custom.
* **Mirrored Margin Sliders:**
  * **Inside Gutter:** `0.50"` to `1.375"` (calibrated for spine binding fold).
  * **Outside Margin:** `0.375"` to `1.125"`.
  * **Top Margin:** `0.50"` to `1.25"`.
  * **Bottom Margin:** `0.50"` to `1.25"`.
* **Typography & Leading:**
  * Body font selector with live size slider (`9.0pt` to `13.5pt`) and leading slider (`12.0pt` to `18.5pt`).
  * Display font selector for chapter titles and drop caps.
  * First-line indent slider (`0.0"` to `0.50"`).
  * Chapter opening sinkage slider (`1.0"` to `2.75"`).
* **Paper Tint Palette:** Antique Cream (`#FBF8F1`), Ochre Vellum (`#FAF6EE`), Slate Crisp (`#F5F6F8`), and Pure White (`#FFFFFF`).
* **Running Headers:** Custom text overrides and tracked small-caps controls.

---

### II. Click-to-Edit Inline Manuscript Studio
Never leave the spread preview to fix a typo or test line breaks:
* **Direct Spread Editing:** Click any paragraph or container directly in the 2-page spread preview to edit text. As you type, line capacity and pagination recalculate live.
* **In-Spread Element Toolbar:**
  * **✓ Save Edit:** Persists changes directly into the manuscript session.
  * **❖ Break:** Inserts a thematic SVG scene break divider after the selected element.
  * **📦 Box:** Wraps the paragraph in in-world containers (`.inquest-writ`, `.welsh-slate`, `.audio-transcript`, `.pelham-journal`, `.cuneiform-tablet`).

---

### III. Visual "Click-to-Drop" Vector Callout Studio
Eliminate AI text hallucinations inside illustrations and diagrams:
* **Interactive Canvas:** Open any illustration plate in a high-resolution workspace.
* **Click to Drop Pins:** Click anywhere on the plate to drop a precision vector callout pin.
* **Drag to Reposition:** Drag pins with mouse precision to point at technical or epigraphic details.
* **Pin Styles:** Badges, Technical Boxes, Crosshairs, Arrow Pointers (Up, Down, Left, Right).
* **High-DPI Vector Rendering:** Renders vector callouts over images using Pillow at 300/600 DPI.

---

### IV. Image Print Lab with Interactive Split Before/After Slider
Fine-tune illustrations to match the exact artistic medium of each book:
* **Split Comparison Slider:** Drag a vertical divider across the image to see raw uploads vs print-processed plates side-by-side.
* **Medium Presets:**
  * *Cyanotype / 19th-Century Silver-Plate Etching*
  * *Charcoal & Hebridean Lithograph Wash*
  * *High-Contrast Oscilloscope & Architectural Blueprint Halftone*
  * *1928 Sepia & Bioluminescent Amber Botanical Plate*
  * *Desert Ochre & UV-Fluorescence Archaeometric Micro-Grain*
* **Parameter Sliders:** Grain Intensity (0%–22%), Contrast & Shadow Depth (0.7x–2.2x), and Edge Vignette (0%–75%).
* **Resolution Scaling:** Resamples and saves at 300 DPI or 600 DPI Ultra-Fine.

---

### V. Bird's-Eye Thumbnail Filmstrip
* Collapsible horizontal filmstrip dock at the bottom of the canvas showing every 2-page spread in the book.
* Click any thumbnail to jump to that spread.
* Color-coded indicator chips:
  * `Ch` — Chapter Opener page.
  * `Pl` — Full-Page Illustration Plate.
  * `⚠️` — Short Ending (< 18 lines).
  * `Fm` — Front Matter.

---

### VI. Extended Front & Back Matter Customizer
Comprehensive publishing structure configured via a dedicated panel:
* **Front Matter:** Half-Title, Thematic Frontispiece, Full Title Page with custom imprint and city, Copyright & ISBN block, Dedication Page, Epigraph Page, and Auto-Calculated Table of Contents.
* **Back Matter:** Acknowledgements, About the Author biographical note, and Typesetting Colophon.

---

### VII. Dynamic Multi-Format Export Sync
Every adjustment made in the Geometry Inspector, Typography Sliders, Front/Back Matter Customizer, and Image Lab is synchronized into all export formats:
* **[PDF] Print-Ready 6×9" (or Custom Trim) PDF:** Generated with CSS Paged Media `@page` mirrored margins, headers, and footers.
* **[DOCX] Styled Word Manuscript:** Configured with custom page dimensions, section margins, paragraph indentation, and styled container tables.
* **[EPUB] Reflowable EPUB 3:** Compliant publication with embedded CSS matching your typography.
* **[ZIP] Release Bundle:** Compiles PDF, DOCX, and EPUB into a single package.

---

## 2. Five Selectable Book Theme Profiles

| Profile | Title & Genre | Typography (Body / Display) | In-World Containers | Scene Break & Tailpiece | Image Filter Medium (300 DPI) |
|---|---|---|---|---|---|
| **01** | *Cormac Vane: The Alchemical Inquest* (Gaslamp Forensic) | EB Garamond (11pt / 15pt) • Cinzel (`#1B365D`) | `.inquest-writ`, `.sensory-draw` | Brass Caliper & Gear Diamond | Cyanotype / 19th-C Silver Plate |
| **02** | *The Fourteen-Hour Barometer* (Chronometric Thriller) | Lora (10.5pt / 14.5pt) • Oswald Bold (`#1E2229`) | `.welsh-slate`, `.telemetry-equation` | Split Piezoelectric Wave-Fault Line | Charcoal & Hebridean Lithograph |
| **03** | *Dead-Room Transcripts* (Acoustic Locked-Room) | Source Serif 4 (10.5pt / 14.5pt) • JetBrains Mono | `.audio-transcript`, `.fsk-payload` | 42.4 Hz Sine-Wave Dampening Pulse | Oscilloscope & Blueprint Halftone |
| **04** | *The Salt Orchard of Saint Jude* (Southern Gothic) | Cormorant Garamond (11.5pt / 15.2pt) • Garamond Italic | `.pelham-journal`, `.oscilloscope-readout` | Intertwined Sea-Fig Root & Seahorse | 1928 Sepia & Bioluminescent Amber |
| **05** | *Provenance of Ashes* (Archaeometric Thriller) | Crimson Pro (10.5pt / 14.5pt) • Trajan Decorative | `.cuneiform-tablet`, `.cedar-sliver` | Triple Cuneiform Wedge Divider | Desert Ochre & UV-Fluorescence Micro-Grain |

---

## 3. Quick Start & Execution

### 1. Launch the Studio
```powershell
python run.py
```
Open your browser to: **`http://127.0.0.1:8000`**

### 2. Run the Verification Test Suite
```powershell
python -m pytest tests/ --basetemp="D:\The Argon Book Studio\tmp_test" -v
```
*(All 25 unit and integration tests passing: specifications, theme profiles, settings manager, parsers, filters, paginator, filmstrip, inline editing, and multi-format exporters).*

---

## 4. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web studio UI |
| `GET` | `/api/profiles` | Theme profiles, specs, and trim presets |
| `GET` | `/api/books` | Bundled books list |
| `GET` | `/api/book/{book_id}` | Full book state (manuscript, manifest, settings, spreads, filmstrip) |
| `GET` | `/api/project/{book_id}/settings` | Current geometry and typography settings |
| `POST` | `/api/project/{book_id}/settings` | Update geometry, margins, typography, matter |
| `POST` | `/api/project/{book_id}/reset-settings`| Reset book geometry to defaults |
| `POST` | `/api/manuscript/{book_id}/edit-element`| Inline paragraph/container editing |
| `POST` | `/api/manuscript/{book_id}/insert-element`| Insert paragraph, scene break, or container |
| `POST` | `/api/manuscript/{book_id}/wrap-container`| Wrap element into custom container |
| `POST` | `/api/image-lab/preview` | Generate split before/after comparison preview |
| `POST` | `/api/image-lab/apply` | Apply 300 DPI filter parameters to plate |
| `POST` | `/api/manifest/{book_id}/update-callouts`| Save precision vector callout pins |
| `POST` | `/api/tailpiece/auto-insert` | 1-click whitespace balancing tailpiece |
| `POST` | `/api/export/pdf` | Export PDF synced with live geometry |
| `POST` | `/api/export/docx` | Export DOCX synced with live geometry |
| `POST` | `/api/export/epub` | Export reflowable EPUB 3 |
| `POST` | `/api/export/all` | Export complete release ZIP bundle |
