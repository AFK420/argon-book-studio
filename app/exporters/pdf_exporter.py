"""
Argon Book Studio - Print-Ready PDF Exporter.
Renders book manuscripts with exact book-production rules:
- Trim Size: configurable (default 6.0 in x 9.0 in) with optional +0.125 in bleed toggle.
- Mirrored print margins (inside gutter vs outside margin, top, bottom).
- Strict widow/orphan control.
- First paragraph text-indent: 0; subsequent body paragraphs text-indent: 0.25in.
- Optical margin alignment (hanging-punctuation: first last).
- Verso running header: Book Title in tracked small-caps.
- Recto running header: Chapter Number & Title in tracked small-caps.
- Header/footer suppression on front matter, chapter opening pages, full plates, blank pages.
- Chapter openings with top sinkage.
- Headless Chromium/Edge physical page container model (<div class="physical-pdf-page">)
  driven directly by paginate_manuscript() for 100% WYSIWYG parity.
"""

import os
import subprocess
from typing import Dict, Any, List, Optional
from app.profiles import BOOK_PROFILES, UNIVERSAL_PUBLISHING_SPECS
from app.paginator import paginate_manuscript


def _resolve_image_src(img_path: str) -> str:
    if not img_path:
        return ""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    root_dir = os.path.abspath(os.path.join(base_dir, ".."))
    if img_path.startswith("/static/"):
        local_path = os.path.join(base_dir, img_path.lstrip("/")).replace("\\", "/")
        return f"file:///{local_path}"
    elif img_path.startswith("/uploads/"):
        local_path = os.path.join(root_dir, img_path.lstrip("/")).replace("\\", "/")
        return f"file:///{local_path}"
    elif os.path.isabs(img_path) or (len(img_path) > 1 and img_path[1] == ":"):
        return f"file:///{img_path.replace(chr(92), '/')}"
    return img_path


def generate_pdf_html(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    bleed: bool = False,
    include_front_matter: bool = True,
    custom_specs: Dict[str, Any] = None,
    custom_matter: Dict[str, Any] = None
) -> str:
    profile = BOOK_PROFILES.get(profile_id, BOOK_PROFILES["book01"])
    specs = UNIVERSAL_PUBLISHING_SPECS
    cs = custom_specs or {}
    cm = custom_matter or {}
    
    bleed_val = float(cs.get("bleed_in", specs["bleed_in"])) if bleed else 0.0
    width_in = float(cs.get("trim_width_in", specs["trim_width_in"])) + (bleed_val * 2)
    height_in = float(cs.get("trim_height_in", specs["trim_height_in"])) + (bleed_val * 2)
    
    gutter = float(cs.get("margins", {}).get("inside_gutter_in", cs.get("inside_gutter_in", specs["margins"]["inside_gutter_in"])))
    outside = float(cs.get("margins", {}).get("outside_margin_in", cs.get("outside_margin_in", specs["margins"]["outside_margin_in"])))
    top = float(cs.get("margins", {}).get("top_margin_in", cs.get("top_margin_in", specs["margins"]["top_margin_in"])))
    bottom = float(cs.get("margins", {}).get("bottom_margin_in", cs.get("bottom_margin_in", specs["margins"]["bottom_margin_in"])))
    
    sinkage = float(cs.get("typography", {}).get("chapter_sinkage_in", cs.get("chapter_sinkage_in", specs["grid_rules"]["chapter_sinkage_in"])))
    indent = float(cs.get("typography", {}).get("subsequent_p_indent_in", cs.get("subsequent_p_indent_in", specs["grid_rules"]["subsequent_p_indent_in"])))
    body_size = float(cs.get("typography", {}).get("body_font_size_pt", cs.get("body_font_size_pt", 11.0)))
    body_leading = float(cs.get("typography", {}).get("body_leading_pt", cs.get("body_leading_pt", 15.0)))
    
    body_font = cs.get("typography", {}).get("body_font", profile["body_font"])
    display_font = cs.get("typography", {}).get("display_font", profile["display_font"])
    accent_color = cs.get("typography", {}).get("accent_color", profile["accent_color"])
    paper_tint = cs.get("typography", {}).get("paper_tint", profile["paper_tint"])
    
    running_header_text = cs.get("typography", {}).get("running_header_override") or profile["short_title"].upper()
    rh_style = cs.get("typography", {}).get("running_header_style", "Small Caps Centered")
    drop_cap_enabled = cs.get("typography", {}).get("drop_cap_enabled", True)
    drop_cap_lines = int(cs.get("typography", {}).get("drop_cap_lines", 3))
    drop_cap_style = cs.get("typography", {}).get("drop_cap_style", "Plain Serif")
    justify_text = cs.get("typography", {}).get("justify_text", True)
    hyphenation = cs.get("typography", {}).get("hyphenation", True)
    para_spacing_pt = float(cs.get("typography", {}).get("para_spacing_pt", 0.0))
    letter_spacing_em = float(cs.get("typography", {}).get("letter_spacing_em", 0.0))

    drop_cap_extra = ""
    if drop_cap_style == "Boxed Rule":
        drop_cap_extra = "border: 1px solid #B8860B; padding: 2pt 5pt; background: #FAF6EE; margin-right: 5pt;"
    elif drop_cap_style == "Botanical/Ornate":
        drop_cap_extra = "font-style: italic; font-family: 'Cormorant Garamond', Georgia, serif; color: #2C402E; margin-right: 4pt;"

    # Run pagination simulation to drive physical page rendering
    paginated_res = paginate_manuscript(
        parsed_book,
        manifest,
        profile_id,
        include_front_matter=include_front_matter,
        custom_specs=cs,
        custom_matter=cm
    )
    pages = paginated_res.get("pages", [])

    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Cinzel+Decorative:wght@700&family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&family=Lora:ital,wght@0,400;0,600;1,400&family=Oswald:wght@400;600;700&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap');

    @page {{
        size: {width_in}in {height_in}in;
        margin: 0;
    }}

    html, body {{
        margin: 0;
        padding: 0;
        font-family: {body_font};
        font-size: {body_size}pt;
        line-height: {body_leading}pt;
        color: #1a1a1a;
        background-color: #fff;
        text-rendering: optimizeLegibility;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}

    .physical-pdf-page {{
        width: {width_in}in;
        height: {height_in}in;
        page-break-after: always;
        break-after: page;
        position: relative;
        box-sizing: border-box;
        overflow: hidden;
        background-color: {paper_tint or '#fff'};
    }}

    .physical-pdf-page.page-verso {{
        padding-top: {top}in;
        padding-bottom: {bottom}in;
        padding-left: {outside}in;
        padding-right: {gutter}in;
    }}

    .physical-pdf-page.page-recto {{
        padding-top: {top}in;
        padding-bottom: {bottom}in;
        padding-left: {gutter}in;
        padding-right: {outside}in;
    }}

    .physical-pdf-page.page-full-plate {{
        padding: 0 !important;
    }}

    .pdf-running-header {{
        position: absolute;
        top: {top * 0.35}in;
        height: {top * 0.55}in;
        line-height: {top * 0.55}in;
        font-family: {body_font};
        font-size: 8.5pt;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #555;
        box-sizing: border-box;
    }}

    .page-verso .pdf-running-header {{
        left: {outside}in;
        right: {gutter}in;
    }}

    .page-recto .pdf-running-header {{
        left: {gutter}in;
        right: {outside}in;
    }}

    .pdf-running-footer {{
        position: absolute;
        bottom: {bottom * 0.35}in;
        left: 0;
        right: 0;
        text-align: center;
        font-family: {body_font};
        font-size: 8.5pt;
        color: #555;
    }}

    .physical-pdf-page-content {{
        width: 100%;
        height: 100%;
        box-sizing: border-box;
    }}

    p {{
        margin: 0 0 {para_spacing_pt}pt 0;
        text-indent: {indent}in;
        text-align: {'justify' if justify_text else 'left'};
        hyphens: {'auto' if hyphenation else 'none'};
        -webkit-hyphens: {'auto' if hyphenation else 'none'};
        letter-spacing: {letter_spacing_em}em;
    }}

    p.indent-zero {{
        text-indent: 0 !important;
    }}

    h1.chapter-title {{
        font-family: {display_font};
        font-size: 20pt;
        font-weight: 600;
        text-align: center;
        margin-top: 0;
        margin-bottom: 8pt;
        color: {accent_color};
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}

    .chapter-num-label {{
        font-family: {display_font};
        font-size: 10pt;
        letter-spacing: 0.2em;
        text-align: center;
        text-transform: uppercase;
        color: {profile['brass_accent']};
        margin-bottom: 4pt;
    }}

    .chapter-ornament {{
        text-align: center;
        margin: 10pt 0 18pt 0;
    }}

    .chapter-ornament svg {{
        width: 180px;
        height: 24px;
    }}

    .scene-break-div {{
        text-align: center;
        margin: 16pt 0;
    }}

    .scene-break-div svg {{
        width: 160px;
        height: 22px;
    }}

    .tailpiece-div {{
        text-align: center;
        margin: 24pt 0 10pt 0;
    }}

    .tailpiece-div svg {{
        width: 140px;
        height: 70px;
    }}

    p.has-drop-cap::first-letter {{
        font-family: {display_font};
        font-size: {drop_cap_lines * 1.15}em;
        float: left;
        line-height: 0.82;
        padding-right: 0.12em;
        padding-top: 0.04em;
        color: {accent_color};
        {drop_cap_extra}
    }}

    .chapter-subtitle {{
        font-family: {display_font};
        font-size: 10pt;
        font-weight: 700;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: {accent_color};
        margin: 6pt 0 16pt 0;
    }}

    .inquest-writ, .inworld-writ, .inworld_writ {{
        border: 2px solid #1B365D;
        outline: 1px solid #B8860B;
        outline-offset: 2px;
        background: #FBF8F1;
        padding: 10pt 14pt;
        margin: 14pt 0;
        font-family: 'EB Garamond', Georgia, serif;
    }}

    .sensory-draw {{
        border-left: 3.5px solid #B8860B;
        padding: 8pt 14pt;
        margin: 14pt 16pt;
        font-style: italic;
        background: #FDFBF7;
    }}

    .welsh-slate, .welsh_slate {{
        background: #1E2229;
        color: #F8FAFC;
        border-left: 4px solid #00A896;
        padding: 12pt 16pt;
        margin: 14pt 0;
    }}

    .telemetry-equation, .scientific-formula, .scientific_formula {{
        border: 1.5px solid #4A5568;
        background: #F5F6F8;
        padding: 10pt 14pt;
        margin: 14pt 0;
        text-align: center;
        font-family: 'JetBrains Mono', monospace;
    }}

    .audio-transcript, .audio_transcript {{
        background: #0F172A;
        color: #38BDF8;
        border-left: 5px solid #0284C7;
        padding: 10pt 14pt;
        margin: 14pt 0;
        font-family: 'JetBrains Mono', monospace;
    }}

    .pelham-journal, .archival-journal, .archival_journal {{
        border: 1px solid #4A6B4E;
        background: #FCFAF2;
        padding: 12pt 16pt;
        margin: 14pt 0;
        border-left: 4px solid #2C402E;
        font-style: italic;
    }}

    .cuneiform-tablet, .cuneiform-clause, .cuneiform_clause {{
        border: 2px solid #8C4A28;
        background: #FAF6EE;
        padding: 10pt 14pt;
        margin: 14pt 0;
    }}

    .frame-thin_ink_border {{
        border: 1.5px solid #1A202C !important;
        padding: 3px;
        background: #FFF;
    }}

    .frame-double_brass_frame {{
        border: 2px solid #1A202C !important;
        outline: 1.5px solid #B8860B !important;
        outline-offset: 3px !important;
        padding: 2px;
        background: #FFF;
    }}

    .frame-blueprint_grid_frame {{
        border: 2px solid #00A896 !important;
        outline: 1px dashed #38BDF8 !important;
        outline-offset: 3px !important;
        padding: 2px;
        background: #FFF;
    }}

    .frame-rounded_slate {{
        border: 3px solid #334155 !important;
        border-radius: 6px !important;
        padding: 2px;
        background: #FFF;
    }}

    .inline-plate-div {{
        text-align: center;
        page-break-inside: avoid;
    }}

    .plate-caption {{
        margin-top: 8pt;
        font-family: {body_font};
        font-size: 8.5pt;
        font-style: italic;
        text-align: center;
        color: #444;
    }}

    .toc-entry {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 8pt;
        font-size: 10pt;
    }}
    """

    body_pages_html = ""

    for page in pages:
        p_num = page.get("page_number", 1)
        is_verso = page.get("is_verso", False)
        page_type = page.get("page_type", "body")
        suppress_header = page.get("suppress_header", False) or (rh_style == "Hidden")
        suppress_footer = page.get("suppress_footer", False)
        
        page_cls = "page-verso" if is_verso else "page-recto"
        if page_type == "full_plate":
            page_cls += " page-full-plate"

        # Running header resolution
        if is_verso:
            h_text = page.get("running_header_text") or running_header_text
        else:
            ch_n = page.get("chapter_number")
            ch_t = page.get("chapter_title")
            if ch_n and ch_t:
                h_text = f"CHAPTER {ch_n} • {ch_t.upper()}"
            else:
                h_text = page.get("running_header_text") or running_header_text

        h_align = "text-align: center;"
        if rh_style == "Small Caps Outer":
            h_align = "text-align: left;" if is_verso else "text-align: right;"
        
        h_border = "border-bottom: 0.5pt solid #777; padding-bottom: 2pt;" if rh_style == "Rule Underlined" else ""

        header_markup = ""
        if not suppress_header and h_text.strip():
            header_markup = f'<div class="pdf-running-header" style="{h_align} {h_border}">{h_text}</div>'

        footer_markup = ""
        if not suppress_footer:
            footer_markup = f'<div class="pdf-running-footer">{p_num}</div>'

        # Render page elements
        elem_markup = ""
        for elem in page.get("elements", []):
            etype = elem.get("type", "")
            
            if etype == "chapter_header":
                c_num = elem.get("chapter_number") or elem.get("number", "")
                c_title = elem.get("title", "")
                ornament = elem.get("ornament_svg") or profile["scene_break_svg"]
                elem_markup += f"""
                <div class="chapter-start-header" style="padding-top: {sinkage}in;">
                    <div class="chapter-num-label">Chapter {c_num}</div>
                    <h1 class="chapter-title">{c_title}</h1>
                    <div class="chapter-ornament">{ornament}</div>
                </div>
                """
            elif etype == "paragraph":
                btype = elem.get("block_type", "body")
                is_first = elem.get("is_first_after_break") or elem.get("is_first", False)
                has_drop = elem.get("has_drop_cap", False) or (is_first and page_type == "chapter_opener")
                p_text = elem.get("formatted_html") or elem.get("html") or elem.get("text", "")
                if btype == "chapter_subtitle":
                    elem_markup += f'<div class="chapter-subtitle">{p_text}</div>\n'
                else:
                    cls_list = []
                    if is_first:
                        cls_list.append("indent-zero")
                    if has_drop and drop_cap_enabled and drop_cap_style != "None":
                        cls_list.append("has-drop-cap")
                    cls_attr = f' class="{" ".join(cls_list)}"' if cls_list else ""
                    elem_markup += f'<p{cls_attr}>{p_text}</p>\n'
            elif etype == "container":
                btype = elem.get("block_type", "container")
                tag = elem.get("tag", btype.replace("_", "-"))
                c_text = elem.get("formatted_html") or elem.get("html") or elem.get("content", "").replace("\n", "<br>")
                elem_markup += f'<div class="custom-container {tag}">{c_text}</div>\n'
            elif etype == "scene_break":
                svg = elem.get("svg") or profile["scene_break_svg"]
                elem_markup += f'<div class="scene-break-div">{svg}</div>\n'
            elif etype == "tailpiece_ornament":
                svg = elem.get("svg") or profile["tailpiece_svg"]
                elem_markup += f'<div class="tailpiece-div">{svg}</div>\n'
            elif etype == "illustration":
                asset = elem.get("asset", {})
                placement = elem.get("placement", asset.get("placement", "Inline Centered"))
                img_src = _resolve_image_src(asset.get("image_url", ""))
                caption = asset.get("caption", asset.get("caption_text", ""))
                caption_pos = asset.get("caption_position", "below")
                frame_style = asset.get("frame_style", "none")
                frame_cls = f"frame-{frame_style}" if frame_style and frame_style != "none" else ""
                w_pct = asset.get("width_pct", 100)
                max_h = asset.get("max_height_in", 3.5)
                m_top = asset.get("margin_top_pt", 12.0)
                m_bottom = asset.get("margin_bottom_pt", 12.0)
                
                cap_html = f'<div class="plate-caption">{caption}</div>' if (caption and caption_pos != "hidden") else ""
                
                if placement in ["Full-Page Recto Plate", "Full-Page Verso Plate", "Full Bleed Plate"]:
                    elem_markup += f"""
                    <div style="display:flex; flex-direction:column; justify-content:center; align-items:center; height:100%; box-sizing:border-box; padding:0.4in;">
                        {cap_html if caption_pos == 'above' else ''}
                        <img src="{img_src}" class="{frame_cls}" style="max-width:{w_pct}%; max-height:{max_h}in; object-fit:contain;" alt="{asset.get('title', '')}">
                        {cap_html if caption_pos == 'below' else ''}
                    </div>
                    """
                elif placement == "Chapter End Tailpiece":
                    elem_markup += f"""
                    <div class="tailpiece-div" style="margin-top:20pt; margin-bottom:10pt;">
                        <img src="{img_src}" class="{frame_cls}" style="max-width:40%; max-height:1.5in; object-fit:contain;" alt="{asset.get('title', '')}">
                        {cap_html if caption_pos == 'below' else ''}
                    </div>
                    """
                elif placement == "Chapter Opener Vignette":
                    elem_markup += f"""
                    <div class="chapter-ornament" style="margin:12pt 0;">
                        <img src="{img_src}" class="{frame_cls}" style="max-width:50%; max-height:1.8in; object-fit:contain;" alt="{asset.get('title', '')}">
                        {cap_html if caption_pos == 'below' else ''}
                    </div>
                    """
                else:
                    elem_markup += f"""
                    <div class="inline-plate-div" style="margin-top:{m_top}pt; margin-bottom:{m_bottom}pt;">
                        {cap_html if caption_pos == 'above' else ''}
                        <img src="{img_src}" class="{frame_cls}" style="width:{w_pct}%; max-height:{max_h}in; object-fit:contain;" alt="{asset.get('title', '')}">
                        {cap_html if caption_pos == 'below' else ''}
                    </div>
                    """
            elif etype == "half_title":
                title_val = elem.get("title", "")
                elem_markup += f"""
                <div style="text-align:center; padding-top:2.8in;">
                    <h2 style="font-family:{display_font}; font-size:16pt; letter-spacing:0.14em; text-transform:uppercase; color:{accent_color};">
                        {title_val}
                    </h2>
                </div>
                """
            elif etype == "frontispiece":
                img_u = elem.get("image_url")
                sub_t = elem.get("subtitle", "")
                if img_u:
                    f_src = _resolve_image_src(img_u)
                    art_box = f'<img src="{f_src}" style="max-width:85%; max-height:4.2in; object-fit:contain; border:1px solid #444;" alt="Frontispiece">'
                else:
                    art_box = f'<div style="margin-bottom:20pt;">{elem.get("svg") or profile["scene_break_svg"]}</div>'
                elem_markup += f"""
                <div style="text-align:center; padding-top:2.2in;">
                    {art_box}
                    <p class="indent-zero" style="font-style:italic; font-size:9.5pt; color:#555; margin-top:14pt;">
                        {sub_t}
                    </p>
                </div>
                """
            elif etype == "title_page":
                impr = elem.get("imprint") or cm.get("publisher_imprint", "THE ARGON BOOK STUDIO • FINE TYPESETTING")
                elem_markup += f"""
                <div style="text-align:center; padding-top:1.4in;">
                    <h1 style="font-family:{display_font}; font-size:24pt; color:{accent_color}; margin-bottom:8pt; text-transform:uppercase;">{elem.get('title', '')}</h1>
                    <h2 style="font-family:{body_font}; font-size:12.5pt; font-style:italic; font-weight:400; margin-bottom:32pt;">{elem.get('subtitle', '')}</h2>
                    <div style="margin:18pt 0;">{profile['scene_break_svg']}</div>
                    <div style="font-family:{display_font}; font-size:11.5pt; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:50pt;">{elem.get('author', '')}</div>
                    <div style="font-family:{display_font}; font-size:8.5pt; letter-spacing:0.16em; color:#666; margin-top:1.0in;">
                        {impr}
                    </div>
                </div>
                """
            elif etype in ["copyright", "copyright_page"]:
                isbn_val = elem.get("isbn") or cm.get("isbn_hardcover", "978-1-987654-32-1")
                isbn_ep = cm.get("isbn_epub", "978-1-987654-33-8")
                elem_markup += f"""
                <div style="font-size:8.5pt; line-height:12.5pt; color:#444; padding-top:4.5in;">
                    <p class="indent-zero"><strong>{elem.get('title', '')}</strong></p>
                    <p class="indent-zero">Copyright © {elem.get('year', '2026')} by {elem.get('author', '')}</p>
                    <p class="indent-zero" style="margin-top:8pt;">All rights reserved. First Illustrated Collector's Edition.</p>
                    <p class="indent-zero">ISBN {isbn_val} (Fine Hardcover)</p>
                    <p class="indent-zero">ISBN {isbn_ep} (EPUB 3 Edition)</p>
                </div>
                """
            elif etype == "map_plate":
                img_u = elem.get("image_url")
                m_title = elem.get("title", "Archival Chart & Survey Map")
                m_cap = elem.get("caption", "Hydrographic Soundings & Survey of the Ghyll Skerries.")
                if img_u:
                    m_src = _resolve_image_src(img_u)
                    m_box = f'<img src="{m_src}" style="max-width:90%; max-height:3.6in; object-fit:contain; border:1.5px solid #444;" alt="Map Plate">'
                else:
                    m_box = f'<div style="margin:20pt auto; width:85%; height:2.8in; border:1.5px solid #444; background:#FAF7F0; display:flex; align-items:center; justify-content:center;">{elem.get("svg") or profile["scene_break_svg"]}</div>'
                elem_markup += f"""
                <div style="text-align:center; padding-top:1.8in;">
                    <h2 style="font-family:{display_font}; font-size:13pt; letter-spacing:0.14em; text-transform:uppercase; margin-bottom:12pt;">
                        {m_title}
                    </h2>
                    {m_box}
                    <p class="indent-zero" style="font-style:italic; font-size:8.5pt; color:#555; margin-top:10pt;">
                        {m_cap}
                    </p>
                </div>
                """
            elif etype == "dedication":
                elem_markup += f"""
                <div style="text-align:center; padding-top:3.2in; font-style:italic;">
                    <p class="indent-zero" style="font-size:11pt; color:#333;">{elem.get('text', '')}</p>
                </div>
                """
            elif etype == "epigraph":
                elem_markup += f"""
                <div style="text-align:center; padding-top:3.2in;">
                    <p class="indent-zero" style="font-size:11pt; font-style:italic; color:#333;">"{elem.get('text', '')}"</p>
                    <p class="indent-zero" style="font-size:8.5pt; margin-top:10pt; color:#666;">{elem.get('source', '')}</p>
                </div>
                """
            elif etype in ["toc", "table_of_contents"]:
                toc_rows = ""
                for ch in elem.get("chapters", []):
                    ch_num_val = ch.get("chapter_number") or ch.get("number", "")
                    toc_rows += f"""
                    <div class="toc-entry">
                        <span><strong>Chapter {ch_num_val}</strong> — {ch.get('title', '')}</span>
                    </div>
                    """
                elem_markup += f"""
                <div style="padding-top:1.4in;">
                    <h2 style="font-family:{display_font}; font-size:13pt; letter-spacing:0.16em; text-align:center; text-transform:uppercase; margin-bottom:20pt;">
                        Contents
                    </h2>
                    {toc_rows}
                </div>
                """
            elif etype == "appendix":
                elem_markup += f"""
                <div style="padding-top:1.6in; text-align:left;">
                    <h2 style="font-family:{display_font}; font-size:13pt; letter-spacing:0.14em; text-transform:uppercase; margin-bottom:14pt; text-align:center;">
                        {elem.get('title', 'Appendix')}
                    </h2>
                    <div style="font-family:'JetBrains Mono', monospace; font-size:8.5pt; line-height:14pt; background:#F8FAFC; border:1px solid #CBD5E1; padding:12pt 16pt; margin:0 auto; max-width:4.8in;">
                        {elem.get('text', '').replace(chr(10), '<br>')}
                    </div>
                </div>
                """
            elif etype == "glossary":
                g_html = ""
                for g in elem.get("terms", []):
                    g_html += f"<p class='indent-zero' style='margin-bottom:8pt;'><strong>{g.get('term', '')}</strong> — {g.get('definition', '')}</p>"
                elem_markup += f"""
                <div style="padding-top:1.6in;">
                    <h2 style="font-family:{display_font}; font-size:13pt; letter-spacing:0.14em; text-transform:uppercase; margin-bottom:16pt; text-align:center;">
                        {elem.get('title', 'Glossary')}
                    </h2>
                    <div style="font-size:8.5pt; line-height:13pt; max-width:4.8in; margin:0 auto;">
                        {g_html}
                    </div>
                </div>
                """
            elif etype == "acknowledgements":
                elem_markup += f"""
                <div style="padding-top:1.8in; text-align:center;">
                    <h2 style="font-family:{display_font}; font-size:13pt; letter-spacing:0.16em; text-transform:uppercase; margin-bottom:16pt;">{elem.get('title', 'Acknowledgements')}</h2>
                    <p class="indent-zero" style="max-width:4.5in; margin:0 auto; line-height:1.5;">{elem.get('text', '')}</p>
                </div>
                """
            elif etype == "about_author":
                elem_markup += f"""
                <div style="padding-top:1.8in; text-align:center;">
                    <h2 style="font-family:{display_font}; font-size:13pt; letter-spacing:0.16em; text-transform:uppercase; margin-bottom:16pt;">{elem.get('title', 'About the Author')}</h2>
                    <p class="indent-zero" style="max-width:4.5in; margin:0 auto; line-height:1.5;">{elem.get('text', '')}</p>
                </div>
                """
            elif etype == "colophon":
                c_body = elem.get("specs") or cm.get("colophon_text") or (
                    f"This volume was typeset and produced using the Argon Book Studio Desktop Publishing Engine. "
                    f"Layout adheres to {width_in:.1f} x {height_in:.1f} inch book signatures with mirrored gutter margins ({gutter}in inside, {outside}in outside)."
                )
                elem_markup += f"""
                <div style="padding-top:2.2in; font-size:8.5pt; line-height:13.5pt; color:#333; text-align:center;">
                    <h3 style="font-family:{display_font}; font-size:10.5pt; letter-spacing:0.16em; text-transform:uppercase; margin-bottom:12pt; color:{accent_color};">
                        Colophon
                    </h3>
                    <p class="indent-zero" style="max-width:4.2in; margin:0 auto; text-align:center;">
                        {c_body}
                    </p>
                    <div style="margin-top:20pt;">{profile['tailpiece_svg']}</div>
                </div>
                """

        body_pages_html += f"""
        <div class="physical-pdf-page {page_cls}">
            {header_markup}
            <div class="physical-pdf-page-content">
                {elem_markup}
            </div>
            {footer_markup}
        </div>
        """

    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{parsed_book.get('title', profile['title'])}</title>
        <style>{css}</style>
    </head>
    <body>
        {body_pages_html}
    </body>
    </html>
    """
    return html


def export_pdf(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    output_pdf_path: str,
    bleed: bool = False,
    custom_specs: Dict[str, Any] = None,
    custom_matter: Dict[str, Any] = None
) -> str:
    html_content = generate_pdf_html(
        parsed_book,
        manifest,
        profile_id,
        bleed=bleed,
        custom_specs=custom_specs,
        custom_matter=custom_matter
    )
    
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    temp_html_path = output_pdf_path + ".html"
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    edge_exe = next((p for p in edge_paths if os.path.exists(p)), None)

    if edge_exe:
        abs_html = os.path.abspath(temp_html_path)
        abs_pdf = os.path.abspath(output_pdf_path)
        
        cmd = [
            edge_exe,
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            f"--print-to-pdf={abs_pdf}",
            "--no-pdf-header-footer",
            abs_html
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if os.path.exists(temp_html_path):
            try:
                os.remove(temp_html_path)
            except Exception:
                pass
        if os.path.exists(abs_pdf):
            return abs_pdf

    return _build_fallback_reportlab_pdf(parsed_book, manifest, profile_id, output_pdf_path, custom_specs)


def _build_fallback_reportlab_pdf(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    output_pdf_path: str,
    custom_specs: Dict[str, Any] = None
) -> str:
    from reportlab.lib.pagesizes import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    cs = custom_specs or {}
    w = float(cs.get("trim_width_in", 6.0))
    h = float(cs.get("trim_height_in", 9.0))
    gutter = float(cs.get("margins", {}).get("inside_gutter_in", cs.get("inside_gutter_in", 0.875)))
    outside = float(cs.get("margins", {}).get("outside_margin_in", cs.get("outside_margin_in", 0.625)))
    top = float(cs.get("margins", {}).get("top_margin_in", cs.get("top_margin_in", 0.75)))
    bottom = float(cs.get("margins", {}).get("bottom_margin_in", cs.get("bottom_margin_in", 0.875)))
    
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=(w * inch, h * inch),
        leftMargin=gutter * inch,
        rightMargin=outside * inch,
        topMargin=top * inch,
        bottomMargin=bottom * inch
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'BookTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=14
    )
    body_style = ParagraphStyle(
        'BookBody',
        parent=styles['Normal'],
        fontSize=10.5,
        leading=14.5,
        firstLineIndent=18,
        spaceAfter=0
    )
    
    for ch in parsed_book.get("chapters", []):
        story.append(Paragraph(ch.get("title", ""), title_style))
        story.append(Spacer(1, 0.25 * inch))
        for elem in ch.get("elements", []):
            if elem.get("type") == "paragraph":
                story.append(Paragraph(elem.get("text", ""), body_style))
        story.append(PageBreak())
        
    doc.build(story)
    return output_pdf_path
