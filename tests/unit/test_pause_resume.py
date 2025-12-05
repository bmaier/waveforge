"""
Unit Tests for Pause/Resume Recording Functionality

Tests the JavaScript pause/resume logic through Python test automation.
"""

import pytest
from pathlib import Path
import json


class TestPauseResumeRecording:
    """Test suite for pause/resume recording functionality."""
    
    def test_pause_resume_feature_exists_in_html(self):
        """Verify that pause button exists in the HTML."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        assert html_path.exists(), "index.html not found"
        
        content = html_path.read_text(encoding='utf-8')
        
        # Check for pause button
        assert 'id="pauseButton"' in content, "Pause button not found"
        assert 'data-i18n="ui.pause"' in content or 'PAUSE' in content, "Pause button label not found"
        
    def test_pause_function_exists_in_html(self):
        """Verify that pauseRecording function is defined."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check for function definition
        assert 'function pauseRecording()' in content, "pauseRecording function not defined"
        assert 'mediaRecorder.pause()' in content, "MediaRecorder pause() not called"
        assert 'mediaRecorder.resume()' in content, "MediaRecorder resume() not called"
        
    def test_pause_state_variables_exist(self):
        """Verify that pause state variables are initialized."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check for state variables
        assert 'isPaused' in content, "isPaused variable not found"
        assert 'pausedTime' in content, "pausedTime variable not found"
        
    def test_pause_button_disabled_initially(self):
        """Verify that pause button is disabled before recording starts."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Find pause button definition
        pause_button_start = content.find('id="pauseButton"')
        assert pause_button_start != -1, "Pause button not found"
        
        # Check for disabled attribute in button definition (within 500 chars)
        button_section = content[pause_button_start:pause_button_start + 500]
        assert 'disabled' in button_section, "Pause button not initially disabled"
        
    def test_timer_pause_functions_exist(self):
        """Verify that timer pause/resume functions are defined."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check for timer functions
        assert 'function pauseTimer()' in content, "pauseTimer function not defined"
        assert 'function resumeTimer()' in content, "resumeTimer function not defined"
        assert 'clearInterval(timerInterval)' in content, "Timer not cleared on pause"
        
    def test_pause_button_event_listener_exists(self):
        """Verify that pause button has event listener."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check for event listener
        assert "getElementById('pauseButton').addEventListener" in content, \
            "Pause button event listener not found"
        assert "'click', pauseRecording" in content or '"click", pauseRecording' in content, \
            "pauseRecording not bound to click event"
        
    def test_pause_css_animations_exist(self):
        """Verify that pause CSS animations are defined."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check for CSS animation
        assert '.paused-active' in content, "paused-active CSS class not defined"
        assert 'pulse-pause' in content, "pulse-pause animation not defined"
        assert '@keyframes pulse-pause' in content, "pulse-pause keyframes not defined"
        
    def test_pause_aria_labels_exist(self):
        """Verify that pause button has proper ARIA labels."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check for ARIA labels in pause function
        assert 'aria-label' in content[content.find('pauseRecording'):content.find('pauseRecording') + 2000], \
            "ARIA labels not updated in pauseRecording function"
        
    def test_live_upload_indicator_pause_integration(self):
        """Verify that LiveUploadIndicator has pause/resume methods."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check for LiveUploadIndicator integration
        assert 'onRecordingPause' in content, "onRecordingPause method not found"
        assert 'onRecordingResume' in content, "onRecordingResume method not found"
        assert 'LiveUploadIndicator.onRecordingPause()' in content, \
            "LiveUploadIndicator.onRecordingPause() not called"
        assert 'LiveUploadIndicator.onRecordingResume()' in content, \
            "LiveUploadIndicator.onRecordingResume() not called"
        
    def test_pause_button_state_changes(self):
        """Verify that pause button changes state correctly."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check for button text changes
        pause_function = content[content.find('function pauseRecording()'):
                                 content.find('function pauseRecording()') + 3000]
        
        assert 'RESUME' in pause_function, "Button text not changed to RESUME"
        assert 'PAUSE' in pause_function, "Button text not changed back to PAUSE"
        assert 'paused-active' in pause_function, "CSS class not toggled"
        
    def test_recording_state_management(self):
        """Verify that recording state is managed correctly during pause/resume."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check for state checks in pauseRecording function
        pause_function = content[content.find('function pauseRecording()'):
                                 content.find('function pauseRecording()') + 3000]
        
        assert 'isRecording' in pause_function, "isRecording state not checked"
        assert 'isPaused' in pause_function, "isPaused state not checked"
        assert "mediaRecorder.state" in pause_function or "state === 'recording'" in pause_function, \
            "MediaRecorder state not validated"


class TestPauseResumeIntegration:
    """Integration tests for pause/resume with other components."""
    
    def test_pause_button_enabled_on_start_recording(self):
        """Verify that pause button is enabled when recording starts."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Find startRecording function
        start_recording = content.find('function startRecording(')
        assert start_recording != -1, "startRecording function not found"
        
        # Check that pause button is enabled
        start_section = content[start_recording:start_recording + 5000]
        assert "pauseButton" in start_section, "pauseButton not referenced in startRecording"
        assert ".disabled = false" in start_section, "pauseButton not enabled in startRecording"
        
    def test_pause_button_reset_on_stop_recording(self):
        """Verify that pause button is reset when recording stops."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Find stopRecording function
        stop_recording = content.find('function stopRecording(')
        assert stop_recording != -1, "stopRecording function not found"
        
        # Check that pause button is reset
        stop_section = content[stop_recording:stop_recording + 5000]
        assert "pauseButton" in stop_section, "pauseButton not referenced in stopRecording"
        assert ".disabled = true" in stop_section, "pauseButton not disabled in stopRecording"
        assert "isPaused = false" in stop_section, "isPaused not reset in stopRecording"
        
    def test_paused_time_accumulated_correctly(self):
        """Verify that paused time is accumulated correctly across pause/resume cycles."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Check pauseTimer implementation
        pause_timer = content[content.find('function pauseTimer()'):
                             content.find('function pauseTimer()') + 500]
        
        assert 'pausedTime = Date.now() - startTime' in pause_timer or \
               'pausedTime=Date.now()-startTime' in pause_timer.replace(' ', ''), \
               "pausedTime not calculated correctly"
        
        # Check resumeTimer implementation  
        resume_timer = content[content.find('function resumeTimer()'):
                              content.find('function resumeTimer()') + 500]
        
        assert 'startTime = Date.now() - pausedTime' in resume_timer or \
               'startTime=Date.now()-pausedTime' in resume_timer.replace(' ', ''), \
               "startTime not restored correctly from pausedTime"


class TestPauseResumeButtonLayout:
    """Test suite for pause button layout and styling."""
    
    def test_pause_button_in_centered_grid(self):
        """Verify that pause button is in the new centered grid layout."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Find the grid layout section
        grid_layout = content.find('grid grid-cols-3')
        assert grid_layout != -1, "Grid layout not found"
        
        # Verify pause button is within grid
        grid_section = content[grid_layout:grid_layout + 2000]
        assert 'id="pauseButton"' in grid_section, "Pause button not in grid layout"
        
    def test_pause_button_has_icon(self):
        """Verify that pause button has a pause icon."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Find pause button
        pause_button_start = content.find('id="pauseButton"')
        assert pause_button_start != -1, "Pause button not found"
        
        # Check for pause icon (within 500 chars of button start)
        button_section = content[pause_button_start:pause_button_start + 500]
        assert '⏸' in button_section, "Pause icon not found in button"
        
    def test_all_buttons_have_consistent_styling(self):
        """Verify that all recording control buttons have consistent styling."""
        html_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "index.html"
        content = html_path.read_text(encoding='utf-8')
        
        # Find grid layout
        grid_start = content.find('grid grid-cols-3')
        grid_section = content[grid_start:grid_start + 3000]
        
        # Check that all buttons have py-3 (consistent vertical padding)
        rec_button = grid_section[grid_section.find('id="recordButton"'):
                                  grid_section.find('id="recordButton"') + 300]
        pause_button = grid_section[grid_section.find('id="pauseButton"'):
                                   grid_section.find('id="pauseButton"') + 300]
        stop_button = grid_section[grid_section.find('id="stopButton"'):
                                  grid_section.find('id="stopButton"') + 300]
        
        assert 'py-3' in rec_button, "REC button missing py-3"
        assert 'py-3' in pause_button, "PAUSE button missing py-3"
        assert 'py-3' in stop_button, "STOP button missing py-3"
        
        # Check consistent horizontal padding
        assert 'px-6' in rec_button, "REC button missing px-6"
        assert 'px-6' in pause_button, "PAUSE button missing px-6"
        assert 'px-6' in stop_button, "STOP button missing px-6"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
