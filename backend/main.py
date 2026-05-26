"""
Main FastAPI application entry point.

- Mounts all routers under /api prefix
- Serves the frontend as static files
- Auto-creates all database tables on startup
- CORS is set to allow all origins for cross-device access
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.database import Base, engine
from backend.routers import auth as auth_router
from backend.routers import documents as docs_router
from backend.routers import generation as gen_router

# ─── App setup ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Study Assistant",
    description="Upload study material and get AI-generated flashcards and quiz questions.",
    version="1.0.0",
)

# CORS — allow all origins so the app works from any device/domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Database ────────────────────────────────────────────────────────────────

@app.on_event("startup")
def create_tables():
    """Create all database tables on startup if they don't exist."""
    # Ensure data directory exists for Render persistent disk
    db_url = os.getenv("DATABASE_URL", "sqlite:///./study_assistant.db")
    if "////" in db_url:  # absolute path like sqlite:////data/study_assistant.db
        db_path = db_url.replace("sqlite:////", "/")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


# ─── API Routers ─────────────────────────────────────────────────────────────

app.include_router(auth_router.router, prefix="/api")
app.include_router(docs_router.router, prefix="/api")
app.include_router(gen_router.router, prefix="/api")

# ─── Frontend static files ───────────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Catch-all: serve index.html for any non-API route (SPA routing)."""
        # Don't intercept API or static routes
        if full_path.startswith("api/") or full_path.startswith("static/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        return FileResponse(str(FRONTEND_DIR / "index.html"))
