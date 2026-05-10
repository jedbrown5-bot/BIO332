"""Streamlit front-end for the Ecosystem Management: State & Transition Adventure."""

from __future__ import annotations

import copy
import streamlit as st

from ecosystem_game import EcosystemAdventure, GRAZABLE_INVASIVE_EFFECTS, State

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ecosystem Manager",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session-state bootstrap ───────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "game":             None,
        "phase":            "intro",   # intro | main | sub_* | gameover
        "submenu":          None,      # None | grazing | shrubs | reseed | invasive | inv_target
        "log":              [],        # messages from the last completed turn
        "prev":             {},        # metric values from the previous year (for delta display)
        "undo_stack":       [],        # list of (game_snapshot, prev_snapshot) pairs
        "undos_remaining":  None,      # None = unlimited (easy); int countdown (hard)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# Convenience alias (re-bound after any rerun)
game: EcosystemAdventure | None = st.session_state.game

# ── Helpers ───────────────────────────────────────────────────────────────────

STATE_COLOUR = {
    State.GRASSLAND:  "🟢",
    State.TRANSITION: "🟡",
    State.SHRUBLAND:  "🔴",
}

METRIC_DEFS = [
    ("Grass Cover",        "grass_cover",        "🌿"),
    ("Grass Biomass",      "grass_biomass",       "🌾"),
    ("Grass Diversity",    "grass_diversity",     "🌼"),
    ("Shrub Density",      "shrub_density",       "🌳"),
    ("Ecosystem Function", "ecosystem_function",  "🌱"),
    ("Grazing Pressure",   "grazing_pressure",    "🐄"),
]

# Sub-functions tracked separately for display (not included in delta tracking)
SUB_FN_DEFS = [
    ("Productivity",   "fn_productivity", "🌾", "#2a9d3f"),
    ("Soil function",  "fn_soil",         "🪱", "#8B5E3C"),
    ("Hydrology",      "fn_hydrology",    "💧", "#1d7fc4"),
]


def _save_prev() -> None:
    g = st.session_state.game
    st.session_state.prev = {attr: getattr(g, attr) for _, attr, _ in METRIC_DEFS}
    for _, attr, _, _ in SUB_FN_DEFS:
        st.session_state.prev[attr] = getattr(g, attr)


def _delta(attr: str) -> str | None:
    prev = st.session_state.prev.get(attr)
    if prev is None:
        return None
    d = getattr(st.session_state.game, attr) - prev
    return f"{'+' if d >= 0 else ''}{d:.1f}%"


def _flush() -> list[str]:
    """Collect and clear the game's message buffer."""
    msgs = [m for m in game.messages if m.strip()]
    game.messages.clear()
    return msgs


def _push_undo() -> None:
    """Snapshot the current game + prev-metrics state onto the undo stack."""
    st.session_state.undo_stack.append(
        (copy.deepcopy(st.session_state.game), dict(st.session_state.prev))
    )
    # Cap easy-mode stack at 30 (one per year maximum)
    if len(st.session_state.undo_stack) > 30:
        st.session_state.undo_stack.pop(0)


def _run(action_fn, *args, **kwargs) -> None:
    """Call a management action, simulate the year, collect messages, rerun."""
    _push_undo()
    game.messages.clear()
    action_fn(*args, **kwargs)
    if not game.game_over:
        game.simulate_year()
        game._check_end_conditions()
    st.session_state.log = _flush()
    st.session_state.submenu = None
    _save_prev()
    st.session_state.phase = "gameover" if game.game_over else "main"
    st.rerun()


# ── Status panel (left column) ────────────────────────────────────────────────

def _coloured_bar(value: float, colour: str) -> str:
    """Return HTML for a 100%-wide bar with a coloured fill."""
    pct = max(0.0, min(100.0, value))
    return (
        f"<div style='background:#e6e6e6;border-radius:4px;height:14px;width:100%;"
        f"overflow:hidden;'>"
        f"<div style='background:{colour};height:100%;width:{pct:.1f}%;"
        f"transition:width .3s;'></div>"
        f"</div>"
    )


def _bar_colour(attr: str, val: float) -> str:
    if attr == "ecosystem_function":
        if val < 25:  return "#d62828"
        if val < 50:  return "#e08e0b"
        return "#2a9d3f"
    if attr == "shrub_density":
        return "#a06030"
    return "#2a9d3f"


def _render_status() -> None:
    g = st.session_state.game
    st.subheader("Ecosystem Status")

    for label, attr, icon in METRIC_DEFS:
        val   = getattr(g, attr)
        delt  = _delta(attr) or ""
        col   = _bar_colour(attr, val)
        delta_html = (
            f"<span style='color:#888;font-size:0.85em;'>&nbsp;{delt}</span>"
            if delt else ""
        )
        st.markdown(
            f"**{icon} {label}**&nbsp;&nbsp;<span style='color:#444;'>"
            f"{val:.1f}%</span>{delta_html}",
            unsafe_allow_html=True,
        )
        st.markdown(_coloured_bar(val, col), unsafe_allow_html=True)

        # Show sub-functions inline under the Ecosystem Function bar
        if attr == "ecosystem_function":
            st.markdown(
                "<div style='margin-left:16px;margin-top:4px;'>",
                unsafe_allow_html=True,
            )
            for sub_label, sub_attr, sub_icon, sub_col in SUB_FN_DEFS:
                sub_val = getattr(g, sub_attr)
                sub_prev = st.session_state.prev.get(sub_attr)
                if sub_prev is not None:
                    d = sub_val - sub_prev
                    sub_delt = f"{'+'  if d >= 0 else ''}{d:.1f}%"
                    sub_delt_html = (
                        f"<span style='color:#888;font-size:0.78em;'>&nbsp;{sub_delt}</span>"
                    )
                else:
                    sub_delt_html = ""
                st.markdown(
                    f"<span style='font-size:0.88em;'>{sub_icon} {sub_label}&nbsp;"
                    f"<span style='color:#444;'>{sub_val:.1f}%</span>"
                    f"{sub_delt_html}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    _coloured_bar(sub_val, sub_col).replace(
                        "height:14px", "height:8px"
                    ),
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        st.write("")  # small spacer

    st.caption(f"🔥 Years since last fire: {g.years_since_fire}")

    # Active invasive species
    if g.invasive_species:
        st.error("⚠️ Active invasive species")
        for sp in g.invasive_species:
            st.markdown(f"&nbsp;&nbsp;**{sp.name}** — Impact: {int(sp.strength * 100)}%")

    # Contextual hints (easy mode only)
    if not g.hard_mode:
        hints = g._diagnostic_hints()
        if hints:
            with st.expander("🔬 Field observations", expanded=True):
                for h in hints:
                    st.info(h)

    # State-transition history
    if g.history:
        with st.expander("📜 State transition history"):
            for h in g.history:
                st.markdown(h)


# ── Action panel (right column) ───────────────────────────────────────────────

def _btn(label: str, key: str, disabled: bool = False) -> bool:
    return st.button(label, key=key, use_container_width=True, disabled=disabled)


def _render_undo_button() -> None:
    stack = st.session_state.undo_stack
    remaining = st.session_state.undos_remaining  # None = unlimited
    can_undo = bool(stack) and (remaining is None or remaining > 0)

    if remaining is None:
        label = "↩️ Undo Last Action"
    elif remaining > 0:
        label = f"↩️ Undo  ({remaining} left)"
    else:
        label = "↩️ Undo  (none left)"

    if st.button(label, key="undo", use_container_width=True, disabled=not can_undo):
        game_snap, prev_snap = stack.pop()
        st.session_state.game = game_snap
        st.session_state.prev = prev_snap
        if remaining is not None:
            st.session_state.undos_remaining = remaining - 1
        st.session_state.submenu = None
        st.session_state.log    = []
        st.session_state.phase  = "main"
        st.rerun()


def _render_main_menu() -> None:
    st.subheader("Management Actions")

    cost = lambda c: f" (${c})" if game.hard_mode else ""

    if _btn(f"🔥 Prescribed Burn{cost(30)}", "burn"):
        _run(game.conduct_prescribed_burn)

    if _btn("🐄 Adjust Grazing", "grazing"):
        st.session_state.submenu = "grazing"
        st.rerun()

    if _btn("🪓 Remove Shrubs", "shrubs"):
        st.session_state.submenu = "shrubs"
        st.rerun()

    if _btn("🌱 Reseed Native Grasses", "reseed"):
        st.session_state.submenu = "reseed"
        st.rerun()

    has_invasives = bool(game.invasive_species)
    if _btn("🚫 Manage Invasive Species", "invasive", disabled=not has_invasives):
        st.session_state.submenu = "invasive"
        st.rerun()

    st.divider()

    if _btn("⏭️ Do Nothing (advance year)", "nothing"):
        _run(game.do_nothing)

    st.divider()

    _render_undo_button()


def _back_btn(target: str | None = None) -> None:
    if _btn("← Back", "back"):
        st.session_state.submenu = target
        st.rerun()


def _render_grazing_menu() -> None:
    st.subheader("Adjust Grazing Pressure")
    st.caption(f"Current: {game.grazing_pressure:.1f}%")

    options = [
        (1, "Remove all livestock (0%)",    0),
        (2, "Light grazing (20%)",           0),
        (3, "Moderate grazing (40%)",        0),
        (4, "Heavy grazing (60%)",           0),
        (5, "Very heavy grazing (80%)",      0),
        (6, "Rotational grazing system",    25),
    ]
    for idx, label, cost in options:
        cost_str = f" (${cost})" if cost and game.hard_mode else ""
        if _btn(f"{label}{cost_str}", f"g{idx}"):
            _run(game.adjust_grazing, choice=idx)

    _back_btn()


def _render_shrubs_menu() -> None:
    st.subheader("Remove Shrubs")

    options = [
        (1, "Selective hand removal  (−10%)",  10),
        (2, "Mechanical clearing     (−30%)",  25),
        (3, "Herbicide application   (−50%)",  35),
        (4, "Integrated management",           45),
    ]
    for idx, label, cost in options:
        cost_str = f" (${cost})" if game.hard_mode else ""
        if _btn(f"{label}{cost_str}", f"s{idx}"):
            _run(game.remove_shrubs, choice=idx)

    _back_btn()


def _render_reseed_menu() -> None:
    st.subheader("Reseed Native Grasses")

    options = [
        (1, "Minimal reseeding   (+10%)",   15),
        (2, "Moderate reseeding  (+25%)",   30),
        (3, "Intensive reseeding (+40%)",   50),
        (4, "Experimental native seed mix", 40),
    ]
    for idx, label, cost in options:
        cost_str = f" (${cost})" if game.hard_mode else ""
        if _btn(f"{label}{cost_str}", f"r{idx}"):
            _run(game.reseed_grasses, choice=idx)

    _back_btn()


def _render_invasive_menu() -> None:
    st.subheader("Invasive Species Management")

    grazable = any(sp.effect in GRAZABLE_INVASIVE_EFFECTS for sp in game.invasive_species)

    options = [
        (1, "Targeted removal",              25),
        (2, "Biocontrol introduction",       40),
        (3, "Comprehensive management",      50),
        (4, "Targeted/conservation grazing", 30, not grazable),
    ]
    for row in options:
        idx, label, cost = row[0], row[1], row[2]
        disabled = row[3] if len(row) > 3 else False
        cost_str = f" (${cost})" if game.hard_mode else ""

        if idx == 1:
            # Targeted removal needs a species picker — go to sub-sub-menu
            if _btn(f"{label}{cost_str}", f"i{idx}", disabled=disabled):
                st.session_state.submenu = "inv_target"
                st.rerun()
        else:
            if _btn(f"{label}{cost_str}", f"i{idx}", disabled=disabled):
                _run(game.manage_invasive_species, choice=idx)

    if not grazable:
        st.caption("Grazing option disabled — no palatable invaders currently present.")

    _back_btn()


def _render_inv_target_menu() -> None:
    st.subheader("Select Target Species")

    for i, sp in enumerate(game.invasive_species, 1):
        label = f"{sp.name}  (Impact: {int(sp.strength * 100)}%)"
        if _btn(label, f"t{i}"):
            _run(game.manage_invasive_species, choice=1, target_idx=i)

    _back_btn(target="invasive")


SUBMENU_RENDERERS = {
    "grazing":    _render_grazing_menu,
    "shrubs":     _render_shrubs_menu,
    "reseed":     _render_reseed_menu,
    "invasive":   _render_invasive_menu,
    "inv_target": _render_inv_target_menu,
}


# ── Event log (below main columns) ───────────────────────────────────────────

def _render_log() -> None:
    if not st.session_state.log:
        return
    year_shown = max(1, game.year - 1)
    with st.expander(f"📋 Year {year_shown} events", expanded=True):
        for msg in st.session_state.log:
            if msg.strip():
                st.markdown(msg)


# ── Score helpers ─────────────────────────────────────────────────────────────

def _score_bar(score: int) -> None:
    stars = min(5, max(0, score // 40))
    st.markdown("★" * stars + "☆" * (5 - stars))


# ── Pages ─────────────────────────────────────────────────────────────────────

def _page_intro() -> None:
    st.title("🌿 Ecosystem Management")
    st.subheader("State & Transition Adventure")

    st.markdown("""
    You are managing a grassland ecosystem that can exist in **multiple stable states**.
    Your goal: restore and maintain a healthy grassland over **30 years**.

    The grass community is tracked in three dimensions:
    | Dimension | What it measures |
    |---|---|
    | **Cover** | Structural presence of grass on the ground |
    | **Biomass** | Standing crop and litter — the fire fuel load |
    | **Diversity** | Species richness of the grass community |

    Productive grassland with no disturbance accumulates biomass, which suppresses
    diversity and ecosystem function.  Both **fire** and **appropriate grazing**
    are needed to keep the system open and diverse.

    **Ecosystem function** is the composite of three sub-processes that respond
    differently to your decisions:
    | Sub-function | What drives it |
    |---|---|
    | 🌾 **Productivity** | Plant growth — needs cover, diversity *and* healthy soil |
    | 🪱 **Soil function** | Organic matter, microbes, structure — slow to build, fast to lose |
    | 💧 **Hydrology** | Infiltration and water retention — depends on cover and soil |

    Soil is the **limiting factor**: degraded soil caps how high productivity and
    hydrology can climb, no matter how much grass you have. Some interventions
    (like herbicide) damage soil — be careful what you reach for.

    > ⚠️ You begin in a **degraded, shrub-encroached state** — restoration is the challenge.
    """)

    st.divider()
    st.subheader("Choose your ecosystem type")
    st.markdown("""
    The **evolutionary grazing history** of your grassland fundamentally changes how
    it responds to management — based on [Cingolani, Noy-Meir & Díaz (2005)](https://doi.org/10.1890/03-5272).
    """)

    col_l, col_r = st.columns(2)
    with col_l:
        st.success("""
        **🌍 Long evolutionary history**
        *(African savanna, Eurasian steppe, Pampas)*
        - Native grasses co-evolved with large herbivores
        - Two species pools: grazing-adapted + grazing-tolerant
        - Moderate grazing can *increase* diversity
        - Overgrazing is **reversible** — reduce pressure, system recovers
        - Soil stability partly decoupled from cover
        - Lower invasion risk
        """)
    with col_r:
        st.error("""
        **🦘 Short evolutionary history**
        *(Australia, New Zealand, pre-colonial Americas)*
        - Native plants have no evolved grazing defences
        - No pre-adapted species pool — any sustained overgrazing hurts
        - State transitions are **irreversible** — thresholds are real
        - Soil collapses rapidly when cover is lost
        - Higher invasion risk (introduced grazers' weeds are competitive)
        """)

    history = st.radio(
        "Evolutionary grazing history",
        ["Long history", "Short history"],
        horizontal=True,
    )

    st.divider()
    st.subheader("Choose difficulty")
    col1, col2 = st.columns(2)
    with col1:
        st.info("""
        **Easy mode**
        - Field observations and ecologist tips
        - No budget constraint
        - Focus on the ecology
        """)
    with col2:
        st.warning(f"""
        **Hard mode**
        - No hints
        - Tight management budget (start ${EcosystemAdventure.STARTING_BUDGET},
          +${EcosystemAdventure.ANNUAL_BUDGET}/yr)
        - Every dollar matters
        """)

    difficulty = st.radio("Choose difficulty", ["Easy", "Hard"], horizontal=True)

    if st.button("🌱 Start Game", type="primary", use_container_width=True):
        g = EcosystemAdventure()
        g.headless        = True
        g.hard_mode       = (difficulty == "Hard")
        g.grazing_history = "long" if history == "Long history" else "short"
        st.session_state.game             = g
        st.session_state.log              = []
        st.session_state.phase            = "main"
        st.session_state.undo_stack       = []
        st.session_state.undos_remaining  = 3 if g.hard_mode else None
        _save_prev()  # need game bound for _save_prev
        st.rerun()


def _page_main() -> None:
    icon  = STATE_COLOUR.get(game.current_state, "⚪")
    hist_tag = "🌍 Long history" if game._long_history else "🦘 Short history"
    title = f"{icon} Year {game.year} / {game.GAME_LENGTH}  —  {game.current_state.value}  |  {hist_tag}"

    if game.hard_mode:
        title += f"  |  Budget: ${game.budget}"

    st.title(title)

    left, right = st.columns([3, 2], gap="large")

    with left:
        _render_status()

    with right:
        submenu = st.session_state.submenu
        renderer = SUBMENU_RENDERERS.get(submenu, _render_main_menu)
        renderer()

    _render_log()


def _page_gameover() -> None:
    if game.year >= game.GAME_LENGTH:
        st.balloons()
        st.title("🎉 Congratulations — 30 years managed!")
    else:
        st.title("💀 Ecosystem Collapsed")
        st.error("Ecosystem function reached zero. The land can no longer support its community.")

    endings = {
        State.GRASSLAND:  ("🌿 GRASSLAND maintained",
                           "The grass–fire feedback loop is intact and functioning."),
        State.TRANSITION: ("⚠️ TRANSITION state at end",
                           "The ecosystem is neither fully grass nor shrub dominated."),
        State.SHRUBLAND:  ("🌳 SHRUBLAND — woody plants dominate",
                           "Shrubs have established a positive feedback that is hard to reverse."),
    }
    headline, detail = endings[game.current_state]
    st.subheader(headline)
    st.markdown(detail)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Final statistics")

        def _stat_row(label: str, value: str) -> None:
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"padding:4px 0;border-bottom:1px solid #eee;'>"
                f"<span style='color:#444;'>{label}</span>"
                f"<span style='font-weight:600;'>{value}</span></div>",
                unsafe_allow_html=True,
            )

        _stat_row("Grass cover",        f"{game.grass_cover:.1f}%")
        _stat_row("Grass biomass",      f"{game.grass_biomass:.1f}%")
        _stat_row("Grass diversity",    f"{game.grass_diversity:.1f}%")
        _stat_row("Shrub density",      f"{game.shrub_density:.1f}%")
        _stat_row("Ecosystem function", f"{game.ecosystem_function:.1f}%")

        st.markdown(
            "<div style='margin-top:10px;font-size:0.9em;color:#666;'>"
            "Sub-functions:</div>",
            unsafe_allow_html=True,
        )
        for sub_label, sub_attr, sub_icon, sub_col in SUB_FN_DEFS:
            sub_val = getattr(game, sub_attr)
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;padding:2px 0;'>"
                f"<span style='color:#444;'>&nbsp;&nbsp;{sub_icon} {sub_label}</span>"
                f"<span style='font-weight:600;color:{sub_col};'>{sub_val:.1f}%</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                _coloured_bar(sub_val, sub_col).replace("height:14px", "height:6px"),
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        _stat_row("State transitions",     str(len(game.history)))
        _stat_row("Invasive species",      str(len(game.invasive_species)))
        _stat_row("Optimal fire interval", f"every {game.optimal_fire_interval} yrs")

    with col2:
        score = game._compute_score()
        st.subheader(f"Final Score: {score} / 200")
        _score_bar(score)
        st.markdown(f"**{game._rating(score)}**")

        st.divider()
        if game.history:
            st.subheader("State transition history")
            for h in game.history:
                st.markdown(h)

    st.divider()
    if st.button("🌱 Play Again", type="primary", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────

phase = st.session_state.phase

if phase == "intro":
    _page_intro()

elif phase in ("main",):
    # game must exist at this point
    _page_main()

elif phase == "gameover":
    _page_gameover()

else:
    # Fallback — shouldn't happen, but prevents a blank screen
    st.session_state.phase = "intro"
    st.rerun()
