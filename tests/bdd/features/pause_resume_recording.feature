Feature: Pause and Resume Recording
  As a user recording audio
  I want to pause and resume my recordings
  So that I can take breaks without losing my work or starting over

  Background:
    Given the WaveForge Pro application is loaded
    And the user is on the main recording page
    And the browser supports MediaRecorder API

  Scenario: Pause button is disabled before recording
    Given the user has not started recording
    Then the pause button should be disabled
    And the pause button should have text "PAUSE"
    And the pause button should have yellow color scheme

  Scenario: Pause button becomes enabled when recording starts
    Given the user has not started recording
    When the user clicks the record button
    Then the recording indicator should be visible
    And the recording should start
    And the pause button should be enabled
    And the pause button should have text "PAUSE"

  Scenario: Pause active recording
    Given the user is recording audio
    And the recording has been active for 3 seconds
    When the user clicks the pause button
    Then the recording should be paused
    And the pause button text should change to "RESUME"
    And the pause button should have the paused-active CSS class
    And the timer should stop updating
    And the MediaRecorder state should be "paused"
    And a pause icon should be visible in the LiveUploadIndicator

  Scenario: Resume paused recording
    Given the user has a paused recording
    And the pause button shows "RESUME"
    When the user clicks the pause button
    Then the recording should resume
    And the pause button text should change to "PAUSE"
    And the paused-active CSS class should be removed
    And the timer should resume from the paused time
    And the MediaRecorder state should be "recording"
    And the LiveUploadIndicator should show normal recording state

  Scenario: Multiple pause/resume cycles
    Given the user is recording audio
    When the user clicks the pause button
    Then the recording should be paused
    When the user waits for 2 seconds
    And the user clicks the pause button again
    Then the recording should resume
    When the user waits for 2 seconds
    And the user clicks the pause button again
    Then the recording should be paused again
    And the timer should accurately reflect only active recording time

  Scenario: Pause recording for extended time
    Given the user is recording audio
    And the recording has been active for 5 seconds
    When the user clicks the pause button
    Then the recording should be paused
    When the user waits for 60 seconds
    And the user clicks the pause button to resume
    Then the recording should continue without data loss
    And the timer should show 5 seconds plus new recording time
    And no audio chunks should be lost

  Scenario: Stop recording while paused
    Given the user has a paused recording
    And the pause button shows "RESUME"
    When the user clicks the stop button
    Then the recording should stop
    And the save modal should appear
    And the pause button should be disabled
    And the pause button text should reset to "PAUSE"
    And the paused-active CSS class should be removed
    And the total recording time should be accurate

  Scenario: Background upload continues during pause
    Given the user is recording audio in online mode
    And chunks are being uploaded in the background
    When the user clicks the pause button
    Then the recording should be paused
    But the upload queue should continue processing
    And existing chunks should still upload
    And the LiveUploadIndicator should show pause icon with upload progress

  Scenario: Pause button styling and accessibility
    Given the user is recording audio
    When the user hovers over the pause button
    Then the button should show hover effect
    And the button should have proper ARIA label "Aufnahme pausieren"
    When the user pauses the recording
    Then the ARIA label should change to "Aufnahme fortsetzen"
    And the button should have pulse-pause animation
    And screen readers should announce the state change

  Scenario: Pause icon display
    Given the user views the recording controls
    Then the pause button should display a pause icon (⏸)
    And the icon should be properly aligned with the button text
    And the icon should be visible on all screen sizes

  Scenario: Responsive button layout
    Given the user views the recording controls
    Then the pause button should be in a 3-column grid
    And the button should have consistent sizing with REC and STOP
    And the layout should be centered on the page
    When the screen size is reduced to mobile
    Then all three buttons should remain visible
    And buttons should maintain proper spacing

  Scenario: Pause state persistence across UI updates
    Given the user is recording audio
    And the user has paused the recording
    When the UI updates track list or other components
    Then the pause state should remain consistent
    And the pause button should still show "RESUME"
    And the paused-active CSS class should remain applied

  Scenario: Error handling - pause without active recording
    Given the user has not started recording
    When the pause button is programmatically clicked
    Then no error should occur
    And the application state should remain stable
    And the button should remain in its initial state

  Scenario: Error handling - pause when MediaRecorder unavailable
    Given the user is recording audio
    And the MediaRecorder becomes unavailable
    When the user clicks the pause button
    Then the application should handle the error gracefully
    And the user should not see a crash
    And appropriate error logging should occur

  Scenario: Timer accuracy with multiple pauses
    Given the user starts recording
    And the timer shows 00:00:05 after 5 seconds
    When the user pauses for 10 seconds
    And the user resumes and records for 5 more seconds
    Then the timer should show 00:00:10
    And the timer should not include paused time
    And the total elapsed time should be accurately tracked

  Scenario: Pause during format change
    Given the user is recording in WEBM format
    When the user attempts to change format during recording
    Then the format selector should be disabled
    And the pause functionality should remain operational
    And format can only be changed after stopping

  Scenario: Console logging for pause/resume
    Given the user is recording audio
    When the user clicks the pause button
    Then "⏸ Recording paused" should be logged to console
    When the user clicks the pause button again
    Then "▶ Recording resumed" should be logged to console
    And all logs should be properly formatted
