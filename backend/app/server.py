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

# Input Validation Helpers
def validate_session_id(session_id: str):
    if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format")
    # Prevent path traversal
    if ".." in session_id or "/" in session_id or "\\" in session_id:
        raise HTTPException(status_code=400, detail="Invalid session_id path")

def validate_file_name(file_name: str):
    if not re.match(r"^[a-zA-Z0-9._-]+$", file_name):
        raise HTTPException(status_code=400, detail="Invalid file_name format")
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        raise HTTPException(status_code=400, detail="Invalid file_name path")

# Helper function for sharded chunk paths
def get_chunk_path(session_id: str, chunk_index: int, temp_suffix: str = "") -> Path:
    """
    Get sharded path for a chunk file.
    Chunks are organized into subdirectories: shard_0000, shard_0001, etc.
    Each shard contains up to CHUNKS_PER_SHARD chunks.
    
    Args:
        session_id: Session identifier
        chunk_index: Index of the chunk
        temp_suffix: Optional suffix (e.g., ".tmp" for temporary files)
    
    Returns:
        Path to the chunk file in its appropriate shard directory
    """
    validate_session_id(session_id) # Validate input
    session_dir = UPLOAD_DIR / session_id
    shard_num = chunk_index // CHUNKS_PER_SHARD
    shard_dir = session_dir / "temp" / f"shard_{shard_num:04d}"
    shard_dir.mkdir(parents=True, exist_ok=True)
    return shard_dir / f"{chunk_index}.part{temp_suffix}"

# 4. File Assembly Logic
def assemble_file(session_id: str, file_name: str, metadata: dict = None):
    """
    Background task to assemble chunks into the final file with metadata.
    Called when client signals recording is complete.
    Handles sharded directory structure efficiently.
    """
    try:
        validate_session_id(session_id)
        validate_file_name(file_name)
    except HTTPException as e:
        print(f"❌ Assembly aborted: {e.detail}")
        return

    session_dir = UPLOAD_DIR / session_id
    temp_dir = session_dir / "temp"
    completed_dir = session_dir / "completed"
    
    # Check if temp directory exists
    if not temp_dir.exists():
        print(f"⚠ No temp directory found for session {session_id}")
        print(f"   Session directory: {session_dir}")
        print(f"   Expected temp directory: {temp_dir}")
        print(f"   This usually means chunks haven't been uploaded yet or wrong session ID")
        return
    
    # Check if any shard directories exist (chunks are stored in shards)
    shard_dirs = list(temp_dir.glob("shard_*"))
    if not shard_dirs:
        print(f"⚠ No shard directories found in {temp_dir}")
        print(f"   This means no chunks have been uploaded yet")
        print(f"   Directory contents: {list(temp_dir.iterdir())}")
        return

    print(f"🔧 Assembling {file_name} for session {session_id}...")
    print(f"   Found {len(shard_dirs)} shard directories")
    
    # Create completed directory
    completed_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the original file name
    final_path = completed_dir / file_name
    metadata_path = completed_dir / f"{file_name}.meta.json"
    
    try:
        # CRITICAL: Only assemble COMPLETE chunks (.part files)
        # Ignore any .tmp files that may still be in progress
        file_size = 0
        chunk_info = []
        chunk_index = 0
        missing_chunks = []
        incomplete_chunks = []  # Track .tmp files found
        
        print(f"🔧 Starting assembly in strict mode (only complete .part files)")
        
        with open(final_path, "wb") as outfile:
            while True:
                chunk_path = get_chunk_path(session_id, chunk_index)
                chunk_tmp_path = get_chunk_path(session_id, chunk_index, temp_suffix=".tmp")
                
                # Check if chunk is still being written (.tmp exists)
                if chunk_tmp_path.exists() and not chunk_path.exists():
                    print(f"⚠️  Chunk {chunk_index} incomplete (.tmp exists, .part missing)")
                    incomplete_chunks.append(chunk_index)
                    
                    # Look ahead to see if there are more complete chunks
                    found_more = False
                    for look_ahead in range(1, 11):
                        future_chunk = get_chunk_path(session_id, chunk_index + look_ahead)
                        if future_chunk.exists():
                            found_more = True
                            break
                    
                    if found_more:
                        # Skip this incomplete chunk, continue with next
                        missing_chunks.append(chunk_index)
                        chunk_index += 1
                        continue
                    else:
                        # No more complete chunks ahead, stop assembly
                        print(f"⚠️  Stopping assembly - last chunk ({chunk_index}) is incomplete")
                        break
                
                # Check if complete chunk exists
                if not chunk_path.exists():
                    # Check if this is truly the end or a gap
                    # Look ahead 10 chunks to see if there are more
                    found_more = False
                    for look_ahead in range(1, 11):
                        if get_chunk_path(session_id, chunk_index + look_ahead).exists():
                            found_more = True
                            missing_chunks.append(chunk_index)
                            break
                    
                    if not found_more:
                        # No more chunks found, we're done
                        break
                    else:
                        # Gap detected, skip this chunk and continue
                        print(f"⚠️  Chunk {chunk_index} missing (gap detected)")
                        chunk_index += 1
                        continue
                
                # Verify chunk file size (must be > 0 bytes)
                chunk_size = chunk_path.stat().st_size
                if chunk_size == 0:
                    print(f"⚠️  Chunk {chunk_index} is empty (0 bytes), skipping")
                    missing_chunks.append(chunk_index)
                    chunk_index += 1
                    continue
                
                # Read and append chunk (only complete, non-empty chunks)
                with open(chunk_path, "rb") as infile:
                    data = infile.read()
                    outfile.write(data)
                    file_size += len(data)
                    chunk_info.append({
                        "index": chunk_index,
                        "size": len(data),
                        "filename": chunk_path.name
                    })
                
                chunk_index += 1
        
        # Report assembly status
        if incomplete_chunks:
            print(f"⚠️  Assembly completed with {len(incomplete_chunks)} incomplete chunks: {incomplete_chunks}")
        if missing_chunks:
            print(f"⚠️  Assembly completed with {len(missing_chunks)} missing chunks: {missing_chunks}")
        if not missing_chunks and not incomplete_chunks:
            print(f"✅ Assembly completed successfully with {len(chunk_info)} chunks (no gaps)")
        else:
            print(f"✓ Assembly completed with {len(chunk_info)} chunks ({len(missing_chunks)} gaps, {len(incomplete_chunks)} incomplete)")
        
        # Create metadata file
        meta_info = {
            "file_name": file_name,
            "session_id": session_id,
            "file_size_bytes": file_size,
            "total_chunks": len(chunk_info),
            "missing_chunks": missing_chunks if missing_chunks else [],
            "incomplete_chunks": incomplete_chunks if incomplete_chunks else [],
            "recording_completed_at": metadata.get("recordingCompletedAt") if metadata else None,
            "upload_completed_at": datetime.now().isoformat(),
            "mime_type": metadata.get("mimeType") if metadata else "audio/webm",
            "extension": metadata.get("extension") if metadata else file_name.split(".")[-1],
            "duration_seconds": metadata.get("duration") if metadata else None,
            "sample_rate": metadata.get("sampleRate") if metadata else None,
            "chunk_details": chunk_info,
            "client_metadata": metadata or {},
            "assembly_mode": "strict",
            "assembly_notes": "Only complete .part files assembled; .tmp files skipped"
        }
        
        with open(metadata_path, "w") as meta_file:
            json.dump(meta_info, meta_file, indent=2)
        
        # Cleanup temp directory
        shutil.rmtree(temp_dir)
        print(f"✓ File completed: {final_path} ({file_size} bytes)")
        print(f"✓ Metadata saved: {metadata_path}")
        print(f"✓ Cleaned up temp directory")
        
    except Exception as e:
        print(f"❌ Error assembling file: {e}")

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
        "upload_methods": ["tus", "legacy"],
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

@app.post("/upload/chunk")
async def upload_chunk(
    session_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...)
):
    """
    Receive a single chunk during recording with hash-based sharding.
    Chunks are stored in sharded subdirectories (1000 chunks per shard).
    Supports delayed/out-of-order chunk uploads.
    """
    validate_session_id(session_id) # Validate input

    # Use sharded path - automatically creates shard directory if needed
    chunk_path = get_chunk_path(session_id, chunk_index)
    chunk_path_tmp = get_chunk_path(session_id, chunk_index, temp_suffix=".tmp")
    
    # Check if chunk already exists (idempotency - allow retries)
    if chunk_path.exists():
        # CRITICAL: Verify existing chunk is complete by checking size matches
        # If chunk was partially written before server crash, we need to rewrite it
        try:
            existing_size = chunk_path.stat().st_size
            file.file.seek(0, 2)  # Seek to end to get size
            incoming_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning
            
            if existing_size == incoming_size and existing_size > 0:
                print(f"⏩ Chunk {chunk_index} already exists with correct size ({existing_size} bytes), skipping")
                return {"status": "chunk_already_exists", "chunk_index": chunk_index, "session_id": session_id}
            else:
                print(f"⚠️ Chunk {chunk_index} exists but size mismatch: existing={existing_size}, incoming={incoming_size}")
                print(f"⚠️ Chunk may be corrupted - will overwrite")
                # Delete corrupted chunk so it can be rewritten
                chunk_path.unlink()
        except Exception as check_err:
            print(f"⚠️ Error checking existing chunk {chunk_index}: {check_err}")
            print(f"⚠️ Will attempt to overwrite")
            try:
                chunk_path.unlink()
            except:
                pass
    
    # Clean up any orphaned .tmp file from previous failed upload
    if chunk_path_tmp.exists():
        print(f"⚠️ Found orphaned .tmp file for chunk {chunk_index}, removing")
        try:
            chunk_path_tmp.unlink()
        except Exception as cleanup_err:
            print(f"⚠️ Could not remove orphaned .tmp file: {cleanup_err}")
    
    try:
        # Write to temporary file first
        with open(chunk_path_tmp, "wb") as f:
            shutil.copyfileobj(file.file, f)
            # Ensure data is written to disk before proceeding
            f.flush()
            os.fsync(f.fileno())
        
        # Atomic rename - if this succeeds, chunk is guaranteed to be saved
        # If server crashes before this, client will retry
        chunk_path_tmp.rename(chunk_path)
        
        # CRITICAL: Sync the parent directory to ensure the rename is persisted
        # Without this, the directory entry might not survive a sudden server kill
        parent_dir = chunk_path.parent
        dir_fd = os.open(str(parent_dir), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        
        print(f"✓ Chunk {chunk_index} received and saved for session {session_id}")
    except Exception as e:
        print(f"❌ Error saving chunk: {e}")
        # Clean up temporary file if it exists
        if chunk_path_tmp.exists():
            chunk_path_tmp.unlink()
        raise HTTPException(status_code=500, detail="Could not write chunk to disk")

    return {"status": "chunk_received", "chunk_index": chunk_index, "session_id": session_id}

async def _verify_chunk_impl(session_id: str, chunk_index: int):
    """
    Internal implementation for chunk verification.
    Shared by both /api/verify and /upload/verify endpoints.
    
    CRITICAL: This does a deep verification including:
    1. Check file exists
    2. Check file size > 0
    3. Read first byte to ensure file is readable and data is persisted
    """
    print(f"🔍 Verify request: session={session_id}, chunk={chunk_index}")
    
    try:
        chunk_path = get_chunk_path(session_id, chunk_index)
        
        if not chunk_path.exists():
            print(f"⚠️ Chunk {chunk_index} NOT found for session {session_id} at path: {chunk_path}")
            return {"exists": False, "chunk_index": chunk_index, "session_id": session_id, "path": str(chunk_path)}
        
        # Check file size
        size = chunk_path.stat().st_size
        if size == 0:
            print(f"⚠️ Chunk {chunk_index} exists but is EMPTY (0 bytes)")
            return {"exists": False, "chunk_index": chunk_index, "session_id": session_id, "reason": "empty_file", "size": 0}
        
        # CRITICAL: Read first byte to ensure data is actually persisted to disk
        # This forces the OS to actually access the file data, not just the inode
        try:
            with open(chunk_path, "rb") as f:
                first_byte = f.read(1)
                if not first_byte:
                    print(f"⚠️ Chunk {chunk_index} exists but cannot read data")
                    return {"exists": False, "chunk_index": chunk_index, "session_id": session_id, "reason": "unreadable"}
        except Exception as read_err:
            print(f"⚠️ Chunk {chunk_index} exists but read failed: {read_err}")
            return {"exists": False, "chunk_index": chunk_index, "session_id": session_id, "reason": "read_error", "error": str(read_err)}
        
        print(f"✓ Chunk {chunk_index} verified for session {session_id} ({size} bytes, readable)")
        return {"exists": True, "chunk_index": chunk_index, "session_id": session_id, "size": size}
        
    except Exception as e:
        print(f"❌ Error verifying chunk {chunk_index} for session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        return {"exists": False, "chunk_index": chunk_index, "session_id": session_id, "error": str(e)}

@app.get("/api/verify/{session_id}/{chunk_index}")
async def verify_chunk_api(session_id: str, chunk_index: int):
    """
    Verify if a specific chunk exists on the server (new endpoint).
    Used by Service Worker to confirm chunk was actually saved before removing from queue.
    """
    return await _verify_chunk_impl(session_id, chunk_index)

@app.get("/upload/verify/{session_id}/{chunk_index}")
async def verify_chunk_legacy(session_id: str, chunk_index: int):
    """
    Legacy verify endpoint for backward compatibility with cached Service Workers.
    Redirects to same implementation as /api/verify.
    """
    print("⚠️ Using legacy /upload/verify endpoint - Service Worker should be updated")
    return await _verify_chunk_impl(session_id, chunk_index)

@app.get("/debug/session/{session_id}")
async def debug_session(session_id: str):
    """
    Debug endpoint to check which chunks have been received for a session.
    """
    validate_session_id(session_id) # Validate input

    session_dir = UPLOAD_DIR / session_id
    temp_dir = session_dir / "temp"
    
    if not temp_dir.exists():
        return {"error": "Session not found", "session_id": session_id}
    
    chunks = sorted([f for f in temp_dir.glob("*.part")], key=lambda x: int(x.stem))
    chunk_info = []
    
    for chunk in chunks:
        chunk_info.append({
            "index": int(chunk.stem),
            "size": chunk.stat().st_size,
            "path": str(chunk)
        })
    
    return {
        "session_id": session_id,
        "chunks_received": len(chunks),
        "chunk_indices": [int(c.stem) for c in chunks],
        "missing_indices": [],  # Will be filled if we know total
        "chunk_details": chunk_info
    }

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
    