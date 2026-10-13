from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from avatar_engine import render_fashion_avatar_svg
from ui_theme import (
    apply_theme,
    ensure_session_defaults,
    render_page_header,
    render_section_heading,
    render_step_progress,
)

apply_theme()
ensure_session_defaults()

st.markdown(
    """
    <style>
    .avatar-studio-container {
        max-width: 1300px;
        margin: 0 auto;
    }

    .choice-card {
        background: #ffffff;
        border: 2px solid rgba(103, 80, 154, 0.14);
        border-radius: 24px;
        padding: 1.8rem;
        text-align: center;
        box-shadow: 0 14px 30px rgba(45, 30, 65, 0.05);
        transition: all 0.25s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .choice-card.active {
        border-color: #6b4bb0;
        background: linear-gradient(180deg, #f5efff 0%, #ffffff 100%);
        box-shadow: 0 18px 40px rgba(107, 75, 176, 0.2);
    }

    .choice-icon {
        font-size: 3.2rem;
        margin-bottom: 0.8rem;
    }

    .choice-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #1f162d;
        margin-bottom: 0.4rem;
    }

    .choice-desc {
        font-size: 0.84rem;
        color: #625b6e;
        line-height: 1.5;
        margin-bottom: 1.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

render_page_header(
    "Virtual Stylist & Avatar Studio",
    "Create your personalized visual styling model or upload a photo.",
    active="04 Avatar",
)

render_step_progress(step_num=3, total_steps=5, step_title="Photo or Avatar Profile Creation")

if "visual_mode" not in st.session_state:
    st.session_state.visual_mode = "avatar"

st.markdown("<div class='avatar-studio-container'>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero-panel" style="margin-bottom:1.5rem;">
        <div class="page-kicker">ONBOARDING STAGE 3</div>
        <div style="font-size: clamp(1.5rem, 2.2vw, 2.3rem); font-weight: 800; color: #1f162d;">
            How Would You Like To Create Your Look?
        </div>
        <div style="color: #5f5a6d; font-size: 0.92rem; margin-top: 0.3rem;">
            Choose between building a personalized virtual model or uploading your own photo for styling.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col_mode_a, col_mode_b = st.columns(2, gap="large")

with col_mode_a:
    is_photo = st.session_state.visual_mode == "photo"
    st.markdown(
        f"""
        <div class="choice-card {'active' if is_photo else ''}">
            <div>
                <div class="choice-icon">📷</div>
                <div class="choice-title">OPTION 1: UPLOAD YOUR PHOTO</div>
                <div class="choice-desc">
                    Use your own full-body photo for personalized outfit recommendations and visual analysis.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Choose Photo Upload 📷", key="btn_choose_photo", use_container_width=True):
        st.session_state.visual_mode = "photo"
        st.rerun()

with col_mode_b:
    is_avatar = st.session_state.visual_mode == "avatar"
    st.markdown(
        f"""
        <div class="choice-card {'active' if is_avatar else ''}">
            <div>
                <div class="choice-icon">🧑‍🎨</div>
                <div class="choice-title">OPTION 2: CREATE YOUR AVATAR</div>
                <div class="choice-desc">
                    Build a personalized high-fidelity virtual fashion model based on your profile proportions and skin tone.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Choose Avatar Builder 🧑‍🎨", key="btn_choose_avatar", type="primary", use_container_width=True):
        st.session_state.visual_mode = "avatar"
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# OPTION 1: PHOTO UPLOAD SECTION
# ------------------------------------------------------------------------------
if st.session_state.visual_mode == "photo":
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    render_section_heading("Full-Body Photo Upload", "📷")

    uploaded = st.file_uploader("Upload full-body picture (JPG, PNG)", type=["jpg", "jpeg", "png"])
    if uploaded is not None:
        st.session_state.uploaded_photo = uploaded
        st.image(uploaded, width=280)
        st.success("Photo uploaded successfully! Your styling engine will use this photo.")

    col_p_nav1, col_p_nav2 = st.columns([1, 1])
    with col_p_nav2:
        if st.button("PROCEED TO PREFERENCE ANALYSIS →", type="primary", use_container_width=True):
            st.session_state.step_progress = 4
            st.switch_page("pages/04_AI_Outfit_Recommendations.py")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# OPTION 2: PROFESSIONAL AVATAR BUILDER STUDIO
# ------------------------------------------------------------------------------
else:
    st.markdown("<div class='panel' style='margin-top:1rem;'>", unsafe_allow_html=True)
    render_section_heading("Professional Fashion Avatar Studio", "🎨")

    builder = st.session_state.avatar_builder

    # Ensure profile values are synced
    builder["gender"] = st.session_state.get("gender", builder.get("gender", "Female"))
    builder["height"] = st.session_state.get("height", builder.get("height", 168))
    builder["weight"] = st.session_state.get("weight", builder.get("weight", 58))
    builder["skin_tone"] = st.session_state.get("skin_tone", builder.get("skin_tone", "Medium"))
    builder["occasion"] = st.session_state.get("occasion", builder.get("occasion", "College"))

    # DESKTOP SIDE-BY-SIDE LAYOUT (LEFT 60% Preview, RIGHT 40% Customization)
    left_preview_col, right_controls_col = st.columns([1.2, 1], gap="large")

    with left_preview_col:
        # Full component inside iframe guarantees model is centered INSIDE the card container
        full_html = render_fashion_avatar_svg(builder, full_component=True)
        components.html(full_html, height=540, scrolling=False)

    with right_controls_col:
        st.markdown("<div class='page-kicker'>CUSTOMIZE YOUR LOOK</div>", unsafe_allow_html=True)

        tab_categories = ["Preset Model", "Hair & Style", "Body Shape", "Skin Tone", "Accessories"]
        if "active_avatar_tab" not in st.session_state:
            st.session_state.active_avatar_tab = "Preset Model"

        cols_tab = st.columns(len(tab_categories))
        for idx, tab_name in enumerate(tab_categories):
            with cols_tab[idx]:
                is_t_active = st.session_state.active_avatar_tab == tab_name
                if st.button(tab_name, key=f"tab_btn_{idx}", use_container_width=True, type="primary" if is_t_active else "secondary"):
                    st.session_state.active_avatar_tab = tab_name
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        current_tab = st.session_state.active_avatar_tab

        # TAB 1: PRESET MODEL POSES
        if current_tab == "Preset Model":
            st.write("**Model Base & Stance Variations**")
            st.caption("Each stance offers a distinct fashion posture while maintaining your personal proportions.")

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                is_p1 = builder.get("model_preset") == "Model A"
                st.markdown(f"<div class='select-card {'active' if is_p1 else ''}'><div class='card-title'>Model A (Runway Frontal) {'✓' if is_p1 else ''}</div></div>", unsafe_allow_html=True)
                if st.button("Select Model A", key="btn_preset_a", use_container_width=True):
                    builder["model_preset"] = "Model A"
                    st.session_state.avatar_builder = builder
                    st.rerun()

            with col_p2:
                is_p2 = builder.get("model_preset") == "Model B"
                st.markdown(f"<div class='select-card {'active' if is_p2 else ''}'><div class='card-title'>Model B (3/4 Fashion Pose) {'✓' if is_p2 else ''}</div></div>", unsafe_allow_html=True)
                if st.button("Select Model B", key="btn_preset_b", use_container_width=True):
                    builder["model_preset"] = "Model B"
                    st.session_state.avatar_builder = builder
                    st.rerun()

        # TAB 2: HAIR & STYLE
        elif current_tab == "Hair & Style":
            st.write("**Hairstyle & Cut**")
            h_styles = ["Long Straight", "Wavy", "Curly", "Bob", "Ponytail", "Bun"]
            cols_hs = st.columns(3)
            for idx, hs in enumerate(h_styles):
                with cols_hs[idx % 3]:
                    is_hs = builder.get("hair_style") == hs
                    if st.button(f"{'✓ ' if is_hs else ''}{hs}", key=f"btn_hs_{hs}", use_container_width=True):
                        builder["hair_style"] = hs
                        st.session_state.avatar_builder = builder
                        st.rerun()

            st.write("**Hair Colour**")
            h_colors = ["Black", "Dark Brown", "Brown", "Light Brown", "Blonde", "Auburn", "Red"]
            cols_hc = st.columns(4)
            for idx, hc in enumerate(h_colors):
                with cols_hc[idx % 4]:
                    is_hc = builder.get("hair_colour") == hc
                    if st.button(f"{'✓ ' if is_hc else ''}{hc}", key=f"btn_hc_{hc}", use_container_width=True):
                        builder["hair_colour"] = hc
                        st.session_state.avatar_builder = builder
                        st.rerun()

        # TAB 3: BODY SHAPE
        elif current_tab == "Body Shape":
            st.write("**Body Contour & Silhouette**")
            shapes = ["Balanced", "Slim", "Athletic", "Curvy"]
            cols_bs = st.columns(2)
            for idx, bs in enumerate(shapes):
                with cols_bs[idx % 2]:
                    is_bs = builder.get("body_shape") == bs
                    if st.button(f"{'✓ ' if is_bs else ''}{bs}", key=f"btn_bs_{bs}", use_container_width=True):
                        builder["body_shape"] = bs
                        st.session_state.avatar_builder = builder
                        st.rerun()

        # TAB 4: SKIN TONE
        elif current_tab == "Skin Tone":
            st.write("**Skin Tone Shading**")
            skin_options = ["Porcelain", "Light Beige", "Warm Almond", "Golden Tan", "Deep Cocoa", "Espresso"]
            cols_st = st.columns(3)
            for idx, st_opt in enumerate(skin_options):
                with cols_st[idx % 3]:
                    is_st = builder.get("skin_tone") == st_opt
                    if st.button(f"{'✓ ' if is_st else ''}{st_opt}", key=f"btn_st_{st_opt}", use_container_width=True):
                        builder["skin_tone"] = st_opt
                        st.session_state.skin_tone = st_opt
                        st.session_state.avatar_builder = builder
                        st.rerun()

        # TAB 5: ACCESSORIES
        else:
            st.write("**Accessories & Details**")
            acc_list = ["Minimal Watch", "Glasses", "Sunglasses", "Earrings", "Canvas Tote"]
            cols_acc = st.columns(2)
            for idx, acc in enumerate(acc_list):
                with cols_acc[idx % 2]:
                    is_acc = builder.get("accessory") == acc
                    if st.button(f"{'✓ ' if is_acc else ''}{acc}", key=f"btn_acc_{acc}", use_container_width=True):
                        builder["accessory"] = acc
                        st.session_state.avatar_builder = builder
                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# AVATAR ACTION BUTTONS
# ------------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)

col_act1, col_act2, col_act3, col_act4 = st.columns(4)

with col_act1:
    if st.button("← Back to Appearance", use_container_width=True):
        st.session_state.step_progress = 2
        st.switch_page("pages/02_Appearance___Colour.py")

with col_act2:
    if st.button("↺ Reset Avatar", use_container_width=True):
        st.session_state.avatar_builder = {
            "gender": st.session_state.get("gender", "Female"),
            "model_preset": "Model A",
            "body_shape": "Balanced",
            "height": st.session_state.get("height", 168),
            "weight": st.session_state.get("weight", 58),
            "skin_tone": st.session_state.get("skin_tone", "Medium"),
            "hair_style": "Long Straight",
            "hair_colour": "Dark Brown",
            "occasion": st.session_state.get("occasion", "College"),
            "accessory": "Minimal Watch",
        }
        st.rerun()

with col_act3:
    if st.button("💾 Save Avatar Look", use_container_width=True):
        occ = builder.get("occasion", "College")
        st.session_state.avatars[occ] = {**builder}
        st.session_state.selected_avatar_key = occ
        st.success(f"Avatar saved to your '{occ}' style collection!")

with col_act4:
    if st.button("CONTINUE TO PREFERENCE ANALYSIS →", type="primary", use_container_width=True):
        st.session_state.step_progress = 4
        st.switch_page("pages/04_AI_Outfit_Recommendations.py")

st.markdown("</div>", unsafe_allow_html=True)