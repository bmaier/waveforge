"""
Behave environment configuration for BDD tests with Playwright
"""

from playwright.sync_api import sync_playwright
import os


def before_all(context):
    """
    Set up Playwright before all tests
    """
    context.playwright = sync_playwright().start()
    context.browser = context.playwright.chromium.launch(
        headless=os.getenv('HEADLESS', 'true').lower() == 'true'
    )
    context.base_url = os.getenv('BASE_URL', 'http://localhost:8000')


def before_scenario(context, scenario):
    """
    Set up a new browser context and page for each scenario
    """
    context.browser_context = context.browser.new_context(
        viewport={'width': 1280, 'height': 720},
        permissions=['microphone'],
        record_video_dir='test-results/videos/' if os.getenv('RECORD_VIDEO') else None
    )
    context.page = context.browser_context.new_page()
    
    # Set up console message capture
    context.console_messages = []
    context.page.on('console', lambda msg: context.console_messages.append(msg))
    
    # Set up network request tracking
    context.requests = []
    context.page.on('request', lambda request: context.requests.append(request))
    
    # Initialize timing tracking for connection loss scenarios
    context.last_event_time = 0
    context.record_start_time = None
    context.stop_time = None
    context.play_start_time = None
    context.download = None
    context.filename = None
    context.network_unstable = False


def after_scenario(context, scenario):
    """
    Clean up after each scenario
    """
    if hasattr(context, 'page'):
        # Take screenshot on failure
        if scenario.status == 'failed':
            screenshot_dir = 'test-results/screenshots'
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = f"{screenshot_dir}/{scenario.name.replace(' ', '_')}.png"
            context.page.screenshot(path=screenshot_path)
            print(f"Screenshot saved: {screenshot_path}")
        
        context.page.close()
    
    if hasattr(context, 'browser_context'):
        context.browser_context.close()


def after_all(context):
    """
    Clean up Playwright after all tests
    """
    if hasattr(context, 'browser'):
        context.browser.close()
    if hasattr(context, 'playwright'):
        context.playwright.stop()
