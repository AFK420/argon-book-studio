"""
Argon Book Studio - Reflowable EPUB 3 Exporter.
Generates compliant, beautifully styled reflowable EPUB 3 editions
with full embedded CSS matching the selected Book Theme Profile,
chapter navigational landmarks, in-world container stylings, and image manifests.
Supports custom typography, matter additions, and palette overrides.
"""

import os
from typing import Dict, Any, List, Optional
import ebooklib
from ebooklib import epub
from app.profiles import BOOK_PROFILES


def export_epub(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    output_epub_path: str,
    include_front_matter: bool = True,
    custom_specs: Dict[str, Any] = None,
    custom_matter: Dict[str, Any] = None
) -> str:
    profile = BOOK_PROFILES.get(profile_id, BOOK_PROFILES["book01"])
    cs = custom_specs or {}
    cm = custom_matter or {}
    
    accent_color = cs.get("typography", {}).get("accent_color", profile["accent_color"])
    brass_accent = cs.get("typography", {}).get("brass_accent", profile["brass_accent"])
    font_name = cs.get("typography", {}).get("body_font_name", profile["body_font_name"])
    
    book = epub.EpubBook()
    
    book.set_identifier(f"argon-studio-{profile_id}-2026")
    book.set_title(parsed_book.get("title", profile["title"]))
    book.set_language("en")
    book.add_author(parsed_book.get("author", profile["author"]))
    
    style = f"""
    @namespace epub "http://www.idpf.org/2007/ops";
    body {{
        font-family: '{font_name}', Georgia, serif;
        margin: 5%;
        text-align: justify;
        line-height: 1.48;
        color: #111;
        background-color: #fafafa;
    }}
    h1.chapter-title {{
        text-align: center;
        text-transform: uppercase;
        font-size: 1.6em;
        margin-top: 1.5em;
        margin-bottom: 0.2em;
        color: {accent_color};
    }}
    .chapter-number {{
        text-align: center;
        font-size: 0.9em;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: {brass_accent};
        margin-bottom: 0.3em;
    }}
    .scene-break {{
        text-align: center;
        margin: 1.5em 0;
        letter-spacing: 0.3em;
        color: {accent_color};
    }}
    p {{
        margin: 0;
        text-indent: 1.5em;
    }}
    p.indent-zero, p:first-of-type, .scene-break + p, .container + p {{
        text-indent: 0 !important;
    }}
    .container {{
        margin: 1.2em 0;
        padding: 0.8em 1.1em;
        font-size: 0.95em;
        border-radius: 4px;
    }}
    .inquest-writ {{
        border: 2px solid #1B365D;
        background: #FBF8F1;
        color: #1a1a1a;
    }}
    .sensory-draw {{
        border-left: 4px solid #B8860B;
        background: #FDFBF7;
        font-style: italic;
    }}
    .welsh-slate {{
        background: #1E2229;
        color: #F8FAFC;
        border-left: 4px solid #00A896;
    }}
    .telemetry-equation {{
        border: 1px solid #4A5568;
        background: #F5F6F8;
        font-family: monospace;
    }}
    .audio-transcript {{
        background: #0F172A;
        color: #38BDF8;
        border-left: 4px solid #0284C7;
        font-family: monospace;
        font-size: 0.88em;
    }}
    .fsk-payload {{
        border: 1px dashed #475569;
        background: #1E293B;
        color: #E2E8F0;
        font-family: monospace;
    }}
    .pelham-journal {{
        border: 1px solid #4A6B4E;
        background: #FCFAF2;
        color: #2C402E;
        border-left: 4px solid #2C402E;
    }}
    .oscilloscope-readout {{
        border: 1px solid #D97706;
        background: #FFFBEB;
        font-family: monospace;
    }}
    .cuneiform-tablet {{
        border: 2px solid #8C4A28;
        background: #FAF6EE;
    }}
    .cedar-sliver {{
        border-left: 4px solid #C98A2C;
        background: #FDF9F3;
        color: #5A2A18;
    }}
    .illustration-block {{
        text-align: center;
        margin: 1.5em 0;
    }}
    .illustration-block img {{
        max-width: 100%;
        height: auto;
        border: 1px solid #ccc;
    }}
    .caption {{
        font-size: 0.85em;
        font-style: italic;
        color: #555;
        margin-top: 0.4em;
    }}
    .title-screen {{
        text-align: center;
        margin-top: 25%;
    }}
    """
    
    css_item = epub.EpubItem(
        uid="style_book",
        file_name="style/book.css",
        media_type="text/css",
        content=style
    )
    book.add_item(css_item)

    assets_by_anchor: Dict[str, List[Dict[str, Any]]] = {}
    for a in manifest.get("assets", []):
        assets_by_anchor.setdefault(a.get("anchor", ""), []).append(a)

    spine: List[Any] = ['nav']
    toc_items: List[Any] = []

    # Title page
    if include_front_matter:
        imprint_txt = cm.get("publisher_imprint", "THE ARGON BOOK STUDIO • FINE EDITIONS")
        title_html = f"""
        <div class="title-screen">
            <h1 style="font-size: 2em; margin-bottom: 0.3em; color: {accent_color};">{parsed_book.get('title', profile['title'])}</h1>
            <p style="font-style: italic; margin-bottom: 2em; color: #555;">{parsed_book.get('subtitle', profile['subtitle'])}</p>
            <p style="font-weight: bold; letter-spacing: 0.1em; text-transform: uppercase;">{parsed_book.get('author', profile['author'])}</p>
            <p style="margin-top: 3em; font-size: 0.8em; color: #777;">{imprint_txt}</p>
        </div>
        """
        c_title = epub.EpubHtml(title="Title Page", file_name="title.xhtml", lang="en")
        c_title.content = title_html
        c_title.add_item(css_item)
        book.add_item(c_title)
        spine.append(c_title)

        if cm.get("include_dedication", False):
            ded_html = f"""
            <div style="text-align:center; margin-top:30%; font-style:italic;">
                <p>{cm.get('dedication_text', '')}</p>
            </div>
            """
            c_ded = epub.EpubHtml(title="Dedication", file_name="dedication.xhtml", lang="en")
            c_ded.content = ded_html
            c_ded.add_item(css_item)
            book.add_item(c_ded)
            spine.append(c_ded)

        if cm.get("include_epigraph", False):
            epi_html = f"""
            <div style="text-align:center; margin-top:30%;">
                <p style="font-style:italic;">"{cm.get('epigraph_text', '')}"</p>
                <p style="font-size:0.85em; color:#666; margin-top:1em;">{cm.get('epigraph_source', '')}</p>
            </div>
            """
            c_epi = epub.EpubHtml(title="Epigraph", file_name="epigraph.xhtml", lang="en")
            c_epi.content = epi_html
            c_epi.add_item(css_item)
            book.add_item(c_epi)
            spine.append(c_epi)

    # Chapters
    for ch_idx, chapter in enumerate(parsed_book.get("chapters", [])):
        ch_num = chapter.get("chapter_number", str(ch_idx + 1))
        ch_title = chapter.get("title", "")
        file_name = f"chapter_{ch_idx + 1:02d}.xhtml"
        
        ch_html = f"""
        <div class="chapter-number">Chapter {ch_num}</div>
        <h1 class="chapter-title">{ch_title}</h1>
        """
        
        first_p_done = False
        for elem in chapter.get("elements", []):
            elem_id = elem.get("id", "")
            elem_type = elem.get("type", "paragraph")
            
            for asset in assets_by_anchor.get(elem_id, []):
                caption = asset.get("caption", "")
                ch_html += f"""
                <div class="illustration-block">
                    <p class="caption"><strong>[Plate: {asset.get('title', '')}]</strong><br>{caption}</p>
                </div>
                """

            if elem_type == "paragraph":
                text = elem.get("text", "")
                is_first = elem.get("is_first_after_break", False) or not first_p_done
                cls = ' class="indent-zero"' if is_first else ''
                ch_html += f'<p{cls}>{text}</p>\n'
                first_p_done = True
            elif elem_type == "container":
                tag = elem.get("tag", "inquest-writ")
                content = elem.get("content", "").replace("\n", "<br/>")
                ch_html += f'<div class="container {tag}">{content}</div>\n'
            elif elem_type == "scene_break":
                ch_html += '<div class="scene-break">❖   ❖   ❖</div>\n'

        c_item = epub.EpubHtml(title=f"Chapter {ch_num}: {ch_title}", file_name=file_name, lang="en")
        c_item.content = ch_html
        c_item.add_item(css_item)
        book.add_item(c_item)
        spine.append(c_item)
        toc_items.append(c_item)

    if cm.get("include_acknowledgements", False):
        ack_html = f"""
        <div style="margin-top:15%;">
            <h2 style="text-align:center; text-transform:uppercase;">Acknowledgements</h2>
            <p>{cm.get('acknowledgements_text', '')}</p>
        </div>
        """
        c_ack = epub.EpubHtml(title="Acknowledgements", file_name="acknowledgements.xhtml", lang="en")
        c_ack.content = ack_html
        c_ack.add_item(css_item)
        book.add_item(c_ack)
        spine.append(c_ack)

    if cm.get("include_about_author", False):
        aut_html = f"""
        <div style="margin-top:15%;">
            <h2 style="text-align:center; text-transform:uppercase;">About the Author</h2>
            <p>{cm.get('about_author_text', '')}</p>
        </div>
        """
        c_aut = epub.EpubHtml(title="About the Author", file_name="about_author.xhtml", lang="en")
        c_aut.content = aut_html
        c_aut.add_item(css_item)
        book.add_item(c_aut)
        spine.append(c_aut)

    if cm.get("include_colophon", True):
        colophon_body = cm.get("colophon_text") or (
            "This reflowable EPUB edition was produced with the Argon Book Studio Universal Typesetting Engine.<br/>"
            "Engineered for high readability across e-ink readers and modern mobile displays."
        )
        colophon_html = f"""
        <div style="text-align: center; margin-top: 30%; font-size: 0.9em; line-height: 1.5; color: #555;">
            <h3 style="letter-spacing: 0.15em; text-transform: uppercase;">Colophon</h3>
            <p class="indent-zero">{colophon_body}</p>
        </div>
        """
        c_col = epub.EpubHtml(title="Colophon", file_name="colophon.xhtml", lang="en")
        c_col.content = colophon_html
        c_col.add_item(css_item)
        book.add_item(c_col)
        spine.append(c_col)

    book.toc = tuple(toc_items)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    os.makedirs(os.path.dirname(output_epub_path), exist_ok=True)
    epub.write_epub(output_epub_path, book)
    return output_epub_path
