from __future__ import annotations

import streamlit as st

from ui_theme import (
    apply_theme,
    ensure_session_defaults,
    render_page_header,
    render_section_heading,
    render_step_progress,
)

apply_theme()
ensure_session_defaults()

render_page_header(
    "Fine-Tune Style Signals",
    "Detailed fit, brand preferences, fabric choices and avoided styles.",
    active="03 Preferences",
)

render_step_progress(step_num=2, total_steps=5, step_title="Detailed Style Signals")

with st.container(border=True):
    col1, col2 = st.columns(2, gap="large")

    with col1:
        render_section_heading("Fit & Silhouette Preference", "👗")
        fits = ["Loose / Oversized", "Regular Fit", "Slim / Fitted"]
        current_fit = st.session_state.get("preferred_fit", "Regular Fit")
        fit_choice = st.radio("Preferred Cut", fits, index=fits.index(current_fit) if current_fit in fits else 1)
        st.session_state.preferred_fit = fit_choice

        render_section_heading("Fabric & Textile Preferences", "🧵")
        fabrics = ["Breathable Linen", "Crisp Cotton Blend", "Classic Denim", "Silk & Satin", "Soft Supima Cotton", "Handloom Khadi"]
        selected_fabrics = st.multiselect("Preferred Fabrics", fabrics, default=["Breathable Linen", "Crisp Cotton Blend"])
        st.session_state.preferred_fabrics = selected_fabrics

    with col2:
        render_section_heading("Colours & Styles to Avoid", "🚫")
        avoid = ["Neon / Flashy", "Overly Bright", "Dense Layering", "Clashing Tones", "Pastels"]
        current_avoid = st.session_state.get("avoid_colours", ["Neon / Flashy"])
        selected_avoid = st.multiselect("Styles & Tones I Avoid", avoid, default=current_avoid)
        st.session_state.avoid_colours = selected_avoid

        render_section_heading("Favorite Fashion Brands", "🛍️")
        brands = ["ZARA", "UNIQLO", "H&M", "FabIndia", "Mango", "Levi's", "Adidas", "Aldo", "Myntra"]
        selected_brands = st.multiselect("Preferred Stores / Brands", brands, default=["ZARA", "UNIQLO", "Myntra"])
        st.session_state.preferred_brands = selected_brands

st.markdown("<br>", unsafe_allow_html=True)

col_b1, col_b2 = st.columns(2)
with col_b1:
    if st.button("← Back to Appearance Inputs", use_container_width=True):
        st.switch_page("pages/02_Appearance___Colour.py")

with col_b2:
    if st.button("PROCEED TO AVATAR BUILDER →", type="primary", use_container_width=True):
        st.session_state.step_progress = 3
        st.switch_page("pages/01_Avatar.py")
