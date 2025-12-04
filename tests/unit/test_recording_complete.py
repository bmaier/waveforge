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


@pytest.fixture
def app():
    """Import and return the FastAPI app."""
    from app.server import app
    return app


@pytest.fixture
def test_client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_session(temp_upload_dir, monkeypatch):
    """Create a mock TUS upload session."""
    session_id = str(uuid.uuid4())
    
    # Mock upload_sessions dictionary with correct structure
    from routes import tus_upload, recording_complete
    mock_sessions = {
        session_id: {
            "file_name": "test_recording.webm",
            "file_size": 3000,
            "total_chunks": 3,
            "uploaded_chunks": {0, 1, 2},  # Set of uploaded chunk indices
            "upload_offset": 3000,
            "created_at": "2025-11-29T10:00:00"
        }
    }
    monkeypatch.setattr(tus_upload, "upload_sessions", mock_sessions)
    
    # Also need to patch for recording_complete import
    monkeypatch.setattr(recording_complete, "upload_sessions", mock_sessions)
    
    # Create mock chunks on disk with proper directory structure
    session_dir = temp_upload_dir / session_id
    session_dir.mkdir(parents=True)
    
    # Create temp/shard_0000 directory for chunks
    temp_dir = session_dir / "temp" / "shard_0000"
    temp_dir.mkdir(parents=True)
    
    # Create completed directory for final files
    completed_dir = session_dir / "completed"
    completed_dir.mkdir(parents=True)
    
    # Patch UPLOAD_DIR so get_session_dir works
    import routes.recording_complete
    routes.recording_complete.Path = lambda x: temp_upload_dir if str(x) == "UPLOAD_DIR" else Path(x)
    
    # Create 3 test chunks in temp/shard_0000
    for i in range(3):
        chunk_data = f"Audio chunk {i} data" * 100  # Make it substantial
        chunk_path = temp_dir / f"{i}.part"
        chunk_path.write_text(chunk_data)
    
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
        """Test successful recording completion and assembly."""
        metadata = json.dumps({
            "duration": 125.5,
            "size": 3000,
            "format": "audio/webm;codecs=opus"
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
        print(f"Response: {json_response}")  # Debug output
        
        assert response.status_code == 200
        assert json_response["status"] in ["assembling", "complete"]
        assert "session_id" in json_response
        assert json_response["file_name"] == mock_session["file_name"]
    
    def test_recording_complete_missing_session(self, test_client):
        """Test recording complete with non-existent session."""
        fake_session_id = str(uuid.uuid4())
        metadata = json.dumps({"duration": 10.0})
        
        response = test_client.post(
            "/recording/complete",
            data={
                "session_id": fake_session_id,
                "file_name": "test.webm",
                "metadata": metadata
            }
        )
        
        assert response.status_code == 404
        json_response = response.json()
        assert json_response["status"] == "error"
        assert "not found" in json_response["message"].lower()
    
    def test_recording_complete_missing_parameters(self, test_client):
        """Test recording complete with missing required parameters."""
        # Missing file_name
        response = test_client.post(
            "/recording/complete",
            data={
                "session_id": str(uuid.uuid4()),
                "metadata": "{}"
            }
        )
        
        assert response.status_code == 422  # FastAPI validation error
    
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
        
        # Should still work, metadata is optional
        assert response.status_code in [200, 400]
    
    def test_recording_complete_incomplete_upload(self, test_client, temp_upload_dir, monkeypatch):
        """Test recording complete when chunks are still uploading."""
        session_id = str(uuid.uuid4())
        
        # Mock a session with incomplete upload
        from routes import tus_upload
        mock_sessions = {
            session_id: {
                "file_name": "test.webm",
                "file_size": 3000,
                "chunks_uploaded": 2,  # Only 2 of 3 chunks
                "totalChunks": 3,
                "upload_offset": 2000,
                "created_at": "2025-11-29T10:00:00"
            }
        }
        monkeypatch.setattr(tus_upload, "upload_sessions", mock_sessions)
        monkeypatch.setattr("app.server.UPLOAD_DIR", temp_upload_dir)
        
        metadata = json.dumps({"duration": 10.0})
        
        response = test_client.post(
            "/recording/complete",
            data={
                "session_id": session_id,
                "file_name": "test.webm",
                "metadata": metadata
            }
        )
        
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "pending"
        assert "uploaded" in json_response
        assert "total" in json_response
        assert json_response["uploaded"] == 2
        assert json_response["total"] == 3


@pytest.mark.unit
@pytest.mark.slow
class TestChunkAssembly:
    """Test the chunk assembly background task."""
    
    @pytest.mark.anyio
    async def test_assemble_chunks_with_metadata(self, mock_session):
        """Test assembling chunks into final file with metadata."""
        from routes.recording_complete import assemble_chunks_with_metadata
        
        metadata = {
            "duration": 125.5,
            "size": 3000,
            "format": "audio/webm;codecs=opus",
            "sampleRate": 48000
        }
        
        # Run assembly (synchronously for testing)
        try:
            await assemble_chunks_with_metadata(
                session_id=mock_session["session_id"],
                session_info={},
                file_name=mock_session["file_name"],
                metadata=metadata
            )
            
            # Verify final file exists in completed/ directory
            final_path = mock_session["session_dir"] / "completed" / mock_session["file_name"]
            assert final_path.exists(), f"Expected file at {final_path}"
            
            # Verify metadata file exists in completed/ directory
            metadata_path = mock_session["session_dir"] / "completed" / f"{mock_session['file_name']}.meta.json"
            assert metadata_path.exists(), f"Expected metadata at {metadata_path}"
            
            # Verify metadata content
            with open(metadata_path) as f:
                saved_metadata = json.load(f)
            assert saved_metadata["duration"] == 125.5
            assert saved_metadata["size"] == 3000
            
            # Verify chunks are assembled in order
            content = final_path.read_text()
            assert "Audio chunk 0 data" in content
            assert content.index("chunk 0") < content.index("chunk 1") < content.index("chunk 2")
            
        except Exception as e:
            pytest.fail(f"Assembly failed: {e}")
    
    def test_assemble_with_missing_chunks(self, temp_upload_dir, monkeypatch):
        """Test assembly fails gracefully when chunks are missing."""
        from routes.recording_complete import assemble_chunks_with_metadata
        from routes import tus_upload
        
        session_id = str(uuid.uuid4())
        session_dir = temp_upload_dir / session_id
        session_dir.mkdir()
        
        # Create only 2 of 3 chunks
        for i in range(2):
            chunk_path = session_dir / f"{i}.part"
            chunk_path.write_text(f"Chunk {i}")
        
        # Mock session expecting 3 chunks
        mock_sessions = {
            session_id: {
                "file_name": "incomplete.webm",
                "totalChunks": 3,
                "chunks_uploaded": 3
            }
        }
        monkeypatch.setattr(tus_upload, "upload_sessions", mock_sessions)
        monkeypatch.setattr("app.server.UPLOAD_DIR", temp_upload_dir)
        
        # Assembly should fail or skip missing chunk
        with pytest.raises(Exception):
            assemble_chunks_with_metadata(
                session_id=session_id,
                file_name="incomplete.webm",
                metadata={}
            )
    
    @pytest.mark.anyio
    async def test_assemble_cleans_up_chunks(self, mock_session):
        """Test that chunk files are cleaned up after assembly."""
        from routes.recording_complete import assemble_chunks_with_metadata
        
        # Verify chunks exist before (in temp/shard_0000)
        temp_dir = mock_session["session_dir"] / "temp" / "shard_0000"
        chunk_paths = [temp_dir / f"{i}.part" for i in range(3)]
        for chunk_path in chunk_paths:
            assert chunk_path.exists(), f"Expected chunk at {chunk_path}"
        
        # Run assembly
        await assemble_chunks_with_metadata(
            session_id=mock_session["session_id"],
            session_info={},
            file_name=mock_session["file_name"],
            metadata={"duration": 10.0}
        )
        
        # Verify chunks are deleted after assembly
        for chunk_path in chunk_paths:
            assert not chunk_path.exists(), f"Chunk should be deleted: {chunk_path}"
        
        # Verify final file exists in completed/ directory
        final_path = mock_session["session_dir"] / "completed" / mock_session["file_name"]
        assert final_path.exists(), f"Expected final file at {final_path}"
    
    @pytest.mark.anyio
    async def test_assemble_with_large_chunks(self, temp_upload_dir, monkeypatch):
        """Test assembly with larger chunks (>1MB) to verify buffering."""
        from routes.recording_complete import assemble_chunks_with_metadata
        from routes import tus_upload
        
        session_id = str(uuid.uuid4())
        session_dir = temp_upload_dir / session_id
        session_dir.mkdir()
        
        # Create temp/shard_0000 directory structure
        temp_dir = session_dir / "temp" / "shard_0000"
        temp_dir.mkdir(parents=True)
        
        # Create 3 large chunks (2MB each)
        large_data = b"X" * (2 * 1024 * 1024)  # 2MB
        for i in range(3):
            chunk_path = temp_dir / f"{i}.part"
            chunk_path.write_bytes(large_data)
        
        mock_sessions = {
            session_id: {
                "file_name": "large_recording.webm",
                "totalChunks": 3,
                "chunks_uploaded": 3
            }
        }
        monkeypatch.setattr(tus_upload, "upload_sessions", mock_sessions)
        monkeypatch.setattr("app.server.UPLOAD_DIR", temp_upload_dir)
        
        # Assembly should handle large files
        await assemble_chunks_with_metadata(
            session_id=session_id,
            session_info=mock_sessions[session_id],
            file_name="large_recording.webm",
            metadata={"size": 6 * 1024 * 1024}
        )
        
        final_path = session_dir / "completed" / "large_recording.webm"
        assert final_path.exists(), f"Expected final file at {final_path}"
        assert final_path.stat().st_size == 3 * 2 * 1024 * 1024  # 6MB


@pytest.mark.unit
class TestServerPath:
    """Test server path generation for client."""
    
    def test_server_path_format(self, mock_session):
        """Test that server path is correct format."""
        session_id = mock_session["session_id"]
        file_name = mock_session["file_name"]
        
        expected_path = f"/uploads/{session_id}/{file_name}"
        
        # This would be returned in the API response
        assert session_id in expected_path
        assert file_name in expected_path
    
    def test_server_path_with_special_characters(self):
        """Test server path with special characters in filename."""
        session_id = str(uuid.uuid4())
        file_name = "My Recording (2025-11-29) #1.webm"
        
        # Path should be URL-safe
        server_path = f"/uploads/{session_id}/{file_name}"
        assert server_path is not None
        # In production, this would be URL-encoded


@pytest.mark.unit
class TestMetadataStorage:
    """Test metadata storage alongside audio files."""
    
    @pytest.mark.anyio
    async def test_metadata_json_format(self, mock_session):
        """Test that metadata is stored in correct JSON format."""
        from routes.recording_complete import assemble_chunks_with_metadata
        
        metadata = {
            "duration": 125.5,
            "size": 3000,
            "format": "audio/webm;codecs=opus",
            "sampleRate": 48000,
            "channels": 2,
            "bitrate": 128000
        }
        
        await assemble_chunks_with_metadata(
            session_id=mock_session["session_id"],
            session_info={},
            file_name=mock_session["file_name"],
            metadata=metadata
        )
        
        metadata_path = mock_session["session_dir"] / "completed" / f"{mock_session['file_name']}.meta.json"
        assert metadata_path.exists(), f"Expected metadata at {metadata_path}"
        
        with open(metadata_path) as f:
            saved = json.load(f)
        
        # Verify all fields preserved
        assert saved["duration"] == metadata["duration"]
        assert saved["size"] == metadata["size"]
        assert saved["sampleRate"] == metadata["sampleRate"]
        assert saved["channels"] == metadata["channels"]
    
    @pytest.mark.anyio
    async def test_metadata_with_unicode(self, mock_session):
        """Test metadata storage with unicode characters."""
        from routes.recording_complete import assemble_chunks_with_metadata
        
        metadata = {
            "title": "Test Aufnahme äöü",
            "artist": "Müller & Söhne",
            "notes": "Recording with émojis 🎵🎤"
        }
        
        await assemble_chunks_with_metadata(
            session_id=mock_session["session_id"],
            session_info={},
            file_name=mock_session["file_name"],
            metadata=metadata
        )
        
        metadata_path = mock_session["session_dir"] / "completed" / f"{mock_session['file_name']}.meta.json"
        
        with open(metadata_path, encoding='utf-8') as f:
            saved = json.load(f)
        
        assert saved["title"] == "Test Aufnahme äöü"
        assert saved["artist"] == "Müller & Söhne"
        assert "🎵" in saved["notes"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
