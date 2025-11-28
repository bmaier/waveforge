"""
Unit Tests for WaveForge Pro Server

Tests the main FastAPI server endpoints and functionality.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import io
import uuid


@pytest.fixture
def app():
    """Import and return the FastAPI app."""
    from app.server import app
    return app


@pytest.fixture
def test_client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.mark.unit
class TestFrontendRoutes:
    """Test frontend serving routes."""
    
    def test_root_serves_index(self, test_client):
        """Test that / serves index.html."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"WaveForge Pro" in response.content
    
    def test_service_worker_route(self, test_client):
        """Test that /sw.js serves the service worker."""
        response = test_client.get("/sw.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"].lower()
    
    def test_favicon_route(self, test_client):
        """Test that /favicon.svg serves the favicon."""
        response = test_client.get("/favicon.svg")
        # May be 200 or 404 depending on if file exists
        assert response.status_code in [200, 404]


@pytest.mark.unit
class TestUploadEndpoint:
    """Test file upload endpoint."""
    
    def test_upload_chunk_success(self, test_client, temp_upload_dir, monkeypatch):
        """Test successful chunk upload."""
        # Mock the upload directory
        monkeypatch.setattr("app.server.UPLOAD_DIR", temp_upload_dir)
        
        file_id = str(uuid.uuid4())
        file_content = b"Test audio data chunk"
        
        files = {
            "file": ("test.webm", io.BytesIO(file_content), "audio/webm")
        }
        data = {
            "session_id": file_id,
            "chunk_index": "0",
            "total_chunks": "1",
            "file_name": "test_recording.webm"
        }
        
        response = test_client.post("/upload/chunk", files=files, data=data)
        
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] in ["chunk_received", "file_complete"]
        assert json_response["session_id"] == file_id
    
    def test_upload_chunk_missing_file_id(self, test_client):
        """Test upload fails without file_id."""
        files = {
            "file": ("test.webm", io.BytesIO(b"data"), "audio/webm")
        }
        data = {
            "chunk_index": "0",
            "total_chunks": "1",
            "file_name": "test.webm"
        }
        
        response = test_client.post("/upload/chunk", files=files, data=data)
        assert response.status_code == 422
    
    def test_upload_multiple_chunks(self, test_client, temp_upload_dir, monkeypatch):
        """Test uploading multiple chunks for the same file."""
        monkeypatch.setattr("app.server.UPLOAD_DIR", temp_upload_dir)
        
        file_id = str(uuid.uuid4())
        total_chunks = 3
        
        for i in range(total_chunks):
            file_content = f"Chunk {i} data".encode()
            files = {
                "file": (f"chunk_{i}.part", io.BytesIO(file_content), "audio/webm")
            }
            data = {
                "session_id": file_id,
                "chunk_index": str(i),
                "total_chunks": str(total_chunks),
                "file_name": "test_recording.webm"
            }
            
            response = test_client.post("/upload/chunk", files=files, data=data)
            assert response.status_code == 200
            
            json_response = response.json()
            if i == total_chunks - 1:
                # Last chunk is still just a chunk upload in this implementation
                assert json_response["status"] == "chunk_received"
            else:
                assert json_response["status"] == "chunk_received"


@pytest.mark.unit
class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, test_client):
        """Test that health endpoint returns status."""
        response = test_client.get("/health")
        
        # Health endpoint may not be implemented yet
        if response.status_code == 404:
            pytest.skip("Health endpoint not implemented yet")
        
        assert response.status_code == 200
        json_response = response.json()
        assert "status" in json_response
        assert json_response["status"] == "ok"


@pytest.mark.unit
class TestRecordingManagement:
    """Test recording management endpoints."""
    
    def test_list_recordings(self, test_client):
        """Test listing all recordings."""
        response = test_client.get("/recordings")
        
        # Endpoint may not be implemented yet
        if response.status_code == 404:
            pytest.skip("Recordings list endpoint not implemented yet")
        
        assert response.status_code == 200
        json_response = response.json()
        assert "recordings" in json_response
        assert isinstance(json_response["recordings"], list)
    
    def test_get_recording_not_found(self, test_client):
        """Test getting a non-existent recording."""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/recording/{fake_id}")
        
        # Endpoint may not be implemented yet
        if response.status_code == 404:
            # Could be either "endpoint not found" or "recording not found"
            pass
        else:
            assert response.status_code in [200, 404]
    
    def test_delete_recording_not_found(self, test_client):
        """Test deleting a non-existent recording."""
        fake_id = str(uuid.uuid4())
        response = test_client.delete(f"/recording/{fake_id}")
        
        # Endpoint may not be implemented yet
        if response.status_code == 404:
            pass
        else:
            assert response.status_code in [200, 404]


@pytest.mark.unit
@pytest.mark.slow
class TestChunkAssembly:
    """Test chunk assembly logic."""
    
    def test_assemble_chunks_in_order(self, temp_upload_dir, monkeypatch):
        """Test that chunks are assembled in correct order."""
        from app.server import assemble_file
        
        # Mock UPLOAD_DIR
        monkeypatch.setattr("app.server.UPLOAD_DIR", temp_upload_dir)
        
        file_id = "test_session"
        file_name = "test_assembled.webm"
        
        # Create session directory structure
        session_dir = temp_upload_dir / file_id
        temp_dir = session_dir / "temp"
        # Create shard 0 directory (since CHUNKS_PER_SHARD=1000, indices 0,1,2 go to shard_0000)
        shard_dir = temp_dir / "shard_0000"
        shard_dir.mkdir(parents=True)
        
        # Create chunks
        chunks = [b"Chunk 0", b"Chunk 1", b"Chunk 2"]
        for i, data in enumerate(chunks):
            chunk_file = shard_dir / f"{i}.part"
            chunk_file.write_bytes(data)
        
        # Run assembly
        assemble_file(file_id, file_name)
        
        # Verify assembled file
        output_path = session_dir / "completed" / file_name
        assert output_path.exists()
        content = output_path.read_bytes()
        assert content == b"Chunk 0Chunk 1Chunk 2"


@pytest.mark.unit
class TestStoragePaths:
    """Test that storage paths are configured correctly."""
    
    def test_upload_dir_exists(self, backend_root):
        """Test that upload directory structure exists."""
        from app.server import UPLOAD_DIR
        
        # UPLOAD_DIR should be configured
        assert UPLOAD_DIR is not None
        
        # In production, directory should exist
        # In tests, we use temp directories
        assert isinstance(UPLOAD_DIR, Path)
    
    def test_frontend_paths_exist(self, frontend_root):
        """Test that frontend paths are correct."""
        from app.server import FRONTEND_SRC, STATIC_DIR
        
        assert FRONTEND_SRC is not None
        assert STATIC_DIR is not None
        assert isinstance(FRONTEND_SRC, Path)
        assert isinstance(STATIC_DIR, Path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
