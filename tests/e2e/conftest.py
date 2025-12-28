"""
Playwright configuration for E2E tests.

This module configures Playwright for browser automation testing.
"""

import pytest
import os


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context with permissions and fake media."""
    return {
        **browser_context_args,
        "permissions": ["microphone"],
        "viewport": {"width": 1920, "height": 1080},
        "locale": "de-DE",
        "timezone_id": "Europe/Berlin"
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure browser launch arguments."""
    return {
        **browser_type_launch_args,
        "args": [
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            "--mute-audio"
        ]
    }


@pytest.fixture
def browser_context(browser_context):
    """Enhance browser context with request logging."""
    browser_context.on("request", lambda req: print(f"REQ_CTX: {req.method} {req.url}"))
    browser_context.on("response", lambda res: print(f"RES_CTX: {res.status} {res.url}"))
    return browser_context


@pytest.fixture
def page(page):
    """Enhance page fixture with console logging."""
    page.on("console", lambda msg: print(f"BROWSER: {msg.type}: {msg.text}"))
    page.on("pageerror", lambda err: print(f"BROWSER ERROR: {err.message}"))
    return page


@pytest.fixture(scope="session")
def base_url():
    """Get base URL for tests."""
    return os.getenv("TEST_BASE_URL", "http://localhost:8000")
