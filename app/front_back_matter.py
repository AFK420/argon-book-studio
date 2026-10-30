"""
Argon Book Studio - Front & Back Matter Generator.
Builds publishing-ready:
1. Half-Title Page
2. Frontispiece Page (with thematic ornament or plate)
3. Full Title Page (Title, Subtitle, Author, Imprint)
4. Copyright Page (Cataloging-in-publication, notices, ISBN, font specs)
5. Table of Contents (Chapter titles, Roman/Arabic numbers)
6. Back-of-Book Edition Colophon
"""

from typing import Dict, Any, List
from app.profiles import BOOK_PROFILES


def generate_front_matter_data(book_profile_id: str, manuscript_meta: Dict[str, Any] = None) -> Dict[str, Any]:
    profile = BOOK_PROFILES.get(book_profile_id, BOOK_PROFILES["book01"])
    meta = manuscript_meta or {}
    
    title = meta.get("title") or profile["title"]
    subtitle = meta.get("subtitle") or profile["subtitle"]
    author = meta.get("author") or profile["author"]
    
    return {
        "half_title": {
            "title": title
        },
        "frontispiece": {
            "title": title,
            "subtitle": subtitle,
            "ornament_svg": profile["scene_break_svg"]
        },
        "title_page": {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "edition": "First Illustrated Fine Edition",
            "imprint": "THE ARGON BOOK STUDIO • PRESS",
            "city": "London & San Francisco"
        },
        "copyright_page": {
            "title": title,
            "author": author,
            "year": "2026",
            "publisher": "Argon Book Studio Press",
            "isbn_hardcover": "978-1-954321-01-9",
            "isbn_epub": "978-1-954321-02-6",
            "notice": "All rights reserved. No part of this publication may be reproduced, stored in a retrieval system, or transmitted in any form without prior permission.",
            "colophon_summary": f"Typeset in 6.0 x 9.0 in format. Body typeface: {profile['body_font_name']} ({profile['body_font_size']}/{profile['body_leading']}). Display typeface: {profile['display_font_name']}."
        },
        "colophon": {
            "headline": "A NOTE ON THE TYPE AND PRODUCTION",
            "body": f"This volume was designed and typeset using the Argon Book Studio Desktop Publishing Engine. The body text is set in {profile['body_font_name']}, chosen for its exceptional legibility and classical proportion. Display headers and chapter openings are set in {profile['display_font_name']}. The book conforms to standard 6.0 x 9.0 inch book signatures, printed with mirrored gutter margins on 70-pound acid-free archival vellum paper.",
            "emblem_svg": profile["tailpiece_svg"]
        }
    }
