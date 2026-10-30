"""
Argon Book Studio - Print-Ready PDF Exporter.
Renders book manuscripts with exact book-production rules:
- Trim Size: configurable (default 6.0 in x 9.0 in) with optional +0.125 in bleed toggle.
- Mirrored print margins (@page :left inside gutter, outside margin; @page :right inside, outside).
- Strict widow/orphan control (orphans: 3; widows: 3).
- First paragraph text-indent: 0; subsequent body paragraphs text-indent: 0.25in.
- Optical margin alignment (hanging-punctuation: first last).
- Verso running header: Book Title in tracked small-caps.
- Recto running header: Chapter Number & Title in tracked small-caps.
- Header/footer suppression on @page :first, front matter, chapter opening pages, full plates, blank pages.
- Chapter openings with top sinkage.
- Respects dynamic custom geometry, typography, and extended matter.
"""

import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from app.profiles import BOOK_PROFILES, UNIVERSAL_PUBLISHING_SPECS


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

    if rh_style == "Hidden":
        left_top_rule = "@top-center { content: none; } @top-left { content: none; } @top-right { content: none; }"
        right_top_rule = "@top-center { content: none; } @top-left { content: none; } @top-right { content: none; }"
    elif rh_style == "Small Caps Outer":
        left_top_rule = f'@top-left {{ content: "{running_header_text}"; font-family: {body_font}; font-size: 8.5pt; letter-spacing: 0.14em; text-transform: uppercase; }} @top-center {{ content: none; }}'
        right_top_rule = f'@top-right {{ content: string(chapter-title); font-family: {body_font}; font-size: 8.5pt; letter-spacing: 0.14em; text-transform: uppercase; }} @top-center {{ content: none; }}'
    elif rh_style == "Rule Underlined":
        left_top_rule = f'@top-center {{ content: "{running_header_text}"; font-family: {body_font}; font-size: 8.5pt; letter-spacing: 0.14em; text-transform: uppercase; border-bottom: 0.5pt solid #777; padding-bottom: 3pt; }}'
        right_top_rule = f'@top-center {{ content: string(chapter-title); font-family: {body_font}; font-size: 8.5pt; letter-spacing: 0.14em; text-transform: uppercase; border-bottom: 0.5pt solid #777; padding-bottom: 3pt; }}'
    else: # Small Caps Centered
        left_top_rule = f'@top-center {{ content: "{running_header_text}"; font-family: {body_font}; font-size: 8.5pt; letter-spacing: 0.14em; text-transform: uppercase; }}'
        right_top_rule = f'@top-center {{ content: string(chapter-title); font-family: {body_font}; font-size: 8.5pt; letter-spacing: 0.14em; text-transform: uppercase; }}'

    drop_cap_extra = ""
    if drop_cap_style == "Boxed Rule":
        drop_cap_extra = "border: 1px solid #B8860B; padding: 2pt 5pt; background: #FAF6EE; margin-right: 5pt;"
    elif drop_cap_style == "Botanical/Ornate":
        drop_cap_extra = "font-style: italic; font-family: 'Cormorant Garamond', Georgia, serif; color: #2C402E; margin-right: 4pt;"

    assets_by_anchor: Dict[str, List[Dict[str, Any]]] = {}
    for a in manifest.get("assets", []):
        assets_by_anchor.setdefault(a.get("anchor", ""), []).append(a)

    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Cinzel+Decorative:wght@700&family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&family=Lora:ital,wght@0,400;0,600;1,400&family=Oswald:wght@400;600;700&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap');

    @page {{
        size: {width_in}in {height_in}in;
        orphans: 3;
        widows: 3;
        hanging-punctuation: first last;
        margin: 0;
    }}

    @page :left {{
        margin-top: {top}in;
        margin-bottom: {bottom}in;
        margin-left: {outside}in;
        margin-right: {gutter}in;
        {left_top_rule}
        @bottom-center {{
            content: counter(page);
            font-family: {body_font};
            font-size: 8.5pt;
        }}
    }}

    @page :right {{
        margin-top: {top}in;
        margin-bottom: {bottom}in;
        margin-left: {gutter}in;
        margin-right: {outside}in;
        {right_top_rule}
        @bottom-center {{
            content: counter(page);
            font-family: {body_font};
            font-size: 8.5pt;
        }}
    }}

    @page chapter-page {{
        margin-top: {top}in;
        margin-bottom: {bottom}in;
        @top-center {{ content: none; }}
        @bottom-center {{ content: counter(page); }}
    }}

    @page no-header-footer {{
        margin: {top}in {outside}in {bottom}in {gutter}in;
        @top-center {{ content: none; }}
        @bottom-center {{ content: none; }}
    }}

    @page full-bleed-plate {{
        margin: 0;
        @top-center {{ content: none; }}
        @bottom-center {{ content: none; }}
    }}

    body {{
        margin: 0;
        padding: 0;
        font-family: {body_font};
        font-size: {body_size}pt;
        line-height: {body_leading}pt;
        color: #1a1a1a;
        background-color: #fff;
        text-rendering: optimizeLegibility;
    }}

    .suppress-all {{
        page: no-header-footer;
        page-break-before: always;
        page-break-after: always;
    }}

    .chapter-start {{
        page: chapter-page;
        page-break-before: always;
        padding-top: {sinkage}in;
        string-set: chapter-title attr(data-chapter-title);
    }}

    .full-plate-page {{
        page: full-bleed-plate;
        page-break-before: always;
        page-break-after: always;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-sizing: border-box;
        padding: 0.5in;
    }}

    .full-plate-page img {{
        max-width: 95%;
        max-height: 80%;
        object-fit: contain;
        border: 1px solid #333;
    }}

    .plate-caption {{
        margin-top: 14pt;
        font-family: {body_font};
        font-size: 9pt;
        font-style: italic;
        text-align: center;
        color: #333;
    }}

    p {{
        margin: 0 0 0 0;
        text-indent: {indent}in;
        text-align: justify;
    }}

    p.indent-zero,
    .chapter-start > p:first-of-type,
    .scene-break-div + p,
    .custom-container + p,
    .inline-plate-div + p {{
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
        margin: 12pt 0 24pt 0;
    }}

    .chapter-ornament svg {{
        width: 180px;
        height: 24px;
    }}

    .scene-break-div {{
        text-align: center;
        margin: 18pt 0;
    }}

    .scene-break-div svg {{
        width: 160px;
        height: 22px;
    }}

    .tailpiece-div {{
        text-align: center;
        margin: 28pt 0 10pt 0;
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
        padding: 12pt 16pt;
        margin: 16pt 0;
        font-family: 'EB Garamond', Georgia, serif;
    }}

    .sensory-draw {{
        border-left: 3.5px solid #B8860B;
        padding: 8pt 16pt;
        margin: 16pt 18pt;
        font-style: italic;
        background: #FDFBF7;
    }}

    .welsh-slate, .welsh_slate {{
        background: #1E2229;
        color: #F8FAFC;
        border-left: 4px solid #00A896;
        padding: 14pt 18pt;
        margin: 16pt 0;
    }}

    .telemetry-equation, .scientific-formula, .scientific_formula {{
        border: 1.5px solid #4A5568;
        background: #F5F6F8;
        padding: 12pt 16pt;
        margin: 16pt 0;
        text-align: center;
        font-family: 'JetBrains Mono', monospace;
    }}

    .audio-transcript, .audio_transcript {{
        background: #0F172A;
        color: #38BDF8;
        border-left: 5px solid #0284C7;
        padding: 12pt 16pt;
        margin: 16pt 0;
        font-family: 'JetBrains Mono', monospace;
    }}

    .fsk-payload {{
        border: 1px dashed #334155;
        background: #1E293B;
        color: #E2E8F0;
        padding: 10pt 14pt;
        margin: 14pt 0;
        font-family: monospace;
    }}

    .pelham-journal, .archival-journal, .archival_journal {{
        border: 1px solid #4A6B4E;
        background: #FCFAF2;
        padding: 14pt 18pt;
        margin: 16pt 0;
        border-left: 4px solid #2C402E;
        font-style: italic;
    }}

    .oscilloscope-readout {{
        border: 1px solid #D97706;
        background: #FFFBEB;
        padding: 12pt 14pt;
        margin: 14pt 0;
        font-family: monospace;
    }}

    .cuneiform-tablet, .cuneiform-clause, .cuneiform_clause {{
        border: 2px solid #8C4A28;
        background: #FAF6EE;
        padding: 12pt 16pt;
        margin: 16pt 0;
    }}

    .cedar-sliver {{
        border-left: 4px solid #C98A2C;
        background: #FDF9F3;
        padding: 10pt 14pt;
        margin: 14pt 0;
    }}

    .frame-thin_ink_border {{
        border: 1.5px solid #1A202C !important;
        padding: 4px;
        background: #FFF;
    }}

    .frame-double_brass_frame {{
        border: 2px solid #1A202C !important;
        outline: 1.5px solid #B8860B !important;
        outline-offset: 4px !important;
        padding: 2px;
        background: #FFF;
    }}

    .frame-blueprint_grid_frame {{
        border: 2px solid #00A896 !important;
        outline: 1px dashed #38BDF8 !important;
        outline-offset: 4px !important;
        padding: 2px;
        background: #FFF;
    }}

    .frame-rounded_slate {{
        border: 3px solid #334155 !important;
        border-radius: 8px !important;
        padding: 2px;
        background: #FFF;
    }}

    .inline-plate-div {{
        margin: 16pt 0;
        text-align: center;
        page-break-inside: avoid;
    }}

    .inline-plate-div img {{
        max-width: 100%;
        max-height: 3.5in;
        border: 1px solid #444;
    }}

    .half-title-page, .title-page, .colophon-page {{
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-sizing: border-box;
    }}

    .title-page h1 {{
        font-family: {display_font};
        font-size: 26pt;
        color: {accent_color};
        margin-bottom: 8pt;
    }}

    .title-page h2 {{
        font-family: {body_font};
        font-size: 13pt;
        font-style: italic;
        font-weight: 400;
        margin-bottom: 40pt;
    }}

    .title-page .author {{
        font-family: {display_font};
        font-size: 12pt;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 60pt;
    }}

    .title-page .imprint {{
        font-family: {display_font};
        font-size: 9pt;
        letter-spacing: 0.16em;
        color: #666;
    }}

    .toc-entry {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 8pt;
        font-size: 10.5pt;
    }}
    """

    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{parsed_book.get('title', profile['title'])}</title>
        <style>{css}</style>
    </head>
    <body>
    """

    # FRONT MATTER
    if include_front_matter:
        if cm.get("include_half_title", True):
            html += f"""
            <div class="suppress-all half-title-page">
                <h2 style="font-family: {display_font}; font-size: 16pt; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 3in;">
                    {parsed_book.get('title', profile['title'])}
                </h2>
            </div>
            """

        if cm.get("include_frontispiece", True):
            html += f"""
            <div class="suppress-all" style="text-align: center; padding-top: 3.2in;">
                <div style="margin-bottom: 20pt;">{profile['scene_break_svg']}</div>
                <p style="text-indent: 0; font-style: italic; font-size: 10pt; color: #555;">
                    {parsed_book.get('subtitle', profile['subtitle'])}
                </p>
            </div>
            """

        if cm.get("include_title_page", True):
            imprint_txt = cm.get("publisher_imprint", "THE ARGON BOOK STUDIO • FINE TYPESETTING")
            html += f"""
            <div class="suppress-all title-page">
                <div style="margin-top: 1.5in;">
                    <h1>{parsed_book.get('title', profile['title'])}</h1>
                    <h2>{parsed_book.get('subtitle', profile['subtitle'])}</h2>
                    <div style="margin: 20pt 0;">{profile['scene_break_svg']}</div>
                    <div class="author">{parsed_book.get('author', profile['author'])}</div>
                    <div class="imprint" style="margin-top: 1.5in;">
                        {imprint_txt}
                    </div>
                </div>
            </div>
            """

        if cm.get("include_copyright", True):
            isbn_hc = cm.get("isbn_hardcover", "978-1-987654-32-1")
            isbn_ep = cm.get("isbn_epub", "978-1-987654-33-8")
            html += f"""
            <div class="suppress-all" style="font-size: 8.5pt; line-height: 12.5pt; color: #444; padding-top: 4.8in;">
                <p class="indent-zero"><strong>{parsed_book.get('title', profile['title'])}</strong></p>
                <p class="indent-zero">Copyright © 2026 by {parsed_book.get('author', profile['author'])}</p>
                <p class="indent-zero" style="margin-top: 8pt;">All rights reserved. First Illustrated Collector's Edition.</p>
                <p class="indent-zero">ISBN {isbn_hc} (Fine Hardcover)</p>
                <p class="indent-zero">ISBN {isbn_ep} (EPUB 3 Edition)</p>
            </div>
            """

        if cm.get("include_dedication", False):
            html += f"""
            <div class="suppress-all" style="text-align: center; padding-top: 3.5in; font-style: italic;">
                <p class="indent-zero" style="font-size: 11pt; color: #333;">{cm.get('dedication_text', '')}</p>
            </div>
            """

        if cm.get("include_epigraph", False):
            html += f"""
            <div class="suppress-all" style="text-align: center; padding-top: 3.5in;">
                <p class="indent-zero" style="font-size: 11pt; font-style: italic; color: #333;">"{cm.get('epigraph_text', '')}"</p>
                <p class="indent-zero" style="font-size: 9pt; margin-top: 10pt; color: #666;">{cm.get('epigraph_source', '')}</p>
            </div>
            """

        if cm.get("include_toc", True):
            html += f"""
            <div class="suppress-all" style="padding-top: 1.5in;">
                <h2 style="font-family: {display_font}; font-size: 14pt; letter-spacing: 0.16em; text-align: center; text-transform: uppercase; margin-bottom: 24pt;">
                    Contents
                </h2>
            """
            for ch in parsed_book.get("chapters", []):
                html += f"""
                <div class="toc-entry">
                    <span><strong>Chapter {ch.get('chapter_number', '')}</strong> — {ch.get('title', '')}</span>
                </div>
                """
            html += "</div>"

        if cm.get("include_map", False):
            html += f"""
            <div class="suppress-all" style="text-align: center; padding-top: 2.2in;">
                <h2 style="font-family: {display_font}; font-size: 14pt; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 12pt;">
                    {cm.get('map_title', 'Archival Chart & Survey Map')}
                </h2>
                <div style="margin: 20pt auto; width: 85%; height: 2.8in; border: 1.5px solid #444; background: #FAF7F0; display: flex; align-items: center; justify-content: center;">
                    {profile['scene_break_svg']}
                </div>
                <p style="text-indent: 0; font-style: italic; font-size: 9pt; color: #555;">
                    {cm.get('map_caption', 'Hydrographic Soundings & Survey of the Ghyll Skerries.')}
                </p>
            </div>
            """

    # BODY CHAPTERS
    for ch_idx, chapter in enumerate(parsed_book.get("chapters", [])):
        ch_num = chapter.get("chapter_number", str(ch_idx + 1))
        ch_title = chapter.get("title", "")
        
        html += f"""
        <div class="chapter-start" data-chapter-title="CHAPTER {ch_num} • {ch_title.upper()}">
            <div class="chapter-num-label">Chapter {ch_num}</div>
            <h1 class="chapter-title">{ch_title}</h1>
            <div class="chapter-ornament">{profile['scene_break_svg']}</div>
        """
        
        first_p_done = False
        elements = chapter.get("elements", [])
        
        for elem in elements:
            elem_id = elem.get("id", "")
            elem_type = elem.get("type", "paragraph")
            btype = elem.get("block_type", "body")
            pb_style = ' style="page-break-before: always;"' if elem.get("page_break_before") else ""
            
            for asset in assets_by_anchor.get(elem_id, []):
                placement = asset.get("placement", "")
                img_path = asset.get("image_url", "")
                caption = asset.get("caption", "")
                frame_cls = f"frame-{asset.get('frame_style', 'none')}" if asset.get("frame_style") and asset.get("frame_style") != "none" else ""
                
                if img_path.startswith("/static/"):
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    local_path = os.path.join(base_dir, img_path.lstrip("/")).replace("\\", "/")
                    img_src = f"file:///{local_path}"
                else:
                    img_src = img_path
                    
                if placement in ["Full-Page Recto Plate", "Full-Page Verso Plate", "Full Bleed Plate"]:
                    html += f"""
                    </div>
                    <div class="full-plate-page">
                        <img src="{img_src}" class="{frame_cls}" alt="{asset.get('title', '')}">
                        <div class="plate-caption">{caption}</div>
                    </div>
                    <div style="page-break-before: always; string-set: chapter-title 'CHAPTER {ch_num} • {ch_title.upper()}';">
                    """
                else:
                    html += f"""
                    <div class="inline-plate-div">
                        <img src="{img_src}" class="{frame_cls}" alt="{asset.get('title', '')}">
                        <div class="plate-caption">{caption}</div>
                    </div>
                    """

            f_html = elem.get("formatted_html") or elem.get("text", "")
            if btype == "chapter_subtitle":
                html += f'<div class="chapter-subtitle"{pb_style}>{f_html}</div>\n'
            elif btype in ["inworld_writ", "welsh_slate", "audio_transcript", "archival_journal", "scientific_formula", "cuneiform_clause"] or elem_type == "container":
                tag = elem.get("tag", btype.replace("_", "-"))
                content = f_html or elem.get("content", "").replace("\n", "<br>")
                html += f'<div class="custom-container {tag}"{pb_style}>{content}</div>\n'
            elif elem_type == "scene_break":
                html += f'<div class="scene-break-div"{pb_style}>{profile["scene_break_svg"]}</div>\n'
            else:
                is_first = elem.get("is_first_after_break", False) or not first_p_done
                drop_cls = "has-drop-cap" if (drop_cap_enabled and drop_cap_style != "None" and not first_p_done) else ""
                cls = f"indent-zero {drop_cls}".strip() if (is_first or not first_p_done) else ""
                html += f'<p class="{cls}"{pb_style}>{f_html}</p>\n'
                first_p_done = True

        html += f"""
            <div class="tailpiece-div">{profile['tailpiece_svg']}</div>
        </div>
        """

    # BACK MATTER
    if cm.get("include_appendix", False):
        html += f"""
        <div class="suppress-all" style="padding-top: 1.8in; text-align: left;">
            <h2 style="font-family: {display_font}; font-size: 14pt; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 16pt; text-align: center;">
                {cm.get('appendix_title', 'Appendix: Forensic Telemetry')}
            </h2>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 8.5pt; line-height: 14pt; background: #F8FAFC; border: 1px solid #CBD5E1; padding: 14pt 18pt; margin: 0 auto; max-width: 4.8in;">
                {cm.get('appendix_text', '').replace(chr(10), '<br>')}
            </div>
        </div>
        """

    if cm.get("include_glossary", False):
        terms_html = ""
        for g in cm.get("glossary_terms", []):
            terms_html += f"<p style='text-indent:0; margin-bottom:8pt;'><strong>{g.get('term', '')}</strong> — {g.get('definition', '')}</p>"
        html += f"""
        <div class="suppress-all" style="padding-top: 1.8in;">
            <h2 style="font-family: {display_font}; font-size: 14pt; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 18pt; text-align: center;">
                {cm.get('glossary_title', 'Glossary of In-World Terms')}
            </h2>
            <div style="font-size: 9pt; line-height: 13.5pt; max-width: 4.8in; margin: 0 auto;">
                {terms_html}
            </div>
        </div>
        """

    if cm.get("include_acknowledgements", False):
        html += f"""
        <div class="suppress-all" style="padding-top: 2.0in; text-align: center;">
            <h2 style="font-family: {display_font}; font-size: 14pt; letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 18pt;">Acknowledgements</h2>
            <p class="indent-zero" style="max-width: 4.5in; margin: 0 auto; line-height: 1.5;">{cm.get('acknowledgements_text', '')}</p>
        </div>
        """

    if cm.get("include_about_author", False):
        html += f"""
        <div class="suppress-all" style="padding-top: 2.0in; text-align: center;">
            <h2 style="font-family: {display_font}; font-size: 14pt; letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 18pt;">About the Author</h2>
            <p class="indent-zero" style="max-width: 4.5in; margin: 0 auto; line-height: 1.5;">{cm.get('about_author_text', '')}</p>
        </div>
        """

    if cm.get("include_colophon", True):
        colophon_body = cm.get("colophon_text") or (
            f"This volume was typeset and produced using the Argon Book Studio Desktop Publishing Engine. "
            f"Layout adheres to {width_in:.1f} x {height_in:.1f} inch book signatures with mirrored gutter margins ({gutter}in inside, {outside}in outside)."
        )
        html += f"""
        <div class="suppress-all colophon-page" style="padding-top: 2.5in; font-size: 9pt; line-height: 14pt; color: #333; text-align: center;">
            <h3 style="font-family: {display_font}; font-size: 11pt; letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 14pt; color: {accent_color};">
                Colophon
            </h3>
            <p class="indent-zero" style="max-width: 4.2in; margin: 0 auto; text-align: center;">
                {colophon_body}
            </p>
            <div style="margin-top: 24pt;">{profile['tailpiece_svg']}</div>
        </div>
        """

    html += "</body></html>"
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
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
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
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
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
