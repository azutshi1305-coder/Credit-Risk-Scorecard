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
from rag_memo import generate_memo_with_mode
from challenger_model import compare_models
from pdf_report import build_pdf_report

from ui.theme import CSS
from ui import view_model as vm
from ui import components as comp
from ui import form_help as FH

st.set_page_config(page_title="Sample Bank -- Credit Assessment", layout="wide", initial_sidebar_state="collapsed")
# st.html drops a style-only block in Streamlit 1.45, so the theme must be
# injected through st.markdown (a <style> HTML block is passed through intact).
st.markdown(CSS, unsafe_allow_html=True)


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
MEMO_LABEL = {
    "claude": "Written by Claude from the bank's policy documents",
    "template": "Standard memo template",
    "fallback": "Standard memo template — the AI memo writer couldn't be reached, so this memo was "
                "built from the same policy sections",
}

LATE_OPTIONS = ["0", "1", "2", "3", "4", "5+"]
PROPERTY_OPTIONS = ["0", "1", "2", "3", "4+"]


def _count(choice):
    """'5+' -> 5; None stays None (unanswered)."""
    return None if choice is None else int(str(choice).rstrip("+"))


def build_row(utilization_pct, d30, d60, d90, monthly_income, debt_ratio_pct, real_estate,
              delinquency_unknown, income_unknown, applicant_id="live_applicant") -> pd.Series:
    """The model's input row. Same convention as training: no income -> debt-to-income missing too."""
    return pd.Series({
        "RevolvingUtilizationOfUnsecuredLines": utilization_pct / 100.0,
        "NumberOfTime30-59DaysPastDueNotWorse": np.nan if delinquency_unknown else d30,
        "DebtRatio": np.nan if income_unknown else debt_ratio_pct / 100.0,
        "MonthlyIncome": np.nan if income_unknown else monthly_income,
        "NumberOfTimes90DaysLate": np.nan if delinquency_unknown else d90,
        "NumberRealEstateLoansOrLines": real_estate,
        "NumberOfTime60-89DaysPastDueNotWorse": np.nan if delinquency_unknown else d60,
    }, name=applicant_id)


def quick_score(row: pd.Series):
    """Score + band + decision for one row. Cheap (a table lookup), so the live panel and
    the what-if simulator can call it on every change. Never touches the memo/AI."""
    df = pd.DataFrame([row])
    bin_labels, points_df, scores, base_points = score_applicants(df, transformer, features_b, points_table)
    bands, _ = assign_bands(scores)
    decision = make_decision(row, scores[row.name], bands[row.name])
    return decision, bin_labels, points_df, base_points


def _section(num: int, title: str, helper: str):
    """Numbered section: a step badge + title + helper text rendered as one HTML header
    (no extra st.columns level, so the body can still hold a two-field st.columns row)."""
    st.markdown(
        f'<div class="sb-sec"><span class="sb-sec-num">{num}</span>'
        f'<div><div class="sb-section-title">{title}</div><div class="sb-helper">{helper}</div></div></div>',
        unsafe_allow_html=True)
    return st.container(key=f"section_body_{num}")


def _slider_field(label, key, max_value, help_text):
    """A 0–max % slider that counts as unanswered until the user actually moves it,
    so the form has no silent default values."""
    set_key = f"{key}_set"
    st.session_state.setdefault(set_key, False)

    def _mark_set():
        st.session_state[set_key] = True

    value = st.slider(label, min_value=0, max_value=max_value, value=0, step=1, format="%d%%",
                      key=key, help=help_text, on_change=_mark_set)
    if not st.session_state[set_key]:
        st.markdown('<div class="sb-slide-hint">Drag the slider to set a value</div>', unsafe_allow_html=True)
        return None
    return value


def render_form_page():
    _, _, cutoffs = score_range_and_cutoffs()
    form_col, live_col = st.columns([0.62, 0.38], gap="large")

    with form_col, st.container(key="form_card"):
        st.markdown("### New credit application")
        st.caption("Fields marked * are required. Hover over the (?) icon next to any field "
                   "to see what it means and how to work it out.")

        # --- 1. Applicant ---
        with _section(1, "Applicant", "Who the application is for."):
            ac1, ac2 = st.columns(2)
            applicant_name = ac1.text_input("Applicant name *", key="applicant_name",
                                            placeholder="e.g. Jordan Blake", help=FH.HELP["name"])
            reference = ac2.text_input("Application reference", value=st.session_state.applicant_ref,
                                       key="applicant_ref_input", help=FH.HELP["reference"])
            st.markdown('<div class="sb-note">Used for the report only — not used in scoring '
                        'and not sent to the AI.</div>', unsafe_allow_html=True)

        # --- 2. Credit usage ---
        with _section(2, "Credit usage", "How much of the available revolving credit is being used."):
            utilization_pct = _slider_field("Credit utilisation *", "f_util", 150, FH.HELP["utilisation"])

        # --- 3. Payment history ---
        with _section(3, "Payment history", "Late payments in the last two years. Tap a number for each."):
            delinquency_unknown = st.toggle("Payment history unavailable", key="f_hist_unknown",
                                            help=FH.HELP["history_unavailable"])
            d30 = d60 = d90 = None
            if not delinquency_unknown:
                d30 = _count(st.segmented_control("Payments 30–59 days late *", LATE_OPTIONS, key="f_d30",
                                                  help=FH.HELP["late_30_59"]))
                d60 = _count(st.segmented_control("Payments 60–89 days late *", LATE_OPTIONS, key="f_d60",
                                                  help=FH.HELP["late_60_89"]))
                d90 = _count(st.segmented_control("Payments 90+ days late *", LATE_OPTIONS, key="f_d90",
                                                  help=FH.HELP["late_90"]))

        # --- 4. Income and debt ---
        with _section(4, "Income and debt", "Monthly income and existing debt obligations."):
            income_unknown = st.toggle("Income not declared", key="f_income_unknown",
                                       help=FH.HELP["income_not_declared"])
            monthly_income = debt_ratio_pct = None
            if not income_unknown:
                ic1, ic2 = st.columns(2)
                monthly_income = ic1.number_input(
                    "Monthly income, before tax *", min_value=0.0, value=None, step=100.0, format="%.0f",
                    placeholder="e.g. 5000", help=FH.HELP["income"], key="f_income",
                )
                with ic2:
                    debt_ratio_pct = _slider_field("Debt-to-income *", "f_dti", 150, FH.HELP["dti"])
            real_estate = _count(st.segmented_control(
                "Property loans (mortgages, home-equity lines) *", PROPERTY_OPTIONS, key="f_re",
                help=FH.HELP["real_estate"]))

        st.html("<br>")
        assess_clicked = st.button("Assess application", type="primary", use_container_width=True)
        error_slot = st.empty()

    # ---- what's answered so far (drives the live panel and validation) ----
    progress = [
        ("Applicant name", bool(applicant_name.strip())),
        ("Credit utilisation", utilization_pct is not None),
        ("Payment history", delinquency_unknown or None not in (d30, d60, d90)),
        ("Income and debt-to-income", income_unknown or None not in (monthly_income, debt_ratio_pct)),
        ("Property loans", real_estate is not None),
    ]
    scoring_ready = all(done for label, done in progress if label != "Applicant name")

    preview = None
    if scoring_ready:
        row = build_row(utilization_pct, d30, d60, d90, monthly_income, debt_ratio_pct, real_estate,
                        delinquency_unknown, income_unknown)
        decision, _, _, _ = quick_score(row)
        preview = {"score": float(decision["score"]), "band": decision["band"],
                   "decision": decision["final_decision"], "flags": decision["triggered_rules"],
                   "pd_text": vm.PD_RANGE_TEXT.get(decision["band"], "")}
    with live_col, st.container(key="live_panel"):
        st.html(comp.live_panel_html(progress, preview, cutoffs))

    if assess_clicked:
        required = {
            "Applicant name": applicant_name.strip() or None,
            "Credit utilisation": utilization_pct,
            "Property loans": real_estate,
        }
        if not delinquency_unknown:
            required.update({"30–59 days late": d30, "60–89 days late": d60, "90+ days late": d90})
        if not income_unknown:
            required.update({"Monthly income": monthly_income, "Debt-to-income": debt_ratio_pct})
        missing = [label for label, value in required.items() if value is None]
        if missing:
            error_slot.markdown(
                '<div class="sb-error-box"><b>Fill in the required fields to continue:</b> '
                + ", ".join(missing) + ".</div>", unsafe_allow_html=True)
            return

        st.session_state.applicant_ref = reference
        applicant_id = "live_applicant"
        row = build_row(utilization_pct, d30, d60, d90, monthly_income, debt_ratio_pct, real_estate,
                        delinquency_unknown, income_unknown, applicant_id)
        # `row` above is the ONLY applicant data passed to scoring and decisioning.
        # The applicant's name never leaves the app; the memo only receives the
        # random application reference so the memo can be filed against it.
        applicant_df = pd.DataFrame([row])

        bin_labels, points_df, scores, base_points = score_applicants(applicant_df, transformer, features_b, points_table)
        bands, cutoffs = assign_bands(scores)
        decision = make_decision(row, scores[applicant_id], bands[applicant_id])
        r_codes = reason_codes(points_table, features_b, bin_labels.loc[applicant_id])

        with st.spinner("Writing the credit memo…"):
            memo, memo_source = generate_memo_with_mode(reference, decision, r_codes, retriever)

        metrics = champion_metrics()
        char_rows = vm.characteristic_rows(row, features_b, points_table, points_df.loc[applicant_id])

        st.session_state.assessment = {
            "applicant_id": applicant_id, "applicant_name": applicant_name.strip(),
            "reference": reference, "row": row, "decision": decision,
            "reason_codes": r_codes, "memo": memo,
            "memo_mode": MEMO_LABEL[memo_source], "memo_source": memo_source,
            "gini": metrics["gini"], "auc": metrics["auc"], "ks": metrics["ks"],
            "base_points": int(base_points), "characteristic_rows": char_rows,
            "score_range_cutoffs": score_range_and_cutoffs(),
            "generated_at": datetime.now().strftime("%d %b %Y, %H:%M"),
            "pdf_bytes": None,
        }
        st.session_state.page = "result"
        st.rerun()


def render_what_if(a, cutoffs):
    """Sliders that re-score the applicant instantly: drag a value and watch the dial,
    band and decision move. Uses the same scorecard and policy rules, never the AI."""
    row = a["row"]
    ref = a["reference"]
    base = a["decision"]
    hist_known = not pd.isna(row["NumberOfTimes90DaysLate"])
    income_known = not pd.isna(row["MonthlyIncome"])

    with st.container(key="whatif"):
        st.html('<div class="sb-whatif-title">What if…?</div>'
                '<div class="sb-whatif-sub">Move the sliders to see how the score would change. '
                'This doesn\'t alter the decision above — it shows what would make the biggest difference.</div>')
        left, right = st.columns([0.55, 0.45], gap="large")
        with left:
            util = st.slider("Credit utilisation (%)", 0, 150,
                             int(min(150, round(row["RevolvingUtilizationOfUnsecuredLines"] * 100))),
                             key=f"wi_util_{ref}", help=FH.HELP["utilisation"])
            if income_known:
                dti = st.slider("Debt-to-income (%)", 0, 150, int(min(150, round(row["DebtRatio"] * 100))),
                                key=f"wi_dti_{ref}", help=FH.HELP["dti"])
            else:
                dti = None
                st.caption("Debt-to-income can't be simulated — income wasn't declared.")
            if hist_known:
                d90 = st.select_slider("Payments 90+ days late", options=[0, 1, 2, 3, 4, 5],
                                       value=int(min(5, row["NumberOfTimes90DaysLate"])), key=f"wi_d90_{ref}")
                d30 = st.select_slider("Payments 30–59 days late", options=[0, 1, 2, 3, 4, 5],
                                       value=int(min(5, row["NumberOfTime30-59DaysPastDueNotWorse"])),
                                       key=f"wi_d30_{ref}")
            else:
                d90 = d30 = None
                st.caption("Late payments can't be simulated — payment history is unavailable.")

        sim = row.copy()
        sim["RevolvingUtilizationOfUnsecuredLines"] = util / 100.0
        if dti is not None:
            sim["DebtRatio"] = dti / 100.0
        if d90 is not None:
            sim["NumberOfTimes90DaysLate"] = d90
            sim["NumberOfTime30-59DaysPastDueNotWorse"] = d30
        sim.name = "what_if"
        new_decision, _, _, _ = quick_score(sim)
        with right:
            st.html(comp.whatif_html(float(base["score"]), float(new_decision["score"]), base["band"],
                                     new_decision["band"], new_decision["final_decision"], cutoffs))


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
        render_what_if(a, cutoffs)
        st.html("<br>")
        st.html(comp.drawer_html(a["characteristic_rows"], a["base_points"], decision["score"]))

        st.html("<br>")
        with st.expander("Read the credit memo"):
            st.caption(a["memo_mode"])
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
                # start the next application with a clean form
                for k in list(st.session_state.keys()):
                    if k.startswith("f_") or k in ("applicant_name", "applicant_ref_input"):
                        del st.session_state[k]
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
