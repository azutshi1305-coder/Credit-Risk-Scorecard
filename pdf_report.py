import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from rag_memo import friendly_reason

_REPLACEMENTS = {
    "—": "-", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", "•": "-",
    "→": "->", "≤": "<=", "≥": ">=", "±": "+/-",
}


def _pdf_safe(text: str) -> str:
    """fpdf2's core fonts are Latin-1 only; transliterate the common
    Unicode punctuation our markdown/memo text uses, then drop anything
    else that still doesn't fit rather than crash the PDF build."""
    for bad, good in _REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


INPUT_LABELS = {
    "RevolvingUtilizationOfUnsecuredLines": "Revolving utilization of unsecured lines",
    "NumberOfTime30-59DaysPastDueNotWorse": "Times 30-59 days past due",
    "DebtRatio": "Debt ratio",
    "MonthlyIncome": "Monthly income ($)",
    "NumberOfTimes90DaysLate": "Times 90+ days late",
    "NumberRealEstateLoansOrLines": "Number of real estate loans or lines",
    "NumberOfTime60-89DaysPastDueNotWorse": "Times 60-89 days past due",
}


def build_pdf_report(assessment: dict) -> bytes:
    """One self-contained PDF: applicant inputs, score/band/decision,
    triggered rules, reason codes with points, the full memo (with its
    citations and source list), and a short model note."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _pdf_safe("Sample Bank -- Credit Assessment Report"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, _pdf_safe(f"Applicant ID: {assessment['applicant_id']}   |   Fictional lender; portfolio project only"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    def section_title(title):
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(242, 246, 251)
        pdf.cell(0, 9, _pdf_safe(f"  {title}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        pdf.ln(2)

    def body(text, size=10, font="Helvetica", style=""):
        pdf.set_x(pdf.l_margin)
        pdf.set_font(font, style, size)
        pdf.multi_cell(0, 6, _pdf_safe(text))

    # --- Applicant inputs ---
    section_title("Applicant Inputs")
    row = assessment["row"]
    for field, label in INPUT_LABELS.items():
        value = row[field]
        display = "Not declared / unavailable" if pd.isna(value) else f"{value}"
        body(f"{label}: {display}")
    pdf.ln(2)

    # --- Result ---
    decision = assessment["decision"]
    section_title("Assessment Result")
    body(f"Score: {decision['score']:.0f}        Risk band: {decision['band']}        "
         f"Automated band decision: {decision['band_decision']}")
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 7, _pdf_safe(f"FINAL DECISION: {decision['final_decision']}"))
    pdf.ln(2)

    # --- Triggered rules ---
    section_title("Triggered Hard Rules")
    if decision["rule_details"]:
        for rule_id, desc, action in decision["rule_details"]:
            body(f"- {rule_id}: {desc}  (minimum action: {action})")
    else:
        body("None triggered.")
    pdf.ln(2)

    # --- Reason codes ---
    section_title("Reason Codes (points lost vs. best bin)")
    r_codes = assessment["reason_codes"]
    if r_codes:
        for r in r_codes:
            body(f"- {friendly_reason(r['variable'], r['applicant_bin'])}  "
                 f"(-{r['points_lost']:.0f} pts; variable: {r['variable']}, bin: {r['applicant_bin']})")
    else:
        body("No points lost relative to the best bin for any scorecard variable.")
    pdf.ln(2)

    # --- Memo ---
    section_title(f"Credit Memo ({assessment['memo_mode']})")
    body(assessment["memo"], size=9, font="Courier")
    pdf.ln(2)

    # --- Model note ---
    section_title("Model Note")
    body(
        f"Champion model: logistic regression on Weight-of-Evidence encoded variables "
        f"(the fair-lending scorecard). Test-set Gini: {assessment['gini']:.3f}, "
        f"AUC: {assessment['auc']:.3f}, KS: {assessment['ks']:.3f}. "
        f"Age and number of dependents are deliberately excluded from scoring -- age is "
        f"an explicitly protected characteristic under US ECOA, and number of dependents "
        f"is a proxy for marital/family status. Removing both cost approximately 0.7% of "
        f"the scorecard's Gini, measured against held-out test data."
    )

    return bytes(pdf.output())
