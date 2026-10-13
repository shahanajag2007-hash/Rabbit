from __future__ import annotations

import streamlit as st

from demo_data import DEMO_FABRIC_NOTES, DEMO_PALETTES, DEMO_SUGGESTION_CHIPS
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
    "AI Preference Analysis & Fashion Marketplace",
    "Tell your AI stylist your vision and explore curated marketplace recommendations.",
    active="05 Recommendations",
)

render_step_progress(step_num=4, total_steps=5, step_title="Preference Analysis & Marketplace")

# ==============================================================================
# SCREEN 5: "TELL US YOUR PREFERENCE" - AI STYLIST ANALYSIS
# ==============================================================================
st.markdown("<div class='panel' style='margin-bottom:1.5rem;'>", unsafe_allow_html=True)
render_section_heading("Tell Us Your Preference", "💬")

st.caption("Tell your AI stylist what you are looking for today.")

pref_text = st.session_state.get("preference_text", "")
user_prompt = st.text_area(
    "Describe your styling mood or occasion goals",
    value=pref_text,
    placeholder="Example: I want a comfortable college outfit with a minimal style, preferably in blue or neutral shades...",
    height=100,
)
st.session_state.preference_text = user_prompt

# Suggestion Chips
st.markdown("<div class='page-kicker' style='margin-top:0.6rem;'>QUICK SUGGESTION CHIPS</div>", unsafe_allow_html=True)
chip_cols = st.columns(len(DEMO_SUGGESTION_CHIPS))
for idx, chip in enumerate(DEMO_SUGGESTION_CHIPS):
    with chip_cols[idx]:
        if st.button(chip, key=f"chip_btn_{idx}", use_container_width=True):
            if chip not in st.session_state.preference_text:
                st.session_state.preference_text = (st.session_state.preference_text + " " + chip).strip()
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

if st.button("✨ ANALYZE MY STYLE", type="primary", use_container_width=True):
    st.session_state.style_analyzed = True
    st.success("Preference analysis complete! Styling profile generated.")

if st.session_state.get("style_analyzed", False) or user_prompt:
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(107,75,176,0.08), rgba(239,125,143,0.08)); border: 1px solid rgba(107,75,176,0.18); border-radius: 18px; padding: 1rem; margin-top: 1rem;">
            <div class="page-kicker">YOUR GENERATED STYLE PROFILE</div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #1f162d; margin-top: 0.2rem;">
                {st.session_state.style} + {st.session_state.occasion} + Comfortable
            </div>
            <div style="font-size: 0.82rem; color: #5f5a6d; margin-top: 0.3rem;">
                <strong>Styling Direction:</strong> Clean, practical and modern. Prioritizing breathable textiles and harmonized color palettes suitable for {st.session_state.occasion.lower()}.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# SCREEN 6: MAIN CLOTHING RECOMMENDATION MARKETPLACE DASHBOARD
# ==============================================================================
st.markdown("<div class='panel'>", unsafe_allow_html=True)
render_section_heading("Recommended Colour Palette", "🎨")

skin_key = st.session_state.get("skin_tone", "Medium")

# Handle Skin Tone key mapping
if skin_key in ["Porcelain", "Light Beige"]:
    palette_key = "Light"
elif skin_key in ["Golden Tan", "Tan"]:
    palette_key = "Tan"
elif skin_key in ["Deep Cocoa", "Espresso", "Deep"]:
    palette_key = "Deep"
else:
    palette_key = "Medium"

palette_swatches = DEMO_PALETTES.get(palette_key, DEMO_PALETTES["Medium"])

st.markdown(
    f"<div style='font-size:0.82rem; color:#625b6e; margin-bottom:0.8rem;'>Curated color swatches based on your <strong>{skin_key}</strong> skin tone and <strong>{st.session_state.occasion}</strong> setting.</div>",
    unsafe_allow_html=True,
)

cols_p = st.columns(len(palette_swatches))
for idx, swatch in enumerate(palette_swatches):
    with cols_p[idx]:
        st.markdown(
            f"""
            <div style="text-align:center; background:#ffffff; border:1px solid rgba(103,80,154,0.12); border-radius:16px; padding:0.6rem;">
                <div style="width:100%; height:42px; border-radius:10px; background:{swatch['hex']}; margin-bottom:0.4rem; border:1px solid rgba(0,0,0,0.08);"></div>
                <div style="font-weight:800; font-size:0.75rem; color:#1f162d;">{swatch['name']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)
render_section_heading("Fashion Marketplace Product Grid", "🛍️")

import recommender

# Generate User Profile
user_profile = {
    "gender": st.session_state.get("gender"),
    "height": st.session_state.get("height"),
    "weight": st.session_state.get("weight"),
    "skin_tone": st.session_state.get("skin_tone"),
    "style": st.session_state.get("style"),
    "occasion": st.session_state.get("occasion"),
    "budget": st.session_state.get("budget"),
    "favorite_colours": st.session_state.get("favorite_colours", []),
    "avoid_colours": st.session_state.get("avoid_colours", [])
}
st.session_state["user_profile"] = user_profile

# Connect to backend
df = recommender.load_dataset()
outfits = recommender.recommend_outfits(
    frame=df,
    user_profile=user_profile,
    limit=3
)
st.session_state["recommended_outfits"] = outfits

if not outfits:
    st.warning("No outfits found for this criteria.")
else:
    for idx, outfit in enumerate(outfits):
        st.markdown(f"<div style='font-size:1.2rem; font-weight:800; color:#1d1528; margin:1.5rem 0 0.5rem;'>Recommended Outfit {idx + 1}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.9rem; color:#625b6e; margin-bottom:1rem;'>Total: {money(outfit['total_price'])} | Compatibility Score: {outfit['score']}/100</div>", unsafe_allow_html=True)
        
        if st.button(f"Select Outfit {idx + 1}", key=f"select_outfit_{idx}", type="primary"):
            st.session_state.selected_outfit = outfit
            st.session_state.cart_items = outfit["items"]
            st.session_state.step_progress = 5
            st.switch_page("pages/05_Outfit_Details.py")

        cols_grid = st.columns(4)
        for c_idx, cat in enumerate(["Top", "Bottom", "Shoes", "Accessory"]):
            if cat in outfit["items"]:
                item = outfit["items"][cat]
                with cols_grid[c_idx]:
                    is_in_cart = st.session_state.cart_items.get(cat, {}).get("item_id") == item["item_id"]
                    
                    import base64
                    import os
                    import urllib.parse
                    
                    img_filename = item.get('image', '')
                    img_url = ""
                    
                    if img_filename:
                        # Try to find the image in likely directories
                        found = False
                        for folder in ["images", "static", "data", "."]:
                            path = os.path.join(folder, img_filename)
                            if os.path.exists(path):
                                with open(path, "rb") as f:
                                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                                    # determine mime type
                                    ext = os.path.splitext(img_filename)[1].lower()
                                    mime = "image/png" if ext == ".png" else "image/jpeg"
                                    img_url = f"data:{mime};base64,{b64_data}"
                                found = True
                                break
                        if not found:
                            # Fallback if image file is not found locally
                            img_url = f"https://placehold.co/400x500/e6e4eb/1d1528?text={urllib.parse.quote(item['item_name'])}"
                    else:
                        img_url = f"https://placehold.co/400x500/e6e4eb/1d1528?text={urllib.parse.quote(item['item_name'])}"

                    st.markdown(
                        f"""
                        <div class="product-card" style="margin-bottom:1.1rem;">
                            <div class="product-image-container">
                                <img src="{img_url}" alt="{item['item_name']}"/>
                                <div class="platform-badge">{item.get('category', '')}</div>
                            </div>
                            <div class="product-info">
                                <div class="product-name">{item['item_name']}</div>
                                <div class="product-meta">{item['colour']} · {item['style']}</div>
                                <div class="product-price-row">
                                    <div class="product-price">{money(item['price'])}</div>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col_m1, col_m2 = st.columns([1, 1])
with col_m2:
    if st.button("GO TO COMPLETE OUTFIT STYLING →", type="primary", use_container_width=True):
        st.session_state.step_progress = 5
        st.switch_page("pages/05_Outfit_Details.py")
