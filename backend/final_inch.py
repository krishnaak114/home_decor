"""
Final Inch — Perceptual Nuance Effects for Photorealistic Compositing

These effects eliminate the last visual gaps between composited product
images and the room background:

  1. Adaptive Noise Injection:  Match room grain to studio-clean products
  2. Edge-Light Wrap:           Bleed room light onto product borders
  3. Fresnel Reflection:        Environment map overlay for glossy surfaces

All effects operate on the product RGBA array BEFORE final compositing,
preserving the alpha channel and operating only on opaque pixels.
"""

import io
import numpy as np
from PIL import Image, ImageFilter
from typing import Optional


# ── Glossy Material Keywords ──────────────────────────────────────────────
GLOSSY_MATERIALS = {
    "glass", "crystal", "chrome", "steel", "metal", "brass", "copper",
    "gold", "silver", "mirror", "lacquer", "gloss", "polished",
    "marble", "granite", "ceramic", "porcelain", "patent", "acrylic",
    "resin", "enamel", "varnish",
}


# ═══════════════════════════════════════════════════════════════════════════
# 5.1  ADAPTIVE NOISE INJECTION
# ═══════════════════════════════════════════════════════════════════════════

def estimate_room_noise(room_bytes: bytes) -> float:
    """
    Estimate the RMS noise level of a room photo.
    
    Strategy:
      1. Convert to grayscale at reduced resolution
      2. Apply a 3x3 Laplacian kernel (isolates high-frequency noise)
      3. Compute the standard deviation of the Laplacian response
      4. Normalize to a 0–1 scale where 0=studio-clean, 1=very grainy
    
    Returns:
        Float 0.0–1.0 representing the room's noise level.
    """
    import cv2
    
    try:
        img = Image.open(io.BytesIO(room_bytes)).convert("L")  # Grayscale
        # Work at reduced resolution (noise estimation doesn't need full res)
        w = min(300, img.width)
        h = int(img.height * (w / img.width))
        img = img.resize((w, h), Image.Resampling.BILINEAR)
        arr = np.array(img, dtype=np.float32)
        
        # Laplacian: detects edges AND noise (high-frequency content)
        laplacian = cv2.Laplacian(arr, cv2.CV_32F, ksize=3)
        noise_sigma = float(laplacian.std())
        
        # Normalize: typical room photos have sigma 5–30
        # Studio clean = ~5, mobile phone in low light = ~25+
        normalized = max(0.0, min(1.0, (noise_sigma - 3.0) / 25.0))
        return round(normalized, 3)
    except Exception:
        return 0.05  # Default: assume fairly clean


def inject_adaptive_noise(
    prod_arr: np.ndarray,
    alpha_mask: np.ndarray,
    room_noise_level: float,
    intensity_scale: float = 0.7,
) -> np.ndarray:
    """
    Inject Gaussian noise into the product image to match the room's grain.
    
    A studio-quality product on a slightly grainy mobile photo is a dead
    giveaway that the image is composited. This bridges the quality gap.
    
    Args:
        prod_arr: HxWx4 uint8 RGBA product array (modified in-place)
        alpha_mask: HxW boolean mask of opaque pixels
        room_noise_level: 0.0–1.0 from estimate_room_noise()
        intensity_scale: How aggressively to match noise (0.7 = 70% of room noise)
    
    Returns:
        Modified prod_arr with matched noise.
    """
    if room_noise_level < 0.02:
        return prod_arr  # Room is studio-clean too, skip
    
    h, w = prod_arr.shape[:2]
    
    # Generate Gaussian noise scaled to the room's noise level
    # Room noise 0.0–1.0 maps to pixel sigma 0–12
    sigma = room_noise_level * intensity_scale * 12.0
    
    if sigma < 0.5:
        return prod_arr
    
    noise = np.random.normal(0, sigma, (h, w, 3)).astype(np.float32)
    
    # Apply noise only to opaque pixels
    rgb = prod_arr[:, :, :3].astype(np.float32)
    rgb[alpha_mask] += noise[alpha_mask]
    prod_arr[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    
    return prod_arr


# ═══════════════════════════════════════════════════════════════════════════
# 5.2  EDGE-LIGHT WRAP
# ═══════════════════════════════════════════════════════════════════════════

def apply_light_wrap(
    prod_arr: np.ndarray,
    room_arr: np.ndarray,
    paste_x: int,
    paste_y: int,
    wrap_radius: int = 3,
    brightness_threshold: float = 0.7,
    wrap_opacity: float = 0.4,
) -> np.ndarray:
    """
    Bleed bright room light onto the edges of the product.
    
    When a bright window or lamp is behind an object, light naturally
    "wraps" around the object's edges. This effect creates a subtle
    inner glow using the actual room colors at the product border.
    
    Pipeline:
      1. Extract the room region behind the product
      2. Find bright pixels (above brightness_threshold)
      3. Detect the product edge pixels (alpha gradient)
      4. Where bright room pixels meet product edges, blend room color
         inward by wrap_radius pixels
    
    Args:
        prod_arr: HxWx4 uint8 RGBA product array (modified in-place)
        room_arr: HxWx3 uint8 room image array
        paste_x, paste_y: Where the product sits in room coordinates
        wrap_radius: Pixel depth of the light wrap effect (2-4 px)
        brightness_threshold: 0.0–1.0, how bright a room pixel must be to wrap
        wrap_opacity: Strength of the wrap blend (0.0–1.0)
    
    Returns:
        Modified prod_arr with light wrap applied at edges.
    """
    import cv2
    
    ph, pw = prod_arr.shape[:2]
    room_h, room_w = room_arr.shape[:2]
    alpha = prod_arr[:, :, 3]
    
    # Create the product edge mask: pixels where alpha transitions from opaque to transparent
    alpha_float = alpha.astype(np.float32) / 255.0
    # Erode alpha to find inner edge
    kernel = np.ones((3, 3), np.uint8)
    alpha_uint8 = (alpha_float * 255).astype(np.uint8)
    eroded = cv2.erode(alpha_uint8, kernel, iterations=wrap_radius)
    edge_mask = (alpha_uint8 > 30) & (eroded < 200)  # Inner edge band
    
    if edge_mask.sum() < 10:
        return prod_arr  # No significant edges
    
    # Extract the room region behind the product
    ry1 = max(0, paste_y)
    ry2 = min(room_h, paste_y + ph)
    rx1 = max(0, paste_x)
    rx2 = min(room_w, paste_x + pw)
    
    # Map to product-local coordinates
    ly1 = ry1 - paste_y
    ly2 = ly1 + (ry2 - ry1)
    lx1 = rx1 - paste_x
    lx2 = lx1 + (rx2 - rx1)
    
    if ly2 <= ly1 or lx2 <= lx1:
        return prod_arr
    
    room_behind = room_arr[ry1:ry2, rx1:rx2, :3].astype(np.float32) / 255.0
    
    # Find bright room pixels
    room_brightness = room_behind.mean(axis=2)
    bright_mask = room_brightness > brightness_threshold
    
    # Combine: edge pixels that are adjacent to bright room pixels
    # Dilate the bright mask slightly to catch nearby edges
    bright_uint8 = (bright_mask.astype(np.uint8) * 255)
    bright_dilated = cv2.dilate(bright_uint8, kernel, iterations=wrap_radius)
    bright_zone = bright_dilated > 128
    
    # Crop edge_mask to the overlap region
    edge_region = edge_mask[ly1:ly2, lx1:lx2]
    wrap_zone = edge_region & bright_zone[:edge_region.shape[0], :edge_region.shape[1]]
    
    if wrap_zone.sum() < 5:
        return prod_arr
    
    # Apply the wrap: blend room color onto product edge pixels
    prod_rgb = prod_arr[ly1:ly2, lx1:lx2, :3].astype(np.float32) / 255.0
    room_rgb = room_behind[:wrap_zone.shape[0], :wrap_zone.shape[1]]
    
    # Blend with distance-based falloff (closer to edge = stronger wrap)
    prod_rgb[wrap_zone] = (
        prod_rgb[wrap_zone] * (1.0 - wrap_opacity) +
        room_rgb[wrap_zone] * wrap_opacity
    )
    
    prod_arr[ly1:ly2, lx1:lx2, :3] = np.clip(prod_rgb * 255, 0, 255).astype(np.uint8)
    
    return prod_arr


# ═══════════════════════════════════════════════════════════════════════════
# 5.3  FRESNEL REFLECTION OVERLAY
# ═══════════════════════════════════════════════════════════════════════════

def apply_fresnel_reflection(
    prod_arr: np.ndarray,
    alpha_mask: np.ndarray,
    room_bytes: bytes,
    product_metadata: dict,
    reflection_opacity: float = 0.05,
) -> np.ndarray:
    """
    Apply an environmental reflection overlay to glossy product surfaces.
    
    The Fresnel effect: reflections are stronger at grazing angles (edges)
    and weaker at face-on angles (center). This function:
    
      1. Checks if the product is glossy (glass, chrome, marble, etc.)
      2. Computes a Fresnel mask (brighter at edges, darker at center)
      3. Blends a blurred, low-opacity version of the room's average
         color onto the product through the Fresnel mask
    
    This makes furniture look like it's actually IN the room's light,
    rather than photoshopped onto it.
    
    Args:
        prod_arr: HxWx4 uint8 RGBA product array (modified in-place)
        alpha_mask: HxW boolean mask of opaque pixels
        room_bytes: Raw room image bytes (for average color extraction)
        product_metadata: Product metadata dict (for material detection)
        reflection_opacity: Max opacity of the reflection (0.05 = 5%)
    
    Returns:
        Modified prod_arr with Fresnel reflection.
    """
    import cv2
    
    # Check if the product is glossy
    searchable = " ".join([
        (product_metadata.get("material") or ""),
        (product_metadata.get("Material") or ""),
        (product_metadata.get("name") or ""),
        (product_metadata.get("notes") or ""),
    ]).lower()
    
    is_glossy = any(kw in searchable for kw in GLOSSY_MATERIALS)
    if not is_glossy:
        return prod_arr  # Matte/fabric products don't reflect
    
    if alpha_mask.sum() < 100:
        return prod_arr
    
    h, w = prod_arr.shape[:2]
    
    # ── Step 1: Extract room's average color (the "environment") ──
    try:
        room_img = Image.open(io.BytesIO(room_bytes)).convert("RGB")
        room_small = room_img.resize((16, 16), Image.Resampling.BILINEAR)
        env_color = np.array(room_small, dtype=np.float32).mean(axis=(0, 1))
        # Boost slightly for reflection (reflections pick up highlights)
        env_color = np.clip(env_color * 1.1, 0, 255)
    except Exception:
        env_color = np.array([180, 180, 180], dtype=np.float32)
    
    # ── Step 2: Generate Fresnel mask ──
    # Fresnel: strongest at edges (where surface curves away from viewer)
    # Approximate by using distance from alpha centroid
    y_coords, x_coords = np.where(alpha_mask)
    if len(y_coords) == 0:
        return prod_arr
    
    center_y = y_coords.mean()
    center_x = x_coords.mean()
    
    # Compute normalized distance from center for all opaque pixels
    # Max distance = half diagonal of bounding box
    bbox_h = y_coords.max() - y_coords.min()
    bbox_w = x_coords.max() - x_coords.min()
    max_dist = max(1.0, np.sqrt(bbox_h**2 + bbox_w**2) * 0.5)
    
    fresnel_map = np.zeros((h, w), dtype=np.float32)
    dist_y = (y_coords - center_y) / max_dist
    dist_x = (x_coords - center_x) / max_dist
    distances = np.sqrt(dist_y**2 + dist_x**2)
    
    # Fresnel: ramp up at edges (distance > 0.5)
    # Schlick's approximation: F = F0 + (1-F0)(1-cos_theta)^5
    # Simplified for 2D: use distance as proxy for grazing angle
    fresnel_values = np.clip(distances * 1.5 - 0.3, 0, 1) ** 2
    fresnel_map[y_coords, x_coords] = fresnel_values
    
    # Smooth the Fresnel mask
    fresnel_map = cv2.GaussianBlur(fresnel_map, (7, 7), 0)
    
    # ── Step 3: Apply environmental reflection ──
    rgb = prod_arr[:, :, :3].astype(np.float32)
    
    for c in range(3):
        channel = rgb[:, :, c]
        # Blend: product pixel + env_color * fresnel * opacity
        reflection = env_color[c] * fresnel_map * reflection_opacity
        channel[alpha_mask] += reflection[alpha_mask]
        rgb[:, :, c] = channel
    
    prod_arr[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    
    return prod_arr
