from __future__ import annotations

import streamlit as st

from ui_theme import apply_theme, ensure_session_defaults, money, render_page_header, render_section_heading

apply_theme()
ensure_session_defaults()

render_page_header("Style Within Your Budget", "See how your outfit compares to your target spend and where you can save.")

budget = float(st.session_state.budget)
current_price = 5795
remaining = budget - current_price

st.markdown(
    f"""
    <div class='budget-box'>
        <div class='page-kicker'>Budget overview</div>
        <div style='font-size:1.8rem; font-weight:800; color:#1d1528; margin-top:0.2rem;'>Your budget: {money(budget)}</div>
        <div style='color:#5f5a6d; margin-top:0.2rem;'>Current outfit: {money(current_price)}</div>
        <div style='margin-top:0.7rem; font-weight:700; color:{'#9a2d4a' if remaining < 0 else '#2f7d57'};'>{'Over budget by ' + money(abs(remaining)) if remaining < 0 else 'Within budget by ' + money(remaining)}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
render_section_heading("Smart replacement suggestions", "💡")
alt_cards = [
    ("White Sneakers", "₹1,799", "Black Sneakers", "₹699", "Save ₹1,100"),
    ("Leather Watch", "₹2,499", "Minimal Watch", "₹1,299", "Save ₹1,200"),
    ("Denim Jacket", "₹2,999", "Cotton Overshirt", "₹1,699", "Save ₹1,300"),
]
for current_name, current_price_txt, alt_name, alt_price_txt, save_txt in alt_cards:
    st.markdown(
        f"""
        <div class='panel' style='margin-bottom:0.8rem;'>
            <div style='display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap;'><div><div class='small-muted'>Current</div><div style='font-weight:800; color:#1d1528;'>{current_name}</div><div class='small-muted'>{current_price_txt}</div></div><div><div class='small-muted'>Alternative</div><div style='font-weight:800; color:#1d1528;'>{alt_name}</div><div class='small-muted'>{alt_price_txt}</div></div></div>
            <div style='margin-top:0.8rem; font-weight:700; color:#5e3b80;'>{save_txt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
render_section_heading("Budget status", "📊")
progress = 75
st.markdown(
    f"""
    <div class='panel'>
        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;'><div class='score-label'>₹2,595 / ₹3,000</div><div class='pill'>Within budget ✓</div></div>
        <div class='progress-bar'><span class='progress-fill' style='width:{progress}%'></span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    if st.button("← Back to Outfit Details"):
        st.switch_page("pages/05_Outfit_Details.py")
with col2:
    if st.button("Interactive Pairing →", type="primary", use_container_width=True):
        st.switch_page("pages/08_Interactive_Pairing.py")
