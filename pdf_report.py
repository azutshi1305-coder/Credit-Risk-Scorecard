"""PDF credit assessment report -- 'underwriter's desk' theme, matching
the Streamlit result page. Fonts (Lora, Public Sans) are embedded from
assets/fonts/ so the PDF never falls back to a core font, and the memo is
rendered as real PDF text styles (via markdown -> HTML -> fpdf2's
write_html), not raw '**'/'#' markdown syntax.
"""
import re

import markdown
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace

from ui.theme import COLORS, BAND_TINTS, BAND_FULL
from ui import view_model as vm

FONT_DIR = "assets/fonts"
AUTHOR = "Annapurna Zutshi"


def _strip_formatting_in_table_cells(html: str) -> str:
    """fpdf2's write_html cannot handle inline tags (em/b/strong/...) nested
    inside <td>/<th> -- strip those tags inside table cells, keeping the
    text, rather than letting a Claude-generated bold/italic word in a
    table crash the whole report."""
    def clean_cell(m):
        inner = re.sub(r"</?(em|i|b|strong)>", "", m.group(2))
        return m.group(1) + inner + m.group(3)
    return re.sub(r"(<t[dh][^>]*>)(.*?)(</t[dh]>)", clean_cell, html, flags=re.DOTALL)


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


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__(format="A4", unit="mm")
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(18, 18, 18)
        self.add_font("Lora", "", f"{FONT_DIR}/Lora-Regular.ttf")
        self.add_font("Lora", "B", f"{FONT_DIR}/Lora-SemiBold.ttf")
        self.add_font("Lora", "I", f"{FONT_DIR}/Lora-Italic.ttf")
        self.add_font("PublicSans", "", f"{FONT_DIR}/PublicSans-Regular.ttf")
        self.add_font("PublicSans", "B", f"{FONT_DIR}/PublicSans-SemiBold.ttf")
        self.alias_nb_pages()
        self.set_font("PublicSans", "", 10)

    def footer(self):
        self.set_y(-15)
        self.set_font("PublicSans", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 10, f"Sample Bank is a fictional lender  ·  Portfolio project by {AUTHOR}  "
                          f"·  Page {self.page_no()} of {{nb}}", align="C")


def draw_bar(pdf: ReportPDF, x, y, w, h, fraction, fill_color=BRASS, track_color=RULE):
    pdf.set_fill_color(*track_color)
    pdf.rect(x, y, w, h, style="F")
    fw = max(0.0, min(1.0, fraction)) * w
    if fw > 0:
        pdf.set_fill_color(*fill_color)
        pdf.rect(x, y, fw, h, style="F")


def draw_stamp(pdf: ReportPDF, text: str, decision_class: str, cx, cy):
    """Rotated double-border stamp, centred at (cx, cy) in mm."""
    color = {"approve": COLORS["approve"], "caution": COLORS["caution"], "decline": COLORS["decline"]}[decision_class]
    tint = {"approve": COLORS["approve_tint"], "caution": COLORS["caution_tint"], "decline": COLORS["decline_tint"]}[decision_class]
    rgb = hex_to_rgb(color)
    tint_rgb = hex_to_rgb(tint)

    pdf.set_font("Lora", "B", 15)
    text_w = pdf.get_string_width(text)
    box_w, box_h = text_w + 14, 14
    x, y = cx - box_w / 2, cy - box_h / 2

    with pdf.rotation(-7, x=cx, y=cy):
        pdf.set_fill_color(*tint_rgb)
        pdf.set_draw_color(*rgb)
        pdf.set_line_width(0.6)
        pdf.rect(x, y, box_w, box_h, style="FD")
        pdf.rect(x + 1.1, y + 1.1, box_w - 2.2, box_h - 2.2, style="D")
        pdf.set_text_color(*rgb)
        pdf.set_xy(x, y + box_h / 2 - 3)
        pdf.cell(box_w, 6, text, align="C")
    pdf.set_text_color(*INK)


def draw_ruler(pdf: ReportPDF, score, band, cutoffs, score_min, score_max, x, y, width):
    lo = min(score_min, score, min(cutoffs.values())) - 5
    hi = max(score_max, score, max(cutoffs.values())) + 5
    span = hi - lo
    edges = [lo, cutoffs["D"], cutoffs["C"], cutoffs["B"], cutoffs["A"], hi]
    order = ["E", "D", "C", "B", "A"]

    seg_h = 7
    cx_pos = x
    for i, letter in enumerate(order):
        seg_w = max(0.0, (edges[i + 1] - edges[i]) / span) * width
        bg = hex_to_rgb(BAND_FULL[letter]) if letter == band else hex_to_rgb(BAND_TINTS[letter])
        fg = WHITE if letter == band else MUTED
        pdf.set_fill_color(*bg)
        pdf.rect(cx_pos, y, seg_w, seg_h, style="F")
        pdf.set_text_color(*fg)
        pdf.set_font("PublicSans", "B", 8)
        pdf.set_xy(cx_pos, y)
        pdf.cell(seg_w, seg_h, letter, align="C")

        lo_i, hi_i = round(edges[i]), round(edges[i + 1])
        range_text = f"{lo_i}+" if letter == "A" else (f"<={hi_i}" if letter == "E" else f"{lo_i}-{hi_i}")
        pdf.set_text_color(*MUTED)
        pdf.set_font("PublicSans", "", 7)
        pdf.set_xy(cx_pos, y + seg_h + 1)
        pdf.cell(seg_w, 4, range_text, align="C")
        cx_pos += seg_w

    marker_x = x + max(0.0, min(1.0, (score - lo) / span)) * width
    pdf.set_font("Lora", "B", 9)
    pdf.set_text_color(*INK)
    label_w = 14
    pdf.set_xy(marker_x - label_w / 2, y - 7)
    pdf.cell(label_w, 5, f"{score:.0f}", align="C")
    pdf.set_draw_color(*BRASS)
    pdf.set_line_width(0.5)
    pdf.line(marker_x, y - 1.5, marker_x, y)
    pdf.set_text_color(*INK)


def section_label(pdf: ReportPDF, text: str, size=10):
    pdf.set_font("PublicSans", "B", size)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("PublicSans", "", 9)


def build_pdf_report(assessment: dict) -> bytes:
    decision = assessment["decision"]
    decision_class = vm.DECISION_CLASS.get(decision["final_decision"], "caution")
    stamp_text = vm.STAMP_TEXT.get(decision["final_decision"], decision["final_decision"].upper())
    char_rows = assessment["characteristic_rows"]
    top_rows = vm.top_characteristics(char_rows, decision_class, n=3)
    policy_notes = vm.policy_check_notes(decision["rule_details"])

    pdf = ReportPDF()
    pdf.add_page()
    page_w = pdf.w - pdf.l_margin - pdf.r_margin

    # ---- header band ----
    pdf.set_fill_color(*LEDGER)
    pdf.rect(0, 0, pdf.w, 28, style="F")
    pdf.set_draw_color(*BRASS)
    pdf.set_line_width(1.2)
    pdf.line(0, 28, pdf.w, 28)

    pdf.set_xy(pdf.l_margin, 8)
    pdf.set_font("Lora", "B", 15)
    pdf.set_text_color(*WHITE)
    pdf.cell(100, 7, "Sample Bank", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("PublicSans", "", 9)
    pdf.cell(100, 5, "Credit assessment report")

    pdf.set_xy(pdf.w - pdf.r_margin - 80, 8)
    pdf.set_font("PublicSans", "", 8)
    pdf.cell(80, 5, f"Application {assessment['reference']}", align="R", new_x=XPos.LMARGIN, new_y=YPos.TOP)
    pdf.set_xy(pdf.w - pdf.r_margin - 80, 13)
    pdf.cell(80, 5, f"Assessed {assessment['generated_at']}", align="R")

    pdf.set_y(36)
    pdf.set_text_color(*INK)
    pdf.set_font("Lora", "B", 19)
    pdf.set_x(pdf.l_margin)
    pdf.cell(page_w - 55, 10, assessment["applicant_name"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    name_bottom_y = pdf.get_y()

    draw_stamp(pdf, stamp_text, decision_class, cx=pdf.w - pdf.r_margin - 30, cy=42)

    pdf.set_font("PublicSans", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.set_xy(pdf.l_margin, name_bottom_y)
    pdf.multi_cell(page_w - 55, 5, vm.NEXT_STEP.get(decision["final_decision"], ""))
    pdf.ln(2)

    # ---- three figures ----
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.2)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)

    fig_w = page_w / 3
    figures = [
        ("Score", f"{decision['score']:.0f}"),
        ("Risk band", decision["band"]),
        ("Estimated default risk", vm.PD_RANGE_TEXT.get(decision["band"], "")),
    ]
    fig_y = pdf.get_y()
    for i, (label, value) in enumerate(figures):
        fx = pdf.l_margin + i * fig_w
        pdf.set_xy(fx, fig_y)
        pdf.set_font("PublicSans", "", 8)
        pdf.set_text_color(*MUTED)
        pdf.cell(fig_w, 4, label)
        pdf.set_xy(fx, fig_y + 5)
        pdf.set_font("Lora", "B", 15 if i < 2 else 11)
        pdf.set_text_color(*INK)
        pdf.cell(fig_w, 8, value)
    pdf.set_y(fig_y + 15)

    # ---- band ruler ----
    score_min, score_max, cutoffs = assessment["score_range_cutoffs"]
    draw_ruler(pdf, decision["score"], decision["band"], cutoffs, score_min, score_max,
               x=pdf.l_margin, y=pdf.get_y() + 8, width=page_w)
    pdf.set_y(pdf.get_y() + 22)

    # ---- what helped/held back + policy checks ----
    pdf.set_draw_color(*RULE)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(5)

    col_w = page_w / 2 - 4
    col_y = pdf.get_y()
    title = "What helped" if decision_class == "approve" else "What held the score back"
    pdf.set_xy(pdf.l_margin, col_y)
    section_label(pdf, title)
    for r in top_rows:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("PublicSans", "B", 9)
        pdf.set_text_color(*INK)
        pdf.cell(col_w, 5, r["name"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("PublicSans", "", 8.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(col_w, 4.5, r["value_text"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        draw_bar(pdf, pdf.l_margin, pdf.get_y() + 1, col_w, 1.4, r["bar_fraction"])
        pdf.ln(5)
    left_bottom = pdf.get_y()

    right_x = pdf.l_margin + page_w / 2 + 4
    pdf.set_xy(right_x, col_y)
    pdf.set_font("PublicSans", "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(col_w, 6, "Policy checks", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(right_x)
    if not policy_notes:
        pdf.set_font("PublicSans", "", 8.5)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(col_w, 4.5, "No policy rules were triggered.")
    else:
        for rule_id, text in policy_notes:
            note_y = pdf.get_y()
            pdf.set_fill_color(*hex_to_rgb(COLORS["caution_tint"]))
            # measure height first by a dry run
            pdf.set_font("PublicSans", "", 8.5)
            lines = pdf.multi_cell(col_w - 3, 4.2, f"{rule_id}: {text}", dry_run=True, output="LINES")
            note_h = max(8, len(lines) * 4.2 + 3)
            pdf.rect(right_x, note_y, col_w, note_h, style="F")
            pdf.set_draw_color(*BRASS)
            pdf.set_line_width(0.8)
            pdf.line(right_x, note_y, right_x, note_y + note_h)
            pdf.set_xy(right_x + 2.5, note_y + 1.5)
            pdf.set_text_color(*INK)
            pdf.multi_cell(col_w - 4, 4.2, f"{rule_id}: {text}")
            pdf.set_xy(right_x, note_y + note_h + 2)
    right_bottom = pdf.get_y()
    pdf.set_y(max(left_bottom, right_bottom) + 4)

    # ================= PAGE 2: how the score was built =================
    pdf.add_page()
    pdf.set_font("Lora", "B", 14)
    pdf.set_text_color(*INK)
    pdf.cell(0, 8, "How the score was built", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("PublicSans", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, f"Base points: {assessment['base_points']}. Score = base points + points earned on each "
                   f"characteristic.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    name_w, val_w, bar_w, pts_w = 42, 72, 40, page_w - 42 - 72 - 40
    header_y = pdf.get_y()
    pdf.set_font("PublicSans", "B", 8.5)
    pdf.set_text_color(*INK)
    pdf.set_x(pdf.l_margin)
    pdf.cell(name_w, 6, "Characteristic")
    pdf.cell(val_w, 6, "Value")
    pdf.cell(bar_w, 6, "Points earned")
    pdf.cell(pts_w, 6, "Of possible", align="R")
    pdf.ln(6)
    pdf.set_draw_color(*RULE)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)

    for r in char_rows:
        row_y = pdf.get_y()
        pdf.set_font("PublicSans", "", 8.5)
        pdf.set_text_color(*INK)
        pdf.set_xy(pdf.l_margin, row_y)
        pdf.multi_cell(name_w - 2, 4.3, r["name"])
        name_bottom = pdf.get_y()

        pdf.set_xy(pdf.l_margin + name_w, row_y)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(val_w - 2, 4.3, r["value_text"])
        val_bottom = pdf.get_y()

        bar_x = pdf.l_margin + name_w + val_w
        draw_bar(pdf, bar_x, row_y + 1, bar_w - 4, 2.2, r["bar_fraction"])

        pdf.set_xy(bar_x + bar_w, row_y)
        pdf.set_text_color(*INK)
        pdf.set_font("PublicSans", "B", 8.5)
        pdf.cell(pts_w, 4.3, f"{r['points_earned']} / {r['best_possible']}", align="R")

        row_bottom = max(name_bottom, val_bottom, row_y + 6)
        pdf.set_y(row_bottom + 2)
        pdf.set_draw_color(*RULE)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(2)

    pdf.ln(2)
    pdf.set_font("PublicSans", "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, f"Base points: {assessment['base_points']}      Total score: {decision['score']:.0f}")

    # ================= PAGE 3+: credit memo =================
    pdf.add_page()
    pdf.set_font("Lora", "B", 14)
    pdf.set_text_color(*INK)
    pdf.cell(0, 8, "Credit memo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("PublicSans", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, assessment["memo_mode"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("PublicSans", "", 9.5)
    pdf.set_text_color(*INK)
    memo_html = markdown.markdown(assessment["memo"], extensions=["tables", "nl2br"])
    memo_html = _strip_formatting_in_table_cells(memo_html)
    pdf.write_html(memo_html, tag_styles={
        "h1": FontFace(family="Lora", emphasis="BOLD", size_pt=13, color=INK),
        "h2": FontFace(family="Lora", emphasis="BOLD", size_pt=12, color=INK),
        "h3": FontFace(family="Lora", emphasis="BOLD", size_pt=11, color=INK),
        "p": FontFace(family="PublicSans", size_pt=9.5, color=INK),
        "li": FontFace(family="PublicSans", size_pt=9.5, color=INK),
        "b": FontFace(family="PublicSans", emphasis="BOLD", color=INK),
        "strong": FontFace(family="PublicSans", emphasis="BOLD", color=INK),
        "i": FontFace(family="Lora", emphasis="I", size_pt=9.5, color=INK),
        "em": FontFace(family="Lora", emphasis="I", size_pt=9.5, color=INK),
    })

    pdf.ln(4)
    pdf.set_draw_color(*RULE)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Lora", "B", 11)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, "About this model", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("PublicSans", "", 9)
    pdf.set_text_color(*INK)
    pdf.multi_cell(
        0, 4.8,
        f"Champion model: logistic regression on Weight-of-Evidence encoded variables (the fair-lending "
        f"scorecard). Test-set Gini: {assessment['gini']:.3f}, AUC: {assessment['auc']:.3f}, "
        f"KS: {assessment['ks']:.3f}. Age and number of dependents are deliberately excluded from scoring -- "
        f"age is an explicitly protected characteristic under US ECOA, and number of dependents is a proxy "
        f"for marital/family status. Removing both cost approximately 0.7% of the scorecard's Gini, measured "
        f"against held-out test data."
    )

    return bytes(pdf.output())
