import os

import numpy as np
import pandas as pd
import streamlit as st

from scorecard_model import run_pipeline, TARGET
from points_scorecard import build_points_table, score_applicants, reason_codes
from decision_engine import make_decision, DELINQUENCY_COLS
from validate_and_report import assign_bands
from policy_retriever import load_policy_chunks, PolicyRetriever
from rag_memo import generate_memo, friendly_reason, load_dotenv
from challenger_model import compare_models

st.set_page_config(page_title="Sample Bank Credit Scorecard", layout="wide")


@st.cache_resource
def load_pipeline():
    result = run_pipeline(verbose=False)
    points_table = build_points_table(result["model_b"], result["transformer"], result["features_b"])
    retriever = PolicyRetriever(load_policy_chunks())
    return result, points_table, retriever


@st.cache_resource
def load_model_comparison():
    result, _, _ = load_pipeline()
    comparison = compare_models(result["train"], result["test"], result, verbose=False)
    return comparison["comparison"]


@st.cache_data
def load_policy_text(filename: str) -> str:
    with open(os.path.join("policies", filename), encoding="utf-8") as f:
        return f.read()


result, points_table, retriever = load_pipeline()
transformer, model_b, features_b = result["transformer"], result["model_b"], result["features_b"]

st.title("Sample Bank -- Retail Credit Scorecard")
st.caption("Fictional lender / portfolio project. Not a real bank, not real applicants, not legal or credit advice.")

tab1, tab2, tab3, tab4 = st.tabs([
    "Assess an Applicant", "Model Performance", "Scorecard Points Table", "Policy Documents",
])

# ============================= TAB 1: ASSESS =============================
with tab1:
    st.header("Assess an Applicant")
    st.caption("Inputs cover every variable the champion scorecard and hard policy rules use. "
               "Age and number of dependents are deliberately excluded from scoring (fair lending).")

    col1, col2 = st.columns(2)
    with col1:
        utilization = st.number_input(
            "Revolving utilization of unsecured lines (share of credit limit used; 1.0 = 100%)",
            min_value=0.0, value=0.30, step=0.01, format="%.3f",
        )
        debt_ratio = st.number_input(
            "Debt ratio (monthly debt payments / monthly income)",
            min_value=0.0, value=0.30, step=0.01, format="%.3f",
        )
        real_estate = st.number_input("Number of real estate loans or lines", min_value=0, value=1, step=1)

        income_unknown = st.checkbox("Income not declared (triggers rule R4)")
        monthly_income = None
        if not income_unknown:
            monthly_income = st.number_input("Monthly income ($)", min_value=0.0, value=5000.0, step=100.0)

    with col2:
        delinquency_unknown = st.checkbox(
            "Delinquency history unavailable / invalid (triggers rule R5)",
            help="Matches the real sentinel-code pattern found in the training data, where all three "
                 "past-due counts are missing or invalid together, not independently.",
        )
        if delinquency_unknown:
            st.caption("All three past-due counts below will be treated as missing.")
            d30 = d90 = d60 = None
        else:
            d30 = st.number_input("Times 30-59 days past due", min_value=0, value=0, step=1)
            d90 = st.number_input("Times 90+ days late", min_value=0, value=0, step=1)
            d60 = st.number_input("Times 60-89 days past due", min_value=0, value=0, step=1)

    if st.button("Assess Applicant", type="primary"):
        applicant_id = "live_applicant"
        row = pd.Series({
            "RevolvingUtilizationOfUnsecuredLines": utilization,
            "NumberOfTime30-59DaysPastDueNotWorse": np.nan if delinquency_unknown else d30,
            "DebtRatio": debt_ratio,
            "MonthlyIncome": np.nan if income_unknown else monthly_income,
            "NumberOfTimes90DaysLate": np.nan if delinquency_unknown else d90,
            "NumberRealEstateLoansOrLines": real_estate,
            "NumberOfTime60-89DaysPastDueNotWorse": np.nan if delinquency_unknown else d60,
        }, name=applicant_id)
        applicant_df = pd.DataFrame([row])

        bin_labels, points_df, scores, base_points = score_applicants(applicant_df, transformer, features_b, points_table)
        bands, _ = assign_bands(scores)
        decision = make_decision(row, scores[applicant_id], bands[applicant_id])
        r_codes = reason_codes(points_table, features_b, bin_labels.loc[applicant_id])

        m1, m2, m3 = st.columns(3)
        m1.metric("Score", f"{decision['score']:.0f}")
        m2.metric("Risk Band", decision["band"])
        m3.metric("Final Decision", decision["final_decision"])

        if decision["band_decision"] != decision["final_decision"]:
            st.info(f"Automated band decision was **{decision['band_decision']}**, "
                    f"overridden to **{decision['final_decision']}** by a triggered hard rule.")

        if decision["rule_details"]:
            st.subheader("Triggered Hard Rules")
            for rule_id, desc, action in decision["rule_details"]:
                st.write(f"**{rule_id}**: {desc}  \nMinimum action: {action}")
        else:
            st.subheader("Triggered Hard Rules")
            st.write("None.")

        st.subheader("Reason Codes (customer-friendly)")
        if r_codes:
            for r in r_codes:
                st.write(f"- {friendly_reason(r['variable'], r['applicant_bin'])} "
                         f"(-{r['points_lost']:.0f} pts vs. best bin)")
        else:
            st.write("No points lost relative to the best bin for any scorecard variable.")

        load_dotenv()
        using_api = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
        st.subheader(f"Credit Memo -- {'Claude-generated' if using_api else 'Template fallback (no ANTHROPIC_API_KEY set)'}")
        with st.spinner("Generating memo..."):
            memo = generate_memo(applicant_id, decision, r_codes, retriever)
        st.markdown(memo)

# ============================= TAB 2: PERFORMANCE =============================
with tab2:
    st.header("Model Performance")
    st.caption("Scorecard champion vs. the official fair-lending LightGBM challenger vs. an all-features "
               "reference model (not usable in production -- it uses age and dependents).")
    with st.spinner("Training LightGBM challengers (first load only, cached after)..."):
        comparison_df = load_model_comparison()
    st.dataframe(comparison_df.style.format({"AUC": "{:.4f}", "Gini": "{:.4f}", "KS": "{:.4f}"}), use_container_width=True)

    st.header("Charts")
    chart_files = [
        ("roc_curve.png", "ROC Curve"),
        ("score_distribution.png", "Score Distribution by Outcome"),
        ("default_rate_by_band.png", "Default Rate by Risk Band"),
        ("iv_bar_chart.png", "Information Value by Variable"),
        ("shap_summary.png", "SHAP Summary (Fair-Lending Challenger)"),
        ("shap_individual.png", "SHAP Individual Explanation"),
    ]
    cols = st.columns(2)
    for i, (filename, caption) in enumerate(chart_files):
        path = os.path.join("reports", "figures", filename)
        with cols[i % 2]:
            if os.path.exists(path):
                st.image(path, caption=caption, use_container_width=True)
            else:
                st.warning(f"{filename} not found -- run validate_and_report.py / challenger_model.py first.")

# ============================= TAB 3: POINTS TABLE =============================
with tab3:
    st.header("Scorecard Points Table")
    st.caption("Champion model (Model B, fair lending). Score = Base Points + sum of the bin points for each variable.")
    st.dataframe(points_table, use_container_width=True)

# ============================= TAB 4: POLICY DOCUMENTS =============================
with tab4:
    st.header("Policy Documents")
    doc_files = [
        "01_retail_credit_policy.md",
        "02_fair_lending_and_adverse_action.md",
        "03_model_risk_and_validation.md",
    ]
    doc_choice = st.selectbox("Choose a document", doc_files)
    st.markdown(load_policy_text(doc_choice))
