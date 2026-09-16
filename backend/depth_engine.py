import torch
import numpy as np
import io
import cv2
from PIL import Image
from pathlib import Path
from transformers import AutoImageProcessor, AutoModelForDepthEstimation


class DepthEngine:
    """
    Depth estimation engine using Depth Anything V2 Small.
    
    Replaces MiDaS DPT-Hybrid which produced blurry depth maps with
    poor furniture/floor edge discrimination. Depth Anything V2 delivers
    significantly sharper boundary detection for accurate surface placement.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DepthEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        print("[DepthEngine] Initializing Depth Anything V2 Small...")
        # Depth Anything V2 Small: sharp edges, CPU-friendly, indoor-scene optimized
        self.model_name = "depth-anything/Depth-Anything-V2-Small-hf"

        cache_dir = Path(__file__).parent / ".cache" / "huggingface"
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.device = torch.device("cpu")

        self.image_processor = AutoImageProcessor.from_pretrained(
            self.model_name, cache_dir=cache_dir
        )
        self.model = AutoModelForDepthEstimation.from_pretrained(
            self.model_name, cache_dir=cache_dir
        )
        self.model.to(self.device)
        self.model.eval()

        self._initialized = True
        print("[DepthEngine] Depth Anything V2 loaded successfully.")

    def get_depth_map(self, image_bytes: bytes) -> np.ndarray:
        """
        Generates a sharpened, normalized depth map (0=far, 1=close).

        Pipeline:
          1. Depth Anything V2 inference at full resolution
          2. Bilateral filter to sharpen edges while preserving smooth gradients
          3. Normalize to [0, 1]
        """
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = image.size

        # 1. Inference
        inputs = self.image_processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            predicted_depth = outputs.predicted_depth

        # Upsample to original resolution with bilinear (preserves sharpness better than bicubic for depth)
        prediction = torch.nn.functional.interpolate(
            predicted_depth.unsqueeze(1),
            size=(height, width),
            mode="bilinear",
            align_corners=False,
        ).squeeze().cpu().numpy()

        # 2. Normalize to float32 [0, 1] for OpenCV
        depth_min, depth_max = prediction.min(), prediction.max()
        if depth_max > depth_min:
            normalized = (prediction - depth_min) / (depth_max - depth_min)
        else:
            normalized = np.zeros_like(prediction)

        normalized = normalized.astype(np.float32)

        # 3. Bilateral filter: sharpens furniture/floor edges while keeping
        #    smooth gradients on flat surfaces (walls, tabletops).
        #    d=9: 9px neighbourhood, sigmaColor=75: colour sensitivity,
        #    sigmaSpace=75: spatial smoothing range
        sharpened = cv2.bilateralFilter(normalized, d=9, sigmaColor=75, sigmaSpace=75)

        return sharpened

    def get_depth_at_coord(self, depth_map: np.ndarray, x: int, y: int) -> float:
        """Returns normalized depth (0-1) at pixel (x, y)."""
        h, w = depth_map.shape
        cx = max(0, min(w - 1, int(x)))
        cy = max(0, min(h - 1, int(y)))
        return float(depth_map[cy, cx])


# Singleton accessor
_engine = None

def get_depth_map(image_bytes: bytes) -> np.ndarray:
    global _engine
    if _engine is None:
        _engine = DepthEngine()
    return _engine.get_depth_map(image_bytes)
