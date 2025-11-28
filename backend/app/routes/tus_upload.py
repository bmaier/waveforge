"""
TUS Protocol Upload Routes
Implements tus.io resumable upload protocol for audio chunks
"""

import base64
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Header, Request, Response, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

router = APIRouter()

# Session tracking
upload_sessions: Dict[str, dict] = {}

# Storage configuration
UPLOAD_DIR = Path("backend/uploaded_data")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
    """Get path for specific chunk file"""
    session_dir = get_session_dir(session_id)
    return session_dir / f"chunk_{chunk_id}.bin"


def assemble_chunks(session_id: str, recording_name: str, format: str):
    """
    Assemble all uploaded chunks into final file
    Background task to avoid blocking response
    """
    try:
        session = upload_sessions.get(session_id)
        if not session:
            print(f"[TUS] Session {session_id} not found for assembly")
            return
        
        total_chunks = session.get('total_chunks', 0)
        session_dir = get_session_dir(session_id)
        
        # Check all chunks exist
        missing_chunks = []
        for i in range(total_chunks):
            chunk_path = session_dir / f"chunk_{i}.bin"
            if not chunk_path.exists():
                missing_chunks.append(i)
        
        if missing_chunks:
            print(f"[TUS] Cannot assemble - missing chunks: {missing_chunks}")
            return
        
        # Assemble file
        output_file = UPLOAD_DIR / session_id / f"{recording_name}.{format}"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"[TUS] Assembling {total_chunks} chunks into {output_file}")
        
        with open(output_file, 'wb') as outfile:
            for i in range(total_chunks):
                chunk_path = session_dir / f"chunk_{i}.bin"
                with open(chunk_path, 'rb') as infile:
                    shutil.copyfileobj(infile, outfile)
        
        # Cleanup chunks after successful assembly
        shutil.rmtree(session_dir)
        
        # Update session
        upload_sessions[session_id]['assembled'] = True
        upload_sessions[session_id]['output_file'] = str(output_file)
        upload_sessions[session_id]['assembled_at'] = datetime.now().isoformat()
        
        print(f"[TUS] Assembly complete: {output_file}")
        
    except Exception as e:
        print(f"[TUS] Error assembling chunks: {e}")


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
    if session_id not in upload_sessions:
        upload_sessions[session_id] = {
            'total_chunks': total_chunks,
            'uploaded_chunks': set(),
            'recording_name': recording_name,
            'format': format,
            'started_at': datetime.now().isoformat(),
            'chunk_sizes': {}
        }
    
    session = upload_sessions[session_id]
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
    if session_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = upload_sessions[session_id]
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
    if session_id not in upload_sessions:
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
    if session_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = upload_sessions[session_id]
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
    if session_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = upload_sessions[session_id]
    
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
    if session_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Cleanup chunks directory
    session_dir = UPLOAD_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
    
    # Remove session
    del upload_sessions[session_id]
    
    print(f"[TUS] Cancelled session {session_id}")
    
    return JSONResponse({
        "message": "Upload cancelled",
        "session_id": session_id
    })
