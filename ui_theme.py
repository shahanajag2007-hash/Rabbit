from __future__ import annotations

import streamlit as st

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background: linear-gradient(180deg, #f8f2ff 0%, #fffaf7 48%, #ffffff 100%);
        color: #1b1627;
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
        max-width: 1400px;
    }

    /* ==========================================================================
       GLOBAL BUTTON FIXES (ISSUE 1 RESOLUTION)
       Ensures ALL Streamlit buttons have fully visible text in normal, hover,
       active, focus, and disabled states.
       ========================================================================== */
    
    /* Default / Secondary Streamlit Buttons */
    div.stButton > button,
    button[kind="secondary"],
    .stButton > button {
        background: #f5efff !important;
        background-color: #f5efff !important;
        color: #2d174d !important;
        border: 1.5px solid rgba(107, 75, 176, 0.25) !important;
        border-radius: 14px !important;
        font-weight: 800 !important;
        font-size: 0.88rem !important;
        padding: 0.55rem 1.1rem !important;
        box-shadow: 0 4px 12px rgba(45, 30, 65, 0.04) !important;
        transition: all 0.2s ease !important;
        opacity: 1 !important;
        text-shadow: none !important;
    }

    div.stButton > button p,
    div.stButton > button span,
    button[kind="secondary"] p,
    button[kind="secondary"] span {
        color: #2d174d !important;
        -webkit-text-fill-color: #2d174d !important;
        opacity: 1 !important;
        font-weight: 800 !important;
    }

    div.stButton > button:hover,
    button[kind="secondary"]:hover {
        background: #ebe2fc !important;
        background-color: #ebe2fc !important;
        color: #1f0f38 !important;
        border-color: #6b4bb0 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(107, 75, 176, 0.18) !important;
    }

    div.stButton > button:hover p,
    div.stButton > button:hover span {
        color: #1f0f38 !important;
        -webkit-text-fill-color: #1f0f38 !important;
    }

    div.stButton > button:focus,
    div.stButton > button:active {
        background: #e4d6f9 !important;
        background-color: #e4d6f9 !important;
        color: #1f0f38 !important;
        border-color: #6b4bb0 !important;
        box-shadow: 0 0 0 3px rgba(107, 75, 176, 0.25) !important;
    }

    div.stButton > button:focus p,
    div.stButton > button:focus span,
    div.stButton > button:active p,
    div.stButton > button:active span {
        color: #1f0f38 !important;
        -webkit-text-fill-color: #1f0f38 !important;
    }

    /* Primary Streamlit Buttons */
    div.stButton > button[kind="primary"],
    button[kind="primary"] {
        background: linear-gradient(135deg, #6a4bb0, #ef7d8f) !important;
        background-color: #6a4bb0 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 800 !important;
        font-size: 0.88rem !important;
        padding: 0.6rem 1.2rem !important;
        box-shadow: 0 8px 20px rgba(106, 75, 176, 0.28) !important;
        opacity: 1 !important;
    }

    div.stButton > button[kind="primary"] p,
    div.stButton > button[kind="primary"] span,
    button[kind="primary"] p,
    button[kind="primary"] span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
        font-weight: 800 !important;
    }

    div.stButton > button[kind="primary"]:hover,
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #5b3fa1, #e06c7e) !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 12px 26px rgba(106, 75, 176, 0.38) !important;
    }

    div.stButton > button[kind="primary"]:hover p,
    div.stButton > button[kind="primary"]:hover span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    /* Top Brand Nav Header */
    .brand-shell {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(76, 51, 112, 0.10);
        border-radius: 24px;
        padding: 1rem 1.4rem;
        box-shadow: 0 14px 30px rgba(55, 38, 83, 0.06);
        margin-bottom: 1.2rem;
    }

    .brand-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
    }

    .brand-left {
        display: flex;
        align-items: center;
        gap: 0.85rem;
    }

    .brand-mark {
        width: 48px;
        height: 48px;
        border-radius: 16px;
        background: linear-gradient(135deg, #6b4bb0, #ef7d8f);
        display: flex;
        justify-content: center;
        align-items: center;
        color: white;
        font-size: 1.4rem;
        box-shadow: 0 8px 18px rgba(108, 75, 176, 0.25);
    }

    .brand-title {
        font-size: 1.15rem;
        font-weight: 800;
        line-height: 1.2;
        margin: 0;
        color: #1f162c;
    }

    .brand-sub {
        font-size: 0.78rem;
        color: #665f72;
        margin: 0.15rem 0 0;
    }

    .nav-pill {
        background: linear-gradient(135deg, #f0eaff, #fff0f4);
        color: #4f3977;
        border: 1px solid rgba(103, 80, 154, 0.14);
        padding: 0.45rem 0.9rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Onboarding Step Indicator */
    .step-indicator-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(103, 80, 154, 0.12);
        border-radius: 18px;
        padding: 0.75rem 1.2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 20px rgba(45, 30, 65, 0.04);
    }

    .step-badge {
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6b4bb0;
        background: #f1eafe;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
    }

    .step-dots {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 700;
        color: #6c5f82;
        font-size: 0.85rem;
    }

    .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #e0d8ed;
        transition: all 0.3s ease;
    }

    .dot.active {
        width: 28px;
        border-radius: 999px;
        background: linear-gradient(90deg, #6b4bb0, #ef7d8f);
    }

    /* Budget Card Display */
    .budget-display-card {
        background: linear-gradient(135deg, #2a1b40 0%, #46285c 100%);
        color: white;
        border-radius: 22px;
        padding: 1.3rem 1.6rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 16px 32px rgba(42, 27, 64, 0.2);
    }

    .budget-label {
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #d1b9ff;
    }

    .budget-value {
        font-size: 2.3rem;
        font-weight: 900;
        color: #ffffff;
        margin: 0.2rem 0 0.8rem;
    }

    .budget-slider-visual {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.78rem;
        color: #e0d4f7;
        font-weight: 600;
    }

    .budget-track {
        flex: 1;
        height: 8px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 999px;
        margin: 0 1rem;
        position: relative;
        overflow: hidden;
    }

    .budget-track-fill {
        height: 100%;
        background: linear-gradient(90deg, #9b72cf, #ff8da1);
        border-radius: 999px;
    }

    /* Selection Cards & Chips */
    .selection-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 0.8rem;
        margin: 1rem 0;
    }

    .select-card {
        background: #ffffff;
        border: 2px solid rgba(103, 80, 154, 0.12);
        border-radius: 18px;
        padding: 0.9rem;
        text-align: center;
        box-shadow: 0 6px 16px rgba(40, 25, 60, 0.03);
    }

    .select-card.active {
        border-color: #6b4bb0;
        background: linear-gradient(180deg, #f4edff 0%, #ffffff 100%);
        box-shadow: 0 10px 24px rgba(107, 75, 176, 0.18);
    }

    .select-card .card-icon {
        font-size: 1.8rem;
        margin-bottom: 0.4rem;
    }

    .select-card .card-title {
        font-weight: 800;
        font-size: 0.88rem;
        color: #1f162d;
    }

    /* Product Marketplace Cards */
    .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 1.1rem;
        margin-top: 1rem;
    }

    .product-card {
        background: #ffffff;
        border: 1px solid rgba(89, 65, 128, 0.12);
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 12px 26px rgba(38, 26, 49, 0.05);
        display: flex;
        flex-direction: column;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }

    .product-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 18px 36px rgba(38, 26, 49, 0.10);
    }

    .product-image-container {
        height: 180px;
        background: #f4eeff;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }

    .product-image-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .fabric-badge {
        position: absolute;
        top: 10px;
        left: 10px;
        background: rgba(255, 255, 255, 0.92);
        backdrop-filter: blur(4px);
        color: #4b3475;
        border-radius: 999px;
        padding: 0.25rem 0.6rem;
        font-size: 0.68rem;
        font-weight: 800;
        border: 1px solid rgba(75, 52, 117, 0.12);
    }

    .platform-badge {
        position: absolute;
        bottom: 10px;
        right: 10px;
        background: rgba(31, 22, 44, 0.82);
        color: #ffffff;
        border-radius: 8px;
        padding: 0.2rem 0.5rem;
        font-size: 0.66rem;
        font-weight: 700;
    }

    .product-info {
        padding: 1rem;
        display: flex;
        flex-direction: column;
        flex: 1;
    }

    .product-name {
        font-weight: 800;
        font-size: 0.9rem;
        color: #1f162d;
        line-height: 1.3;
        margin-bottom: 0.3rem;
    }

    .product-meta {
        font-size: 0.74rem;
        color: #665f73;
        margin-bottom: 0.5rem;
    }

    .product-price-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: auto;
        padding-top: 0.5rem;
    }

    .product-price {
        font-size: 1.15rem;
        font-weight: 900;
        color: #1f162d;
    }

    .rating-star {
        color: #f59e0b;
        font-size: 0.78rem;
        font-weight: 700;
    }

    /* Swiggy-Style Complete Outfit Breakdown Card */
    .outfit-breakdown-card {
        background: #ffffff;
        border: 1px solid rgba(89, 65, 128, 0.14);
        border-radius: 24px;
        padding: 1.25rem;
        box-shadow: 0 16px 36px rgba(38, 26, 49, 0.06);
        margin: 1.2rem 0;
    }

    .breakdown-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 0;
        border-bottom: 1px dashed rgba(103, 80, 154, 0.15);
    }

    .breakdown-row:last-child {
        border-bottom: none;
    }

    .item-left {
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }

    .item-icon-box {
        width: 44px;
        height: 44px;
        border-radius: 14px;
        background: #f4eeff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        color: #5d4295;
    }

    .item-title {
        font-weight: 800;
        font-size: 0.88rem;
        color: #1f162d;
    }

    .item-subtitle {
        font-size: 0.74rem;
        color: #686175;
    }

    .item-right {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }

    .item-price {
        font-weight: 800;
        font-size: 0.95rem;
        color: #1f162d;
    }

    .outfit-total-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, #f4ebff, #fff0f4);
        border: 1px solid rgba(107, 75, 176, 0.18);
        border-radius: 18px;
        padding: 1rem 1.2rem;
        margin-top: 1rem;
    }

    .total-label {
        font-size: 0.85rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #4f367e;
    }

    .total-amount {
        font-size: 1.6rem;
        font-weight: 900;
        color: #1b1227;
    }

    /* General Panel Styling */
    .panel, .card {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(89, 65, 128, 0.12);
        border-radius: 22px;
        box-shadow: 0 16px 30px rgba(38, 26, 49, 0.05);
        padding: 1.2rem;
    }

    .hero-panel {
        padding: 1.6rem;
        border-radius: 26px;
        background: linear-gradient(135deg, rgba(112, 83, 173, 0.10), rgba(239, 125, 143, 0.10));
        border: 1px solid rgba(109, 82, 165, 0.15);
        box-shadow: 0 18px 34px rgba(92, 69, 128, 0.08);
    }

    .page-kicker {
        color: #7a5fe2;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 0.72rem;
        font-weight: 800;
    }

    [data-testid="stSidebar"] {
        display: none !important;
    }

    .top-nav {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        padding: 0.55rem 0.8rem;
        margin-bottom: 1.1rem;
        background: rgba(255,255,255,0.88);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(89,65,128,0.12);
        border-radius: 18px;
        box-shadow: 0 10px 24px rgba(38,26,49,0.05);
        overflow-x: auto;
    }

    .top-nav-brand {
        color: #2e1e46;
        font-weight: 900;
        letter-spacing: 0.08em;
        margin-right: 0.6rem;
        white-space: nowrap;
    }

    .top-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 2.3rem;
        padding: 0.45rem 0.8rem;
        border-radius: 12px;
        color: #3d3152 !important;
        font-size: 0.82rem;
        font-weight: 800;
        text-decoration: none !important;
        white-space: nowrap;
    }

    .top-link.active {
        background: linear-gradient(135deg, #6a4bb0, #ef7d8f);
        color: #ffffff !important;
        box-shadow: 0 6px 14px rgba(106, 75, 176, 0.22);
    }
</style>
"""


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def money(value: float) -> str:
    return f"₹{value:,.0f}"


def render_top_nav(active: str = "Home"):
    labels = [
        ("Home", "/Home"),
        ("01 Profile", "/My_Profile"),
        ("02 Appearance", "/Appearance_Colour"),
        ("03 Preferences", "/My_Preferences"),
        ("04 Avatar", "/Avatar"),
        ("05 Recommendations", "/AI_Outfit_Recommendations"),
        ("06 Complete Look", "/Outfit_Details"),
        ("07 Customize", "/Customize_My_Outfit"),
        ("08 Budget", "/Budget_Stylist"),
        ("09 Pairing", "/Interactive_Pairing"),
        ("10 Why", "/Why_This_Outfit"),
        ("10 Preview", "/Virtual_Styling_Preview"),
        ("11 Identity", "/Multi_Identity"),
        ("12 Final Look", "/Final_Look"),
    ]
    links = "".join(
        f"<a class='top-link {'active' if label.endswith(active) or label == active else ''}' href='{path}' target='_self'>{label}</a>"
        for label, path in labels
    )
    st.markdown(f"<nav class='top-nav'><div class='top-nav-brand'>STYLEAI</div>{links}</nav>", unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str, badge: str = "StyleAI", active: str = "Home"):
    render_top_nav(active)
    st.markdown(
        f"""
        <div class="brand-shell">
            <div class="brand-row">
                <div class="brand-left">
                    <div class="brand-mark">✦</div>
                    <div>
                        <p class="brand-title">{title}</p>
                        <p class="brand-sub">{subtitle}</p>
                    </div>
                </div>
                <div class="nav-pill">{badge}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_progress(step_num: int, total_steps: int = 5, step_title: str = "Profile Setup"):
    dots = "".join(
        f"<div class='dot {'active' if i == step_num else ''}'></div>"
        for i in range(1, total_steps + 1)
    )
    st.markdown(
        f"""
        <div class="step-indicator-bar">
            <div class="step-badge">STEP {step_num} OF {total_steps} · {step_title}</div>
            <div class="step-dots">{dots}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, icon: str = "✨"):
    st.markdown(
        f"""
        <div class="page-kicker" style="margin-top:0.8rem; margin-bottom:0.4rem;">{icon} {title}</div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_panel(title: str, text: str, icon: str = "✨"):
    st.markdown(
        f"""
        <div class="panel">
            <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.5rem;">
                <div style="font-size:1.6rem;">{icon}</div>
                <div style="font-weight:800; color:#21182f;">{title}</div>
            </div>
            <div style="color:#5d5867; font-size:0.92rem;">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_value(value, default: str = "Pending"):
    return value if value not in (None, "", "None") else default


def ensure_session_defaults():
    # User Profile
    if "user_name" not in st.session_state:
        st.session_state.user_name = "Alex"
    if "age" not in st.session_state:
        st.session_state.age = 22
    if "gender" not in st.session_state:
        st.session_state.gender = "Female"
    if "height" not in st.session_state:
        st.session_state.height = 168
    if "weight" not in st.session_state:
        st.session_state.weight = 58
    if "budget" not in st.session_state:
        st.session_state.budget = 3500.0

    # Step Progress
    if "step_progress" not in st.session_state:
        st.session_state.step_progress = 1
    if "appearance_substep" not in st.session_state:
        st.session_state.appearance_substep = 1

    # Appearance & Preferences
    if "skin_tone" not in st.session_state or st.session_state.skin_tone is None:
        st.session_state.skin_tone = "Medium"
    if "favorite_colours" not in st.session_state:
        st.session_state.favorite_colours = ["Navy", "Beige", "White"]
    if "style" not in st.session_state:
        st.session_state.style = "Casual"
    if "occasion" not in st.session_state:
        st.session_state.occasion = "College"
    if "avoid_colours" not in st.session_state:
        st.session_state.avoid_colours = ["Neon / Flashy", "Clashing Tones"]
    if "preferred_fit" not in st.session_state:
        st.session_state.preferred_fit = "Regular Fit"

    # Avatar Mode & Builder
    if "avatar_choice" not in st.session_state:
        st.session_state.avatar_choice = "avatar"
    if "uploaded_photo" not in st.session_state:
        st.session_state.uploaded_photo = None

    if "avatar_builder" not in st.session_state:
        st.session_state.avatar_builder = {
            "gender": "Female",
            "model_preset": "Model A",
            "body_shape": "Balanced",
            "height": 168,
            "weight": 58,
            "skin_tone": "Medium",
            "hair_style": "Long Straight",
            "hair_colour": "Dark Brown",
            "hair_type": "Straight",
            "occasion": "College",
            "outfit": "Casual Tee & Jeans",
            "accessory": "Minimal Watch",
        }

    if "avatars" not in st.session_state:
        st.session_state.avatars = {
            "College": {**st.session_state.avatar_builder, "occasion": "College", "model_preset": "Model A"},
            "Office": {**st.session_state.avatar_builder, "occasion": "Office", "model_preset": "Model A", "outfit": "Oxford Shirt & Chinos"},
            "Party": {**st.session_state.avatar_builder, "occasion": "Party", "model_preset": "Model B", "outfit": "Satin Blouse & Flare Pants"},
        }
    if "selected_avatar_key" not in st.session_state:
        st.session_state.selected_avatar_key = "College"

    # Preferences Text & Marketplace
    if "preference_text" not in st.session_state:
        st.session_state.preference_text = ""
    if "style_profile" not in st.session_state:
        st.session_state.style_profile = {}
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []
    if "selected_outfit" not in st.session_state:
        st.session_state.selected_outfit = None
    if "cart_items" not in st.session_state:
        st.session_state.cart_items = {}
    if "locked_items" not in st.session_state:
        st.session_state.locked_items = {"Top": False, "Bottom": False, "Shoes": False, "Accessory": False}
