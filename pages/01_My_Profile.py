from __future__ import annotations

import streamlit as st

from ui_theme import (
    apply_theme,
    ensure_session_defaults,
    money,
    render_page_header,
    render_section_heading,
    render_step_progress,
)

apply_theme()
ensure_session_defaults()

render_page_header(
    "Welcome to STYLEAI",
    "Let's build your personalized fashion profile to get started.",
    active="01 Profile",
)

render_step_progress(step_num=1, total_steps=5, step_title="Basic Profile Input")

st.markdown(
    """
    <div class="hero-panel" style="margin-bottom: 1.2rem;">
        <div class="page-kicker">ONBOARDING STAGE 1</div>
        <div style="font-size: clamp(1.4rem, 2.2vw, 2.2rem); font-weight: 800; color: #1f162d; margin-top: 0.2rem;">
            Tell Us About Yourself
        </div>
        <div style="color: #5f5a6d; font-size: 0.92rem; margin-top: 0.3rem;">
            Your height, weight, gender and budget allow our virtual styling engine to tailor proportions, fits and recommendations.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col_left, col_right = st.columns([1.1, 1], gap="large")

with col_left:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    render_section_heading("Personal Identity", "👤")

    name = st.text_input("Full Name", value=st.session_state.get("user_name", "Alex"))
    st.session_state.user_name = name

    col_age, col_gender = st.columns(2)
    with col_age:
        age = st.number_input("Age", min_value=14, max_value=90, value=int(st.session_state.get("age", 22)))
        st.session_state.age = age

    with col_gender:
        gender_options = ["Female", "Male", "Non-binary"]
        current_gender = st.session_state.get("gender", "Female")
        gender = st.selectbox(
            "Gender Identity",
            gender_options,
            index=gender_options.index(current_gender) if current_gender in gender_options else 0,
        )
        st.session_state.gender = gender

    render_section_heading("Body Proportions", "📏")
    col_h, col_w = st.columns(2)
    with col_h:
        height = st.slider(
            "Height (cm)",
            min_value=140,
            max_value=210,
            value=int(st.session_state.get("height", 168)),
            step=1,
        )
        st.session_state.height = height

    with col_w:
        weight = st.slider(
            "Weight (kg)",
            min_value=35,
            max_value=140,
            value=int(st.session_state.get("weight", 58)),
            step=1,
        )
        st.session_state.weight = weight

    st.markdown("</div>", unsafe_allow_html=True)

with col_right:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    render_section_heading("Style Budget", "💳")

    current_budget = float(st.session_state.get("budget", 3500.0))
    budget_val = st.slider(
        "Select your preferred outfit budget limit",
        min_value=500,
        max_value=10000,
        value=int(current_budget),
        step=250,
        format="₹%d",
    )
    st.session_state.budget = float(budget_val)

    # Budget Card Display
    pct = max(0, min(100, int(((budget_val - 500) / (10000 - 500)) * 100)))
    st.markdown(
        f"""
        <div class="budget-display-card">
            <div class="budget-label">YOUR STYLE BUDGET</div>
            <div class="budget-value">{money(float(budget_val))}</div>
            <div class="budget-slider-visual">
                <span>₹500</span>
                <div class="budget-track">
                    <div class="budget-track-fill" style="width: {pct}%;"></div>
                </div>
                <span>₹10,000</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='mini-card'>", unsafe_allow_html=True)
    st.markdown("<div class='page-kicker' style='margin-bottom:0.4rem;'>Profile Summary</div>", unsafe_allow_html=True)
    st.write(f"• **Name**: {st.session_state.user_name}")
    st.write(f"• **Gender**: {st.session_state.gender} ({st.session_state.age} yrs)")
    st.write(f"• **Height & Weight**: {st.session_state.height} cm · {st.session_state.weight} kg")
    st.write(f"• **Budget**: {money(float(st.session_state.budget))}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col_nav_l, col_nav_r = st.columns([1, 1])
with col_nav_r:
    if st.button("CONTINUE TO APPEARANCE →", type="primary", use_container_width=True):
        st.session_state.step_progress = 2
        st.switch_page("pages/02_Appearance___Colour.py")
