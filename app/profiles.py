"""
Book Theme Profiles for Argon Book Studio.
Each profile encodes the typography, ornamentation, custom document containers,
scene break SVG, image filter presets, and print styling rules for a specific book.
"""

from typing import Dict, Any, List

BOOK_PROFILES: Dict[str, Dict[str, Any]] = {
    "book01": {
        "id": "book01",
        "title": "Cormac Vane: The Alchemical Inquest",
        "short_title": "Cormac Vane",
        "author": "A. E. Sterling & The Argon Studio",
        "genre": "Gaslamp Forensic / Victorian Occult Mystery",
        "subtitle": "Being the Case of the Salt-Cellar Murders",
        "body_font": "EB Garamond, Baskerville, 'Times New Roman', serif",
        "body_font_name": "EB Garamond",
        "body_font_size": "11pt",
        "body_leading": "15pt",
        "display_font": "Cinzel, 'Caslon Antique', 'Times New Roman', serif",
        "display_font_name": "Cinzel",
        "accent_color": "#1B365D",
        "frame_color": "#2C2C2C",
        "brass_accent": "#B8860B",
        "paper_tint": "#FBF8F1",
        "drop_cap_style": "cinzel-brass",
        "scene_break_name": "Brass Caliper & Gear Diamond",
        "scene_break_svg": """<svg viewBox="0 0 240 32" class="scene-break-svg" xmlns="http://www.w3.org/2000/svg">
            <line x1="10" y1="16" x2="85" y2="16" stroke="#1B365D" stroke-width="1.2" stroke-dasharray="4,2"/>
            <circle cx="95" cy="16" r="3" fill="#B8860B"/>
            <polygon points="120,6 128,16 120,26 112,16" fill="none" stroke="#1B365D" stroke-width="1.5"/>
            <circle cx="120" cy="16" r="2" fill="#B8860B"/>
            <!-- Caliper points -->
            <path d="M110,16 Q120,2 130,16" fill="none" stroke="#B8860B" stroke-width="1" stroke-linecap="round"/>
            <path d="M110,16 Q120,30 130,16" fill="none" stroke="#B8860B" stroke-width="1" stroke-linecap="round"/>
            <circle cx="145" cy="16" r="3" fill="#B8860B"/>
            <line x1="155" y1="16" x2="230" y2="16" stroke="#1B365D" stroke-width="1.2" stroke-dasharray="4,2"/>
        </svg>""",
        "tailpiece_svg": """<svg viewBox="0 0 160 80" class="tailpiece-svg" xmlns="http://www.w3.org/2000/svg">
            <g transform="translate(80, 40)">
                <circle cx="0" cy="0" r="14" fill="none" stroke="#1B365D" stroke-width="1.2"/>
                <circle cx="0" cy="0" r="10" fill="none" stroke="#B8860B" stroke-width="0.8" stroke-dasharray="2,2"/>
                <!-- Caliper arms -->
                <path d="M-22,-18 C-10,-5 -5,15 0,26 C5,15 10,-5 22,-18" fill="none" stroke="#1B365D" stroke-width="1.5"/>
                <circle cx="0" cy="0" r="3" fill="#1B365D"/>
                <polygon points="0,-30 -4,-22 4,-22" fill="#B8860B"/>
                <line x1="-50" y1="0" x2="-25" y2="0" stroke="#1B365D" stroke-width="1"/>
                <line x1="25" y1="0" x2="50" y2="0" stroke="#1B365D" stroke-width="1"/>
                <circle cx="-55" cy="0" r="2" fill="#B8860B"/>
                <circle cx="55" cy="0" r="2" fill="#B8860B"/>
            </g>
        </svg>""",
        "filter_preset": "cyanotype_silver_plate",
        "filter_name": "Cyanotype / 19th-Century Silver-Plate Etching",
        "filter_description": "Monochromatic Prussian-cyan tint with 19th-century silver halide etched grain, contrast-deepened midtones, and delicate paper stippling.",
        "containers": [
            {
                "tag": "inquest-writ",
                "label": "Coroner's Inquest Writ",
                "description": "Double-framed antique parchment container for sworn testimonies, post-mortem findings, and magistrate warrants.",
                "css_class": "inquest-writ",
            },
            {
                "tag": "sensory-draw",
                "label": "Vesper Sensory Draw",
                "description": "Narrowed inner-margin rule block for heightened alchemical perception, olfactory notes, and nervous impressions.",
                "css_class": "sensory-draw",
            }
        ]
    },
    "book02": {
        "id": "book02",
        "title": "The Fourteen-Hour Barometer",
        "short_title": "Fourteen-Hour Barometer",
        "author": "Dr. E. K. Maren & The Argon Studio",
        "genre": "Chronometric Island Thriller / Meteorological Mystery",
        "subtitle": "Telemetry of the Ghyll Skerries Anomaly",
        "body_font": "Lora, Georgia, 'Times New Roman', serif",
        "body_font_name": "Lora",
        "body_font_size": "10.5pt",
        "body_leading": "14.5pt",
        "display_font": "Oswald, 'Montserrat Bold', 'Arial Black', sans-serif",
        "display_font_name": "Oswald",
        "accent_color": "#1E2229",
        "frame_color": "#4A5568",
        "brass_accent": "#00A896",
        "paper_tint": "#F5F6F8",
        "drop_cap_style": "oswald-bold",
        "scene_break_name": "Split Piezoelectric Wave-Fault Line",
        "scene_break_svg": """<svg viewBox="0 0 240 32" class="scene-break-svg" xmlns="http://www.w3.org/2000/svg">
            <line x1="10" y1="16" x2="70" y2="16" stroke="#1E2229" stroke-width="1.5"/>
            <!-- Wave pulse -->
            <path d="M70,16 L85,16 L92,4 L100,28 L108,8 L116,22 L122,16 L170,16" fill="none" stroke="#00A896" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            <line x1="170" y1="16" x2="230" y2="16" stroke="#1E2229" stroke-width="1.5"/>
            <!-- Fault fissure -->
            <circle cx="100" cy="28" r="2.5" fill="#1E2229"/>
            <circle cx="108" cy="8" r="2.5" fill="#00A896"/>
        </svg>""",
        "tailpiece_svg": """<svg viewBox="0 0 160 80" class="tailpiece-svg" xmlns="http://www.w3.org/2000/svg">
            <g transform="translate(80, 40)">
                <rect x="-35" y="-18" width="70" height="36" rx="3" fill="#1E2229" stroke="#00A896" stroke-width="1.2"/>
                <!-- Oscillating mercury meniscus -->
                <path d="M-28,4 Q-14,-10 0,2 Q14,14 28,-4" fill="none" stroke="#FFFFFF" stroke-width="1.5"/>
                <circle cx="0" cy="2" r="3" fill="#00A896"/>
                <line x1="-55" y1="0" x2="-35" y2="0" stroke="#1E2229" stroke-width="1.5"/>
                <line x1="35" y1="0" x2="55" y2="0" stroke="#1E2229" stroke-width="1.5"/>
                <text x="0" y="-8" fill="#A0AEC0" font-family="monospace" font-size="6" text-anchor="middle">982.4 hPa</text>
            </g>
        </svg>""",
        "filter_preset": "charcoal_lithograph",
        "filter_name": "Charcoal & Hebridean Lithograph Wash",
        "filter_description": "Desaturated wet charcoal wash with authentic Hebridean lithographic plate grain, high salt spray atmospheric haze, and deep slate shadows.",
        "containers": [
            {
                "tag": "welsh-slate",
                "label": "Welsh Slate Message",
                "description": "Dark basalt/slate background (#1E2229) with rough chalk-white serif typography representing etched island warnings.",
                "css_class": "welsh-slate",
            },
            {
                "tag": "telemetry-equation",
                "label": "Chronometric Telemetry",
                "description": "Framed engineering callout with uppercase tracked telemetry timestamps (RONAN: Thursday, 08:00) and barometer gradient data.",
                "css_class": "telemetry-equation",
            }
        ]
    },
    "book03": {
        "id": "book03",
        "title": "Dead-Room Transcripts",
        "short_title": "Dead-Room Transcripts",
        "author": "Dr. Harlan Finch & The Argon Studio",
        "genre": "Acoustic Locked-Room Mystery / Sonic Espionage",
        "subtitle": "The Audio Cryptanalysis of Bunker Zero",
        "body_font": "'Source Serif 4', Charter, Georgia, serif",
        "body_font_name": "Source Serif 4",
        "body_font_size": "10.5pt",
        "body_leading": "14.5pt",
        "display_font": "'JetBrains Mono', 'IBM Plex Mono', 'Courier New', monospace",
        "display_font_name": "JetBrains Mono",
        "accent_color": "#0F172A",
        "frame_color": "#334155",
        "brass_accent": "#38BDF8",
        "paper_tint": "#F8FAFC",
        "drop_cap_style": "mono-clean",
        "scene_break_name": "42.4 Hz Sine-Wave Dampening Pulse",
        "scene_break_svg": """<svg viewBox="0 0 240 32" class="scene-break-svg" xmlns="http://www.w3.org/2000/svg">
            <line x1="10" y1="16" x2="60" y2="16" stroke="#0F172A" stroke-width="1.2"/>
            <!-- Sine pulse dampening -->
            <path d="M60,16 Q72,-4 84,16 Q96,36 108,16 Q118,4 128,16 Q138,26 148,16 Q156,11 164,16 Q172,19 180,16" fill="none" stroke="#0284C7" stroke-width="1.6" stroke-linecap="round"/>
            <line x1="180" y1="16" x2="230" y2="16" stroke="#0F172A" stroke-width="1.2"/>
            <text x="120" y="30" fill="#64748B" font-family="monospace" font-size="6" text-anchor="middle">f = 42.40 Hz</text>
        </svg>""",
        "tailpiece_svg": """<svg viewBox="0 0 160 80" class="tailpiece-svg" xmlns="http://www.w3.org/2000/svg">
            <g transform="translate(80, 40)">
                <!-- Sound baffle diamond grid -->
                <rect x="-30" y="-18" width="60" height="36" fill="none" stroke="#0F172A" stroke-width="1.2"/>
                <line x1="-30" y1="-18" x2="30" y2="18" stroke="#38BDF8" stroke-width="0.8"/>
                <line x1="-30" y1="18" x2="30" y2="-18" stroke="#38BDF8" stroke-width="0.8"/>
                <line x1="-30" y1="0" x2="30" y2="0" stroke="#0F172A" stroke-width="1"/>
                <circle cx="0" cy="0" r="6" fill="#0F172A"/>
                <circle cx="0" cy="0" r="3" fill="#38BDF8"/>
                <line x1="-50" y1="0" x2="-30" y2="0" stroke="#0F172A" stroke-width="1"/>
                <line x1="30" y1="0" x2="50" y2="0" stroke="#0F172A" stroke-width="1"/>
            </g>
        </svg>""",
        "filter_preset": "blueprint_halftone",
        "filter_name": "High-Contrast Oscilloscope & Architectural Blueprint Halftone",
        "filter_description": "Navy-cyan blueprint duotone with oscilloscope beam glow, matrix grid coordinates, high edge contrast, and micro-dot screening.",
        "containers": [
            {
                "tag": "audio-transcript",
                "label": "DAW Audio Transcript Log",
                "description": "Monospace DAW log box with left decibel ruler (-60dB to 0dB), channel markers (CH-1 / CH-2), and timecode stamps [00:14:22.109].",
                "css_class": "audio-transcript",
            },
            {
                "tag": "fsk-payload",
                "label": "FSK Decoded Payload",
                "description": "Bordered terminal decode block with hex dump stream, parity checks, and deciphered phonetic audio packets.",
                "css_class": "fsk-payload",
            }
        ]
    },
    "book04": {
        "id": "book04",
        "title": "The Salt Orchard of Saint Jude",
        "short_title": "Salt Orchard of Saint Jude",
        "author": "Cordelia Vane Pelham & The Argon Studio",
        "genre": "Ecological Southern Gothic / Lowcountry Bioluminescence",
        "subtitle": "Field Studies in Marsh Necrosis and Deep Root Glow",
        "body_font": "'Cormorant Garamond', Palatino, 'Times New Roman', serif",
        "body_font_name": "Cormorant Garamond",
        "body_font_size": "11.5pt",
        "body_leading": "15.2pt",
        "display_font": "'Cormorant Garamond', Garamond, 'Georgia', serif",
        "display_font_name": "Cormorant Garamond Italic",
        "accent_color": "#2C402E",
        "frame_color": "#4A6B4E",
        "brass_accent": "#D97706",
        "paper_tint": "#FCFAF2",
        "drop_cap_style": "botanical-italic",
        "scene_break_name": "Intertwined Sea-Fig Root & Seahorse Vignette",
        "scene_break_svg": """<svg viewBox="0 0 240 32" class="scene-break-svg" xmlns="http://www.w3.org/2000/svg">
            <path d="M10,16 Q45,12 80,16 Q100,18 110,12 Q120,4 125,12 Q130,22 140,16 Q175,12 230,16" fill="none" stroke="#2C402E" stroke-width="1.2"/>
            <!-- Seahorse & botanical bud center -->
            <g transform="translate(120,16)">
                <path d="M-8,6 C-12,0 -8,-8 0,-8 C6,-8 8,-3 4,4 C0,10 -4,12 -8,6 Z" fill="#4A6B4E" opacity="0.85"/>
                <circle cx="-1" cy="-4" r="1.5" fill="#D97706"/>
                <path d="M4,-4 Q12,-8 10,0 Q8,8 2,10" fill="none" stroke="#D97706" stroke-width="1.2"/>
                <circle cx="10" cy="0" r="1.5" fill="#2C402E"/>
            </g>
        </svg>""",
        "tailpiece_svg": """<svg viewBox="0 0 160 80" class="tailpiece-svg" xmlns="http://www.w3.org/2000/svg">
            <g transform="translate(80, 40)">
                <!-- Intertwined botanical tendrils -->
                <path d="M-40,15 C-25,5 -15,-20 0,-15 C15,-10 25,15 40,5" fill="none" stroke="#2C402E" stroke-width="1.5"/>
                <path d="M-40,-5 C-25,-15 -15,10 0,5 C15,0 25,-20 40,-15" fill="none" stroke="#4A6B4E" stroke-width="1.2"/>
                <circle cx="0" cy="-5" r="4" fill="#D97706"/>
                <circle cx="-18" cy="2" r="2" fill="#2C402E"/>
                <circle cx="18" cy="-2" r="2" fill="#2C402E"/>
                <line x1="-55" y1="0" x2="-40" y2="0" stroke="#2C402E" stroke-width="1"/>
                <line x1="40" y1="0" x2="55" y2="0" stroke="#2C402E" stroke-width="1"/>
            </g>
        </svg>""",
        "filter_preset": "sepia_bioluminescent_amber",
        "filter_name": "1928 Sepia & Bioluminescent Amber Botanical Plate",
        "filter_description": "Rich 1928 archival warm sepia plate stippling with glowing warm amber bioluminescent highlights in deep botanical shadows.",
        "containers": [
            {
                "tag": "pelham-journal",
                "label": "Pelham 1928 Archival Ledger",
                "description": "Sepia-lined ledger container with hand-notated dates, water-stain margins, and botanical specimen classifications.",
                "css_class": "pelham-journal",
            },
            {
                "tag": "oscilloscope-readout",
                "label": "Neuro-Conduction Metric Box",
                "description": "Scientific field box measuring sap-flow microvoltages, tidal immersion hours, and root-spore bio-luminescence curves.",
                "css_class": "oscilloscope-readout",
            }
        ]
    },
    "book05": {
        "id": "book05",
        "title": "Provenance of Ashes",
        "short_title": "Provenance of Ashes",
        "author": "T. A. Qadir & The Argon Studio",
        "genre": "Archaeometric Thriller / Epigraphic Provenance",
        "subtitle": "Neutron Activation and the Nineveh Smuggler's Tablets",
        "body_font": "'Crimson Pro', 'Minion Pro', Georgia, serif",
        "body_font_name": "Crimson Pro",
        "body_font_size": "10.5pt",
        "body_leading": "14.5pt",
        "display_font": "'Cinzel Decorative', Trajan, 'Cinzel', serif",
        "display_font_name": "Trajan / Cinzel Decorative",
        "accent_color": "#5A2A18",
        "frame_color": "#8C4A28",
        "brass_accent": "#C98A2C",
        "paper_tint": "#FAF6EE",
        "drop_cap_style": "cuneiform-frame",
        "scene_break_name": "Triple Cuneiform Wedge Divider",
        "scene_break_svg": """<svg viewBox="0 0 240 32" class="scene-break-svg" xmlns="http://www.w3.org/2000/svg">
            <line x1="10" y1="16" x2="80" y2="16" stroke="#5A2A18" stroke-width="1.2"/>
            <!-- Cuneiform wedge rule ◁ • ▷ -->
            <polygon points="90,16 102,11 102,21" fill="#8C4A28"/>
            <polygon points="107,16 119,11 119,21" fill="#C98A2C"/>
            <circle cx="120" cy="16" r="3" fill="#5A2A18"/>
            <polygon points="133,16 121,11 121,21" fill="#C98A2C"/>
            <polygon points="150,16 138,11 138,21" fill="#8C4A28"/>
            <line x1="160" y1="16" x2="230" y2="16" stroke="#5A2A18" stroke-width="1.2"/>
        </svg>""",
        "tailpiece_svg": """<svg viewBox="0 0 160 80" class="tailpiece-svg" xmlns="http://www.w3.org/2000/svg">
            <g transform="translate(80, 40)">
                <polygon points="0,-22 24,0 0,22 -24,0" fill="none" stroke="#5A2A18" stroke-width="1.5"/>
                <!-- Cuneiform wedge motifs -->
                <polygon points="0,-12 6,-6 -6,-6" fill="#C98A2C"/>
                <polygon points="0,12 6,6 -6,6" fill="#C98A2C"/>
                <polygon points="-12,0 -6,6 -6,-6" fill="#8C4A28"/>
                <polygon points="12,0 6,6 6,-6" fill="#8C4A28"/>
                <circle cx="0" cy="0" r="2.5" fill="#5A2A18"/>
                <line x1="-50" y1="0" x2="-24" y2="0" stroke="#5A2A18" stroke-width="1"/>
                <line x1="24" y1="0" x2="50" y2="0" stroke="#5A2A18" stroke-width="1"/>
            </g>
        </svg>""",
        "filter_preset": "desert_ochre_uv",
        "filter_name": "Desert Ochre & UV-Fluorescence Archaeometric Micro-Grain",
        "filter_description": "Desert ochre terra-cotta tones blended with UV-induced fluorescent trace highlights, micro-crack line etching, and museum specimen stippling.",
        "containers": [
            {
                "tag": "cuneiform-tablet",
                "label": "Epigraphic Transliteration Table",
                "description": "Two-column tablet transcription container with line numbers, bracketed phonetic signs [an-za-qàr], and translation glosses.",
                "css_class": "cuneiform-tablet",
            },
            {
                "tag": "cedar-sliver",
                "label": "Carved Cedar Note Block",
                "description": "Warm timber-grain callout box for carbon-14 dendrochronology dating and excavator field diary fragments.",
                "css_class": "cedar-sliver",
            }
        ]
    }
}

UNIVERSAL_PUBLISHING_SPECS = {
    "trim_width_in": 6.0,
    "trim_height_in": 9.0,
    "bleed_in": 0.125,
    "margins": {
        "inside_gutter_in": 0.875,
        "outside_margin_in": 0.625,
        "top_margin_in": 0.75,
        "bottom_margin_in": 0.875,
    },
    "grid_rules": {
        "orphans": 3,
        "widows": 3,
        "first_p_indent_in": 0.0,
        "subsequent_p_indent_in": 0.25,
        "subsequent_p_margin_bottom_in": 0.0,
        "chapter_sinkage_in": 1.75,
        "running_header_font_size_pt": 8.5,
        "short_ending_threshold_lines": 18,
    }
}
