"""Cleanup Assistant FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Cleanup Assistant", version="1.2.1")

# Serve static files (CSS, JS)
static_path = Path(__file__).parent.parent.parent / "dist"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
else:
    # Fallback to development files
    app.mount("/static", StaticFiles(directory=str(Path(__file__).parent.parent / "ui")), name="static")

# Serve index.html at root
@app.get("/", response_class="HTMLResponse")
def read_root():
    """Serve the main HTML page."""
    index_path = Path(__file__).parent.parent.parent / "dist" / "index.html"
    if not index_path.exists():
        # Fallback to development file
        index_path = Path(__file__).parent.parent / "ui" / "index.html"
    return index_path.read_text()


@app.get("/api/")
def read_api():
    """API root endpoint."""
    return {"message": "Cleanup Assistant API"}


def main():
    """Run the application."""
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

