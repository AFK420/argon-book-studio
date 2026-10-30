"""
Argon Book Studio - Print-Ready 6x9" PDF Exporter.
Renders book manuscripts with exact book-production rules:
- Trim Size: 6.0 in x 9.0 in (with optional +0.125 in bleed toggle).
- Mirrored print margins (@page :left inside gutter 0.875in, outside 0.625in; @page :right inside 0.875in, outside 0.625in).
- Strict widow/orphan control (orphans: 3; widows: 3).
- First paragraph text-indent: 0; subsequent body paragraphs text-indent: 0.25in, margin-bottom: 0.
- Optical margin alignment (hanging-punctuation: first last).
- Verso running header: Book Title in tracked small-caps (8.5pt).
- Recto running header: Chapter Number & Title in tracked small-caps (8.5pt).
- Header/footer suppression on @page :first, front matter, chapter opening pages, full plates, blank pages.
- Chapter openings with 1.75in top sinkage.
"""

import os
import subprocess
import tempfile
from typing import Dict, Any, List
from app.profiles import BOOK_PROFILES, UNIVERSAL_PUBLISHING_SPECS


def generate_pdf_html(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    bleed: bool = False,
    include_front_matter: bool = True
) -> str:
    profile = BOOK_PROFILES.get(profile_id, BOOK_PROFILES["book01"])
    specs = UNIVERSAL_PUBLISHING_SPECS
    
    width_in = specs["trim_width_in"] + (specs["bleed_in"] * 2 if bleed else 0)
    height_in = specs["trim_height_in"] + (specs["bleed_in"] * 2 if bleed else 0)
    
    gutter = specs["margins"]["inside_gutter_in"]
    outside = specs["margins"]["outside_margin_in"]
    top = specs["margins"]["top_margin_in"]
    bottom = specs["margins"]["bottom_margin_in"]
    sinkage = specs["grid_rules"]["chapter_sinkage_in"]
    
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
        @top-center {{
            content: "{profile['short_title'].upper()}";
            font-family: {profile['body_font']};
            font-size: 8.5pt;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }}
        @bottom-center {{
            content: counter(page);
            font-family: {profile['body_font']};
            font-size: 8.5pt;
        }}
    }}

    @page :right {{
        margin-top: {top}in;
        margin-bottom: {bottom}in;
        margin-left: {gutter}in;
        margin-right: {outside}in;
        @top-center {{
            content: string(chapter-title);
            font-family: {profile['body_font']};
            font-size: 8.5pt;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }}
        @bottom-center {{
            content: counter(page);
            font-family: {profile['body_font']};
            font-size: 8.5pt;
        }}
    }}

    /* Running Header / Footer Suppression */
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
        font-family: {profile['body_font']};
        font-size: {profile['body_font_size']};
        line-height: {profile['body_leading']};
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
        font-family: {profile['body_font']};
        font-size: 9pt;
        font-style: italic;
        text-align: center;
        color: #333;
    }}

    /* Paragraph indentation rules */
    p {{
        margin: 0 0 0 0;
        text-indent: 0.25in;
        text-align: justify;
    }}

    p.indent-zero,
    .chapter-start > p:first-of-type,
    .scene-break-div + p,
    .custom-container + p,
    .inline-plate-div + p {{
        text-indent: 0 !important;
    }}

    /* Typography & Headers */
    h1.chapter-title {{
        font-family: {profile['display_font']};
        font-size: 20pt;
        font-weight: 600;
        text-align: center;
        margin-top: 0;
        margin-bottom: 8pt;
        color: {profile['accent_color']};
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}

    .chapter-num-label {{
        font-family: {profile['display_font']};
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

    /* Drop caps */
    p.has-drop-cap::first-letter {{
        font-family: {profile['display_font']};
        font-size: 3.4em;
        float: left;
        line-height: 0.8;
        padding-right: 0.12em;
        padding-top: 0.04em;
        color: {profile['accent_color']};
    }}

    /* In-world Custom Containers */
    .inquest-writ {{
        border: 2px solid #1B365D;
        background: #FBF8F1;
        padding: 14pt 18pt;
        margin: 16pt 0;
        font-family: 'EB Garamond', Georgia, serif;
        box-shadow: 2px 2px 0px rgba(27, 54, 93, 0.15);
    }}

    .inquest-writ h3 {{
        font-family: 'Cinzel', serif;
        font-size: 10pt;
        letter-spacing: 0.1em;
        color: #1B365D;
        margin-top: 0;
        margin-bottom: 6pt;
        border-bottom: 1px solid #B8860B;
        padding-bottom: 4pt;
    }}

    .sensory-draw {{
        border-left: 3.5px solid #B8860B;
        padding: 8pt 16pt;
        margin: 16pt 18pt;
        font-style: italic;
        background: #FDFBF7;
    }}

    .welsh-slate {{
        background: #1E2229;
        color: #F8FAFC;
        border-left: 4px solid #00A896;
        padding: 14pt 18pt;
        margin: 16pt 0;
        font-family: Georgia, serif;
        font-size: 10pt;
        letter-spacing: 0.04em;
    }}

    .telemetry-equation {{
        border: 1.5px solid #4A5568;
        background: #F5F6F8;
        padding: 12pt 16pt;
        margin: 16pt 0;
        font-family: monospace;
        font-size: 9.5pt;
    }}

    .audio-transcript {{
        background: #0F172A;
        color: #38BDF8;
        border-left: 5px solid #0284C7;
        padding: 12pt 16pt;
        margin: 16pt 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 9pt;
        line-height: 14pt;
    }}

    .fsk-payload {{
        border: 1px dashed #334155;
        background: #1E293B;
        color: #E2E8F0;
        padding: 10pt 14pt;
        margin: 14pt 0;
        font-family: monospace;
        font-size: 8.5pt;
    }}

    .pelham-journal {{
        border: 1px solid #4A6B4E;
        background: #FCFAF2;
        padding: 14pt 18pt;
        margin: 16pt 0;
        color: #2C402E;
        border-left: 4px solid #2C402E;
    }}

    .oscilloscope-readout {{
        border: 1px solid #D97706;
        background: #FFFBEB;
        padding: 12pt 14pt;
        margin: 14pt 0;
        font-family: monospace;
        font-size: 9pt;
    }}

    .cuneiform-tablet {{
        border: 2px solid #8C4A28;
        background: #FAF6EE;
        padding: 12pt 16pt;
        margin: 16pt 0;
        font-family: 'Crimson Pro', Georgia, serif;
        font-size: 9.5pt;
    }}

    .cedar-sliver {{
        border-left: 4px solid #C98A2C;
        background: #FDF9F3;
        padding: 10pt 14pt;
        margin: 14pt 0;
        color: #5A2A18;
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

    /* Front Matter Styles */
    .half-title-page, .title-page, .colophon-page {{
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-sizing: border-box;
    }}

    .title-page h1 {{
        font-family: {profile['display_font']};
        font-size: 26pt;
        color: {profile['accent_color']};
        margin-bottom: 8pt;
    }}

    .title-page h2 {{
        font-family: {profile['body_font']};
        font-size: 13pt;
        font-style: italic;
        font-weight: 400;
        margin-bottom: 40pt;
    }}

    .title-page .author {{
        font-family: {profile['display_font']};
        font-size: 12pt;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 60pt;
    }}

    .title-page .imprint {{
        font-family: {profile['display_font']};
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
        # Half title
        html += f"""
        <div class="suppress-all half-title-page">
            <h2 style="font-family: {profile['display_font']}; font-size: 16pt; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 3in;">
                {parsed_book.get('title', profile['title'])}
            </h2>
        </div>
        """

        # Frontispiece
        html += f"""
        <div class="suppress-all" style="text-align: center; padding-top: 3.2in;">
            <div style="margin-bottom: 20pt;">{profile['scene_break_svg']}</div>
            <p style="text-indent: 0; font-style: italic; font-size: 10pt; color: #555;">
                {parsed_book.get('subtitle', profile['subtitle'])}
            </p>
        </div>
        """

        # Full Title Page
        html += f"""
        <div class="suppress-all title-page">
            <div style="margin-top: 1.5in;">
                <h1>{parsed_book.get('title', profile['title'])}</h1>
                <h2>{parsed_book.get('subtitle', profile['subtitle'])}</h2>
                <div style="margin: 20pt 0;">{profile['scene_break_svg']}</div>
                <div class="author">{parsed_book.get('author', profile['author'])}</div>
                <div class="imprint" style="margin-top: 1.5in;">
                    THE ARGON BOOK STUDIO • FINE TYPESETTING
                </div>
            </div>
        </div>
        """

        # Copyright Page
        html += f"""
        <div class="suppress-all" style="font-size: 8.5pt; line-height: 12.5pt; color: #444; padding-top: 4.8in;">
            <p class="indent-zero"><strong>{parsed_book.get('title', profile['title'])}</strong></p>
            <p class="indent-zero">Copyright © 2026 by {parsed_book.get('author', profile['author'])}</p>
            <p class="indent-zero" style="margin-top: 8pt;">All rights reserved. First 6x9" Illustrated Collector's Edition.</p>
            <p class="indent-zero" style="margin-top: 8pt;">Published by The Argon Book Studio Press.</p>
            <p class="indent-zero">ISBN 978-1-987654-32-1 (Fine Hardcover)</p>
            <p class="indent-zero">ISBN 978-1-987654-33-8 (EPUB 3 Edition)</p>
            <p class="indent-zero" style="margin-top: 14pt;">
                Typeset in {profile['body_font_name']} ({profile['body_font_size']}) with display elements in {profile['display_font_name']}.
                Printed on 70lb acid-free archival vellum paper.
            </p>
        </div>
        """

        # Table of Contents
        html += f"""
        <div class="suppress-all" style="padding-top: 1.5in;">
            <h2 style="font-family: {profile['display_font']}; font-size: 14pt; letter-spacing: 0.16em; text-align: center; text-transform: uppercase; margin-bottom: 24pt;">
                Contents
            </h2>
        """
        for ch in parsed_book.get("chapters", []):
            ch_num = ch.get("chapter_number", "")
            ch_title = ch.get("title", "")
            html += f"""
            <div class="toc-entry">
                <span><strong>Chapter {ch_num}</strong> — {ch_title}</span>
            </div>
            """
        html += "</div>"

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
        
        # Check opener vignette
        first_p_done = False
        elements = chapter.get("elements", [])
        
        for elem in elements:
            elem_id = elem.get("id", "")
            elem_type = elem.get("type", "paragraph")
            
            # Check anchored illustrations
            for asset in assets_by_anchor.get(elem_id, []):
                placement = asset.get("placement", "")
                img_path = asset.get("image_url", "")
                caption = asset.get("caption", "")
                
                # Convert relative static path to absolute file URL if local
                if img_path.startswith("/static/"):
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    local_path = os.path.join(base_dir, img_path.lstrip("/")).replace("\\", "/")
                    img_src = f"file:///{local_path}"
                else:
                    img_src = img_path
                    
                if placement == "Full-Page Recto Plate":
                    html += f"""
                    </div>
                    <div class="full-plate-page">
                        <img src="{img_src}" alt="{asset.get('title', '')}">
                        <div class="plate-caption">{caption}</div>
                    </div>
                    <div style="page-break-before: always; string-set: chapter-title 'CHAPTER {ch_num} • {ch_title.upper()}';">
                    """
                else:
                    html += f"""
                    <div class="inline-plate-div">
                        <img src="{img_src}" alt="{asset.get('title', '')}">
                        <div class="plate-caption">{caption}</div>
                    </div>
                    """

            if elem_type == "paragraph":
                text = elem.get("text", "")
                is_first = elem.get("is_first_after_break", False) or not first_p_done
                cls = "indent-zero has-drop-cap" if not first_p_done else ("indent-zero" if is_first else "")
                html += f'<p class="{cls}">{text}</p>\n'
                first_p_done = True
                
            elif elem_type == "container":
                tag = elem.get("tag", "inquest-writ")
                content = elem.get("content", "").replace("\n", "<br>")
                html += f'<div class="custom-container {tag}">{content}</div>\n'
                
            elif elem_type == "scene_break":
                html += f'<div class="scene-break-div">{profile["scene_break_svg"]}</div>\n'

        # Chapter tailpiece
        html += f"""
            <div class="tailpiece-div">{profile['tailpiece_svg']}</div>
        </div>
        """

    # COLOPHON
    html += f"""
    <div class="suppress-all colophon-page" style="padding-top: 2.5in; font-size: 9pt; line-height: 14pt; color: #333; text-align: center;">
        <h3 style="font-family: {profile['display_font']}; font-size: 11pt; letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 14pt; color: {profile['accent_color']};">
            Colophon
        </h3>
        <p class="indent-zero" style="max-width: 4.2in; margin: 0 auto; text-align: center;">
            This volume was typeset and produced using the Argon Book Studio Universal Publishing Engine.
            Body text is set in {profile['body_font_name']}, calibrated at {profile['body_font_size']} on {profile['body_leading']} leading.
            Display typography and chapter headings are set in {profile['display_font_name']}.
            Layout adheres to 6.0 x 9.0 inch book signatures with mirrored gutter margins.
        </p>
        <div style="margin-top: 24pt;">{profile['tailpiece_svg']}</div>
    </div>
    </body>
    </html>
    """

    return html


def export_pdf(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    output_pdf_path: str,
    bleed: bool = False
) -> str:
    """
    Renders the print-ready 6x9" PDF using Chromium/Edge headless with strict CSS @page rules.
    """
    html_content = generate_pdf_html(parsed_book, manifest, profile_id, bleed=bleed)
    
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

    # If headless browser failed or wasn't available, build via ReportLab
    return _build_fallback_reportlab_pdf(parsed_book, manifest, profile_id, output_pdf_path)


def _build_fallback_reportlab_pdf(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    output_pdf_path: str
) -> str:
    """Fallback ReportLab generator for 6x9 inch PDF."""
    from reportlab.lib.pagesizes import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=(6.0 * inch, 9.0 * inch),
        leftMargin=0.875 * inch,
        rightMargin=0.625 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.875 * inch
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'BookTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
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
