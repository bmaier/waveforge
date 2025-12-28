"""
Integration Tests for Hybrid TUS Upload System

Tests the complete flow from chunk upload to assembly,
including online/offline scenarios and recovery.
"""

import pytest
import asyncio
import json
from pathlib import Path
from fastapi.testclient import TestClient
import uuid
import time
from datetime import datetime


@pytest.fixture
def app():
    """Import and return the FastAPI app with disabled TrustedHostMiddleware for testing."""
    from app.server import app
    # Remove TrustedHostMiddleware for tests
    app.user_middleware = [m for m in app.user_middleware if "TrustedHost" not in str(m)]
    app.middleware_stack = None  # Force rebuild
    app.build_middleware_stack()
    return app


@pytest.fixture
def test_client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app, base_url="http://testserver")


@pytest.fixture
def session_manager(temp_upload_dir, monkeypatch):
    """Setup session management for tests."""
    from routes import tus_upload, recording_complete
    from routes.tus_upload import save_session_info
    
    # Patch UPLOAD_DIR in all modules
    monkeypatch.setattr("app.server.UPLOAD_DIR", temp_upload_dir)
    monkeypatch.setattr(tus_upload, "UPLOAD_DIR", temp_upload_dir)
    monkeypatch.setattr(recording_complete, "UPLOAD_DIR", temp_upload_dir)
    
    # Return helper to create sessions
    def create_session(session_id, total_chunks=3, recording_name=None):
        name = recording_name or f"recording_{session_id[:8]}"
        session_info = {
            "recording_name": name,
            "format": "webm",
            "total_chunks": total_chunks,
            "uploaded_chunks": set(),
            "started_at": datetime.now().isoformat(),
            "chunk_sizes": {},
            "client_metadata": {}
        }
        
        save_session_info(session_id, session_info)
        
        session_dir = temp_upload_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        return session_id
    
    return create_session


@pytest.mark.integration
class TestOnlineRecordingFlow:
    """Test complete online recording flow: record → upload chunks → server assembly."""
    
    def test_complete_online_flow(self, test_client, session_manager, temp_upload_dir):
        """Test full flow from chunk upload to server assembly."""
        session_id = str(uuid.uuid4())
        recording_name = f"my_recording_{session_id[:8]}"
        session_manager(session_id, total_chunks=3, recording_name=recording_name)
        
        # Step 1: Upload all chunks via custom endpoint (Service Worker path)
        for i in range(3):
            chunk_data = f"Audio data for chunk {i}" * 50
            response = test_client.post(
                "/upload/chunk",
                data={
                    "session_id": session_id,
                    "chunk_index": i,
                    "total_chunks": 3,
                    "recording_name": recording_name,
                    "format": "webm"
                },
                files={"file": ("chunk.part", chunk_data.encode())}
            )
            assert response.status_code == 200
        
        # Step 2: Signal recording complete
        metadata = json.dumps({
            "name": recording_name,
            "extension": "webm",
            "duration": 45.5
        })
        
        response = test_client.post(
            "/recording/complete",
            data={
                "session_id": session_id,
                "file_name": f"{recording_name}.webm",
                "metadata": metadata
            }
        )
        
        # Step 3: Verify response
        assert response.status_code == 200
        json_response = response.json()
        # It could be "assembling" if background task hasn't finished, 
        # or "already_completed" if it finished during the last chunk upload
        assert json_response["status"] in ["assembling", "already_completed"]
        
        # Step 4: Verify final file exists in completed/ directory
        final_path = temp_upload_dir / session_id / "completed" / f"{recording_name}.webm"
        assert final_path.exists(), f"Final file not found at {final_path}"
        
        # Verify metadata
        assert (temp_upload_dir / session_id / "completed" / f"{recording_name}.webm.meta.json").exists()

    def test_custom_upload_idempotency(self, test_client, session_manager):
        """Test that custom upload handles duplicate chunks WITHOUT triggering assembly prematurely."""
        session_id = str(uuid.uuid4())
        # Use 2 chunks so assembly isn't triggered after the first one
        session_manager(session_id, total_chunks=2)
        
        chunk_data = b"Some audio data"
        
        # First upload
        test_client.post(
            "/upload/chunk",
            data={"session_id": session_id, "chunk_index": 0, "total_chunks": 2},
            files={"file": ("chunk.part", chunk_data)}
        )
        
        # Second upload of same chunk
        response = test_client.post(
            "/upload/chunk",
            data={"session_id": session_id, "chunk_index": 0, "total_chunks": 2},
            files={"file": ("chunk.part", chunk_data)}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "chunk_already_exists"

    def test_verify_endpoint(self, test_client, session_manager, temp_upload_dir):
        """Test the verify endpoint used by SW."""
        session_id = str(uuid.uuid4())
        # Use 2 chunks so assembly isn't triggered immediately
        session_manager(session_id, total_chunks=2)
        
        # Before upload
        response = test_client.get(f"/api/verify/{session_id}/0")
        assert not response.json()["exists"]
        
        # Upload chunk
        test_client.post(
            "/upload/chunk",
            data={"session_id": session_id, "chunk_index": 0, "total_chunks": 2},
            files={"file": ("chunk.part", b"data")}
        )
        
        # After upload
        response = test_client.get(f"/api/verify/{session_id}/0")
        assert response.json()["exists"]


@pytest.mark.integration
class TestTUSFlow:
    """Test standard TUS protocol flow."""
    
    def test_tus_upload_flow(self, test_client, session_manager, temp_upload_dir):
        """Test TUS creation and patch flow."""
        session_id = str(uuid.uuid4())
        
        # Step 1: Create upload (POST)
        # chunkIndex=0, totalChunks=3, recordingName=test, format=webm
        metadata = "chunkIndex MC==,totalChunks Mw==,recordingName dGVzdA==,format d2VibQ=="
        response = test_client.post(
            f"/files/{session_id}/chunks/",
            headers={"Upload-Metadata": metadata}
        )
        assert response.status_code == 201
        location = response.headers["Location"]
        assert f"/files/{session_id}/chunks/0" in location
        
        # Step 2: Upload data (PATCH)
        chunk_data = b"Audio data for TUS chunk"
        patch_response = test_client.patch(
            location,
            content=chunk_data,
            headers={"Upload-Offset": "0", "Content-Length": str(len(chunk_data))}
        )
        assert patch_response.status_code == 204
        assert patch_response.headers["Upload-Offset"] == str(len(chunk_data))
        
        # Verify chunk file on disk
        chunk_file = temp_upload_dir / session_id / "chunks" / "chunk_0.bin"
        assert chunk_file.exists()
        assert chunk_file.read_bytes() == chunk_data
