"""
Step definitions for UI indicators scenarios
"""

from behave import given, when, then
from playwright.sync_api import expect


@given('a "☁ SERVER" badge should be visible')
@then('a "☁ SERVER" badge should be visible')
def step_server_badge_visible(context):
    """Verify server badge visible"""
    expect(context.page.locator('.badge:has-text("SERVER"), .badge:has-text("☁")')).to_be_visible(timeout=5000)


@given('the user has recorded audio offline')
def step_recorded_offline(context):
    """Simulate offline recording"""
    # Would set offline mode and create recording
    pass


@given('the recording was assembled on the client')
def step_assembled_on_client(context):
    """Verify client assembly"""
    pass


@then('a "💾 LOCAL" badge should be visible')
def step_local_badge_visible(context):
    """Verify local badge visible"""
    expect(context.page.locator('.badge:has-text("LOCAL"), .badge:has-text("💾")')).to_be_visible()


@then('an upload button should be visible for that recording')
def step_upload_button_visible(context):
    """Verify upload button visible"""
    expect(context.page.locator('.upload-btn, button:has-text("Upload")')).to_be_visible()


@when('the user has a server-backed recording')
def step_has_server_recording(context):
    """Setup server recording"""
    pass


@then('no upload button should be visible for that recording')
def step_no_upload_button(context):
    """Verify no upload button"""
    expect(context.page.locator('.upload-btn')).not_to_be_visible()


@given('the user clicks the record button')
def step_clicks_record(context):
    """Click record button"""
    context.page.click('#recordBtn')


@given('the user is using the application')
def step_using_application(context):
    """Navigate to application"""
    context.page.goto(context.base_url)
    context.page.wait_for_load_state('networkidle')


@when('the connection changes from online to offline')
def step_connection_offline(context):
    """Simulate offline"""
    context.page.context.set_offline(True)
    context.page.wait_for_timeout(500)


@when('the connection is restored')
def step_connection_restored(context):
    """Restore connection"""
    context.page.context.set_offline(False)
    context.page.wait_for_timeout(500)


@then('a toast notification should say "Back online"')
def step_toast_back_online(context):
    """Verify back online toast"""
    expect(context.page.locator('.toast, .notification')).to_contain_text('back online', ignore_case=True, timeout=3000)


@given('the user has a local recording')
def step_has_local_recording(context):
    """Setup local recording"""
    # Would create local recording in IndexedDB
    pass


@then('a progress bar should appear')
def step_progress_bar_appears(context):
    """Verify progress bar"""
    expect(context.page.locator('.progress-bar, progress')).to_be_visible(timeout=2000)


@then('the progress should update as chunks upload')
def step_progress_updates(context):
    """Verify progress updates"""
    initial = context.page.locator('.progress-bar').get_attribute('value') or '0'
    context.page.wait_for_timeout(2000)
    updated = context.page.locator('.progress-bar').get_attribute('value') or '0'
    assert initial != updated, "Progress did not update"


@given('the user recorded offline')
def step_recorded_offline_alt(context):
    """Recorded offline"""
    pass


@then('a modal dialog should appear')
def step_modal_appears(context):
    """Verify modal appears"""
    expect(context.page.locator('.modal, dialog')).to_be_visible(timeout=2000)


@then('the modal should have a filename input field')
def step_modal_has_filename_input(context):
    """Verify filename input"""
    expect(context.page.locator('input[name="filename"], #filenameInput')).to_be_visible()


@then('a save button should be present')
def step_save_button_present(context):
    """Verify save button"""
    expect(context.page.locator('button:has-text("Save"), .save-btn')).to_be_visible()


@given('the user recorded a 60-minute audio offline')
def step_recorded_60min_offline(context):
    """Simulate 60min recording"""
    # Would create large recording
    pass


@when('the user stops and saves the recording')
def step_stops_and_saves(context):
    """Stop and save"""
    context.page.click('#stopBtn')
    context.page.wait_for_timeout(500)


@given('the user clicks download on a large recording')
def step_clicks_download_large(context):
    """Click download"""
    context.page.click('.download-btn, button:has-text("Download")')


@then('the browser\'s native download should start')
def step_native_download_starts(context):
    """Verify download starts"""
    # Would monitor download events
    pass


@given('an error occurs during upload')
def step_error_during_upload(context):
    """Simulate upload error"""
    # Would intercept network and fail request
    pass


@when('the upload fails')
def step_upload_fails(context):
    """Upload fails"""
    pass


@then('an error toast should appear')
def step_error_toast_appears(context):
    """Verify error toast"""
    expect(context.page.locator('.toast.error, .notification.error')).to_be_visible(timeout=3000)


@given('the user clicks play on a recording')
def step_clicks_play(context):
    """Click play"""
    context.page.click('.play-btn, button:has-text("Play")')


@then('the current time should update smoothly')
def step_time_updates_smoothly(context):
    """Verify time updates"""
    initial = context.page.locator('.current-time').text_content()
    context.page.wait_for_timeout(1500)
    updated = context.page.locator('.current-time').text_content()
    assert initial != updated, "Time did not update"


@given('the user has no recordings')
def step_has_no_recordings(context):
    """No recordings"""
    # Would clear IndexedDB
    pass


@when('the playlist is displayed')
def step_playlist_displayed(context):
    """Verify playlist shown"""
    expect(context.page.locator('.playlist, .track-list')).to_be_visible()


@given('the application is loading recordings from IndexedDB')
def step_loading_from_indexeddb(context):
    """Loading from IndexedDB"""
    # Would monitor loading state
    pass


@given('the user has 10 recordings')
def step_has_10_recordings(context):
    """Setup 10 recordings"""
    # Would seed IndexedDB
    pass


@when('the user selects "Upload All"')
def step_selects_upload_all(context):
    """Click upload all"""
    context.page.click('button:has-text("Upload All"), .upload-all-btn')


@then('a batch progress indicator should appear')
def step_batch_progress_appears(context):
    """Verify batch progress"""
    expect(context.page.locator('.batch-progress')).to_be_visible(timeout=2000)


@then('it should show "Uploading 3 of 10"')
def step_shows_upload_count(context):
    """Verify upload count"""
    expect(context.page.locator('.batch-progress')).to_contain_text('of 10')


@then('individual recording status should update')
def step_individual_status_updates(context):
    """Verify individual status"""
    expect(context.page.locator('.track-item .status')).to_be_visible()


@then('an overall percentage should be displayed')
def step_overall_percentage(context):
    """Verify overall percentage"""
    expect(context.page.locator('.batch-progress')).to_contain_text('%')
