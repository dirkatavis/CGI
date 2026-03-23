import pytest
from selenium.common.exceptions import WebDriverException
from unittest.mock import Mock

from core import driver_manager as dm


@pytest.fixture(autouse=True)
def reset_driver_state():
    dm.quit_driver()
    yield
    dm.quit_driver()


def test_create_driver_uses_selenium_manager_as_primary(monkeypatch):
    """Selenium Manager (no explicit service) is always tried first."""
    monkeypatch.setattr(dm, "get_browser_version", lambda: "141.0.3537.57")
    monkeypatch.setattr(dm, "get_driver_version", lambda path: "141.0.3537.57")

    calls = []
    created_driver = Mock()

    def fake_edge(**kwargs):  # pylint: disable=unused-argument
        calls.append({"service": kwargs.get("service")})
        return created_driver

    monkeypatch.setattr(dm.webdriver, "Edge", fake_edge)

    assert dm.create_driver() is created_driver
    assert len(calls) == 1
    assert calls[0]["service"] is None


def test_create_driver_still_uses_selenium_manager_when_bundled_is_stale(monkeypatch):
    """Even when the bundled driver is outdated, Selenium Manager is primary."""
    monkeypatch.setattr(dm, "get_browser_version", lambda: "141.0.3537.57")
    monkeypatch.setattr(dm, "get_driver_version", lambda path: "130.0.2849.68")

    calls = []
    created_driver = Mock()

    def fake_edge(**kwargs):  # pylint: disable=unused-argument
        calls.append({"service": kwargs.get("service")})
        return created_driver

    monkeypatch.setattr(dm.webdriver, "Edge", fake_edge)

    assert dm.create_driver() is created_driver
    assert len(calls) == 1
    assert calls[0]["service"] is None


def test_create_driver_falls_back_to_bundled_driver_when_selenium_manager_fails(monkeypatch):
    """Bundled driver is used only when Selenium Manager raises."""
    monkeypatch.setattr(dm, "get_browser_version", lambda: "141.0.3537.57")
    monkeypatch.setattr(dm, "get_driver_version", lambda path: "141.0.3537.57")

    calls = []
    bundled_service = object()
    created_driver = Mock()
    responses = iter([WebDriverException("manager unavailable"), created_driver])

    monkeypatch.setattr(dm, "Service", lambda path: bundled_service)

    def fake_edge(**kwargs):  # pylint: disable=unused-argument
        calls.append({"service": kwargs.get("service")})
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(dm.webdriver, "Edge", fake_edge)

    assert dm.create_driver() is created_driver
    assert len(calls) == 2
    assert calls[0]["service"] is None         # Selenium Manager tried first
    assert calls[1]["service"] is bundled_service  # bundled fallback used
