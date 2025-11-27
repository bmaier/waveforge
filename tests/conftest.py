# pytest configuration for WaveForge Pro

import pytest
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def backend_root(project_root):
    """Return the backend directory."""
    return project_root / "backend"


@pytest.fixture(scope="session")
def frontend_root(project_root):
    """Return the frontend directory."""
    return project_root / "frontend"


@pytest.fixture
def temp_upload_dir(tmp_path):
    """Create a temporary upload directory for tests."""
    upload_dir = tmp_path / "uploaded_data"
    upload_dir.mkdir()
    temp_dir = upload_dir / "temp"
    temp_dir.mkdir()
    return upload_dir


@pytest.fixture
def sample_audio_blob():
    """Create a sample audio blob for testing."""
    # Create a minimal WebM audio blob (header + minimal data)
    import io
    
    # Minimal WebM header (simplified)
    webm_data = bytes([
        0x1A, 0x45, 0xDF, 0xA3,  # EBML header
        0x01, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x20,
        # ... more WebM structure would go here
    ]) + b'\x00' * 1000  # Padding
    
    return io.BytesIO(webm_data)


@pytest.fixture
async def client():
    """Create a test client for the FastAPI app."""
    from httpx import AsyncClient
    from app.server import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def uuid_generator():
    """Generate UUIDs for testing."""
    import uuid
    return lambda: str(uuid.uuid4())


# Configure pytest markers
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "asyncio: Async tests")
