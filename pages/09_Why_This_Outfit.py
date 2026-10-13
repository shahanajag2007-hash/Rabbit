from __future__ import annotations

import streamlit as st

from ui_theme import apply_theme, ensure_session_defaults, render_page_header, render_section_heading

apply_theme()
ensure_session_defaults()

render_page_header("Why This Outfit?", "A clearer, structured explanation of how the recommendation fits your choice.")

if not st.session_state.selected_outfit:
    st.info("Select a recommendation first to view the score breakdown.")
    st.stop()

outfit = st.session_state.selected_outfit
breakdown = outfit.get("breakdown", {})

st.markdown(
    f"""
    <div class='panel'>
        <div class='page-kicker' style='margin-bottom:0.2rem;'>Overall match</div>
        <div style='font-size:2rem; font-weight:800; color:#1d1528;'>{outfit.get('score', 0):.0f} / 100</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
score_items = [
    ("🎨 Colour Match", breakdown.get("colour", 0.0), 30),
    ("👗 Style Match", breakdown.get("style", 0.0), 20),
    ("📍 Occasion Match", breakdown.get("occasion", 0.0), 20),
    ("🔗 Outfit Compatibility", breakdown.get("compatibility", 0.0), 15),
    ("💰 Budget Fit", breakdown.get("budget", 0.0), 15),
]
for label, value, total in score_items:
    percentage = (value / total) * 100 if total else 0
    st.markdown(
        f"""
        <div class='panel' style='margin-bottom:0.7rem;'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;'><div style='font-weight:700; color:#20192d;'>{label}</div><div style='font-weight:800; color:#1d1528;'>{value:.1f} / {total}</div></div>
            <div class='progress-bar'><span class='progress-fill' style='width:{percentage}%'></span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
render_section_heading("Why it suits you", "✨")
explanations = [
    ("🎨 Colour Harmony", "The selected palette keeps the outfit polished and visually balanced with your overall style preferences."),
    ("👗 Style Compatibility", f"This look supports the chosen {st.session_state.style.lower()} direction and maintains a cohesive identity."),
    ("📍 Occasion Fit", f"The outfit is designed for {st.session_state.occasion.lower()} and aligns with the mood of the setting."),
    ("💰 Budget Fit", "The outfit remains conscious of your spend while still expressing a complete fashion-forward look."),
    ("✨ Overall Styling", "This combination balances comfort, polish and outfit coordination in a way that feels confident and intentional."),
]
for title, description in explanations:
    st.markdown(
        f"""
        <div class='explain-card' style='margin-bottom:0.7rem;'>
            <h4>{title}</h4>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    """
    <div class='panel' style='background:linear-gradient(135deg, rgba(110,83,170,0.08), rgba(239,125,143,0.08));'>
        <div class='page-kicker'>AI stylist summary</div>
        <div style='font-size:1.05rem; font-weight:700; color:#20192d; line-height:1.6;'>"This combination balances your selected style, occasion and budget while keeping the outfit visually coordinated."</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    if st.button("← Back to Interactive Pairing"):
        st.switch_page("pages/08_Interactive_Pairing.py")
with col2:
    if st.button("Virtual Styling →", type="primary", use_container_width=True):
        st.switch_page("pages/10_Virtual_Styling___Preview.py")
