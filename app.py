import os
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from scorecard_model import run_pipeline, TARGET
from points_scorecard import build_points_table, score_applicants, reason_codes
from decision_engine import make_decision
from validate_and_report import assign_bands, SEQ_BLUE_5, ks_statistic, predict_proba_bad
from policy_retriever import load_policy_chunks, PolicyRetriever
from rag_memo import generate_memo, friendly_reason, load_dotenv
from challenger_model import compare_models
from pdf_report import build_pdf_report

st.set_page_config(page_title="Sample Bank Credit Scorecard", layout="centered", initial_sidebar_state="expanded")

# ============================= STYLING =============================
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.block-container {padding-top: 2.5rem; padding-bottom: 3rem; max-width: 760px;}

.sb-card {
    background: #ffffff; border: 1px solid #e1e0d9; border-radius: 12px;
    padding: 2rem 2.25rem; box-shadow: 0 1px 3px rgba(11,11,11,0.06);
}
.sb-group-heading {
    font-size: 0.8rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.04em; color: #52514e; margin: 1.4rem 0 0.4rem 0;
}
.sb-group-heading:first-child {margin-top: 0;}

.sb-badge {
    display: flex; align-items: center; gap: 0.75rem; border-radius: 12px;
    padding: 1.1rem 1.5rem; margin-bottom: 1.25rem;
}
.sb-badge-icon {font-size: 2rem; line-height: 1;}
.sb-badge-text {font-size: 1.4rem; font-weight: 700;}

.sb-tiles {display: flex; gap: 1rem; margin-bottom: 1.25rem;}
.sb-tile {
    flex: 1; background: #f9f9f7; border: 1px solid #e1e0d9; border-radius: 10px;
    padding: 1rem 1.25rem; text-align: center;
}
.sb-tile-label {font-size: 0.78rem; color: #898781; text-transform: uppercase; letter-spacing: 0.03em;}
.sb-tile-value {font-size: 1.9rem; font-weight: 700; color: #0b0b0b; margin-top: 0.15rem;}

.sb-bar-wrap {margin: 0.5rem 0 2rem 0; position: relative;}
.sb-bar {display: flex; height: 22px; border-radius: 6px; overflow: hidden;}
.sb-bar-marker {
    position: absolute; top: -10px; transform: translateX(-50%);
    font-size: 0.9rem; color: #0b0b0b;
}
.sb-bar-caption {display: flex; justify-content: space-between; font-size: 0.72rem; color: #898781; margin-top: 2px;}

.sb-reasons {margin-top: 0.5rem;}
.sb-reason-item {
    padding: 0.6rem 0.9rem; background: #f9f9f7; border-radius: 8px;
    margin-bottom: 0.5rem; font-size: 0.95rem;
}
</style>
""", unsafe_allow_html=True)

DECISION_STYLE = {
    "Approve": {"icon": "✅", "bg": "#e7f6e7", "fg": "#0ca30c"},
    "Approve with conditions": {"icon": "✅", "bg": "#fdf3d9", "fg": "#8a6d00"},
    "Refer to underwriter": {"icon": "\U0001F50D", "bg": "#f0efec", "fg": "#52514e"},
    "Manual review": {"icon": "\U0001F50D", "bg": "#f0efec", "fg": "#52514e"},
    "Decline": {"icon": "⛔", "bg": "#fbe9e9", "fg": "#d03b3b"},
}


# ============================= CACHED LOADERS =============================
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


@st.cache_data
def score_range_and_cutoffs():
    result, points_table, _ = load_pipeline()
    _, _, scores, _ = score_applicants(result["test"], result["transformer"], result["features_b"], points_table)
    _, cutoffs = assign_bands(scores)
    return float(scores.min()), float(scores.max()), cutoffs


@st.cache_data
def champion_ks():
    result, _, _ = load_pipeline()
    pred = predict_proba_bad(result["model_b"], result["transformer"], result["test"], result["features_b"])
    return ks_statistic(result["test"][TARGET].values, pred)


result, points_table, retriever = load_pipeline()
transformer, model_b, features_b = result["transformer"], result["model_b"], result["features_b"]

if "nav" not in st.session_state:
    st.session_state.nav = "assess"
if "page" not in st.session_state:
    st.session_state.page = "form"
if "assessment" not in st.session_state:
    st.session_state.assessment = None


# ============================= SIDEBAR =============================
with st.sidebar:
    st.markdown("**Sample Bank**")
    st.caption("Fictional lender / portfolio project")
    nav_choice = st.radio("Navigate", ["Assess an Applicant", "About the Model"], label_visibility="collapsed")
    st.session_state.nav = "assess" if nav_choice == "Assess an Applicant" else "about"


# ============================= SCORE BAR =============================
def render_score_bar(score: float):
    overall_min, overall_max, cutoffs = score_range_and_cutoffs()
    lo = min(overall_min, score) - 5
    hi = max(overall_max, score) + 5
    span = hi - lo

    edges = [lo, cutoffs["D"], cutoffs["C"], cutoffs["B"], cutoffs["A"], hi]
    colors = SEQ_BLUE_5  # E -> A, light to dark
    segments = ""
    for i in range(5):
        width_pct = max(0.0, (edges[i + 1] - edges[i]) / span) * 100
        segments += f'<div style="flex-basis:{width_pct}%; background:{colors[i]};"></div>'

    marker_pct = max(0.0, min(100.0, (score - lo) / span * 100))
    st.markdown(f"""
    <div class="sb-bar-wrap">
        <div class="sb-bar-marker" style="left:{marker_pct}%;">&#9660;</div>
        <div class="sb-bar">{segments}</div>
        <div class="sb-bar-caption"><span>Higher risk</span><span>Lower risk</span></div>
    </div>
    """, unsafe_allow_html=True)


# ============================= FORM PAGE =============================
def render_form_page():
    st.title("Sample Bank")
    st.caption("Retail credit assessment -- fictional lender, portfolio project. Not real credit advice.")

    st.markdown('<div class="sb-card">', unsafe_allow_html=True)

    st.markdown('<div class="sb-group-heading">Credit usage</div>', unsafe_allow_html=True)
    utilization = st.number_input(
        "Revolving utilization of unsecured lines", min_value=0.0, value=0.30, step=0.01, format="%.3f",
        help="Share of available revolving credit currently used. 1.0 = 100% of the limit.",
    )

    st.markdown('<div class="sb-group-heading">Payment history</div>', unsafe_allow_html=True)
    delinquency_unknown = st.checkbox(
        "Delinquency history unavailable or invalid",
        help="Matches real data-quality gaps found during cleaning, where all three past-due counts "
             "are missing or invalid together -- triggers a mandatory manual review.",
    )
    if delinquency_unknown:
        d30 = d90 = d60 = None
    else:
        c1, c2, c3 = st.columns(3)
        d30 = c1.number_input("30-59 days late", min_value=0, value=0, step=1)
        d90 = c2.number_input("90+ days late", min_value=0, value=0, step=1)
        d60 = c3.number_input("60-89 days late", min_value=0, value=0, step=1)

    st.markdown('<div class="sb-group-heading">Income & debt</div>', unsafe_allow_html=True)
    income_unknown = st.checkbox("Income not declared", help="Triggers a mandatory income verification.")
    monthly_income = None
    if not income_unknown:
        monthly_income = st.number_input("Monthly income ($)", min_value=0.0, value=5000.0, step=100.0)
    debt_ratio = st.number_input(
        "Debt ratio", min_value=0.0, value=0.30, step=0.01, format="%.3f",
        help="Monthly debt payments divided by monthly income.",
    )
    real_estate = st.number_input("Real estate loans or lines", min_value=0, value=1, step=1)

    st.markdown("<br>", unsafe_allow_html=True)
    assess_clicked = st.button("Assess", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if assess_clicked:
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

        bin_labels, _, scores, _ = score_applicants(applicant_df, transformer, features_b, points_table)
        bands, _ = assign_bands(scores)
        decision = make_decision(row, scores[applicant_id], bands[applicant_id])
        r_codes = reason_codes(points_table, features_b, bin_labels.loc[applicant_id])

        load_dotenv()
        using_api = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
        with st.spinner("Generating credit memo..."):
            memo = generate_memo(applicant_id, decision, r_codes, retriever)

        st.session_state.assessment = {
            "applicant_id": applicant_id, "row": row, "decision": decision,
            "reason_codes": r_codes, "memo": memo,
            "memo_mode": "Claude-generated" if using_api else "Template fallback (no API key set)",
            "gini": result["gini_b"], "auc": result["auc_b"], "ks": champion_ks(),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        st.session_state.page = "result"
        st.rerun()


# ============================= RESULT PAGE =============================
def render_result_page():
    a = st.session_state.assessment
    decision = a["decision"]

    if st.button("← Assess another applicant"):
        st.session_state.page = "form"
        st.session_state.assessment = None
        st.rerun()

    style = DECISION_STYLE.get(decision["final_decision"], DECISION_STYLE["Refer to underwriter"])
    st.markdown(f"""
    <div class="sb-badge" style="background:{style['bg']}; color:{style['fg']};">
        <div class="sb-badge-icon">{style['icon']}</div>
        <div class="sb-badge-text">{decision['final_decision']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sb-tiles">
        <div class="sb-tile"><div class="sb-tile-label">Score</div><div class="sb-tile-value">{decision['score']:.0f}</div></div>
        <div class="sb-tile"><div class="sb-tile-label">Risk Band</div><div class="sb-tile-value">{decision['band']}</div></div>
    </div>
    """, unsafe_allow_html=True)
    render_score_bar(decision["score"])

    st.markdown('<div class="sb-group-heading">Top reasons</div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-reasons">', unsafe_allow_html=True)
    top_reasons = a["reason_codes"][:3]
    if top_reasons:
        for r in top_reasons:
            st.markdown(f'<div class="sb-reason-item">{friendly_reason(r["variable"], r["applicant_bin"])}</div>',
                        unsafe_allow_html=True)
    else:
        st.markdown('<div class="sb-reason-item">No points lost relative to the best bin for any variable.</div>',
                    unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    pdf_bytes = build_pdf_report(a)
    st.download_button(
        "Download full report (PDF)", data=pdf_bytes,
        file_name=f"sample_bank_credit_report_{a['applicant_id']}.pdf",
        mime="application/pdf", use_container_width=True,
    )


# ============================= ABOUT THE MODEL PAGE =============================
def render_about_page():
    st.title("About the Model")
    tab1, tab2, tab3 = st.tabs(["Model Performance", "Scorecard Points Table", "Policy Documents"])

    with tab1:
        st.caption("Scorecard champion vs. the official fair-lending LightGBM challenger vs. an all-features "
                   "reference model (not production-usable -- it uses age and dependents).")
        with st.spinner("Training LightGBM challengers (first load only, cached after)..."):
            comparison_df = load_model_comparison()
        st.dataframe(comparison_df.style.format({"AUC": "{:.4f}", "Gini": "{:.4f}", "KS": "{:.4f}"}), use_container_width=True)

        st.subheader("Charts")
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

    with tab2:
        st.caption("Champion model (Model B, fair lending). Score = Base Points + sum of the bin points for each variable.")
        st.dataframe(points_table, use_container_width=True)

    with tab3:
        doc_files = [
            "01_retail_credit_policy.md",
            "02_fair_lending_and_adverse_action.md",
            "03_model_risk_and_validation.md",
        ]
        doc_choice = st.selectbox("Choose a document", doc_files)
        st.markdown(load_policy_text(doc_choice))


# ============================= ROUTER =============================
if st.session_state.nav == "about":
    render_about_page()
elif st.session_state.page == "form":
    render_form_page()
else:
    render_result_page()
