Feature: WaveForge Pro UI Interactions
  As a user
  I want to interact with the WaveForge Pro interface
  So that I can record and manage audio through the browser

  Scenario: Load application and verify UI elements
    Given I navigate to the WaveForge Pro homepage
    Then I should see the "WaveForge Pro" title
    And I should see the record button
    And I should see the EQ controls
    And I should see the recordings database section

  Scenario: Record audio via UI
    Given I am on the WaveForge Pro homepage
    And I have granted microphone permissions
    When I click the record button
    Then the record button should change to "stop" state
    And the timer should start incrementing
    And the waveform visualizer should animate
    When I wait for 5 seconds
    And I click the stop button
    Then a save modal should appear
    When I enter "UI Test Recording" in the name field
    And I click the save button in the modal
    Then the modal should close
    And "UI Test Recording" should appear in the recordings list

  Scenario: Play a recording via UI
    Given I have a recording named "Playback Test" in the database
    When I click the play button for "Playback Test"
    Then the player dock should slide up from the bottom
    And the play button should change to pause icon
    And the seek bar should start filling
    When I click the pause button
    Then playback should pause
    And the pause icon should change to play icon

  Scenario: Adjust EQ settings via UI
    Given I am on the WaveForge Pro homepage
    When I drag the "Low" EQ slider to +10dB
    Then the slider value should display "+10"
    And the audio processing should reflect the change
    When I drag the "Mid" EQ slider to -5dB
    Then the slider value should display "-5"
    When I drag the "High" EQ slider to 0dB
    Then the slider value should display "0"

  Scenario: Upload recording via UI
    Given I have a recording named "Upload UI Test" in the database
    When I click the cloud upload button for "Upload UI Test"
    Then an upload progress bar should appear
    And the progress should increment from 0% to 100%
    When the upload completes
    Then the upload button should show a success checkmark
    And the recording should be marked as uploaded

  Scenario: Delete recording via UI
    Given I have a recording named "Delete Test" in the database
    When I click the delete button for "Delete Test"
    Then a confirmation dialog should appear
    When I click "Confirm" in the dialog
    Then "Delete Test" should be removed from the list
    And the database count should decrement by 1

  Scenario: Switch language via UI
    Given I am on the WaveForge Pro homepage
    And the current language is "DE" (German)
    When I click the language toggle button
    Then the interface should switch to "EN" (English)
    And the "AUFNAHME" button should change to "RECORD"
    And the "AUFNAHMEN" heading should change to "RECORDINGS"
    When I click the language toggle button again
    Then the interface should switch back to "DE"

  Scenario: Keyboard navigation
    Given I am on the WaveForge Pro homepage
    When I press the Tab key
    Then the focus should move to the first interactive element
    When I press Tab multiple times
    Then the focus should cycle through all controls
    When I press Enter on the record button
    Then recording should start
    When I press Escape
    Then any open modal should close

  Scenario: Responsive design on mobile
    Given I am on the WaveForge Pro homepage
    When I resize the browser to mobile width (375px)
    Then the layout should adapt to mobile view
    And all controls should remain accessible
    And the EQ controls should stack vertically
    When I resize back to desktop width (1920px)
    Then the layout should return to desktop view

  Scenario: Info modal interaction
    Given I am on the WaveForge Pro homepage
    When I click the info button
    Then the info modal should appear
    And it should display application information
    And it should show keyboard shortcuts
    When I click the close button in the modal
    Then the modal should close
    When I click the info button again
    And I press the Escape key
    Then the modal should close
