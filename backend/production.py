"""Production entrypoint serving FastAPI APIs and the compiled React app."""

import os
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
if railway_domain:
    public_url = f"https://{railway_domain}"
    os.environ["CORS_ORIGINS"] = public_url
    os.environ["FRONTEND_URL"] = public_url

from server import app


frontend_build = (Path(__file__).resolve().parent.parent / "frontend" / "build").resolve()
if not frontend_build.exists():
    raise RuntimeError(f"Frontend production build not found at {frontend_build}")

static_dir = frontend_build / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    requested = (frontend_build / full_path).resolve()
    try:
        requested.relative_to(frontend_build)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    if requested.is_file():
        return FileResponse(str(requested))
    index_file = frontend_build / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=500, detail="Frontend build unavailable")
    return FileResponse(str(index_file))
