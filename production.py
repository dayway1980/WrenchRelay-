import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from server import app

# Railway provides this automatically; add it to CORS when no explicit list was supplied.
domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
if domain and not os.getenv("FRONTEND_URL"):
    os.environ["FRONTEND_URL"] = f"https://{domain}"

build_dir = Path(__file__).resolve().parent.parent / "frontend" / "build"
if build_dir.exists():
    assets = build_dir / "static"
    if assets.exists():
        app.mount("/static", StaticFiles(directory=assets), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        requested = build_dir / path
        if path and requested.is_file():
            return FileResponse(requested)
        return FileResponse(build_dir / "index.html")
