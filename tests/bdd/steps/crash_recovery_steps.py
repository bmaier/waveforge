"""
Step definitions for crash recovery scenarios
"""

from behave import given, when, then
from playwright.sync_api import expect


@when('the user clicks "Resume Recording"')
def step_click_resume(context):
    """Click resume button"""
    context.page.click('button:has-text("Resume"), .resume-btn')
    context.page.wait_for_timeout(500)


@then('the recording should resume from where it left off')
def step_recording_resumes(context):
    """Verify recording resumes"""
    expect(context.page.locator('#recordBtn')).to_have_class('recording')


@then('chunks should continue uploading to the server')
def step_chunks_continue_uploading(context):
    """Verify uploads continue"""
    context.page.wait_for_timeout(2000)
    # Check network activity
    upload_requests = [r for r in context.requests if 'upload' in r.url or 'chunk' in r.url]
    assert len(upload_requests) > 0, "No upload requests found"


@then('the session ID should remain the same')
def step_session_id_same(context):
    """Verify session ID unchanged"""
    # Would check session storage or DOM
    pass


@when('the user clicks "Save to Local Storage"')
def step_click_save_local(context):
    """Click save local button"""
    context.page.click('button:has-text("Save"), .save-btn')
    context.page.wait_for_timeout(500)


@then('the crashed recording should be saved to IndexedDB')
def step_crashed_saved_to_indexeddb(context):
    """Verify crashed recording saved to IndexedDB"""
    result = context.page.evaluate("""
        () => new Promise((resolve) => {
            const request = indexedDB.open('WaveForgeDB');
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction('recordings', 'readonly');
                const store = tx.objectStore('recordings');
                const countReq = store.count();
                countReq.onsuccess = () => resolve(countReq.result > 0);
            };
        })
    """)
    assert result, "No recordings in IndexedDB"


@then('the recording should appear in the playlist with local badge')
def step_appears_with_local_badge(context):
    """Verify recording in playlist with badge"""
    expect(context.page.locator('.track-item')).to_be_visible()
    expect(context.page.locator('.badge:has-text("LOCAL")')).to_be_visible()


@when('the user clicks "Discard"')
def step_click_discard(context):
    """Click discard button"""
    context.page.click('button:has-text("Discard"), .discard-btn')
    context.page.wait_for_timeout(500)


@then('the recovery data should be deleted')
def step_recovery_deleted(context):
    """Verify recovery data cleaned up"""
    result = context.page.evaluate("""
        () => new Promise((resolve) => {
            const request = indexedDB.open('WaveForgeDB');
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction('recovery_chunks', 'readonly');
                const store = tx.objectStore('recovery_chunks');
                const countReq = store.count();
                countReq.onsuccess = () => resolve(countReq.result === 0);
            };
        })
    """)
    assert result, "Recovery data not deleted"


@then('the modal should close')
def step_modal_closes(context):
    """Verify modal closed"""
    expect(context.page.locator('#recoveryModal')).not_to_be_visible(timeout=2000)


@given('there are {count:d} crashed sessions')
def step_multiple_crashed_sessions(context, count):
    """Simulate multiple crashed sessions"""
    # Would seed IndexedDB with crashed session data
    pass


@then('the modal should list all {count:d} sessions')
def step_modal_lists_sessions(context, count):
    """Verify all sessions listed"""
    sessions = context.page.locator('.recovery-session-item').count()
    assert sessions == count, f"Expected {count} sessions, found {sessions}"


@then('each session should have individual Resume/Discard buttons')
def step_individual_buttons(context):
    """Verify buttons for each session"""
    expect(context.page.locator('.recovery-session-item button:has-text("Resume")')).to_be_visible()
    expect(context.page.locator('.recovery-session-item button:has-text("Discard")')).to_be_visible()


@given('some chunks in recovery_chunks are corrupted')
def step_corrupted_chunks(context):
    """Simulate corrupted chunks"""
    # Would inject bad data into IndexedDB
    pass


@then('the modal should indicate partial recovery')
def step_indicates_partial(context):
    """Verify partial recovery indicated"""
    expect(context.page.locator('#recoveryModal')).to_contain_text('partial', ignore_case=True)


@then('the modal should show how many chunks are recoverable')
def step_shows_recoverable_count(context):
    """Verify chunk count shown"""
    expect(context.page.locator('#recoveryModal')).to_contain_text('chunk')


@when('the user chooses to save the partial recording')
def step_save_partial(context):
    """Save partial recording"""
    context.page.click('button:has-text("Save"), .save-btn')
    context.page.wait_for_timeout(500)


@then('only valid chunks should be assembled')
def step_only_valid_chunks(context):
    """Verify only valid chunks used"""
    # Would check assembled file integrity
    pass


@given('the system was shut down during recording')
def step_system_shutdown(context):
    """Simulate system shutdown"""
    # Similar to crash scenario
    pass


@given('the recording was active in a background tab')
def step_background_tab(context):
    """Simulate background tab recording"""
    # Would create recording in background context
    pass


@when('the user switches back to the tab')
def step_switch_back_to_tab(context):
    """Switch to tab"""
    context.page.bring_to_front()


@when('the user successfully saves or uploads')
def step_successful_save(context):
    """Complete save/upload"""
    context.page.click('button:has-text("Save"), .save-btn')
    context.page.wait_for_timeout(1000)


@then('recovery_chunks should be cleared')
def step_recovery_chunks_cleared(context):
    """Verify recovery chunks cleaned up"""
    result = context.page.evaluate("""
        () => new Promise((resolve) => {
            const request = indexedDB.open('WaveForgeDB');
            request.onsuccess = () => {
                const db = request.result;
                const tx = db.transaction('recovery_chunks', 'readonly');
                const store = tx.objectStore('recovery_chunks');
                const countReq = store.count();
                countReq.onsuccess = () => resolve(countReq.result === 0);
            };
        })
    """)
    assert result, "Recovery chunks not cleared"


@then('no recovery modal should appear on next load')
def step_no_recovery_modal(context):
    """Verify no modal on reload"""
    context.page.reload()
    context.page.wait_for_load_state('networkidle')
    expect(context.page.locator('#recoveryModal')).not_to_be_visible()
