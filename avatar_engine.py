from __future__ import annotations

from typing import Dict, Optional


def render_fashion_avatar_svg(
    params: dict,
    outfit_items: Optional[dict] = None,
    compact: bool = False,
    full_component: bool = False,
) -> str:
    """Renders a polished, 3D-styled fashion model silhouette with smooth anatomical curves,

    dimensional skin shading, layered hair paths, clothing cut silhouettes, lighting highlights,
    and centered alignment.
    """
    gender = params.get("gender", "Female")
    skin_label = params.get("skin_tone", "Medium")
    hair_style = params.get("hair_style", "Long Straight")
    hair_colour_label = params.get("hair_colour", "Dark Brown")
    body_shape = params.get("body_shape", "Balanced")
    height_cm = float(params.get("height", 168))
    weight_kg = float(params.get("weight", 58))
    occasion = params.get("occasion", "College")
    model_preset = params.get("model_preset", "Model A")
    accessory = params.get("accessory", "Minimal Watch")

    # 1. Dimensional Skin Colors (3D Gradient Highlights & Shadows)
    skin_colors = {
        "Porcelain": {"base": "#f8dfd4", "shadow": "#e4bcae", "highlight": "#fff5ef", "blush": "#e89994"},
        "Light Beige": {"base": "#eabfa6", "shadow": "#cf9e83", "highlight": "#f8e6da", "blush": "#df877e"},
        "Warm Almond": {"base": "#c9906d", "shadow": "#a67150", "highlight": "#dfaa88", "blush": "#b8615b"},
        "Medium": {"base": "#c9906d", "shadow": "#a67150", "highlight": "#dfaa88", "blush": "#b8615b"},
        "Golden Tan": {"base": "#ac6d4c", "shadow": "#8a5032", "highlight": "#c68864", "blush": "#a84e44"},
        "Deep Cocoa": {"base": "#774734", "shadow": "#573022", "highlight": "#915c47", "blush": "#6e382d"},
        "Espresso": {"base": "#482928", "shadow": "#301918", "highlight": "#5f3836", "blush": "#422020"},
    }
    skin = skin_colors.get(skin_label, skin_colors["Medium"])

    # 2. Hair Colors
    hair_colors = {
        "Black": {"base": "#16131c", "highlight": "#383144"},
        "Dark Brown": {"base": "#35231c", "highlight": "#593d32"},
        "Brown": {"base": "#684332", "highlight": "#8c5e48"},
        "Light Brown": {"base": "#895d44", "highlight": "#ac795b"},
        "Blonde": {"base": "#d4a762", "highlight": "#f0c986"},
        "Auburn": {"base": "#7d3323", "highlight": "#a64935"},
        "Red": {"base": "#ad3825", "highlight": "#d4523d"},
    }
    hair = hair_colors.get(hair_colour_label, hair_colors["Dark Brown"])

    # 3. Anatomical Proportions derived from Height & Weight
    height_scale = 0.86 + (height_cm - 140) / 70.0 * 0.28
    width_scale = 0.88 + (weight_kg - 40) / 80.0 * 0.28

    if body_shape == "Slim":
        width_scale *= 0.90
    elif body_shape == "Curvy":
        width_scale *= 1.14
    elif body_shape == "Athletic":
        width_scale *= 1.05

    torso_w = 76 * width_scale if gender == "Female" else 92 * width_scale
    shoulder_w = 88 * width_scale if gender == "Female" else 108 * width_scale
    hip_w = 90 * width_scale if gender == "Female" else 84 * width_scale

    # Pose Shift & Stance Variations (Model A vs Model B)
    if model_preset == "Model B":
        arm_l_path = "M 104 172 L 72 265 Q 68 280 82 282 L 102 205"
        arm_r_path = "M 194 172 L 208 235 L 180 270 Q 172 265 178 245 L 190 205"
        leg_l_path = "M 125 330 L 115 460 Q 120 475 132 472 L 140 330"
        leg_r_path = "M 158 330 L 172 460 Q 182 475 188 460 L 172 330"
        pose_rotate = "transform='rotate(4 150 250)'"
    else:
        arm_l_path = f"M {150 - shoulder_w/2} 175 L {112} 265 Q {104} 280 {116} 282 L {132} 205"
        arm_r_path = f"M {150 + shoulder_w/2} 175 L {188} 265 Q {196} 280 {184} 282 L {168} 205"
        leg_l_path = "M 125 335 L 120 465 Q 125 478 135 475 L 142 335"
        leg_r_path = "M 158 335 L 165 475 Q 175 478 180 465 L 175 335"
        pose_rotate = ""

    # 4. Item-Specific Garment Layering Logic
    top_color = "#8b5cf6"
    top_type = "Tee"
    bottom_color = "#2563eb"
    bottom_type = "Jeans"
    shoe_color = "#1e293b"
    shoe_type = "Sneakers"
    acc_type = accessory

    if outfit_items:
        if outfit_items.get("Top"):
            t_item = outfit_items["Top"]
            name = t_item.get("item_name", "").lower()
            if "blazer" in name:
                top_type = "Blazer"
                top_color = "#1e293b"
            elif "shirt" in name or "oxford" in name:
                top_type = "Shirt"
                top_color = "#f8fafc" if "white" in name else "#3b82f6"
            elif "blouse" in name or "wrap" in name:
                top_type = "Blouse"
                top_color = "#be185d"
            elif "kurti" in name or "ethnic" in name:
                top_type = "Kurti"
                top_color = "#d97706"
            else:
                top_type = "Tee"
                top_color = "#8b5cf6"

        if outfit_items.get("Bottom"):
            b_item = outfit_items["Bottom"]
            name = b_item.get("item_name", "").lower()
            if "wide" in name or "palazzo" in name:
                bottom_type = "Wide"
                bottom_color = "#0f172a" if "black" in name else "#475569"
            elif "chino" in name or "trouser" in name:
                bottom_type = "Chino"
                bottom_color = "#d97706" if "beige" in name or "khaki" in name else "#334155"
            elif "flare" in name or "leather" in name:
                bottom_type = "Flare"
                bottom_color = "#451a03"
            else:
                bottom_type = "Jeans"
                bottom_color = "#1d4ed8"

        if outfit_items.get("Shoes"):
            s_item = outfit_items["Shoes"]
            name = s_item.get("item_name", "").lower()
            if "loafer" in name:
                shoe_type = "Loafers"
                shoe_color = "#78350f"
            elif "heel" in name or "stiletto" in name:
                shoe_type = "Heels"
                shoe_color = "#be185d"
            elif "mojari" in name or "ethnic" in name:
                shoe_type = "Mojaris"
                shoe_color = "#d97706"
            else:
                shoe_type = "Sneakers"
                shoe_color = "#f8fafc"

        if outfit_items.get("Accessory"):
            a_item = outfit_items["Accessory"]
            name = a_item.get("item_name", "").lower()
            if "watch" in name:
                acc_type = "Minimal Watch"
            elif "tote" in name:
                acc_type = "Canvas Tote"
            elif "handbag" in name or "bag" in name:
                acc_type = "Handbag"
            elif "earring" in name:
                acc_type = "Earrings"
            elif "glasses" in name or "sunglasses" in name:
                acc_type = "Sunglasses"

    # SVG Garment Layer Renderers
    # TOP GARMENT SILHOUETTE
    if top_type == "Blazer":
        top_garment_svg = f"""
            <!-- Blazer Structured Lapels & Fit -->
            <path d="M{150 - shoulder_w/2 - 4} 170 L{150 + shoulder_w/2 + 4} 170 L{150 + torso_w/2 + 6} 275 L{150 - torso_w/2 - 6} 275 Z" fill="{top_color}"/>
            <path d="M150 170 L135 220 L150 275 L165 220 Z" fill="#ffffff" opacity="0.9"/>
            <path d="M{150 - shoulder_w/2 - 4} 170 L138 225 L150 275" fill="none" stroke="#0f172a" stroke-width="2"/>
            <path d="M{150 + shoulder_w/2 + 4} 170 L162 225 L150 275" fill="none" stroke="#0f172a" stroke-width="2"/>
            <circle cx="150" cy="245" r="3" fill="#f59e0b"/>
        """
    elif top_type == "Shirt":
        top_garment_svg = f"""
            <!-- Tailored Oxford Shirt -->
            <path d="M{150 - shoulder_w/2 - 2} 172 Q150 158 {150 + shoulder_w/2 + 2} 172 L{150 + torso_w/2 + 2} 270 Q150 280 {150 - torso_w/2 - 2} 270 Z" fill="{top_color}"/>
            <path d="M136 172 L150 190 L164 172" fill="#e2e8f0"/>
            <path d="M150 190 L150 270" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="3,3"/>
            <circle cx="150" cy="205" r="2" fill="#475569"/>
            <circle cx="150" cy="225" r="2" fill="#475569"/>
            <circle cx="150" cy="245" r="2" fill="#475569"/>
        """
    elif top_type == "Blouse":
        top_garment_svg = f"""
            <!-- Satin Wrap Blouse -->
            <path d="M{150 - shoulder_w/2 - 3} 170 Q150 160 {150 + shoulder_w/2 + 3} 170 L{150 + torso_w/2 + 4} 270 Q150 285 {150 - torso_w/2 - 4} 270 Z" fill="{top_color}"/>
            <path d="M{150 - shoulder_w/2} 170 Q130 220 160 270" fill="none" stroke="#fda4af" stroke-width="2.5"/>
        """
    elif top_type == "Kurti":
        top_garment_svg = f"""
            <!-- Handloom Ethnic Kurti Tunic -->
            <path d="M{150 - shoulder_w/2 - 2} 170 Q150 158 {150 + shoulder_w/2 + 2} 170 L{150 + torso_w/2 + 6} 310 Q150 318 {150 - torso_w/2 - 6} 310 Z" fill="{top_color}"/>
            <path d="M142 170 L150 205 L158 170" fill="#fef3c7" stroke="#b45309" stroke-width="1.5"/>
        """
    else:
        top_garment_svg = f"""
            <!-- Casual Crewneck Tee Cut -->
            <path d="M{150 - shoulder_w/2 - 2} 172 Q150 158 {150 + shoulder_w/2 + 2} 172 L{150 + torso_w/2 + 2} 270 Q150 280 {150 - torso_w/2 - 2} 270 Z" fill="{top_color}"/>
            <path d="M136 172 Q150 184 164 172" fill="none" stroke="#6d28d9" stroke-width="2"/>
        """

    # BOTTOM GARMENT SILHOUETTE
    if bottom_type == "Wide":
        bottom_garment_svg = f"""
            <!-- High-Waist Wide Trouser Drape -->
            <path d="M{150 - hip_w/2 - 4} 270 Q150 282 {150 + hip_w/2 + 4} 270 L{150 + hip_w/2 + 10} 445 L152 445 L150 310 L148 445 L{150 - hip_w/2 - 10} 445 Z" fill="{bottom_color}"/>
        """
    elif bottom_type == "Chino":
        bottom_garment_svg = f"""
            <!-- Tailored Slim Chino Trousers -->
            <path d="M{150 - hip_w/2 - 3} 270 Q150 282 {150 + hip_w/2 + 3} 270 L{150 + hip_w/2 - 4} 445 L152 445 L150 310 L148 445 L{150 - hip_w/2 + 4} 445 Z" fill="{bottom_color}"/>
        """
    elif bottom_type == "Flare":
        bottom_garment_svg = f"""
            <!-- Flare Trouser Cut -->
            <path d="M{150 - hip_w/2 - 3} 270 Q150 282 {150 + hip_w/2 + 3} 270 L{150 + hip_w/2 + 8} 445 L152 445 L150 310 L148 445 L{150 - hip_w/2 - 8} 445 Z" fill="{bottom_color}"/>
        """
    else:
        bottom_garment_svg = f"""
            <!-- Classic Denim Jeans Silhouette -->
            <path d="M{150 - hip_w/2 - 4} 270 Q150 282 {150 + hip_w/2 + 4} 270 L{150 + hip_w/2 - 2} 445 L152 445 L150 310 L148 445 L{150 - hip_w/2 + 2} 445 Z" fill="{bottom_color}"/>
            <path d="M150 270 L150 310" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="2,2"/>
        """

    # FOOTWEAR SILHOUETTE
    if shoe_type == "Loafers":
        shoe_garment_svg = f"""
            <path d="M116 458 Q130 452 142 464 L142 476 Q125 480 114 470 Z" fill="{shoe_color}"/>
            <path d="M158 464 Q170 452 184 458 L186 470 Q175 480 158 476 Z" fill="{shoe_color}"/>
            <rect x="122" y="460" width="14" height="4" fill="#f59e0b"/>
            <rect x="164" y="460" width="14" height="4" fill="#f59e0b"/>
        """
    elif shoe_type == "Heels":
        shoe_garment_svg = f"""
            <path d="M120 460 L126 478 L122 482 L116 468 Z" fill="{shoe_color}"/>
            <path d="M180 460 L174 478 L178 482 L184 468 Z" fill="{shoe_color}"/>
            <path d="M118 460 Q130 458 140 465 L138 472 Q125 470 116 464 Z" fill="{shoe_color}"/>
            <path d="M160 465 Q170 458 182 460 L184 464 Q175 470 162 472 Z" fill="{shoe_color}"/>
        """
    elif shoe_type == "Mojaris":
        shoe_garment_svg = f"""
            <path d="M114 458 Q130 452 142 464 L142 476 Q125 482 110 468 Z" fill="{shoe_color}"/>
            <path d="M158 464 Q170 452 186 458 L190 468 Q175 482 158 476 Z" fill="{shoe_color}"/>
        """
    else:
        shoe_garment_svg = f"""
            <path d="M118 460 Q130 454 142 464 L142 476 Q125 482 114 470 Z" fill="{shoe_color}"/>
            <path d="M158 464 Q170 454 182 460 L186 470 Q175 482 158 476 Z" fill="{shoe_color}"/>
            <rect x="116" y="470" width="26" height="5" fill="#ffffff" rx="2"/>
            <rect x="158" y="470" width="26" height="5" fill="#ffffff" rx="2"/>
        """

    # HAIR SILHOUETTE
    hair_svg = {
        "Long Straight": f"""
            <path d="M106 100 C 98 42, 202 42, 194 100 C 198 160, 196 245, 190 295 C 182 295, 175 255, 172 170 C 160 88, 140 88, 128 170 C 125 255, 118 295, 110 295 C 104 245, 102 160, 106 100 Z" fill="{hair['base']}"/>
            <path d="M122 70 Q 150 55 178 70 Q 150 75 122 70" fill="{hair['highlight']}" opacity="0.6"/>
        """,
        "Wavy": f"""
            <path d="M105 100 C 94 38, 206 38, 195 100 C 206 155, 186 205, 197 265 C 183 265, 179 215, 172 170 C 160 88, 140 88, 128 170 C 121 215, 117 265, 103 265 C 114 205, 94 155, 105 100 Z" fill="{hair['base']}"/>
            <path d="M125 72 Q 150 58 175 72" fill="none" stroke="{hair['highlight']}" stroke-width="4" opacity="0.5"/>
        """,
        "Curly": f"""
            <circle cx="150" cy="82" r="48" fill="{hair['base']}"/>
            <circle cx="116" cy="102" r="24" fill="{hair['base']}"/>
            <circle cx="184" cy="102" r="24" fill="{hair['base']}"/>
            <circle cx="108" cy="132" r="22" fill="{hair['base']}"/>
            <circle cx="192" cy="132" r="22" fill="{hair['base']}"/>
            <circle cx="112" cy="162" r="20" fill="{hair['base']}"/>
            <circle cx="188" cy="162" r="20" fill="{hair['base']}"/>
            <circle cx="150" cy="65" r="20" fill="{hair['highlight']}" opacity="0.4"/>
        """,
        "Bob": f"""
            <path d="M106 100 C 98 42, 202 42, 194 100 C 198 152, 182 178, 172 178 C 160 88, 140 88, 128 178 C 118 178, 102 152, 106 100 Z" fill="{hair['base']}"/>
            <path d="M125 70 Q 150 58 175 70" fill="none" stroke="{hair['highlight']}" stroke-width="4" opacity="0.5"/>
        """,
        "Ponytail": f"""
            <ellipse cx="206" cy="112" rx="18" ry="48" fill="{hair['base']}" transform="rotate(18 206 112)"/>
            <path d="M106 100 C 98 42, 202 42, 194 100 C 180 84, 120 84, 106 100 Z" fill="{hair['base']}"/>
            <rect x="187" y="96" width="12" height="9" rx="3" fill="{top_color}"/>
        """,
        "Bun": f"""
            <circle cx="150" cy="45" r="26" fill="{hair['base']}"/>
            <circle cx="150" cy="45" r="14" fill="{hair['highlight']}" opacity="0.3"/>
            <path d="M106 100 C 98 52, 202 52, 194 100 C 180 86, 120 86, 106 100 Z" fill="{hair['base']}"/>
        """,
    }.get(hair_style, f"<path d='M106 100 C 98 42, 202 42, 194 100 Z' fill='{hair['base']}'/>")

    # Accessory SVG
    accessory_svg = {
        "Glasses": "<g fill='none' stroke='#1e293b' stroke-width='3.5'><rect x='118' y='122' width='26' height='16' rx='5'/><rect x='156' y='122' width='26' height='16' rx='5'/><path d='M144 128 h12'/></g>",
        "Sunglasses": "<g fill='#0f172a' opacity='0.92'><rect x='116' y='120' width='30' height='18' rx='6'/><rect x='154' y='120' width='30' height='18' rx='6'/><path d='M146 126 h8' stroke='#0f172a' stroke-width='3'/></g>",
        "Earrings": "<circle cx='108' cy='144' r='4.5' fill='#f59e0b'/><circle cx='192' cy='144' r='4.5' fill='#f59e0b'/>",
        "Minimal Watch": "<rect x='194' y='275' width='10' height='20' rx='3' fill='#f59e0b'/><circle cx='199' cy='285' r='5' fill='#ffffff'/>",
        "Canvas Tote": f"<path d='M75 260 L70 350 Q115 365 160 350 L155 260 Z' fill='#f8fafc' stroke='#cbd5e1' stroke-width='2'/><path d='M92 260 Q115 218 138 260' fill='none' stroke='#475569' stroke-width='3'/>",
        "Handbag": f"<path d='M180 270 L175 330 Q205 340 235 330 L230 270 Z' fill='#1e293b'/><path d='M195 270 Q205 240 215 270' fill='none' stroke='#f59e0b' stroke-width='3'/>",
    }.get(acc_type, "")

    scale_style = "transform: scale(0.82); transform-origin: top center;" if compact else ""

    svg_content = f"""
    <svg viewBox="0 0 300 520" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="3D Dimensional Fashion Model Avatar" style="{scale_style}">
        <defs>
            <linearGradient id="bgGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#f5eeff"/>
                <stop offset="100%" stop-color="#fff0f5"/>
            </linearGradient>
            <linearGradient id="skinGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{skin['highlight']}"/>
                <stop offset="50%" stop-color="{skin['base']}"/>
                <stop offset="100%" stop-color="{skin['shadow']}"/>
            </linearGradient>
            <filter id="softShadow" x="-10%" y="-10%" width="120%" height="120%">
                <feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#2d174d" flood-opacity="0.14"/>
            </filter>
        </defs>

        <!-- Model Ground Shadow -->
        <ellipse cx="150" cy="485" rx="75" ry="12" fill="#2d174d" opacity="0.12"/>

        <g filter="url(#softShadow)" {pose_rotate}>
            <!-- Legs (Skin Base) -->
            <path d="{leg_l_path}" fill="url(#skinGrad)"/>
            <path d="{leg_r_path}" fill="url(#skinGrad)"/>

            <!-- Footwear Silhouette -->
            {shoe_garment_svg}

            <!-- Bottom Apparel Silhouette -->
            {bottom_garment_svg}

            <!-- Torso / Waist / Chest (Skin Base) -->
            <path d="M{150 - shoulder_w/2} 170 Q150 155 {150 + shoulder_w/2} 170 L{150 + torso_w/2} 275 Q150 290 {150 - torso_w/2} 275 Z" fill="url(#skinGrad)"/>

            <!-- Top Apparel Silhouette -->
            {top_garment_svg}

            <!-- Arms & Hands -->
            <path d="{arm_l_path}" fill="url(#skinGrad)"/>
            <path d="{arm_r_path}" fill="url(#skinGrad)"/>

            <!-- Neck -->
            <path d="M136 142 L164 142 L168 178 Q150 188 132 178 Z" fill="url(#skinGrad)"/>

            <!-- Head & Facial Contour -->
            <ellipse cx="150" cy="122" rx="36" ry="46" fill="url(#skinGrad)"/>

            <!-- Hair Layer -->
            {hair_svg}

            <!-- Facial Features (Dimensional Touch) -->
            <path d="M132 120 Q140 114 144 120 M156 120 Q160 114 168 120" stroke="#3b231c" stroke-width="2.5" fill="none" stroke-linecap="round"/>
            <ellipse cx="138" cy="128" rx="4" ry="5" fill="#2d1a15"/>
            <ellipse cx="162" cy="128" rx="4" ry="5" fill="#2d1a15"/>
            <!-- Subtle Blush -->
            <ellipse cx="128" cy="138" rx="6" ry="3" fill="{skin['blush']}" opacity="0.4"/>
            <ellipse cx="172" cy="138" rx="6" ry="3" fill="{skin['blush']}" opacity="0.4"/>
            <!-- Nose & Lips Cut -->
            <path d="M149 130 L147 140 L152 141" stroke="{skin['shadow']}" stroke-width="2" fill="none" stroke-linecap="round"/>
            <path d="M140 152 Q150 160 160 152 Q150 155 140 152" fill="#d9777f"/>

            <!-- Accessories Layer -->
            {accessory_svg}
        </g>
    </svg>
    """

    if full_component:
        html_wrapper = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    overflow: hidden;
                    font-family: system-ui, -apple-system, sans-serif;
                }}
                .model-card {{
                    background: linear-gradient(160deg, #f0e7ff 0%, #fff0f4 50%, #ffffff 100%);
                    border: 1px solid rgba(107,75,176,0.18);
                    border-radius: 24px;
                    padding: 12px;
                    box-shadow: 0 16px 36px rgba(42,28,64,0.08);
                    width: 100%;
                    height: 100%;
                    box-sizing: border-box;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                }}
                .canvas {{
                    background: rgba(255,255,255,0.85);
                    border-radius: 18px;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
            </style>
        </head>
        <body>
            <div class="model-card">
                <div class="canvas">
                    {svg_content}
                </div>
            </div>
        </body>
        </html>
        """
        return html_wrapper

    return svg_content
