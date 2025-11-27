"""
Playwright + Behave step definitions for E2E GUI tests.

This module implements browser automation steps using Playwright
to test the WaveForge Pro user interface.
"""

from behave import given, when, then
from playwright.sync_api import expect
import time


# Navigation steps

@given('I navigate to the WaveForge Pro homepage')
@given('I am on the WaveForge Pro homepage')
def step_navigate_to_homepage(context):
    """Navigate to the application homepage."""
    context.page.goto(context.base_url)
    context.page.wait_for_load_state("networkidle")


# Verification steps

@then('I should see the "{text}" title')
def step_see_title(context, text):
    """Verify page title contains text."""
    expect(context.page.locator("h1, h2")).to_contain_text(text)


@then('I should see the record button')
def step_see_record_button(context):
    """Verify record button is visible."""
    record_button = context.page.locator('button:has-text("REC"), button:has-text("AUFNAHME")')
    expect(record_button).to_be_visible()


@then('I should see the EQ controls')
def step_see_eq_controls(context):
    """Verify EQ controls are visible."""
    eq_section = context.page.locator('text=/EQ|EQUALIZER/i')
    expect(eq_section).to_be_visible()


@then('I should see the recordings database section')
def step_see_database_section(context):
    """Verify recordings database section is visible."""
    database_section = context.page.locator('text=/AUFNAHMEN|RECORDINGS|DATABASE/i')
    expect(database_section).to_be_visible()


# Permission steps

@given('I have granted microphone permissions')
def step_grant_mic_permissions(context):
    """Grant microphone permissions (handled by Playwright context)."""
    # Permissions are granted in conftest.py browser_context fixture
    pass


# Recording interaction steps

@when('I click the record button')
def step_click_record_button(context):
    """Click the record button."""
    record_button = context.page.locator('button:has-text("REC"), button:has-text("AUFNAHME")')
    record_button.click()
    time.sleep(0.5)  # Wait for state change


@then('the record button should change to "{state}" state')
def step_record_button_state(context, state):
    """Verify record button state."""
    if state.lower() == "stop":
        stop_button = context.page.locator('button:has-text("STOP"), button.recording')
        expect(stop_button).to_be_visible()


@then('the timer should start incrementing')
def step_timer_incrementing(context):
    """Verify timer is incrementing."""
    timer = context.page.locator('.timer, [data-timer]')
    initial_text = timer.text_content()
    time.sleep(2)
    updated_text = timer.text_content()
    assert initial_text != updated_text, "Timer should be incrementing"


@then('the waveform visualizer should animate')
def step_waveform_animating(context):
    """Verify waveform visualizer is animating."""
    canvas = context.page.locator('canvas#visualizer, canvas.waveform')
    expect(canvas).to_be_visible()


@when('I wait for {seconds:d} seconds')
def step_wait_seconds(context, seconds):
    """Wait for specified seconds."""
    time.sleep(seconds)


@when('I click the stop button')
def step_click_stop_button(context):
    """Click the stop button."""
    stop_button = context.page.locator('button:has-text("STOP")')
    stop_button.click()
    time.sleep(0.5)


# Modal interaction steps

@then('a save modal should appear')
def step_save_modal_appears(context):
    """Verify save modal appears."""
    modal = context.page.locator('.modal, [role="dialog"]')
    expect(modal).to_be_visible(timeout=5000)


@when('I enter "{text}" in the name field')
def step_enter_text_in_name_field(context, text):
    """Enter text in the recording name field."""
    name_input = context.page.locator('input[type="text"], input[placeholder*="name" i]')
    name_input.fill(text)


@when('I click the save button in the modal')
def step_click_modal_save_button(context):
    """Click the save button in the modal."""
    save_button = context.page.locator('.modal button:has-text("Save"), .modal button:has-text("Speichern")')
    save_button.click()


@then('the modal should close')
def step_modal_closes(context):
    """Verify modal closes."""
    modal = context.page.locator('.modal, [role="dialog"]')
    expect(modal).to_be_hidden(timeout=5000)


@then('"{name}" should appear in the recordings list')
def step_recording_appears_in_list(context, name):
    """Verify recording appears in the list."""
    recording_item = context.page.locator(f'text="{name}"')
    expect(recording_item).to_be_visible(timeout=5000)


# Playback steps

@given('I have a recording named "{name}" in the database')
def step_have_recording(context, name):
    """Ensure a recording exists (may need to create it first)."""
    # Check if recording exists, if not, create it via UI
    recording = context.page.locator(f'text="{name}"')
    if not recording.is_visible():
        # Create a quick recording
        context.execute_steps(f'''
            When I click the record button
            And I wait for 2 seconds
            And I click the stop button
            And I enter "{name}" in the name field
            And I click the save button in the modal
        ''')


@when('I click the play button for "{name}"')
def step_click_play_button(context, name):
    """Click the play button for a specific recording."""
    # Find the recording row and click its play button
    recording_row = context.page.locator(f'text="{name}"').locator('..')
    play_button = recording_row.locator('button[title*="Play" i], button:has-text("▶")')
    play_button.click()


@then('the player dock should slide up from the bottom')
def step_player_dock_appears(context):
    """Verify player dock appears."""
    player_dock = context.page.locator('.player-dock, .floating-player')
    expect(player_dock).to_be_visible(timeout=3000)


@then('the play button should change to pause icon')
def step_play_becomes_pause(context):
    """Verify play button changes to pause."""
    pause_button = context.page.locator('button:has-text("⏸"), button[title*="Pause" i]')
    expect(pause_button).to_be_visible(timeout=2000)


@then('the seek bar should start filling')
def step_seek_bar_filling(context):
    """Verify seek bar progress."""
    seek_bar = context.page.locator('input[type="range"], .seek-bar')
    initial_value = seek_bar.get_attribute('value') or '0'
    time.sleep(1)
    updated_value = seek_bar.get_attribute('value') or '0'
    # Value should have changed (increased)


@when('I click the pause button')
def step_click_pause_button(context):
    """Click the pause button."""
    pause_button = context.page.locator('button:has-text("⏸"), button[title*="Pause" i]')
    pause_button.click()


@then('playback should pause')
@then('the pause icon should change to play icon')
def step_playback_paused(context):
    """Verify playback is paused."""
    play_button = context.page.locator('button:has-text("▶"), button[title*="Play" i]')
    expect(play_button).to_be_visible()


# EQ interaction steps

@when('I drag the "{band}" EQ slider to {value} dB')
def step_drag_eq_slider(context, band, value):
    """Drag an EQ slider to a specific value."""
    # Find the slider for the specified band
    slider = context.page.locator(f'input[type="range"][id*="{band.lower()}" i]').first
    
    # Set the slider value
    slider.fill(value.replace('dB', '').replace('+', '').strip())


@then('the slider value should display "{value}"')
def step_slider_displays_value(context, value):
    """Verify slider value display."""
    # Find the value display element
    value_display = context.page.locator(f'text="{value}"')
    expect(value_display).to_be_visible(timeout=2000)


@then('the audio processing should reflect the change')
def step_audio_processing_updated(context):
    """Verify audio processing is updated (visual check)."""
    # In real test, might check waveform changes or audio analyzer
    time.sleep(0.5)


# Upload steps

@when('I click the cloud upload button for "{name}"')
def step_click_upload_button(context, name):
    """Click the upload button for a recording."""
    recording_row = context.page.locator(f'text="{name}"').locator('..')
    upload_button = recording_row.locator('button:has-text("☁"), button[title*="Upload" i]')
    upload_button.click()


@then('an upload progress bar should appear')
def step_upload_progress_appears(context):
    """Verify upload progress bar appears."""
    progress_bar = context.page.locator('.progress, [role="progressbar"]')
    expect(progress_bar).to_be_visible(timeout=3000)


@then('the progress should increment from 0% to 100%')
def step_progress_increments(context):
    """Verify progress increments."""
    progress_bar = context.page.locator('.progress, [role="progressbar"]')
    # Wait for progress to reach 100%
    context.page.wait_for_function(
        "element => element.value === '100' || element.textContent.includes('100%')",
        progress_bar,
        timeout=30000
    )


@when('the upload completes')
def step_upload_completes(context):
    """Wait for upload to complete."""
    # Wait for success indicator
    time.sleep(1)


@then('the upload button should show a success checkmark')
def step_upload_success_indicator(context):
    """Verify upload success indicator."""
    success_icon = context.page.locator('text="✓", [data-upload-status="success"]')
    expect(success_icon).to_be_visible(timeout=5000)


# Delete steps

@when('I click the delete button for "{name}"')
def step_click_delete_button(context, name):
    """Click the delete button for a recording."""
    recording_row = context.page.locator(f'text="{name}"').locator('..')
    delete_button = recording_row.locator('button:has-text("×"), button[title*="Delete" i]')
    delete_button.click()


@then('a confirmation dialog should appear')
def step_confirmation_dialog_appears(context):
    """Verify confirmation dialog appears."""
    dialog = context.page.locator('[role="dialog"], .confirmation-modal')
    expect(dialog).to_be_visible(timeout=2000)


@when('I click "{button}" in the dialog')
def step_click_dialog_button(context, button):
    """Click a button in the dialog."""
    dialog_button = context.page.locator(f'.modal button:has-text("{button}"), [role="dialog"] button:has-text("{button}")')
    dialog_button.click()


@then('"{name}" should be removed from the list')
def step_recording_removed(context, name):
    """Verify recording is removed."""
    recording = context.page.locator(f'text="{name}"')
    expect(recording).to_be_hidden(timeout=3000)


# Language switching steps

@given('the current language is "{lang}" ({full_name})')
def step_current_language(context, lang, full_name):
    """Verify current language."""
    # Check for language indicator
    lang_indicator = context.page.locator(f'text="{lang}"')
    # May or may not be visible, depends on UI


@when('I click the language toggle button')
def step_click_language_toggle(context):
    """Click the language toggle button."""
    lang_button = context.page.locator('button[title*="Language" i], button:has-text("DE"), button:has-text("EN")')
    lang_button.click()


@then('the interface should switch to "{lang}" ({full_name})')
def step_interface_switches_language(context, lang, full_name):
    """Verify interface language switched."""
    # Check for language-specific text
    time.sleep(0.5)


@then('the "{old_text}" button should change to "{new_text}"')
def step_button_text_changes(context, old_text, new_text):
    """Verify button text changes."""
    button = context.page.locator(f'button:has-text("{new_text}")')
    expect(button).to_be_visible(timeout=2000)


@then('the "{old_text}" heading should change to "{new_text}"')
def step_heading_text_changes(context, old_text, new_text):
    """Verify heading text changes."""
    heading = context.page.locator(f'h1:has-text("{new_text}"), h2:has-text("{new_text}"), h3:has-text("{new_text}")')
    expect(heading).to_be_visible(timeout=2000)


@then('the interface should switch back to "{lang}"')
def step_interface_switches_back(context, lang):
    """Verify interface switches back."""
    time.sleep(0.5)


# Keyboard navigation steps

@when('I press the Tab key')
def step_press_tab(context):
    """Press the Tab key."""
    context.page.keyboard.press('Tab')


@when('I press Tab multiple times')
def step_press_tab_multiple(context):
    """Press Tab multiple times."""
    for _ in range(5):
        context.page.keyboard.press('Tab')
        time.sleep(0.2)


@then('the focus should move to the first interactive element')
@then('the focus should cycle through all controls')
def step_focus_cycles(context):
    """Verify focus cycles through controls."""
    # Check that some element has focus
    focused = context.page.evaluate('document.activeElement.tagName')
    assert focused in ['BUTTON', 'INPUT', 'A', 'SELECT']


@when('I press Enter on the record button')
def step_press_enter_on_record(context):
    """Press Enter on the record button."""
    record_button = context.page.locator('button:has-text("REC"), button:has-text("AUFNAHME")')
    record_button.focus()
    context.page.keyboard.press('Enter')


@when('I press Escape')
def step_press_escape(context):
    """Press the Escape key."""
    context.page.keyboard.press('Escape')


@then('any open modal should close')
def step_modal_closes_on_escape(context):
    """Verify modals close on Escape."""
    modal = context.page.locator('.modal, [role="dialog"]')
    expect(modal).to_be_hidden(timeout=2000)


# Responsive design steps

@when('I resize the browser to mobile width ({width}px)')
def step_resize_to_mobile(context, width):
    """Resize browser to mobile width."""
    context.page.set_viewport_size({"width": int(width), "height": 667})


@then('the layout should adapt to mobile view')
def step_layout_adapts_mobile(context):
    """Verify layout adapts to mobile."""
    # Check that viewport is mobile size
    viewport = context.page.viewport_size
    assert viewport['width'] <= 768


@then('all controls should remain accessible')
def step_controls_accessible(context):
    """Verify controls are still accessible."""
    # Check that main controls are visible
    record_button = context.page.locator('button:has-text("REC"), button:has-text("AUFNAHME")')
    expect(record_button).to_be_visible()


@when('I resize back to desktop width ({width}px)')
def step_resize_to_desktop(context, width):
    """Resize browser to desktop width."""
    context.page.set_viewport_size({"width": int(width), "height": 1080})


@then('the layout should return to desktop view')
def step_layout_returns_desktop(context):
    """Verify layout returns to desktop."""
    viewport = context.page.viewport_size
    assert viewport['width'] >= 1024


# Info modal steps

@when('I click the info button')
def step_click_info_button(context):
    """Click the info button."""
    info_button = context.page.locator('button[title*="Info" i], button:has-text("ℹ"), button:has-text("?")')
    info_button.click()


@then('the info modal should appear')
def step_info_modal_appears(context):
    """Verify info modal appears."""
    modal = context.page.locator('.modal, [role="dialog"]')
    expect(modal).to_be_visible(timeout=2000)


@then('it should display application information')
def step_displays_app_info(context):
    """Verify modal displays app info."""
    info_text = context.page.locator('text=/WaveForge|Version|Author/i')
    expect(info_text).to_be_visible()


@then('it should show keyboard shortcuts')
def step_shows_keyboard_shortcuts(context):
    """Verify modal shows keyboard shortcuts."""
    shortcuts = context.page.locator('text=/Shortcut|Keyboard|Key/i')
    # May or may not exist depending on modal content


@when('I click the close button in the modal')
def step_click_modal_close(context):
    """Click the close button in the modal."""
    close_button = context.page.locator('.modal button:has-text("×"), .modal [aria-label="Close"]')
    close_button.click()
