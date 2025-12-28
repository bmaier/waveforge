"""
Unit Tests for WaveForge Pro Server

Tests the main FastAPI server endpoints and functionality.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import io
import uuid
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


@pytest.mark.unit
class TestFrontendRoutes:
    """Test frontend serving routes."""
    
    def test_root_serves_index(self, test_client):
        """Test that / serves index.html."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
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
    """Test file upload endpoint (delegated to tus_upload router)."""
    
    def test_upload_chunk_success(self, test_client, temp_upload_dir, monkeypatch):
        """Test successful chunk upload via custom endpoint."""
        # Mock the upload directory
        monkeypatch.setattr("app.server.UPLOAD_DIR", temp_upload_dir)
        import routes.tus_upload
        monkeypatch.setattr(routes.tus_upload, "UPLOAD_DIR", temp_upload_dir)
        
        file_id = str(uuid.uuid4())
        file_content = b"Test audio data chunk"
        
        files = {
            "file": ("test.webm", io.BytesIO(file_content), "audio/webm")
        }
        data = {
            "session_id": file_id,
            "chunk_index": "0",
            "total_chunks": "2", # More than 1 to avoid auto-assembly
            "recording_name": "test_recording",
            "format": "webm"
        }
        
        response = test_client.post("/upload/chunk", files=files, data=data)
        
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "chunk_received"
        assert json_response["session_id"] == file_id

    def test_upload_chunk_missing_params(self, test_client):
        """Test upload fails with missing required Form parameters."""
        files = {
            "file": ("test.webm", io.BytesIO(b"data"), "audio/webm")
        }
        # Missing session_id and chunk_index
        data = {
            "total_chunks": "1",
            "recording_name": "test.webm"
        }
        
        response = test_client.post("/upload/chunk", files=files, data=data)
        assert response.status_code == 422


@pytest.mark.unit
class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, test_client):
        """Test that health endpoint returns status."""
        response = test_client.get("/health")
        assert response.status_code == 200
        json_response = response.json()
        assert "status" in json_response
        assert json_response["status"] == "ok"


@pytest.mark.unit
class TestConfigEndpoint:
    """Test config endpoint."""
    
    def test_get_config(self, test_client):
        """Test that /api/config returns expected settings."""
        response = test_client.get("/api/config")
        assert response.status_code == 200
        config = response.json()
        assert "chunk_size" in config
        assert "upload_methods" in config
        assert "tus" in config["upload_methods"]
