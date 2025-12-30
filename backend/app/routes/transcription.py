
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from backend.app.services.transcription import transcription_service
import logging
import os
import asyncio

router = APIRouter()
logger = logging.getLogger("uvicorn")

# Configuration (should be imported from config later)
UPLOAD_DIR = os.path.abspath("backend/uploaded_data")

@router.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection for transcription accepted")
    
    try:
        # Create an iterator for the incoming audio stream
        async def audio_generator():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    if not data:
                        break
                    yield data
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected inside generator")
            except Exception as e:
                logger.error(f"Error receiving bytes: {e}")

        # Process the stream
        async for result in transcription_service.stream_transcription(audio_generator()):
            await websocket.send_json(result)
            
    except WebSocketDisconnect:
        logger.info("Client disconnected from transcription")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass

@router.post("/transcribe/{session_id}")
async def start_post_processing_transcription(session_id: str):
    """
    Triggers post-processing transcription for a completed session.
    Finds the audio file, converts if necessary (handled by service in real impl), 
    and saves the transcript.
    """
    logger.info(f"Requested transcription for session: {session_id}")
    
    # 1. Locate the file
    session_dir = os.path.join(UPLOAD_DIR, session_id, "completed")
    if not os.path.isdir(session_dir):
        # Fallback to main directory if not in completed
        session_dir = os.path.join(UPLOAD_DIR, session_id)
        if not os.path.isdir(session_dir):
            raise HTTPException(status_code=404, detail="Session directory not found")

    # Find audio file (naive approach: find first media file)
    audio_file = None
    file_format = None
    
    # Valid extensions
    valid_exts = ['.webm', '.wav', '.mp3', '.ogg', '.m4a']
    
    try:
        for file in os.listdir(session_dir):
            base, ext = os.path.splitext(file)
            if ext.lower() in valid_exts and not file.endswith('.temp'):
                audio_file = os.path.join(session_dir, file)
                file_format = ext.lower().replace('.', '')
                break
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File system access error: {str(e)}")
        
    if not audio_file:
        raise HTTPException(status_code=404, detail="No audio file found for this session")

    # 2. Perform Transcription
    try:
        result = await transcription_service.transcribe_file(audio_file, file_format)
        
        # 3. Save Transcript to file
        transcript_filename = os.path.splitext(audio_file)[0] + ".txt"
        async with asyncio.Lock(): # Simple lock if using shared resources, usually not needed for file write here
            with open(transcript_filename, "w", encoding="utf-8") as f:
                f.write(result["transcript"])
                
        return {
            "status": "success", 
            "message": "Transcription complete",
            "transcript_preview": result["transcript"][:100] + "...",
            "file_path": transcript_filename
        }
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
