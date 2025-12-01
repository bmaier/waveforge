"""
Recording Complete Endpoint
Handles recording completion signals from client and triggers server-side assembly
"""

from fastapi import APIRouter, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import json
from pathlib import Path
import shutil

router = APIRouter()

# Import from tus_upload
from .tus_upload import upload_sessions, get_chunk_path, get_session_dir, UPLOAD_DIR

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
    session_id: str = Form(...),
    file_name: str = Form(...),
    metadata: str = Form(None)
):
    """
    Signal that recording is complete and chunks should be assembled.
    Works with BOTH TUS uploads (upload_sessions) AND Custom uploads (sharded storage).
    
    Args:
        session_id: The unique session identifier
        file_name: The desired output filename
        metadata: JSON string containing recording metadata (optional)
    
    Returns:
        Status of the assembly operation
    """
    # Parse metadata if provided
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    # Check for session in SHARDED storage (custom uploads from Service Worker)
    session_dir = UPLOAD_DIR / session_id
    temp_dir = session_dir / "temp"
    
    if not temp_dir.exists():
        # Fallback: Check if session exists in TUS upload_sessions
        if session_id not in upload_sessions:
            print(f"❌ Session not found in sharded storage OR upload_sessions: {session_id}")
            return {
                "status": "error",
                "error": "session_not_found",
                "message": f"Session {session_id} not found",
                "session_id": session_id
            }
        
        # TUS path: use old logic
        print(f"📌 Using TUS upload path for session {session_id}")
        session_info = upload_sessions[session_id]
        total = metadata_dict.get('totalChunks') if metadata_dict else session_info.get('total_chunks', 0)
        uploaded = len(session_info.get('uploaded_chunks', set()))
        
        if uploaded < total:
            return {
                "status": "pending",
                "uploaded": uploaded,
                "total": total,
                "message": f"Still uploading: {uploaded}/{total} chunks"
            }
        
        # Trigger TUS assembly in background
        from fastapi import BackgroundTasks
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            assemble_chunks_with_metadata,
            session_id,
            session_info,
            file_name,
            metadata_dict or {}
        )
        
        return {
            "status": "assembling",
            "message": "Recording is being assembled on server (TUS)",
            "session_id": session_id,
            "file_name": file_name
        }
    
    # SHARDED STORAGE PATH (Custom uploads from Service Worker)
    print(f"📌 Using sharded storage path for session {session_id}")
    
    # Check for shard directories
    shard_dirs = list(temp_dir.glob("shard_*"))
    if not shard_dirs:
        print(f"❌ No shard directories found in {temp_dir}")
        print(f"   Directory contents: {list(temp_dir.iterdir())}")
        return {
            "status": "error",
            "error": "no_chunks",
            "message": f"No chunk shards found for session {session_id}",
            "session_id": session_id,
            "temp_dir_contents": [str(p) for p in temp_dir.iterdir()]
        }
    
    print(f"✓ Found {len(shard_dirs)} shard directories")
    
    # Wait for filesystem to stabilize
    import time
    print("⏳ Waiting for all chunks to be fully written...")
    stable_count = 0
    last_chunk_count = -1
    
    for cycle in range(10):  # Max 5 seconds
        current_chunk_count = sum(1 for shard in shard_dirs for _ in shard.glob("*.part"))
        
        if current_chunk_count == last_chunk_count:
            stable_count += 1
            if stable_count >= 2:
                print(f"✓ Filesystem stable: {current_chunk_count} chunks")
                break
        else:
            stable_count = 0
            print(f"   Chunks still being written: {current_chunk_count}...")
        
        last_chunk_count = current_chunk_count
        time.sleep(0.5)
    
    # Assemble SYNCHRONOUSLY (not in background)
    try:
        result = await assemble_chunks_with_metadata(
            session_id,
            {},  # No session_info needed for sharded storage
            file_name,
            metadata_dict or {}
        )
        return {
            "status": "success",
            "message": "File assembled successfully",
            "session_id": session_id,
            "file_name": file_name
        }
    except Exception as e:
        print(f"❌ Assembly failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": "assembly_failed",
            "message": str(e),
            "session_id": session_id
        }


async def assemble_chunks_with_metadata(
    session_id: str,
    session_info: dict,
    file_name: str,
    metadata: dict
):
    """
    Assemble chunks with custom filename and metadata.
    Works with BOTH sharded storage AND legacy chunk storage.
    
    Args:
        session_id: The unique session identifier
        session_info: Session information from upload_sessions (may be empty for sharded storage)
        file_name: The desired output filename
        metadata: Recording metadata from client
    """
    try:
        recording_name = metadata.get('name', session_info.get('recording_name', 'recording') if session_info else 'recording')
        format_ext = metadata.get('extension', session_info.get('format', 'webm') if session_info else 'webm')
        
        session_dir = UPLOAD_DIR / session_id
        temp_dir = session_dir / "temp"
        completed_dir = session_dir / "completed"
        completed_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = completed_dir / file_name
        temp_file = completed_dir / f"{file_name}.tmp"
        
        # SHARDED STORAGE PATH
        if temp_dir.exists():
            print(f"🔧 Assembling from sharded storage...")
            
            # Assemble chunks in order
            file_size = 0
            chunk_info = []
            chunk_index = 0
            missing_chunks = []
            
            with open(temp_file, "wb") as outfile:
                while True:
                    chunk_path = get_chunk_path(session_id, chunk_index)
                    
                    if not chunk_path.exists():
                        # Look ahead to see if there are more chunks
                        found_more = False
                        for look_ahead in range(1, 11):
                            if get_chunk_path(session_id, chunk_index + look_ahead).exists():
                                found_more = True
                                missing_chunks.append(chunk_index)
                                break
                        
                        if not found_more:
                            break
                        else:
                            print(f"⚠️  Chunk {chunk_index} missing (gap detected)")
                            chunk_index += 1
                            continue
                    
                    # Verify chunk is not empty
                    chunk_size = chunk_path.stat().st_size
                    if chunk_size == 0:
                        print(f"⚠️  Chunk {chunk_index} is empty, skipping")
                        missing_chunks.append(chunk_index)
                        chunk_index += 1
                        continue
                    
                    # Read and append chunk
                    with open(chunk_path, "rb") as infile:
                        data = infile.read()
                        outfile.write(data)
                        file_size += len(data)
                        chunk_info.append({
                            "index": chunk_index,
                            "size": len(data)
                        })
                    
                    if chunk_index % 10 == 0:
                        print(f"  ✓ Chunk {chunk_index} appended")
                    
                    chunk_index += 1
            
            # Atomic rename
            temp_file.rename(output_file)
            
            print(f"✅ Assembled {file_name} ({file_size} bytes, {len(chunk_info)} chunks)")
            
            if missing_chunks:
                print(f"⚠️  {len(missing_chunks)} missing chunks: {missing_chunks}")
            
            # Store metadata
            metadata_path = completed_dir / f"{file_name}.meta.json"
            with open(metadata_path, 'w') as f:
                json.dump({
                    "file_name": file_name,
                    "session_id": session_id,
                    "file_size_bytes": file_size,
                    "total_chunks": len(chunk_info),
                    "missing_chunks": missing_chunks,
                    "client_metadata": metadata
                }, f, indent=2)
            
            print(f"✓ Metadata saved to {metadata_path}")
            
            # Cleanup temp directory
            shutil.rmtree(temp_dir)
            print(f"✓ Cleaned up temp directory")
            
            return output_file
        
        # LEGACY PATH (TUS upload_sessions)
        else:
            print(f"🔧 Assembling from legacy chunk storage...")
            total_chunks = metadata.get('totalChunks', session_info.get('total_chunks', 0) if session_info else 0)
            
            # Verify all chunks exist
            missing = []
            for chunk_index in range(total_chunks):
                chunk_path = get_chunk_path(session_id, chunk_index)
                if not chunk_path.exists():
                    missing.append(chunk_index)
            
            if missing:
                error_msg = f"Missing chunks: {missing}"
                print(f"❌ Assembly failed: {error_msg}")
                raise FileNotFoundError(error_msg)
            
            # Concatenate chunks
            with open(temp_file, "wb") as outfile:
                for chunk_index in range(total_chunks):
                    chunk_path = get_chunk_path(session_id, chunk_index)
                    
                    with open(chunk_path, "rb") as infile:
                        while True:
                            data = infile.read(1024 * 1024)
                            if not data:
                                break
                            outfile.write(data)
                    
                    if chunk_index % 10 == 0:
                        print(f"  ✓ Chunk {chunk_index + 1}/{total_chunks} appended")
            
            # Atomic rename
            temp_file.rename(output_file)
            
            print(f"✅ Assembled {file_name} ({output_file.stat().st_size} bytes)")
            
            # Store metadata
            metadata_path = session_dir / f"{recording_name}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✓ Metadata saved to {metadata_path}")
            
            # Cleanup chunks
            chunks_dir = session_dir / "chunks"
            if chunks_dir.exists():
                shutil.rmtree(chunks_dir)
                print(f"✓ Cleaned up {total_chunks} chunk files")
            
            # Remove from tracking
            if session_id in upload_sessions:
                del upload_sessions[session_id]
                print(f"✓ Session {session_id} removed from tracking")
            
            return output_file
        
    except Exception as e:
        print(f"❌ Assembly failed for session {session_id}: {str(e)}")
        raise
