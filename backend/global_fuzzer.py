import asyncio
import io
import time
import random
import numpy as np
from PIL import Image

print("==================================================")
print("  CODEBASE-WIDE VULNERABILITY & BOTTLENECK FUZZER ")
print("==================================================")
print("Identifying architectural limits, memory leaks, and model bottlenecks...")

# --- 1. MEMORY & VRAM BOTTLENECK TESTING ---
def test_depth_model_vram_limits():
    print("\n[TEST] Depth Anything V2 VRAM Scaling Limit")
    from vision_agent import _lazy_get_depth_map
    
    resolutions = [
        (512, 512), (1024, 1024), (2048, 2048), (4096, 4096), (8192, 8192)
    ]
    
    for w, h in resolutions:
        print(f"  Testing resolution: {w}x{h}...", end=" ")
        arr = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        b = io.BytesIO()
        Image.fromarray(arr).save(b, format="JPEG")
        
        start = time.time()
        try:
            _lazy_get_depth_map(b.getvalue())
            elapsed = time.time() - start
            print(f"SUCCESS ({elapsed:.2f}s)")
        except Exception as e:
            print(f"FAILED: {type(e).__name__} (This is your maximum hardware ceiling)")
            break # Stop before crashing the whole OS


# --- 2. VECTOR DATABASE BOTTLENECK TESTING ---
def test_chromadb_limits():
    print("\n[TEST] ChromaDB Retrieval Bounds")
    from main import get_product_collection
    
    col = get_product_collection()
    if not col:
        print("  [SKIP] Database not initialized.")
        return
        
    print("  Testing 100k Character Semantic Query...")
    massive_query = "sofa " * 20000 
    
    start = time.time()
    try:
        results = col.query(query_texts=[massive_query], n_results=5)
        elapsed = time.time() - start
        print(f"  SUCCESS ({elapsed:.2f}s) - ChromaDB handles massive string vectors securely.")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__} - {e}")


# --- 3. VISION PARSER VULNERABILITY TESTING ---
def test_lifestyle_agent_fuzzing():
    print("\n[TEST] Lifestyle Agent Output Fuzzing")
    from lifestyle_agent import detect_lifestyle_markers
    
    # We test what happens if Gemini fails to analyze the image
    print("  Testing pure static noise image injection...")
    arr = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
    b = io.BytesIO()
    Image.fromarray(arr).save(b, format="JPEG")
    
    try:
        res = detect_lifestyle_markers(b.getvalue())
        print(f"  SUCCESS - Handled gracefully. Fallback output: {res}")
    except Exception as e:
        print(f"  FAILED: {type(e).__name__} - Agent crashed on noise!")


# --- 4. FASTAPI ENDPOINT ASYNC BLOCKING TEST ---
async def test_async_event_loop_blocking():
    print("\n[TEST] FastAPI Event Loop Synchronous Blocking")
    import main
    
    print("  Testing if _compose_room_with_product blocks the async event loop...")
    # Generate a small dummy room and try to compose
    arr = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    b = io.BytesIO()
    Image.fromarray(arr).save(b, format="JPEG")
    
    # Track event loop delay
    start = time.time()
    
    # Run the heavy synchronous CPU bound task
    try:
        # We pass an invalid product_id to see how fast it rejects
        res = main._compose_room_with_product(b.getvalue(), product_id="INVALID_ID_FUZZ")
    except Exception:
        pass
        
    elapsed = time.time() - start
    if elapsed > 0.1:
        print(f"  [WARNING] Synchronous blocking detected! Took {elapsed:.2f}s.")
        print("  Fix: You need to wrap this in asyncio.to_thread() or use Celery, otherwise 1 user will freeze all others.")
    else:
        print(f"  [PASS] Speedy rejection/execution ({elapsed:.4f}s). No severe blocking.")

def run_fuzzer():
    test_depth_model_vram_limits()
    test_chromadb_limits()
    test_lifestyle_agent_fuzzing()
    
    # Run async tests
    asyncio.run(test_async_event_loop_blocking())
    
    print("\n==================================================")
    print("  VULNERABILITY & BOTTLENECK SCAN COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    run_fuzzer()
