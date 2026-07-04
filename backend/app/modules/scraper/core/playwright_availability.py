"""Playwright bundled browser availability checks (no auto-install)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings

if TYPE_CHECKING:
    from app.modules.scraper.core.browser_service import BrowserConfig

logger = logging.getLogger(__name__)

PLAYWRIGHT_BROWSER_MISSING_MESSAGE = (
    "Playwright browser kurulu değil. Local için: python -m playwright install"
)

_HEADLESS_SHELL_DIR_GLOB = "chromium_headless_shell-*"
_HEADLESS_SHELL_EXECUTABLE_NAMES = (
    "chrome-headless-shell.exe",
    "chrome-headless-shell",
)
_FULL_CHROMIUM_DIR_GLOB = "chromium-*"
_FULL_CHROMIUM_EXECUTABLE_NAMES = (
    "chrome.exe",
    "chrome",
)


class PlaywrightBrowserNotInstalledError(RuntimeError):
    """Raised when Playwright bundled Chromium is required but not installed."""

    def __init__(self) -> None:
        super().__init__(PLAYWRIGHT_BROWSER_MISSING_MESSAGE)


def _default_ms_playwright_root() -> Path:
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def _is_playwright_env_root_invalid() -> bool:
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if not env_path or env_path == "0":
        return False
    root = Path(env_path)
    if not root.is_dir():
        return True
    return _find_full_chromium_executable(root) is None


def _find_headless_shell_executable(browsers_root: Path) -> Path | None:
    if not browsers_root.is_dir():
        return None
    for directory in browsers_root.glob(_HEADLESS_SHELL_DIR_GLOB):
        for name in _HEADLESS_SHELL_EXECUTABLE_NAMES:
            for candidate in directory.rglob(name):
                if candidate.is_file():
                    return candidate
    return None


def _find_full_chromium_executable(browsers_root: Path) -> Path | None:
    if not browsers_root.is_dir():
        return None
    for directory in browsers_root.glob(_FULL_CHROMIUM_DIR_GLOB):
        if "headless_shell" in directory.name:
            continue
        for name in _FULL_CHROMIUM_EXECUTABLE_NAMES:
            for candidate in directory.rglob(name):
                if candidate.is_file():
                    return candidate
    return None


def _resolve_installed_chromium_paths() -> tuple[Path | None, Path | None]:
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if env_path and env_path != "0":
        root = Path(env_path)
        if root.is_dir():
            full_chromium = _find_full_chromium_executable(root)
            headless_shell = _find_headless_shell_executable(root)
            if full_chromium is not None or headless_shell is not None:
                return full_chromium, headless_shell

    default_root = _default_ms_playwright_root()
    if default_root.is_dir():
        return (
            _find_full_chromium_executable(default_root),
            _find_headless_shell_executable(default_root),
        )
    return None, None


def _is_chromium_launch_ready(config: BrowserConfig) -> bool:
    if config.channel:
        return True

    full_chromium, headless_shell = _resolve_installed_chromium_paths()
    if not config.headless:
        return full_chromium is not None

    if headless_shell is not None:
        return True
    return full_chromium is not None


def build_chromium_launch_options(playwright: Any, config: BrowserConfig) -> dict[str, Any]:
    """Build Playwright launch options aligned with installed browser bundles."""
    _ = playwright
    launch_options: dict[str, Any] = {"headless": config.headless}
    if config.channel:
        launch_options["channel"] = config.channel
        return launch_options

    if not config.headless:
        return launch_options

    full_chromium, headless_shell = _resolve_installed_chromium_paths()
    env_root_invalid = _is_playwright_env_root_invalid()

    if not env_root_invalid and headless_shell is not None:
        return launch_options

    if headless_shell is not None and env_root_invalid:
        launch_options["executable_path"] = str(headless_shell)
        return launch_options

    if full_chromium is not None:
        launch_options["executable_path"] = str(full_chromium)
    return launch_options


def is_playwright_browser_installed(config: BrowserConfig | None = None) -> bool:
    """Return True when scraper launch can proceed without `playwright install`."""
    if config is None:
        from app.modules.scraper.core.browser_service import BrowserConfig

        cfg: BrowserConfig = BrowserConfig()
    else:
        cfg = config
    return _is_chromium_launch_ready(cfg)


def ensure_playwright_browser_installed(config: BrowserConfig | None = None) -> None:
    if not is_playwright_browser_installed(config):
        raise PlaywrightBrowserNotInstalledError()


def looks_like_missing_playwright_browser(exc: BaseException) -> bool:
    message = str(exc).casefold()
    return (
        "executable doesn't exist" in message
        or "playwright install" in message
        or "browser has not been found" in message
        or "chromium_headless_shell" in message
    )


def log_playwright_browser_startup_check() -> None:
    from app.modules.scraper.core.browser_service import BrowserConfig

    settings = get_settings()
    config = BrowserConfig.from_settings(settings)
    if is_playwright_browser_installed(config):
        return
    logger.warning(PLAYWRIGHT_BROWSER_MISSING_MESSAGE)


def playwright_browser_unavailable_message(config: BrowserConfig | None = None) -> str | None:
    if is_playwright_browser_installed(config):
        return None
    return PLAYWRIGHT_BROWSER_MISSING_MESSAGE
