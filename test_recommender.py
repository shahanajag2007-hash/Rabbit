import pandas as pd
import recommender

df = recommender.load_dataset()

# Test Profile A
profile_a = {
    "gender": "Female",
    "height": 160,
    "weight": 55,
    "skin_tone": "Medium",
    "style": "Casual",
    "occasion": "College",
    "budget": 3500,
    "favorite_colours": ["Navy", "White"],
    "avoid_colours": ["Orange"]
}

outfits_a = recommender.recommend_outfits(df, profile_a)
print("Profile A - College Casual")
for idx, o in enumerate(outfits_a):
    print(f"Outfit {idx+1}: Score {o['score']} Price {o['total_price']}")
    for cat, item in o['items'].items():
        print(f"  {cat}: {item['item_name']} ({item['colour']}, {item['style']}, {item['occasion']})")

# Test Profile B
profile_b = {
    "gender": "Male",
    "height": 175,
    "weight": 70,
    "skin_tone": "Medium",
    "style": "Formal",
    "occasion": "Office",
    "budget": 5000,
    "favorite_colours": ["Black", "Navy"],
    "avoid_colours": ["Yellow"]
}

outfits_b = recommender.recommend_outfits(df, profile_b)
print("\nProfile B - Office Formal")
for idx, o in enumerate(outfits_b):
    print(f"Outfit {idx+1}: Score {o['score']} Price {o['total_price']}")

# Test Cheaper Alternative
expensive_top = df[(df["category"] == "Top") & (df["price"] > 1000)].iloc[0].to_dict()
print("\nCheaper Alternative Test")
print(f"Original: {expensive_top['item_name']} - {expensive_top['price']} - {expensive_top['colour']}")
cheaper = recommender.get_cheaper_alternative(df, expensive_top)
if cheaper:
    print(f"Cheaper: {cheaper['item_name']} - {cheaper['price']} - {cheaper['colour']}")
else:
    print("No cheaper alternative found.")

# Test Replacements
if outfits_a:
    top_replacements = recommender.get_replacement_candidates(df, "Top", outfits_a[0], profile_a)
    print("\nReplacements for Top:")
    for r in top_replacements[:3]:
        print(f"  {r['items']['Top']['item_name']} ({r['items']['Top']['price']})")
