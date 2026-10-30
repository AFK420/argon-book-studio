"""
Argon Book Studio - Front & Back Matter Generator.
Builds publishing-ready front and back matter structures:
1. Half-Title Page
2. Thematic Frontispiece Page
3. Full Title Page (Title, Subtitle, Author, Imprint, City)
4. Copyright Page (Cataloging, ISBNs, Rights, Typography Specs)
5. Dedication Page (Optional)
6. Epigraph Page (Optional)
7. Table of Contents
8. Acknowledgements Page (Optional)
9. About the Author Page (Optional)
10. Back-of-Book Edition Colophon
"""

from typing import Dict, Any, List, Optional
from app.profiles import BOOK_PROFILES


def generate_front_matter_data(
    book_profile_id: str,
    manuscript_meta: Dict[str, Any] = None,
    custom_matter: Dict[str, Any] = None
) -> Dict[str, Any]:
    profile = BOOK_PROFILES.get(book_profile_id, BOOK_PROFILES["book01"])
    meta = manuscript_meta or {}
    cm = custom_matter or {}
    
    title = meta.get("title") or profile["title"]
    subtitle = meta.get("subtitle") or profile["subtitle"]
    author = meta.get("author") or profile["author"]
    
    imprint = cm.get("publisher_imprint", "THE ARGON BOOK STUDIO • PRESS")
    city = cm.get("city", "London & San Francisco")
    isbn_hardcover = cm.get("isbn_hardcover", "978-1-954321-01-9")
    isbn_epub = cm.get("isbn_epub", "978-1-954321-02-6")
    
    return {
        "half_title": {
            "title": title,
            "enabled": cm.get("include_half_title", True)
        },
        "frontispiece": {
            "title": title,
            "subtitle": subtitle,
            "ornament_svg": profile["scene_break_svg"],
            "enabled": cm.get("include_frontispiece", True)
        },
        "title_page": {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "edition": "First Illustrated Fine Edition",
            "imprint": imprint,
            "city": city,
            "enabled": cm.get("include_title_page", True)
        },
        "copyright_page": {
            "title": title,
            "author": author,
            "year": "2026",
            "publisher": imprint,
            "isbn_hardcover": isbn_hardcover,
            "isbn_epub": isbn_epub,
            "notice": "All rights reserved. No part of this publication may be reproduced, stored in a retrieval system, or transmitted in any form without prior permission of the publisher.",
            "colophon_summary": f"Typeset in 6.0 x 9.0 in format. Body typeface: {profile['body_font_name']} ({profile['body_font_size']}/{profile['body_leading']}). Display typeface: {profile['display_font_name']}.",
            "enabled": cm.get("include_copyright", True)
        },
        "dedication": {
            "text": cm.get("dedication_text", "To those who seek truth in the silence between notes."),
            "enabled": cm.get("include_dedication", False)
        },
        "epigraph": {
            "text": cm.get("epigraph_text", "The sea does not surrender its dead, nor does the stone forget."),
            "source": cm.get("epigraph_source", "— Port Assayer's Chronicle, 1844"),
            "enabled": cm.get("include_epigraph", False)
        },
        "table_of_contents": {
            "title": "Contents",
            "enabled": cm.get("include_toc", True)
        },
        "map_plate": {
            "title": cm.get("map_title", "Archival Chart & Survey Map"),
            "caption": cm.get("map_caption", "Hydrographic Soundings & Survey of the Ghyll Skerries."),
            "ornament_svg": profile["scene_break_svg"],
            "enabled": cm.get("include_map", False)
        },
        "appendix": {
            "title": cm.get("appendix_title", "Appendix: Chronometric & Forensic Telemetry"),
            "text": cm.get("appendix_text", "Calibration logs recorded at 14-minute intervals following the barometric depression."),
            "enabled": cm.get("include_appendix", False)
        },
        "glossary": {
            "title": cm.get("glossary_title", "Glossary of Technical & In-World Terms"),
            "terms": cm.get("glossary_terms", [
                {"term": "Barometer Skerry", "definition": "A sub-surface basalt reef producing localized micro-baric fluctuations."},
                {"term": "Vesper Draw", "definition": "An occult sensory distillation utilizing mercury and sea-salt."}
            ]),
            "enabled": cm.get("include_glossary", False)
        },
        "acknowledgements": {
            "title": "Acknowledgements",
            "text": cm.get("acknowledgements_text", "With special gratitude to the archivists and epigraphers whose field diaries provided foundational technical references."),
            "enabled": cm.get("include_acknowledgements", False)
        },
        "about_author": {
            "title": "About the Author",
            "text": cm.get("about_author_text", "The authors and artists of Argon Studio specialize in archaeometric thrillers and illustrated fine book design."),
            "enabled": cm.get("include_about_author", False)
        },
        "colophon": {
            "headline": cm.get("colophon_headline", "A NOTE ON THE TYPE AND PRODUCTION"),
            "body": cm.get("colophon_text") or (
                f"This volume was designed and typeset using the Argon Book Studio Desktop Publishing Engine. "
                f"The body text is set in {profile['body_font_name']}, chosen for its exceptional legibility and classical proportion. "
                f"Display headers and chapter openings are set in {profile['display_font_name']}. "
                f"Printed on acid-free archival vellum paper."
            ),
            "emblem_svg": profile["tailpiece_svg"],
            "enabled": cm.get("include_colophon", True)
        }
    }
