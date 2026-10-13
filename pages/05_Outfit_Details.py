from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from avatar_engine import render_fashion_avatar_svg
from demo_data import DEMO_FABRIC_NOTES, filter_demo_products
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
    "Your Complete Look",
    "Complete outfit styling dashboard with virtual preview, breakdown, and textile insights.",
    active="06 Complete Look",
)

render_step_progress(step_num=5, total_steps=5, step_title="Complete Outfit & Virtual Styling")

# ISSUE 4 FIX: Ensure ALL 4 outfit categories exist (Top, Bottom, Shoes, Accessory)
import recommender
cart = st.session_state.cart_items
user_profile = st.session_state.get("user_profile", {})

if not cart:
    st.info("No outfit selected. Please return to the Marketplace.")
    st.stop()

# Calculate real scores
outfit = st.session_state.get("selected_outfit", {"items": cart})
current_score_info = recommender.score_single_outfit(outfit, user_profile)
total_cost = current_score_info["total_price"]
overall_score = int(current_score_info["score"])
breakdown = current_score_info["breakdown"]

builder = st.session_state.get("avatar_builder")

# ==============================================================================
# TOP SHOWCASE: LARGE AVATAR MODEL WEARING COMPLETE OUTFIT
# ==============================================================================
st.markdown("<div class='panel'>", unsafe_allow_html=True)
col_show_l, col_show_r = st.columns([1.1, 1.2], gap="large")

with col_show_l:
    if builder:
        svg_preview_html = render_fashion_avatar_svg(builder, outfit_items=cart, full_component=True)
        components.html(svg_preview_html, height=530, scrolling=False)
    else:
        st.info("Avatar not generated.")

with col_show_r:
    summary_html = f"""<div class="hero-panel" style="height:100%; display:flex; flex-direction:column; justify-content:center;">
<div class="page-kicker">STYLING SUMMARY</div>
<div style="font-size: 1.8rem; font-weight: 900; color: #1f162d; margin-top: 0.2rem;">Curated {st.session_state.occasion} Outfit</div>
<div style="color: #5f5a6d; font-size: 0.9rem; margin-top: 0.4rem; line-height: 1.55;">
This complete look coordinates your selected <strong>{st.session_state.skin_tone}</strong> skin tone palette, <strong>{st.session_state.style}</strong> preference, and stays within your <strong>{money(float(st.session_state.budget))}</strong> budget.
</div>
<div style="margin-top: 1.5rem; display:flex; gap:1rem; flex-wrap:wrap;">
<div class="stat-card" style="flex:1;">
<div class="stat-label">Total Look Cost</div>
<div class="stat-value">{money(total_cost)}</div>
</div>
<div class="stat-card" style="flex:1;">
<div class="stat-label">Match Score</div>
<div class="stat-value" style="color:#6b4bb0;">{overall_score}/100</div>
</div>
</div>
</div>"""
    st.markdown(summary_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# SWIGGY-STYLE OUTFIT ITEM BREAKDOWN CARD
# ==============================================================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<div class='outfit-breakdown-card'>", unsafe_allow_html=True)
render_section_heading("Outfit Item Breakdown", "🛍️")

categories = ["Top", "Bottom", "Shoes", "Accessory"]
icons = {"Top": "👕", "Bottom": "👖", "Shoes": "👟", "Accessory": "⌚"}

for cat in categories:
    item = cart.get(cat)
    is_locked = st.session_state.locked_items.get(cat, False)

    if item:
        item_html = f"""<div class="breakdown-row">
<div class="item-left">
<div class="item-icon-box">{icons.get(cat, '✨')}</div>
<div>
<div class="item-title">{item['item_name']} {'🔒 (Locked)' if is_locked else ''}</div>
<div class="item-subtitle">{cat} · {item['colour']} · {item.get('fabric_tag', 'N/A')}</div>
</div>
</div>
<div class="item-right">
<div class="item-price">{money(item['price'])}</div>
</div>
</div>"""
        st.markdown(item_html, unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button(f"[-] Remove {cat}", key=f"btn_rem_{cat}", use_container_width=True):
                cart.pop(cat, None)
                st.session_state.cart_items = cart
                st.rerun()

        with c2:
            if st.button(f"Replace {cat}", key=f"btn_rep_{cat}", use_container_width=True):
                st.session_state.replace_target = cat
                st.switch_page("pages/06_Customize_My_Outfit.py")

        with c3:
            lock_txt = "Unlock Item" if is_locked else "🔒 Lock Item"
            if st.button(lock_txt, key=f"btn_lock_{cat}", use_container_width=True):
                st.session_state.locked_items[cat] = not is_locked
                st.rerun()

# Total Cost Pill Row
total_html = f"""<div class="outfit-total-row">
<div class="total-label">TOTAL OUTFIT PRICE</div>
<div class="total-amount">{money(total_cost)}</div>
</div>"""
st.markdown(total_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# WHY WE CHOSE THIS LOOK FOR YOU & FABRIC NOTES
# ==============================================================================
st.markdown("<br>", unsafe_allow_html=True)
col_why_l, col_why_r = st.columns(2, gap="large")

with col_why_l:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    render_section_heading("Why We Chose This Look For You", "💡")

    reasons = []
    
    # Calculate percentages for logic checks
    style_pct = (breakdown.get('style', 0) / 20.0) * 100
    colour_pct = (breakdown.get('colour', 0) / 30.0) * 100
    occasion_pct = (breakdown.get('occasion', 0) / 20.0) * 100
    budget_pct = (breakdown.get('budget', 0) / 15.0) * 100
    compat_pct = (breakdown.get('compatibility', 0) / 15.0) * 100
    
    if style_pct >= 70:
        reasons.append(f"✓ Strong match for your preferred **{st.session_state.style}** aesthetic")
    if colour_pct >= 60:
        reasons.append(f"✓ Aligns well with your **{st.session_state.skin_tone}** skin tone palette and colour preferences")
    if occasion_pct >= 80:
        reasons.append(f"✓ Highly appropriate for **{st.session_state.occasion}** settings")
    if budget_pct == 100:
        reasons.append(f"✓ Comfortably fits within your **{money(float(st.session_state.budget))}** budget limit")
    elif budget_pct > 0:
        reasons.append(f"✓ Close to your target budget")
    if compat_pct >= 75:
        reasons.append("✓ High visual harmony and coordination between pieces")
        
    if not reasons:
        reasons.append("✓ Selected from available marketplace items based on your criteria")
        
    for r in reasons:
        st.write(r)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='page-kicker'>MATCH SCORE BREAKDOWN</div>", unsafe_allow_html=True)

    # Normalize breakdown scores to percentage approximations for UI
    scores = [
        ("Style Match", int((breakdown.get('style', 0) / 20.0) * 100)),
        ("Colour Harmony", int((breakdown.get('colour', 0) / 30.0) * 100)),
        ("Occasion Fit", int((breakdown.get('occasion', 0) / 20.0) * 100)),
        ("Budget Score", int((breakdown.get('budget', 0) / 15.0) * 100)),
    ]
    for label, val in scores:
        val = min(100, max(0, val)) # Clamp between 0-100
        bar_html = f"""<div style="margin-bottom:0.6rem;">
<div style="display:flex; justify-content:space-between; font-size:0.78rem; font-weight:700; color:#20192d;">
<span>{label}</span>
<span>{val}%</span>
</div>
<div class="progress-bar"><span class="progress-fill" style="width:{val}%;"></span></div>
</div>"""
        st.markdown(bar_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

with col_why_r:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    render_section_heading("Fabric & Textile Details", "🧵")

    for cat, item in cart.items():
        if item:
            fab_name = item.get("fabric", "Cotton Blend")
            note = DEMO_FABRIC_NOTES.get(fab_name, "Comfortable textile tailored for daily wear.")
            fab_html = f"""<div class="explain-card" style="margin-bottom:0.75rem;">
<h4>{item['category']}: {item['item_name']}</h4>
<p><strong>Fabric:</strong> {fab_name} ({item.get('fabric_tag', 'N/A')})</p>
<p style="font-size:0.76rem; color:#625b6e; margin-top:0.2rem;">{note}</p>
</div>"""
            st.markdown(fab_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Navigation
col_fn1, col_fn2, col_fn3 = st.columns(3)

with col_fn1:
    if st.button("← Back to Marketplace", use_container_width=True):
        st.switch_page("pages/04_AI_Outfit_Recommendations.py")

with col_fn2:
    if st.button("✨ Customize Outfit", use_container_width=True):
        st.switch_page("pages/06_Customize_My_Outfit.py")

with col_fn3:
    if st.button("Budget Stylist →", type="primary", use_container_width=True):
        st.switch_page("pages/07_Budget_Stylist.py")
