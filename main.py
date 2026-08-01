"""VRAV AI — Sovereign Agentic Orchestrator"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from core.orchestrator import router as orchestrator_router
from core.auth.routes import router as auth_router
from core.auth.middleware import AuthMiddleware
from core.safety.shield import ShieldMiddleware

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
WEB_DIST = ROOT / "web" / "dist"

app = FastAPI(
    title=settings.app_name,
    description="Independent, privacy-first agentic orchestration. No OpenAI / Anthropic.",
    version="0.8.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(AuthMiddleware)
app.add_middleware(ShieldMiddleware)

app.include_router(orchestrator_router, prefix="/api")
app.include_router(auth_router, prefix="/api")

if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
if WEB_DIST.exists():
    app.mount("/ui", StaticFiles(directory=str(WEB_DIST), html=True), name="spa")


@app.get("/")
async def ui_root():
    spa = WEB_DIST / "index.html"
    if spa.exists():
        return FileResponse(spa)
    index = STATIC / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"service": "VRAV AI", "docs": "/docs", "health": "/api/health"}


@app.get("/app")
async def ui_app():
    return FileResponse(STATIC / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
