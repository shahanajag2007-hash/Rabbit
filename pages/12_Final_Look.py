from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from avatar_engine import render_fashion_avatar_svg
from ui_theme import (
    apply_theme,
    ensure_session_defaults,
    money,
    render_page_header,
)

apply_theme()
ensure_session_defaults()

render_page_header(
    "Final Look & Order Summary",
    "Congratulations! Your personalized outfit styling is complete and ready to wear.",
    active="Final Look",
)

builder = st.session_state.avatar_builder
cart = st.session_state.cart_items
total_cost = sum(float(item.get("price", 0)) for item in cart.values() if item)

st.markdown("<div class='panel'>", unsafe_allow_html=True)
col_l, col_r = st.columns([1, 1.2], gap="large")

with col_l:
    svg_final = render_fashion_avatar_svg(builder, outfit_items=cart, full_component=True)
    components.html(svg_final, height=530, scrolling=False)

with col_r:
    hero_html = f"""<div class="hero-panel" style="height:100%; display:flex; flex-direction:column; justify-content:center;">
<div class="page-kicker">STYLING READY</div>
<div style="font-size: 2rem; font-weight: 900; color: #1f162d; margin-top: 0.2rem;">
{st.session_state.user_name}'s {st.session_state.occasion} Style
</div>
<div style="color: #5f5a6d; font-size: 0.9rem; margin-top: 0.4rem; line-height: 1.55;">
Your complete look is optimized for <strong>{st.session_state.occasion}</strong> propriety, complements your <strong>{st.session_state.skin_tone}</strong> skin tone, and totals <strong>{money(total_cost)}</strong>.
</div>
<div style="margin-top: 1.5rem;">
<div class="stat-card">
<div class="stat-label">Total Outfitted Spend</div>
<div class="stat-value">{money(total_cost)}</div>
<div class="stat-detail">Budget Target: {money(float(st.session_state.budget))}</div>
</div>
</div>
</div>"""
    st.markdown(hero_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col_act1, col_act2 = st.columns(2)

with col_act1:
    if st.button("🔄 Restart Styling Journey", use_container_width=True):
        st.session_state.step_progress = 1
        st.switch_page("pages/01_My_Profile.py")

with col_act2:
    if st.button("✨ Modify Complete Look", type="primary", use_container_width=True):
        st.switch_page("pages/05_Outfit_Details.py")
