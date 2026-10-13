from __future__ import annotations

import streamlit as st

from ui_theme import apply_theme, ensure_session_defaults, render_page_header, render_section_heading

apply_theme()
ensure_session_defaults()

render_page_header("See Your Look", "Preview the complete outfit before you finalize it.")

import streamlit.components.v1 as components
from avatar_engine import render_fashion_avatar_svg

cart = st.session_state.get("cart_items", {})

with st.container(border=True):
    if cart and st.session_state.get("avatar_builder"):
        svg_preview_html = render_fashion_avatar_svg(st.session_state.avatar_builder, outfit_items=cart, full_component=True)
        components.html(svg_preview_html, height=530, scrolling=False)
    else:
        st.markdown(
            """
            <div class='page-kicker'>Virtual preview</div>
            <div style='height:220px; border-radius:20px; background:linear-gradient(135deg, #f0ebff, #ffeef2); display:flex; align-items:center; justify-content:center; flex-direction:column; text-align:center; color:#4d3a6c; border:1px dashed rgba(108,75,176,0.28);'>
                <div style='font-size:3rem;'>🪞</div>
                <div style='font-weight:800; margin-top:0.3rem;'>Your virtual look</div>
                <div class='small-muted' style='margin-top:0.2rem;'>Preview will appear here once you select an outfit</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

import recommender
from ui_theme import money

cart = st.session_state.get("cart_items", {})
outfit = st.session_state.get("selected_outfit", {})
user_profile = st.session_state.get("user_profile", {})

if not outfit:
    st.info("Please select an outfit to preview.")
    st.stop()

# Score and price calculations
current_score_info = recommender.score_single_outfit(outfit, user_profile)
total_price = current_score_info["total_price"]
budget = float(user_profile.get("budget", 3500.0))
budget_diff = budget - total_price

st.markdown(f"<div style='background: {'#f0fdf4' if budget_diff >= 0 else '#fef2f2'}; padding:1rem; border-radius:12px; margin-bottom:1.5rem;'>", unsafe_allow_html=True)
st.markdown(f"**Total Outfit Price:** {money(total_price)} (Budget: {money(budget)})")
if budget_diff < 0:
    st.markdown(f"<span style='color:#dc2626;'>Over budget by {money(abs(budget_diff))}</span>", unsafe_allow_html=True)
else:
    st.markdown(f"<span style='color:#16a34a;'>Under budget by {money(budget_diff)}</span>", unsafe_allow_html=True)
st.markdown(f"**Compatibility Score:** {current_score_info['score']}/100")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
render_section_heading("Selected outfit details", "👗")
col1, col2, col3, col4 = st.columns(4)
for col, icon, name in zip([col1, col2, col3, col4], ["👕", "👖", "👟", "⌚"], ["Top", "Bottom", "Shoes", "Accessory"]):
    with col:
        item = cart.get(name)
        item_text = item.get("item_name") if item else "Not Selected"
        st.markdown(f"<div class='mini-card'><div style='font-size:2rem; margin-bottom:0.4rem;'>{icon}</div><div style='font-weight:700; color:#20192d;'>{name}</div><div style='font-size:0.8rem; color:#625b6e;'>{item_text}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("← Back to Why This Outfit"):
        st.switch_page("pages/09_Why_This_Outfit.py")
with col_b:
    st.button("↻ Regenerate preview")
with col_c:
    if st.button("Multi Identity →", type="primary"):
        st.switch_page("pages/11_Multi_Identity.py")
