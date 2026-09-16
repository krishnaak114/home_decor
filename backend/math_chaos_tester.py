import numpy as np
import io
from PIL import Image
import traceback

# Import core mathematical and vision functions
from surface_detector import (
    detect_floor_region,
    detect_room_bounds,
    detect_empty_surfaces,
    build_walkable_flow_grid,
    compute_visual_center_of_mass
)
from light_probe import estimate_sh_coefficients
from main import _find_perspective_coeffs

print("==================================================")
print("  PROJECT-WIDE MATHEMATICAL CHAOS TESTING SUITE")
print("==================================================")
print("Testing every core function with extreme noise, zeros, and structural anomalies...")

failed_tests = 0
passed_tests = 0

def log_result(name, success, error=None):
    global failed_tests, passed_tests
    if success:
        print(f"[PASS] {name}")
        passed_tests += 1
    else:
        print(f"[FAIL] {name} -> {type(error).__name__}: {error}")
        failed_tests += 1

def make_dummy_image(w, h, color="black"):
    if color == "black":
        arr = np.zeros((h, w, 3), dtype=np.uint8)
    elif color == "white":
        arr = np.ones((h, w, 3), dtype=np.uint8) * 255
    elif color == "noise":
        arr = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    
    img = Image.fromarray(arr)
    b = io.BytesIO()
    img.save(b, format="JPEG")
    return arr, b.getvalue()

def test_detect_floor_region():
    print("\n--- Testing detect_floor_region ---")
    
    # Test 1: All zeros depth map
    try:
        depth = np.zeros((100, 100), dtype=np.float32)
        bounds = {"left": 0, "top": 0, "right": 100, "bottom": 100}
        res = detect_floor_region(depth, bounds)
        log_result("All zeros depth map", True)
    except Exception as e:
        log_result("All zeros depth map", False, e)
        
    # Test 2: Extreme aspect ratio
    try:
        depth = np.random.rand(10, 5000).astype(np.float32)
        bounds = {"left": 0, "top": 0, "right": 5000, "bottom": 10}
        res = detect_floor_region(depth, bounds)
        log_result("Extreme wide depth map", True)
    except Exception as e:
        log_result("Extreme wide depth map", False, e)

    # Test 3: Bounding box outside depth map bounds
    try:
        depth = np.random.rand(100, 100).astype(np.float32)
        bounds = {"left": 50, "top": 50, "right": 200, "bottom": 200}
        res = detect_floor_region(depth, bounds)
        log_result("Out of bounds slicing", True)
    except Exception as e:
        log_result("Out of bounds slicing", False, e)


def test_detect_room_bounds():
    print("\n--- Testing detect_room_bounds ---")
    
    # Test 1: Pure black image (no brightness)
    try:
        arr, _ = make_dummy_image(100, 100, "black")
        res = detect_room_bounds(arr)
        log_result("Pure black image", True)
    except Exception as e:
        log_result("Pure black image", False, e)

    # Test 2: Pure white image
    try:
        arr, _ = make_dummy_image(100, 100, "white")
        res = detect_room_bounds(arr)
        log_result("Pure white image", True)
    except Exception as e:
        log_result("Pure white image", False, e)


def test_build_walkable_flow_grid():
    print("\n--- Testing build_walkable_flow_grid ---")
    try:
        _, bytes_img = make_dummy_image(200, 200, "noise")
        depth = np.random.rand(200, 200).astype(np.float32)
        bounds = {"left": 0, "top": 0, "right": 200, "bottom": 200}
        # High clearance that exceeds image size
        res = build_walkable_flow_grid(bytes_img, depth, bounds, floor_y=100, clearance_px=500)
        log_result("Massive clearance radius", True)
    except Exception as e:
        log_result("Massive clearance radius", False, e)
        
    try:
        _, bytes_img = make_dummy_image(10, 10, "noise")
        depth = np.zeros((10, 10), dtype=np.float32)
        bounds = {"left": 0, "top": 0, "right": 10, "bottom": 10}
        res = build_walkable_flow_grid(bytes_img, depth, bounds, floor_y=5, clearance_px=2)
        log_result("Tiny image flow grid", True)
    except Exception as e:
        log_result("Tiny image flow grid", False, e)


def test_perspective_coeffs():
    print("\n--- Testing _find_perspective_coeffs ---")
    
    # Test 1: Collinear points (matrix inversion should fail mathematically)
    try:
        src = [(0,0), (1,1), (2,2), (3,3)]
        dst = [(0,0), (10,10), (20,20), (30,30)]
        res = _find_perspective_coeffs(src, dst)
        log_result("Collinear perspective points", True)
    except Exception as e:
        log_result("Collinear perspective points", False, e)

    # Test 2: Exact same points
    try:
        src = [(0,0), (1,0), (1,1), (0,1)]
        dst = [(0,0), (1,0), (1,1), (0,1)]
        res = _find_perspective_coeffs(src, dst)
        log_result("Identical source and destination", True)
    except Exception as e:
        log_result("Identical source and destination", False, e)


def test_estimate_sh_coefficients():
    print("\n--- Testing estimate_sh_coefficients ---")
    
    # Test 1: Empty light vector
    try:
        _, bytes_img = make_dummy_image(100, 100, "white")
        light_vec = {"sources": [], "angle_deg": 0, "confidence": 0}
        res = estimate_sh_coefficients(bytes_img, light_vec)
        log_result("Empty light sources", True)
    except Exception as e:
        log_result("Empty light sources", False, e)

    # Test 2: Extreme coordinates for light source
    try:
        _, bytes_img = make_dummy_image(100, 100, "black")
        light_vec = {"sources": [{"x": 9999, "y": -9999, "kelvin": 6000, "intensity": 1.0, "area_pct": 0.5}]}
        res = estimate_sh_coefficients(bytes_img, light_vec)
        log_result("Out of bounds light coordinates", True)
    except Exception as e:
        log_result("Out of bounds light coordinates", False, e)


def test_compute_visual_center_of_mass():
    print("\n--- Testing compute_visual_center_of_mass ---")
    
    # Test 1: All black image (zero division risk in CoM)
    try:
        _, bytes_img = make_dummy_image(100, 100, "black")
        bounds = {"left": 0, "top": 0, "right": 100, "bottom": 100}
        res = compute_visual_center_of_mass(bytes_img, bounds)
        log_result("CoM on pure black (divide by zero risk)", True)
    except Exception as e:
        log_result("CoM on pure black (divide by zero risk)", False, e)


def main():
    test_detect_floor_region()
    test_detect_room_bounds()
    test_build_walkable_flow_grid()
    test_perspective_coeffs()
    test_estimate_sh_coefficients()
    test_compute_visual_center_of_mass()
    
    print("\n==================================================")
    print(f"  CHAOS TEST COMPLETE")
    print(f"  Passed: {passed_tests} | Failed: {failed_tests}")
    print("==================================================")

if __name__ == "__main__":
    main()
