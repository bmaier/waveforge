import os
import shutil
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()

# 1. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Storage Configuration
UPLOAD_DIR = Path("./uploaded_data")
STATIC_DIR = Path("./static")
CHUNKS_PER_SHARD = 1000  # Max chunks per subdirectory

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

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
    session_dir = UPLOAD_DIR / session_id
    shard_num = chunk_index // CHUNKS_PER_SHARD
    shard_dir = session_dir / "temp" / f"shard_{shard_num:04d}"
    shard_dir.mkdir(parents=True, exist_ok=True)
    return shard_dir / f"{chunk_index}.part{temp_suffix}"

# 3. File Assembly Logic
def assemble_file(session_id: str, file_name: str, metadata: dict = None):
    """
    Background task to assemble chunks into the final file with metadata.
    Called when client signals recording is complete.
    Handles sharded directory structure efficiently.
    """
    session_dir = UPLOAD_DIR / session_id
    temp_dir = session_dir / "temp"
    completed_dir = session_dir / "completed"
    
    # Check if temp directory exists
    if not temp_dir.exists():
        print(f"⚠ No temp directory found for session {session_id}")
        print(f"   This usually means chunks haven't been uploaded yet or wrong session ID")
        return

    print(f"🔧 Assembling {file_name} for session {session_id}...")
    
    # Create completed directory
    completed_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the original file name
    final_path = completed_dir / file_name
    metadata_path = completed_dir / f"{file_name}.meta.json"
    
    try:
        # Assemble file by reading chunks in order
        file_size = 0
        chunk_info = []
        chunk_index = 0
        missing_chunks = []
        
        with open(final_path, "wb") as outfile:
            while True:
                chunk_path = get_chunk_path(session_id, chunk_index)
                
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
                        print(f"⚠ Chunk {chunk_index} missing (gap detected)")
                        chunk_index += 1
                        continue
                
                # Read and append chunk
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
        
        if missing_chunks:
            print(f"⚠ Assembly completed with {len(missing_chunks)} missing chunks: {missing_chunks}")
        else:
            print(f"✓ Assembly completed successfully with {len(chunk_info)} chunks")
        
        # Create metadata file
        meta_info = {
            "file_name": file_name,
            "session_id": session_id,
            "file_size_bytes": file_size,
            "total_chunks": len(chunk_info),
            "missing_chunks": missing_chunks if missing_chunks else [],
            "recording_completed_at": metadata.get("recordingCompletedAt") if metadata else None,
            "upload_completed_at": datetime.now().isoformat(),
            "mime_type": metadata.get("mimeType") if metadata else "audio/webm",
            "extension": metadata.get("extension") if metadata else file_name.split(".")[-1],
            "duration_seconds": metadata.get("duration") if metadata else None,
            "sample_rate": metadata.get("sampleRate") if metadata else None,
            "chunk_details": chunk_info,
            "client_metadata": metadata or {}
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

# 4. API Endpoints
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
    # Use sharded path - automatically creates shard directory if needed
    chunk_path = get_chunk_path(session_id, chunk_index)
    chunk_path_tmp = get_chunk_path(session_id, chunk_index, temp_suffix=".tmp")
    
    # Check if chunk already exists (idempotency - allow retries)
    if chunk_path.exists():
        print(f"⏩ Chunk {chunk_index} already exists for session {session_id}, skipping")
        return {"status": "chunk_already_exists", "chunk_index": chunk_index, "session_id": session_id}
    
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
        
        print(f"✓ Chunk {chunk_index} received and saved for session {session_id}")
    except Exception as e:
        print(f"❌ Error saving chunk: {e}")
        # Clean up temporary file if it exists
        if chunk_path_tmp.exists():
            chunk_path_tmp.unlink()
        raise HTTPException(status_code=500, detail="Could not write chunk to disk")

    return {"status": "chunk_received", "chunk_index": chunk_index, "session_id": session_id}

@app.get("/debug/session/{session_id}")
async def debug_session(session_id: str):
    """
    Debug endpoint to check which chunks have been received for a session.
    """
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

@app.post("/recording/complete")
async def recording_complete(
    background_tasks: BackgroundTasks,
    session_id: str = Form(...),
    file_name: str = Form(...),
    metadata: str = Form(None)
):
    """
    Called when recording is complete on the client.
    Triggers assembly of all chunks for this session.
    """
    print(f"📢 Recording complete signal received for session {session_id}")
    
    # Parse metadata if provided
    meta_dict = None
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except Exception as e:
            print(f"⚠ Could not parse metadata: {e}")
    
    # Trigger assembly in background
    background_tasks.add_task(assemble_file, session_id, file_name, meta_dict)
    
    return {"status": "assembly_queued", "session_id": session_id, "file_name": file_name}

# Explicit route for manifest.json (before static mount)
@app.get("/manifest.json")
async def serve_manifest():
    """Serve manifest.json for PWA support"""
    from fastapi.responses import FileResponse
    manifest_path = STATIC_DIR / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")
    return FileResponse(manifest_path, media_type="application/json")

# 5. Frontend Serving
# This mounts the 'static' directory to root.
# Ensure 'index.html' and 'sw.js' are inside the 'static' folder.
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("--- WAVEFORGE SERVER ---")
    print(f"Serving Static: {STATIC_DIR.absolute()}")
    print(f"Storage Path:   {UPLOAD_DIR.absolute()}")
    print("Running on http://localhost:8000")
    
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
    