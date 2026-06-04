"""Dark-theme styling for the DebateIQ handbook PDF.

Colors picked to mimic a developer's editor (GitHub Dark / Monokai blend) so
code blocks, callouts, and diagrams feel cohesive. All hex values live here
so the rest of the build script can stay declarative.
"""

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import mm

# ---------------------------------------------------------------- palette
PAGE_BG       = colors.HexColor("#0d1117")  # github dark
PANEL_BG      = colors.HexColor("#161b22")
SOFT_BG       = colors.HexColor("#1f242c")
BORDER        = colors.HexColor("#30363d")
TEXT          = colors.HexColor("#e6edf3")
MUTED         = colors.HexColor("#8b949e")
ACCENT        = colors.HexColor("#7ee8fa")   # chapter cyan
ACCENT_2      = colors.HexColor("#f0c674")   # section gold
ACCENT_3      = colors.HexColor("#a5e075")   # callouts green
WARN          = colors.HexColor("#ff7b72")   # red for bugs / dangers
INFO          = colors.HexColor("#79c0ff")   # blue for tips
CODE_BG       = colors.HexColor("#0f141a")
CODE_KEYWORD  = colors.HexColor("#ff7b72")
CODE_STRING   = colors.HexColor("#a5e075")
CODE_COMMENT  = colors.HexColor("#8b949e")
LINK          = colors.HexColor("#58a6ff")

# Page geometry
PAGE_W, PAGE_H = (170 * mm, 235 * mm)   # custom — slightly slimmer than A4
LEFT, RIGHT, TOP, BOTTOM = 18 * mm, 18 * mm, 22 * mm, 22 * mm


# ---------------------------------------------------------------- styles
def build_styles() -> StyleSheet1:
    ss = StyleSheet1()

    ss.add(ParagraphStyle(
        name="CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=34, leading=40, textColor=ACCENT,
        alignment=TA_CENTER, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        name="CoverSubtitle",
        fontName="Helvetica",
        fontSize=14, leading=20, textColor=TEXT,
        alignment=TA_CENTER, spaceAfter=4,
    ))
    ss.add(ParagraphStyle(
        name="CoverMuted",
        fontName="Helvetica",
        fontSize=10, leading=14, textColor=MUTED,
        alignment=TA_CENTER,
    ))
    ss.add(ParagraphStyle(
        name="ChapterNumber",
        fontName="Helvetica",
        fontSize=10, leading=14, textColor=MUTED,
        alignment=TA_LEFT, spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        name="ChapterTitle",
        fontName="Helvetica-Bold",
        fontSize=26, leading=30, textColor=ACCENT,
        alignment=TA_LEFT, spaceAfter=12,
    ))
    ss.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=16, leading=20, textColor=ACCENT_2,
        spaceBefore=14, spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        name="SubSection",
        fontName="Helvetica-Bold",
        fontSize=12, leading=16, textColor=ACCENT_3,
        spaceBefore=8, spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        name="Body",
        fontName="Helvetica",
        fontSize=10.5, leading=15.5, textColor=TEXT,
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
        leftIndent=14, bulletIndent=2, spaceAfter=2, alignment=TA_LEFT,
    ))
    ss.add(ParagraphStyle(
        name="Code",
        fontName="Courier",
        fontSize=9, leading=12, textColor=TEXT,
        leftIndent=10, rightIndent=10,
        backColor=CODE_BG, borderColor=BORDER, borderWidth=0.5, borderPadding=8,
        spaceBefore=4, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        name="Callout",
        fontName="Helvetica",
        fontSize=10, leading=14, textColor=TEXT,
        leftIndent=10, rightIndent=10,
        backColor=PANEL_BG, borderColor=ACCENT, borderWidth=0.6, borderPadding=8,
        spaceBefore=6, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        name="Warning",
        fontName="Helvetica",
        fontSize=10, leading=14, textColor=TEXT,
        leftIndent=10, rightIndent=10,
        backColor=PANEL_BG, borderColor=WARN, borderWidth=0.6, borderPadding=8,
        spaceBefore=6, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        name="Tip",
        fontName="Helvetica",
        fontSize=10, leading=14, textColor=TEXT,
        leftIndent=10, rightIndent=10,
        backColor=PANEL_BG, borderColor=INFO, borderWidth=0.6, borderPadding=8,
        spaceBefore=6, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        name="Caption",
        fontName="Helvetica-Oblique",
        fontSize=9, leading=12, textColor=MUTED,
        alignment=TA_CENTER, spaceBefore=2, spaceAfter=10,
    ))
    ss.add(ParagraphStyle(
        name="TOCEntry",
        fontName="Helvetica",
        fontSize=11, leading=16, textColor=TEXT,
        spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        name="TOCNumber",
        fontName="Helvetica-Bold",
        fontSize=11, leading=16, textColor=ACCENT,
    ))
    return ss
