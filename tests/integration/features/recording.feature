Feature: Audio Recording
  As a user of WaveForge Pro
  I want to record audio
  So that I can save and manage my recordings

  Background:
    Given the WaveForge Pro application is running
    And I have granted microphone permissions

  Scenario: Start and stop a recording
    Given I am on the main application page
    When I click the "Record" button
    Then the recording should start
    And the timer should begin counting
    And the waveform visualizer should show activity
    When I wait for 5 seconds
    And I click the "Stop" button
    Then the recording should stop
    And the save dialog should appear

  Scenario: Save a recording with a custom name
    Given I have completed a 10-second recording
    And the save dialog is displayed
    When I enter "My Test Recording" as the name
    And I click "Save"
    Then the recording should be saved to IndexedDB
    And "My Test Recording" should appear in the recordings list

  Scenario: Record and upload to cloud
    Given I have a saved recording named "Upload Test"
    When I click the upload button for "Upload Test"
    Then the file should be split into chunks
    And each chunk should be uploaded to the server
    And the upload progress should be displayed
    And when complete, the recording should be marked as uploaded

  Scenario: Crash recovery
    Given I am recording audio
    And 30 seconds have passed
    When the browser is forcefully closed
    And I reopen the application
    Then a recovery modal should appear
    And it should show the orphaned recording session
    And the session should have approximately 30 chunks
    When I click "Restore & Save"
    Then the chunks should be assembled
    And the save dialog should appear with the recovered audio

  Scenario: Multiple recordings management
    Given I have 3 saved recordings
    When I view the recordings list
    Then I should see all 3 recordings
    And each recording should show its name and duration
    When I delete the second recording
    Then only 2 recordings should remain

  Scenario: Playback with EQ adjustments
    Given I have a saved recording named "EQ Test"
    When I click play on "EQ Test"
    Then the player dock should appear
    And playback should start
    When I adjust the low frequency EQ to +10dB
    Then the audio should reflect the EQ change
    And the waveform should update accordingly

  Scenario: Recording format selection
    Given I am on the main application page
    When I select "WAV" as the recording format
    And I start recording for 10 seconds
    And I stop and save the recording as "WAV Test"
    Then "WAV Test" should be saved in WAV format
    And the file extension should be ".wav"

  Scenario: Long recording with low memory
    Given I select "WebM" as the recording format
    When I start recording
    And I wait for 300 seconds
    And I stop and save the recording
    Then the recording should be saved successfully
    And no memory overflow should occur
    And all chunks should be present in IndexedDB

  Scenario: Simultaneous upload queue
    Given I have 5 recordings ready to upload
    When I click upload on all 5 recordings
    Then the uploads should be queued
    And they should upload sequentially
    And the queue should process all uploads
    And all recordings should be marked as uploaded

  Scenario: Network failure during upload
    Given I am uploading a recording
    And the upload is 50% complete
    When the network connection is lost
    Then the upload should pause
    And the Service Worker should queue the retry
    When the network connection is restored
    Then the upload should resume from the last successful chunk
    And the upload should complete successfully
