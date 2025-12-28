"""
Recording Complete Endpoint
Handles recording completion signals from client and triggers server-side assembly
"""

from fastapi import APIRouter, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import json
import os
import shutil
from pathlib import Path

router = APIRouter()

# Import from tus_upload
from .tus_upload import UPLOAD_DIR

@router.get("/recordings/{session_id}/{file_name}")
async def get_recording(session_id: str, file_name: str):
    """
    Retrieve a completed recording file from the server
    
    Args:
        session_id: The unique session identifier
        file_name: The filename to retrieve
    
    Returns:
        The audio file as streaming response
    """
    file_path = UPLOAD_DIR / session_id / file_name
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Recording not found: {session_id}/{file_name}"
        )
    
    # Determine media type from extension
    ext = file_path.suffix.lower()
    media_types = {
        '.webm': 'audio/webm',
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.ogg': 'audio/ogg'
    }
    media_type = media_types.get(ext, 'application/octet-stream')
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_name
    )


@router.post("/recording/complete")
async def recording_complete(
    background_tasks: BackgroundTasks,
    session_id: str = Form(...),
    file_name: str = Form(...),
    metadata: str = Form(None)
):
    """
    Signal that recording is complete and chunks should be assembled.
    Now specifically for TUS uploads.
    """
    # Parse metadata if provided
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    # Check if session exists in TUS session info
    from .tus_upload import load_session_info, assemble_chunks
    session_info = load_session_info(session_id)
    
    if not session_info:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Fast path: if the file is already assembled, return success
    completed_dir = UPLOAD_DIR / session_id / "completed"
    output_file = completed_dir / file_name
    if output_file.exists():
        return {
            "status": "already_completed",
            "message": "Recording already assembled",
            "session_id": session_id,
            "file_name": file_name
        }
    
    # Trigger TUS assembly in background
    background_tasks.add_task(
        assemble_chunks,
        session_id,
        metadata_dict.get('name', file_name.split('.')[0]) if metadata_dict else file_name.split('.')[0],
        metadata_dict.get('extension', file_name.split('.')[-1]) if metadata_dict else file_name.split('.')[-1],
        metadata_dict or {}
    )
    
    return {
        "status": "assembling",
        "message": "Recording is being assembled on server",
        "session_id": session_id,
        "file_name": file_name
    }
