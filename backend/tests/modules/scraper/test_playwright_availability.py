"""Tests for Playwright browser availability helpers."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.modules.scraper.core.browser_service import BrowserConfig
from app.modules.scraper.core.playwright_availability import (
    PLAYWRIGHT_BROWSER_MISSING_MESSAGE,
    PlaywrightBrowserNotInstalledError,
    build_chromium_launch_options,
    ensure_playwright_browser_installed,
    is_playwright_browser_installed,
    looks_like_missing_playwright_browser,
    playwright_browser_unavailable_message,
)


def _install_full_chromium(root: Path, revision: str = "1228") -> Path:
    chromium_dir = root / f"chromium-{revision}" / "chrome-win64"
    chromium_dir.mkdir(parents=True)
    chrome_exe = chromium_dir / "chrome.exe"
    chrome_exe.write_bytes(b"stub")
    return chrome_exe


def _install_headless_shell(root: Path, revision: str = "1228") -> Path:
    shell_dir = root / f"chromium_headless_shell-{revision}" / "chrome-headless-shell-win64"
    shell_dir.mkdir(parents=True)
    shell_exe = shell_dir / "chrome-headless-shell.exe"
    shell_exe.write_bytes(b"stub")
    return shell_exe


def test_channel_config_skips_bundled_chromium_check():
    config = BrowserConfig(channel="msedge")
    assert is_playwright_browser_installed(config) is True
    assert playwright_browser_unavailable_message(config) is None


def test_is_playwright_browser_installed_true_when_only_full_chromium_installed(
    tmp_path, monkeypatch
):
    browsers_root = tmp_path / "ms-playwright"
    _install_full_chromium(browsers_root)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browsers_root))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "unused-local"))

    assert is_playwright_browser_installed(BrowserConfig(headless=True)) is True


def test_is_playwright_browser_installed_true_when_env_invalid_but_default_has_chromium(
    tmp_path, monkeypatch
):
    default_root = tmp_path / "default-ms-playwright"
    _install_full_chromium(default_root)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "missing-sandbox-playwright"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    default_install = tmp_path / "ms-playwright"
    _install_full_chromium(default_install)

    assert is_playwright_browser_installed(BrowserConfig(headless=True)) is True


def test_is_playwright_browser_installed_false_when_no_browsers_found(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "also-empty"))

    assert is_playwright_browser_installed(BrowserConfig(headless=True)) is False


def test_build_chromium_launch_options_uses_full_chromium_when_headless_shell_missing(
    tmp_path, monkeypatch
):
    browsers_root = tmp_path / "ms-playwright"
    chrome_exe = _install_full_chromium(browsers_root)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browsers_root))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "unused-local"))

    options = build_chromium_launch_options(MagicMock(), BrowserConfig(headless=True))

    assert options == {"headless": True, "executable_path": str(chrome_exe)}


def test_build_chromium_launch_options_uses_shell_when_env_invalid(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "missing-sandbox-playwright"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    install_root = tmp_path / "ms-playwright"
    shell_exe = _install_headless_shell(install_root)

    options = build_chromium_launch_options(MagicMock(), BrowserConfig(headless=True))

    assert options == {"headless": True, "executable_path": str(shell_exe)}


def test_build_chromium_launch_options_keeps_default_headless_when_shell_installed(
    tmp_path, monkeypatch
):
    browsers_root = tmp_path / "ms-playwright"
    _install_full_chromium(browsers_root)
    _install_headless_shell(browsers_root)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browsers_root))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "unused-local"))

    options = build_chromium_launch_options(MagicMock(), BrowserConfig(headless=True))

    assert options == {"headless": True}


def test_ensure_playwright_browser_installed_raises_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "missing"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "missing-local"))

    with pytest.raises(PlaywrightBrowserNotInstalledError, match="python -m playwright install"):
        ensure_playwright_browser_installed()


def test_playwright_browser_unavailable_message_returns_install_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "missing"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "missing-local"))

    assert playwright_browser_unavailable_message() == PLAYWRIGHT_BROWSER_MISSING_MESSAGE


@pytest.mark.parametrize(
    "message",
    [
        "Executable doesn't exist at C:/playwright/chromium_headless_shell-1228/chrome-headless-shell.exe",
        "Please run playwright install",
        "browser has not been found",
    ],
)
def test_looks_like_missing_playwright_browser(message: str):
    assert looks_like_missing_playwright_browser(RuntimeError(message)) is True


def test_looks_like_missing_playwright_browser_rejects_unrelated_errors():
    assert looks_like_missing_playwright_browser(RuntimeError("timeout waiting for selector")) is False
