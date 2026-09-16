Role: You are an expert Full-Stack Engineer for the Home Decor AI Platform.

## Context
Always read `graphify-out/GRAPH_REPORT.md` before starting a task. It contains the up-to-date architecture, data flow, and module map.

## Architecture
- **Backend**: FastAPI (Python 3.11) at `backend/main.py`
- **Frontend**: Next.js 15 + React 18 + TypeScript at `frontend/`
- **AI Models**: Gemini 2.0 Flash (room analysis), CLIP ViT-B-32 (search), Depth Anything V2 (depth)
- **Database**: ChromaDB (vector similarity search for products)
- **Rendering**: Stability AI (inpainting) with PIL fallback

## Key Modules
| File | Responsibility |
|------|---------------|
| `backend/main.py` | API endpoints + product compositor (placement engine) |
| `backend/vision_agent.py` | Room analysis (Gemini), background removal (rembg), shadows |
| `backend/depth_engine.py` | Depth Anything V2 — monocular depth estimation |
| `backend/render_engine.py` | Stability AI inpainting + PIL fallback rendering |
| `backend/master_sync.py` | Excel → ChromaDB product data pipeline |

## Coding Standards
- Follow PEP 8
- All image processing belongs in `vision_agent.py` or `render_engine.py`
- Product classification and placement logic stays in `main.py`
- Use type hints for all function signatures
- Keep the CLIP model as a singleton (via `get_clip_model()`)
- Never break the compositor pipeline — test with `python -c "import ast; ast.parse(open('main.py').read())"`

## Product Placement Rules (Interior Designer Logic)
1. Detect visible room boundaries first (ignore black bars)
2. Detect floor line from depth map
3. Scale products as % of visible wall width (assume 10ft = 305cm default)
4. Floor items → bottom edge on floor, centered
5. Wall art → eye level (35% from top), centered
6. Ceiling lights → top of frame, centered
7. Small decor → slightly offset from center, on floor or surface

## Environment Variables
- `GEMINI_API_KEY` — Required for room analysis
- `STABILITY_API_KEY` — Optional for AI rendering (PIL fallback otherwise)
