"""Warm-paper theme for the DebateIQ handbook.

Dark themes look slick on screen but get tiring after ~30 minutes of study.
This theme borrows from physical textbooks: a cream background, deep navy
body text, muted rust and teal accents. Code blocks stay slightly darker
than the page so they stand out without shouting.
"""

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import mm

# ---------------------------------------------------------------- palette
PAGE_BG       = colors.HexColor("#f6f1e7")  # warm cream
PANEL_BG      = colors.HexColor("#ece5d2")  # soft tan for callout boxes
SOFT_BG       = colors.HexColor("#e6ddc6")
BORDER        = colors.HexColor("#cdbe9f")
TEXT          = colors.HexColor("#1f2530")  # near-black navy, easy contrast
MUTED         = colors.HexColor("#5a5a52")
ACCENT        = colors.HexColor("#1a4a5c")  # deep teal for chapter titles
ACCENT_2      = colors.HexColor("#8a4124")  # rust for section titles
ACCENT_3      = colors.HexColor("#3f6f3f")  # forest green for sub-sections
WARN          = colors.HexColor("#a8341d")  # warm red for bugs / dangers
INFO          = colors.HexColor("#2a5a8c")  # navy blue for tips
TERM          = colors.HexColor("#6e4a18")  # buzzword gloss color
CODE_BG       = colors.HexColor("#262626")  # dark code block contrasts paper
CODE_TEXT     = colors.HexColor("#f0e9d0")
LINK          = colors.HexColor("#1e5a8c")

# Page geometry
PAGE_W, PAGE_H = (170 * mm, 235 * mm)
LEFT, RIGHT, TOP, BOTTOM = 18 * mm, 18 * mm, 22 * mm, 22 * mm


# ---------------------------------------------------------------- styles
def build_styles() -> StyleSheet1:
    ss = StyleSheet1()

    ss.add(ParagraphStyle(
        name="CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=36, leading=42, textColor=ACCENT,
        alignment=TA_CENTER, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        name="CoverSubtitle",
        fontName="Helvetica",
        fontSize=13, leading=18, textColor=TEXT,
        alignment=TA_CENTER, spaceAfter=4,
    ))
    ss.add(ParagraphStyle(
        name="CoverMuted",
        fontName="Helvetica-Oblique",
        fontSize=10, leading=14, textColor=MUTED,
        alignment=TA_CENTER,
    ))
    ss.add(ParagraphStyle(
        name="ChapterNumber",
        fontName="Helvetica-Bold",
        fontSize=10, leading=14, textColor=MUTED,
        alignment=TA_LEFT, spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        name="ChapterTitle",
        fontName="Helvetica-Bold",
        fontSize=24, leading=30, textColor=ACCENT,
        alignment=TA_LEFT, spaceAfter=10,
    ))
    ss.add(ParagraphStyle(
        name="ChapterLead",
        fontName="Helvetica-Oblique",
        fontSize=11, leading=16, textColor=MUTED,
        alignment=TA_LEFT, spaceAfter=10,
    ))
    ss.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=15, leading=20, textColor=ACCENT_2,
        spaceBefore=14, spaceAfter=5,
    ))
    ss.add(ParagraphStyle(
        name="SubSection",
        fontName="Helvetica-Bold",
        fontSize=11.5, leading=16, textColor=ACCENT_3,
        spaceBefore=8, spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        name="Body",
        fontName="Helvetica",
        fontSize=10.5, leading=16, textColor=TEXT,
        spaceBefore=2, spaceAfter=6, alignment=TA_JUSTIFY,
    ))
    ss.add(ParagraphStyle(
        name="Muted",
        fontName="Helvetica-Oblique",
        fontSize=9.5, leading=13, textColor=MUTED,
    ))
    ss.add(ParagraphStyle(
        name="Bullet",
        fontName="Helvetica",
        fontSize=10.5, leading=15, textColor=TEXT,
        leftIndent=18, firstLineIndent=-12,
        spaceAfter=3, alignment=TA_LEFT,
    ))
    # Code block uses a dark surface — it's the only dark element on the page,
    # which makes code immediately legible as code.
    ss.add(ParagraphStyle(
        name="Code",
        fontName="Courier",
        fontSize=9, leading=12, textColor=CODE_TEXT,
        leftIndent=10, rightIndent=10,
        backColor=CODE_BG, borderColor=CODE_BG, borderWidth=0.5, borderPadding=10,
        spaceBefore=4, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        name="Callout",
        fontName="Helvetica",
        fontSize=10, leading=14, textColor=TEXT,
        leftIndent=10, rightIndent=10,
        backColor=PANEL_BG, borderColor=ACCENT, borderWidth=0.6, borderPadding=10,
        spaceBefore=6, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        name="Warning",
        fontName="Helvetica",
        fontSize=10, leading=14, textColor=TEXT,
        leftIndent=10, rightIndent=10,
        backColor=PANEL_BG, borderColor=WARN, borderWidth=0.6, borderPadding=10,
        spaceBefore=6, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        name="Tip",
        fontName="Helvetica",
        fontSize=10, leading=14, textColor=TEXT,
        leftIndent=10, rightIndent=10,
        backColor=PANEL_BG, borderColor=INFO, borderWidth=0.6, borderPadding=10,
        spaceBefore=6, spaceAfter=8,
    ))
    # Buzzword gloss — a smaller, indented note that follows a term.
    ss.add(ParagraphStyle(
        name="Buzz",
        fontName="Helvetica-Oblique",
        fontSize=9.5, leading=13, textColor=TERM,
        leftIndent=14, rightIndent=14,
        spaceBefore=2, spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        name="Caption",
        fontName="Helvetica-Oblique",
        fontSize=9, leading=12, textColor=MUTED,
        alignment=TA_CENTER, spaceBefore=2, spaceAfter=10,
    ))
    return ss
