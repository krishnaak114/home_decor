import os
import sys
import re
import time
import pandas as pd
import chromadb
import numpy as np
from chromadb.utils import embedding_functions
from pathlib import Path
from PIL import Image
import io

# Paths
BASE_DIR     = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
EXCEL_PATH   = PROJECT_ROOT / "Product Master Sheet.xlsx"
PRODUCTS_DIR = PROJECT_ROOT / "Products"
DB_DIR       = BASE_DIR / "chroma_db"

def normalize(text):
    if not text or pd.isna(text): return ""
    return re.sub(r'[^a-z0-9]', '', str(text).lower())

IMAGE_INDEX = {}
IMAGE_PATH_INDEX = {}

def index_images():
    print("\n[STEP 1] Indexing image vault...", end="", flush=True)
    count = 0
    for root, _, files in os.walk(PRODUCTS_DIR):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                # Normalize both the filename and the parent folder name for better matching
                stem = Path(f).stem
                norm_name = normalize(stem)
                if norm_name:
                    rel_path = Path(root).relative_to(PRODUCTS_DIR) / f
                    IMAGE_INDEX[norm_name]      = f"/images_vault/{rel_path.as_posix()}"
                    IMAGE_PATH_INDEX[norm_name] = Path(root) / f
                    count += 1
    print(f" Done. ({count} images indexed)")

def get_clip_embedding(image_path: Path, text: str, clip_model) -> list:
    import numpy as np
    try:
        img = Image.open(image_path).convert("RGB").resize((224, 224))
        img_emb  = clip_model.encode(img,  show_progress_bar=False)
        txt_emb  = clip_model.encode(text, show_progress_bar=False)
        # Weight text slightly more for better category relevance
        fused    = (img_emb * 0.4 + txt_emb * 0.6)
        return fused.tolist()
    except Exception as e:
        try:
            return clip_model.encode(text, show_progress_bar=False).tolist()
        except:
            return [0.0] * 512


def compute_dominant_color_hex(image_path: Path) -> str:
    """
    Calculate the average (dominant) color of a product image as a hex string.
    Uses a small thumbnail for speed. Returns '#CBD5E1' on failure.
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img.thumbnail((160, 160))
            arr = np.asarray(img, dtype=np.float32)
        r, g, b = arr[..., 0].mean(), arr[..., 1].mean(), arr[..., 2].mean()
        return f"#{int(r):02X}{int(g):02X}{int(b):02X}"
    except Exception:
        return "#CBD5E1"


def compute_has_transparency(image_path: Path) -> bool:
    """
    Check if a product image has any transparent pixels (RGBA with alpha < 255).
    Images with transparency are preferred for compositing.
    """
    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "LA"):
                alpha = img.getchannel("A")
                return alpha.getextrema()[0] < 255
        return False
    except Exception:
        return False


def compute_aspect_ratio(image_path: Path) -> float:
    """
    Calculate width/height aspect ratio of a product image.
    Returns 1.0 on failure.
    """
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            return round(w / max(1, h), 4)
    except Exception:
        return 1.0

def main():
    index_images()

    print("\n[STEP 2] Loading CLIP model (clip-ViT-B-32)...", flush=True)
    from sentence_transformers import SentenceTransformer
    clip_model = SentenceTransformer("clip-ViT-B-32")
    print("         CLIP model loaded OK")

    print("\n[STEP 3] Initialising ChromaDB...")
    client = chromadb.PersistentClient(path=str(DB_DIR))

    for coll_name in ["products"]:
        try:
            client.delete_collection(name=coll_name)
            print(f"  > Wiping old '{coll_name}'...")
        except:
            pass

    collection = client.create_collection(
        name="products",
        metadata={"hnsw:space": "cosine"}
    )

    xl = pd.ExcelFile(EXCEL_PATH)
    total_indexed = 0

    print("\n[STEP 4] Syncing categories with CLIP embeddings...\n")

    for sheet_name in xl.sheet_names:
        if sheet_name.lower() in ['all items list', 'layouts', 'inspiration images']:
            continue

        print(f"CATEGORY: [{sheet_name}]", flush=True)
        try:
            df_raw = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, header=None)
            header_row_idx = 0
            found_header = False
            for idx, row_data in df_raw.iterrows():
                row_str = " ".join([str(v).lower() for v in row_data.values if pd.notna(v)])
                if 'product name' in row_str or 'item name' in row_str or 'particular' in row_str:
                    header_row_idx = idx
                    found_header = True
                    break
            
            if not found_header:
                print(f"   ! Could not find header row in {sheet_name}, skipping.")
                continue

            df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, header=header_row_idx)
            df.columns = [str(c).strip() for c in df.columns]
            
            # Find the best name column
            name_col = next((c for c in df.columns if any(t in c.lower() for t in ['name', 'item', 'particular', 'product'])), df.columns[0])

            count = 0
            batch_ids, batch_embeddings, batch_metadatas, batch_documents = [], [], [], []

            for _, row in df.iterrows():
                p_name = str(row[name_col]).strip()
                if not p_name or p_name.lower() in ['nan', 'none', 'product name', 'item name']:
                    continue

                # Fuzzy matching for image
                norm_p_name = normalize(p_name)
                image_url  = IMAGE_INDEX.get(norm_p_name)
                image_path = IMAGE_PATH_INDEX.get(norm_p_name)
                
                # Try prefix matching if exact normalized match fails
                if not image_url:
                    for key in IMAGE_INDEX:
                        if key.startswith(norm_p_name) or norm_p_name.startswith(key):
                            image_url = IMAGE_INDEX[key]
                            image_path = IMAGE_PATH_INDEX[key]
                            break
                
                if not image_url:
                    continue

                metadata = {}
                price_val = 0.0
                for col in df.columns:
                    val = row[col]
                    if pd.notna(val) and str(val).strip():
                        # Store everything in metadata
                        metadata[col] = str(val)
                        # Specific price detection
                        col_lower = col.lower()
                        if any(t in col_lower for t in ['price', 'mrp', 'rate', 'value', 'target']):
                            try:
                                nums = re.findall(r"[\d.]+", str(val).replace(',', ''))
                                if nums:
                                    price_val = float(nums[0])
                            except:
                                pass

                pid_base = f"{normalize(sheet_name)}-{norm_p_name}"
                pid = pid_base
                # Handle potential duplicate IDs within the same sheet
                dup_count = 1
                while pid in batch_ids:
                    pid = f"{pid_base}_{dup_count}"
                    dup_count += 1

                metadata["id"]        = pid
                metadata["name"]      = p_name
                metadata["image_url"] = image_url
                metadata["category"]  = sheet_name
                metadata["price"]     = str(price_val)

                # ── Pre-compute visual metadata (avoids runtime I/O) ──
                metadata["dominant_color_hex"] = compute_dominant_color_hex(image_path)
                metadata["has_transparency"]   = str(compute_has_transparency(image_path))  # ChromaDB stores strings
                metadata["aspect_ratio"]       = str(compute_aspect_ratio(image_path))

                # Build a rich searchable document
                doc_parts = [f"{k}: {v}" for k, v in metadata.items() if len(str(v)) < 100]
                document  = ". ".join(doc_parts)
                
                embedding = get_clip_embedding(image_path, document, clip_model)

                batch_ids.append(pid)
                batch_metadatas.append(metadata)
                batch_documents.append(document)
                batch_embeddings.append(embedding)

                count += 1
                if count % 10 == 0:
                    print(f"   > {count} items processed...", flush=True)

            if batch_ids:
                collection.add(
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                    ids=batch_ids,
                    embeddings=batch_embeddings
                )
                total_indexed += count

            print(f"   DONE: [{sheet_name}] synced ({count} products).\n")
            time.sleep(0.05)

        except Exception as e:
            print(f"   ERROR in sheet [{sheet_name}]: {e}")

    print(f"\nALL DONE! {total_indexed} products indexed successfully.")

if __name__ == "__main__":
    main()
