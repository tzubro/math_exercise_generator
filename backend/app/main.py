from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import initialize_database
from .models import ApiHealth
from .routes.exercises import router as exercises_router
from .routes.imports import router as imports_router
from .routes.images import router as images_router
from .routes.tests import router as tests_router


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"
ASSETS_DIR = FRONTEND_DIST / "assets"

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Math Test Generator API", version="0.1.0", lifespan=lifespan)
app.include_router(exercises_router)
app.include_router(tests_router)
app.include_router(imports_router)
app.include_router(images_router)

if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/api/health", response_model=ApiHealth, tags=["system"])
def health() -> ApiHealth:
    return ApiHealth(status="ok")


@app.get("/", include_in_schema=False)
def frontend_root():
    if not FRONTEND_INDEX.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Frontend build not found. Run `npm run build` in frontend."
            },
        )
    return FileResponse(FRONTEND_INDEX)


@app.get("/{path:path}", include_in_schema=False)
def frontend_route(path: str):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")

    if not FRONTEND_INDEX.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Frontend build not found. Run `npm run build` in frontend."
            },
        )

    requested_file = (FRONTEND_DIST / path).resolve()
    if FRONTEND_DIST.resolve() not in requested_file.parents:
        raise HTTPException(status_code=404, detail="Not found")
    if requested_file.is_file():
        return FileResponse(requested_file)
    if Path(path).suffix:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(FRONTEND_INDEX)
