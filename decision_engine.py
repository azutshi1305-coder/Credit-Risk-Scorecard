import pandas as pd

from scorecard_model import run_pipeline, TARGET
from points_scorecard import build_points_table, score_applicants
from validate_and_report import assign_bands, BAND_DEFS

BAND_DECISION = {band: decision for band, _, _, decision, _ in BAND_DEFS}

# Decision severity, low -> high. A rule or band can only push the final
# decision to something at least this conservative -- never looser.
SEVERITY = {
    "Approve": 1,
    "Approve with conditions": 2,
    "Refer to underwriter": 3,
    "Manual review": 3,
    "Decline": 4,
}
TIER_LABEL = {1: "Approve", 2: "Approve with conditions", 3: "Refer to underwriter / Manual review", 4: "Decline"}

DELINQUENCY_COLS = [
    "NumberOfTime30-59DaysPastDueNotWorse", "NumberOfTimes90DaysLate", "NumberOfTime60-89DaysPastDueNotWorse",
]


def apply_hard_rules(row: pd.Series, loan: dict = None) -> list:
    """Returns a list of (rule_id, description, minimum_action) for every
    hard policy rule this applicant triggers. `loan` (optional) carries the
    requested loan's affordability figures, used by R6."""
    triggered = []

    if pd.notna(row["NumberOfTimes90DaysLate"]) and row["NumberOfTimes90DaysLate"] >= 1:
        triggered.append(("R1", "History of 90+ days late payment -- cannot be auto-approved", "Refer to underwriter"))

    if pd.notna(row["RevolvingUtilizationOfUnsecuredLines"]) and row["RevolvingUtilizationOfUnsecuredLines"] > 1.0:
        triggered.append(("R2", "Revolving utilization above 100%", "Refer to underwriter"))

    if pd.notna(row["DebtRatio"]) and row["DebtRatio"] > 0.5:
        triggered.append(("R3", "Debt-to-income above 50% -- refer to underwriter for affordability check", "Refer to underwriter"))

    if pd.isna(row["MonthlyIncome"]):
        triggered.append(("R4", "Declared income missing -- refer to underwriter to verify income", "Refer to underwriter"))

    if row[DELINQUENCY_COLS].isna().any():
        triggered.append(("R5", "Missing/invalid delinquency data -- manual review required", "Manual review"))

    # R6: affordable today, but not once the new loan's repayment is added. Only checked
    # when R3 hasn't already fired, so the same affordability concern isn't counted twice.
    post = (loan or {}).get("post_loan_dti")
    r3 = pd.notna(row["DebtRatio"]) and row["DebtRatio"] > 0.5
    if post is not None and post > 0.5 and not r3:
        triggered.append(("R6", "Debt-to-income above 50% once the new loan repayment is added -- "
                                "refer to underwriter for affordability check", "Refer to underwriter"))

    return triggered


def make_decision(row: pd.Series, score: float, band: str, loan: dict = None) -> dict:
    """Any triggered hard rule floors the decision at 'Refer to underwriter'
    -- a rule can never leave an applicant at Approve or Approve with
    conditions, because the check it requires (affordability, income
    verification, delinquency history review) has to be performed by a
    person, not inferred automatically.

    R5 is a deliberate exception on the other end: even if the band alone
    says Decline, a missing/invalid delinquency history could reflect a
    data problem rather than genuine risk, so R5 caps the outcome at
    Manual review instead of letting the system auto-decline on a data
    quality issue. See policies/01_retail_credit_policy.md Section 4 for
    the trade-off this involves."""
    band_decision = BAND_DECISION[band]
    rules = apply_hard_rules(row, loan)
    triggered_ids = [r[0] for r in rules]

    tiers = [(SEVERITY[band_decision], f"Band {band} ({band_decision})")]
    for rule_id, desc, action in rules:
        tiers.append((SEVERITY[action], f"{rule_id}: {desc}"))

    final_tier = max(t for t, _ in tiers)
    if "R5" in triggered_ids:
        final_tier = min(final_tier, SEVERITY["Manual review"])

    if final_tier == 4:
        final_decision = "Decline"
    elif final_tier == 3:
        final_decision = "Manual review" if "R5" in triggered_ids else "Refer to underwriter"
    else:
        final_decision = TIER_LABEL[final_tier]

    # Reasons at or above the final tier -- includes a band-driven Decline
    # even when R5 caps the actual outcome at Manual review, since that's
    # useful context for why the applicant needs a human look.
    driving_reasons = [label for tier, label in tiers if tier >= final_tier]

    return {
        "score": score,
        "band": band,
        "band_decision": band_decision,
        "triggered_rules": triggered_ids,
        "rule_details": rules,
        "final_decision": final_decision,
        "driving_reasons": driving_reasons,
    }


def score_and_decide(df: pd.DataFrame, transformer, features, points_table) -> pd.DataFrame:
    _, _, scores, _ = score_applicants(df, transformer, features, points_table)
    bands, _ = assign_bands(scores)

    results = []
    for idx in df.index:
        decision = make_decision(df.loc[idx], scores[idx], bands[idx])
        decision["applicant_id"] = idx
        results.append(decision)
    return pd.DataFrame(results).set_index("applicant_id")


if __name__ == "__main__":
    pd.set_option("display.width", 160)
    pd.set_option("display.max_colwidth", 60)

    result = run_pipeline(verbose=False)
    transformer, model_b, features_b = result["transformer"], result["model_b"], result["features_b"]
    test = result["test"]

    points_table = build_points_table(model_b, transformer, features_b)
    _, _, scores, _ = score_applicants(test, transformer, features_b, points_table)
    bands, cutoffs = assign_bands(scores)

    # Pick 3 illustrative real applicants from test: low risk (clean Band A,
    # Approve), medium risk (clean Band C, Approve with conditions -- only
    # reachable now when no hard rule is triggered), high risk (reuse the
    # applicant from steps 5 & 7, whose Band E + R5 demonstrates the new
    # "capped at Manual review, not auto-Declined" behavior).
    no_rules_triggered = (
        (~test[DELINQUENCY_COLS].isna().any(axis=1))
        & (test["RevolvingUtilizationOfUnsecuredLines"] <= 1.0)
        & (test["DebtRatio"] <= 0.5)
        & (test["MonthlyIncome"].notna())
        & (test["NumberOfTimes90DaysLate"] < 1)
    )
    band_a_clean = test.index[(bands == "A") & no_rules_triggered]
    band_c_clean = test.index[(bands == "C") & no_rules_triggered]

    low_id = band_a_clean[0]
    medium_id = band_c_clean[0] if len(band_c_clean) > 0 else test.index[(bands == "C")][0]
    high_id = 104180 if 104180 in test.index else test.index[(bands == "E")][0]

    print("=== DECISION ENGINE: 3 EXAMPLE APPLICANTS ===\n")
    for label, applicant_id in [("LOW RISK", low_id), ("MEDIUM RISK", medium_id), ("HIGH RISK", high_id)]:
        row = test.loc[applicant_id]
        decision = make_decision(row, scores[applicant_id], bands[applicant_id])

        print(f"--- {label}: applicant {applicant_id} ---")
        print(f"Score: {decision['score']:.0f}   Band: {decision['band']} ({decision['band_decision']})")
        print(f"Actual outcome (for reference only, not used in decisioning): "
              f"{'Defaulted' if row[TARGET] == 1 else 'Did not default'}")
        if decision["rule_details"]:
            print("Triggered hard rules:")
            for rule_id, desc, action in decision["rule_details"]:
                print(f"  {rule_id}: {desc} (min. action: {action})")
        else:
            print("Triggered hard rules: none")
        print(f"FINAL DECISION: {decision['final_decision']}")
        print(f"Driving reason(s): {decision['driving_reasons']}")
        print()
