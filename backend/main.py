from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path
from typing import Optional, List
import json
import urllib.parse
import os
import io
import re
import numpy as np
from uuid import uuid4
from PIL import Image, ImageFilter
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PRODUCTS_DIR = PROJECT_ROOT / 'Products'
PUBLIC_DIR = BASE_DIR / 'public'
UPLOAD_DIR = PUBLIC_DIR / 'uploads'
BASE_IMAGE_URL = 'http://localhost:8000'

# Gemini API is handled in vision_agent.py via GEMINI_API_KEY env var

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Global CLIP model (loaded once at startup) ──
_clip_model = None
def get_clip_model():
    global _clip_model
    if _clip_model is None:
        from sentence_transformers import SentenceTransformer
        _clip_model = SentenceTransformer("clip-ViT-B-32")
    return _clip_model

app = FastAPI(title="Home Decor AI", version="1.0.0", description="AI-powered home decor design platform")

# Serve static files (product images and user uploads)
if (PUBLIC_DIR / "images").exists():
    app.mount("/images", StaticFiles(directory=PUBLIC_DIR / "images"), name="images")
if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
if PRODUCTS_DIR.exists():
    app.mount("/images_vault", StaticFiles(directory=PRODUCTS_DIR), name="images_vault")


def build_image_url(image_path: str) -> str:
    if not image_path:
        return ''
    if image_path.startswith('http://') or image_path.startswith('https://'):
        return image_path
    encoded_path = urllib.parse.quote(image_path, safe='/')
    return f"{BASE_IMAGE_URL}{encoded_path}"


def _safe_public_file_path(url_path: str) -> Optional[Path]:
    """
    Convert a URL path like '/images/vendor/file.png' to a safe filesystem path under PUBLIC_DIR.
    Prevents path traversal and returns None if outside public dir.
    """
    if not url_path:
        return None
    # drop scheme/host if mistakenly provided
    parsed = urllib.parse.urlparse(url_path)
    path = parsed.path if parsed.scheme else url_path
    path = urllib.parse.unquote(path)
    # Map URL prefix to physical directory
    if path.startswith("/images_vault/"):
        rel = path.replace("/images_vault/", "", 1)
        candidate = (PRODUCTS_DIR / rel).resolve()
        # Verify it's actually inside the Products dir
        if str(candidate).startswith(str(PRODUCTS_DIR.resolve())):
            return candidate
        return None
        
    rel = path.lstrip("/")
    candidate = (PUBLIC_DIR / rel).resolve()
    public_root = PUBLIC_DIR.resolve()
    try:
        candidate.relative_to(public_root)
    except Exception:
        return None
    return candidate


def _find_perspective_coeffs(source_coords, target_coords):
    """
    Calculate perspective transform coefficients for PIL.Image.transform.
    Maps source quadrilateral to target quadrilateral.
    """
    import numpy as np
    matrix = []
    for s, t in zip(source_coords, target_coords):
        matrix.append([t[0], t[1], 1, 0, 0, 0, -s[0]*t[0], -s[0]*t[1]])
        matrix.append([0, 0, 0, t[0], t[1], 1, -s[1]*t[0], -s[1]*t[1]])
    A = np.matrix(matrix, dtype=float)
    B = np.array([coord for pair in source_coords for coord in pair]).reshape(8)
    try:
        res = np.dot(np.linalg.inv(A.T * A) * A.T, B)
        return np.array(res).reshape(8).tolist()
    except np.linalg.LinAlgError:
        print("[Warning] Singular matrix in perspective transform. Falling back to identity.")
        return [1, 0, 0, 0, 1, 0, 0, 0]


def _classify_product(product: dict) -> dict:
    """
    Smart product classifier: analyzes name, category, size, and notes
    to determine placement type and real-world dimensions.
    
    Returns: {type, placement, real_width_cm, real_height_cm}
    Types: wall_cover, wall_hang, floor_large, ceiling, surface_small
    """
    cat = (product.get("category") or "").lower()
    name = (product.get("name") or "").lower()
    notes = (product.get("Notes") or product.get("notes") or "").lower()
    size_str = product.get("Size") or product.get("size") or ""
    
    # Parse real dimensions from size string (e.g. "66.7L x 66.8B x 78.6H")
    dims = re.findall(r"([\d.]+)", str(size_str))
    dims_float = [float(d) for d in dims if float(d) > 0] if dims else []
    
    # --- Classification rules (most specific first) ---
    
    # WALL COVERINGS: wallpaper, wall panels
    if cat in ["wallpaper"] or "wallpaper" in name:
        return {"type": "wall_cover", "placement": "wall", "real_width_cm": 200, "real_height_cm": 250}
    if "wall panel" in cat or "adhesive" in cat or "panel" in name:
        return {"type": "wall_cover", "placement": "wall", "real_width_cm": 120, "real_height_cm": 120}
    
    # CEILING: pendant lights, chandeliers
    if any(t in name for t in ["pendant", "chandelier", "hanging light", "ceiling"]):
        w = dims_float[0] if dims_float else 40
        return {"type": "ceiling", "placement": "ceiling", "real_width_cm": w, "real_height_cm": w * 1.5}
    if cat == "lighting" and any(t in name for t in ["cluster", "drop", "suspend"]):
        w = dims_float[0] if dims_float else 40
        return {"type": "ceiling", "placement": "ceiling", "real_width_cm": w, "real_height_cm": w * 1.5}
    
    # WALL HANGINGS: wall art, clocks, mirrors, hooks, frames
    if cat in ["wallart", "wall hooks"]:
        w = dims_float[0] if dims_float else 40
        return {"type": "wall_hang", "placement": "wall", "real_width_cm": w, "real_height_cm": w}
    if any(t in name for t in ["wall art", "wall hook", "frame", "canvas", "painting", "mirror", "clock"]):
        w = dims_float[0] if dims_float else 40
        return {"type": "wall_hang", "placement": "wall", "real_width_cm": w, "real_height_cm": w}
    if "wall" in name and cat == "atrang":
        w = dims_float[0] if dims_float else 25
        return {"type": "wall_hang", "placement": "wall", "real_width_cm": w, "real_height_cm": w}
    
    # FLOOR LARGE: furniture (sofas, tables, cupboards, beds, chairs, cabinets, dressers)
    if cat in ["bl living", "bl-bedroom", "bl-outdoor", "bl-dining", "meraki"]:
        w = dims_float[0] if dims_float else 80
        h = dims_float[2] if len(dims_float) >= 3 else w * 0.8
        return {"type": "floor_large", "placement": "floor", "real_width_cm": w, "real_height_cm": h}
    if any(t in name for t in ["sofa", "table", "cabinet", "cupboard", "bed", "dresser", "chair", "bench", "shelf", "rack", "wardrobe"]):
        w = dims_float[0] if dims_float else 80
        h = dims_float[2] if len(dims_float) >= 3 else w * 0.8
        return {"type": "floor_large", "placement": "floor", "real_width_cm": w, "real_height_cm": h}
    
    # FLOOR MEDIUM: floor lamps, large planters, rugs
    if cat == "lighting" and any(t in name for t in ["floor", "standing", "tripod"]):
        w = dims_float[0] if dims_float else 40
        return {"type": "floor_large", "placement": "floor", "real_width_cm": w, "real_height_cm": w * 3}
    if cat in ["rugscarpet", "blinds, curtains"]:
        return {"type": "wall_cover", "placement": "floor", "real_width_cm": 150, "real_height_cm": 200}
    
    # SURFACE SMALL (default): vases, sculptures, small decor, tabletop items
    # Most ATRANG and GHAR ART items are tabletop decor
    w = dims_float[0] if dims_float else 20
    h = dims_float[2] if len(dims_float) >= 3 else (dims_float[1] if len(dims_float) >= 2 else w * 1.5)
    return {"type": "surface_small", "placement": "surface", "real_width_cm": w, "real_height_cm": h}


def _compose_room_with_product(room_bytes: bytes, product_id: str, wall_length: Optional[float] = None) -> Optional[bytes]:
    """
    Phase 3 AI-powered compositor:
      1. Gemini vision for room analysis
      2. Deterministic surface detection (depth map + edge density)
      3. Dynamic masking around the placed product
      4. Stability AI inpainting to photorealistically blend the product
      5. Mask-preserving blend ensures 100% original room background
      6. Graceful PIL fallback if no Stability API key
    """
    from vision_agent import (
        analyze_room_metadata, 
        generate_drop_shadow, 
        isolate_product_background,
        get_material_weight,
    )
    from vision_agent import _lazy_get_depth_map
    from render_engine import render_product_in_room, save_debug_artifacts
    from surface_detector import (
        detect_room_bounds, detect_floor_region, detect_empty_surfaces,
        get_best_placement_for_type, build_walkable_flow_grid, CLEARANCE_RADII,
        compute_visual_center_of_mass,
    )
    
    collection = get_product_collection()
    if not collection:
        return None
        
    res = collection.get(ids=[product_id])
    if not res or not res["metadatas"]:
        print(f"[Error] Product ID '{product_id}' not found in database.")
        return None
        
    product = res["metadatas"][0]
    product_image_url_or_path = product.get("image_url", "")
    product_path = _safe_public_file_path(product_image_url_or_path)
    
    if not product_path:
        print(f"[Error] Could not resolve public path for: {product_image_url_or_path}")
        return None
        
    if not product_path.exists():
        print(f"[Error] Product image file does not exist: {product_path}")
        return None
        
    print(f"[Compositor] Starting composition for '{product.get('name')}' using {product_path}")
        
    try:
        # ── Step 1: Background Isolation ──
        isolated_bytes = isolate_product_background(product_path)
        prod_img = Image.open(io.BytesIO(isolated_bytes)).convert("RGBA")
        
        # ── Step 2: Room Analysis & Depth Map ──
        metadata = analyze_room_metadata(room_bytes)
        color_temp = metadata.get("color_temperature", "Neutral")
        light_dir = metadata.get("lighting_direction", "overhead")
        surf_mat = metadata.get("surface_material", "Standard")
        room_style = metadata.get("room_style", "modern")

        depth_map = _lazy_get_depth_map(room_bytes)
        
        # Save depth map for debugging
        depth_viz = (depth_map * 255).astype(np.uint8)
        depth_path = UPLOAD_DIR / f"depth_{uuid4().hex[:8]}.png"
        Image.fromarray(depth_viz).save(depth_path)
        
        # ── Step 3: Smart Product Classification ──
        product_type = _classify_product(product)
        ptype = product_type["type"]
        real_w_cm = product_type["real_width_cm"]
        real_h_cm = product_type.get("real_height_cm", real_w_cm)
        print(f"[Compositor] Product type: {ptype} | real_size: {real_w_cm}x{real_h_cm}cm")
        
        with Image.open(io.BytesIO(room_bytes)) as _tmp:
            img_h, img_w = _tmp.height, _tmp.width

        # ── Step 4: Deterministic Surface Detection & Placement ──
        #
        # Step 4a: Detect visible room boundaries and surfaces using the
        # deterministic surface_detector module (no LLM coordinate hallucination)
        
        with Image.open(io.BytesIO(room_bytes)) as room_img:
            room = room_img.convert("RGBA")
            room_arr = np.array(room.convert("RGB"))
            
            # Deterministic room bounds detection (replaces inline brightness scan)
            room_bounds = detect_room_bounds(room_arr)
            room_left = room_bounds["left"]
            room_top = room_bounds["top"]
            room_right = room_bounds["right"]
            room_bottom = room_bounds["bottom"]
            visible_w = room_right - room_left
            visible_h = room_bottom - room_top
            room_cx = room_left + visible_w // 2
            
            bounds_coverage = (visible_w * visible_h) / max(1, img_w * img_h) * 100
            print(f"[Compositor] Image: {img_w}x{img_h}px | Room bounds: ({room_left},{room_top})-({room_right},{room_bottom}) = {visible_w}x{visible_h}px ({bounds_coverage:.0f}% coverage)")
        
            # Deterministic floor detection (multi-column median, replaces single-column scan)
            floor_region = detect_floor_region(depth_map, room_bounds)
            floor_y = floor_region["floor_y"]
            
            # Detect empty surfaces for smarter placement decisions
            empty_surfaces = detect_empty_surfaces(room_bytes, depth_map, room_bounds, floor_y)
            
            # Build walkable flow grid for floor-placed products
            # This enforces ergonomic clearance zones around existing furniture
            walkable_grid = None
            if ptype in ("floor_large", "surface_small"):
                clearance = CLEARANCE_RADII.get(ptype, 20)
                walkable_grid = build_walkable_flow_grid(
                    room_bytes, depth_map, room_bounds, floor_y, clearance_px=clearance
                )
                safe_pct = float(walkable_grid[floor_y:room_bottom, room_left:room_right].mean()) * 100
                print(f"[Compositor] Walkable flow: {safe_pct:.1f}% of floor is safe (clearance={clearance}px)")
            
            # Compute visual equilibrium for balanced placement
            visual_com = compute_visual_center_of_mass(room_bytes, room_bounds)
            balance_bias_x = visual_com["bias_x"]
            print(f"[Compositor] Visual CoM: x={visual_com['cx']:.2f}, skew={visual_com['skew']:.2f}, bias={balance_bias_x:+.2f}")
            
            # Get the best deterministic placement for this product type
            placement_suggestion = get_best_placement_for_type(
                ptype, room_bounds, floor_region, empty_surfaces,
                walkable_grid=walkable_grid,
                balance_bias_x=balance_bias_x,
            )
            print(f"[Compositor] Floor at y={floor_y}, placement suggestion: {placement_suggestion}")
            
            # Step 4c: Product sizing — as % of VISIBLE WALL, not full image
            # Interior designer logic:
            #   - A 10ft (305cm) wall is the reference
            #   - A dining table (120cm) = ~40% of wall = dominant piece
            #   - A side cabinet (80cm) = ~26% of wall = medium piece
            #   - A vase (17cm) = ~6% of wall but MINIMUM 10% for visibility
            assumed_wall_cm = (wall_length * 100) if (wall_length and wall_length > 0) else 305.0
            product_wall_ratio = real_w_cm / assumed_wall_cm
            
            # ── Step 4b: Material-weight-aware shadow generation ──
            mat_weight = get_material_weight(product)
            print(f"[Compositor] Material weight: {mat_weight:.2f} (controls AO intensity)")
            
            # Detect physical light sources from specular highlights
            from vision_agent import detect_light_sources
            light_vec = detect_light_sources(room_bytes)
            if light_vec:
                src_count = len(light_vec.get("sources", []))
                print(f"[Compositor] Light probe: {src_count} source(s), "
                      f"angle={light_vec['angle_deg']:.1f}deg, confidence={light_vec['confidence']:.2f}")
                for i, src in enumerate(light_vec.get("sources", [])):
                    print(f"  Source {i+1}: ({src['x']},{src['y']}) {src['kelvin']}K "
                          f"intensity={src['intensity']:.2f} area={src['area_pct']:.1f}%")
            else:
                print(f"[Compositor] Light probe: no specular highlights, using text fallback")
            
            # Compute Spherical Harmonics coefficients (L0-L2) from light sources
            from light_probe import estimate_sh_coefficients
            sh_coeffs = estimate_sh_coefficients(room_bytes, light_vec)
            # Log SH ambient (L0) as the estimated room color
            ambient_rgb = sh_coeffs[0] * 0.282095  # Undo normalization to get actual color
            print(f"[Compositor] SH L0 ambient: R={ambient_rgb[0]:.2f} G={ambient_rgb[1]:.2f} B={ambient_rgb[2]:.2f}")
            if light_vec:
                # Log dominant directional component (L1)
                l1_mag = float(np.sqrt(sh_coeffs[1:4].sum(axis=1) ** 2).sum())
                print(f"[Compositor] SH L1 directional magnitude: {l1_mag:.3f}")
            
            shadowed_product = generate_drop_shadow(
                prod_img, color_temp, light_dir,
                surface_material=surf_mat,
                material_weight=mat_weight,
                light_vector=light_vec,
            )
            ar = shadowed_product.height / max(1, shadowed_product.width)
            wall_height = floor_y - room_top
            
            # ── PLACEMENT ENGINE v2: Percentage-of-Wall Sizing + Precise Anchoring ──
            # Uses the product's real cm dimensions relative to the assumed wall
            # width (305cm / 10ft default) to derive a proportional size.
            # This is visually correct because the product occupies the same
            # fraction of the photo as it would occupy in a real room.
            
            if ptype == "wall_cover":
                # Wall panels: cover significant wall area, MAINTAIN aspect ratio
                target_w = int(visible_w * 0.55)
                target_h = int(target_w * ar)
                # If too tall, cap and recalculate width
                max_h = int(wall_height * 0.85)
                if target_h > max_h:
                    target_h = max_h
                    target_w = max(1, int(target_h / max(0.1, ar)))
                # Use detected empty wall surface if confident, else center
                px = placement_suggestion["x"] - target_w // 2 if placement_suggestion["confidence"] > 0.6 else room_cx - target_w // 2
                py = room_top + int(wall_height * 0.05)
                
            elif ptype == "wall_hang":
                # Wall art at eye level — typically 20-35% of wall width
                target_w = max(int(visible_w * 0.18), int(visible_w * product_wall_ratio))
                target_w = min(target_w, int(visible_w * 0.40))
                target_h = int(target_w * ar)
                target_h = min(target_h, int(wall_height * 0.45))
                if target_h < int(wall_height * 0.15):
                    target_h = int(wall_height * 0.15)
                    target_w = max(1, int(target_h / max(0.1, ar)))
                # Use detected empty wall if confident, else center
                px = placement_suggestion["x"] - target_w // 2 if placement_suggestion["confidence"] > 0.6 else room_cx - target_w // 2
                eye_y = room_top + int(wall_height * 0.35)
                py = eye_y - target_h // 2
                
            elif ptype == "floor_large":
                # FURNITURE: the hero piece of the room
                # Minimum 30% of wall, up to 55% for large tables/sofas
                target_w = max(int(visible_w * 0.30), int(visible_w * product_wall_ratio * 1.2))
                target_w = min(target_w, int(visible_w * 0.55))
                target_h = int(target_w * ar)
                # Cap height at 55% of wall (a tall wardrobe)
                max_h = int(wall_height * 0.55)
                if target_h > max_h:
                    target_h = max_h
                    target_w = max(1, int(target_h / max(0.1, ar)))
                # Ensure minimum height for short/wide tables
                min_h = int(wall_height * 0.18)
                if target_h < min_h:
                    target_h = min_h
                    target_w = max(1, int(target_h / max(0.1, ar)))
                # Use detected empty floor area if confident, else center
                px = placement_suggestion["x"] - target_w // 2 if placement_suggestion["confidence"] > 0.6 else room_cx - target_w // 2
                py = floor_y - target_h  # Bottom edge sits ON the floor line
                
            elif ptype == "ceiling":
                # Pendant light / chandelier: hangs from ceiling
                target_w = max(int(visible_w * 0.12), int(visible_w * product_wall_ratio))
                target_w = min(target_w, int(visible_w * 0.30))
                target_h = int(target_w * ar)
                target_h = min(target_h, int(wall_height * 0.50))
                px = room_cx - target_w // 2
                py = room_top  # Starts at ceiling
                
            else:
                # SURFACE ITEMS (vases, sculptures, decor):
                # Minimum 10% of wall width so they're always visible
                target_w = max(int(visible_w * 0.10), int(visible_w * product_wall_ratio * 1.5))
                target_w = min(target_w, int(visible_w * 0.22))
                target_h = int(target_w * ar)
                # Height: between 12% and 30% of wall height
                min_h = int(wall_height * 0.12)
                max_h = int(wall_height * 0.30)
                if target_h < min_h:
                    target_h = min_h
                    target_w = max(1, int(target_h / max(0.1, ar)))
                if target_h > max_h:
                    target_h = max_h
                    target_w = max(1, int(target_h / max(0.1, ar)))
                # Use detected empty surface if confident, else offset right
                px = placement_suggestion["x"] - target_w // 2 if placement_suggestion["confidence"] > 0.6 else room_cx + int(visible_w * 0.08)
                py = floor_y - target_h  # Bottom edge sits ON the floor line
            
            # ── Safety clamps (from regression testing) ──
            # Prevent any item from clipping below the image
            if py + target_h > img_h:
                target_h = max(1, img_h - py - 5)
                target_w = max(1, int(target_h / max(0.1, ar)))
            # Prevent negative Y
            if py < 0:
                py = max(0, room_top)
            # Prevent X from going off-screen
            px = max(room_left, min(px, room_right - target_w))
            # Absolute minimum size so items are always visible
            target_w = max(int(visible_w * 0.04), target_w)
            target_h = max(int(wall_height * 0.05), target_h)
            
            # ── Step 4d: Z-Axis Depth Scaling (Gentle) ──
            # For 2D paste compositing, aggressive depth scaling makes products
            # look too small. We only apply a very subtle correction.
            try:
                ref_x = max(0, min(depth_map.shape[1] - 1, room_cx))
                ref_y = max(0, min(depth_map.shape[0] - 1, floor_y))
                ref_depth = float(depth_map[ref_y, ref_x])
                
                place_x = max(0, min(depth_map.shape[1] - 1, px + target_w // 2))
                place_y = max(0, min(depth_map.shape[0] - 1, py + target_h))
                place_depth = float(depth_map[place_y, place_x])
                
                if ref_depth > 0.05:
                    depth_ratio = place_depth / ref_depth
                else:
                    depth_ratio = 1.0
                
                # Very gentle scaling: max 10% shrink for deep placement
                # Wall items: no depth scaling (they sit on the back wall by design)
                if ptype not in ("wall_cover", "wall_hang", "ceiling"):
                    depth_scale = max(0.90, min(1.0, 0.7 + 0.3 * depth_ratio))
                    if abs(depth_scale - 1.0) > 0.03:
                        target_w = int(target_w * depth_scale)
                        target_h = int(target_h * depth_scale)
                        print(f"[Compositor] Z-axis scaling: depth_ratio={depth_ratio:.2f}, scale={depth_scale:.2f} → {target_w}x{target_h}px")
            except Exception:
                pass  # Skip depth scaling if anything fails
            
            # Resize the product
            target_w = max(40, target_w)
            target_h = max(40, target_h)
            shadowed_product = shadowed_product.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            # ── Designer Touch 1: Perspective Correction ──
            # Floor items photographed at 3/4 angle → apply subtle front-facing transform
            if ptype in ("floor_large", "surface_small"):
                try:
                    w, h = shadowed_product.size
                    # Slight perspective: widen the bottom, narrow the top
                    # This makes angled catalogue shots appear more front-on
                    squeeze = int(w * 0.03)  # 3% perspective correction
                    coeffs = _find_perspective_coeffs(
                        [(squeeze, 0), (w - squeeze, 0), (w, h), (0, h)],  # Source (slightly squeezed top)
                        [(0, 0), (w, 0), (w, h), (0, h)]  # Destination (full rectangle)
                    )
                    shadowed_product = shadowed_product.transform(
                        (w, h), Image.Transform.PERSPECTIVE, coeffs,
                        Image.Resampling.BICUBIC
                    )
                except Exception:
                    pass  # Skip if transform fails
            
            # ── Step 4d: SH-Based Room Lighting Match ──
            # Replaces flat brightness ratio + hardcoded ±3 tint with
            # physically-motivated SH color grading from the light probe.
            # IMPORTANT: Only affects opaque pixels — never touches transparency.
            try:
                from light_probe import apply_sh_color_grading
                prod_arr = np.array(shadowed_product.convert("RGBA"))
                alpha_ch = prod_arr[:, :, 3].copy()  # Preserve original alpha
                alpha_mask = alpha_ch > 30
                
                if alpha_mask.sum() > 100:
                    prod_arr = apply_sh_color_grading(
                        prod_arr, sh_coeffs, alpha_mask,
                        blend_strength=0.35,
                    )
                    # Restore original alpha — never modified
                    prod_arr[:, :, 3] = alpha_ch
                    shadowed_product = Image.fromarray(prod_arr, "RGBA")
                    print(f"[Compositor] SH color grading applied (blend=0.35)")
            except Exception:
                pass  # Skip lighting match if it fails
            
            pct_of_wall = target_w / max(1, visible_w) * 100
            print(f"[Compositor] Product sized to {target_w}x{target_h}px ({pct_of_wall:.0f}% of wall), placed at ({px},{py}), floor_y={floor_y} ({floor_y/max(1,img_h)*100:.0f}% down)")
            
            # Final bounds clamping (keep within visible room)
            px = max(room_left, min(room_right - target_w, px))
            py = max(room_top, min(room_bottom - target_h, py))
            
            # ── Step 4e: Depth-Based Occlusion Masking ──
            # If existing room objects are CLOSER to the camera than the product's
            # placement depth, make those product pixels transparent so the product
            # appears to sit BEHIND the foreground object (e.g., a rug behind a table).
            try:
                prod_w, prod_h = shadowed_product.size
                
                # Product's placement depth: sampled at its bottom-center
                prod_depth_x = max(0, min(depth_map.shape[1] - 1, px + prod_w // 2))
                prod_depth_y = max(0, min(depth_map.shape[0] - 1, py + prod_h))
                product_z = float(depth_map[prod_depth_y, prod_depth_x])
                
                # Extract the room's depth values in the product's footprint region
                # Clamp to valid depth map bounds
                dm_y1 = max(0, py)
                dm_y2 = min(depth_map.shape[0], py + prod_h)
                dm_x1 = max(0, px)
                dm_x2 = min(depth_map.shape[1], px + prod_w)
                
                if dm_y2 > dm_y1 and dm_x2 > dm_x1:
                    room_depth_region = depth_map[dm_y1:dm_y2, dm_x1:dm_x2]
                    
                    # Occlusion mask: room pixels that are CLOSER to camera than the product
                    # In our depth map: higher value = closer to camera (1=close, 0=far)
                    # Add a small tolerance (0.03) to avoid flickering at depth boundaries
                    occlusion_mask = room_depth_region > (product_z + 0.03)
                    
                    occluded_count = int(occlusion_mask.sum())
                    total_pixels = occlusion_mask.size
                    
                    if occluded_count > 0 and occluded_count < total_pixels * 0.85:
                        # Apply occlusion: zero out product alpha where room is in front
                        prod_arr = np.array(shadowed_product.convert("RGBA"))
                        
                        # Map the occlusion mask to the product's local coordinates
                        local_y1 = dm_y1 - py
                        local_y2 = local_y1 + (dm_y2 - dm_y1)
                        local_x1 = dm_x1 - px
                        local_x2 = local_x1 + (dm_x2 - dm_x1)
                        
                        # Ensure dimensions match
                        mask_h, mask_w = occlusion_mask.shape
                        if (local_y2 - local_y1 == mask_h and 
                            local_x2 - local_x1 == mask_w and
                            local_y2 <= prod_arr.shape[0] and 
                            local_x2 <= prod_arr.shape[1]):
                            
                            # Zero out alpha channel where room object is in front
                            prod_arr[local_y1:local_y2, local_x1:local_x2, 3][occlusion_mask] = 0
                            shadowed_product = Image.fromarray(prod_arr, "RGBA")
                            
                            occluded_pct = (occluded_count / total_pixels) * 100
                            print(f"[Compositor] Occlusion masking: {occluded_pct:.1f}% of product hidden behind foreground objects (product_z={product_z:.2f})")
            except Exception:
                pass  # Skip occlusion if anything fails
            
            # ── Step 4f: Surface Compression Effect ──
            # If a heavy product is placed on a soft surface (rug, carpet),
            # darken + blur the room pixels underneath to simulate fiber compression.
            if ptype in ("floor_large", "surface_small"):
                try:
                    from vision_agent import apply_surface_compression
                    room_arr_modified = apply_surface_compression(
                        room_arr=room_arr,
                        product_rgba=shadowed_product,
                        paste_x=px,
                        paste_y=py,
                        surface_material=surf_mat,
                        material_weight=mat_weight,
                    )
                    # Update the room image if compression was applied
                    if room_arr_modified is not None:
                        room = Image.fromarray(room_arr_modified).convert("RGBA")
                        print(f"[Compositor] Surface compression applied (weight={mat_weight:.2f}, surface='{surf_mat}')")
                except Exception:
                    pass  # Skip compression if anything fails
            
            # ── Step 4g: Final Inch Effects ──
            # These perceptual nuance effects bridge the quality gap between
            # studio-quality product images and mobile phone room photos.
            
            # 5.1 — Adaptive Noise Injection
            try:
                from final_inch import estimate_room_noise, inject_adaptive_noise
                room_noise = estimate_room_noise(room_bytes)
                if room_noise > 0.02:
                    prod_arr = np.array(shadowed_product.convert("RGBA"))
                    alpha_ch = prod_arr[:, :, 3].copy()
                    alpha_mask = alpha_ch > 30
                    prod_arr = inject_adaptive_noise(prod_arr, alpha_mask, room_noise)
                    prod_arr[:, :, 3] = alpha_ch
                    shadowed_product = Image.fromarray(prod_arr, "RGBA")
                    print(f"[FinalInch] Noise injection: room_noise={room_noise:.3f}")
            except Exception:
                pass
            
            # 5.2 — Edge-Light Wrap
            try:
                from final_inch import apply_light_wrap
                prod_arr = np.array(shadowed_product.convert("RGBA"))
                prod_arr = apply_light_wrap(
                    prod_arr, room_arr, paste_x=px, paste_y=py,
                    wrap_radius=3, brightness_threshold=0.7, wrap_opacity=0.4,
                )
                shadowed_product = Image.fromarray(prod_arr, "RGBA")
                print(f"[FinalInch] Light wrap applied")
            except Exception:
                pass
            
            # 5.3 — Fresnel Reflection Overlay (glossy surfaces only)
            try:
                from final_inch import apply_fresnel_reflection
                prod_arr = np.array(shadowed_product.convert("RGBA"))
                alpha_ch = prod_arr[:, :, 3].copy()
                alpha_mask = alpha_ch > 30
                prod_arr = apply_fresnel_reflection(
                    prod_arr, alpha_mask, room_bytes, product,
                    reflection_opacity=0.05,
                )
                prod_arr[:, :, 3] = alpha_ch
                shadowed_product = Image.fromarray(prod_arr, "RGBA")
            except Exception:
                pass
            
            # ── Step 5: AI Rendering Pipeline ──
            # Sends the room + product to Stability AI for photorealistic blending.
            # Falls back to PIL paste if no API key is configured.
            product_name = product.get("name", "decorative item")
            
            final_image, mask_image, render_method = render_product_in_room(
                room_image=room,
                product_rgba=shadowed_product,
                paste_x=px,
                paste_y=py,
                product_name=product_name,
                room_style=room_style,
                color_temperature=color_temp,
                lighting_direction=light_dir,
                surface_material=surf_mat,
                depth_value=0.5,
            )
            
            # Save mask for debugging/visualization
            save_debug_artifacts(mask_image, UPLOAD_DIR, prefix="render")
            
            print(f"[Compositor] Rendered '{product_name}' via {render_method} "
                  f"at ({px},{py}), type={product_type['type']}")
            
            # ── Step 6: Register in Anchor Registry for multi-product cohesion ──
            try:
                from anchor_registry import AnchorRegistry
                # Use module-level registry so it persists across compositions
                if not hasattr(_compose_room_with_product, "_anchor_registry"):
                    _compose_room_with_product._anchor_registry = AnchorRegistry()
                
                registry = _compose_room_with_product._anchor_registry
                prod_w, prod_h = shadowed_product.size
                registry.register(
                    object_id=product_id,
                    product_type=ptype,
                    bbox=(px, py, px + prod_w, py + prod_h),
                    product_name=product_name,
                    metadata={
                        "material_weight": mat_weight,
                        "depth_z": float(depth_map[
                            min(py + prod_h, depth_map.shape[0] - 1),
                            min(px + prod_w // 2, depth_map.shape[1] - 1)
                        ]),
                    },
                )
                print(registry.get_hierarchy_summary())
            except Exception:
                pass  # Registry is optional
            
            out = io.BytesIO()
            final_image.convert("RGB").save(out, format="JPEG", quality=92, optimize=True)
            return out.getvalue()

    except Exception as e:
        print(f"AI Composition failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def _edge_density_map(rgb: np.ndarray) -> np.ndarray:
    """
    Compute a simple edge magnitude map using finite differences.
    rgb: HxWx3 uint8
    returns: HxW float32 in [0, ~255]
    """
    gray = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)
    dx = np.abs(gray[:, 1:] - gray[:, :-1])
    dy = np.abs(gray[1:, :] - gray[:-1, :])
    edge = np.zeros_like(gray, dtype=np.float32)
    edge[:, :-1] += dx
    edge[:-1, :] += dy
    return edge


def _find_low_edge_box(room_bytes: bytes) -> Optional[dict]:
    """
    Heuristic "wall space" finder: search top ~70% of the image for a rectangle with low edge density.
    Returns dict {x,y,w,h} in pixel coords, or None.
    """
    try:
        with Image.open(io.BytesIO(room_bytes)) as img:
            img = img.convert("RGB")
            # Downscale for speed; keep mapping scale
            orig_w, orig_h = img.size
            work_w = min(640, orig_w)
            scale = work_w / orig_w if orig_w else 1.0
            work_h = int(orig_h * scale)
            work = img.resize((work_w, work_h), Image.Resampling.BILINEAR)
            arr = np.asarray(work, dtype=np.uint8)

        edge = _edge_density_map(arr)
        h, w = edge.shape
        search_h = int(h * 0.7)
        edge = edge[:search_h, :]

        # Candidate box sizes (relative)
        box_ws = [int(w * r) for r in (0.28, 0.34, 0.40)]
        box_hs = [int(search_h * r) for r in (0.20, 0.26, 0.32)]

        best = None
        best_score = None
        step = max(8, int(min(w, search_h) * 0.03))
        for bw in box_ws:
            for bh in box_hs:
                if bw < 40 or bh < 40:
                    continue
                for y in range(10, max(11, search_h - bh - 10), step):
                    for x in range(10, max(11, w - bw - 10), step):
                        patch = edge[y : y + bh, x : x + bw]
                        score = float(patch.mean())
                        if best_score is None or score < best_score:
                            best_score = score
                            best = (x, y, bw, bh)

        if not best:
            return None

        x, y, bw, bh = best
        # Map back to original coordinates
        inv = 1.0 / scale if scale else 1.0
        return {
            "x": int(x * inv),
            "y": int(y * inv),
            "w": int(bw * inv),
            "h": int(bh * inv),
        }
    except Exception:
        return None


def _avg_color_hex(image_bytes: bytes, region: Optional[dict] = None) -> str:
    """
    Average color of an image (or a region {x,y,w,h}).
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            if region:
                x, y, w, h = region["x"], region["y"], region["w"], region["h"]
                x2, y2 = max(x + 1, x + w), max(y + 1, y + h)
                img = img.crop((max(0, x), max(0, y), min(img.size[0], x2), min(img.size[1], y2)))
            img.thumbnail((160, 160))
            arr = np.asarray(img, dtype=np.float32)
        r, g, b = arr[..., 0].mean(), arr[..., 1].mean(), arr[..., 2].mean()
        return f"#{int(r):02X}{int(g):02X}{int(b):02X}"
    except Exception:
        return "#CBD5E1"


def _color_distance(c1: str, c2: str) -> float:
    def _parse(h: str) -> np.ndarray:
        h = h.lstrip("#")
        if len(h) != 6:
            return np.array([200, 200, 200], dtype=np.float32)
        return np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)], dtype=np.float32)
    v1 = _parse(c1)
    v2 = _parse(c2)
    return float(np.linalg.norm(v1 - v2))


def _product_has_transparency(product_path: Path) -> bool:
    try:
        with Image.open(product_path) as img:
            if img.mode in ("RGBA", "LA"):
                alpha = img.getchannel("A")
                # If any pixels are not fully opaque, treat as cutout/transparent-friendly
                return alpha.getextrema()[0] < 255
        return False
    except Exception:
        return False


def _select_top_k_products_for_room(
    room_bytes: bytes,
    k: int = 8,
    placement: str = "wall",
    wall_box: Optional[dict] = None,
    room_metadata: Optional[dict] = None,
) -> List[dict]:
    """
    Ranks products using ChromaDB vector search based on the room's style and features.
    
    Performance: Uses pre-computed metadata (dominant_color_hex, has_transparency)
    stored in ChromaDB during ingestion (master_sync.py) to avoid filesystem I/O
    on every search request.
    """
    room_ref = _avg_color_hex(room_bytes, region=wall_box if placement == "wall" else None)
    
    collection = get_product_collection()
    
    # If no ChromaDB, return empty
    if not collection:
        print("[WARN] ChromaDB collection 'products' not found.")
        return []
        
    # Categories suitable for wall/room display
    deny_any = ["wallpaper", "vinyl", "flooring", "rug", "runner", "carpet", "curtain", "blind", "cusion"]

    # Build a query string describing the room
    query_text = "Modern elegant decor"
    if room_metadata:
        style = room_metadata.get("room_style", "")
        materials = room_metadata.get("surface_material", "")
        # Create a rich query that ChromaDB can actually use
        query_text = f"{style} furniture and decor with {materials} aesthetic"
    
    # Generate rich room descriptor for semantic re-ranking
    room_descriptor = None
    try:
        from rules_engine.semantic_bridge import generate_rich_room_descriptor
        room_descriptor = generate_rich_room_descriptor(room_bytes)
        if room_descriptor:
            print(f"[Search] Rich descriptor: {room_descriptor[:120]}...")
            # Enhance the CLIP query with the first sentence of the descriptor
            # This gives the vector search more semantic context
            first_sentence = room_descriptor.split(".")[0].strip()
            if first_sentence and len(first_sentence) > 20:
                query_text = f"{query_text}. {first_sentence}"
    except Exception:
        pass  # Descriptor is optional, search works without it
        
    # [PATCH] Truncate the final query string to prevent ChromaDB/SentenceTransformer hang
    # If a malicious user submits a 100k character string, the embedding model will peg the CPU
    query_text = query_text[:250].strip()
    
    print(f"--- Searching Database ---")
    print(f"Target Vibe: {query_text}")

    try:
        model = get_clip_model()
        query_embedding = model.encode(query_text).tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k * 10, # Fetch many to allow diversity filtering
            include=["metadatas", "documents", "distances"]
        )
        
        candidates = []
        if results and results["metadatas"] and results["metadatas"][0]:
            print(f"DB Match count: {len(results['metadatas'][0])}")
            for i, meta in enumerate(results["metadatas"][0]):
                p = dict(meta)
                p['id'] = results["ids"][0][i]
                
                # Normalize keys for UI consistency
                p['category'] = p.get('category', 'Decor')
                p['price'] = float(p.get('price', 0) or 0)
                p['Notes'] = p.get('notes', '')
                p['Material'] = p.get('material', '')
                p['Size'] = p.get('size', '')
                
                cat = (p.get("category") or "").lower()
                name = (p.get("name") or "").lower()
                
                # Filter: allow decorative items, deny wallpapers/flooring/textiles
                if any(tok in cat or tok in name for tok in deny_any):
                    continue

                # Verify the image file exists (cheap stat check, no read)
                img_url = p.get("image_url", "")
                product_path = _safe_public_file_path(img_url)
                if not product_path or not product_path.exists():
                    continue

                # ── Visual scoring from PRE-COMPUTED metadata (zero filesystem I/O) ──
                # These fields are computed once during master_sync.py ingestion
                product_color = p.get("dominant_color_hex", "")
                product_has_transp = p.get("has_transparency", "False") == "True"

                # ── HSL Color Contrast Strategist ──
                # Replaces raw RGB distance with design-aware HSL scoring
                # that rewards complementary/analogous/split-comp relationships
                from rules_engine.color_contrast import compute_color_contrast_score
                if product_color:
                    score = compute_color_contrast_score(room_ref, product_color)
                else:
                    # Fallback for products ingested before metadata optimization
                    try:
                        p_bytes = product_path.read_bytes()
                        fallback_color = _avg_color_hex(p_bytes)
                        score = compute_color_contrast_score(room_ref, fallback_color)
                    except Exception:
                        score = 45.0  # Moderate penalty for unreadable images

                if product_has_transp:
                    score -= 35.0
                    
                # Add vector distance to score (smaller is better)
                vector_dist = results["distances"][0][i]
                score += (vector_dist * 50)
                
                # ── Material Harmonics: Design-Aware Ranking ──
                if room_metadata:
                    from rules_engine.harmonics import compute_material_harmony_score
                    harmony_adj = compute_material_harmony_score(
                        room_style=room_metadata.get("room_style", ""),
                        surface_material=room_metadata.get("surface_material", ""),
                        product=p,
                    )
                    score += harmony_adj

                # ── Phase 6: Lifestyle Intelligence ──
                try:
                    from lifestyle_agent import (
                        detect_lifestyle_markers,
                        compute_lifestyle_score_adjustment,
                        classify_time_of_day,
                        compute_lighting_boost
                    )
                    
                    # 6.1: Lifestyle Markers (Pets, Kids, High Traffic)
                    lifestyle_markers = detect_lifestyle_markers(room_bytes)
                    lifestyle_adj = compute_lifestyle_score_adjustment(p, lifestyle_markers)
                    score += lifestyle_adj
                    
                    # 6.3: Adaptive Lighting Time-of-Day
                    from vision_agent import detect_light_sources
                    light_sources = detect_light_sources(room_bytes)
                    time_of_day = classify_time_of_day(light_sources)
                    lighting_boost = compute_lighting_boost(p, time_of_day)
                    score += lighting_boost
                    
                except Exception as e:
                    pass  # Fail gracefully if lifestyle agent isn't available

                candidates.append((score, p))
                    
            candidates.sort(key=lambda x: x[0])
            final_results = []
            seen_cats = set()
            for _, p in candidates:
                c = p.get('category', '').lower()
                if c not in seen_cats:
                    final_results.append(p)
                    seen_cats.add(c)
                if len(final_results) >= k:
                    break
            
            if len(final_results) < k:
                for _, p in candidates:
                    if p not in final_results:
                        final_results.append(p)
                    if len(final_results) >= k:
                        break
            
            # ── LLM Semantic Re-Ranking ──
            # If we have a rich room descriptor and enough candidates,
            # ask Gemini to re-rank by designer judgment.
            if room_descriptor and len(final_results) >= 5:
                try:
                    from rules_engine.semantic_bridge import llm_rerank_products
                    # Pass up to 15 candidates for re-ranking
                    reranked = llm_rerank_products(
                        room_descriptor=room_descriptor,
                        candidates=final_results[:15],
                        top_k=k,
                    )
                    if reranked:
                        final_results = reranked
                        print(f"[Search] LLM re-ranked {len(final_results)} products")
                except Exception:
                    pass  # Re-ranking is optional, original order is preserved
            
            # --- Fallback: If no products passed the filters, try a generic style search ---
            if not final_results and room_metadata:
                print("[INFO] No candidates passed filters. Trying fallback style-only search...")
                fallback_style = room_metadata.get("room_style", "Modern")
                fallback_embedding = get_clip_model().encode(f"{fallback_style} decor").tolist()
                results = collection.query(
                    query_embeddings=[fallback_embedding],
                    n_results=k,
                    include=["metadatas"]
                )
                if results and results["metadatas"] and results["metadatas"][0]:
                    for meta in results["metadatas"][0]:
                        p = dict(meta)
                        p['price'] = float(p.get('price', 0) or 0)
                        final_results.append(p)
            
            return final_results
            
    except Exception as e:
        print(f"[Error] Vector search failed: {e}")
        
    return []


def _fallback_analysis(wall_length: Optional[float], wall_colors: Optional[str], room_description: Optional[str]) -> dict:
    """Fallback analysis used if AI vision fails."""
    style = guess_style(room_description, wall_colors)
    colors = [c.strip() for c in (wall_colors or '').split(',') if c.strip()] or ["#F3F4F6", "#CBD5E1", "#94A3B8"]
    
    # Simple keyword-based recommendations
    keywords = (room_description or '').lower() + ' ' + (wall_colors or '').lower()
    recommended_ids = []
    
    # No longer using static product_catalog fallback
    
    return {
        "style": style,
        "colors": colors,
        "recommended_ids": recommended_ids,
        "analysis": "AI room analysis unavailable. Showing curated recommendations."
    }


def guess_style(description: Optional[str], wall_colors: Optional[str]) -> str:
    text = f"{description or ''} {wall_colors or ''}".lower()
    if 'modern' in text or 'minimal' in text or 'contemporary' in text:
        return 'Modern Minimal'
    if 'classic' in text or 'traditional' in text or 'vintage' in text:
        return 'Classic Comfort'
    if 'boho' in text or 'bohemian' in text:
        return 'Bohemian Chic'
    if 'industrial' in text or 'warehouse' in text or 'metal' in text:
        return 'Industrial Loft'
    if 'scandi' in text or 'scandinavian' in text or 'mid-century' in text:
        return 'Scandinavian Calm'
    return 'Contemporary Living'


def _image_bytes_to_jpeg_bytes(image_bytes: bytes) -> bytes:
    """
    Normalize arbitrary uploads to JPEG bytes.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=90, optimize=True)
            return out.getvalue()
    except Exception:
        return image_bytes


def _extract_first_json_object(text: str) -> Optional[dict]:
    """
    Extract the first JSON object from a model response.
    """
    if not text:
        return None
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _dominant_colors_hex(image_bytes: bytes, limit: int = 5) -> List[str]:
    """
    Extract dominant colors from an image locally.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail((160, 160))
            q = img.quantize(colors=24, method=2)
            palette = q.getpalette()
            color_counts = q.getcolors() or []
            color_counts.sort(reverse=True, key=lambda x: x[0])
            hexes: List[str] = []
            for count, idx in color_counts:
                base = idx * 3
                r, g, b = palette[base : base + 3]
                hx = f"#{r:02X}{g:02X}{b:02X}"
                if hx not in hexes:
                    hexes.append(hx)
                if len(hexes) >= limit:
                    break
            return hexes or ["#F3F4F6", "#CBD5E1", "#94A3B8"]
    except Exception:
        return ["#F3F4F6", "#CBD5E1", "#94A3B8"]

import chromadb
from chromadb.utils import embedding_functions

# Initialize ChromaDB client
DB_DIR = BASE_DIR / 'chroma_db'
chroma_client = chromadb.PersistentClient(path=str(DB_DIR))
# Use consistent embedding function (CLIP for multimodal support)
# Note: Since master_sync manually computes fused embeddings, we should use 
# a compatible text embedding here for text-only queries.
# However, for simply fetching the collection metadata, the most important part 
# is having the same collection name and space.
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="clip-ViT-B-32")

# We'll fetch the collection dynamically in endpoints to avoid issues if it doesn't exist yet
def get_product_collection():
    try:
        # We get the collection without specifying the embedding function here
        # to avoid conflicts with the persisted 'default' function.
        # Queries that need specific embeddings (like CLIP) will handle it locally.
        return chroma_client.get_collection(name="products")
    except Exception:
        return None

# Vector database is our primary catalog source

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Home Decor AI POC Backend"}

@app.get("/api/catalogue")
async def get_catalogue():
    """Fetch all products from ChromaDB grouped by their original Excel categories."""
    collection = get_product_collection()
    if not collection:
        # Fallback if DB is empty
        return {"categories": {}}
    
    # Get all products (limit 1000)
    results = collection.get(limit=1000)
    
    catalog = {}
    for i in range(len(results["ids"])):
        meta = results["metadatas"][i]
        cat = meta.get("category", "Other")
        
        if cat not in catalog:
            catalog[cat] = []
            
        catalog[cat].append({
            "id": results["ids"][i],
            "name": meta.get("name", "Unknown Item"),
            "price": float(meta.get("price", 0) or 0),
            "image_url": meta.get("image_url", ""),
            "category": cat,
            "metadata": meta
        })
    
    return {"categories": catalog}


# ── Style Profiles ─────────────────────────────────────────────────────────────
STYLE_PROFILES_FILE = BASE_DIR / "data" / "style_profiles.json"
STYLE_PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)

def _load_profiles() -> dict:
    if STYLE_PROFILES_FILE.exists():
        try:
            return json.loads(STYLE_PROFILES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_profiles(profiles: dict):
    STYLE_PROFILES_FILE.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")


@app.get("/api/style-profile/{user_id}")
async def get_style_profile(user_id: str):
    """Return the saved Style Profile for a given user_id."""
    profiles = _load_profiles()
    profile = profiles.get(user_id)
    if not profile:
        return {"user_id": user_id, "profile": None}
    return {"user_id": user_id, "profile": profile}


@app.post("/api/style-profile/{user_id}")
async def save_style_profile(user_id: str, payload: dict):
    """
    Persist a Style Profile for a user.
    Expected payload keys (all optional):
      preferred_styles: list[str]   e.g. ["Modern", "Bohemian"]
      preferred_rooms:  list[str]   e.g. ["Living Room", "Bedroom"]
      preferred_colors: list[str]   e.g. ["#F3F4F6", "#7c5cfc"]
      liked_product_ids: list[str]  product IDs the user liked
      budget_range:     [min, max]  e.g. [5000, 50000]
      updated_at:       str         ISO timestamp (set by client)
    """
    profiles = _load_profiles()
    existing = profiles.get(user_id, {})
    existing.update(payload)
    profiles[user_id] = existing
    _save_profiles(profiles)
    return {"user_id": user_id, "profile": existing, "status": "saved"}


# ── Similar Products (CLIP vector similarity) ─────────────────────────────────
@app.get("/api/products/similar/{product_id}")
async def get_similar_products(product_id: str, limit: int = 6):
    """
    Return the `limit` most similar products to `product_id` using
    CLIP multimodal vector similarity stored in ChromaDB.
    """
    collection = get_product_collection()
    if not collection:
        return {"similar": []}

    try:
        # Fetch the source product's embedding via its document text
        src = collection.get(ids=[product_id], include=["documents", "metadatas"])
        if not src["ids"]:
            return {"similar": [], "error": "Product not found"}

        src_doc = src["documents"][0]
        src_meta = src["metadatas"][0]

        # Since the collection doesn't have a CLIP embedding function assigned,
        # we manually compute the query embedding using our model.
        model = get_clip_model()
        query_embedding = model.encode(src_doc).tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit + 1,
            include=["metadatas", "distances"]
        )

        similar = []
        for i, meta in enumerate(results["metadatas"][0]):
            if meta.get("id") == product_id:
                continue  # skip self
            similar.append({
                "id": meta.get("id"),
                "name": meta.get("name", ""),
                "price": float(meta.get("price", 0) or 0),
                "image_url": meta.get("image_url", ""),
                "category": meta.get("category", ""),
                "similarity_score": round(1 - float(results["distances"][0][i]), 3),
                "metadata": meta,
            })
            if len(similar) >= limit:
                break

        return {
            "product_id": product_id,
            "product_name": src_meta.get("name", ""),
            "similar": similar
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"similar": [], "error": str(e)}


@app.post("/api/design/generate")
async def generate_design(
    room_photo: UploadFile = File(...),
    wall_length: Optional[float] = None,
    wall_colors: Optional[str] = None,
    room_description: Optional[str] = None,
    selected_products: Optional[str] = Form(None)
):
    """
    Upload room photo → Gemini Vision analyzes style/lighting → ranks products → composes preview.
    """
    
    # Save uploaded room photo
    uploaded_bytes = await room_photo.read()
    upload_suffix = Path(room_photo.filename).suffix or '.jpg'
    upload_name = f"{uuid4().hex}{upload_suffix}"
    upload_path = UPLOAD_DIR / upload_name
    upload_path.write_bytes(uploaded_bytes)
    original_room_image_url = build_image_url(f"/uploads/{upload_name}")
    
    # Use Gemini Vision for real AI room analysis (style, colors, lighting)
    # Falls back to heuristic if Gemini is unavailable
    try:
        from vision_agent import analyze_room_metadata
        room_metadata = analyze_room_metadata(uploaded_bytes)
        
        # Build rich analysis from Gemini's output
        gemini_style = room_metadata.get("room_style", "Contemporary Living")
        gemini_temp = room_metadata.get("color_temperature", "Neutral")
        gemini_light = room_metadata.get("lighting_direction", "Natural")
        gemini_surface = room_metadata.get("surface_material", "Standard")
        
        # Extract colors from the image locally (Gemini gives us style, not hex codes)
        gemini_colors = _dominant_colors_hex(uploaded_bytes, limit=5)
        
        analysis = {
            "style": gemini_style,
            "colors": gemini_colors[:3] if gemini_colors else ["#F3F4F6", "#CBD5E1", "#94A3B8"],
            "analysis": f"{gemini_style} room with {gemini_temp.lower()} tones and {gemini_light.lower()} lighting. Surface: {gemini_surface}.",
            "recommended_ids": [],
            "room_metadata": room_metadata,
        }
        print(f"[OK] Gemini room analysis: {gemini_style}, {gemini_temp}, {gemini_light}")
    except Exception as e:
        print(f"[WARN] Gemini analysis failed ({e}), using heuristic fallback")
        analysis = _fallback_analysis(wall_length, wall_colors, room_description)
    wall_box = _find_low_edge_box(uploaded_bytes)

    ranked = _select_top_k_products_for_room(
        uploaded_bytes,
        k=8,
        placement="wall",
        wall_box=wall_box,
        room_metadata=analysis.get("room_metadata")
    )
    suggested_products = ranked[:5]
    
    # ── Phase 6.2: Dynamic Ensemble Generator ──
    # If we have a primary product recommendation, suggest a secondary
    # "Shop the Look" item that visually balances the room.
    try:
        if suggested_products:
            from surface_detector import detect_room_bounds, compute_visual_center_of_mass
            with Image.open(io.BytesIO(uploaded_bytes)) as img:
                arr = np.array(img.convert("RGB"))
                bounds = detect_room_bounds(arr)
            visual_com = compute_visual_center_of_mass(uploaded_bytes, bounds)
            
            from lifestyle_agent import generate_ensemble_suggestion
            companion = generate_ensemble_suggestion(
                placed_product=suggested_products[0],
                room_metadata=analysis.get("room_metadata", {}),
                visual_com=visual_com,
                available_products=ranked[5:], # Exclude already suggested items
            )
            if companion:
                # Add to the end of the suggested list
                suggested_products.append(companion)
                # Ensure it's unique
                seen_ids = set()
                deduped = []
                for p in suggested_products:
                    if p["id"] not in seen_ids:
                        deduped.append(p)
                        seen_ids.add(p["id"])
                suggested_products = deduped
    except Exception as e:
        print(f"[Ensemble] Generator failed: {e}")
    
    total_value = sum(float(item.get('price', 0) or 0) for item in suggested_products)

    composed_room_image_url = None

    # Fallback to simple overlay
    if not composed_room_image_url and suggested_products:
        if wall_box:
            # Note: We keep _compose_room_with_product_in_box for wall-specific placement if needed
            # But currently we'll use the upgraded _compose_room_with_product for consistency
            composed_bytes = _compose_room_with_product(uploaded_bytes, suggested_products[0].get("id", ""), wall_length)
        else:
            composed_bytes = _compose_room_with_product(uploaded_bytes, suggested_products[0].get("id", ""), wall_length)
        
        if composed_bytes:
            composed_name = f"{uuid4().hex}.jpg"
            composed_path = UPLOAD_DIR / composed_name
            composed_path.write_bytes(composed_bytes)
            composed_room_image_url = build_image_url(f"/uploads/{composed_name}")
    
    return {
        "design_id": f"design-{uuid4().hex}",
        "style": analysis.get('style', 'Contemporary Living'),
        "colors": analysis.get('colors', ["#F3F4F6", "#CBD5E1", "#94A3B8"]),
        # Prefer composed image if available, else original
        "room_image_url": composed_room_image_url or original_room_image_url,
        "original_room_image_url": original_room_image_url,
        "suggested_products": [
            {
                "id": item['id'],
                "name": item['name'],
                "price": float(item.get('price', 0) or 0),
                "category": item.get('category', ''),
                "image_url": item.get('image_url', ''),
                "metadata": item
            }
            for item in suggested_products[:6]
        ],
        "total_value": total_value,
        "room_description": room_description,
        "wall_length": wall_length,
        "wall_colors": wall_colors,
        "analysis": analysis.get('analysis', ''),
        "placement_debug": {
            "wall_box": wall_box,
        },
    }

@app.post("/api/design/analyze")
async def analyze_room(room_photo: UploadFile = File(...)):
    """
    Stand-alone analysis endpoint for instant feedback on upload.
    """
    try:
        uploaded_bytes = await room_photo.read()
        from vision_agent import analyze_room_metadata
        room_metadata = analyze_room_metadata(uploaded_bytes)
        
        # Get dominant colors for the "Wall Colors" field
        colors = _dominant_colors_hex(uploaded_bytes, limit=3)
        
        return {
            "style": room_metadata.get("room_style", "Modern"),
            "colors": ", ".join(colors) if colors else "Neutral",
            "temperature": room_metadata.get("color_temperature", "Neutral"),
            "lighting": room_metadata.get("lighting_direction", "Natural"),
            "surface": room_metadata.get("surface_material", "Standard"),
            "description": f"{room_metadata.get('room_style', 'Modern')} space with {room_metadata.get('color_temperature', 'neutral').lower()} tones and {room_metadata.get('lighting_direction', 'natural').lower()} lighting."
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/design/preview")
async def preview_design(
    room_image: UploadFile = File(...),
    product_id: str = Form(...),
    wall_length: Optional[float] = Form(None)
):
    try:
        room_bytes = await room_image.read()
        
        # [PATCH] Run heavy CPU-bound compositor in a separate thread so it doesn't block the async event loop
        import asyncio
        composed_bytes = await asyncio.to_thread(_compose_room_with_product, room_bytes, product_id, wall_length)
        
        if not composed_bytes:
            return {"error": "Composition failed"}
            
        # Save the result
        preview_name = f"preview-{uuid4().hex}.jpg"
        preview_path = UPLOAD_DIR / preview_name
        preview_path.write_bytes(composed_bytes)
        preview_url = build_image_url(f"/uploads/{preview_name}")

        return {
            "preview_url": preview_url,
            "product_id": product_id,
            "wall_length": wall_length
        }
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)