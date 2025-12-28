import os
import shutil
import json
import re
from datetime import datetime
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware

# Import routers
from routes import tus_upload, recording_complete
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load configuration from environment variables (or defaults)
ALLOWED_HOSTS = json.loads(os.getenv("ALLOWED_HOSTS", '["localhost", "127.0.0.1", "testserver"]'))
CORS_ORIGINS = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:8000"]'))
SECRET_KEY = os.getenv("SECRET_KEY", "default_insecure_key_for_dev") # WARN: Change in prod!
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1048576"))  # Default 1MB
TUS_CHUNK_SIZE = int(os.getenv("TUS_CHUNK_SIZE", "524288"))  # Default 512KB for TUS sub-chunks

app = FastAPI()

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data:; media-src 'self' blob: data:; connect-src 'self';"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# 1. Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=ALLOWED_HOSTS
)

# Include routers
app.include_router(tus_upload.router, tags=["TUS Upload"])
app.include_router(recording_complete.router, tags=["Recording"])

# 2. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD", "PATCH", "DELETE"], # Restrict methods but allow TUS methods
    allow_headers=["*"],
    expose_headers=["Upload-Offset", "Upload-Length", "Tus-Resumable", "Location"],
)

# 3. Storage Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "backend" / "uploaded_data"
STATIC_DIR = BASE_DIR / "frontend" / "public"
FRONTEND_SRC = BASE_DIR / "frontend" / "src"
CHUNKS_PER_SHARD = 1000  # Max chunks per subdirectory

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# 5. API Endpoints
@app.get("/api/config")
async def get_config():
    """
    Get server configuration for frontend.
    Returns chunk sizes and other settings loaded from .env or defaults.
    """
    return {
        "chunk_size": CHUNK_SIZE,
        "tus_chunk_size": TUS_CHUNK_SIZE,
        "upload_methods": ["tus"],
        "default_upload_method": "tus"
    }

@app.head("/health")
@app.get("/health")
async def health_check():
    """
    Health check endpoint for connection testing.
    Returns 200 OK if server is running.
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# NOTE: /recording/complete endpoint is now handled by routes/recording_complete.py
# This avoids duplication and uses the router-based implementation which supports
# both sharded storage (Service Worker uploads) and TUS uploads

# 6. Frontend Serving
# Mount static assets (favicon, etc.)
app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")

# Serve index.html and sw.js from frontend/src
@app.get("/")
async def serve_index():
    return FileResponse(FRONTEND_SRC / "index.html")

@app.get("/sw.js")
async def serve_service_worker():
    return FileResponse(FRONTEND_SRC / "sw.js", media_type="application/javascript")

@app.get("/tus-upload-manager.js")
async def serve_tus_upload_manager():
    return FileResponse(FRONTEND_SRC / "tus-upload-manager.js", media_type="application/javascript")

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(FRONTEND_SRC / "manifest.json", media_type="application/json")

@app.get("/favicon.svg")
async def serve_favicon():
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")

@app.get("/tus.min.js")
async def serve_tus_client():
    return FileResponse(FRONTEND_SRC / "tus.min.js", media_type="application/javascript")

@app.get("/tailwind.min.js")
async def serve_tailwind():
    return FileResponse(FRONTEND_SRC / "tailwind.min.js", media_type="application/javascript")

@app.get("/fonts.css")
async def serve_fonts_css():
    return FileResponse(FRONTEND_SRC / "fonts.css", media_type="text/css")

# Serve font files
app.mount("/fonts", StaticFiles(directory=str(FRONTEND_SRC / "fonts")), name="fonts")

if __name__ == "__main__":
    import uvicorn
    print("--- WAVEFORGE PRO SERVER ---")
    print(f"Frontend Source: {FRONTEND_SRC.absolute()}")
    print(f"Static Assets:   {STATIC_DIR.absolute()}")
    print(f"Storage Path:    {UPLOAD_DIR.absolute()}")
    print("")
    print("🌐 Server URLs:")
    print("   Local:   http://localhost:8000")
    print("   Network: http://0.0.0.0:8000")
    print("")
    print("📝 Note: In production, use HTTPS with TLS/SSL certificates")
    print("         (automatically handled by Kubernetes Ingress)")
    
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
    