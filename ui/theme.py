"""Design tokens and injected CSS for the 'underwriter's desk' theme."""

COLORS = {
    # soft teal replaces the original deep ledger green; brass stays as the single accent
    "ledger": "#1F6F78",
    "ledger_hover": "#185C64",
    "paper": "#F2F6F6",
    "white": "#FFFFFF",
    "ink": "#16262A",
    "muted": "#586C70",
    "rule": "#D8E4E5",
    "brass": "#B8872B",
    "approve": "#2E8A62", "approve_tint": "#E3F3EC",
    "caution": "#B7791F", "caution_tint": "#FBF1DE",
    "decline": "#B42318", "decline_tint": "#FBE7E5",
    "input_fill": "#FAFCFC",
    "top_bar_sub": "#BFDCDF",
    "teal_tint": "#E4F1F2",
}

# E -> A, pale tint to full decision colour, used for the band ruler
BAND_TINTS = {
    "E": "#FBE7E5", "D": "#FDEEDB", "C": "#FBF1DE", "B": "#E9F5EE", "A": "#E3F3EC",
}
# score dial, warm (higher risk) to green (lower risk)
DIAL = {"E": "#C0392B", "D": "#DC7F3A", "C": "#E5B74A", "B": "#7DBE95", "A": "#2E8A62"}

BAND_FULL = {
    "E": "#B42318", "D": "#B7791F", "C": "#B7791F", "B": "#2E8A62", "A": "#2E8A62",
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Nunito+Sans:ital,wght@0,400;0,600;1,400&family=Public+Sans:wght@400;500;600&display=swap');

:root {{
    --ledger: {COLORS['ledger']}; --ledger-hover: {COLORS['ledger_hover']};
    --paper: {COLORS['paper']}; --white: {COLORS['white']}; --ink: {COLORS['ink']};
    --muted: {COLORS['muted']}; --rule: {COLORS['rule']}; --brass: {COLORS['brass']};
}}

/* ---- hide Streamlit chrome ---- */
#MainMenu, header[data-testid="stHeader"], div[data-testid="stToolbar"],
div[data-testid="stDecoration"], footer, section[data-testid="stSidebar"] {{
    visibility: hidden; height: 0; display: none;
}}
div[data-testid="stAppViewContainer"] {{ padding-top: 0 !important; }}

html, body, [class*="css"] {{
    font-family: 'Public Sans', sans-serif; color: var(--ink); background: var(--paper);
}}
.stApp {{ background: var(--paper); }}
h1, h2, h3, .sb-lora {{ font-family: 'Lora', serif; }}

.block-container {{ padding-top: 0 !important; padding-bottom: 3rem; max-width: 1200px; }}

/* ---- top bar (a real st.container(key="topbar"), full-bleed) ---- */
.st-key-topbar {{
    background: var(--ledger); border-bottom: 3px solid var(--brass);
    width: 100vw !important; max-width: 100vw !important; box-sizing: border-box;
    margin: 0 0 2rem calc(50% - 50vw) !important;
    padding: 1rem max(1.5rem, calc(50vw - 600px)) !important;
}}
section.main, [data-testid="stMain"], [data-testid="stAppViewContainer"] {{ overflow-x: hidden; }}
.st-key-topbar div[data-testid="stHorizontalBlock"] {{ align-items: center; }}
.sb-topbar-title {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.3rem; color: #fff; }}
.sb-topbar-sub {{ font-size: 0.82rem; color: {COLORS['top_bar_sub']}; margin-top: 0.1rem; }}
.st-key-topbar div[data-testid="stMarkdownContainer"] {{ color: #fff; }}
.sb-brand {{ display: flex; align-items: center; gap: 0.8rem; }}
.sb-logo {{
    width: 2.4rem; height: 2.4rem; border-radius: 8px; background: var(--brass); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Lora', serif; font-weight: 600; font-size: 1rem; letter-spacing: 0.02em;
    background-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2.2' stroke-linecap='round'%3E%3Cpath d='M4 17a8 8 0 0 1 16 0'/%3E%3Cpath d='M12 17l4.2-5.2'/%3E%3Ccircle cx='12' cy='17' r='1.4' fill='white' stroke='none'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: center;
    background-size: 1.45rem;
}}

/* Segmented controls (Streamlit renders them as a button group). Topbar version: white on green. */
.st-key-topbar button {{
    background: transparent !important; border: 1px solid rgba(255,255,255,0.55) !important;
    color: #fff !important; border-radius: 5px !important;
}}
.st-key-topbar button p {{ color: inherit !important; }}
.st-key-topbar button[kind$="Active"], .st-key-topbar button[data-testid$="Active"],
.st-key-topbar button[aria-checked="true"] {{
    background: #fff !important; color: var(--ledger) !important; border-color: #fff !important;
}}
/* selected tab: white pill with dark teal text (text lives in a markdown container, so colour it too) */
.st-key-topbar button[kind$="Active"] *, .st-key-topbar button[data-testid$="Active"] *,
.st-key-topbar button[aria-checked="true"] * {{ color: var(--ledger) !important; font-weight: 600; }}
/* Form version: answer chips (0, 1, 2 ...) that fill green when picked. */
.st-key-form_card div[data-testid="stButtonGroup"] button {{
    min-width: 2.8rem; border-radius: 5px !important; background: #FAFBFA !important;
    border: 1px solid var(--rule) !important; color: var(--ink) !important; transition: all .12s ease;
}}
.st-key-form_card div[data-testid="stButtonGroup"] button:hover {{ border-color: var(--brass) !important; color: var(--ledger) !important; }}
.st-key-form_card div[data-testid="stButtonGroup"] button[kind$="Active"],
.st-key-form_card div[data-testid="stButtonGroup"] button[data-testid$="Active"] {{
    background: var(--ledger) !important; border-color: var(--ledger) !important; color: #fff !important;
}}
.st-key-form_card div[data-testid="stButtonGroup"] button[kind$="Active"] p,
.st-key-form_card div[data-testid="stButtonGroup"] button[data-testid$="Active"] p {{ color: #fff !important; }}
/* toggles */
.stApp label[data-baseweb="checkbox"] > div:first-child {{ transition: background .15s ease; }}

/* ---- live score panel (form page) ---- */
.st-key-live_panel {{
    position: sticky; top: 1rem; background: var(--white); border: 1px solid var(--rule);
    border-radius: 8px; padding: 1.4rem 1.4rem 1.2rem; box-shadow: 0 2px 14px rgba(31,111,120,0.08);
}}
.sb-live-title {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.15rem; }}
.sb-live-sub {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 0.6rem; }}
.sb-live-dial {{ display: flex; justify-content: center; margin: 0.2rem 0 0.4rem; }}
.sb-live-dial svg, .sb-live-dial img {{ width: 100%; max-width: 300px; height: auto; }}
.sb-live-dial svg .sb-needle {{ transition: transform .45s cubic-bezier(.3,1.3,.5,1); }}
.sb-live-decision {{ text-align: center; font-weight: 600; font-size: 0.95rem; margin-top: .2rem; }}
.sb-live-chips {{ display: flex; flex-wrap: wrap; gap: .35rem; justify-content: center; margin: .6rem 0 .2rem; }}
.sb-chip {{ display: inline-block; padding: .18rem .6rem; border-radius: 999px; font-size: .76rem; font-weight: 600; border: 1px solid currentColor; }}
.sb-chip.fill {{ color: #fff !important; }}
.sb-progress {{ height: 8px; background: var(--rule); border-radius: 999px; overflow: hidden; margin: .5rem 0 .4rem; }}
.sb-progress > div {{ height: 100%; background: linear-gradient(90deg, var(--brass), var(--ledger)); border-radius: 999px; transition: width .3s ease; }}
.sb-todo {{ list-style: none; padding: 0; margin: .4rem 0 0; font-size: .84rem; }}
.sb-todo li {{ padding: .22rem 0; color: var(--muted); }}
.sb-todo li.done {{ color: {COLORS['approve']}; }}
.sb-todo li::before {{ content: "○"; display: inline-block; width: 1.2rem; color: var(--rule); }}
.sb-todo li.done::before {{ content: "●"; color: {COLORS['approve']}; }}
.sb-live-note {{ color: var(--muted); font-size: .74rem; text-align: center; margin-top: .6rem; }}

/* ---- what-if simulator (result page) ---- */
.st-key-whatif {{
    background: var(--white); border: 1px solid var(--rule); border-radius: 8px; padding: 1.5rem 1.8rem;
    box-shadow: 0 2px 10px rgba(31,111,120,0.06); max-width: 860px; margin: 0 auto;
}}
.st-key-whatif div[data-testid="stSlider"] div[role="slider"] {{ background: var(--ledger) !important; border-color: var(--ledger) !important; }}
.sb-whatif-title {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.25rem; }}
.sb-whatif-sub {{ color: var(--muted); font-size: .85rem; margin-bottom: .4rem; }}
.sb-delta {{ text-align: center; margin-top: .2rem; }}
.sb-delta-score {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.05rem; }}
.sb-delta-score .up {{ color: {COLORS['approve']}; }} .sb-delta-score .down {{ color: {COLORS['decline']}; }}
.sb-delta-line {{ color: var(--muted); font-size: .82rem; margin-top: .15rem; }}

/* ---- cards ----
   st.container(key=...) really nests its children in the DOM (unlike two
   separate st.html('<div>')/st.html('</div>') calls, which do NOT nest
   the widgets rendered between them) -- so card chrome is applied to the
   .st-key-<name> wrapper around the real Streamlit widgets, not to a
   hand-written div pair. */
.st-key-form_card {{
    background: var(--white); border: 1px solid var(--rule); border-radius: 6px;
    padding: 2.25rem 2.5rem; box-shadow: 0 2px 10px rgba(31,111,120,0.07);
    max-width: 100%; margin: 0;
}}
.st-key-result_wrap {{ max-width: 860px; margin: 0 auto; }}
.st-key-about_wrap {{ max-width: 980px; margin: 0 auto; }}
.sb-section-row {{ display: flex; gap: 1.25rem; padding: 1.25rem 0; border-top: 1px solid var(--rule); }}
.sb-section-row:first-of-type {{ border-top: none; padding-top: 0.25rem; }}
.sb-section-num {{
    font-family: 'Lora', serif; font-weight: 600; color: var(--brass); font-size: 1.1rem;
    width: 28px; flex-shrink: 0;
}}
.sb-section-title {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.12rem; margin-bottom: 0.1rem; color: var(--ink); }}
/* numbered section header: step badge + title, hairline above */
.sb-sec {{
    display: flex; align-items: flex-start; gap: 0.85rem;
    border-top: 1px solid var(--rule); padding-top: 1.2rem; margin-top: 0.9rem;
}}
.sb-sec-num {{
    flex: 0 0 auto; width: 1.9rem; height: 1.9rem; border-radius: 50%;
    background: {COLORS['teal_tint']}; color: var(--ledger); border: 1.5px solid var(--ledger);
    display: inline-flex; align-items: center; justify-content: center;
    font-family: 'Lora', serif; font-weight: 600; font-size: 0.95rem; margin-top: 0.05rem;
}}
.sb-slide-hint {{ color: var(--brass); font-size: 0.78rem; margin: -0.6rem 0 0.4rem; font-style: italic; }}
/* sliders: teal track and thumb, value bubble in teal */
div[data-testid="stSlider"] div[role="slider"] {{ box-shadow: 0 0 0 4px rgba(31,111,120,0.15) !important; }}
div[data-testid="stSliderThumbValue"] {{ color: var(--ledger) !important; font-weight: 600; }}
div[data-testid="stSliderTickBarMin"], div[data-testid="stSliderTickBarMax"] {{ color: var(--muted); font-size: 0.75rem; }}
/* number boxes: no +/- steppers, just a clean field */
div[data-testid="stNumberInput"] button {{ display: none !important; }}
div[data-testid="stNumberInput"] [data-baseweb="input"] > div {{ border-radius: 5px; }}
.st-key-form_card h3 {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.85rem; margin-bottom: 0; }}
.st-key-form_card div[data-testid="stCaptionContainer"] p {{ color: var(--muted); font-size: 0.92rem; }}
.st-key-form_card label p {{ font-size: 0.85rem !important; font-weight: 500 !important; }}
.sb-helper {{ color: var(--muted); font-size: 0.82rem; margin-bottom: 0.6rem; }}
.sb-note {{ color: var(--muted); font-size: 0.76rem; margin-top: 0.2rem; }}

/* ---- inputs ---- */
div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input {{
    background: {COLORS['input_fill']} !important; border: 1px solid var(--rule) !important;
    border-radius: 5px !important; color: var(--ink) !important;
}}
div[data-testid="stNumberInput"] input:focus, div[data-testid="stTextInput"] input:focus {{
    border-color: var(--brass) !important; box-shadow: 0 0 0 2px rgba(184,135,43,0.25) !important;
}}


.stButton > button[kind="primary"] {{
    background: var(--ledger) !important; border-color: var(--ledger) !important;
    border-radius: 5px !important; font-weight: 600 !important;
}}
.stButton > button[kind="primary"]:hover {{ background: var(--ledger-hover) !important; border-color: var(--ledger-hover) !important; }}
.stButton > button[kind="secondary"] {{ border-radius: 5px !important; border-color: var(--rule) !important; color: var(--ink) !important; }}

/* ---- application file card ---- */
.sb-file-card {{
    background: var(--white); border: 1px solid var(--rule); border-radius: 6px;
    padding: 2rem 2.5rem; box-shadow: 0 2px 10px rgba(31,111,120,0.07); position: relative; overflow: hidden;
    max-width: 860px; margin: 0 auto;
}}
.sb-file-meta {{ color: var(--muted); font-size: 0.78rem; }}
.sb-file-name {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.9rem; margin-top: 0.15rem; }}
.sb-next-step {{ color: var(--ink); font-size: 0.96rem; margin-top: 0.5rem; max-width: 58%; line-height: 1.5; }}

.sb-stamp {{
    position: absolute; top: 1.6rem; right: 2.2rem; font-family: 'Lora', serif; font-weight: 600;
    font-size: 1.35rem; letter-spacing: 0.04em; padding: 0.55rem 1.1rem; border-radius: 4px;
    border: 3px double; transform: rotate(-7deg); opacity: 0.9; mix-blend-mode: multiply;
    animation: sb-stamp-in 380ms cubic-bezier(0.34, 1.56, 0.64, 1);
    white-space: nowrap; max-width: 46%;
}}
.sb-stamp.long {{ font-size: 1rem; white-space: normal; text-align: center; line-height: 1.25; max-width: 210px; }}
@keyframes sb-stamp-in {{
    0% {{ transform: rotate(-7deg) scale(1.6); opacity: 0; }}
    100% {{ transform: rotate(-7deg) scale(1); opacity: 0.9; }}
}}
@media (prefers-reduced-motion: reduce) {{ .sb-stamp {{ animation: none; }} }}
.sb-stamp.approve {{ color: {COLORS['approve']}; border-color: {COLORS['approve']}; background: {COLORS['approve_tint']}; }}
.sb-stamp.caution {{ color: {COLORS['caution']}; border-color: {COLORS['caution']}; background: {COLORS['caution_tint']}; }}
.sb-stamp.decline {{ color: {COLORS['decline']}; border-color: {COLORS['decline']}; background: {COLORS['decline_tint']}; }}

.sb-figures {{ display: flex; gap: 2.5rem; margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--rule); }}
.sb-figure-label {{ color: var(--muted); font-size: 0.8rem; }}
.sb-figure-value {{ font-family: 'Lora', serif; font-weight: 600; font-size: 2.1rem; margin-top: 0.1rem; }}
.sb-figure-value.small {{ font-size: 1.3rem; }}

/* ---- band ruler ---- */
.sb-ruler-wrap {{ margin: 1.75rem 0 0.5rem 0; position: relative; padding-top: 1.6rem; }}
.sb-ruler {{ display: flex; height: 26px; border-radius: 5px; overflow: hidden; border: 1px solid var(--rule); }}
.sb-ruler-seg {{ display: flex; align-items: center; justify-content: center; font-size: 0.72rem; font-weight: 600; color: var(--ink); }}
.sb-ruler-labels {{ display: flex; margin-top: 4px; }}
.sb-ruler-label {{ font-size: 0.68rem; color: var(--muted); text-align: center; }}
.sb-ruler-pin {{ position: absolute; top: 0; transform: translateX(-50%); text-align: center; }}
.sb-ruler-pin-score {{ font-family: 'Lora', serif; font-weight: 600; font-size: 0.82rem; color: var(--ink); white-space: nowrap; }}
.sb-ruler-pin-mark {{ width: 2px; height: 12px; background: var(--brass); margin: 2px auto 0; border-radius: 1px; }}
.sb-ruler-seg.active {{ font-weight: 700; font-size: 0.8rem; }}

/* ---- reason / policy items ---- */
.sb-item {{ padding: 0.7rem 0; border-top: 1px solid var(--rule); }}
.sb-item:first-child {{ border-top: none; }}
.sb-item-name {{ font-weight: 600; font-size: 0.9rem; }}
.sb-item-value {{ color: var(--muted); font-size: 0.84rem; margin: 0.1rem 0 0.4rem 0; }}
.sb-bar-track {{ background: var(--rule); border-radius: 3px; height: 6px; width: 100%; overflow: hidden; }}
.sb-bar-fill {{ background: var(--brass); height: 100%; }}

.sb-policy-note {{
    border-left: 3px solid var(--brass); background: {COLORS['caution_tint']};
    padding: 0.6rem 0.8rem; border-radius: 0 4px 4px 0; font-size: 0.86rem; margin-bottom: 0.6rem;
}}
.sb-policy-note b {{ color: var(--caution); }}
.sb-policy-none {{ color: var(--muted); font-size: 0.88rem; }}

.sb-column-title {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 0.5rem; }}

/* ---- drawer rows ---- */
.sb-drawer-row {{ display: grid; grid-template-columns: 1.4fr 1.6fr 1fr 60px; gap: 0.75rem; align-items: center;
    padding: 0.55rem 0; border-top: 1px solid var(--rule); font-size: 0.84rem; }}
.sb-drawer-row:first-child {{ border-top: none; }}
.sb-drawer-points {{ text-align: right; font-weight: 600; }}
details.sb-details summary {{ cursor: pointer; font-weight: 600; list-style: none; display: flex; align-items: center; gap: 0.4rem; }}
details.sb-details summary::-webkit-details-marker {{ display: none; }}
details.sb-details summary .sb-chevron {{ transition: transform 150ms ease; display: inline-block; color: var(--brass); }}
details.sb-details[open] summary .sb-chevron {{ transform: rotate(90deg); }}

/* ---- tabs ---- */
button[data-baseweb="tab"] {{ font-weight: 500 !important; }}
div[data-baseweb="tab-highlight"] {{ background-color: var(--brass) !important; }}
div[data-baseweb="tab-border"] {{ background-color: var(--rule) !important; }}

.sb-tile {{ background: var(--white); border: 1px solid var(--rule); border-radius: 6px; padding: 1.25rem 1.5rem; text-align: center; }}
.sb-tile-label {{ color: var(--muted); font-size: 0.78rem; }}
.sb-tile-value {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.9rem; margin-top: 0.15rem; }}

.sb-error-box {{
    background: {COLORS['decline_tint']}; border-left: 3px solid {COLORS['decline']};
    color: var(--ink); padding: 0.7rem 0.9rem; border-radius: 0 4px 4px 0; font-size: 0.88rem; margin-top: 0.6rem;
}}
.sb-error-box b {{ color: {COLORS['decline']}; }}
/* (?) help icons beside field labels: brass so they read as an invitation, not decoration */
div[data-testid="stTooltipIcon"] svg, div[data-testid="stTooltipHoverTarget"] svg {{ color: var(--brass) !important; stroke: var(--brass); }}
div[data-testid="stTooltipContent"] {{ font-size: 0.86rem; line-height: 1.5; max-width: 340px; }}
/* empty-field placeholders */
.stApp input::placeholder {{ color: #9AA8A3 !important; opacity: 1; }}
/* body copy rhythm */
.stApp p, .stApp li {{ line-height: 1.55; }}
.sb-error {{ color: {COLORS['decline']}; font-size: 0.85rem; margin-top: 0.3rem; }}
/* ---- step-by-step wizard ---- */
.sb-stepper {{ position: relative; display: flex; justify-content: space-between; margin: 0.2rem 0 1.6rem; }}
.sb-stepper-track {{ position: absolute; top: 15px; left: 10%; right: 10%; height: 3px; background: var(--rule); border-radius: 2px; }}
.sb-stepper-fill {{ height: 100%; width: var(--sb-step-pct); background: var(--ledger); border-radius: 2px; transition: width .35s ease; }}
.sb-step {{ position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column; align-items: center; gap: 0.4rem; }}
.sb-step-dot {{
    width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: 0.85rem; background: var(--white); border: 2px solid var(--rule); color: var(--muted);
    transition: all .25s ease;
}}
.sb-step-label {{ font-size: 0.74rem; color: var(--muted); text-align: center; line-height: 1.2; }}
.sb-step-done .sb-step-dot {{ background: var(--ledger); border-color: var(--ledger); color: #fff; }}
.sb-step-current .sb-step-dot {{ border-color: var(--ledger); color: var(--ledger); box-shadow: 0 0 0 5px {COLORS['teal_tint']}; }}
.sb-step-current .sb-step-label {{ color: var(--ink); font-weight: 600; }}
.sb-step-done .sb-step-label {{ color: var(--ledger); }}
.sb-q-title {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.5rem; color: var(--ink); margin: 0 0 0.3rem; line-height: 1.25; }}
.sb-q-help {{ color: var(--muted); font-size: 0.92rem; margin: 0 0 1.1rem; max-width: 60ch; }}
.sb-review-label {{ color: var(--muted); font-size: 0.8rem; }}
.sb-review-value {{ font-weight: 600; font-size: 0.98rem; color: var(--ink); }}
.sb-review-row {{ border-bottom: 1px solid var(--rule); padding: 0.55rem 0; }}
div[class*="st-key-step_body_"] {{ animation: sbStepIn .28s ease-out both; }}
@keyframes sbStepIn {{ from {{ opacity: 0; transform: translateX(14px); }} to {{ opacity: 1; transform: none; }} }}
@media (prefers-reduced-motion: reduce) {{
    div[class*="st-key-step_body_"] {{ animation: none; }}
    .sb-stepper-fill, .sb-step-dot {{ transition: none; }}
}}
@media (max-width: 640px) {{ .sb-step-label {{ font-size: 0.66rem; }} .sb-q-title {{ font-size: 1.25rem; }} }}
/* ---- credit memo: softer, rounder reading face ---- */
.st-key-memo_text p, .st-key-memo_text li, .st-key-memo_text td, .st-key-memo_text th {{
    font-family: 'Nunito Sans', 'Public Sans', sans-serif !important; font-weight: 400;
    color: #3B4D51 !important; font-size: 1rem; line-height: 1.7;
}}
.st-key-memo_text strong, .st-key-memo_text b {{ font-weight: 600; color: var(--ink); }}
.st-key-memo_text h1, .st-key-memo_text h2, .st-key-memo_text h3 {{
    font-family: 'Lora', serif; color: var(--ledger); font-weight: 600; margin: 1.1rem 0 .3rem; padding: 0;
}}
.st-key-memo_text h1 {{ font-size: 1.3rem; }} .st-key-memo_text h2 {{ font-size: 1.15rem; }} .st-key-memo_text h3 {{ font-size: 1.05rem; }}
.st-key-memo_text li::marker {{ color: var(--brass); }}
.sb-eco-note {{
    background: {COLORS['teal_tint']}; border-left: 3px solid var(--ledger); border-radius: 0 6px 6px 0;
    padding: .7rem 1rem; font-size: .9rem; color: var(--ink); margin-top: .9rem;
}}
.sb-eco-note b {{ color: var(--ledger); }}
.sb-calc {{
    display: inline-block; background: {COLORS['teal_tint']}; color: var(--ink); border-radius: 999px;
    padding: .35rem .9rem; font-size: .88rem; margin-top: .2rem;
}}
.sb-calc b {{ color: var(--ledger); }}
.sb-sample-title {{ margin-top: 1.6rem; padding-top: 1.1rem; border-top: 1px dashed var(--rule);
    font-weight: 600; font-size: .9rem; color: var(--ink); }}
.sb-sample-sub {{ color: var(--muted); font-size: .8rem; margin-bottom: .2rem; }}
.st-key-samples button {{ border-radius: 999px !important; border: 1px solid var(--ledger) !important;
    color: var(--ledger) !important; background: #fff !important; font-size: .85rem !important; }}
.st-key-samples button p {{ color: var(--ledger) !important; }}
.st-key-samples button:hover {{ background: {COLORS['teal_tint']} !important; }}
</style>
"""
