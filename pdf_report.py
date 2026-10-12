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
        # softer, rounder face for the credit memo body text
        self.add_font("Nunito", "", f"{FONT_DIR}/NunitoSans-Regular.ttf")
        self.add_font("Nunito", "B", f"{FONT_DIR}/NunitoSans-SemiBold.ttf")
        self.add_font("Nunito", "I", f"{FONT_DIR}/NunitoSans-Italic.ttf")
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
        self.cell(90, 5, "Credit Assessment Report")
        self.set_font("PublicSans", "", 8)
        self.set_text_color(*TOPBAR_SUB)
        self.set_xy(self.w - self.r_margin - 90, 3.2)
        self.cell(90, 5, f"Application {self.reference}", align="R")
        self.set_y(20)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_y(-12)
        self.set_font("PublicSans", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"Retail credit  ·  Confidential — for internal credit use"
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


# ----------------------------------------------------------------- memo typography
MEMO_INK = hex_to_rgb("#3B4D51")   # a touch lighter than the main ink, easier on the eye

MEMO_TAG_STYLES = {
    "h1": TextStyle(font_family="Lora", font_style="B", font_size_pt=13, color=LEDGER, t_margin=4, b_margin=0),
    "h2": TextStyle(font_family="Lora", font_style="B", font_size_pt=12, color=LEDGER, t_margin=4, b_margin=0),
    "h3": TextStyle(font_family="Lora", font_style="B", font_size_pt=11, color=LEDGER, t_margin=3, b_margin=0),
    "p": TextStyle(font_family="Nunito", font_size_pt=10, color=MEMO_INK, t_margin=1.2, b_margin=1.2),
    "ul": TextStyle(t_margin=1, b_margin=1),
    "ol": TextStyle(t_margin=1, b_margin=1),
    "li": TextStyle(font_family="Nunito", font_size_pt=10, color=MEMO_INK, l_margin=5, t_margin=0.6),
    "b": FontFace(family="Nunito", emphasis="BOLD", color=INK),
    "strong": FontFace(family="Nunito", emphasis="BOLD", color=INK),
    "i": FontFace(family="Nunito", emphasis="ITALICS", color=MEMO_INK),
    "em": FontFace(family="Nunito", emphasis="ITALICS", color=MEMO_INK),
}


def _memo_html(md: str) -> str:
    html = markdown.markdown(md, extensions=["tables"])
    html = _strip_formatting_in_table_cells(html)
    html = re.sub(r">\s*\n\s*<", "><", html)   # stray newlines between tags render as blank lines
    return re.sub(r"<(p|ul|ol)>", r'<\1 style="line-height:1.55">', html)


def _write_memo_html(pdf, html: str):
    pdf.set_font("Nunito", "", 10)
    pdf.set_text_color(*MEMO_INK)
    pdf.set_fill_color(*LEDGER_TINT)
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.2)
    pdf.write_html(html, table_line_separators=True, li_prefix_color=BRASS, tag_styles=MEMO_TAG_STYLES)


def _measure(html: str, reference: str) -> float:
    """Height (mm) a block of memo HTML takes, measured on a scratch page."""
    scratch = ReportPDF(reference)
    scratch.add_page()
    scratch.set_y(40)
    _write_memo_html(scratch, html)
    if scratch.page > 1:
        return float("inf")
    return scratch.get_y() - 40


def render_memo(pdf, memo_md: str, reference: str):
    """Writes the memo section by section; a section that won't fit on the current
    page starts on the next one, so a heading is never separated from its content."""
    parts = re.split(r"(?m)^(?=#{1,3}\s)", memo_md.strip())
    for part in parts:
        if not part.strip():
            continue
        html = _memo_html(part)
        needed = _measure(html, reference)
        room = pdf.page_break_trigger - pdf.get_y()
        if needed > room and needed != float("inf"):
            pdf.add_page()
        elif needed == float("inf") and room < 60:
            pdf.add_page()   # very long section: at least start it near the top of a page
        _write_memo_html(pdf, html)


# ----------------------------------------------------------------- business view
def _pct(x, digits=1):
    return "–" if x is None or x != x else f"{x * 100:.{digits}f}%"


def _table_header(pdf, cols, y):
    """cols: list of (title, width, align). Draws a muted header row with a rule under it."""
    L = pdf.l_margin
    pdf.set_font("PublicSans", "B", 7.4)
    pdf.set_text_color(*MUTED)
    x = L
    for title, w, align in cols:
        pdf.set_xy(x + 1.5, y)
        pdf.multi_cell(w - 3, 3.6, title, align=align)
        x += w
    pdf.set_font("PublicSans", "B", 7.4)
    n_lines = max(len(pdf.multi_cell(w - 3, 3.6, t, dry_run=True, output="LINES")) for t, w, _ in cols)
    y_end = y + n_lines * 3.6 + 1.2
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.3)
    pdf.line(L, y_end, L + sum(c[1] for c in cols), y_end)
    return y_end


def render_business_page(pdf, assessment):
    eco = assessment.get("economics")
    if not eco:
        return
    L, W = pdf.l_margin, pdf.w - pdf.l_margin - pdf.r_margin
    band = assessment["decision"]["band"]
    per = eco["per_amount"]
    lgd = eco["lgd"]
    bands = {r["band"]: r for r in eco["bands"]}
    cuts = eco["cutoffs"]

    pdf.add_page()
    pdf.set_y(pdf.get_y() + 2)
    section_title(pdf, "Choosing the cut-off", L, pdf.get_y(), size=14)
    pdf.set_xy(L, pdf.get_y() + 1)
    pdf.set_font("Nunito", "", 9.2)
    pdf.set_text_color(*MEMO_INK)
    pdf.multi_cell(W, 4.8,
        f"Where the bank draws the approval line decides how much business it writes and how much it "
        f"loses. These figures come from {eco['n_test']:,} past applicants the model never saw while it was "
        f"built; {_pct(eco['portfolio_bad_rate'])} of them went on to default.", align="L")

    # --- this applicant callout ---
    me = bands.get(band)
    loan = assessment.get("loan")
    if me:
        y = pdf.get_y() + 4
        box_h = 23 if loan else 17
        rounded(pdf, L, y, W, box_h, LEDGER_TINT, radius=3)
        rounded(pdf, L + 5, y + 4.2, 9, 9, DIAL[band], radius=2.5)
        pdf.set_xy(L + 5, y + 4.2)
        pdf.set_font("Lora", "B", 12)
        pdf.set_text_color(*WHITE)
        pdf.cell(9, 9, band, align="C")
        pdf.set_xy(L + 18, y + 3.4)
        pdf.set_font("Lora", "B", 10.5)
        pdf.set_text_color(*LEDGER)
        pdf.cell(0, 5, f"This applicant sits in band {band}: expected loss of about "
                       f"{me['el_per_1000']:.0f} for every {per:,} lent")
        pdf.set_xy(L + 18, y + 9.2)
        pdf.set_font("Nunito", "", 8.6)
        pdf.set_text_color(*MEMO_INK)
        pdf.cell(0, 4.5, f"Band {band} default rate {_pct(me['pd'])}  ×  {lgd:.0%} of the balance lost on default"
                         f"  ×  {per:,} lent  =  {me['el_per_1000']:.1f}")
        if loan:
            loss = me["pd"] * lgd * loan["amount"]
            line = (f"This loan of {loan['amount']:,.0f}: expected loss about {loss:,.0f}  ·  "
                    f"repayment {loan['emi']:,.0f} a month")
            if loan.get("post_loan_dti") is not None:
                line += f"  ·  {loan['post_loan_dti'] * 100:.0f}% of income on debt"
            pdf.set_xy(L + 18, y + 14.6)
            pdf.set_font("Nunito", "B", 8.4)
            pdf.set_text_color(*INK)
            pdf.multi_cell(W - 22, 4.3, line, align="L")
        pdf.set_y(y + box_h)

    # --- cut-off trade-off table ---
    pdf.set_y(pdf.get_y() + 7)
    pdf.set_font("Lora", "B", 11)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, "What each approval line would mean")
    cols = [("Approval policy", 50, "L"), ("Lowest score approved", 20, "R"), ("Share approved", 26, "L"),
            ("Default rate of approved", 22, "R"), ("Defaulters kept out", 20, "R"),
            ("Good applicants turned away", 22, "R"), (f"Expected loss per {per:,}", W - 160, "R")]
    y = _table_header(pdf, cols, pdf.get_y() + 7)
    row_h = 8.2
    for r in cuts:
        if r["current"]:
            pdf.set_fill_color(*LEDGER_TINT)
            pdf.rect(L, y, W, row_h, style="F")
        x = L
        cells = [
            r["policy"].replace(" (current policy)", ""),
            "no floor" if r["min_score"] is None or r["min_score"] != r["min_score"] else f"{r['min_score']:.0f}",
            None,
            _pct(r["bad_rate"]),
            _pct(r["bads_avoided"], 0),
            _pct(r["goods_declined"], 0),
            f"{r['el_per_1000']:.1f}",
        ]
        for (title, w, align), text in zip(cols, cells):
            if text is None:   # share approved: number + mini bar
                pdf.set_xy(x + 1.5, y + 1.9)
                pdf.set_font("PublicSans", "B" if r["current"] else "", 8.4)
                pdf.set_text_color(*INK)
                pdf.cell(11, 4.4, _pct(r["approval_rate"], 0))
                bar(pdf, x + 13, y + 3.3, w - 15, 1.8, r["approval_rate"], LEDGER)
            else:
                pdf.set_xy(x + 1.5, y + 1.9)
                pdf.set_font("PublicSans", "B" if r["current"] else "", 8.4)
                pdf.set_text_color(*(LEDGER if r["current"] and align == "L" else INK))
                pdf.cell(w - 3, 4.4, text, align=align)
            x += w
        if r["current"]:
            pdf.set_font("PublicSans", "B", 8.4)
            cx = L + 1.5 + pdf.get_string_width(cells[0]) + 2
            pdf.set_font("PublicSans", "B", 6.4)
            tw = pdf.get_string_width("CURRENT") + 3.6
            rounded(pdf, cx, y + 2.2, tw, 3.8, LEDGER, radius=1.9)
            pdf.set_text_color(*WHITE)
            pdf.set_xy(cx, y + 2.2)
            pdf.cell(tw, 3.8, "CURRENT", align="C")
        pdf.set_draw_color(*RULE)
        pdf.set_line_width(0.2)
        pdf.line(L, y + row_h, L + W, y + row_h)
        y += row_h

    # takeaway sentence, built from the numbers
    cur = next((r for r in cuts if r["current"]), None)
    tighter = next((r for r in cuts if r["lowest_band"] == "B"), None)
    looser = next((r for r in cuts if r["lowest_band"] == "D"), None)
    if cur and tighter and looser:
        text = (f"Tightening the line from band C to band B would cut the default rate of the approved book from "
                f"{_pct(cur['bad_rate'])} to {_pct(tighter['bad_rate'])}, but approve "
                f"{(cur['approval_rate'] - tighter['approval_rate']) * 100:.0f} fewer applicants in every 100. "
                f"Loosening it to band D would approve {(looser['approval_rate'] - cur['approval_rate']) * 100:.0f} "
                f"more in every 100 and raise the default rate to {_pct(looser['bad_rate'])}.")
        pdf.set_xy(L, y + 3)
        pdf.set_font("Nunito", "I", 8.8)
        pdf.set_text_color(*MEMO_INK)
        pdf.multi_cell(W, 4.6, text, align="L")
        y = pdf.get_y()

    # --- expected loss by band ---
    pdf.set_xy(L, y + 7)
    pdf.set_font("Lora", "B", 11)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, "Expected loss by risk band")
    cols2 = [("Band", 16, "L"), ("Standard decision", 46, "L"), ("Share of applicants", 26, "R"),
             ("Default rate", 24, "R"), (f"Expected loss per {per:,} lent", W - 112, "L")]
    y = _table_header(pdf, cols2, pdf.get_y() + 7)
    max_el = max((r["el_per_1000"] for r in eco["bands"] if r["el_per_1000"] == r["el_per_1000"]), default=1) or 1
    for r in eco["bands"]:
        mine = r["band"] == band
        if mine:
            pdf.set_fill_color(*LEDGER_TINT)
            pdf.rect(L, y, W, row_h, style="F")
        rounded(pdf, L + 1.5, y + 1.6, 7, 5, DIAL[r["band"]], radius=1.5)
        pdf.set_xy(L + 1.5, y + 1.6)
        pdf.set_font("PublicSans", "B", 8)
        pdf.set_text_color(*WHITE)
        pdf.cell(7, 5, r["band"], align="C")
        pdf.set_font("PublicSans", "B" if mine else "", 8.4)
        pdf.set_text_color(*INK)
        pdf.set_xy(L + 16 + 1.5, y + 1.9)
        pdf.cell(43, 4.4, r["decision"] + ("  ·  this applicant" if mine else ""))
        pdf.set_xy(L + 62 + 1.5, y + 1.9)
        pdf.cell(23, 4.4, _pct(r["share"]), align="R")
        pdf.set_xy(L + 88 + 1.5, y + 1.9)
        pdf.cell(21, 4.4, _pct(r["pd"]), align="R")
        el = r["el_per_1000"]
        if el == el:
            bx = L + 112 + 1.5
            bw = W - 112 - 18
            bar(pdf, bx, y + 3.2, bw, 2, el / max_el, DIAL[r["band"]])
            pdf.set_xy(bx + bw + 1, y + 1.9)
            pdf.cell(14, 4.4, f"{el:.1f}", align="R")
        pdf.set_draw_color(*RULE)
        pdf.set_line_width(0.2)
        pdf.line(L, y + row_h, L + W, y + row_h)
        y += row_h

    # --- assumptions ---
    note = (f"Expected loss = probability of default × loss given default × exposure at default. "
            f"Probability of default is each band's observed rate of going 90+ days past due within two years, "
            f"so these are two-year losses, not annual ones. Loss given default is assumed at {lgd:.0%} — a common "
            f"benchmark for unsecured consumer lending — and exposure is assumed to equal the amount lent. "
            f"Band D files go to an underwriter, so the true outcome of an A–D policy depends on how many "
            f"of them are approved after review.")
    pdf.set_font("Nunito", "", 8.2)
    lines = pdf.multi_cell(W - 14, 4.3, note, dry_run=True, output="LINES", align="L")
    h = len(lines) * 4.3 + 14
    y += 7
    if y + h > pdf.page_break_trigger:
        pdf.add_page()
        y = pdf.get_y()
    rounded(pdf, L, y, W, h, BRASS_TINT, radius=3)
    pdf.set_xy(L + 7, y + 3.6)
    pdf.set_font("Lora", "B", 9.8)
    pdf.set_text_color(*hex_to_rgb("#7A5A1C"))
    pdf.cell(0, 5, "How these figures are worked out")
    pdf.set_xy(L + 7, y + 9.6)
    pdf.set_font("Nunito", "", 8.2)
    pdf.set_text_color(*MEMO_INK)
    pdf.multi_cell(W - 14, 4.3, note, align="L")


# ----------------------------------------------------------------- glossary
GLOSSARY = [
    ("Credit utilisation",
     "How much of the available credit on cards and personal credit lines is being used.",
     "Total balances ÷ total credit limits × 100. Balances of 15,000 on limits of 50,000 = 30%. "
     "Mortgages and fixed loans are not included. Above 100% means accounts are over their limit."),
    ("Debt-to-income ratio",
     "The share of monthly income already committed to debt payments and other fixed obligations.",
     "Monthly debt payments ÷ gross monthly income × 100. Payments of 1,500 on income of 5,000 = 30%. "
     "Above 50% triggers an affordability check."),
    ("Monthly income",
     "Total income before tax from all sources — salary, business, rent received, pension.",
     "An annual salary of 60,000 = 5,000 a month."),
    ("Late payments",
     "How many times in the last two years a payment was overdue, counted in three ranges: "
     "30–59 days, 60–89 days and 90 days or more.",
     "Each occasion is counted once, in the most serious range it reached. 90+ days late is treated "
     "as serious delinquency."),
    ("Property loans",
     "Mortgages and other loans secured on property, including home-equity lines of credit.",
     "A count of open loans. In this scorecard, holding one or two earns more points than holding "
     "none, because it usually reflects an established credit history."),
    ("Monthly repayment",
     "The fixed amount repaid each month on the new loan, covering interest and part of the amount borrowed.",
     "Worked out from the loan amount, interest rate and repayment period. 15,000 over 36 months at "
     "11% a year is about 491 a month."),
    ("Scorecard points",
     "Each characteristic earns points; the score is base points plus the points from every "
     "characteristic. Higher means lower risk.",
     "The scale is set so that 600 points means odds of 50 good accounts to every 1 that defaults, "
     "and every extra 20 points doubles those odds."),
    ("Risk band",
     "The score grouped into five grades, A (lowest risk) to E (highest). Each band maps to a "
     "standard decision and an expected range of default rates.",
     None),
    ("Probability of default",
     "The chance the applicant falls 90 or more days behind on a payment within the next two years.",
     None),
    ("Reason codes",
     "The characteristics that cost the most points compared with the best possible answer. "
     "They explain the score and are used in any adverse-action notice.",
     None),
    ("Hard policy rules",
     "Checks that apply whatever the score: serious past delinquency, utilisation above 100%, "
     "debt-to-income above 50% (today, or once the new loan's repayment is added), or undeclared "
     "income send the file to an underwriter. Missing payment history sends it to manual review.",
     None),
    ("Gini, AUC and KS",
     "Standard measures of how well the model separates applicants who repay from those who "
     "default, measured on data the model never saw while it was built.",
     "AUC runs from 0.5 (no better than chance) to 1.0 (perfect); Gini = 2 × AUC − 1. KS is the "
     "largest gap between the score distributions of good and bad accounts."),
]


def _glossary_entry(pdf, term, meaning, how, dry=False):
    """Draws one glossary row (or just measures it when dry=True). Returns its height."""
    L, W = pdf.l_margin, pdf.w - pdf.l_margin - pdf.r_margin
    TERM_W, GAP = 46, 5
    text_w = W - TERM_W - GAP
    pdf.set_font("Nunito", "", 9)
    h1 = len(pdf.multi_cell(text_w, 4.6, meaning, dry_run=True, output="LINES", align="L")) * 4.6
    h2 = 0
    if how:
        pdf.set_font("Nunito", "", 8.3)
        h2 = len(pdf.multi_cell(text_w, 4.3, how, dry_run=True, output="LINES", align="L")) * 4.3 + 1.2
    h = max(h1 + h2, 5) + 4.2
    if dry:
        return h
    y = pdf.get_y()
    pdf.set_xy(L, y + 1.8)
    pdf.set_font("Lora", "B", 9.8)
    pdf.set_text_color(*LEDGER)
    pdf.multi_cell(TERM_W, 4.6, term, align="L")
    pdf.set_xy(L + TERM_W + GAP, y + 1.8)
    pdf.set_font("Nunito", "", 9)
    pdf.set_text_color(*MEMO_INK)
    pdf.multi_cell(text_w, 4.6, meaning, align="L")
    if how:
        pdf.set_xy(L + TERM_W + GAP, pdf.get_y() + 1.2)
        pdf.set_font("Nunito", "I", 8.3)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(text_w, 4.3, how, align="L")
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.2)
    pdf.line(L, y + h, L + W, y + h)
    pdf.set_y(y + h)
    return h


def render_glossary(pdf):
    L, W = pdf.l_margin, pdf.w - pdf.l_margin - pdf.r_margin
    pdf.add_page()   # the glossary always gets its own page
    pdf.set_y(pdf.get_y() + 2)
    section_title(pdf, "What the measures mean", L, pdf.get_y(), size=14)
    pdf.set_xy(L, pdf.get_y() + 1)
    pdf.set_font("Nunito", "I", 8.8)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 4.5, "For information — plain-language definitions of the terms used in this report.")
    pdf.set_y(pdf.get_y() + 7)
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.2)
    pdf.line(L, pdf.get_y(), L + W, pdf.get_y())
    for entry in GLOSSARY:
        if pdf.get_y() + _glossary_entry(pdf, *entry, dry=True) > pdf.page_break_trigger:
            pdf.add_page()
            pdf.set_y(pdf.get_y() + 2)
        _glossary_entry(pdf, *entry)


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
    pdf.cell(100, 8, "Credit Assessment Report")
    pdf.set_xy(L, 17)
    pdf.set_font("PublicSans", "", 9.5)
    pdf.set_text_color(*TOPBAR_SUB)
    pdf.cell(100, 5, "Retail credit decisioning")
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
    loan = assessment.get("loan")
    label = "Applicant"
    if loan:
        label += f"  ·  Loan of {loan['amount']:,.0f} over {loan['term_months']} months"
    pdf.cell(left_w, 4, label)
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
    render_memo(pdf, memo_md, assessment["reference"])

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

    # ---------------- business view, then glossary ----------------
    render_business_page(pdf, assessment)
    render_glossary(pdf)

    return bytes(pdf.output())
