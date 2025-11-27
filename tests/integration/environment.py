"""
Behave environment configuration for WaveForge Pro integration tests.

This module sets up the test environment before and after test runs.
"""

import os
from pathlib import Path


def before_all(context):
    """Setup before all tests run."""
    # Set base URL for API calls
    context.base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
    
    # Set project root
    context.project_root = Path(__file__).parent.parent.parent.parent
    
    # Initialize test state
    context.saved_recordings = []
    context.is_recording = False
    context.recording_chunks = []
    
    print(f"Running integration tests against: {context.base_url}")


def before_scenario(context, scenario):
    """Setup before each scenario."""
    # Reset state for each scenario
    context.saved_recordings = []
    context.is_recording = False
    context.recording_chunks = []
    context.recording_start_time = None
    context.recording_duration = 0
    context.save_dialog_visible = False
    context.recording_saved = False
    context.upload_success = False
    context.orphaned_session = None
    context.recovery_modal_visible = False


def after_scenario(context, scenario):
    """Cleanup after each scenario."""
    # Cleanup any test data
    if hasattr(context, 'temp_files'):
        for file_path in context.temp_files:
            if Path(file_path).exists():
                Path(file_path).unlink()


def after_all(context):
    """Cleanup after all tests."""
    print("Integration tests complete")
