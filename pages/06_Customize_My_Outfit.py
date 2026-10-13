from __future__ import annotations
import streamlit as st
import pandas as pd
from recommender import CATEGORIES, get_replacement_candidates, get_cheaper_alternative, recommend_outfits, score_single_outfit, load_dataset
from ui_theme import apply_theme, ensure_session_defaults, money, render_page_header, render_section_heading

apply_theme()
ensure_session_defaults()

render_page_header("Make It Yours", "Keep what you love and personalize the rest of your outfit.")

if not st.session_state.get("selected_outfit"):
    st.info("Select an outfit from the Recommendations page first to customize it.")
    st.stop()

outfit = st.session_state.selected_outfit
user_profile = st.session_state.get("user_profile", {})
df = load_dataset()

# Ensure locked_items exists in session state
if "locked_items" not in st.session_state:
    st.session_state.locked_items = {cat: False for cat in CATEGORIES}

# Helper to sync checkbox state
def toggle_lock(cat):
    st.session_state.locked_items[cat] = st.session_state[f"chk_lock_{cat}"]

render_section_heading("Lock what you love", "🔒")
lock_cols = st.columns(4)
for category, column in zip(CATEGORIES, lock_cols):
    with column:
        st.markdown(f"<div class='mini-card'><div style='font-size:1.5rem; margin-bottom:0.4rem;'>{'👕' if category == 'Top' else '👖' if category == 'Bottom' else '👟' if category == 'Shoes' else '⌚'}</div><div style='font-weight:700; color:#1b1528;'>{category}</div></div>", unsafe_allow_html=True)
        st.checkbox(f"Lock {category}", value=st.session_state.locked_items.get(category, False), key=f"chk_lock_{category}", on_change=toggle_lock, args=(category,))

st.markdown("<br>", unsafe_allow_html=True)

# Display Current Outfit Score & Budget Info
current_score_info = score_single_outfit(outfit, user_profile)
total_price = current_score_info["total_price"]
budget = float(user_profile.get("budget", 3500.0))
budget_diff = budget - total_price

st.markdown(f"<div style='background: {'#f0fdf4' if budget_diff >= 0 else '#fef2f2'}; padding:1rem; border-radius:12px; margin-bottom:1.5rem;'>", unsafe_allow_html=True)
st.markdown(f"**Total Outfit Price:** {money(total_price)} (Budget: {money(budget)})")
if budget_diff < 0:
    st.markdown(f"<span style='color:#dc2626; font-weight:bold;'>Over budget by {money(abs(budget_diff))}</span>", unsafe_allow_html=True)
    
    # Initialize Shopping Integration Layer
    from shopping import ShoppingService
    import os
    
    # For dev mode, you can set this env variable outside the script, or just toggle this line.
    os.environ["USE_MOCK_SHOPPING_DATA"] = "True"
    
    # Cache shopping results in session state to prevent losing them during reruns
    if "shopping_results" not in st.session_state or st.session_state.get("last_outfit_sig") != tuple(item.get("item_id") for item in outfit.get("items", {}).values()):
        with st.spinner("Searching multi-platform for cheaper alternatives..."):
            service = ShoppingService()
            locked_cats = [cat for cat, is_locked in st.session_state.locked_items.items() if is_locked]
            st.session_state.shopping_results = service.find_cheaper_alternatives(outfit, budget, locked_cats)
            st.session_state.last_outfit_sig = tuple(item.get("item_id") for item in outfit.get("items", {}).values())

    shopping_results = st.session_state.shopping_results

    if shopping_results:
        st.markdown("**Platform Alternatives Found:**")
        total_savings = 0.0
        for cat, alt in shopping_results.items():
            orig_price = alt["original_price"]
            new_price = alt["price"]
            total_savings += alt["savings"]
            
            st.markdown(f"""
            - **{cat}**: 
              *Current*: {money(orig_price)} → *Alternative*: {money(new_price)}
              *Platform*: {alt["platform"]} | *Type*: {alt["match_type"]}
              *Savings*: {money(alt["savings"])}
              [View on {alt["platform"]}]({alt["url"]})
            """)
            
        new_total = total_price - total_savings
        new_diff = budget - new_total
        st.markdown(f"**New Total:** {money(new_total)}")
        if new_diff >= 0:
            st.markdown(f"**Remaining Budget:** {money(new_diff)}")
        else:
            st.markdown(f"**Still over budget by:** {money(abs(new_diff))}")
            
        st.markdown("*You can buy these alternatives instead to keep the outfit within your budget.*")
    else:
        st.markdown("- *No cheaper compatible alternatives found on external platforms.*")
else:
    st.markdown(f"<span style='color:#16a34a; font-weight:bold;'>Under budget by {money(budget_diff)}</span>", unsafe_allow_html=True)
st.markdown(f"**Compatibility Score:** {current_score_info['score']}/100")
st.markdown("</div>", unsafe_allow_html=True)

render_section_heading("Customize each piece", "🔄")

# Process Regeneration
if st.button("✨ Regenerate Unlocked Items", type="primary", use_container_width=True):
    locked = {cat: outfit["items"][cat] for cat, is_locked in st.session_state.locked_items.items() if is_locked and cat in outfit["items"]}
    new_outfits = recommend_outfits(df, user_profile, locked_items=locked, limit=1)
    if new_outfits:
        st.session_state.selected_outfit = new_outfits[0]
        st.session_state.cart_items = new_outfits[0]["items"]
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

for category in CATEGORIES:
    if category not in outfit.get("items", {}):
        continue
    item = outfit["items"][category]
    is_locked = st.session_state.locked_items.get(category, False)
    
    with st.container(border=True):
        st.markdown(
            f"""
            <div style='display:flex; align-items:center; gap:0.6rem; margin-bottom:0.6rem;'>
                <div style='font-size:1.4rem;'>{'👕' if category == 'Top' else '👖' if category == 'Bottom' else '👟' if category == 'Shoes' else '⌚'}</div>
                <div style='font-weight:800; color:#1d1528;'>{category} {'🔒' if is_locked else ''}</div>
            </div>
            <div style='font-weight:700; color:#20192d;'>{item.get('item_name', '')}</div>
            <div class='small-muted' style='margin-top:0.2rem;'>{item.get('colour', '')} · {item.get('style', '')} · {money(float(item.get('price', 0)))}</div>
            """,
            unsafe_allow_html=True,
        )
        
        if not is_locked:
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Replace {category}", key=f"replace_{category}", use_container_width=True):
                    st.session_state.replace_target = category
            with col2:
                if st.button(f"Cheaper Option", key=f"cheaper_{category}", use_container_width=True):
                    cheaper = get_cheaper_alternative(df, item)
                    if cheaper:
                        outfit["items"][category] = cheaper
                        st.session_state.selected_outfit = outfit
                        st.session_state.cart_items = outfit["items"]
                        st.success("Found a cheaper alternative!")
                        st.rerun()
                    else:
                        st.warning("No cheaper compatible alternative found.")
        else:
            st.info("Item is locked. Unlock to replace.")

        # Show replacements if this category is being replaced
        if st.session_state.get("replace_target") == category:
            st.markdown("<div style='margin-top:1rem; font-weight:600;'>Select Replacement:</div>", unsafe_allow_html=True)
            candidates = get_replacement_candidates(df, category, outfit, user_profile)
            if not candidates:
                st.warning("No suitable replacement found for this item.")
            else:
                for idx, cand in enumerate(candidates[:3]):
                    cand_item = cand["items"][category]
                    c_col1, c_col2 = st.columns([3, 1])
                    with c_col1:
                        st.markdown(f"**{cand_item['item_name']}**<br/>{cand_item['colour']} · {money(cand_item['price'])}", unsafe_allow_html=True)
                    with c_col2:
                        if st.button("Use", key=f"use_{category}_{idx}"):
                            outfit["items"][category] = cand_item
                            st.session_state.selected_outfit = outfit
                            st.session_state.cart_items = outfit["items"]
                            st.session_state.replace_target = None
                            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
if st.button("← Back to Outfit Details"):
    st.switch_page("pages/05_Outfit_Details.py")
