"""Design tokens and injected CSS for the 'underwriter's desk' theme."""

COLORS = {
    "ledger": "#0F3D2E",
    "ledger_hover": "#1C5240",
    "paper": "#F3F5F4",
    "white": "#FFFFFF",
    "ink": "#18221E",
    "muted": "#5B6B66",
    "rule": "#DCE3E0",
    "brass": "#B8872B",
    "approve": "#1F7A4D", "approve_tint": "#E6F2EC",
    "caution": "#B7791F", "caution_tint": "#FBF1DE",
    "decline": "#B42318", "decline_tint": "#FBE7E5",
    "input_fill": "#FAFBFA",
    "top_bar_sub": "#A9C4B8",
}

# E -> A, pale tint to full decision colour, used for the band ruler
BAND_TINTS = {
    "E": "#FBE7E5", "D": "#FDEEDB", "C": "#FBF1DE", "B": "#EAF4EE", "A": "#E6F2EC",
}
BAND_FULL = {
    "E": "#B42318", "D": "#B7791F", "C": "#B7791F", "B": "#1F7A4D", "A": "#1F7A4D",
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Public+Sans:wght@400;500;600&display=swap');

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

.block-container {{ padding-top: 0 !important; padding-bottom: 3rem; max-width: 1040px; }}

/* ---- top bar (a real st.container(key="topbar"), full-bleed) ---- */
.st-key-topbar {{
    background: var(--ledger); border-bottom: 3px solid var(--brass);
    margin: 0 calc(-50vw + 50%) 2rem calc(-50vw + 50%) !important;
    padding: 1rem max(1.5rem, calc(50vw - 520px)) !important;
}}
.st-key-topbar div[data-testid="stHorizontalBlock"] {{ align-items: center; }}
.sb-topbar-title {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.3rem; color: #fff; }}
.sb-topbar-sub {{ font-size: 0.82rem; color: {COLORS['top_bar_sub']}; margin-top: 0.1rem; }}
.st-key-topbar div[data-testid="stMarkdownContainer"] {{ color: #fff; }}

div[data-testid="stSegmentedControl"] button {{
    background: transparent !important; border: 1px solid rgba(255,255,255,0.55) !important;
    color: #fff !important; border-radius: 5px !important;
}}
div[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
    background: #fff !important; color: var(--ledger) !important; border-color: #fff !important;
}}

/* ---- cards ----
   st.container(key=...) really nests its children in the DOM (unlike two
   separate st.html('<div>')/st.html('</div>') calls, which do NOT nest
   the widgets rendered between them) -- so card chrome is applied to the
   .st-key-<name> wrapper around the real Streamlit widgets, not to a
   hand-written div pair. */
.st-key-form_card {{
    background: var(--white); border: 1px solid var(--rule); border-radius: 6px;
    padding: 2.25rem 2.5rem; box-shadow: 0 2px 10px rgba(15,61,46,0.07);
    max-width: 780px; margin: 0 auto;
}}
.st-key-result_wrap {{ max-width: 860px; margin: 0 auto; }}
.st-key-about_wrap {{ max-width: 980px; margin: 0 auto; }}
.sb-section-row {{ display: flex; gap: 1.25rem; padding: 1.25rem 0; border-top: 1px solid var(--rule); }}
.sb-section-row:first-of-type {{ border-top: none; padding-top: 0.25rem; }}
.sb-section-num {{
    font-family: 'Lora', serif; font-weight: 600; color: var(--brass); font-size: 1.1rem;
    width: 28px; flex-shrink: 0;
}}
.sb-section-title {{ font-weight: 600; font-size: 1.02rem; margin-bottom: 0.15rem; }}
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
div[data-testid="stNumberInput"] button {{ color: var(--muted) !important; background: {COLORS['input_fill']} !important; }}

.stButton > button[kind="primary"] {{
    background: var(--ledger) !important; border-color: var(--ledger) !important;
    border-radius: 5px !important; font-weight: 600 !important;
}}
.stButton > button[kind="primary"]:hover {{ background: var(--ledger-hover) !important; border-color: var(--ledger-hover) !important; }}
.stButton > button[kind="secondary"] {{ border-radius: 5px !important; border-color: var(--rule) !important; color: var(--ink) !important; }}

/* ---- application file card ---- */
.sb-file-card {{
    background: var(--white); border: 1px solid var(--rule); border-radius: 6px;
    padding: 2rem 2.5rem; box-shadow: 0 2px 10px rgba(15,61,46,0.07); position: relative; overflow: hidden;
    max-width: 860px; margin: 0 auto;
}}
.sb-file-meta {{ color: var(--muted); font-size: 0.78rem; }}
.sb-file-name {{ font-family: 'Lora', serif; font-weight: 600; font-size: 1.9rem; margin-top: 0.15rem; }}
.sb-next-step {{ color: var(--ink); font-size: 0.94rem; margin-top: 0.5rem; max-width: 70%; }}

.sb-stamp {{
    position: absolute; top: 1.6rem; right: 2.2rem; font-family: 'Lora', serif; font-weight: 600;
    font-size: 1.35rem; letter-spacing: 0.04em; padding: 0.55rem 1.1rem; border-radius: 4px;
    border: 3px double; transform: rotate(-7deg); opacity: 0.9; mix-blend-mode: multiply;
    animation: sb-stamp-in 380ms cubic-bezier(0.34, 1.56, 0.64, 1);
}}
@keyframes sb-stamp-in {{
    0% {{ transform: rotate(-7deg) scale(1.6); opacity: 0; }}
    100% {{ transform: rotate(-7deg) scale(1); opacity: 0.9; }}
}}
@media (prefers-reduced-motion: reduce) {{ .sb-stamp {{ animation: none; }} }}
.sb-stamp.approve {{ color: {COLORS['approve']}; border-color: {COLORS['approve']}; background: {COLORS['approve_tint']}; }}
.sb-stamp.caution {{ color: {COLORS['caution']}; border-color: {COLORS['caution']}; background: {COLORS['caution_tint']}; }}
.sb-stamp.decline {{ color: {COLORS['decline']}; border-color: {COLORS['decline']}; background: {COLORS['decline_tint']}; }}

.sb-figures {{ display: flex; gap: 2.5rem; margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--rule); }}
.sb-figure-label {{ color: var(--muted); font-size: 0.76rem; text-transform: lowercase; }}
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
.sb-ruler-pin-mark {{ color: var(--brass); font-size: 0.9rem; line-height: 1; }}

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

.sb-error {{ color: {COLORS['decline']}; font-size: 0.85rem; margin-top: 0.3rem; }}
</style>
"""
