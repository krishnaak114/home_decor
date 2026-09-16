# 🏠 Home Decor AI Platform

> AI-powered interior design tool that analyzes rooms and recommends products with photorealistic placement previews.

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────┐
│  Next.js 15      │────▶│  FastAPI Backend (Python 3.11)        │
│  React / TS      │◀────│                                      │
│  localhost:3000   │     │  ┌───────────┐  ┌────────────────┐  │
└─────────────────┘     │  │ Vision    │  │ Render Engine  │  │
                         │  │ Agent     │  │ (PIL/Stability)│  │
                         │  └─────┬─────┘  └───────┬────────┘  │
                         │        │                 │           │
                         │  ┌─────▼─────┐  ┌───────▼────────┐  │
                         │  │ Gemini    │  │ Depth Anything  │  │
                         │  │ 2.0 Flash │  │ V2 (MDE)       │  │
                         │  └───────────┘  └────────────────┘  │
                         │                                      │
                         │  ┌───────────┐  ┌────────────────┐  │
                         │  │ ChromaDB  │  │ CLIP ViT-B-32  │  │
                         │  │ (Vector)  │  │ (Embeddings)   │  │
                         │  └───────────┘  └────────────────┘  │
                         │  localhost:8000                      │
                         └──────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 15, React 18, TypeScript | Interactive design UI |
| **Backend** | FastAPI, Python 3.11, Uvicorn | API server |
| **Room Analysis** | Gemini 2.0 Flash (Google AI Studio) | Style, lighting, surface detection |
| **Product Search** | CLIP ViT-B-32 + ChromaDB | Multimodal vector similarity search |
| **Depth Mapping** | Depth Anything V2 Small | 3D depth estimation for placement |
| **Background Removal** | rembg | Isolate products from backgrounds |
| **Rendering** | Stability AI / PIL fallback | Photorealistic product compositing |
| **Product Data** | Excel → ChromaDB via `master_sync.py` | 500+ products across 13 categories |

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create `backend/.env`:
```env
GEMINI_API_KEY=your_key_here
STABILITY_API_KEY=your_key_here   # Optional — PIL fallback works without it
```

Sync product database (first time only):
```bash
python master_sync.py
```

Start server:
```bash
python main.py
# → http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

## How It Works

1. **Upload** a room photo → Gemini Vision analyzes style, lighting, surfaces
2. **Search** → CLIP encodes the room vibe, ChromaDB finds matching products
3. **Classify** → Each product is typed (furniture, wall art, vase, lighting, etc.)
4. **Place** → Depth map detects floor line; product is sized proportionally to a 10ft wall
5. **Render** → PIL composites the product into the room with shadow and lighting match
6. **Preview** → Click any product to see it placed in your room

## Project Structure

```
HOME_DECOR_PLATFORM/
├── backend/
│   ├── main.py              # FastAPI app — all endpoints + compositor
│   ├── vision_agent.py      # Gemini room analysis, placement coords, shadows
│   ├── depth_engine.py      # Depth Anything V2 wrapper
│   ├── render_engine.py     # Stability AI + PIL fallback rendering
│   ├── master_sync.py       # Excel → ChromaDB product indexer
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # API keys (not committed)
│   └── chroma_db/           # Persistent vector database
├── frontend/
│   └── src/app/page.tsx     # Main React UI
├── Products/                # Product images (organized by vendor)
├── Product Master Sheet.xlsx # Source product catalogue
├── graphify-out/            # Code graph analysis for IDE context
│   └── GRAPH_REPORT.md      # Architecture knowledge graph
└── README_POC.md            # This file
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/design/analyze` | Analyze room photo (style, colors, lighting) |
| `POST` | `/api/design/generate` | Full pipeline: analyze → search → compose |
| `POST` | `/api/design/preview` | Preview a specific product in the room |
| `GET`  | `/api/catalogue` | Browse full product catalogue by category |
| `GET`  | `/api/products/{id}/similar` | Find similar products via CLIP |
| `POST` | `/api/style-profile/{user}` | Save user style preferences |

## Product Categories (13)

| Category | Count | Type | Examples |
|----------|-------|------|---------|
| BL LIVING | 126 | Furniture | Sofas, tables, TV units |
| BL-BEDROOM | 81 | Furniture | Beds, dressers, nightstands |
| Lighting | 53 | Fixtures | Chandeliers, pendant lights, floor lamps |
| wallart | 48 | Wall Decor | Canvas sets, framed prints, gallery walls |
| ATRANG | 44 | Tabletop Decor | Sculptures, figurines, bookends |
| Blinds, Curtains | 33 | Window | Venetian, pleated, roller blinds |
| RugsCarpet | 32 | Floor | Area rugs, runners, dhurries |
| Meraki | 30 | Premium Furniture | Designer sofas, accent chairs |
| Wallpaper | 29 | Wall Cover | Custom wallpapers (per sqft) |
| GHAR ART | 24 | Vases & Decor | Artisan vases, planters |
| cusion covers | 21 | Soft Furnishing | Cushion sets, textured covers |
| BL-OUTDOOR | 14 | Outdoor | Patio furniture |
| SELF ADHESIVE WALL PANEL | 7 | Wall Cover | 3D panels, wood panels |
| wall hooks | 7 | Wall Decor | Decorative hooks |

## Key Algorithms

### Product Classifier (`_classify_product`)
Analyzes name, category, and metadata to determine:
- **wall_cover** → Wallpaper, panels → covers 55% of wall
- **wall_hang** → Art, clocks, mirrors → eye-level centered
- **floor_large** → Furniture → 30-55% of wall, sits on floor
- **ceiling** → Pendant lights → hangs from top
- **surface_small** → Vases, sculptures → 10-20% of wall, on surface

### Visible Room Detection
Photos often have black borders. The compositor detects the actual room boundaries using brightness thresholding, then scales/places products only within the visible area.

### Floor Line Detection
Uses Depth Anything V2 to find the wall-floor transition by analyzing depth gradients in the center column of the visible room.

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | ✅ Yes | Room analysis via Google AI Studio |
| `STABILITY_API_KEY` | ❌ Optional | AI inpainting (falls back to PIL) |

## Known Limitations

- Product images are single-angle catalogue shots (no 3D rotation)
- PIL fallback compositing is less photorealistic than AI inpainting
- Stability AI requires credits (402 error when exhausted)
- No user authentication or persistence yet

## Roadmap

1. Multi-angle product images for better room placement
2. AI perspective correction using generative models
3. User authentication and saved designs
4. Docker containerization
5. Payment integration (Razorpay)