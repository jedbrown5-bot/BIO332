"""Streamlit v2 — Ecosystem Management: immersive themed interface + Plotly charts."""
from __future__ import annotations

import copy
import streamlit as st
import plotly.graph_objects as go

from ecosystem_game import EcosystemAdventure, GRAZABLE_INVASIVE_EFFECTS, State

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ecosystem Manager",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Theme constants ───────────────────────────────────────────────────────────

STATE_THEME = {
    State.GRASSLAND: {
        "bg":     "#1b4332",
        "mid":    "#2d6a4f",
        "accent": "#52b788",
        "light":  "#d8f3dc",
        "emoji":  "🌿",
        "label":  "Grassland",
    },
    State.TRANSITION: {
        "bg":     "#7d4e00",
        "mid":    "#a06c00",
        "accent": "#e9c46a",
        "light":  "#fff8e1",
        "emoji":  "⚠️",
        "label":  "Transition",
    },
    State.SHRUBLAND: {
        "bg":     "#5c1e1e",
        "mid":    "#7c2d2d",
        "accent": "#c47474",
        "light":  "#fce4e4",
        "emoji":  "🌳",
        "label":  "Shrubland",
    },
}

METRIC_DEFS = [
    ("Grass Cover",        "grass_cover",       "🌿", "#40916c"),
    ("Grass Biomass",      "grass_biomass",      "🌾", "#74c69d"),
    ("Grass Diversity",    "grass_diversity",    "🌼", "#1d7c4d"),
    ("Shrub Density",      "shrub_density",      "🌳", "#a0522d"),
    ("Ecosystem Function", "ecosystem_function", "🌱", "#2d6a4f"),
    ("Grazing Pressure",   "grazing_pressure",   "🐄", "#6d6875"),
]

SUB_FN_DEFS = [
    ("Productivity",  "fn_productivity", "🌾", "#2a9d3f"),
    ("Soil function", "fn_soil",         "🪱", "#8B5E3C"),
    ("Hydrology",     "fn_hydrology",    "💧", "#1d7fc4"),
]

HISTORY_TRACK = [
    "grass_cover", "grass_diversity", "grass_biomass",
    "shrub_density", "ecosystem_function",
    "fn_productivity", "fn_soil", "fn_hydrology",
]

CHART_SERIES = [
    ("grass_cover",        "Grass Cover",    "#16a34a"),   # green
    ("grass_diversity",    "Diversity",      "#2563eb"),   # blue
    ("ecosystem_function", "Eco Function",   "#9333ea"),   # purple
    ("shrub_density",      "Shrub Density",  "#dc2626"),   # red
]


# ── CSS ───────────────────────────────────────────────────────────────────────

def _inject_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Force light mode globally so dark-mode OS settings don't make
           text invisible against the light background ── */
    html, body,
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        background-color: #f4f6f4 !important;
        color: #1f2937 !important;
    }

    /* All markdown / text containers */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stText"],
    .stAlert p {
        color: #1f2937 !important;
    }

    /* Expander — header and content body */
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p {
        color: #1f2937 !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stExpander"] > div {
        background-color: #ffffff !important;
        border-radius: 0 0 8px 8px !important;
    }
    [data-testid="stExpander"] > div p,
    [data-testid="stExpander"] > div li,
    [data-testid="stExpander"] > div span {
        color: #1f2937 !important;
    }

    /* Block container padding */
    .block-container {
        padding-top: 1.2rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 1400px !important;
        background-color: #f4f6f4 !important;
        color: #1f2937 !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 10px 14px !important;
        border: 1.5px solid #d1d5db !important;
        background: #ffffff !important;
        color: #1a2e22 !important;
        transition: all 0.15s ease !important;
        text-align: left !important;
        width: 100% !important;
        margin-bottom: 3px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }

    .stButton > button:hover:not(:disabled) {
        border-color: #52b788 !important;
        background: #f0faf4 !important;
        box-shadow: 0 3px 10px rgba(52,183,120,0.18) !important;
        transform: translateY(-1px) !important;
        color: #1b4332 !important;
    }

    .stButton > button:disabled {
        opacity: 0.38 !important;
        cursor: not-allowed !important;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2d6a4f 0%, #52b788 100%) !important;
        color: white !important;
        border: none !important;
        font-size: 1rem !important;
        padding: 14px 20px !important;
        box-shadow: 0 4px 14px rgba(52,183,120,0.35) !important;
    }

    .stButton > button[kind="primary"]:hover:not(:disabled) {
        background: linear-gradient(135deg, #1b4332 0%, #40916c 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 18px rgba(52,183,120,0.4) !important;
        color: white !important;
    }

    /* ── Dividers ── */
    hr { border-color: #e5e7eb !important; margin: 12px 0 !important; }

    /* ── Captions ── */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #6b7280 !important;
        font-size: 0.8rem !important;
    }

    /* ── Column gap ── */
    div[data-testid="column"] { padding: 0 6px !important; }
    </style>
    """, unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "game":            None,
        "phase":           "intro",
        "submenu":         None,
        "log":             [],
        "prev":            {},
        "undo_stack":      [],
        "undos_remaining": None,
        "metric_history":  [],   # list of {"year": int, attr: float, ...}
        "intro_history":   "short",   # "long" | "short"
        "intro_difficulty": "easy",   # "easy" | "hard"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()
_inject_css()

game: EcosystemAdventure | None = st.session_state.game


# ── Core helpers ──────────────────────────────────────────────────────────────

def _save_prev() -> None:
    g = st.session_state.game
    st.session_state.prev = {attr: getattr(g, attr) for _, attr, _, _ in METRIC_DEFS}
    for _, attr, _, _ in SUB_FN_DEFS:
        st.session_state.prev[attr] = getattr(g, attr)


def _delta(attr: str) -> float | None:
    prev = st.session_state.prev.get(attr)
    if prev is None:
        return None
    return getattr(st.session_state.game, attr) - prev


def _record_metrics() -> None:
    g = st.session_state.game
    row: dict = {"year": g.year}
    for attr in HISTORY_TRACK:
        row[attr] = getattr(g, attr)
    st.session_state.metric_history.append(row)


def _flush() -> list[str]:
    msgs = [m for m in game.messages if m.strip()]
    game.messages.clear()
    return msgs


def _push_undo() -> None:
    st.session_state.undo_stack.append(
        (copy.deepcopy(st.session_state.game), dict(st.session_state.prev))
    )
    if len(st.session_state.undo_stack) > 30:
        st.session_state.undo_stack.pop(0)


def _run(action_fn, *args, **kwargs) -> None:
    _push_undo()
    game.messages.clear()
    action_fn(*args, **kwargs)
    if not game.game_over:
        game.simulate_year()
        game._check_end_conditions()
    st.session_state.log = _flush()
    st.session_state.submenu = None
    _save_prev()
    _record_metrics()
    st.session_state.phase = "gameover" if game.game_over else "main"
    st.rerun()


# ── HTML building blocks ──────────────────────────────────────────────────────

def _bar(pct: float, colour: str, height: int = 6) -> str:
    pct = max(0.0, min(100.0, pct))
    return (
        f"<div style='background:#e5e7eb;border-radius:4px;height:{height}px;"
        f"width:100%;overflow:hidden;margin-top:5px;'>"
        f"<div style='background:{colour};height:100%;width:{pct:.1f}%;"
        f"border-radius:4px;'></div></div>"
    )


def _bar_colour_for(attr: str, val: float, default: str) -> str:
    if attr == "shrub_density":
        return "#c0392b" if val > 40 else "#e9a818" if val > 20 else "#40916c"
    if attr == "ecosystem_function":
        return "#c0392b" if val < 25 else "#e9a818" if val < 50 else default
    if attr == "grazing_pressure":
        return "#c0392b" if val > 60 else "#e9a818" if val > 40 else "#40916c"
    return default


def _delta_badge(d: float, invert: bool = False) -> str:
    if d is None:
        return ""
    positive_is_good = not invert
    good = (d >= 0) == positive_is_good
    colour = "#15803d" if good else "#b91c1c"
    bg     = "#dcfce7" if good else "#fee2e2"
    sign   = "+" if d >= 0 else ""
    return (
        f"<span style='font-size:0.7rem;font-weight:700;color:{colour};"
        f"background:{bg};padding:1px 5px;border-radius:4px;margin-left:6px;'>"
        f"{sign}{d:.1f}</span>"
    )


def _metric_card(label: str, attr: str, icon: str, colour: str) -> str:
    g   = st.session_state.game
    val = getattr(g, attr)
    d   = _delta(attr)
    col = _bar_colour_for(attr, val, colour)
    inv = attr in ("shrub_density", "grazing_pressure")
    badge = _delta_badge(d, invert=inv) if d is not None else ""

    return (
        f"<div style='background:white;border-radius:10px;padding:11px 14px;"
        f"margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,0.07);"
        f"border-left:4px solid {col};'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<span style='font-size:0.82rem;font-weight:600;color:#374151;'>{icon}&nbsp;{label}</span>"
        f"<span style='font-size:0.95rem;font-weight:700;color:{col};'>{val:.1f}%{badge}</span>"
        f"</div>"
        f"{_bar(val, col, 6)}"
        f"</div>"
    )


def _hero_header() -> None:
    g   = st.session_state.game
    th  = STATE_THEME[g.current_state]
    hist_tag = "🌍 Long history" if g._long_history else "🦘 Short history"
    budget_str = f"&nbsp;&nbsp;💰 ${g.budget}" if g.hard_mode else ""
    inv_str = f"&nbsp;&nbsp;🚨 {len(g.invasive_species)} invasive" if g.invasive_species else ""

    st.markdown(
        f"<div style='background:linear-gradient(135deg,{th['bg']} 0%,{th['mid']} 100%);"
        f"border-radius:16px;padding:20px 28px;margin-bottom:18px;"
        f"box-shadow:0 6px 20px rgba(0,0,0,0.25);color:white;'>"
        f"<div style='font-size:0.78rem;opacity:0.75;text-transform:uppercase;"
        f"letter-spacing:2px;margin-bottom:4px;'>"
        f"Year {g.year} of {g.GAME_LENGTH} &nbsp;·&nbsp; {hist_tag}"
        f"</div>"
        f"<div style='font-size:2rem;font-weight:800;line-height:1.2;'>"
        f"{th['emoji']} {th['label']}"
        f"</div>"
        f"<div style='font-size:0.82rem;opacity:0.8;margin-top:6px;'>"
        f"🔥 {g.years_since_fire} yrs since fire"
        f"{budget_str}{inv_str}"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Status panel ──────────────────────────────────────────────────────────────

def _render_status() -> None:
    g = st.session_state.game

    # Metric cards
    cards_html = "".join(
        _metric_card(label, attr, icon, colour)
        for label, attr, icon, colour in METRIC_DEFS
    )
    st.markdown(cards_html, unsafe_allow_html=True)

    # Sub-function row
    cols = st.columns(3)
    for i, (label, attr, icon, col) in enumerate(SUB_FN_DEFS):
        val = getattr(g, attr)
        d   = _delta(attr)
        badge = _delta_badge(d) if d is not None else ""
        with cols[i]:
            st.markdown(
                f"<div style='background:white;border-radius:10px;padding:10px 10px 8px;"
                f"box-shadow:0 1px 3px rgba(0,0,0,0.07);border-top:3px solid {col};"
                f"text-align:center;margin-bottom:10px;'>"
                f"<div style='font-size:1.1rem;'>{icon}</div>"
                f"<div style='font-size:0.68rem;color:#6b7280;margin:1px 0;font-weight:600;"
                f"text-transform:uppercase;letter-spacing:0.5px;'>{label}</div>"
                f"<div style='font-size:0.92rem;font-weight:700;color:{col};'>"
                f"{val:.0f}%{badge}</div>"
                f"{_bar(val, col, 4)}"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Invasive species warning
    if g.invasive_species:
        for sp in g.invasive_species:
            st.markdown(
                f"<div style='background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;"
                f"padding:9px 12px;margin-bottom:6px;font-size:0.85rem;'>"
                f"⚠️ <strong>{sp.name}</strong> — impact {int(sp.strength * 100)}%</div>",
                unsafe_allow_html=True,
            )

    # Easy-mode hints
    if not g.hard_mode:
        hints = g._diagnostic_hints()
        if hints:
            with st.expander("🔬 Field observations", expanded=True):
                for h in hints:
                    st.info(h)

    # State history
    if g.history:
        with st.expander("📜 State transition history"):
            for h in g.history:
                st.markdown(h)


# ── Chart helpers ─────────────────────────────────────────────────────────────

_CHART_CFG = {"displayModeBar": False, "responsive": True}

_AXIS_DEFAULTS = dict(
    gridcolor="#e9ecef", linecolor="#d1d5db",
    tickfont=dict(size=12), title_font=dict(size=12),
    zeroline=False,
)

def _base_layout(height: int, **extra) -> dict:
    """Shared Plotly layout. Callers supply xaxis/yaxis via **extra to avoid
    duplicate-key conflicts when overriding defaults."""
    base = dict(
        height=height,
        # l/b generous so axis labels aren't clipped; t small (legend is inside)
        margin=dict(l=52, r=24, t=20, b=52),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f9fafb",
        font=dict(family="Inter, -apple-system, sans-serif", size=13, color="#1f2937"),
        # Legend sits inside the plot area — top-right corner — so it's never
        # clipped by the chart container and the text colour is always visible.
        legend=dict(
            orientation="v",
            yanchor="top",   y=0.99,
            xanchor="right", x=0.99,
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="#d1d5db",
            borderwidth=1,
            font=dict(size=12, color="#1f2937"),
        ),
        hovermode="x unified",
        hoverlabel=dict(font_size=13, bgcolor="#1f2937", font_color="white"),
    )
    # Provide sensible axis defaults only if the caller hasn't overridden them
    base.setdefault("xaxis", dict(**_AXIS_DEFAULTS))
    base.setdefault("yaxis", dict(
        range=[0, 105], title="%", ticksuffix="%", **_AXIS_DEFAULTS
    ))
    base.update(extra)
    return base


def _trends_chart() -> None:
    history = st.session_state.metric_history
    if len(history) < 2:
        return

    years = [h["year"] for h in history]
    fig = go.Figure()

    dashes = ["solid", "solid", "dash", "solid"]
    for (attr, name, colour), dash in zip(CHART_SERIES, dashes):
        fig.add_trace(go.Scatter(
            x=years,
            y=[h[attr] for h in history],
            name=name,
            line=dict(color=colour, width=2.5, dash=dash),
            mode="lines+markers",
            marker=dict(size=4, color=colour),
            hovertemplate=f"<b>{name}</b>: %{{y:.1f}}%<extra></extra>",
        ))

    fig.add_hline(
        y=40, line_dash="dot", line_color="#9ca3af", line_width=1.5,
        annotation_text="Recovery threshold (40%)",
        annotation_font_size=11,
        annotation_position="bottom right",
    )

    fig.update_layout(**_base_layout(
        300,
        xaxis=dict(
            title="Year", range=[0, 30],
            gridcolor="#e9ecef", linecolor="#d1d5db",
            tickfont=dict(size=12), title_font=dict(size=12),
            zeroline=False,
        ),
    ))

    st.plotly_chart(fig, use_container_width=True, config=_CHART_CFG)


# ── Action panel ──────────────────────────────────────────────────────────────

def _btn(label: str, key: str, disabled: bool = False) -> bool:
    return st.button(label, key=key, use_container_width=True, disabled=disabled)


def _render_undo_button() -> None:
    stack     = st.session_state.undo_stack
    remaining = st.session_state.undos_remaining
    can_undo  = bool(stack) and (remaining is None or remaining > 0)

    if remaining is None:
        label = "↩️ Undo Last Action"
    elif remaining > 0:
        label = f"↩️ Undo  ({remaining} remaining)"
    else:
        label = "↩️ Undo  (none left)"

    if st.button(label, key="undo", use_container_width=True, disabled=not can_undo):
        game_snap, prev_snap = stack.pop()
        st.session_state.game  = game_snap
        st.session_state.prev  = prev_snap
        if remaining is not None:
            st.session_state.undos_remaining = remaining - 1
        if st.session_state.metric_history:
            st.session_state.metric_history.pop()
        st.session_state.submenu = None
        st.session_state.log     = []
        st.session_state.phase   = "main"
        st.rerun()


def _render_cultural_burn_button() -> None:
    g = game
    cost = lambda c: f"  ${c}" if g.hard_mode else ""

    if g._cultural_burn_ready:
        if _btn(f"🌀 Cultural Burn{cost(15)}", "cburn"):
            _run(g.conduct_cultural_burn)
    else:
        yr = g.cultural_burn_years
        label = (
            f"🤝 Begin Cultural Burning Partnership{cost(20)}"
            if yr == 0
            else f"🤝 Invest: Cultural Burning ({yr}/3 yrs){cost(20)}"
        )
        if _btn(label, "cburn_invest"):
            _run(g.invest_cultural_burning)
        if yr > 0:
            dots = "●" * yr + "○" * (3 - yr)
            st.markdown(
                f"<div style='font-size:0.75rem;color:#6b7280;padding:1px 6px;"
                f"margin-bottom:4px;'>Partnership: {dots} {yr}/3 yrs</div>",
                unsafe_allow_html=True,
            )


def _render_main_menu() -> None:
    cost = lambda c: f"  ${c}" if game.hard_mode else ""

    st.markdown(
        "<p style='font-weight:700;font-size:0.95rem;color:#1b4332;"
        "margin-bottom:12px;'>Management Actions</p>",
        unsafe_allow_html=True,
    )

    if _btn(f"🔥 Prescribed Burn{cost(30)}", "burn"):
        _run(game.conduct_prescribed_burn)

    _render_cultural_burn_button()

    if _btn("🐄 Adjust Grazing", "grazing"):
        st.session_state.submenu = "grazing"; st.rerun()

    if _btn("🪓 Remove Shrubs", "shrubs"):
        st.session_state.submenu = "shrubs"; st.rerun()

    if _btn("🌱 Reseed Native Grasses", "reseed"):
        st.session_state.submenu = "reseed"; st.rerun()

    has_invasives = bool(game.invasive_species)
    if _btn("🚫 Manage Invasive Species", "invasive", disabled=not has_invasives):
        st.session_state.submenu = "invasive"; st.rerun()

    st.markdown("<div style='margin:10px 0;border-top:1px solid #e5e7eb;'></div>",
                unsafe_allow_html=True)

    if _btn("⏭️ Do Nothing — advance year", "nothing"):
        _run(game.do_nothing)

    st.markdown("<div style='margin:10px 0;border-top:1px solid #e5e7eb;'></div>",
                unsafe_allow_html=True)

    _render_undo_button()


def _back_btn(target: str | None = None) -> None:
    if _btn("← Back", "back"):
        st.session_state.submenu = target; st.rerun()


def _render_grazing_menu() -> None:
    st.markdown(
        f"<p style='font-weight:700;font-size:0.92rem;color:#1b4332;margin-bottom:4px;'>"
        f"Adjust Grazing</p>"
        f"<p style='color:#6b7280;font-size:0.8rem;margin-bottom:10px;'>"
        f"Current: {game.grazing_pressure:.1f}%</p>",
        unsafe_allow_html=True,
    )
    options = [
        (1, "Remove all livestock  (0%)",     0),
        (2, "Light grazing         (20%)",     0),
        (3, "Moderate grazing      (40%)",     0),
        (4, "Heavy grazing         (60%)",     0),
        (5, "Very heavy grazing    (80%)",     0),
        (6, "Rotational grazing system",      25),
    ]
    for idx, label, cost in options:
        cost_str = f"  ${cost}" if cost and game.hard_mode else ""
        if _btn(f"{label}{cost_str}", f"g{idx}"):
            _run(game.adjust_grazing, choice=idx)
    _back_btn()


def _render_shrubs_menu() -> None:
    st.markdown(
        "<p style='font-weight:700;font-size:0.92rem;color:#1b4332;margin-bottom:10px;'>"
        "Remove Shrubs</p>", unsafe_allow_html=True,
    )
    options = [
        (1, "Selective hand removal  (−10%)",  10),
        (2, "Mechanical clearing     (−30%)",  25),
        (3, "Herbicide application   (−50%)",  35),
        (4, "Integrated management",           45),
    ]
    for idx, label, cost in options:
        cost_str = f"  ${cost}" if game.hard_mode else ""
        if _btn(f"{label}{cost_str}", f"s{idx}"):
            _run(game.remove_shrubs, choice=idx)
    _back_btn()


def _render_reseed_menu() -> None:
    st.markdown(
        "<p style='font-weight:700;font-size:0.92rem;color:#1b4332;margin-bottom:10px;'>"
        "Reseed Native Grasses</p>", unsafe_allow_html=True,
    )
    options = [
        (1, "Minimal reseeding   (+10%)",   15),
        (2, "Moderate reseeding  (+25%)",   30),
        (3, "Intensive reseeding (+40%)",   50),
        (4, "Experimental native seed mix", 40),
    ]
    for idx, label, cost in options:
        cost_str = f"  ${cost}" if game.hard_mode else ""
        if _btn(f"{label}{cost_str}", f"r{idx}"):
            _run(game.reseed_grasses, choice=idx)
    _back_btn()


def _render_invasive_menu() -> None:
    st.markdown(
        "<p style='font-weight:700;font-size:0.92rem;color:#1b4332;margin-bottom:10px;'>"
        "Invasive Species Management</p>", unsafe_allow_html=True,
    )
    grazable = any(sp.effect in GRAZABLE_INVASIVE_EFFECTS for sp in game.invasive_species)
    options = [
        (1, "Targeted removal",              25, False),
        (2, "Biocontrol introduction",       40, False),
        (3, "Comprehensive management",      50, False),
        (4, "Targeted/conservation grazing", 30, not grazable),
    ]
    for idx, label, cost, disabled in options:
        cost_str = f"  ${cost}" if game.hard_mode else ""
        if idx == 1:
            if _btn(f"{label}{cost_str}", f"i{idx}", disabled=disabled):
                st.session_state.submenu = "inv_target"; st.rerun()
        else:
            if _btn(f"{label}{cost_str}", f"i{idx}", disabled=disabled):
                _run(game.manage_invasive_species, choice=idx)
    if not grazable:
        st.caption("Grazing option disabled — no palatable invaders present.")
    _back_btn()


def _render_inv_target_menu() -> None:
    st.markdown(
        "<p style='font-weight:700;font-size:0.92rem;color:#1b4332;margin-bottom:10px;'>"
        "Select Target Species</p>", unsafe_allow_html=True,
    )
    for i, sp in enumerate(game.invasive_species, 1):
        if _btn(f"{sp.name}  (impact {int(sp.strength * 100)}%)", f"t{i}"):
            _run(game.manage_invasive_species, choice=1, target_idx=i)
    _back_btn(target="invasive")


SUBMENU_RENDERERS = {
    "grazing":    _render_grazing_menu,
    "shrubs":     _render_shrubs_menu,
    "reseed":     _render_reseed_menu,
    "invasive":   _render_invasive_menu,
    "inv_target": _render_inv_target_menu,
}


# ── Event log ────────────────────────────────────────────────────────────────

def _render_log() -> None:
    if not st.session_state.log:
        return
    year_shown = max(1, game.year - 1)
    with st.expander(f"📋 Year {year_shown} events", expanded=True):
        for msg in st.session_state.log:
            if msg.strip():
                st.markdown(msg)


# ── Pages ─────────────────────────────────────────────────────────────────────

def _page_intro() -> None:
    st.markdown(
        "<div style='text-align:center;padding:16px 0 4px;'>"
        "<div style='font-size:2.8rem;font-weight:800;color:#1b4332;'>"
        "🌿 Ecosystem Manager</div>"
        "<div style='font-size:1.05rem;color:#6b7280;margin-top:4px;'>"
        "State &amp; Transition Adventure</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div style='max-width:760px;margin:20px auto 0;'>
    <p style='color:#374151;line-height:1.7;'>
    You are managing a <strong>grassland ecosystem</strong> that can exist in multiple stable states.
    Your goal: restore and maintain a healthy, functional grassland over <strong>30 years</strong>
    starting from a degraded, shrub-encroached baseline.
    </p>
    </div>
    """, unsafe_allow_html=True)

    # Three-metric explanation
    c1, c2, c3 = st.columns(3)
    for col, icon, title, body in [
        (c1, "🌿", "Cover", "Structural presence of grass on the ground surface."),
        (c2, "🌾", "Biomass", "Standing crop and litter — the fuel load for fire."),
        (c3, "🌼", "Diversity", "Species richness. Biomass accumulation suppresses it."),
    ]:
        with col:
            st.markdown(
                f"<div style='background:white;border-radius:10px;padding:14px 14px 12px;"
                f"box-shadow:0 1px 4px rgba(0,0,0,0.08);text-align:center;height:100%;'>"
                f"<div style='font-size:1.6rem;'>{icon}</div>"
                f"<div style='font-weight:700;font-size:0.9rem;color:#1b4332;margin:4px 0 3px;'>{title}</div>"
                f"<div style='font-size:0.8rem;color:#6b7280;'>{body}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Ecosystem function
    st.markdown(
        "<p style='font-weight:700;color:#1b4332;font-size:0.95rem;margin-bottom:8px;'>"
        "Ecosystem Function — the three-part score</p>",
        unsafe_allow_html=True,
    )
    fc1, fc2, fc3 = st.columns(3)
    for col, icon, colour, title, body in [
        (fc1, "🌾", "#2a9d3f", "Productivity",
         "Plant growth — needs cover, diversity, and healthy soil."),
        (fc2, "🪱", "#8B5E3C", "Soil Function",
         "Organic matter & microbes — slow to build, fast to lose."),
        (fc3, "💧", "#1d7fc4", "Hydrology",
         "Infiltration and water retention. Depends on cover and soil."),
    ]:
        with col:
            st.markdown(
                f"<div style='background:white;border-radius:10px;padding:14px 14px 12px;"
                f"box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid {colour};"
                f"text-align:center;'>"
                f"<div style='font-size:1.5rem;'>{icon}</div>"
                f"<div style='font-weight:700;font-size:0.88rem;color:{colour};margin:4px 0 3px;'>{title}</div>"
                f"<div style='font-size:0.78rem;color:#6b7280;'>{body}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<p style='font-size:0.82rem;color:#6b7280;margin-top:8px;'>"
        "⚠️ Soil is the <strong>limiting factor</strong>: degraded soil caps how high "
        "productivity and hydrology can climb, no matter how much grass you have.</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    # Evolutionary history
    st.markdown(
        "<p style='font-weight:700;color:#1b4332;font-size:1.0rem;margin-bottom:4px;'>"
        "Choose your evolutionary grazing history</p>"
        "<p style='font-size:0.82rem;color:#6b7280;margin-bottom:14px;'>"
        "Based on <em>Cingolani, Noy-Meir &amp; Díaz (2005)</em> — "
        "the evolutionary context of the grass community fundamentally changes "
        "how the ecosystem responds to grazing and management.</p>",
        unsafe_allow_html=True,
    )

    sel_h = st.session_state.intro_history
    hcol1, hcol2 = st.columns(2)

    with hcol1:
        long_sel = sel_h == "long"
        border   = "3px solid #1b4332" if long_sel else "2px solid #d1d5db"
        bg       = "#e8f5ee" if long_sel else "#ffffff"
        badge    = "<span style='float:right;background:#1b4332;color:white;font-size:0.72rem;font-weight:700;padding:2px 8px;border-radius:10px;'>✓ SELECTED</span>" if long_sel else ""
        st.markdown(
            f"<div style='background:{bg};border:{border};border-radius:12px;"
            f"padding:18px 20px;min-height:180px;'>"
            f"{badge}"
            f"<div style='font-size:1.6rem;margin-bottom:6px;'>🌍</div>"
            f"<div style='font-weight:700;font-size:1.0rem;color:#1b4332;margin-bottom:6px;'>"
            f"Long evolutionary history</div>"
            f"<div style='font-size:0.82rem;color:#374151;line-height:1.6;'>"
            f"<em>African savanna · Eurasian steppe · Pampas</em><br><br>"
            f"Grasses <strong>co-evolved with large herbivores</strong>. "
            f"Moderate grazing can <em>increase</em> diversity. "
            f"Overgrazing is <strong>reversible</strong>. Lower invasion risk."
            f"</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("✓ Long history selected" if long_sel else "Select Long history →",
                     key="sel_long", use_container_width=True,
                     type="primary" if long_sel else "secondary"):
            st.session_state.intro_history = "long"
            st.rerun()

    with hcol2:
        short_sel = sel_h == "short"
        border    = "3px solid #7c1c1c" if short_sel else "2px solid #d1d5db"
        bg        = "#fde8e8" if short_sel else "#ffffff"
        badge     = "<span style='float:right;background:#7c1c1c;color:white;font-size:0.72rem;font-weight:700;padding:2px 8px;border-radius:10px;'>✓ SELECTED</span>" if short_sel else ""
        st.markdown(
            f"<div style='background:{bg};border:{border};border-radius:12px;"
            f"padding:18px 20px;min-height:180px;'>"
            f"{badge}"
            f"<div style='font-size:1.6rem;margin-bottom:6px;'>🦘</div>"
            f"<div style='font-weight:700;font-size:1.0rem;color:#7c1c1c;margin-bottom:6px;'>"
            f"Short evolutionary history</div>"
            f"<div style='font-size:0.82rem;color:#374151;line-height:1.6;'>"
            f"<em>Australia · New Zealand · pre-colonial Americas</em><br><br>"
            f"No evolved grazing defences. State transitions are "
            f"<strong>irreversible</strong>. Soil collapses rapidly. Higher invasion risk."
            f"</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("✓ Short history selected" if short_sel else "Select Short history →",
                     key="sel_short", use_container_width=True,
                     type="primary" if short_sel else "secondary"):
            st.session_state.intro_history = "short"
            st.rerun()

    st.divider()

    # Cultural burning explainer
    st.markdown(
        "<p style='font-weight:700;color:#1b4332;font-size:1.0rem;margin-bottom:6px;'>"
        "🌀 Cultural burning — an unlockable mechanic</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='background:#f5f0ff;border-left:4px solid #7c3aed;"
        "border-radius:8px;padding:14px 16px;margin-bottom:16px;"
        "font-size:0.85rem;color:#374151;line-height:1.7;'>"
        "In Australia, <strong>First Nations peoples maintained grassland ecosystems for 60,000+ years</strong> "
        "through regular, low-intensity cool burns — firestick farming. "
        "This knowledge was largely severed by colonisation and disconnection from Country.<br><br>"
        "In the game, you can invest in re-establishing a <strong>cultural burning partnership</strong> "
        "with local Elders. It takes <strong>3 years of relationship-building</strong> ($20/yr in hard mode) "
        "and gives access to cultural burns that are ecologically superior to Western prescribed burns:<br>"
        "<ul style='margin:6px 0 0 0;padding-left:18px;'>"
        "<li>Cool mosaic fires → <strong>much larger diversity boost</strong></li>"
        "<li>No soil sterilisation → <strong>soil function improves</strong> after each burn</li>"
        "<li>Better shrub control and invasive suppression at optimal timing</li>"
        "<li>Cheaper per burn ($15 vs $30) once established</li>"
        "<li>Especially powerful in Australian (short history) grasslands</li>"
        "</ul></div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # Difficulty
    st.markdown(
        "<p style='font-weight:700;color:#1b4332;font-size:1.0rem;margin-bottom:12px;'>"
        "Choose difficulty</p>",
        unsafe_allow_html=True,
    )
    sel_d = st.session_state.intro_difficulty
    dcol1, dcol2 = st.columns(2)

    with dcol1:
        easy_sel = sel_d == "easy"
        border   = "3px solid #15803d" if easy_sel else "2px solid #d1d5db"
        bg       = "#e8f5ee" if easy_sel else "#ffffff"
        badge    = "<span style='float:right;background:#15803d;color:white;font-size:0.72rem;font-weight:700;padding:2px 8px;border-radius:10px;'>✓ SELECTED</span>" if easy_sel else ""
        st.markdown(
            f"<div style='background:{bg};border:{border};border-radius:12px;padding:16px 18px;'>"
            f"{badge}"
            f"<div style='font-weight:700;font-size:1.0rem;color:#15803d;margin-bottom:8px;'>🟢 Easy</div>"
            f"<ul style='font-size:0.82rem;color:#374151;margin:0;padding-left:18px;line-height:1.8;'>"
            f"<li>Field observation hints from ecologists</li>"
            f"<li>No budget constraint</li>"
            f"<li>Unlimited undo</li>"
            f"</ul></div>",
            unsafe_allow_html=True,
        )
        if st.button("✓ Easy selected" if easy_sel else "Select Easy →",
                     key="sel_easy", use_container_width=True,
                     type="primary" if easy_sel else "secondary"):
            st.session_state.intro_difficulty = "easy"
            st.rerun()

    with dcol2:
        hard_sel = sel_d == "hard"
        border   = "3px solid #b45309" if hard_sel else "2px solid #d1d5db"
        bg       = "#fef3c7" if hard_sel else "#ffffff"
        badge    = "<span style='float:right;background:#b45309;color:white;font-size:0.72rem;font-weight:700;padding:2px 8px;border-radius:10px;'>✓ SELECTED</span>" if hard_sel else ""
        st.markdown(
            f"<div style='background:{bg};border:{border};border-radius:12px;padding:16px 18px;'>"
            f"{badge}"
            f"<div style='font-weight:700;font-size:1.0rem;color:#b45309;margin-bottom:8px;'>🔴 Hard</div>"
            f"<ul style='font-size:0.82rem;color:#374151;margin:0;padding-left:18px;line-height:1.8;'>"
            f"<li>No hints</li>"
            f"<li>Tight budget — start ${EcosystemAdventure.STARTING_BUDGET}, "
            f"+${EcosystemAdventure.ANNUAL_BUDGET}/yr</li>"
            f"<li>Only 3 undos</li>"
            f"</ul></div>",
            unsafe_allow_html=True,
        )
        if st.button("✓ Hard selected" if hard_sel else "Select Hard →",
                     key="sel_hard", use_container_width=True,
                     type="primary" if hard_sel else "secondary"):
            st.session_state.intro_difficulty = "hard"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🌱 Start Game", type="primary", use_container_width=True):
        g = EcosystemAdventure()
        g.headless        = True
        g.hard_mode       = st.session_state.intro_difficulty == "hard"
        g.grazing_history = st.session_state.intro_history
        st.session_state.game            = g
        st.session_state.log             = []
        st.session_state.phase           = "main"
        st.session_state.undo_stack      = []
        st.session_state.undos_remaining = 3 if g.hard_mode else None
        st.session_state.metric_history  = []
        _save_prev()
        _record_metrics()  # record initial state at year 0
        st.rerun()


def _page_main() -> None:
    _hero_header()

    left, right = st.columns([3, 2], gap="large")

    with left:
        _render_status()

    with right:
        submenu  = st.session_state.submenu
        renderer = SUBMENU_RENDERERS.get(submenu, _render_main_menu)
        renderer()

    _render_log()

    # Trend chart full-width below the two panels so it has space to breathe
    if len(st.session_state.metric_history) >= 2:
        st.markdown(
            "<p style='font-weight:700;font-size:0.88rem;color:#6b7280;"
            "text-transform:uppercase;letter-spacing:1px;margin:12px 0 4px;'>"
            "Ecosystem Trends</p>",
            unsafe_allow_html=True,
        )
        _trends_chart()


def _page_gameover() -> None:
    th = STATE_THEME[game.current_state]
    score = game._compute_score()

    if game.year >= game.GAME_LENGTH:
        st.balloons()
        st.markdown(
            f"<div style='background:linear-gradient(135deg,{th['bg']},{th['mid']});"
            f"border-radius:16px;padding:28px 32px;color:white;"
            f"box-shadow:0 8px 24px rgba(0,0,0,0.3);margin-bottom:20px;'>"
            f"<div style='font-size:2.4rem;font-weight:800;'>🎉 30 years managed!</div>"
            f"<div style='opacity:0.8;margin-top:6px;font-size:1.0rem;'>"
            f"{th['emoji']} Final state: {th['label']}</div>"
            f"<div style='font-size:1.6rem;font-weight:700;margin-top:10px;'>"
            f"Score: {score} / 200 &nbsp; {game._rating(score)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='background:linear-gradient(135deg,#5c1e1e,#7c2d2d);"
            "border-radius:16px;padding:28px 32px;color:white;"
            "box-shadow:0 8px 24px rgba(0,0,0,0.3);margin-bottom:20px;'>"
            "<div style='font-size:2.2rem;font-weight:800;'>💀 Ecosystem Collapsed</div>"
            "<div style='opacity:0.8;margin-top:6px;'>"
            "Ecosystem function reached zero — the land can no longer support its community."
            "</div>"
            f"<div style='font-size:1.4rem;font-weight:700;margin-top:10px;'>"
            f"Score: {score} / 200 &nbsp; {game._rating(score)}</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Main content ──────────────────────────────────────────────────────────
    col_stats, col_chart = st.columns([1, 2], gap="large")

    with col_stats:
        st.markdown(
            "<p style='font-weight:700;color:#1b4332;font-size:0.95rem;margin-bottom:10px;'>"
            "Final Ecosystem State</p>",
            unsafe_allow_html=True,
        )

        def stat_row(label, value, colour="#374151"):
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"padding:6px 0;border-bottom:1px solid #f0f0f0;'>"
                f"<span style='font-size:0.85rem;color:#6b7280;'>{label}</span>"
                f"<span style='font-weight:700;font-size:0.88rem;color:{colour};'>{value}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        stat_row("Grass cover",    f"{game.grass_cover:.1f}%",    "#40916c")
        stat_row("Grass diversity", f"{game.grass_diversity:.1f}%", "#1d7c4d")
        stat_row("Shrub density",  f"{game.shrub_density:.1f}%",  "#a0522d")
        stat_row("Eco function",   f"{game.ecosystem_function:.1f}%", "#2d6a4f")
        stat_row("State transitions", str(len(game.history)))
        stat_row("Invasive species", str(len(game.invasive_species)))

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-weight:700;color:#1b4332;font-size:0.92rem;margin-bottom:8px;'>"
            "Sub-functions</p>",
            unsafe_allow_html=True,
        )
        for label, attr, icon, col in SUB_FN_DEFS:
            val = getattr(game, attr)
            st.markdown(
                f"<div style='margin-bottom:8px;'>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:3px;'>"
                f"<span style='font-size:0.82rem;color:#374151;'>{icon} {label}</span>"
                f"<span style='font-weight:700;font-size:0.85rem;color:{col};'>{val:.1f}%</span>"
                f"</div>"
                f"{_bar(val, col, 7)}"
                f"</div>",
                unsafe_allow_html=True,
            )

        if game.history:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                "<p style='font-weight:700;color:#1b4332;font-size:0.88rem;margin-bottom:6px;'>"
                "State transition history</p>",
                unsafe_allow_html=True,
            )
            for h in game.history:
                st.markdown(f"<p style='font-size:0.8rem;color:#6b7280;margin:0;'>{h}</p>",
                            unsafe_allow_html=True)

    with col_chart:
        history = st.session_state.metric_history

        # ── 30-year ecosystem trajectory ──────────────────────────────────────
        if len(history) >= 2:
            st.markdown(
                "<p style='font-weight:700;color:#1b4332;font-size:0.95rem;margin-bottom:4px;'>"
                "30-year Trajectory</p>",
                unsafe_allow_html=True,
            )
            years = [h["year"] for h in history]
            fig_ts = go.Figure()
            dashes = ["solid", "solid", "dash", "solid"]
            for (attr, name, colour), dash in zip(CHART_SERIES, dashes):
                fig_ts.add_trace(go.Scatter(
                    x=years, y=[h[attr] for h in history],
                    name=name,
                    line=dict(color=colour, width=2.5, dash=dash),
                    mode="lines+markers",
                    marker=dict(size=4, color=colour),
                    hovertemplate=f"<b>{name}</b>: %{{y:.1f}}%<extra></extra>",
                ))
            fig_ts.add_hline(
                y=40, line_dash="dot", line_color="#9ca3af", line_width=1.5,
                annotation_text="Recovery threshold (40%)",
                annotation_font_size=11,
                annotation_position="bottom right",
            )
            fig_ts.update_layout(**_base_layout(
                320,
                xaxis=dict(
                    title="Year", range=[0, 30],
                    gridcolor="#e9ecef", linecolor="#d1d5db",
                    tickfont=dict(size=12), title_font=dict(size=12),
                    zeroline=False,
                ),
            ))
            st.plotly_chart(fig_ts, use_container_width=True, config=_CHART_CFG)

        # ── Sub-function final bar chart ───────────────────────────────────────
        st.markdown(
            "<p style='font-weight:700;color:#1b4332;font-size:0.95rem;"
            "margin:16px 0 4px;'>Final Sub-function Breakdown</p>",
            unsafe_allow_html=True,
        )
        sub_labels  = [label for label, _, _, _ in SUB_FN_DEFS]
        sub_values  = [getattr(game, attr) for _, attr, _, _ in SUB_FN_DEFS]
        sub_colours = [col for _, _, _, col in SUB_FN_DEFS]

        fig_sub = go.Figure(go.Bar(
            x=sub_labels, y=sub_values,
            marker_color=sub_colours,
            marker_line_width=0,
            text=[f"{v:.0f}%" for v in sub_values],
            textposition="outside",
            textfont=dict(size=13, color="#374151"),
            hovertemplate="<b>%{x}</b>: %{y:.1f}%<extra></extra>",
        ))
        fig_sub.add_hline(
            y=50, line_dash="dot", line_color="#6b7280", line_width=1.5,
            annotation_text="Target (50%)",
            annotation_font_size=11,
            annotation_position="bottom right",
        )
        lay = _base_layout(260)
        lay["showlegend"] = False
        lay["yaxis"]["range"] = [0, 115]
        lay["xaxis"] = dict(
            gridcolor="#e9ecef", linecolor="#d1d5db",
            tickfont=dict(size=15, color="#1f2937"),
            zeroline=False,
        )
        lay["font"] = dict(size=13, color="#1f2937")
        fig_sub.update_layout(**lay)
        st.plotly_chart(fig_sub, use_container_width=True, config=_CHART_CFG)

        # ── Sub-function trajectory over time ──────────────────────────────────
        if len(history) >= 2:
            st.markdown(
                "<p style='font-weight:700;color:#1b4332;font-size:0.95rem;"
                "margin:16px 0 4px;'>Sub-function Trajectory</p>",
                unsafe_allow_html=True,
            )
            years = [h["year"] for h in history]
            fig_fn = go.Figure()
            for label, attr, icon, colour in SUB_FN_DEFS:
                fig_fn.add_trace(go.Scatter(
                    x=years, y=[h[attr] for h in history],
                    name=f"{icon} {label}",
                    line=dict(color=colour, width=2.5),
                    mode="lines+markers",
                    marker=dict(size=4, color=colour),
                    hovertemplate=f"<b>{label}</b>: %{{y:.1f}}%<extra></extra>",
                ))
            fig_fn.add_hline(
                y=25, line_dash="dot", line_color="#dc2626", line_width=1.5,
                annotation_text="Liebig penalty threshold (25%)",
                annotation_font_size=11,
                annotation_position="bottom right",
            )
            fig_fn.update_layout(**_base_layout(
                300,
                xaxis=dict(
                    title="Year", range=[0, 30],
                    gridcolor="#e9ecef", linecolor="#d1d5db",
                    tickfont=dict(size=12), title_font=dict(size=12),
                    zeroline=False,
                ),
            ))
            st.plotly_chart(fig_fn, use_container_width=True, config=_CHART_CFG)

    st.divider()
    if st.button("🌱 Play Again", type="primary", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ── Router ─────────────────────────────────────────────────────────────────────

phase = st.session_state.phase

if phase == "intro":
    _page_intro()
elif phase == "main":
    game = st.session_state.game
    _page_main()
elif phase == "gameover":
    game = st.session_state.game
    _page_gameover()
else:
    st.session_state.phase = "intro"
    st.rerun()
