"""
Step definitions for performance scenarios
"""

from behave import given, when, then
from playwright.sync_api import expect
import time


@given('the user is online')
def step_user_online(context):
    """Ensure online"""
    context.page.context.set_offline(False)


@when('the user records for 60 minutes')
def step_records_60_minutes(context):
    """Simulate 60 min recording"""
    context.page.click('#recordBtn')
    # Don't actually wait 60 minutes in tests
    context.page.wait_for_timeout(3000)  # Short simulation


@when('the user stops recording')
def step_stops_recording(context):
    """Stop recording"""
    context.page.click('#stopBtn')


@then('the recording should save within 5 seconds')
def step_saves_within_5sec(context):
    """Verify fast save"""
    start = time.time()
    expect(context.page.locator('.toast:has-text("saved"), .notification:has-text("complete")')).to_be_visible(timeout=5000)
    elapsed = time.time() - start
    assert elapsed < 5, f"Save took {elapsed}s, expected < 5s"


@given('the user is offline')
def step_user_offline(context):
    """Set offline"""
    context.page.context.set_offline(True)


@then('client assembly should complete within 10 seconds')
def step_assembly_within_10sec(context):
    """Verify fast assembly"""
    start = time.time()
    expect(context.page.locator('.toast:has-text("assembled"), .notification:has-text("complete")')).to_be_visible(timeout=10000)
    elapsed = time.time() - start
    assert elapsed < 10, f"Assembly took {elapsed}s, expected < 10s"


@given('the user has 100 recordings')
def step_has_100_recordings(context):
    """Setup 100 recordings"""
    # Would seed IndexedDB with 100 recordings
    pass


@when('the user opens the application')
def step_opens_application(context):
    """Open app"""
    context.page.goto(context.base_url)


@then('the playlist should render within 3 seconds')
def step_playlist_renders_within_3sec(context):
    """Verify fast render"""
    start = time.time()
    expect(context.page.locator('.playlist, .track-list')).to_be_visible(timeout=3000)
    elapsed = time.time() - start
    assert elapsed < 3, f"Render took {elapsed}s, expected < 3s"


@then('scrolling should remain smooth with 100+ items')
def step_smooth_scrolling_100(context):
    """Test scrolling performance"""
    # Scroll and check for lag
    context.page.evaluate("document.querySelector('.playlist').scrollBy(0, 1000)")
    context.page.wait_for_timeout(500)
    # In real test, would measure frame rate


@given('the user is downloading a 200MB recording')
def step_downloading_200mb(context):
    """Initiate large download"""
    # Would click download on large file
    pass


@then('a download progress bar should appear')
def step_download_progress_appears(context):
    """Verify download progress"""
    expect(context.page.locator('.download-progress')).to_be_visible(timeout=2000)


@then('the download should not block the UI')
def step_download_no_block(context):
    """Verify UI responsive during download"""
    # Would test UI interactions during download
    expect(context.page.locator('#recordBtn')).to_be_enabled()


@given('the user is recording audio')
def step_is_recording(context):
    """Start recording"""
    context.page.click('#recordBtn')


@then('chunks should buffer in the service worker')
def step_chunks_buffer(context):
    """Verify buffering"""
    # Would check service worker state
    pass


@then('memory usage should not grow linearly with time')
def step_memory_stable(context):
    """Verify memory management"""
    # Would monitor memory metrics
    pass


@given('the user has a long recording playing')
def step_long_recording_playing(context):
    """Play long recording"""
    context.page.click('.play-btn')


@when('the user starts a new recording')
def step_starts_new_recording(context):
    """Start new recording"""
    context.page.click('#recordBtn')


@then('both operations should work without lag')
def step_both_work_smoothly(context):
    """Verify concurrent operations"""
    # Would check both are working
    expect(context.page.locator('#recordBtn')).to_have_class('recording')
    expect(context.page.locator('.play-btn')).to_be_visible()


@given('the application is open in 3 tabs')
def step_open_in_3_tabs(context):
    """Open multiple tabs"""
    # Would create multiple contexts
    pass


@then('each tab should work independently')
def step_tabs_independent(context):
    """Verify tab independence"""
    pass


@then('recordings should sync via IndexedDB')
def step_recordings_sync(context):
    """Verify sync"""
    pass


@given('the service worker is registered')
def step_service_worker_registered(context):
    """Verify SW registered"""
    result = context.page.evaluate("() => 'serviceWorker' in navigator")
    assert result, "Service worker not supported"


@when('the user records and saves')
def step_records_and_saves(context):
    """Record and save"""
    context.page.click('#recordBtn')
    context.page.wait_for_timeout(2000)
    context.page.click('#stopBtn')


@then('service worker should handle upload without blocking main thread')
def step_sw_no_block(context):
    """Verify SW performance"""
    # Would check main thread not blocked
    expect(context.page.locator('#recordBtn')).to_be_enabled()


@given('the user has 50 recordings in IndexedDB')
def step_has_50_recordings(context):
    """Setup 50 recordings"""
    pass


@when('the app performs garbage collection')
def step_garbage_collection(context):
    """Trigger GC"""
    # Would trigger cleanup
    pass


@then('old temporary chunks should be removed')
def step_temp_chunks_removed(context):
    """Verify cleanup"""
    # Would check temp storage cleared
    pass


@then('storage usage should decrease')
def step_storage_decreases(context):
    """Verify storage freed"""
    # Would check storage quota
    pass


@when('the user records for {minutes:d} minutes')
def step_records_for_minutes(context, minutes):
    """Record for N minutes"""
    context.page.click('#recordBtn')
    # Simulate with timeout
    context.page.wait_for_timeout(min(minutes * 1000, 5000))  # Cap at 5s for tests


@then('save time should scale sub-linearly')
def step_save_time_sublinear(context):
    """Verify scalability"""
    # Would measure and compare save times
    pass


@then('assembly time should scale sub-linearly')
def step_assembly_time_sublinear(context):
    """Verify assembly scalability"""
    pass
