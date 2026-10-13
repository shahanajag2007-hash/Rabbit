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
    "Appearance & Preferences",
    "Tailor your color palette, style mood and event context step-by-step.",
    active="02 Appearance",
)

render_step_progress(step_num=2, total_steps=5, step_title="Appearance & Style Inputs")

substep = st.session_state.get("appearance_substep", 1)

# Substep indicator header
substep_names = ["1. Skin Tone", "2. Favourite Colours", "3. Preferred Style", "4. Occasion Context"]
cols_sub = st.columns(4)
for idx, name in enumerate(substep_names, 1):
    with cols_sub[idx - 1]:
        is_active = substep == idx
        if st.button(
            name,
            key=f"substep_tab_{idx}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.appearance_substep = idx
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# SUBSTEP 1: SKIN TONE
# -------------------------------------------------------------
if substep == 1:
    st.markdown(
        """
        <div class="hero-panel">
            <div class="page-kicker">SUBSTEP 1 OF 4</div>
            <div style="font-size: 1.6rem; font-weight: 800; color: #1f162d;">Select Your Skin Tone</div>
            <div style="color: #5f5a6d; font-size: 0.88rem;">
                Our color harmony algorithm matches clothing palettes to complement your skin tone undertones.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    tones = [
        ("Light", "#f6d7c5", "Cool/Fair undertones. Pairs best with Navy, Burgundy, Emerald, White."),
        ("Medium", "#c9906d", "Warm Almond undertones. Pairs best with Teal, Olive, Mustard, Maroon, Cream."),
        ("Tan", "#ad704f", "Golden Olive undertones. Pairs best with Rust, Sage, Camel, Chocolate, Cream."),
        ("Deep", "#794936", "Rich Cocoa undertones. Pairs best with Pure White, Cobalt, Emerald, Coral, Lavender."),
    ]

    current_tone = st.session_state.get("skin_tone", "Medium")

    cols_tone = st.columns(4)
    for idx, (tone_name, hex_code, desc) in enumerate(tones):
        with cols_tone[idx]:
            is_sel = current_tone == tone_name
            st.markdown(
                f"""
                <div class="select-card {'active' if is_sel else ''}">
                    <div style="width:54px; height:54px; border-radius:50%; background:{hex_code}; margin:0 auto 0.6rem; border:3px solid #ffffff; box-shadow:0 6px 14px rgba(0,0,0,0.15);"></div>
                    <div class="card-title">{tone_name} {'✓' if is_sel else ''}</div>
                    <div style="font-size:0.72rem; color:#625b6e; margin-top:0.4rem;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Select {tone_name}", key=f"btn_tone_{tone_name}", use_container_width=True):
                st.session_state.skin_tone = tone_name
                st.rerun()

# -------------------------------------------------------------
# SUBSTEP 2: FAVOURITE COLOURS
# -------------------------------------------------------------
elif substep == 2:
    st.markdown(
        """
        <div class="hero-panel">
            <div class="page-kicker">SUBSTEP 2 OF 4</div>
            <div style="font-size: 1.6rem; font-weight: 800; color: #1f162d;">Select Your Favourite Colours</div>
            <div style="color: #5f5a6d; font-size: 0.88rem;">
                Choose colors you feel most confident wearing. We will prioritize these in recommendations.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    available_colours = [
        ("Black", "#1a1a1a"),
        ("White", "#f8f9fa"),
        ("Navy", "#1B2A47"),
        ("Blue", "#2563eb"),
        ("Green", "#166534"),
        ("Pink", "#ec4899"),
        ("Red", "#dc2626"),
        ("Brown", "#78350f"),
        ("Beige", "#d97706"),
        ("Lavender", "#a855f7"),
        ("Olive", "#65a30d"),
        ("Mustard", "#eab308"),
        ("Burgundy", "#831843"),
    ]

    current_favs = st.session_state.get("favorite_colours", ["Navy", "Beige", "White"])

    cols_fav = st.columns(4)
    for idx, (color_name, hex_val) in enumerate(available_colours):
        with cols_fav[idx % 4]:
            is_fav = color_name in current_favs
            st.markdown(
                f"""
                <div class="select-card {'active' if is_fav else ''}" style="display:flex; align-items:center; gap:0.6rem; padding:0.7rem 0.9rem; text-align:left;">
                    <div style="width:24px; height:24px; border-radius:50%; background:{hex_val}; border:1px solid rgba(0,0,0,0.2);"></div>
                    <div class="card-title" style="font-size:0.82rem;">{color_name} {'✓' if is_fav else ''}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            btn_label = f"Remove {color_name}" if is_fav else f"Add {color_name}"
            if st.button(btn_label, key=f"btn_color_{color_name}", use_container_width=True):
                if is_fav:
                    current_favs.remove(color_name)
                else:
                    current_favs.append(color_name)
                st.session_state.favorite_colours = current_favs
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='mini-card'><strong>Active Palette Preferences:</strong> " + ", ".join(current_favs) + "</div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# SUBSTEP 3: PREFERRED STYLE
# -------------------------------------------------------------
elif substep == 3:
    st.markdown(
        """
        <div class="hero-panel">
            <div class="page-kicker">SUBSTEP 3 OF 4</div>
            <div style="font-size: 1.6rem; font-weight: 800; color: #1f162d;">Select Preferred Style Aesthetic</div>
            <div style="color: #5f5a6d; font-size: 0.88rem;">
                What styling direction resonates most with your personal aesthetic?
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    styles = [
        ("Minimal", "✨", "Clean lines, solid neutrals, effortless cuts."),
        ("Casual", "👟", "Relaxed everyday denim, comfortable tees, sneakers."),
        ("Formal", "👔", "Crisp blazers, tailored trousers, polished footwear."),
        ("Smart Casual", "🧥", "Elevated everyday look blending structure and comfort."),
        ("Trendy", "🔥", "Fashion-forward statement cuts and current silhouettes."),
        ("Traditional", "🌸", "Heritage ethnic wear, kurtas, sarees and classic drapes."),
        ("Elegant", "💎", "Refined evening dresses, graceful drapes and subtle luxury."),
        ("Streetwear", "🧢", "Oversized silhouettes, graphic details and urban aesthetics."),
    ]

    current_style = st.session_state.get("style", "Casual")

    cols_style = st.columns(4)
    for idx, (s_name, s_icon, s_desc) in enumerate(styles):
        with cols_style[idx % 4]:
            is_s_active = current_style == s_name
            st.markdown(
                f"""
                <div class="select-card {'active' if is_s_active else ''}">
                    <div class="card-icon">{s_icon}</div>
                    <div class="card-title">{s_name} {'✓' if is_s_active else ''}</div>
                    <div style="font-size:0.72rem; color:#625b6e; margin-top:0.3rem;">{s_desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Choose {s_name}", key=f"btn_style_{s_name}", use_container_width=True):
                st.session_state.style = s_name
                st.rerun()

# -------------------------------------------------------------
# SUBSTEP 4: OCCASION CONTEXT
# -------------------------------------------------------------
else:
    st.markdown(
        """
        <div class="hero-panel">
            <div class="page-kicker">SUBSTEP 4 OF 4</div>
            <div style="font-size: 1.6rem; font-weight: 800; color: #1f162d;">Select Occasion Context</div>
            <div style="color: #5f5a6d; font-size: 0.88rem;">
                Where are you planning to wear this outfit? Our stylist optimizes for setting propriety.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    occasions = [
        ("College", "🎓", "Expressive, easy dressing for campus life and lectures."),
        ("Office", "💼", "Professional, workday-ready tailoring and polished layers."),
        ("Interview", "📄", "Formal, confident dressing designed to make a strong impression."),
        ("Party", "🎉", "Statement night-out styling, festive fits and evening flair."),
        ("Casual Outing", "☕", "Weekend brunches, relaxed meetups and coffee runs."),
        ("Traditional Event", "🪔", "Festivals, weddings, family celebrations and ceremonies."),
        ("Special Event", "✨", "Gala dinners, award events and high-fashion moments."),
    ]

    current_occ = st.session_state.get("occasion", "College")

    cols_occ = st.columns(4)
    for idx, (o_name, o_icon, o_desc) in enumerate(occasions):
        with cols_occ[idx % 4]:
            is_o_active = current_occ == o_name
            st.markdown(
                f"""
                <div class="select-card {'active' if is_o_active else ''}">
                    <div class="card-icon">{o_icon}</div>
                    <div class="card-title">{o_name} {'✓' if is_o_active else ''}</div>
                    <div style="font-size:0.72rem; color:#625b6e; margin-top:0.3rem;">{o_desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Pick {o_name}", key=f"btn_occ_{o_name}", use_container_width=True):
                st.session_state.occasion = o_name
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Navigation Controls
col_prev, col_spacer, col_next = st.columns([1, 1.2, 1])

with col_prev:
    if substep > 1:
        if st.button("← Previous Substep", use_container_width=True):
            st.session_state.appearance_substep = substep - 1
            st.rerun()
    else:
        if st.button("← Back to Profile", use_container_width=True):
            st.session_state.step_progress = 1
            st.switch_page("pages/01_My_Profile.py")

with col_next:
    if substep < 4:
        if st.button("Next Substep →", type="primary", use_container_width=True):
            st.session_state.appearance_substep = substep + 1
            st.rerun()
    else:
        if st.button("CONTINUE TO AVATAR →", type="primary", use_container_width=True):
            st.session_state.step_progress = 3
            st.switch_page("pages/01_Avatar.py")
