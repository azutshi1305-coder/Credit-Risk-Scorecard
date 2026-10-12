"""PDF credit assessment report — 'underwriter's desk' theme, in full colour.

Page 1 is the decision at a glance: a tinted hero panel with the applicant's
name, the decision stamp and a score dial; three colour-coded figure tiles;
colour-coded cards for what drove the score and for the policy checks.
Page 2 shows how the score was built (coloured bars and a score equation),
followed by the full credit memo rendered as real PDF typography.

Fonts (Lora, Public Sans) are embedded from assets/fonts/.
"""
import math
import re

import markdown
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace, TextStyle

from ui.theme import COLORS, DIAL as THEME_DIAL
from ui import view_model as vm
from ui.components import ruler_segments

FONT_DIR = "assets/fonts"
AUTHOR = "Annapurna Zutshi"


def hex_to_rgb(hex_str: str):
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


INK = hex_to_rgb(COLORS["ink"])
MUTED = hex_to_rgb(COLORS["muted"])
LEDGER = hex_to_rgb(COLORS["ledger"])
BRASS = hex_to_rgb(COLORS["brass"])
RULE = hex_to_rgb(COLORS["rule"])
WHITE = (255, 255, 255)
PAPER = hex_to_rgb(COLORS["paper"])
CARD = hex_to_rgb("#F6F9F9")
LEDGER_TINT = hex_to_rgb(COLORS["teal_tint"])
BRASS_TINT = hex_to_rgb("#F7EDD8")
TOPBAR_SUB = hex_to_rgb(COLORS["top_bar_sub"])

TONE = {
    "approve": (hex_to_rgb(COLORS["approve"]), hex_to_rgb(COLORS["approve_tint"])),
    "caution": (hex_to_rgb(COLORS["caution"]), hex_to_rgb(COLORS["caution_tint"])),
    "decline": (hex_to_rgb(COLORS["decline"]), hex_to_rgb(COLORS["decline_tint"])),
}

# Score dial, E (left, higher risk) -> A (right, lower risk) — shared with the app.
DIAL = {k: hex_to_rgb(v) for k, v in THEME_DIAL.items()}


def status_tone(fraction: float) -> str:
    """How well the applicant did on one characteristic, as a colour tone."""
    if fraction >= 0.85:
        return "approve"
    if fraction >= 0.5:
        return "caution"
    return "decline"


def _strip_formatting_in_table_cells(html: str) -> str:
    """fpdf2's write_html can't nest inline tags inside <td>/<th>; keep the text only."""
    def clean_cell(m):
        inner = re.sub(r"</?(em|i|b|strong)>", "", m.group(2))
        return m.group(1) + inner + m.group(3)
    return re.sub(r"(<t[dh][^>]*>)(.*?)(</t[dh]>)", clean_cell, html, flags=re.DOTALL)


class ReportPDF(FPDF):
    def __init__(self, reference: str):
        super().__init__(format="A4", unit="mm")
        self.reference = reference
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(16, 16, 16)
        self.add_font("Lora", "", f"{FONT_DIR}/Lora-Regular.ttf")
        self.add_font("Lora", "B", f"{FONT_DIR}/Lora-SemiBold.ttf")
        self.add_font("Lora", "I", f"{FONT_DIR}/Lora-Italic.ttf")
        self.add_font("PublicSans", "", f"{FONT_DIR}/PublicSans-Regular.ttf")
        self.add_font("PublicSans", "B", f"{FONT_DIR}/PublicSans-SemiBold.ttf")
        self.alias_nb_pages()
        self.set_font("PublicSans", "", 10)

    def header(self):
        if self.page_no() == 1:
            return
        # slim running header on continuation pages
        self.set_fill_color(*LEDGER)
        self.rect(0, 0, self.w, 11, style="F")
        self.set_fill_color(*BRASS)
        self.rect(0, 11, self.w, 0.8, style="F")
        self.set_xy(self.l_margin, 3.2)
        self.set_font("Lora", "B", 9.5)
        self.set_text_color(*WHITE)
        self.cell(60, 5, "Sample Bank")
        self.set_font("PublicSans", "", 8)
        self.set_text_color(*TOPBAR_SUB)
        self.set_xy(self.w - self.r_margin - 90, 3.2)
        self.cell(90, 5, f"Credit assessment report  ·  {self.reference}", align="R")
        self.set_y(20)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_y(-12)
        self.set_font("PublicSans", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"Sample Bank  ·  Retail credit  ·  Confidential — for internal credit use"
                        f"  ·  Page {self.page_no()} of {{nb}}", align="C")


# ----------------------------------------------------------------- drawing helpers
def rounded(pdf, x, y, w, h, fill, radius=3, border=None):
    pdf.set_fill_color(*fill)
    if border:
        pdf.set_draw_color(*border)
        pdf.set_line_width(0.3)
    pdf.rect(x, y, w, h, style="DF" if border else "F", round_corners=True, corner_radius=radius)


def chip(pdf, x, y, text, fill, color, border=None, size=8.5, bold=True):
    pdf.set_font("PublicSans", "B" if bold else "", size)
    w = pdf.get_string_width(text) + 7
    rounded(pdf, x, y, w, 6.4, fill, radius=3.2, border=border)
    pdf.set_text_color(*color)
    pdf.set_xy(x, y)
    pdf.cell(w, 6.4, text, align="C")
    return w


def bar(pdf, x, y, w, h, fraction, color, track=RULE):
    rounded(pdf, x, y, w, h, track, radius=h / 2)
    fw = max(0.0, min(1.0, fraction)) * w
    if fw >= h:
        rounded(pdf, x, y, fw, h, color, radius=h / 2)
    elif fw > 0:
        pdf.set_fill_color(*color)
        pdf.rect(x, y, fw, h, style="F")


def draw_stamp(pdf, text, tone, cx, cy, size=14):
    color, tint = TONE[tone]
    pdf.set_font("Lora", "B", size)
    tw = pdf.get_string_width(text)
    box_w, box_h = tw + 12, size * 0.85 + 4
    x, y = cx - box_w / 2, cy - box_h / 2
    with pdf.rotation(-7, x=cx, y=cy):
        pdf.set_fill_color(*WHITE)
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.7)
        pdf.rect(x, y, box_w, box_h, style="FD", round_corners=True, corner_radius=1.5)
        pdf.set_line_width(0.3)
        pdf.rect(x + 1.2, y + 1.2, box_w - 2.4, box_h - 2.4, style="D", round_corners=True, corner_radius=1)
        pdf.set_text_color(*color)
        pdf.set_xy(x, y)
        pdf.cell(box_w, box_h, text, align="C")


def draw_dial(pdf, cx, cy, r_out, r_in, score, band, cutoffs, hub_fill):
    """Half-donut gauge: five coloured band arcs (E→A, left→right), needle at the score."""
    segments, marker = ruler_segments(score, cutoffs)
    angle = 180.0
    for letter, frac, _ in segments:
        sweep = frac * 180.0
        pdf.set_fill_color(*DIAL[letter])
        # fpdf2 measures arc angles clockwise on the page (y grows downward),
        # so the upper half of the dial lies between -180 and 0 degrees.
        pdf.solid_arc(cx - r_out, cy - r_out, 2 * r_out, -angle, -(angle - sweep), style="F")  # size = diameter
        # band letter on the arc
        mid = math.radians(angle - sweep / 2)
        lr = (r_out + r_in) / 2
        pdf.set_font("PublicSans", "B", 7.5 if letter != band else 8.5)
        pdf.set_text_color(*WHITE)
        pdf.set_xy(cx + lr * math.cos(mid) - 3, cy - lr * math.sin(mid) - 2.5)
        pdf.cell(6, 5, letter, align="C")
        angle -= sweep
    # inner cut-out
    pdf.set_fill_color(*hub_fill)
    pdf.solid_arc(cx - r_in, cy - r_in, 2 * r_in, -180, 0, style="F")
    pdf.rect(cx - r_out - 0.5, cy, 2 * r_out + 1, 0.6, style="F")
    # needle
    theta = math.radians(180.0 - max(0.0, min(1.0, marker)) * 180.0)
    tip = (cx + (r_out + 1.5) * math.cos(theta), cy - (r_out + 1.5) * math.sin(theta))
    pdf.set_draw_color(*INK)
    pdf.set_line_width(1.1)
    pdf.line(cx, cy, *tip)
    pdf.set_fill_color(*INK)
    pdf.ellipse(cx - 2.2, cy - 2.2, 4.4, 4.4, style="F")
    pdf.set_fill_color(*BRASS)
    pdf.ellipse(cx - 1, cy - 1, 2, 2, style="F")
    # score
    pdf.set_font("Lora", "B", 22)
    pdf.set_text_color(*INK)
    pdf.set_xy(cx - 20, cy + 3)
    pdf.cell(40, 9, f"{score:.0f}", align="C")
    pdf.set_font("PublicSans", "", 7.5)
    pdf.set_text_color(*MUTED)
    pdf.set_xy(cx - 25, cy + 12)
    pdf.cell(50, 4, "scorecard points", align="C")


def section_title(pdf, text, x=None, y=None, size=12.5):
    if x is not None:
        pdf.set_xy(x, y)
    sx, sy = pdf.get_x(), pdf.get_y()
    pdf.set_fill_color(*BRASS)
    pdf.rect(sx, sy + 1.2, 1.4, 5.2, style="F")
    pdf.set_xy(sx + 3.5, sy)
    pdf.set_font("Lora", "B", size)
    pdf.set_text_color(*INK)
    pdf.cell(0, 7.5, text)
    pdf.set_xy(sx, sy + 10)


# ----------------------------------------------------------------- the report
def build_pdf_report(assessment: dict) -> bytes:
    decision = assessment["decision"]
    final = decision["final_decision"]
    tone = vm.DECISION_CLASS.get(final, "caution")
    tone_rgb, tone_tint = TONE[tone]
    stamp_text = vm.STAMP_TEXT.get(final, final.upper())
    rows = assessment["characteristic_rows"]
    top_rows = vm.top_characteristics(rows, tone, n=3)
    notes = vm.policy_check_notes(decision["rule_details"])
    _, _, cutoffs = assessment["score_range_cutoffs"]
    score = float(decision["score"])

    pdf = ReportPDF(assessment["reference"])
    pdf.add_page()
    W = pdf.w - pdf.l_margin - pdf.r_margin
    L = pdf.l_margin

    # ---------------- header band ----------------
    pdf.set_fill_color(*LEDGER)
    pdf.rect(0, 0, pdf.w, 30, style="F")
    pdf.set_fill_color(*BRASS)
    pdf.rect(0, 30, pdf.w, 1.4, style="F")
    pdf.set_xy(L, 8.5)
    pdf.set_font("Lora", "B", 18)
    pdf.set_text_color(*WHITE)
    pdf.cell(100, 8, "Sample Bank")
    pdf.set_xy(L, 17)
    pdf.set_font("PublicSans", "", 9.5)
    pdf.set_text_color(*TOPBAR_SUB)
    pdf.cell(100, 5, "Credit assessment report")
    pdf.set_font("PublicSans", "B", 9)
    pdf.set_text_color(*WHITE)
    pdf.set_xy(pdf.w - pdf.r_margin - 90, 9.5)
    pdf.cell(90, 5, f"Application {assessment['reference']}", align="R")
    pdf.set_font("PublicSans", "", 8.5)
    pdf.set_text_color(*TOPBAR_SUB)
    pdf.set_xy(pdf.w - pdf.r_margin - 90, 15.5)
    pdf.cell(90, 5, f"Assessed {assessment['generated_at']}", align="R")

    # ---------------- hero panel ----------------
    hy, hh = 39, 76
    rounded(pdf, L, hy, W, hh, tone_tint, radius=4)
    pdf.set_fill_color(*tone_rgb)
    pdf.rect(L, hy + 4, 1.8, hh - 8, style="F")

    left_w = W * 0.56
    pdf.set_xy(L + 8, hy + 7)
    pdf.set_font("PublicSans", "", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(left_w, 4, "Applicant")
    pdf.set_xy(L + 8, hy + 12)
    pdf.set_font("Lora", "B", 23)
    pdf.set_text_color(*INK)
    pdf.cell(left_w - 8, 11, assessment["applicant_name"])
    pdf.set_xy(L + 8, hy + 25)
    pdf.set_font("PublicSans", "", 9.5)
    pdf.multi_cell(left_w - 12, 5, vm.NEXT_STEP.get(final, ""))

    cx = L + 8
    cy = hy + 40
    cx += chip(pdf, cx, cy, f"Band {decision['band']}", tone_rgb, WHITE) + 2.5
    cx += chip(pdf, cx, cy, f"Default risk {vm.PD_RANGE_TEXT.get(decision['band'], '')}",
               WHITE, tone_rgb, border=tone_rgb) + 2.5
    n_rules = len(notes)
    chip(pdf, cx, cy, "No policy flags" if n_rules == 0 else f"{n_rules} policy flag{'s' if n_rules > 1 else ''}",
         WHITE, hex_to_rgb(COLORS["caution"]) if n_rules else hex_to_rgb(COLORS["approve"]),
         border=hex_to_rgb(COLORS["caution"]) if n_rules else hex_to_rgb(COLORS["approve"]))

    long_stamp = len(stamp_text) > 14
    draw_stamp(pdf, stamp_text, tone, cx=L + 8 + (34 if not long_stamp else 50), cy=hy + 60,
               size=15 if not long_stamp else 12)

    draw_dial(pdf, cx=L + left_w + (W - left_w) / 2, cy=hy + 44, r_out=30, r_in=19,
              score=score, band=decision["band"], cutoffs=cutoffs, hub_fill=tone_tint)

    # ---------------- figure tiles ----------------
    ty, th = hy + hh + 7, 25
    gap = 4
    tw = (W - 2 * gap) / 3
    tiles = [
        ("Score", f"{score:.0f}", "600 points = 50:1 odds of repaying", LEDGER, WHITE, TOPBAR_SUB),
        ("Risk band", decision["band"], f"Band decision: {decision['band_decision']}", tone_rgb, WHITE,
         (245, 245, 245)),
        ("Estimated default risk", vm.PD_RANGE_TEXT.get(decision["band"], ""), "Chance of serious late payment",
         BRASS_TINT, INK, MUTED),
    ]
    for i, (label, value, sub, fill, fg, sub_fg) in enumerate(tiles):
        x = L + i * (tw + gap)
        rounded(pdf, x, ty, tw, th, fill, radius=3)
        pdf.set_xy(x + 5, ty + 3.5)
        pdf.set_font("PublicSans", "", 8)
        pdf.set_text_color(*sub_fg)
        pdf.cell(tw - 10, 4, label)
        pdf.set_xy(x + 5, ty + 8.5)
        pdf.set_font("Lora", "B", 17 if i < 2 else 14)
        pdf.set_text_color(*fg)
        pdf.cell(tw - 10, 8, value)
        pdf.set_xy(x + 5, ty + 18)
        pdf.set_font("PublicSans", "", 7.2)
        pdf.set_text_color(*sub_fg)
        pdf.cell(tw - 10, 4, sub)

    # ---------------- drivers + policy checks ----------------
    col_y = ty + th + 9
    col_w = (W - 6) / 2
    title = "What helped" if tone == "approve" else "What held the score back"
    section_title(pdf, title, L, col_y)
    y = col_y + 10
    for r in top_rows:
        st = status_tone(r["bar_fraction"])
        st_rgb, st_tint = TONE[st]
        rounded(pdf, L, y, col_w, 19, CARD, radius=2.5)
        pdf.set_fill_color(*st_rgb)
        pdf.rect(L, y + 2.5, 1.6, 14, style="F")
        pdf.set_xy(L + 5, y + 2.5)
        pdf.set_font("PublicSans", "B", 9)
        pdf.set_text_color(*INK)
        pdf.cell(col_w - 30, 5, r["name"])
        pdf.set_xy(L + col_w - 27, y + 2.5)
        pdf.set_font("PublicSans", "B", 8)
        pdf.set_text_color(*st_rgb)
        pdf.cell(23, 5, f"{r['points_earned']} / {r['best_possible']} pts", align="R")
        pdf.set_xy(L + 5, y + 7.5)
        pdf.set_font("PublicSans", "", 8.2)
        pdf.set_text_color(*MUTED)
        pdf.cell(col_w - 10, 4.5, r["value_text"])
        bar(pdf, L + 5, y + 13.5, col_w - 10, 2.2, r["bar_fraction"], st_rgb)
        y += 22
    left_bottom = y

    rx = L + col_w + 6
    section_title(pdf, "Policy checks", rx, col_y)
    y = col_y + 10
    if not notes:
        ap, ap_tint = TONE["approve"]
        rounded(pdf, rx, y, col_w, 19, ap_tint, radius=2.5)
        pdf.set_fill_color(*ap)
        pdf.ellipse(rx + 5, y + 5.5, 8, 8, style="F")
        pdf.set_draw_color(*WHITE)
        pdf.set_line_width(0.8)
        pdf.line(rx + 6.9, y + 9.6, rx + 8.5, y + 11.2)
        pdf.line(rx + 8.5, y + 11.2, rx + 11.3, y + 7.8)
        pdf.set_xy(rx + 16, y + 4)
        pdf.set_font("PublicSans", "B", 9.5)
        pdf.set_text_color(*ap)
        pdf.cell(col_w - 20, 5, "All policy checks passed")
        pdf.set_xy(rx + 16, y + 9.5)
        pdf.set_font("PublicSans", "", 8.2)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(col_w - 20, 4.2, "No hard rule overrides the scorecard decision.")
        y += 22
    else:
        ca, ca_tint = TONE["caution"]
        for rule_id, text in notes:
            pdf.set_font("PublicSans", "", 8.2)
            lines = pdf.multi_cell(col_w - 22, 4.2, text, dry_run=True, output="LINES")
            h = max(14, len(lines) * 4.2 + 7)
            rounded(pdf, rx, y, col_w, h, ca_tint, radius=2.5)
            chip(pdf, rx + 3.5, y + 3.2, rule_id, ca, WHITE, size=8)
            pdf.set_xy(rx + 18, y + 3.5)
            pdf.set_text_color(*INK)
            pdf.set_font("PublicSans", "", 8.2)
            pdf.multi_cell(col_w - 22, 4.2, text)
            y += h + 3
    pdf.set_y(max(left_bottom, y) + 2)

    # ================= page 2: how the score was built =================
    pdf.add_page()
    section_title(pdf, "How the score was built", L, pdf.get_y(), size=14)
    pdf.set_font("PublicSans", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.set_x(L)
    pdf.multi_cell(W, 4.8, "Every application starts from the same base points. Each characteristic then adds "
                           "points — the fuller the bar, the closer the applicant came to the best possible result.")
    pdf.ln(4)

    for r in rows:
        st_rgb, _ = TONE[status_tone(r["bar_fraction"])]
        y = pdf.get_y()
        rounded(pdf, L, y, W, 13, CARD, radius=2.5)
        pdf.set_xy(L + 4, y + 2.2)
        pdf.set_font("PublicSans", "B", 9)
        pdf.set_text_color(*INK)
        pdf.cell(62, 4.5, r["name"])
        pdf.set_xy(L + 4, y + 6.8)
        pdf.set_font("PublicSans", "", 7.8)
        pdf.set_text_color(*MUTED)
        pdf.cell(62, 4, r["value_text"])
        bar(pdf, L + 70, y + 5.2, W - 70 - 30, 2.8, r["bar_fraction"], st_rgb)
        pdf.set_xy(L + W - 28, y + 3.8)
        pdf.set_font("PublicSans", "B", 9.5)
        pdf.set_text_color(*st_rgb)
        pdf.cell(24, 5, f"{r['points_earned']} / {r['best_possible']}", align="R")
        pdf.set_y(y + 15)

    # legend
    pdf.ln(1)
    lx = L
    for tone_key, label in (("approve", "Strong"), ("caution", "Middling"), ("decline", "Weak")):
        c, _ = TONE[tone_key]
        pdf.set_fill_color(*c)
        pdf.ellipse(lx, pdf.get_y() + 1.2, 2.6, 2.6, style="F")
        pdf.set_xy(lx + 3.8, pdf.get_y())
        pdf.set_font("PublicSans", "", 7.8)
        pdf.set_text_color(*MUTED)
        pdf.cell(20, 5, label)
        lx += 24
    pdf.ln(9)

    # score equation: base + each characteristic = score
    pdf.set_x(L)
    pdf.set_font("PublicSans", "B", 9)
    pdf.set_text_color(*INK)
    pdf.cell(0, 5, "The score, added up", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    x, y = L, pdf.get_y()
    parts = [("Base", assessment["base_points"], LEDGER_TINT, LEDGER)]
    for r in rows:
        pts = r["points_earned"]
        good = status_tone(r["bar_fraction"])
        parts.append((r["name"], pts, TONE[good][1], TONE[good][0]))
    for i, (label, pts, fill, fg) in enumerate(parts):
        text = f"{label}  {pts:+d}" if i else f"{label}  {pts}"
        pdf.set_font("PublicSans", "B", 8)
        w = pdf.get_string_width(text) + 7
        if x + w + 8 > L + W:
            x, y = L, y + 9
        if i:
            pdf.set_xy(x, y)
            pdf.set_text_color(*MUTED)
            pdf.cell(4, 6.4, "+", align="C")
            x += 5
        chip(pdf, x, y, text, fill, fg)
        x += w + 1.5
    pdf.set_font("PublicSans", "B", 9)
    if x + 40 > L + W:
        x, y = L, y + 9
    pdf.set_xy(x, y)
    pdf.set_text_color(*MUTED)
    pdf.cell(5, 6.4, "=", align="C")
    chip(pdf, x + 6, y, f"Score  {score:.0f}", tone_rgb, WHITE, size=9)
    pdf.set_y(y + 16)

    # ================= credit memo =================
    if pdf.get_y() > pdf.h - 80:
        pdf.add_page()
    section_title(pdf, "Credit memo", L, pdf.get_y(), size=14)
    chip(pdf, L, pdf.get_y() - 1, assessment["memo_mode"], BRASS_TINT, hex_to_rgb("#7A5A1C"), size=7.8, bold=False)
    pdf.ln(9)

    memo_md = re.sub(r"\A\s*#\s+[^\n]*\n", "", assessment["memo"])  # the page already titles it
    memo_html = markdown.markdown(memo_md, extensions=["tables"])
    memo_html = _strip_formatting_in_table_cells(memo_html)
    memo_html = re.sub(r"<(p|ul|ol)>", r'<\1 style="line-height:1.5">', memo_html)
    pdf.set_font("Lora", "", 10)
    pdf.set_text_color(*INK)
    pdf.set_fill_color(*LEDGER_TINT)
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.2)
    pdf.write_html(
        memo_html,
        table_line_separators=True,
        li_prefix_color=BRASS,
        tag_styles={
            "h1": TextStyle(font_family="Lora", font_style="B", font_size_pt=13, color=LEDGER, t_margin=5, b_margin=2),
            "h2": TextStyle(font_family="Lora", font_style="B", font_size_pt=12, color=LEDGER, t_margin=5, b_margin=1.5),
            "h3": TextStyle(font_family="Lora", font_style="B", font_size_pt=11, color=LEDGER, t_margin=4, b_margin=1),
            "p": TextStyle(font_family="Lora", font_size_pt=10, color=INK, t_margin=0, b_margin=2.5),
            "li": FontFace(family="Lora", size_pt=10, color=INK),
            "b": FontFace(family="Lora", emphasis="BOLD", color=INK),
            "strong": FontFace(family="Lora", emphasis="BOLD", color=INK),
            "i": FontFace(family="Lora", emphasis="ITALICS", color=INK),
            "em": FontFace(family="Lora", emphasis="ITALICS", color=INK),
        },
    )

    # ---------------- about this model ----------------
    pdf.ln(6)
    note = (f"Champion model: a logistic-regression scorecard on Weight-of-Evidence variables. "
            f"On held-out test data it scores Gini {assessment['gini']:.3f}, AUC {assessment['auc']:.3f} and "
            f"KS {assessment['ks']:.3f}. Age and number of dependents are deliberately left out for fair lending — "
            f"age is a protected characteristic under US ECOA and dependents act as a proxy for family status. "
            f"Leaving them out cost about 0.7% of the scorecard's Gini.")
    pdf.set_font("PublicSans", "", 8.5)
    lines = pdf.multi_cell(W - 14, 4.5, note, dry_run=True, output="LINES")
    h = len(lines) * 4.5 + 15
    if pdf.get_y() + h > pdf.h - 24:
        pdf.add_page()
    y = pdf.get_y()
    rounded(pdf, L, y, W, h, LEDGER_TINT, radius=3)
    pdf.set_xy(L + 7, y + 4)
    pdf.set_font("Lora", "B", 10.5)
    pdf.set_text_color(*LEDGER)
    pdf.cell(0, 5, "About this model")
    pdf.set_xy(L + 7, y + 10.5)
    pdf.set_font("PublicSans", "", 8.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(W - 14, 4.5, note)

    return bytes(pdf.output())
