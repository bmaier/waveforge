"""
Playwright configuration for E2E tests.

This module configures Playwright for browser automation testing.
"""

import pytest
from playwright.sync_api import sync_playwright
import os


@pytest.fixture(scope="session")
def browser_context_args():
    """Configure browser context with permissions."""
    return {
        "permissions": ["microphone"],
        "viewport": {"width": 1920, "height": 1080},
        "locale": "de-DE",
        "timezone_id": "Europe/Berlin"
    }


@pytest.fixture(scope="session")
def base_url():
    """Get base URL for tests."""
    return os.getenv("TEST_BASE_URL", "http://localhost:8000")


def before_all(context):
    """Setup Playwright before all tests."""
    context.playwright = sync_playwright().start()
    context.browser = context.playwright.chromium.launch(
        headless=os.getenv("HEADLESS", "true").lower() == "true",
        slow_mo=50  # Slow down actions by 50ms for visibility
    )
    
    context.base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
    print(f"Running E2E tests against: {context.base_url}")


def before_scenario(context, scenario):
    """Setup before each scenario."""
    context.browser_context = context.browser.new_context(
        permissions=["microphone"],
        viewport={"width": 1920, "height": 1080},
        locale="de-DE"
    )
    context.page = context.browser_context.new_page()


def after_scenario(context, scenario):
    """Cleanup after each scenario."""
    if hasattr(context, 'page'):
        context.page.close()
    if hasattr(context, 'browser_context'):
        context.browser_context.close()


def after_all(context):
    """Cleanup after all tests."""
    if hasattr(context, 'browser'):
        context.browser.close()
    if hasattr(context, 'playwright'):
        context.playwright.stop()
    print("E2E tests complete")
