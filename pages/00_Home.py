from __future__ import annotations

import streamlit as st

from ui_theme import (
    apply_theme,
    ensure_session_defaults,
    money,
    render_page_header,
    render_section_heading,
)

apply_theme()
ensure_session_defaults()

render_page_header(
    "Your Personal AI Stylist",
    "Discover outfits tailored to your skin tone, proportions, style aesthetic and budget.",
    active="Home",
)

st.markdown(
    """
    <div class="hero-panel">
        <div class="page-kicker">WELCOME TO STYLEAI</div>
        <div style="font-size: clamp(1.8rem, 2.5vw, 2.8rem); font-weight: 900; line-height: 1.1; color: #1f162d; margin-top: 0.2rem;">
            AI Outfit Recommendation & Virtual Styling System
        </div>
        <div style="margin-top: 0.6rem; color: #5f5a6d; font-size: 0.98rem;">
            Experience personalized fashion styling guided by your skin tone, body proportions, preferred aesthetics, and occasion contexts.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

cta_start, cta_avatar, cta_market = st.columns(3)
with cta_start:
    if st.button("🚀 Start Onboarding Journey →", type="primary", use_container_width=True):
        st.switch_page("pages/01_My_Profile.py")

with cta_avatar:
    if st.button("🧑‍🎨 Open Avatar Studio", use_container_width=True):
        st.switch_page("pages/01_Avatar.py")

with cta_market:
    if st.button("🛍️ Browse Marketplace", use_container_width=True):
        st.switch_page("pages/04_AI_Outfit_Recommendations.py")

st.markdown("<br>", unsafe_allow_html=True)
render_section_heading("Your Progressive Styling Journey", "🧭")

journey_steps = [
    ("1", "Basic Profile Input", "Enter name, gender, age, height, weight and set your interactive budget slider."),
    ("2", "Step-by-Step Appearance", "Progressively set your skin tone, favourite colours, preferred style, and occasion."),
    ("3", "Photo or Avatar Choice", "Select between uploading a full-body photo or entering the Avatar Studio."),
    ("4", "Professional Avatar Builder", "Customize hair, skin tone, body silhouette, and model pose with live updates."),
    ("5", "Preference Analysis", "Tell your AI stylist your mood and generate a tailored style direction."),
    ("6", "Fashion Marketplace", "Browse curated clothing items with fabric details, ratings, and store sources."),
    ("7", "Complete Outfit Dashboard", "Review your complete look, Swiggy-style breakdown, fabric notes, and cost totals."),
]

for num, title, desc in journey_steps:
    st.markdown(
        f"""
        <div class="journey-item" style="margin-bottom:0.6rem;">
            <div class="journey-num">{num}</div>
            <div>
                <div style="font-weight:800; color:#1f162d; font-size:0.92rem;">{title}</div>
                <div style="font-size:0.78rem; color:#625b6e;">{desc}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
render_section_heading("Current Profile Snapshot", "📊")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">User Profile</div>
            <div class="stat-value">{st.session_state.user_name}</div>
            <div class="stat-detail">{st.session_state.gender} · {st.session_state.age} yrs</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">Style Budget</div>
            <div class="stat-value">{money(float(st.session_state.budget))}</div>
            <div class="stat-detail">Spending limit</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">Style Aesthetic</div>
            <div class="stat-value">{st.session_state.style}</div>
            <div class="stat-detail">Current preference</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">Occasion</div>
            <div class="stat-value">{st.session_state.occasion}</div>
            <div class="stat-detail">Planned setting</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
