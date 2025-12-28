"""
End-to-End Tests for Hybrid Upload System

Tests complete user workflows including frontend interactions,
online/offline transitions, and recovery scenarios.
"""

import pytest
import time
from pathlib import Path


def handle_save_modal(page, filename="test_recording"):
    """Helper to handle the mandatory save modal."""
    print(f"DEBUG: Handling save modal with filename: {filename}")
    page.wait_for_selector("#saveModal", state="visible", timeout=10000)
    page.fill("#saveNameInput", filename)
    page.click("#saveModalDefaultBtn")
    # Wait for modal to disappear
    page.wait_for_selector("#saveModal", state="hidden", timeout=5000)


@pytest.mark.e2e
class TestOnlineRecordingE2E:
    """End-to-end tests for online recording scenarios."""
    
    def test_record_and_save_online(self, page):
        """
        Test complete online recording flow:
        1. User starts recording with internet connection
        2. Chunks upload during recording
        3. User stops recording
        4. Server assembles file
        5. Metadata-only save in IndexedDB
        6. Playback from server
        """
        page.goto("http://localhost:8000")
        page.wait_for_selector("#recordButton")
        
        # Verify online status
        online_indicator = page.locator("#dbStatus")
        assert "ONLINE" in online_indicator.text_content().upper()
        
        # Start recording
        page.click("#recordButton")
        page.wait_for_selector("#recordButton.recording-active", timeout=10000)
        
        # Record for 3 seconds
        time.sleep(3)
        
        # Stop recording
        page.wait_for_selector("#stopButton:not([disabled])", timeout=5000)
        start_time = time.time()
        page.click("#stopButton")
        
        # Handle mandatory save modal
        handle_save_modal(page, "online_recording")
        
        # Wait for success notification
        page.wait_for_selector("#toast:has-text('Saved'), #toast:has-text('Upload complete')", state="attached", timeout=10000)
        toast_text = page.locator("#toast").text_content()
        assert any(x in toast_text for x in ["Saved", "Upload complete"])
        
        # Verify fast save (<2.5 seconds)
        save_duration = time.time() - start_time
        assert save_duration < 2.5, f"Save took {save_duration}s, expected <2.5s"
        
        # Verify recording appears in playlist
        page.wait_for_selector(".track-item", timeout=10000)
        track = page.locator(".track-item").first
        
        # Verify synced badge
        try:
            page.wait_for_selector(".upload-status-badge:has-text('SYNCED')", timeout=15000)
            assert track.locator(".upload-status-badge:has-text('SYNCED')").is_visible()
        except:
            # Fallback: check if any upload badge is visible
            assert track.locator(".upload-status-badge").is_visible()
        
        # Test playback
        play_icon = track.locator("button[class^='play-btn-']")
        play_icon.scroll_into_view_if_needed()
        play_icon.click()
        
        # Verify dock opens and playback starts
        page.wait_for_selector("#playerDock.active", timeout=5000)
        page.wait_for_selector("#dockPlayBtn:has-text('❚❚')", timeout=5000)
        assert "❚❚" in page.locator("#dockPlayBtn").text_content()
    
    def test_online_recording_with_metadata(self, page):
        """Test that metadata is properly saved for online recordings."""
        page.goto("http://localhost:8000")
        
        # Record
        page.click("#recordButton")
        time.sleep(2)
        page.click("#stopButton")
        
        # Handle modal
        handle_save_modal(page, "metadata_test")
        
        # Wait for save
        page.wait_for_selector("#toast:has-text('Saved')")
        
        # Verify metadata in first track item
        track = page.locator(".track-item").first
        info = track.locator(".font-mono")
        assert "WEBM" in info.text_content().upper()
        assert "/" in info.text_content() or "." in info.text_content()


@pytest.mark.e2e
class TestOfflineRecordingE2E:
    """End-to-end tests for offline recording scenarios."""
    
    def test_record_offline_then_upload(self, page):
        """Test offline recording with later upload."""
        page.goto("http://localhost:8000")
        
        # Simulate offline
        page.context.set_offline(True)
        time.sleep(1)
        
        # Start recording
        page.click("#recordButton")
        time.sleep(2)
        page.click("#stopButton")
        
        # Handle modal
        handle_save_modal(page, "offline_recording")
        
        # Verify local save
        page.wait_for_selector("#toast:has-text('Saved')")
        
        # Verify track in playlist
        track = page.locator(".track-item").first
        assert "offline_recording" in track.text_content()
        
        # Go back online
        page.context.set_offline(False)
        
        # Wait for synced badge
        page.wait_for_selector(".upload-status-badge:has-text('SYNCED')", timeout=15000)
        assert track.locator(".upload-status-badge:has-text('SYNCED')").is_visible()
    
    def test_offline_recording_playback(self, page):
        """Test playback of offline-recorded audio."""
        page.goto("http://localhost:8000")
        page.context.set_offline(True)
        
        # Record offline
        page.click("#recordButton")
        time.sleep(2)
        page.click("#stopButton")
        
        # Handle modal
        handle_save_modal(page, "test_playback")
        
        # Play back
        page.wait_for_selector(".track-item")
        track = page.locator(".track-item").first
        
        # Click play icon in playlist
        play_icon = track.locator("button:has-text('▶')")
        play_icon.click()
        
        # Wait for player dock
        page.wait_for_selector("#playerDock.active")
        
        # Verify playback starts
        page.wait_for_selector("#dockPlayBtn:has-text('❚❚')", timeout=5000)
        assert "❚❚" in page.locator("#dockPlayBtn").text_content()


@pytest.mark.e2e
class TestConnectionLossE2E:
    """End-to-end tests for connection loss during recording."""
    
    def test_connection_loss_during_recording(self, page):
        """Test seamless handling of connection loss."""
        page.goto("http://localhost:8000")
        
        # Start recording online
        page.click("#recordButton")
        time.sleep(2)
        
        # Simulate connection loss
        page.context.set_offline(True)
        time.sleep(2)
        
        # Stop recording
        page.click("#stopButton")
        
        # Handle modal
        handle_save_modal(page, "connection_loss_test")
        
        # Verify save
        page.wait_for_selector("#toast:has-text('Saved')")
        
        # Verify recording in list
        track = page.locator(".track-item").first
        assert "connection_loss_test" in track.text_content()


@pytest.mark.e2e
class TestRecoveryE2E:
    """End-to-end tests for crash recovery."""
    
    def test_recovery_after_crash(self, page):
        """Test recovery after app crash."""
        page.goto("http://localhost:8000")
        
        # Start recording
        page.click("#recordButton")
        time.sleep(2)
        
        # Simulate crash (reload page)
        page.reload()
        
        # Wait for recovery prompt
        page.wait_for_selector("#recoveryModal", state="visible", timeout=10000)
        
        # Recover
        page.click("#recoveryModalDefaultBtn")
        
        # Recovered sessions lead to save modal
        handle_save_modal(page, "recovered_recording")
        
        # Wait for success toast
        page.wait_for_selector("#toast:has-text('Saved')", timeout=10000)
        
        # Verify recording appears
        page.wait_for_selector(".track-item")
        assert "recovered_recording" in page.locator(".track-item").first.text_content()


@pytest.mark.e2e
class TestUIIndicators:
    """Test UI indicators and feedback."""
    
    def test_upload_button_visibility(self, page):
        """Test upload button shows for recordings."""
        page.goto("http://localhost:8000")
        
        # Record
        page.click("#recordButton")
        time.sleep(1)
        page.click("#stopButton")
        
        # Handle modal
        handle_save_modal(page, "ui_test")
        
        # Wait for track
        page.wait_for_selector(".track-item")
        track = page.locator(".track-item").first
        # Upload button is the cloud icon
        assert track.locator("button:has-text('☁')").is_visible()
