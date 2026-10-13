from __future__ import annotations

import streamlit as st

from ui_theme import apply_theme, ensure_session_defaults, render_page_header, render_section_heading

apply_theme()
ensure_session_defaults()

render_page_header("Build Your Outfit Piece by Piece", "Pair your selected item with complementary options.")

selected = "Blue Shirt"
options = [
    ("Black Jeans", "Indigo", "₹1,299"),
    ("Beige Trousers", "Sand", "₹1,699"),
    ("White Skirt", "Ivory", "₹1,499"),
]

st.markdown(
    f"""
    <div class='panel'>
        <div class='page-kicker'>Selected item</div>
        <div style='display:flex; align-items:center; gap:1rem; margin-top:0.5rem; flex-wrap:wrap;'>
            <div style='width:110px; height:110px; border-radius:18px; background:linear-gradient(135deg, #ebe1ff, #ffe9ec); display:flex; align-items:center; justify-content:center; font-size:3rem;'>👕</div>
            <div>
                <div style='font-size:1.3rem; font-weight:800; color:#1d1528;'>{selected}</div>
                <div class='small-muted'>Blue · Casual · ₹899</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
render_section_heading("Suggested pairings", "🤝")
for name, colour, price in options:
    with st.container(border=True):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown(
                f"""
                <div style='display:flex; align-items:center; gap:0.8rem;'>
                    <div style='width:70px; height:70px; border-radius:16px; background:linear-gradient(135deg, #ecf1ff, #fef1f6); display:flex; align-items:center; justify-content:center; font-size:2rem;'>👖</div>
                    <div>
                        <div style='font-weight:800; color:#1d1528;'>{name}</div>
                        <div class='small-muted'>{colour} · {price}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                st.button("✓ Add", key=f"add_{name}")
            with bcol2:
                st.button("↻ Show another", key=f"another_{name}")

st.markdown("<br>", unsafe_allow_html=True)
render_section_heading("Pairing flow", "🔗")
flow = ["Selected Item", "Suggested Pair", "Next Pair", "Complete Outfit"]
for idx, item in enumerate(flow):
    st.markdown(f"<div class='chip' style='margin-right:0.4rem; margin-bottom:0.4rem;'>{item}</div>", unsafe_allow_html=True)
    if idx < len(flow)-1:
        st.markdown("<div style='display:inline-block; margin:0 0.3rem 0.6rem 0; color:#8c7ea4;'>↓</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    if st.button("← Back to Budget Stylist"):
        st.switch_page("pages/07_Budget_Stylist.py")
with col2:
    if st.button("Why This Outfit →", type="primary", use_container_width=True):
        st.switch_page("pages/09_Why_This_Outfit.py")
