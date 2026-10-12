"""HTML builders for the Streamlit result page. Each function returns a
plain HTML string to be rendered via st.html (no JavaScript needed)."""
import html as _html

from ui.theme import BAND_TINTS, BAND_FULL
from ui.view_model import STAMP_TEXT, NEXT_STEP, DECISION_CLASS, PD_RANGE_TEXT


def esc(text) -> str:
    return _html.escape(str(text))


def top_bar_title_html() -> str:
    """Rendered inside the real st.container(key='topbar') alongside the
    segmented_control widget -- not a standalone bar, since the control
    itself must be an interactive Streamlit widget, not static HTML."""
    return (
        '<div class="sb-topbar-title">Sample Bank</div>'
        '<div class="sb-topbar-sub">Credit assessment &middot; fictional lender, portfolio project</div>'
    )


def band_ruler_html(score: float, band: str, cutoffs: dict, score_min: float, score_max: float) -> str:
    lo = min(score_min, score, min(cutoffs.values())) - 5
    hi = max(score_max, score, max(cutoffs.values())) + 5
    span = hi - lo
    edges = [lo, cutoffs["D"], cutoffs["C"], cutoffs["B"], cutoffs["A"], hi]
    order = ["E", "D", "C", "B", "A"]

    segs = ""
    labels = ""
    for i, letter in enumerate(order):
        width_pct = max(0.0, (edges[i + 1] - edges[i]) / span) * 100
        bg = BAND_FULL[letter] if letter == band else BAND_TINTS[letter]
        fg = "#fff" if letter == band else "var(--muted)"
        lo_i, hi_i = round(edges[i]), round(edges[i + 1])
        range_text = f"{lo_i}+" if letter == "A" else (f"&le;{hi_i}" if letter == "E" else f"{lo_i}-{hi_i}")
        segs += f'<div class="sb-ruler-seg" style="flex-basis:{width_pct}%; background:{bg}; color:{fg};">{letter}</div>'
        labels += f'<div class="sb-ruler-label" style="flex-basis:{width_pct}%;">{range_text}</div>'

    marker_pct = max(0.0, min(100.0, (score - lo) / span * 100))
    return f"""
    <div class="sb-ruler-wrap">
        <div class="sb-ruler-pin" style="left:{marker_pct}%;">
            <div class="sb-ruler-pin-score">{score:.0f}</div>
            <div class="sb-ruler-pin-mark">&#9660;</div>
        </div>
        <div class="sb-ruler">{segs}</div>
        <div class="sb-ruler-labels">{labels}</div>
    </div>
    """


def application_file_card_html(reference: str, assessed_at: str, applicant_name: str,
                                final_decision: str, score: float, band: str,
                                cutoffs: dict, score_min: float, score_max: float) -> str:
    decision_class = DECISION_CLASS.get(final_decision, "caution")
    stamp_text = STAMP_TEXT.get(final_decision, final_decision.upper())
    next_step = NEXT_STEP.get(final_decision, "")
    pd_text = PD_RANGE_TEXT.get(band, "")

    return f"""
    <div class="sb-file-card">
        <div class="sb-stamp {decision_class}">{esc(stamp_text)}</div>
        <div class="sb-file-meta">Application {esc(reference)} &middot; Assessed {esc(assessed_at)}</div>
        <div class="sb-file-name">{esc(applicant_name)}</div>
        <div class="sb-next-step">{esc(next_step)}</div>

        <div class="sb-figures">
            <div>
                <div class="sb-figure-label">Score</div>
                <div class="sb-figure-value">{score:.0f}</div>
            </div>
            <div>
                <div class="sb-figure-label">Risk band</div>
                <div class="sb-figure-value">{esc(band)}</div>
            </div>
            <div>
                <div class="sb-figure-label">Estimated default risk</div>
                <div class="sb-figure-value small">{esc(pd_text)}</div>
            </div>
        </div>
        {band_ruler_html(score, band, cutoffs, score_min, score_max)}
    </div>
    """


def characteristic_item_html(row: dict) -> str:
    pct = round(row["bar_fraction"] * 100)
    return f"""
    <div class="sb-item">
        <div class="sb-item-name">{esc(row['name'])}</div>
        <div class="sb-item-value">{esc(row['value_text'])}</div>
        <div class="sb-bar-track"><div class="sb-bar-fill" style="width:{pct}%;"></div></div>
    </div>
    """


def characteristics_column_html(title: str, rows: list) -> str:
    items = "".join(characteristic_item_html(r) for r in rows)
    return f'<div class="sb-column-title">{esc(title)}</div>{items}'


def policy_checks_column_html(notes: list) -> str:
    if not notes:
        return ('<div class="sb-column-title">Policy checks</div>'
                '<div class="sb-policy-none">No policy rules were triggered.</div>')
    items = "".join(
        f'<div class="sb-policy-note"><b>{esc(rule_id)}:</b> {esc(text)}</div>'
        for rule_id, text in notes
    )
    return f'<div class="sb-column-title">Policy checks</div>{items}'


def drawer_html(rows: list, base_points: int, total_score: float) -> str:
    drawer_rows = ""
    for r in rows:
        pct = round(r["bar_fraction"] * 100)
        title = f"Earned {r['points_earned']} of {r['best_possible']} possible points"
        drawer_rows += f"""
        <div class="sb-drawer-row" title="{esc(title)}">
            <div>{esc(r['name'])}</div>
            <div style="color:var(--muted);">{esc(r['value_text'])}</div>
            <div class="sb-bar-track"><div class="sb-bar-fill" style="width:{pct}%;"></div></div>
            <div class="sb-drawer-points">{r['points_earned']}</div>
        </div>
        """
    return f"""
    <details class="sb-details">
        <summary><span class="sb-chevron">&#9656;</span> Why this decision?</summary>
        <div style="margin-top:0.75rem;">
            {drawer_rows}
            <div style="margin-top:0.75rem; color:var(--muted); font-size:0.82rem;">
                Base points: {base_points}. Score = base points + points earned on each characteristic
                ({base_points} + {total_score - base_points:.0f} = {total_score:.0f}).
            </div>
        </div>
    </details>
    """
