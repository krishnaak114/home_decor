"""
Light Probe — Spherical Harmonics for Indoor Scene Illumination

Computes a 9-coefficient (L0-L2) Spherical Harmonics approximation of
a room's lighting environment from a single viewpoint photograph.

Since we only have one 2D photo (not a 360° environment map), we use a
"partial SH estimation" strategy:

  L0 (1 coeff × 3 channels = 3 floats):  Ambient — average room color
  L1 (3 coeffs × 3 channels = 9 floats):  Directional — weighted light direction
  L2 (5 coeffs × 3 channels = 15 floats): Quadratic — light spread/concentration

These 27 floats fully describe the low-frequency lighting of the room.
A product's pixels can be relit by evaluating the SH at its surface normal.

Usage:
    from light_probe import estimate_sh_coefficients, apply_sh_color_grading
    sh = estimate_sh_coefficients(room_bytes, light_sources)
    product_arr = apply_sh_color_grading(product_arr, sh, alpha_mask)
"""

import io
import math
import numpy as np
from PIL import Image
from typing import Dict, Optional, List


# ── Kelvin to Linear RGB Conversion ──────────────────────────────────────────
# Approximate blackbody radiation for common interior Kelvin values.
# Based on Tanner Helland's algorithm (widely used in photography software).

def kelvin_to_rgb(kelvin: int) -> np.ndarray:
    """
    Convert color temperature in Kelvin to normalized RGB [0, 1].
    Valid range: 1000K – 12000K.
    """
    temp = max(1000, min(12000, kelvin)) / 100.0
    
    # Red
    if temp <= 66:
        r = 1.0
    else:
        r = 1.292936 * ((temp - 60) ** -0.1332047592)
        r = max(0.0, min(1.0, r))
    
    # Green
    if temp <= 66:
        g = 0.3900815 * math.log(temp) - 0.6318414
    else:
        g = 1.129891 * ((temp - 60) ** -0.0755148492)
    g = max(0.0, min(1.0, g))
    
    # Blue
    if temp >= 66:
        b = 1.0
    elif temp <= 19:
        b = 0.0
    else:
        b = 0.5432068 * math.log(temp - 10) - 1.19625408
        b = max(0.0, min(1.0, b))
    
    return np.array([r, g, b], dtype=np.float32)


# ── SH Basis Functions (Real, Order 0-2) ─────────────────────────────────────
# These evaluate the 9 real spherical harmonics at a given direction (nx, ny, nz).

def sh_basis(nx: float, ny: float, nz: float) -> np.ndarray:
    """
    Evaluate the 9 real SH basis functions (L0-L2) for direction (nx, ny, nz).
    The direction should be normalized but doesn't need to be unit-length
    (we normalize internally).
    
    Returns: (9,) array of basis function values.
    
    Basis ordering:
      [0] Y_00  — constant (ambient)
      [1] Y_1-1 — y direction
      [2] Y_10  — z direction  
      [3] Y_11  — x direction
      [4] Y_2-2 — xy
      [5] Y_2-1 — yz
      [6] Y_20  — 3z²-1
      [7] Y_21  — xz
      [8] Y_22  — x²-y²
    """
    basis = np.zeros(9, dtype=np.float32)
    
    # L0: constant
    basis[0] = 0.282095  # 1 / (2*sqrt(pi))
    
    # L1: linear (directional)
    basis[1] = 0.488603 * ny   # Y_1-1
    basis[2] = 0.488603 * nz   # Y_10
    basis[3] = 0.488603 * nx   # Y_11
    
    # L2: quadratic
    basis[4] = 1.092548 * nx * ny        # Y_2-2
    basis[5] = 1.092548 * ny * nz        # Y_2-1
    basis[6] = 0.315392 * (3*nz*nz - 1)  # Y_20
    basis[7] = 1.092548 * nx * nz        # Y_21
    basis[8] = 0.546274 * (nx*nx - ny*ny) # Y_22
    
    return basis


# ── SH Coefficient Estimation ────────────────────────────────────────────────

def estimate_sh_coefficients(
    room_bytes: bytes,
    light_sources: Optional[Dict] = None,
) -> np.ndarray:
    """
    Estimate L0-L2 Spherical Harmonics coefficients from a room image
    and detected light sources.
    
    Strategy (single-viewpoint approximation):
      L0: Average room color across the wall region (ambient fill light)
      L1: Directional component from detected specular highlights
      L2: Light concentration/spread from source distribution
    
    Args:
        room_bytes: Raw room image bytes
        light_sources: Output of detect_light_sources() (may be None)
    
    Returns:
        (9, 3) np.ndarray — 9 SH coefficients × 3 RGB channels
        Each coefficient encodes the room's lighting contribution for
        that spherical harmonic basis function.
    """
    sh_coeffs = np.zeros((9, 3), dtype=np.float32)
    
    # ── L0: Ambient (average room illumination) ──
    try:
        img = Image.open(io.BytesIO(room_bytes)).convert("RGB")
        # Sample center 60% of the image (avoid dark borders/furniture)
        w, h = img.size
        crop = img.crop((int(w * 0.2), int(h * 0.1), int(w * 0.8), int(h * 0.6)))
        crop = crop.resize((80, 80), Image.Resampling.BILINEAR)
        arr = np.array(crop, dtype=np.float32) / 255.0
        ambient_rgb = arr.mean(axis=(0, 1))
    except Exception:
        ambient_rgb = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    
    # Y_00 coefficient = ambient color scaled by the SH normalization constant
    sh_coeffs[0] = ambient_rgb / 0.282095  # Undo basis normalization so eval returns ambient
    
    # ── L1 + L2: Directional and Quadratic from light sources ──
    if light_sources and "sources" in light_sources:
        sources = light_sources["sources"]
        
        try:
            img_w, img_h = Image.open(io.BytesIO(room_bytes)).size
        except Exception:
            img_w, img_h = 800, 600
        
        for src in sources:
            # Convert pixel position to normalized direction vector
            # Map image coordinates to a hemisphere:
            #   x: [-1, +1] left to right
            #   y: [-1, +1] top to bottom → negate for "up is positive"
            #   z: assume light comes FROM the scene toward the camera
            nx = (src["x"] / img_w) * 2.0 - 1.0
            ny = -((src["y"] / img_h) * 2.0 - 1.0)  # Flip: top is positive
            nz = 0.5  # Assume light is somewhat toward the viewer
            
            # Normalize
            length = math.sqrt(nx*nx + ny*ny + nz*nz)
            if length > 0.001:
                nx /= length
                ny /= length
                nz /= length
            
            # Light color from Kelvin temperature
            light_rgb = kelvin_to_rgb(src["kelvin"])
            
            # Weight by intensity and area coverage
            weight = src["intensity"] * max(0.1, src.get("area_pct", 1.0))
            light_contribution = light_rgb * weight
            
            # Evaluate SH basis at this light direction and accumulate
            basis = sh_basis(nx, ny, nz)
            for i in range(9):
                sh_coeffs[i] += basis[i] * light_contribution
    
    return sh_coeffs


def evaluate_sh(sh_coeffs: np.ndarray, nx: float, ny: float, nz: float) -> np.ndarray:
    """
    Evaluate the SH lighting at a given surface normal direction.
    
    Args:
        sh_coeffs: (9, 3) SH coefficients
        nx, ny, nz: Surface normal direction (will be normalized)
    
    Returns:
        (3,) RGB color — the irradiance at this surface orientation
    """
    basis = sh_basis(nx, ny, nz)
    # Dot product of basis with coefficients for each channel
    color = np.zeros(3, dtype=np.float32)
    for i in range(9):
        color += basis[i] * sh_coeffs[i]
    
    return np.clip(color, 0, 1)


def apply_sh_color_grading(
    prod_arr: np.ndarray,
    sh_coeffs: np.ndarray,
    alpha_mask: np.ndarray,
    blend_strength: float = 0.35,
) -> np.ndarray:
    """
    Apply SH-based color grading to a product image.
    
    Since catalogue products are 2D (no surface normals), we approximate:
      - Front face: normal = (0, 0, 1) — receives full SH evaluation
      - Edges: detected from alpha gradient, treated as curved away from viewer
      - Top: slight upward bias for overhead light reception
    
    This replaces flat brightness ratio matching with physically-motivated
    color grading that accounts for light direction and color temperature.
    
    Args:
        prod_arr: HxWx4 uint8 RGBA product array (modified in-place)
        sh_coeffs: (9, 3) SH coefficients from estimate_sh_coefficients()
        alpha_mask: HxW boolean mask of opaque pixels
        blend_strength: 0.0 (no effect) to 1.0 (full replacement)
    
    Returns:
        Modified prod_arr
    """
    if alpha_mask.sum() < 50:
        return prod_arr
    
    h, w = prod_arr.shape[:2]
    
    # Evaluate SH at the front-facing normal (0, 0, 1) — the default for 2D images
    front_color = evaluate_sh(sh_coeffs, 0.0, 0.0, 1.0)
    
    # Evaluate SH at a slight upward bias (0, 0.3, 0.95) — products receive some top light
    top_bias_color = evaluate_sh(sh_coeffs, 0.0, 0.3, 0.95)
    
    # Blend between front and top-biased based on vertical position
    # Top of product receives more overhead light, bottom receives more front light
    y_coords = np.linspace(0, 1, h)
    
    # Work on opaque pixels only
    rgb = prod_arr[:, :, :3].astype(np.float32) / 255.0
    
    for y in range(h):
        # Vertical blend: top rows get more overhead SH, bottom rows get more front SH
        t = y_coords[y]
        sh_color = front_color * (0.6 + 0.4 * t) + top_bias_color * (0.4 - 0.4 * t)
        
        # Row mask
        row_mask = alpha_mask[y]
        if not row_mask.any():
            continue
        
        # Apply: blend between original product color and SH-tinted color
        # SH color acts as a multiplier (like environment lighting)
        original = rgb[y, row_mask]
        tinted = original * sh_color[np.newaxis, :]
        rgb[y, row_mask] = original * (1.0 - blend_strength) + tinted * blend_strength
    
    prod_arr[:, :, :3] = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    return prod_arr
