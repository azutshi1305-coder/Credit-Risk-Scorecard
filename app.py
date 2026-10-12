import os
import random
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from scorecard_model import run_pipeline, TARGET
from points_scorecard import build_points_table, score_applicants, reason_codes
from decision_engine import make_decision
from validate_and_report import assign_bands, ks_statistic, predict_proba_bad
from policy_retriever import load_policy_chunks, PolicyRetriever
from rag_memo import generate_memo, load_dotenv
from challenger_model import compare_models
from pdf_report import build_pdf_report

from ui.theme import CSS
from ui import view_model as vm
from ui import components as comp

st.set_page_config(page_title="Sample Bank -- Credit Assessment", layout="wide", initial_sidebar_state="collapsed")
st.html(CSS)


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
def champion_metrics():
    result, _, _ = load_pipeline()
    pred = predict_proba_bad(result["model_b"], result["transformer"], result["test"], result["features_b"])
    ks = ks_statistic(result["test"][TARGET].values, pred)
    return {"gini": result["gini_b"], "auc": result["auc_b"], "ks": ks}


result, points_table, retriever = load_pipeline()
transformer, model_b, features_b = result["transformer"], result["model_b"], result["features_b"]

if "nav" not in st.session_state:
    st.session_state.nav = "Assess"
if "page" not in st.session_state:
    st.session_state.page = "form"
if "assessment" not in st.session_state:
    st.session_state.assessment = None
if "applicant_ref" not in st.session_state:
    st.session_state.applicant_ref = f"SB-{datetime.now().year}-{random.randint(0, 9999):04d}"


# ============================= TOP BAR =============================
with st.container(key="topbar"):
    tcol1, tcol2 = st.columns([3, 1])
    with tcol1:
        st.html(comp.top_bar_title_html())
    with tcol2:
        nav_choice = st.segmented_control(
            "Navigate", ["Assess", "About the model"],
            default=st.session_state.nav, label_visibility="collapsed", key="nav_control",
        )
        st.session_state.nav = nav_choice or st.session_state.nav


# ============================= FORM PAGE =============================
def render_form_page():
    with st.container(key="form_card"):
        st.markdown("### New credit application")
        st.caption("Enter the applicant's details below to produce a scorecard decision and credit memo.")

        # --- 1. Applicant ---
        r1a, r1b = st.columns([0.05, 0.95])
        r1a.markdown('<div class="sb-section-num">1</div>', unsafe_allow_html=True)
        with r1b:
            st.markdown('<div class="sb-section-title">Applicant</div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-helper">Used to label the application file and the PDF report.</div>',
                        unsafe_allow_html=True)
            ac1, ac2 = st.columns(2)
            applicant_name = ac1.text_input("Applicant name", key="applicant_name", placeholder="e.g. Jordan Blake")
            reference = ac2.text_input("Application reference", value=st.session_state.applicant_ref, key="applicant_ref_input")
            st.markdown('<div class="sb-note">Used for the report only -- not used in scoring and not sent to the AI.</div>',
                        unsafe_allow_html=True)

        # --- 2. Credit usage ---
        r2a, r2b = st.columns([0.05, 0.95])
        r2a.markdown('<div class="sb-section-num">2</div>', unsafe_allow_html=True)
        with r2b:
            st.markdown('<div class="sb-section-title">Credit usage</div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-helper">Share of available revolving credit currently in use.</div>',
                        unsafe_allow_html=True)
            utilization_pct = st.number_input(
                "Credit utilisation (%)", min_value=0.0, value=30.0, step=1.0, format="%.0f",
                help="e.g. 30 means 30% of the credit limit is in use. Values above 100 are allowed.",
            )

        # --- 3. Payment history ---
        r3a, r3b = st.columns([0.05, 0.95])
        r3a.markdown('<div class="sb-section-num">3</div>', unsafe_allow_html=True)
        with r3b:
            st.markdown('<div class="sb-section-title">Payment history</div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-helper">Number of late payments on file, by how late they were.</div>',
                        unsafe_allow_html=True)
            delinquency_unknown = st.checkbox("Payment history unavailable")
            if delinquency_unknown:
                d30 = d90 = d60 = None
            else:
                c1, c2, c3 = st.columns(3)
                d30 = c1.number_input("30-59 days late", min_value=0, value=0, step=1)
                d90 = c2.number_input("90+ days late", min_value=0, value=0, step=1)
                d60 = c3.number_input("60-89 days late", min_value=0, value=0, step=1)

        # --- 4. Income and debt ---
        r4a, r4b = st.columns([0.05, 0.95])
        r4a.markdown('<div class="sb-section-num">4</div>', unsafe_allow_html=True)
        with r4b:
            st.markdown('<div class="sb-section-title">Income and debt</div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-helper">Monthly income and existing debt obligations.</div>',
                        unsafe_allow_html=True)
            income_unknown = st.checkbox("Income not declared")
            ic1, ic2 = st.columns(2)
            monthly_income = None
            if not income_unknown:
                monthly_income = ic1.number_input("Monthly income ($)", min_value=0.0, value=5000.0, step=100.0)
            else:
                ic1.markdown("&nbsp;", unsafe_allow_html=True)
            debt_ratio_pct = ic2.number_input(
                "Debt-to-income (%)", min_value=0.0, value=30.0, step=1.0, format="%.0f",
                help="Monthly debt payments as a percentage of monthly income.",
            )
            real_estate = st.number_input("Real estate loans or lines", min_value=0, value=1, step=1)

        st.html("<br>")
        assess_clicked = st.button("Assess application", type="primary", use_container_width=True)

        name_error = st.empty()

        if assess_clicked:
            if not applicant_name.strip():
                name_error.markdown('<div class="sb-error">Applicant name is required.</div>', unsafe_allow_html=True)
                return

            st.session_state.applicant_ref = reference
            applicant_id = "live_applicant"
            row = pd.Series({
                "RevolvingUtilizationOfUnsecuredLines": utilization_pct / 100.0,
                "NumberOfTime30-59DaysPastDueNotWorse": np.nan if delinquency_unknown else d30,
                "DebtRatio": debt_ratio_pct / 100.0,
                "MonthlyIncome": np.nan if income_unknown else monthly_income,
                "NumberOfTimes90DaysLate": np.nan if delinquency_unknown else d90,
                "NumberRealEstateLoansOrLines": real_estate,
                "NumberOfTime60-89DaysPastDueNotWorse": np.nan if delinquency_unknown else d60,
            }, name=applicant_id)
            # `row` above is the ONLY thing passed to scoring/decisioning/the memo --
            # applicant_name and reference are kept entirely separate and never enter it.
            applicant_df = pd.DataFrame([row])

            bin_labels, points_df, scores, base_points = score_applicants(applicant_df, transformer, features_b, points_table)
            bands, cutoffs = assign_bands(scores)
            decision = make_decision(row, scores[applicant_id], bands[applicant_id])
            r_codes = reason_codes(points_table, features_b, bin_labels.loc[applicant_id])

            load_dotenv()
            using_api = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
            with st.spinner("Generating credit memo..."):
                memo = generate_memo(applicant_id, decision, r_codes, retriever)

            metrics = champion_metrics()
            char_rows = vm.characteristic_rows(row, features_b, points_table, points_df.loc[applicant_id])

            st.session_state.assessment = {
                "applicant_id": applicant_id, "applicant_name": applicant_name.strip(),
                "reference": reference, "row": row, "decision": decision,
                "reason_codes": r_codes, "memo": memo,
                "memo_mode": "Claude-generated" if using_api else "Template fallback (no API key set)",
                "gini": metrics["gini"], "auc": metrics["auc"], "ks": metrics["ks"],
                "base_points": int(base_points), "characteristic_rows": char_rows,
                "score_range_cutoffs": score_range_and_cutoffs(),
                "generated_at": datetime.now().strftime("%d %b %Y, %H:%M"),
                "pdf_bytes": None,
            }
            st.session_state.page = "result"
            st.rerun()


# ============================= RESULT PAGE =============================
def render_result_page():
    a = st.session_state.assessment
    decision = a["decision"]
    decision_class = vm.DECISION_CLASS.get(decision["final_decision"], "caution")

    with st.container(key="result_wrap"):
        overall_min, overall_max, cutoffs = score_range_and_cutoffs()
        st.html(comp.application_file_card_html(
            reference=a["reference"], assessed_at=a["generated_at"], applicant_name=a["applicant_name"],
            final_decision=decision["final_decision"], score=decision["score"], band=decision["band"],
            cutoffs=cutoffs, score_min=overall_min, score_max=overall_max,
        ))

        st.html("<br>")
        col_left, col_right = st.columns(2)
        with col_left:
            top_rows = vm.top_characteristics(a["characteristic_rows"], decision_class, n=3)
            title = "What helped" if decision_class == "approve" else "What held the score back"
            st.html(comp.characteristics_column_html(title, top_rows))
        with col_right:
            notes = vm.policy_check_notes(decision["rule_details"])
            st.html(comp.policy_checks_column_html(notes))

        st.html("<br>")
        st.html(comp.drawer_html(a["characteristic_rows"], a["base_points"], decision["score"]))

        st.html("<br>")
        with st.expander("Read the credit memo"):
            st.caption(f"Written by Claude from the bank's policy documents" if "Claude" in a["memo_mode"]
                       else "Template memo (no API key set)")
            st.markdown(a["memo"])

        st.html("<br>")
        if a["pdf_bytes"] is None:
            a["pdf_bytes"] = build_pdf_report(a)

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            st.download_button(
                "Download full report (PDF)", data=a["pdf_bytes"],
                file_name=f"sample_bank_credit_report_{a['reference']}.pdf",
                mime="application/pdf", type="primary", use_container_width=True,
            )
        with bcol2:
            if st.button("Assess another application", use_container_width=True):
                st.session_state.page = "form"
                st.session_state.assessment = None
                st.session_state.applicant_ref = f"SB-{datetime.now().year}-{random.randint(0, 9999):04d}"
                st.rerun()


# ============================= ABOUT THE MODEL PAGE =============================
def render_about_page():
    with st.container(key="about_wrap"):
        st.markdown("## About the model")
        st.caption("How Sample Bank's credit scorecard works, how it performs, and the policies behind each decision.")

        tab1, tab2, tab3 = st.tabs(["Performance", "Scorecard points", "Policy documents"])

        with tab1:
            metrics = champion_metrics()
            m1, m2, m3 = st.columns(3)
            for col, label, key in [(m1, "Gini", "gini"), (m2, "KS", "ks"), (m3, "AUC", "auc")]:
                col.html(f'<div class="sb-tile"><div class="sb-tile-label">{label}</div>'
                         f'<div class="sb-tile-value">{metrics[key]:.3f}</div></div>')

            st.html("<br>")
            st.caption("Scorecard champion vs. the official fair-lending LightGBM challenger vs. an all-features "
                       "reference model (not production-usable -- it uses age and dependents).")
            with st.spinner("Training LightGBM challengers (first load only, cached after)..."):
                comparison_df = load_model_comparison()
            st.dataframe(comparison_df.style.format({"AUC": "{:.4f}", "Gini": "{:.4f}", "KS": "{:.4f}"}),
                        use_container_width=True)

            st.markdown("#### Charts")
            chart_files = [
                ("roc_curve.png", "ROC curve"),
                ("score_distribution.png", "Score distribution by outcome"),
                ("default_rate_by_band.png", "Default rate by risk band"),
                ("iv_bar_chart.png", "Information value by variable"),
                ("shap_summary.png", "SHAP summary (fair-lending challenger)"),
                ("shap_individual.png", "SHAP individual explanation"),
            ]
            cols = st.columns(2)
            for i, (filename, caption) in enumerate(chart_files):
                path = os.path.join("reports", "figures", filename)
                with cols[i % 2]:
                    if os.path.exists(path):
                        st.image(path, caption=caption, use_container_width=True)

        with tab2:
            st.caption("Champion model (fair-lending scorecard). Score = base points + the points earned on each characteristic.")
            friendly_table = points_table.copy()
            friendly_table["variable"] = friendly_table["variable"].map(
                lambda v: vm.CHARACTERISTIC_NAMES.get(v, v)
            )
            friendly_table = friendly_table.rename(columns={"variable": "characteristic"})
            st.dataframe(friendly_table[["characteristic", "bin", "points"]], use_container_width=True)

        with tab3:
            doc_files = [
                "01_retail_credit_policy.md",
                "02_fair_lending_and_adverse_action.md",
                "03_model_risk_and_validation.md",
            ]
            doc_choice = st.selectbox("Choose a document", doc_files)
            st.markdown(load_policy_text(doc_choice))


# ============================= ROUTER =============================
if st.session_state.nav == "About the model":
    render_about_page()
elif st.session_state.page == "form":
    render_form_page()
else:
    render_result_page()
