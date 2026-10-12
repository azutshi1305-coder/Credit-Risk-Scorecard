import re
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
import portfolio_economics as pe

from ui.theme import CSS
from ui import view_model as vm
from ui import components as comp
from ui import form_help as FH

st.set_page_config(page_title="Credit Assessment", layout="wide", initial_sidebar_state="collapsed")
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


@st.cache_data
def portfolio_view():
    """Cut-off trade-off and expected loss by band, measured on the test set."""
    result, points_table, _ = load_pipeline()
    _, _, scores, _ = score_applicants(result["test"], result["transformer"], result["features_b"], points_table)
    bands, cutoffs = assign_bands(scores)
    y = result["test"].loc[scores.index, TARGET].values
    return pe.summarise(bands.astype(str).values, y, cutoffs)


result, points_table, retriever = load_pipeline()
transformer, model_b, features_b = result["transformer"], result["model_b"], result["features_b"]

if "nav" not in st.session_state:
    st.session_state.nav = "Assess"
if "page" not in st.session_state:
    st.session_state.page = "form"
if "assessment" not in st.session_state:
    st.session_state.assessment = None
if "applicant_ref" not in st.session_state:
    st.session_state.applicant_ref = f"CR-{datetime.now().year}-{random.randint(0, 9999):04d}"


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


STEPS = ["Applicant", "Credit usage", "Payment history", "Income & debt", "Review"]


def _data():
    return st.session_state.setdefault("app_data", {})


def _choice_to_count(choice):
    return None if choice is None else int(str(choice).rstrip("+"))


def _answers(d):
    """Model inputs from the saved answers (None where not answered yet)."""
    hist_unknown = d.get("hist_unknown", False)
    income_unknown = d.get("income_unknown", False)
    return {
        "utilization_pct": d.get("util"),
        "d30": None if hist_unknown else _choice_to_count(d.get("d30")),
        "d60": None if hist_unknown else _choice_to_count(d.get("d60")),
        "d90": None if hist_unknown else _choice_to_count(d.get("d90")),
        "monthly_income": None if income_unknown else d.get("income"),
        "debt_ratio_pct": None if income_unknown else d.get("dti"),
        "real_estate": _choice_to_count(d.get("re")),
        "delinquency_unknown": hist_unknown,
        "income_unknown": income_unknown,
    }


def _step_missing(step, d):
    """Required answers still missing on a given step (empty list = step complete)."""
    a = _answers(d)
    if step == 0:
        return [] if (d.get("name") or "").strip() else ["applicant's name"]
    if step == 1:
        return [] if a["utilization_pct"] is not None else ["credit utilisation"]
    if step == 2:
        if a["delinquency_unknown"]:
            return []
        return [lbl for lbl, k in (("30–59 days late", "d30"), ("60–89 days late", "d60"),
                                   ("90+ days late", "d90")) if a[k] is None]
    if step == 3:
        missing = []
        if not a["income_unknown"]:
            if a["monthly_income"] is None:
                missing.append("monthly income")
            if a["debt_ratio_pct"] is None:
                missing.append("debt-to-income")
        if a["real_estate"] is None:
            missing.append("property loans")
        return missing
    return []


def _go(step):
    st.session_state.step = step
    st.session_state.step_error = None


def _question(title, helper):
    st.html(f'<div class="sb-q-title">{title}</div><div class="sb-q-help">{helper}</div>')


def render_step(step, d):
    """Draw one question screen. Answers are saved into app_data as they're typed, so they
    survive moving back and forth between steps and feed the live score panel."""
    if step == 0:
        _question("Who is applying?", "Enter the applicant's full name as it should appear on the report.")
        d["name"] = st.text_input("Full name *", value=d.get("name", ""), key="w_name",
                                  placeholder="e.g. Jordan Blake", help=FH.HELP["name"])
        st.html('<div class="sb-note">Only shown on the result page and the report — never used in '
                'scoring and never sent to the AI.</div>')

    elif step == 1:
        _question("How much of their available credit is in use?",
                  "Total card and credit-line balances as a share of their combined limits.")
        d["util"] = st.number_input("Credit utilisation (%) *", min_value=0.0, value=d.get("util"), step=1.0,
                                    format="%.0f", placeholder="e.g. 30", key="w_util", help=FH.HELP["utilisation"])

    elif step == 2:
        _question("Any late payments in the last two years?",
                  "Tap how many times a payment was overdue in each range. Choose 0 if never.")
        d["hist_unknown"] = st.toggle("Payment history isn't available", value=d.get("hist_unknown", False),
                                      key="w_hist_unknown", help=FH.HELP["history_unavailable"])
        if not d["hist_unknown"]:
            d["d30"] = st.segmented_control("30–59 days late *", LATE_OPTIONS, default=d.get("d30"),
                                            key="w_d30", help=FH.HELP["late_30_59"])
            d["d60"] = st.segmented_control("60–89 days late *", LATE_OPTIONS, default=d.get("d60"),
                                            key="w_d60", help=FH.HELP["late_60_89"])
            d["d90"] = st.segmented_control("90 days or more late *", LATE_OPTIONS, default=d.get("d90"),
                                            key="w_d90", help=FH.HELP["late_90"])

    elif step == 3:
        _question("Income and existing debt", "Monthly figures, before tax.")
        d["income_unknown"] = st.toggle("Income wasn't declared", value=d.get("income_unknown", False),
                                        key="w_income_unknown", help=FH.HELP["income_not_declared"])
        if not d["income_unknown"]:
            c1, c2 = st.columns(2)
            d["income"] = c1.number_input("Monthly income *", min_value=0.0, value=d.get("income"), step=100.0,
                                          format="%.0f", placeholder="e.g. 5000", key="w_income",
                                          help=FH.HELP["income"])
            d["dti"] = c2.number_input("Debt-to-income (%) *", min_value=0.0, value=d.get("dti"), step=1.0,
                                       format="%.0f", placeholder="e.g. 30", key="w_dti", help=FH.HELP["dti"])
        d["re"] = st.segmented_control("Property loans (mortgages, home-equity lines) *", PROPERTY_OPTIONS,
                                       default=d.get("re"), key="w_re", help=FH.HELP["real_estate"])

    else:
        _question("Check the details", "Everything look right? Edit any section, or run the assessment.")
        a = _answers(d)
        late = ("Not available" if a["delinquency_unknown"] else
                f"{d.get('d30')} × 30–59 days, {d.get('d60')} × 60–89 days, {d.get('d90')} × 90+ days")
        income = ("Not declared" if a["income_unknown"] else
                  f"{a['monthly_income']:,.0f} a month · debt-to-income {a['debt_ratio_pct']:.0f}%")
        rows = [
            (0, "Applicant", d.get("name", "")),
            (1, "Credit utilisation", f"{a['utilization_pct']:.0f}%"),
            (2, "Late payments", late),
            (3, "Income & debt", f"{income} · property loans {d.get('re')}"),
        ]
        for target, label, value in rows:
            c1, c2 = st.columns([0.82, 0.18], vertical_alignment="center")
            c1.html(f'<div class="sb-review-row"><div class="sb-review-label">{label}</div>'
                    f'<div class="sb-review-value">{value}</div></div>')
            c2.button("Edit", key=f"edit_{target}", on_click=_go, args=(target,), use_container_width=True)


def render_form_page():
    _, _, cutoffs = score_range_and_cutoffs()
    d = _data()
    step = st.session_state.setdefault("step", 0)
    st.session_state.setdefault("step_error", None)

    form_col, live_col = st.columns([0.62, 0.38], gap="large")
    assess_clicked = False
    with form_col, st.container(key="form_card"):
        st.html(comp.stepper_html(STEPS, step))
        with st.container(key=f"step_body_{step}"):
            render_step(step, d)

        if st.session_state.step_error:
            st.html(f'<div class="sb-error-box"><b>Almost there:</b> {st.session_state.step_error}</div>')

        st.html('<div style="height:.6rem"></div>')
        back_col, next_col = st.columns(2)
        if step > 0:
            back_col.button("← Back", on_click=_go, args=(step - 1,), use_container_width=True, key="nav_back")
        if step < len(STEPS) - 1:
            if next_col.button("Continue →", type="primary", use_container_width=True, key="nav_next"):
                missing = _step_missing(step, d)
                if missing:
                    st.session_state.step_error = "please fill in " + ", ".join(missing) + "."
                else:
                    _go(step + 1)
                st.rerun()
        else:
            assess_clicked = next_col.button("Assess application", type="primary",
                                              use_container_width=True, key="nav_assess")

    # ---- live score panel ----
    a = _answers(d)
    progress = [
        ("Applicant", not _step_missing(0, d)),
        ("Credit usage", not _step_missing(1, d)),
        ("Payment history", not _step_missing(2, d)),
        ("Income & debt", not _step_missing(3, d)),
    ]
    preview = None
    if all(done for label, done in progress[1:]):
        row = build_row(**a)
        decision, _, _, _ = quick_score(row)
        preview = {"score": float(decision["score"]), "band": decision["band"],
                   "decision": decision["final_decision"], "flags": decision["triggered_rules"],
                   "pd_text": vm.PD_RANGE_TEXT.get(decision["band"], "")}
    with live_col, st.container(key="live_panel"):
        st.html(comp.live_panel_html(progress, preview, cutoffs))

    if assess_clicked:
        incomplete = [s for s in range(4) if _step_missing(s, d)]
        if incomplete:
            _go(incomplete[0])
            st.session_state.step_error = "a few answers are still missing on this step."
            st.rerun()

        reference = st.session_state.applicant_ref   # internal file number, generated automatically
        applicant_name = d["name"].strip()
        applicant_id = "live_applicant"
        row = build_row(applicant_id=applicant_id, **a)
        # `row` above is the ONLY applicant data passed to scoring and decisioning.
        # The applicant's name never leaves the app; the memo only receives the
        # random file reference so the memo can be filed against it.
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
            "economics": portfolio_view(),
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
        eco = a.get("economics")
        band_eco = next((r for r in (eco or {}).get("bands", []) if r["band"] == decision["band"]), None)
        if band_eco:
            st.html(f'<div class="sb-eco-note"><b>Expected loss for band {decision["band"]}:</b> about '
                    f'{band_eco["el_per_1000"]:.0f} for every {eco["per_amount"]:,} lent '
                    f'({band_eco["pd"]:.1%} default rate × {eco["lgd"]:.0%} lost on default). '
                    f'The PDF report shows how each approval cut-off would change this.</div>')

        st.html("<br>")
        with st.expander("Read the credit memo"):
            st.caption(a["memo_mode"])
            with st.container(key="memo_text"):
                st.markdown(a["memo"])

        st.html("<br>")
        if a["pdf_bytes"] is None:
            a["pdf_bytes"] = build_pdf_report(a)

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            st.download_button(
                "Download full report (PDF)", data=a["pdf_bytes"],
                file_name=f"{_report_filename(a.get('applicant_name', ''))}",
                mime="application/pdf", type="primary", use_container_width=True,
            )
        with bcol2:
            if st.button("Assess another application", use_container_width=True):
                st.session_state.page = "form"
                st.session_state.assessment = None
                st.session_state.applicant_ref = f"CR-{datetime.now().year}-{random.randint(0, 9999):04d}"
                # start the next application with a clean form
                for k in list(st.session_state.keys()):
                    if k.startswith(("f_", "w_", "wi_")) or k in ("app_data", "step", "step_error"):
                        del st.session_state[k]
                st.rerun()


def _report_filename(name: str) -> str:
    """'Priya Sharma' -> 'Priya Sharma Credit Report.pdf' (characters Windows
    won't allow in file names are removed)."""
    clean = re.sub(r'[\\/:*?"<>|]+', "", (name or "").strip())
    clean = re.sub(r"\s+", " ", clean).strip(" .")
    return f"{clean or 'Applicant'} Credit Report.pdf"


# ============================= ABOUT THE MODEL PAGE =============================
def render_about_page():
    with st.container(key="about_wrap"):
        st.markdown("## About the model")
        st.caption("How the credit scorecard works, how it performs, and the policies behind each decision.")

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

            st.markdown("#### Choosing the cut-off")
            eco = portfolio_view()
            st.caption(f"Measured on {eco['n_test']:,} test applicants. Expected loss = default rate × "
                       f"{eco['lgd']:.0%} loss given default (assumed) × amount lent, quoted per "
                       f"{eco['per_amount']:,} lent over two years.")
            cut_df = pd.DataFrame(eco["cutoffs"])
            cut_df = cut_df.assign(min_score=cut_df["min_score"].map(
                lambda v: "no floor" if v is None or v != v else f"{v:.0f}"))
            st.dataframe(
                cut_df[["policy", "min_score", "approval_rate", "bad_rate", "bads_avoided",
                        "goods_declined", "el_per_1000"]].rename(columns={
                    "policy": "Approval policy", "min_score": "Lowest score approved",
                    "approval_rate": "Share approved", "bad_rate": "Default rate of approved",
                    "bads_avoided": "Defaulters kept out", "goods_declined": "Good applicants turned away",
                    "el_per_1000": f"Expected loss per {eco['per_amount']:,}"}).style.format({
                    "Share approved": "{:.0%}", "Default rate of approved": "{:.1%}",
                    "Defaulters kept out": "{:.0%}", "Good applicants turned away": "{:.0%}",
                    f"Expected loss per {eco['per_amount']:,}": "{:.1f}"}),
                use_container_width=True, hide_index=True)
            band_df = pd.DataFrame(eco["bands"])[["band", "decision", "share", "pd", "el_per_1000"]].rename(columns={
                "band": "Band", "decision": "Standard decision", "share": "Share of applicants",
                "pd": "Default rate", "el_per_1000": f"Expected loss per {eco['per_amount']:,} lent"})
            st.dataframe(band_df.style.format({"Share of applicants": "{:.1%}", "Default rate": "{:.1%}",
                                               f"Expected loss per {eco['per_amount']:,} lent": "{:.1f}"}),
                         use_container_width=True, hide_index=True)

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
