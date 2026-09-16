"""
Lifestyle Agent — Behavioral Intelligence for Context-Aware Recommendations

A designer doesn't just look at the room — they look at the person living in it.
This module detects lifestyle signals from room photos and adjusts product
recommendations accordingly.

Pipeline:
  6.1 detect_lifestyle_markers() → Pets, kids, high-traffic detection
  6.2 generate_ensemble_suggestion() → "Shop the Look" secondary product
  6.3 classify_time_of_day() → Day/Evening based on Kelvin temperature
"""

import os
import io
import json
import hashlib
from typing import Dict, List, Optional, Tuple

# ── Lifestyle marker cache: {image_hash: markers_dict} ──
_lifestyle_cache: Dict[str, dict] = {}

# ── Fragile materials that should be deprioritized in tough environments ──
FRAGILE_MATERIALS = {
    "silk", "satin", "velvet", "linen", "suede", "cashmere",
    "glass", "crystal", "porcelain", "ceramic", "paper",
    "marble", "lacquer", "gold leaf",
}

# ── Durable materials that thrive in tough environments ──
DURABLE_MATERIALS = {
    "leather", "jute", "sisal", "canvas", "denim", "performance",
    "polypropylene", "nylon", "iron", "steel", "concrete",
    "teak", "oak", "walnut", "bamboo", "rattan", "wicker",
    "vinyl", "rubber", "plastic", "resin", "stone",
}

# ── Lighting product keywords (for evening mood boost) ──
LIGHTING_KEYWORDS = {
    "lamp", "light", "lantern", "candle", "sconce", "chandelier",
    "pendant", "led", "illumin", "glow", "luminary", "torch",
}


# ═══════════════════════════════════════════════════════════════════════════
# 6.1  LIFESTYLE MARKER DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def detect_lifestyle_markers(
    room_bytes: bytes,
    model_name: str = "gemini-2.5-flash",
) -> dict:
    """
    Analyze a room photo for lifestyle signals that affect product suitability.
    
    Detects:
      - Has_Pets: Dog beds, cat trees, pet bowls, fur on furniture
      - Has_Kids: Toys, kid furniture, safety gates, colorful playmat
      - High_Traffic: Entryway shoes, muddy floors, commercial feel
    
    These markers drive "Negative Boosters" that deprioritize fragile
    materials and boost durable ones in the scoring pipeline.
    
    Returns:
        {
            "has_pets": bool,
            "has_kids": bool,
            "high_traffic": bool,
            "durability_required": float,  # 0.0 (no concern) to 1.0 (max durability)
            "markers_detected": list[str], # Human-readable list of what was found
        }
    """
    img_hash = hashlib.md5(room_bytes[:8192]).hexdigest()
    if img_hash in _lifestyle_cache:
        return _lifestyle_cache[img_hash]
    
    # Default: no lifestyle concerns
    default_result = {
        "has_pets": False,
        "has_kids": False,
        "high_traffic": False,
        "durability_required": 0.0,
        "markers_detected": [],
    }
    
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return default_result
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return default_result
    
    client = genai.Client(api_key=api_key)
    
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(room_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        jpeg_bytes = buf.getvalue()
    except Exception:
        jpeg_bytes = room_bytes
    
    prompt = (
        "Analyze this room photo for LIFESTYLE SIGNALS. Look for:\n"
        "1) PET indicators: dog/cat beds, bowls, pet toys, fur on furniture, pet gates\n"
        "2) CHILD indicators: toys, child furniture, safety gates, kid art, highchair\n"
        "3) HIGH-TRAFFIC indicators: shoes at door, muddy/worn floors, entryway clutter\n\n"
        "Return a JSON object strictly following this format:\n"
        '{"has_pets": false, "has_kids": true, "high_traffic": false, '
        '"markers": ["dog bed", "toys"]}\n\n'
        "If nothing is detected, return all false with empty markers list.\n"
        "Be conservative — only flag what you actually SEE, not what you guess."
    )
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[
                prompt,
                types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=500,
                response_mime_type="application/json",
            ),
        )
        
        try:
            data = json.loads(response.text)
        except Exception as e:
            print(f"[Lifestyle] Parsing failed. Raw response: {repr(response.text)}")
            import re
            text = response.text.strip()
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                text = match.group(0)
            try:
                data = json.loads(text)
            except Exception as e2:
                print(f"[Lifestyle] Fallback parsing failed: {e2}")
                raise e2
        
        has_pets = bool(data.get("has_pets", False))
        has_kids = bool(data.get("has_kids", False))
        high_traffic = bool(data.get("high_traffic", False))
        markers = data.get("markers", [])
        
        # Compute durability requirement score
        durability = 0.0
        if has_pets:
            durability += 0.4
        if has_kids:
            durability += 0.35
        if high_traffic:
            durability += 0.25
        durability = min(1.0, durability)
        
        result = {
            "has_pets": has_pets,
            "has_kids": has_kids,
            "high_traffic": high_traffic,
            "durability_required": round(durability, 2),
            "markers_detected": markers if isinstance(markers, list) else [],
        }
        
        _lifestyle_cache[img_hash] = result
        return result
        
    except Exception as e:
        print(f"[Lifestyle] Detection failed: {e}")
        return default_result


def compute_lifestyle_score_adjustment(
    product: dict,
    lifestyle_markers: dict,
) -> float:
    """
    Compute a score adjustment based on lifestyle-material compatibility.
    
    If the room has pets/kids/high-traffic, fragile materials get penalized
    and durable materials get boosted.
    
    Args:
        product: Product metadata dict
        lifestyle_markers: Output of detect_lifestyle_markers()
    
    Returns:
        Score adjustment (negative = worse fit, positive = better fit)
        Range: approximately -30 to +15
    """
    durability = lifestyle_markers.get("durability_required", 0.0)
    
    if durability < 0.1:
        return 0.0  # No lifestyle concerns, no adjustment
    
    searchable = " ".join([
        (product.get("material") or ""),
        (product.get("Material") or ""),
        (product.get("name") or ""),
        (product.get("notes") or ""),
        (product.get("Notes") or ""),
    ]).lower()
    
    # Check for fragile materials → penalize
    is_fragile = any(mat in searchable for mat in FRAGILE_MATERIALS)
    # Check for durable materials → boost
    is_durable = any(mat in searchable for mat in DURABLE_MATERIALS)
    
    adjustment = 0.0
    
    if is_fragile:
        # Penalty scales with durability requirement
        adjustment += durability * 30.0  # Higher score = worse (in the scoring system)
        
    if is_durable:
        # Boost scales with durability requirement
        adjustment -= durability * 15.0  # Lower score = better
    
    return round(adjustment, 1)


# ═══════════════════════════════════════════════════════════════════════════
# 6.2  DYNAMIC ENSEMBLE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def generate_ensemble_suggestion(
    placed_product: dict,
    room_metadata: dict,
    visual_com: dict,
    available_products: List[dict],
) -> Optional[dict]:
    """
    After a product is placed, suggest a complementary secondary item
    that balances the room's visual weight.
    
    Logic:
      1. Determine what the placed product IS (furniture → suggest decor)
      2. Calculate which side of the room needs balancing
      3. Filter available products for complementary categories
      4. Rank by how well they'd balance the room
    
    Args:
        placed_product: The product that was just placed
        room_metadata: Room analysis metadata
        visual_com: Visual center-of-mass data with bias_x
        available_products: All available products to choose from
    
    Returns:
        Suggested companion product dict, or None
    """
    placed_cat = (placed_product.get("category") or "").lower()
    placed_name = (placed_product.get("name") or "").lower()
    
    # ── Determine what kind of companion to suggest ──
    # Large furniture → suggest smaller decor/lighting
    # Decor → suggest complementary decor
    companion_categories = set()
    
    large_indicators = {"sofa", "table", "cabinet", "shelf", "desk", "bed", "chair", "bench"}
    if any(kw in placed_cat or kw in placed_name for kw in large_indicators):
        companion_categories = {"lamp", "vase", "frame", "plant", "candle", "clock", "sculpture"}
    else:
        companion_categories = {"lamp", "plant", "frame", "tray", "basket"}
    
    # ── Filter candidates ──
    candidates = []
    for p in available_products:
        p_cat = (p.get("category") or "").lower()
        p_name = (p.get("name") or "").lower()
        
        # Must be a different product
        if p.get("id") == placed_product.get("id"):
            continue
        
        # Must be in a companion category
        is_companion = any(kw in p_cat or kw in p_name for kw in companion_categories)
        if not is_companion:
            continue
        
        candidates.append(p)
    
    if not candidates:
        return None
    
    # ── Rank by balance potential ──
    # If the placed product shifted weight left, prefer items that work on the right
    bias_x = visual_com.get("bias_x", 0.0) if visual_com else 0.0
    
    # For now, simply return the first companion candidate
    # In a full implementation, this would use the anchor registry
    # to compute exact placement and ranking
    best = candidates[0]
    print(f"[Ensemble] Suggested companion for '{placed_product.get('name', '?')}': "
          f"'{best.get('name', '?')}' ({best.get('category', '?')})")
    
    return best


# ═══════════════════════════════════════════════════════════════════════════
# 6.3  ADAPTIVE LIGHTING TIME-OF-DAY
# ═══════════════════════════════════════════════════════════════════════════

def classify_time_of_day(light_sources: Optional[dict]) -> dict:
    """
    Classify the room's lighting as Day, Evening, or Transitional
    based on the Kelvin temperature of detected light sources.
    
    Kelvin ranges:
      - >5500K  = Daylight (cool/blue, north-facing windows, overcast)
      - 4000-5500K = Transitional (mixed natural + artificial)
      - <4000K  = Evening (warm incandescent, candles, golden hour)
    
    Args:
        light_sources: Output of detect_light_sources() (may be None)
    
    Returns:
        {
            "period": "day" | "evening" | "transitional",
            "avg_kelvin": int,
            "boost_lighting_products": bool,
            "mood": str,
        }
    """
    if not light_sources or "sources" not in light_sources:
        return {
            "period": "transitional",
            "avg_kelvin": 4500,
            "boost_lighting_products": False,
            "mood": "neutral",
        }
    
    sources = light_sources["sources"]
    if not sources:
        return {
            "period": "transitional",
            "avg_kelvin": 4500,
            "boost_lighting_products": False,
            "mood": "neutral",
        }
    
    # Compute intensity-weighted average Kelvin
    total_weight = sum(s["intensity"] for s in sources)
    if total_weight < 0.001:
        total_weight = 1.0
    
    avg_kelvin = int(
        sum(s["kelvin"] * s["intensity"] for s in sources) / total_weight
    )
    
    if avg_kelvin > 5500:
        period = "day"
        mood = "energetic, bright, productive"
        boost = False
    elif avg_kelvin < 3500:
        period = "evening"
        mood = "warm, intimate, relaxing"
        boost = True
    else:
        period = "transitional"
        mood = "balanced, versatile"
        boost = False
    
    return {
        "period": period,
        "avg_kelvin": avg_kelvin,
        "boost_lighting_products": boost,
        "mood": mood,
    }


def compute_lighting_boost(product: dict, time_of_day: dict) -> float:
    """
    Boost lighting products when the room is in "Evening" mode.
    
    Args:
        product: Product metadata dict
        time_of_day: Output of classify_time_of_day()
    
    Returns:
        Score adjustment (negative = better ranking)
    """
    if not time_of_day.get("boost_lighting_products", False):
        return 0.0
    
    searchable = " ".join([
        (product.get("category") or ""),
        (product.get("name") or ""),
        (product.get("notes") or ""),
    ]).lower()
    
    is_lighting = any(kw in searchable for kw in LIGHTING_KEYWORDS)
    
    if is_lighting:
        return -20.0  # Significant boost (lower score = better)
    
    return 0.0
