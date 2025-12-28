"""
TUS Protocol Upload Routes
Implements tus.io resumable upload protocol for audio chunks
"""

import base64
import json
import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Header, Request, Response, HTTPException, BackgroundTasks, Form, UploadFile, File
from fastapi.responses import JSONResponse

router = APIRouter()

# Storage configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(Path(__file__).parent.parent.parent.parent / "backend" / "uploaded_data")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
print(f"📂 UPLOAD_DIR configured: {UPLOAD_DIR.absolute()}")

def get_session_info_path(session_id: str) -> Path:
    """Get path to session info JSON file"""
    return UPLOAD_DIR / session_id / "session_info.json"

def save_session_info(session_id: str, info: dict):
    """Save session info to disk"""
    path = get_session_info_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert sets to lists for JSON serialization
    serialized_info = info.copy()
    if 'uploaded_chunks' in serialized_info and isinstance(serialized_info['uploaded_chunks'], set):
        serialized_info['uploaded_chunks'] = list(serialized_info['uploaded_chunks'])
    
    with open(path, 'w') as f:
        json.dump(serialized_info, f, indent=2)

def load_session_info(session_id: str) -> Optional[dict]:
    """Load session info from disk"""
    path = get_session_info_path(session_id)
    if not path.exists():
        return None
    
    with open(path, 'r') as f:
        info = json.load(f)
    
    # Convert lists back to sets
    if 'uploaded_chunks' in info:
        info['uploaded_chunks'] = set(info['uploaded_chunks'])
    
    return info


def parse_tus_metadata(metadata_header: Optional[str]) -> dict:
    """
    Parse TUS Upload-Metadata header
    Format: key1 base64value1,key2 base64value2
    """
    if not metadata_header:
        return {}
    
    metadata = {}
    pairs = metadata_header.split(',')
    
    for pair in pairs:
        if ' ' not in pair:
            continue
        key, value = pair.strip().split(' ', 1)
        try:
            decoded_value = base64.b64decode(value).decode('utf-8')
            metadata[key] = decoded_value
        except Exception as e:
            print(f"[TUS] Error decoding metadata {key}: {e}")
            metadata[key] = value
    
    return metadata


def get_session_dir(session_id: str) -> Path:
    """Get directory for session chunks"""
    session_dir = UPLOAD_DIR / session_id / "chunks"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def get_chunk_path(session_id: str, chunk_id: str) -> Path:
    """
    Get path for specific chunk file.
    Supports both TUS chunks (chunk_{id}.bin) and sharded chunks (temp/shard_*/index.part)
    """
    # Base session directory (without /chunks/ subdirectory)
    base_session_dir = UPLOAD_DIR / session_id
    
    # Try sharded format FIRST (Service Worker uploads)
    temp_dir = base_session_dir / "temp"
    if temp_dir.exists():
        try:
            chunk_index = int(chunk_id)
            shard_num = chunk_index // 1000
            shard_dir = temp_dir / f"shard_{shard_num:04d}"
            sharded_chunk = shard_dir / f"{chunk_index}.part"
            if sharded_chunk.exists():
                return sharded_chunk
        except (ValueError, TypeError):
            pass  # Not a valid chunk index, try TUS format
    
    # Try TUS format (chunks/chunk_{id}.bin)
    session_dir = get_session_dir(session_id)  # This adds /chunks/
    tus_chunk = session_dir / f"chunk_{chunk_id}.bin"
    
    # Return TUS path (will be checked for existence by caller)
    return tus_chunk


def assemble_chunks(session_id: str, recording_name: str, format: str, client_metadata: Optional[dict] = None):
    """
    Assemble all uploaded chunks into final file
    Background task to avoid blocking response
    """
    try:
        session = load_session_info(session_id)
        if not session:
            print(f"[TUS] Session {session_id} info not found for assembly")
            return
        
        total_chunks = session.get('total_chunks', 0)
        session_dir = get_session_dir(session_id)
        
        if session.get('assembled'):
            print(f"[TUS] Session {session_id} already assembled, skipping.")
            return
        
        # Check all chunks exist
        missing_chunks = []
        for i in range(total_chunks):
            chunk_path = get_chunk_path(session_id, str(i))
            if not chunk_path.exists():
                missing_chunks.append(i)
        
        if missing_chunks:
            print(f"[TUS] Cannot assemble - missing chunks: {missing_chunks}")
            return
        
        # Assemble file in completed/ directory
        completed_dir = UPLOAD_DIR / session_id / "completed"
        completed_dir.mkdir(parents=True, exist_ok=True)
        output_file = completed_dir / f"{recording_name}.{format}"
        
        print(f"[TUS] Assembling {total_chunks} chunks into {output_file}")
        
        with open(output_file, 'wb') as outfile:
            for i in range(total_chunks):
                chunk_path = get_chunk_path(session_id, str(i))
                with open(chunk_path, 'rb') as infile:
                    shutil.copyfileobj(infile, outfile)
        
        # Create metadata file
        file_size = output_file.stat().st_size
        metadata_path = completed_dir / f"{recording_name}.{format}.meta.json"
        
        metadata = {
            "file_name": f"{recording_name}.{format}",
            "session_id": session_id,
            "file_size_bytes": file_size,
            "total_chunks": total_chunks,
            "missing_chunks": [],
            "client_metadata": client_metadata or session.get('client_metadata', {}),
            "assembled_at": datetime.now().isoformat()
        }
        
        with open(metadata_path, "w") as meta_file:
            json.dump(metadata, meta_file, indent=2)
        
        print(f"✓ Metadata saved: {metadata_path}")
        
        # Cleanup chunks and temp files
        try:
            shutil.rmtree(session_dir)
            temp_dir = UPLOAD_DIR / session_id / "temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        except Exception as cleanup_err:
            print(f"[TUS] Cleanup error: {cleanup_err}")
        
        # Update session info
        session['assembled'] = True
        session['output_file'] = str(output_file)
        session['assembled_at'] = datetime.now().isoformat()
        save_session_info(session_id, session)
        
        print(f"[TUS] Assembly complete: {output_file}")
        
    except Exception as e:
        print(f"[TUS] Error assembling chunks: {e}")
        import traceback
        traceback.print_exc()


@router.options("/files/{session_id}/chunks/")
async def chunks_options(session_id: str):
    """CORS preflight for chunk creation"""
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Upload-Metadata, Content-Type",
            "Access-Control-Max-Age": "86400"
        }
    )


@router.options("/files/{session_id}/chunks/{chunk_id}")
async def chunk_options(session_id: str, chunk_id: str):
    """CORS preflight for chunk upload"""
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Methods": "PATCH, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Upload-Offset, Content-Type, Upload-Length",
            "Access-Control-Max-Age": "86400"
        }
    )


@router.post("/files/{session_id}/chunks/")
async def create_chunk_upload(
    session_id: str,
    upload_metadata: Optional[str] = Header(None, alias="Upload-Metadata")
):
    """
    Create a new chunk upload
    Returns Location header with chunk URL and Upload-Offset
    """
    metadata = parse_tus_metadata(upload_metadata)
    
    chunk_index = int(metadata.get('chunkIndex', 0))
    total_chunks = int(metadata.get('totalChunks', 0))
    recording_name = metadata.get('recordingName', 'recording')
    format = metadata.get('format', 'webm')
    
    # Initialize session if needed
    session = load_session_info(session_id)
    if not session:
        session = {
            'total_chunks': total_chunks,
            'uploaded_chunks': set(),
            'recording_name': recording_name,
            'format': format,
            'started_at': datetime.now().isoformat(),
            'chunk_sizes': {},
            'client_metadata': metadata
        }
    else:
        # Update session info with latest metadata
        session['total_chunks'] = total_chunks
        session['recording_name'] = recording_name
        session['format'] = format
        if metadata:
            session['client_metadata'] = metadata
    
    save_session_info(session_id, session)
    chunk_id = str(chunk_index)
    chunk_path = get_chunk_path(session_id, chunk_id)
    
    # Get current upload offset (0 if new, file size if resuming)
    upload_offset = chunk_path.stat().st_size if chunk_path.exists() else 0
    
    print(f"[TUS] Created chunk upload: session={session_id}, chunk={chunk_index}/{total_chunks}, offset={upload_offset}")
    
    return Response(
        status_code=201,
        headers={
            "Location": f"/files/{session_id}/chunks/{chunk_id}",
            "Upload-Offset": str(upload_offset),
            "Tus-Resumable": "1.0.0"
        }
    )


@router.patch("/files/{session_id}/chunks/{chunk_id}")
async def upload_chunk_data(
    session_id: str,
    chunk_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    upload_offset: int = Header(0, alias="Upload-Offset"),
    content_length: Optional[int] = Header(None, alias="Content-Length")
):
    """
    Upload chunk data at specified offset
    Supports resumable uploads
    """
    session = load_session_info(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    chunk_path = get_chunk_path(session_id, chunk_id)
    
    # Verify offset matches current file size
    current_size = chunk_path.stat().st_size if chunk_path.exists() else 0
    if upload_offset != current_size:
        raise HTTPException(
            status_code=409,
            detail=f"Upload offset mismatch. Expected {current_size}, got {upload_offset}"
        )
    
    # Read and append chunk data
    chunk_data = await request.body()
    
    with open(chunk_path, 'ab') as f:
        f.write(chunk_data)
    
    new_offset = chunk_path.stat().st_size
    
    # Mark chunk as uploaded (complete)
    session['uploaded_chunks'].add(int(chunk_id))
    session['chunk_sizes'][chunk_id] = new_offset
    save_session_info(session_id, session)
    
    print(f"[TUS] Uploaded chunk data: session={session_id}, chunk={chunk_id}, offset={upload_offset}->{new_offset}")
    
    # Check if all chunks are uploaded
    if len(session['uploaded_chunks']) == session['total_chunks']:
        print(f"[TUS] All chunks uploaded for session {session_id}, triggering assembly")
        background_tasks.add_task(
            assemble_chunks,
            session_id,
            session['recording_name'],
            session['format']
        )
    
    return Response(
        status_code=204,
        headers={
            "Upload-Offset": str(new_offset),
            "Tus-Resumable": "1.0.0"
        }
    )


@router.head("/files/{session_id}/chunks/{chunk_id}")
async def check_chunk_offset(session_id: str, chunk_id: str):
    """
    Check current upload offset for resuming
    """
    session = load_session_info(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    chunk_path = get_chunk_path(session_id, chunk_id)
    upload_offset = chunk_path.stat().st_size if chunk_path.exists() else 0
    
    return Response(
        status_code=200,
        headers={
            "Upload-Offset": str(upload_offset),
            "Tus-Resumable": "1.0.0"
        }
    )


@router.get("/files/{session_id}/status")
async def get_session_status(session_id: str):
    """
    Get upload status for session
    """
    session = load_session_info(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    uploaded_chunks = list(session['uploaded_chunks'])
    total_chunks = session['total_chunks']
    
    missing_chunks = [i for i in range(total_chunks) if i not in uploaded_chunks]
    
    return JSONResponse({
        "session_id": session_id,
        "total_chunks": total_chunks,
        "uploaded_chunks": len(uploaded_chunks),
        "missing_chunks": missing_chunks,
        "assembled": session.get('assembled', False),
        "started_at": session.get('started_at'),
        "assembled_at": session.get('assembled_at'),
        "recording_name": session.get('recording_name'),
        "format": session.get('format')
    })


@router.post("/files/{session_id}/assemble")
async def trigger_assembly(
    session_id: str,
    background_tasks: BackgroundTasks
):
    """
    Manually trigger assembly of uploaded chunks
    """
    session = load_session_info(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if len(session['uploaded_chunks']) != session['total_chunks']:
        missing = session['total_chunks'] - len(session['uploaded_chunks'])
        raise HTTPException(
            status_code=400,
            detail=f"Cannot assemble - {missing} chunks missing"
        )
    
    background_tasks.add_task(
        assemble_chunks,
        session_id,
        session['recording_name'],
        session['format']
    )
    
    return JSONResponse({
        "message": "Assembly started",
        "session_id": session_id
    })


@router.delete("/files/{session_id}")
async def cancel_upload(session_id: str):
    """
    Cancel upload and cleanup chunks
    """
    if not load_session_info(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Cleanup chunks directory
    session_dir = UPLOAD_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
    
    # Remove session info file
    info_path = get_session_info_path(session_id)
    if info_path.exists():
        info_path.unlink()
    
    print(f"[TUS] Cancelled session {session_id}")
    
    return JSONResponse({
        "message": "Upload cancelled",
        "session_id": session_id
    })
@router.post("/upload/chunk")
async def upload_chunk_custom(
    background_tasks: BackgroundTasks,
    session_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    total_chunks: Optional[int] = Form(None),
    recording_name: Optional[str] = Form(None),
    format: Optional[str] = Form(None)
):
    """
    Custom upload endpoint for Service Worker.
    Uses FormData POST instead of TUS protocol.
    """
    # Use str for chunk_id in Path helpers
    chunk_id = str(chunk_index)
    chunk_path = get_chunk_path(session_id, chunk_id)
    
    # Ensure directory exists
    chunk_path.parent.mkdir(parents=True, exist_ok=True)
    
    if chunk_path.exists():
        print(f"[Custom] Chunk {chunk_index} already exists for session {session_id}")
        return JSONResponse({
            "status": "chunk_already_exists",
            "chunk_index": chunk_index,
            "session_id": session_id
        })
    
    # Save chunk data
    content = await file.read()
    with open(chunk_path, "wb") as f:
        f.write(content)
    
    size = len(content)
    print(f"[Custom] Saved chunk {chunk_index} for session {session_id} ({size} bytes)")
    
    # Update session info
    session = load_session_info(session_id)
    if not session:
        session = {
            'total_chunks': total_chunks or 0,
            'uploaded_chunks': set(),
            'recording_name': recording_name or 'recording',
            'format': format or 'webm',
            'started_at': datetime.now().isoformat(),
            'chunk_sizes': {},
            'client_metadata': {
                'recordingName': recording_name or 'recording',
                'format': format or 'webm',
                'totalChunks': total_chunks or 0
            }
        }
    else:
        # Update existing session with new info if provided
        if total_chunks: session['total_chunks'] = total_chunks
        if recording_name: session['recording_name'] = recording_name
        if format: session['format'] = format

    session['uploaded_chunks'].add(chunk_index)
    session['chunk_sizes'][chunk_id] = size
    save_session_info(session_id, session)
    
    # Check if all chunks are uploaded
    if session['total_chunks'] > 0 and len(session['uploaded_chunks']) == session['total_chunks']:
        print(f"[Custom] All chunks uploaded via custom for session {session_id}, triggering assembly")
        background_tasks.add_task(
            assemble_chunks,
            session_id,
            session['recording_name'],
            session['format']
        )

    return JSONResponse({
        "status": "chunk_received",
        "chunk_index": chunk_index,
        "session_id": session_id,
        "size": size
    })


@router.get("/api/verify/{session_id}/{chunk_index}")
async def verify_chunk(session_id: str, chunk_index: int):
    """
    Verify if a chunk exists on server.
    Used by Service Worker before removing from local queue.
    """
    chunk_id = str(chunk_index)
    chunk_path = get_chunk_path(session_id, chunk_id)
    
    if chunk_path.exists():
        size = chunk_path.stat().st_size
        return {
            "exists": True,
            "session_id": session_id,
            "chunk_index": chunk_index,
            "size": size,
            "path": str(chunk_path.relative_to(UPLOAD_DIR))
        }
    
    return {
        "exists": False,
        "session_id": session_id,
        "chunk_index": chunk_index
    }
