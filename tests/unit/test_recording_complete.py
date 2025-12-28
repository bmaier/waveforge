"""
Unit Tests for Recording Complete Endpoint

Tests the /recording/complete endpoint and server-side assembly logic.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import uuid
import shutil
from datetime import datetime


@pytest.fixture
def app():
    """Import and return the FastAPI app."""
    from app.server import app
    return app


@pytest.fixture
def test_client(app):
    """Create a test client for the FastAPI app."""
    # Disable TrustedHostMiddleware for testing
    app.user_middleware = [
        m for m in app.user_middleware 
        if m.cls.__name__ != "TrustedHostMiddleware"
    ]
    app.middleware_stack = None  # Force rebuild
    app.build_middleware_stack()
    
    return TestClient(app, base_url="http://testserver")


@pytest.fixture
def mock_session(temp_upload_dir, monkeypatch):
    """Create a mock TUS upload session."""
    session_id = str(uuid.uuid4())
    
    # Import routes to patch
    import routes.recording_complete
    import routes.tus_upload
    from routes.tus_upload import save_session_info
    
    # Patch UPLOAD_DIR to use temp directory
    monkeypatch.setattr(routes.recording_complete, "UPLOAD_DIR", temp_upload_dir)
    monkeypatch.setattr(routes.tus_upload, "UPLOAD_DIR", temp_upload_dir)
    monkeypatch.setattr("app.server.UPLOAD_DIR", temp_upload_dir)
    
    session_info = {
        "recording_name": "test_recording",
        "format": "webm",
        "total_chunks": 3,
        "uploaded_chunks": {0, 1, 2},
        "started_at": datetime.now().isoformat(),
        "chunk_sizes": {"0": 1000, "1": 1000, "2": 1000},
        "client_metadata": {}
    }
    
    # Save session info to disk
    save_session_info(session_id, session_info)
    
    # Create chunks on disk using TUS naming (chunk_{id}.bin)
    session_dir = temp_upload_dir / session_id
    chunks_dir = session_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    
    for i in range(3):
        chunk_path = chunks_dir / f"chunk_{i}.bin"
        chunk_path.write_text(f"Audio chunk {i} data" * 100)
    
    return {
        "session_id": session_id,
        "session_dir": session_dir,
        "file_name": "test_recording.webm",
        "chunks": 3
    }


@pytest.mark.unit
class TestRecordingCompleteEndpoint:
    """Test the /recording/complete endpoint."""
    
    def test_recording_complete_success(self, test_client, mock_session):
        """Test successful recording completion and assembly trigger."""
        metadata = json.dumps({
            "name": "test_recording",
            "extension": "webm",
            "duration": 125.5
        })
        
        response = test_client.post(
            "/recording/complete",
            data={
                "session_id": mock_session["session_id"],
                "file_name": mock_session["file_name"],
                "metadata": metadata
            }
        )
        
        json_response = response.json()
        assert response.status_code == 200
        assert json_response["status"] == "assembling"
        assert json_response["session_id"] == mock_session["session_id"]
        assert json_response["file_name"] == mock_session["file_name"]
    
    def test_recording_complete_already_assembled(self, test_client, mock_session):
        """Test behavior when file is already assembled."""
        # Create the completed file
        completed_dir = mock_session["session_dir"] / "completed"
        completed_dir.mkdir(parents=True, exist_ok=True)
        output_file = completed_dir / mock_session["file_name"]
        output_file.write_text("already assembled content")
        
        response = test_client.post(
            "/recording/complete",
            data={
                "session_id": mock_session["session_id"],
                "file_name": mock_session["file_name"],
                "metadata": "{}"
            }
        )
        
        json_response = response.json()
        assert response.status_code == 200
        assert json_response["status"] == "already_completed"
    
    def test_recording_complete_missing_session(self, test_client):
        """Test recording complete with non-existent session."""
        fake_session_id = str(uuid.uuid4())
        
        response = test_client.post(
            "/recording/complete",
            data={
                "session_id": fake_session_id,
                "file_name": "test.webm",
                "metadata": "{}"
            }
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_recording_complete_invalid_metadata(self, test_client, mock_session):
        """Test recording complete with invalid JSON metadata."""
        response = test_client.post(
            "/recording/complete",
            data={
                "session_id": mock_session["session_id"],
                "file_name": "test.webm",
                "metadata": "not valid json"
            }
        )
        
        assert response.status_code == 400
        assert "invalid metadata" in response.json()["detail"].lower()


@pytest.mark.unit
class TestChunkAssembly:
    """Test the chunk assembly logic in tus_upload."""
    
    def test_assemble_chunks_tus(self, mock_session):
        """Test assembling TUS chunks."""
        from routes.tus_upload import assemble_chunks
        
        # Run assembly synchronously for testing
        assemble_chunks(
            session_id=mock_session["session_id"],
            recording_name="test_recording",
            format="webm"
        )
        
        # Verify final file
        final_path = mock_session["session_dir"] / "completed" / "test_recording.webm"
        assert final_path.exists()
        
        # Verify metadata
        meta_path = mock_session["session_dir"] / "completed" / "test_recording.webm.meta.json"
        assert meta_path.exists()
        
        # Verify cleanup (chunks dir should be gone)
        assert not (mock_session["session_dir"] / "chunks").exists()

    def test_assemble_chunks_sharded(self, temp_upload_dir, monkeypatch):
        """Test assembling sharded chunks (sw path)."""
        session_id = str(uuid.uuid4())
        
        import routes.tus_upload
        from routes.tus_upload import save_session_info
        monkeypatch.setattr(routes.tus_upload, "UPLOAD_DIR", temp_upload_dir)
        
        session_dir = temp_upload_dir / session_id
        temp_dir = session_dir / "temp" / "shard_0000"
        temp_dir.mkdir(parents=True)
        
        # Create sharded chunks
        for i in range(3):
            chunk_path = temp_dir / f"{i}.part"
            chunk_path.write_text(f"Shard {i} data")
            
        session_info = {
            "recording_name": "sharded_test",
            "format": "webm",
            "total_chunks": 3,
            "uploaded_chunks": {0, 1, 2}
        }
        save_session_info(session_id, session_info)
        
        from routes.tus_upload import assemble_chunks
        assemble_chunks(session_id, "sharded_test", "webm")
        
        final_path = session_dir / "completed" / "sharded_test.webm"
        assert final_path.exists()
        assert final_path.read_text() == "Shard 0 dataShard 1 dataShard 2 data"
        
        # Verify temp dir cleanup
        assert not (session_dir / "temp").exists()
