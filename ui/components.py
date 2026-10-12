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
        '<div class="sb-brand"><div class="sb-logo">'
        '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#fff" stroke-width="2.2" '
        'stroke-linecap="round" aria-hidden="true"><path d="M4 17a8 8 0 0 1 16 0"/>'
        '<path d="M12 17l4.2-5.2"/><circle cx="12" cy="17" r="1.3" fill="#fff" stroke="none"/></svg></div><div>'
        '<div class="sb-topbar-title">Credit Assessment</div>'
        '<div class="sb-topbar-sub">Retail credit decisioning</div></div></div>'
    )


def stepper_html(steps, current: int) -> str:
    """Progress strip across the top of the wizard: finished steps get a tick,
    the current one is outlined, later ones stay grey."""
    items = []
    for i, label in enumerate(steps):
        state = "done" if i < current else ("current" if i == current else "todo")
        mark = "&#10003;" if i < current else str(i + 1)
        items.append(
            f'<div class="sb-step sb-step-{state}"><div class="sb-step-dot">{mark}</div>'
            f'<div class="sb-step-label">{esc(label)}</div></div>'
        )
    pct = int(round(100 * current / max(len(steps) - 1, 1)))
    return (f'<div class="sb-stepper" style="--sb-step-pct:{pct}%">'
            f'<div class="sb-stepper-track"><div class="sb-stepper-fill"></div></div>'
            + "".join(items) + "</div>")


def ruler_scale(score: float, cutoffs: dict):
    """Score window for the A-E ruler. Bands E and A are open-ended, so they get a
    fixed visual width instead of stretching to the most extreme test score."""
    lo = min(cutoffs["D"] - 45, score - 8)
    hi = max(cutoffs["A"] + 30, score + 8)
    return lo, hi


def ruler_segments(score: float, cutoffs: dict):
    """(letter, width fraction, range label) for E, D, C, B, A -- shared with the PDF."""
    lo, hi = ruler_scale(score, cutoffs)
    edges = [lo, cutoffs["D"], cutoffs["C"], cutoffs["B"], cutoffs["A"], hi]
    labels = {
        "E": f"{cutoffs['D'] - 1} and below",
        "D": f"{cutoffs['D']}\u2013{cutoffs['C'] - 1}",
        "C": f"{cutoffs['C']}\u2013{cutoffs['B'] - 1}",
        "B": f"{cutoffs['B']}\u2013{cutoffs['A'] - 1}",
        "A": f"{cutoffs['A']} and above",
    }
    out = []
    for i, letter in enumerate(["E", "D", "C", "B", "A"]):
        out.append((letter, (edges[i + 1] - edges[i]) / (hi - lo), labels[letter]))
    return out, (score - lo) / (hi - lo)


def band_ruler_html(score: float, band: str, cutoffs: dict, score_min: float = None, score_max: float = None) -> str:
    segments, marker = ruler_segments(score, cutoffs)
    segs = ""
    labels = ""
    for letter, frac, range_text in segments:
        width_pct = frac * 100
        active = letter == band
        bg = BAND_FULL[letter] if active else BAND_TINTS[letter]
        fg = "#fff" if active else "var(--muted)"
        segs += (f'<div class="sb-ruler-seg{" active" if active else ""}" '
                 f'style="flex-basis:{width_pct:.2f}%; background:{bg}; color:{fg};">{letter}</div>')
        labels += f'<div class="sb-ruler-label" style="flex-basis:{width_pct:.2f}%;">{esc(range_text)}</div>'

    marker_pct = max(0.0, min(100.0, marker * 100))
    return f"""
    <div class="sb-ruler-wrap">
        <div class="sb-ruler-pin" style="left:{marker_pct:.2f}%;">
            <div class="sb-ruler-pin-score">{score:.0f}</div>
            <div class="sb-ruler-pin-mark"></div>
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
        <div class="sb-stamp {decision_class}{' long' if len(stamp_text) > 14 else ''}">{esc(stamp_text)}</div>
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


# ============================= interactive pieces =============================
def _polar(cx, cy, r, deg):
    import math
    t = math.radians(deg)
    return cx + r * math.cos(t), cy - r * math.sin(t)


def dial_svg(score, band, cutoffs, width=300, hub_label="points") -> str:
    """Half-donut score dial: five band arcs (E→A, left→right) and a needle at the score.
    Pure SVG, so it renders through st.html with no JavaScript."""
    from ui.theme import DIAL
    segments, marker = ruler_segments(score, cutoffs)
    cx, cy, ro, ri = 150, 140, 120, 80
    paths, labels = "", ""
    angle = 180.0
    for letter, frac, _ in segments:
        sweep = frac * 180.0
        a1, a2 = angle, angle - sweep
        x1, y1 = _polar(cx, cy, ro, a1)
        x2, y2 = _polar(cx, cy, ro, a2)
        x3, y3 = _polar(cx, cy, ri, a2)
        x4, y4 = _polar(cx, cy, ri, a1)
        active = letter == band
        paths += (f'<path d="M{x1:.1f},{y1:.1f} A{ro},{ro} 0 0 1 {x2:.1f},{y2:.1f} '
                  f'L{x3:.1f},{y3:.1f} A{ri},{ri} 0 0 0 {x4:.1f},{y4:.1f} Z" fill="{DIAL[letter]}" '
                  f'opacity="{1 if active else 0.55}" stroke="#fff" stroke-width="2"/>')
        lx, ly = _polar(cx, cy, (ro + ri) / 2, angle - sweep / 2)
        labels += (f'<text x="{lx:.1f}" y="{ly + 5:.1f}" text-anchor="middle" font-size="{15 if active else 12}" '
                   f'font-weight="{700 if active else 600}" fill="#fff" font-family="Public Sans, sans-serif">{letter}</text>')
        angle -= sweep
    needle_deg = 180.0 - max(0.0, min(1.0, marker)) * 180.0
    # needle drawn pointing right (0deg) and rotated, so the CSS transition can animate it
    rot = -needle_deg
    return f"""
    <svg viewBox="0 0 300 208" width="{width}" role="img" aria-label="Score {score:.0f}, band {band}">
      {paths}{labels}
      <g class="sb-needle" style="transform-origin:{cx}px {cy}px; transform: rotate({rot:.1f}deg);">
        <line x1="{cx}" y1="{cy}" x2="{cx + ro + 6}" y2="{cy}" stroke="#16262A" stroke-width="5" stroke-linecap="round"/>
      </g>
      <circle cx="{cx}" cy="{cy}" r="9" fill="#16262A"/><circle cx="{cx}" cy="{cy}" r="4" fill="#B8872B"/>
      <text x="{cx}" y="{cy + 46}" text-anchor="middle" font-size="34" font-weight="600" fill="#16262A"
            font-family="Lora, Georgia, serif">{score:.0f}</text>
      <text x="{cx}" y="{cy + 63}" text-anchor="middle" font-size="11" fill="#586C70"
            font-family="Public Sans, sans-serif">{hub_label}</text>
    </svg>"""


def _chip(text, color, fill=False):
    style = f"background:{color};border-color:{color};" if fill else f"color:{color};"
    return f'<span class="sb-chip{" fill" if fill else ""}" style="{style}">{esc(text)}</span>'


def live_panel_html(progress, preview, cutoffs) -> str:
    """Right-hand panel on the form. progress: [(label, done_bool)].
    preview: None until every scoring field is answered, then
    {score, band, decision, flags: [rule ids], pd_text}."""
    from ui.theme import COLORS
    done = sum(1 for _, d in progress if d)
    total = len(progress)
    head = ('<div class="sb-live-title">Live score</div>'
            '<div class="sb-live-sub">Updates as you fill in the form.</div>')
    if preview is None:
        items = "".join(f'<li class="{"done" if d else ""}">{esc(label)}</li>' for label, d in progress)
        return (head + f'<div class="sb-progress"><div style="width:{done / total * 100:.0f}%"></div></div>'
                f'<div class="sb-live-sub">{done} of {total} answers</div><ul class="sb-todo">{items}</ul>'
                '<div class="sb-live-note">The score appears once every required field is answered.</div>')
    tone = DECISION_CLASS.get(preview["decision"], "caution")
    tone_color = COLORS[tone]
    chips = _chip(f"Band {preview['band']}", tone_color, fill=True) + _chip(f"Default risk {preview['pd_text']}", tone_color)
    if preview["flags"]:
        chips += _chip(f"{len(preview['flags'])} policy flag{'s' if len(preview['flags']) > 1 else ''}: "
                       + ", ".join(preview["flags"]), COLORS["caution"])
    else:
        chips += _chip("No policy flags", COLORS["approve"])
    return (head + f'<div class="sb-live-dial">{dial_svg(preview["score"], preview["band"], cutoffs)}</div>'
            f'<div class="sb-live-decision" style="color:{tone_color}">Likely outcome: {esc(preview["decision"])}</div>'
            f'<div class="sb-live-chips">{chips}</div>'
            '<div class="sb-live-note">Provisional. Press “Assess application” for the full decision, '
            'reasons and credit memo.</div>')


def whatif_html(base_score, new_score, base_band, new_band, new_decision, cutoffs) -> str:
    from ui.theme import COLORS
    diff = round(new_score - base_score)
    cls = "up" if diff > 0 else ("down" if diff < 0 else "")
    sign = f"+{diff}" if diff > 0 else str(diff)
    tone_color = COLORS[DECISION_CLASS.get(new_decision, "caution")]
    band_line = (f"Band {base_band} → <b>{new_band}</b>" if new_band != base_band else f"Still band {new_band}")
    return (f'<div class="sb-live-dial">{dial_svg(new_score, new_band, cutoffs, hub_label="what-if score")}</div>'
            f'<div class="sb-delta"><div class="sb-delta-score">{base_score:.0f} → {new_score:.0f} '
            f'<span class="{cls}">({sign})</span></div>'
            f'<div class="sb-delta-line">{band_line} · <span style="color:{tone_color};font-weight:600">'
            f'{esc(new_decision)}</span></div></div>')
