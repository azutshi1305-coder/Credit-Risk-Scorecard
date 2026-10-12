"""Shared plain-language presentation logic for the Streamlit app and the
PDF report. This is the ONLY place that should ever translate a raw
scorecard variable name or bin label into something a user sees -- both
app.py and pdf_report.py must go through these functions so a raw name
like 'RevolvingUtilizationOfUnsecuredLines' or a bin interval like
'(0.0831, 0.154]' never reaches the screen or the PDF.
"""
import pandas as pd

CHARACTERISTIC_NAMES = {
    "RevolvingUtilizationOfUnsecuredLines": "Credit utilisation",
    "NumberOfTime30-59DaysPastDueNotWorse": "30-59 day delinquencies",
    "DebtRatio": "Debt-to-income",
    "NumberOfTimes90DaysLate": "90+ day delinquencies",
    "NumberRealEstateLoansOrLines": "Real estate loans",
    "NumberOfTime60-89DaysPastDueNotWorse": "60-89 day delinquencies",
}

_DELINQUENCY_LABELS = {
    "NumberOfTime30-59DaysPastDueNotWorse": "30-59 days late",
    "NumberOfTimes90DaysLate": "90+ days late",
    "NumberOfTime60-89DaysPastDueNotWorse": "60-89 days late",
}

STAMP_TEXT = {
    "Approve": "APPROVED",
    "Approve with conditions": "APPROVED WITH CONDITIONS",
    "Refer to underwriter": "REFERRED",
    "Manual review": "MANUAL REVIEW",
    "Decline": "DECLINED",
}

NEXT_STEP = {
    "Approve": "The application proceeds to offer and documentation.",
    "Approve with conditions": "The application proceeds once the listed conditions are satisfied.",
    "Refer to underwriter": "An underwriter reviews the file before any decision is made.",
    "Manual review": "An underwriter reviews the file — the automated system could not confirm "
                      "enough information to decide on its own.",
    "Decline": "The application does not proceed. The applicant may request the reasons for this decision.",
}

# approve / caution / decline -- the three visual decision classes
DECISION_CLASS = {
    "Approve": "approve",
    "Approve with conditions": "caution",
    "Refer to underwriter": "caution",
    "Manual review": "caution",
    "Decline": "decline",
}

PD_RANGE_TEXT = {
    "A": "under 2%",
    "B": "2% to 5%",
    "C": "5% to 10%",
    "D": "10% to 20%",
    "E": "20% or more",
}

RULE_PLAIN_LANGUAGE = {
    "R1": "This applicant has a history of serious (90+ day) late payments, so an underwriter must review "
          "the file before it can be approved.",
    "R2": "Credit usage is above 100% of the limit, so an underwriter must review the file.",
    "R3": "Debt payments are more than half of income, so an affordability check is required.",
    "R4": "Income was not declared, so it must be verified before a decision is made.",
    "R5": "Payment history could not be confirmed, so a person must review the file before any "
          "automated decline can be finalised.",
}


def plain_value(variable: str, raw_value) -> str:
    """The applicant's raw value for one scorecard variable, in plain words."""
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        if variable in _DELINQUENCY_LABELS:
            return "Payment history unavailable"
        if variable == "DebtRatio":
            return "Can't be measured — income not declared"
        return "Not available"

    if variable == "RevolvingUtilizationOfUnsecuredLines":
        pct = round(float(raw_value) * 100)
        return f"Uses {pct}% of available credit" + (" (over limit)" if raw_value > 1.0 else "")

    if variable == "DebtRatio":
        return f"Debt payments are {round(float(raw_value) * 100)}% of income"

    if variable in _DELINQUENCY_LABELS:
        n = int(raw_value)
        label = _DELINQUENCY_LABELS[variable]
        if n == 0:
            return f"No payments {label}"
        return f"{n} payment{'s' if n != 1 else ''} {label}"

    if variable == "NumberRealEstateLoansOrLines":
        n = int(raw_value)
        return f"{n} real estate loan{'s' if n != 1 else ''} or line{'s' if n != 1 else ''}"

    return str(raw_value)


def characteristic_rows(row: pd.Series, features: list, points_table: pd.DataFrame,
                         points_df_row: pd.Series) -> list:
    """One row per scored characteristic: plain name, plain value, points
    earned, and the best possible points for that characteristic -- the
    data behind both the 'Why this decision?' drawer and PDF page 2."""
    rows = []
    for feature in features:
        var_table = points_table[points_table["variable"] == feature]
        best_possible = int(var_table["points"].max())
        earned = int(points_df_row[feature])
        rows.append({
            "name": CHARACTERISTIC_NAMES.get(feature, feature),
            "value_text": plain_value(feature, row[feature]),
            "points_earned": earned,
            "best_possible": best_possible,
            "bar_fraction": max(0.0, min(1.0, earned / best_possible)) if best_possible > 0 else 0.0,
        })
    return rows


def top_characteristics(rows: list, decision_class: str, n: int = 3) -> list:
    """Top N characteristics to headline: strongest (highest points earned)
    when approved, weakest (lowest points earned, i.e. most points lost
    relative to best) otherwise."""
    reverse = decision_class == "approve"
    return sorted(rows, key=lambda r: r["points_earned"], reverse=reverse)[:n]


def policy_check_notes(rule_details: list) -> list:
    """(rule_id, plain_language_text) per triggered hard rule -- the rule
    id itself (e.g. 'R3') is shown per spec, but never the internal
    description/action text."""
    notes = []
    for rule_id, _desc, _action in rule_details:
        notes.append((rule_id, RULE_PLAIN_LANGUAGE.get(rule_id, "A policy check was triggered.")))
    return notes
