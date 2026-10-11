import os
from pathlib import Path

from scorecard_model import run_pipeline, TARGET
from points_scorecard import build_points_table, score_applicants, reason_codes
from decision_engine import make_decision
from validate_and_report import assign_bands
from policy_retriever import load_policy_chunks, PolicyRetriever, retrieve_for_applicant

FRIENDLY_REASON = {
    "RevolvingUtilizationOfUnsecuredLines": "High use of available credit compared with credit limits",
    "NumberOfTime30-59DaysPastDueNotWorse": "History of payments 30 to 59 days late",
    "NumberOfTimes90DaysLate": "History of serious payment delinquency (90+ days late)",
    "NumberOfTime60-89DaysPastDueNotWorse": "History of payments 60 to 89 days late",
    "DebtRatio": "High level of debt compared with income",
    "NumberRealEstateLoansOrLines": "No real estate loans or credit lines on file",
}
FRIENDLY_MISSING = {
    "NumberOfTime30-59DaysPastDueNotWorse": "Payment history could not be confirmed (missing or invalid delinquency data on file)",
    "NumberOfTimes90DaysLate": "Payment history could not be confirmed (missing or invalid delinquency data on file)",
    "NumberOfTime60-89DaysPastDueNotWorse": "Payment history could not be confirmed (missing or invalid delinquency data on file)",
    "DebtRatio": "Debt-to-income could not be confirmed (income not declared)",
}


def friendly_reason(variable: str, applicant_bin: str) -> str:
    if applicant_bin == "Missing":
        return FRIENDLY_MISSING.get(variable, f"{variable} could not be confirmed")
    return FRIENDLY_REASON.get(variable, variable)


def load_dotenv(path: str = ".env"):
    """Minimal .env loader -- no extra dependency. Only sets a variable if
    it isn't already set in the real environment."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_fallback_memo(applicant_id, decision, reason_list, chunks) -> str:
    """Deterministic, template-based memo built from the same structured
    data -- used whenever no API key is configured, so the project works
    for anyone who clones it without needing credentials."""
    lines = [
        f"CREDIT MEMO (template -- no ANTHROPIC_API_KEY configured)",
        f"Applicant: {applicant_id}",
        f"Score: {decision['score']:.0f}   Band: {decision['band']} (target: see policy [1])",
        f"Automated band decision: {decision['band_decision']}",
        f"FINAL DECISION: {decision['final_decision']}",
        "",
        "Top reason codes (customer-friendly):",
    ]
    for r in reason_list:
        lines.append(f"  - {friendly_reason(r['variable'], r['applicant_bin'])} (-{r['points_lost']:.0f} pts vs. best case)")

    if decision["rule_details"]:
        lines.append("")
        lines.append("Hard policy rules triggered:")
        for rule_id, desc, action in decision["rule_details"]:
            lines.append(f"  - {rule_id}: {desc}")

    lines.append("")
    lines.append("Policy references:")
    for c in chunks:
        lines.append(f"  [{c['citation']}] {c['doc']} -- {c['section']}")

    lines.append("")
    lines.append("This applicant's data never leaves the local machine in template mode; "
                  "no protected characteristics (age, dependents) were used in scoring or are referenced above.")
    return "\n".join(lines)


def generate_memo(applicant_id, decision, reason_list, chunks) -> str:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return build_fallback_memo(applicant_id, decision, reason_list, chunks)

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    friendly_reasons = "\n".join(
        f"- {friendly_reason(r['variable'], r['applicant_bin'])} "
        f"(variable: {r['variable']}, bin: {r['applicant_bin']}, {r['points_lost']:.0f} points lost vs. best bin)"
        for r in reason_list
    )
    rules_text = "\n".join(f"- {rid}: {desc} (min. action: {action})" for rid, desc, action in decision["rule_details"]) or "None triggered"

    policy_text = "\n\n".join(f"[{c['citation']}] ({c['doc']} -- {c['section']})\n{c['text']}" for c in chunks)

    system = (
        "You are a credit memo writer for Sample Bank (a fictional lender used for a portfolio project). "
        "Write a short, professional credit memo using ONLY the retrieved policy text provided below -- "
        "do not invent policy that isn't in the retrieved text. "
        "Every policy-based statement you make must cite the retrieved chunk it came from, in the form [1], [2], etc., "
        "matching the bracketed numbers given with each chunk. "
        "Never mention age, number of dependents, or any other protected characteristic, even to say they were excluded. "
        "Keep the tone factual and suitable for an underwriter's file."
    )
    user_message = (
        f"Applicant ID: {applicant_id}\n"
        f"Score: {decision['score']:.0f}\n"
        f"Risk band: {decision['band']} (automated band decision: {decision['band_decision']})\n"
        f"Final decision: {decision['final_decision']}\n"
        f"Driving reason(s): {decision['driving_reasons']}\n\n"
        f"Top reason codes (customer-friendly wording already applied):\n{friendly_reasons}\n\n"
        f"Hard policy rules triggered:\n{rules_text}\n\n"
        f"Retrieved policy text (cite using these bracket numbers):\n{policy_text}\n\n"
        "Write the credit memo now, following the structure required by the retrieved policy for what a "
        "credit memo must contain."
    )

    response = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=4096,
        output_config={"effort": "medium"},
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


if __name__ == "__main__":
    result = run_pipeline(verbose=False)
    transformer, model_b, features_b = result["transformer"], result["model_b"], result["features_b"]
    test = result["test"]

    points_table = build_points_table(model_b, transformer, features_b)
    bin_labels, _, scores, _ = score_applicants(test, transformer, features_b, points_table)
    bands, _ = assign_bands(scores)

    chunks = load_policy_chunks()
    retriever = PolicyRetriever(chunks)

    no_rules_triggered = (
        (~test[["NumberOfTime30-59DaysPastDueNotWorse", "NumberOfTimes90DaysLate", "NumberOfTime60-89DaysPastDueNotWorse"]].isna().any(axis=1))
        & (test["RevolvingUtilizationOfUnsecuredLines"] <= 1.0) & (test["DebtRatio"] <= 0.5)
        & (test["MonthlyIncome"].notna()) & (test["NumberOfTimes90DaysLate"] < 1)
    )
    low_id = test.index[(bands == "A") & no_rules_triggered][0]
    medium_id = test.index[(bands == "C") & no_rules_triggered][0]
    high_id = 104180 if 104180 in test.index else test.index[(bands == "E")][0]

    using_api = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    if not using_api:
        load_dotenv()
        using_api = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    print(f"Mode: {'Claude API' if using_api else 'template fallback (no ANTHROPIC_API_KEY found)'}\n")

    memos = {}
    for label, applicant_id in [("LOW RISK", low_id), ("MEDIUM RISK", medium_id), ("HIGH RISK", high_id)]:
        row = test.loc[applicant_id]
        decision = make_decision(row, scores[applicant_id], bands[applicant_id])
        r_codes = reason_codes(points_table, features_b, bin_labels.loc[applicant_id])
        retrieved = retrieve_for_applicant(decision, r_codes, retriever)
        memo = generate_memo(applicant_id, decision, r_codes, retrieved)
        memos[label] = (applicant_id, memo)
        print(f"=== {label}: memo generated for applicant {applicant_id} ({len(memo)} chars) ===")

    print("\n\n" + "=" * 70)
    print("FULL MEMO -- HIGH RISK EXAMPLE")
    print("=" * 70)
    print(memos["HIGH RISK"][1])
