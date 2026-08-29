#!/usr/bin/env python3
"""P0.2 cross-repo identity lifecycle certification through FAIR CRM.

The test deliberately exercises KYROX Core's real SMTP adapter while keeping
activation/reset tokens only in this process's memory. Mail bodies, raw tokens,
passwords, access tokens, and refresh tokens are never printed or persisted.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import threading
import time
import uuid
from email import policy
from email.parser import BytesParser
from urllib.parse import parse_qs, urlparse

import httpx
from aiosmtpd.controller import Controller

FAIR_BASE = os.environ.get("FAIR_CRM_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
SMTP_HOST = os.environ.get("P0_2_IDENTITY_SMTP_HOST", "127.0.0.1")
SMTP_PORT = int(os.environ.get("P0_2_IDENTITY_SMTP_PORT", "1025"))
REFRESH_COOKIE_NAME = "fair_crm_refresh_token"
CSRF_HEADER = {"X-Fair-CRM-Requested-With": "XMLHttpRequest"}
TOKEN_URL_RE = re.compile(r"https?://[^\s<>]+")


class CertificationError(RuntimeError):
    pass


class MemoryMailbox:
    def __init__(self) -> None:
        self._messages: list[bytes] = []
        self._lock = threading.Lock()

    def add(self, raw_message: bytes | str) -> None:
        raw = raw_message.encode("utf-8") if isinstance(raw_message, str) else bytes(raw_message)
        with self._lock:
            self._messages.append(raw)

    def wait_for_action_token(self, *, recipient: str, path: str, timeout_seconds: float = 15.0) -> str:
        deadline = time.monotonic() + timeout_seconds
        checked = 0
        recipient_lower = recipient.lower()

        while time.monotonic() < deadline:
            with self._lock:
                batch = self._messages[checked:]
                checked = len(self._messages)

            for raw in batch:
                message = BytesParser(policy=policy.default).parsebytes(raw)
                to_header = str(message.get("To", "")).lower()
                if recipient_lower not in to_header:
                    continue

                body_part = message.get_body(preferencelist=("plain",))
                if body_part is None:
                    continue
                body = body_part.get_content()
                for candidate in TOKEN_URL_RE.findall(body):
                    parsed = urlparse(candidate.rstrip(".,);]"))
                    if parsed.path != path:
                        continue
                    token_values = parse_qs(parsed.query).get("token", [])
                    if token_values and token_values[0]:
                        return token_values[0]

            time.sleep(0.1)

        raise CertificationError(f"email action token was not delivered for path={path}")


class MemorySmtpHandler:
    def __init__(self, mailbox: MemoryMailbox) -> None:
        self._mailbox = mailbox

    async def handle_DATA(self, server, session, envelope):  # noqa: N802, ANN001
        self._mailbox.add(envelope.content)
        return "250 Message accepted for in-memory certification"


def require_status(response: httpx.Response, expected: int | set[int], phase: str) -> None:
    expected_set = {expected} if isinstance(expected, int) else expected
    if response.status_code not in expected_set:
        raise CertificationError(f"{phase} returned status={response.status_code}")


def require_access_token(response: httpx.Response, phase: str) -> str:
    try:
        payload = response.json()
    except ValueError as exc:
        raise CertificationError(f"{phase} returned malformed JSON") from exc
    access_token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(access_token, str) or not access_token:
        raise CertificationError(f"{phase} did not return an access token")
    return access_token


def require_refresh_cookie(response: httpx.Response, phase: str) -> str:
    refresh_token = response.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise CertificationError(f"{phase} did not return the refresh cookie")
    return refresh_token


def login(client: httpx.Client, *, email: str, password: str, phase: str) -> tuple[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    require_status(response, 200, phase)
    return require_access_token(response, phase), require_refresh_cookie(response, phase)


def assert_refresh_revoked(refresh_token: str, phase: str) -> None:
    with httpx.Client(base_url=FAIR_BASE, timeout=15.0) as probe:
        response = probe.post(
            "/api/v1/auth/refresh",
            headers=CSRF_HEADER,
            json={"refresh_token": refresh_token},
        )
    require_status(response, 401, phase)


def assert_access_revoked(access_token: str, phase: str) -> None:
    # Deliberately use a wrong current password so a broken revocation check can
    # never mutate credentials. A valid-but-not-revoked token would therefore
    # return a non-401 response and fail certification safely.
    response = httpx.post(
        f"{FAIR_BASE}/api/v1/auth/password/change",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "NotTheCurrentPassword!9000",
            "new_password": "NeverAppliedPassword!9001",
        },
        timeout=15.0,
    )
    require_status(response, 401, phase)


def run_certification(mailbox: MemoryMailbox) -> None:
    run_id = uuid.uuid4().hex[:12]
    email = f"p02-identity-{run_id}@example.com"
    organization_name = f"P0.2 Identity E2E {run_id}"
    organization_slug = f"p02-identity-{run_id}"

    password_1 = f"Aa1!{secrets.token_urlsafe(20)}"
    password_2 = f"Bb2!{secrets.token_urlsafe(20)}"
    password_3 = f"Cc3!{secrets.token_urlsafe(20)}"

    with httpx.Client(base_url=FAIR_BASE, timeout=15.0) as client:
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "organization_name": organization_name,
                "organization_slug": organization_slug,
                "email": email,
            },
        )
        require_status(response, 202, "signup")

        activation_token = mailbox.wait_for_action_token(recipient=email, path="/activate")
        response = client.post(
            "/api/v1/auth/activation/complete",
            json={"token": activation_token, "password": password_1},
        )
        require_status(response, 200, "activation")
        if response.cookies.get(REFRESH_COOKIE_NAME):
            raise CertificationError("activation unexpectedly created a refresh session")

        replay = client.post(
            "/api/v1/auth/activation/complete",
            json={"token": activation_token, "password": password_1},
        )
        require_status(replay, 400, "activation token replay")
        activation_token = ""

        access_1, refresh_1 = login(client, email=email, password=password_1, phase="initial login")

        response = client.post("/api/v1/auth/password/forgot", json={"email": email})
        require_status(response, 202, "forgot password")

        reset_token = mailbox.wait_for_action_token(recipient=email, path="/reset-password")
        response = client.post(
            "/api/v1/auth/password/reset",
            json={"token": reset_token, "password": password_2},
        )
        require_status(response, 200, "password reset")
        if client.cookies.get(REFRESH_COOKIE_NAME):
            raise CertificationError("password reset did not clear the FAIR CRM refresh cookie")

        replay = client.post(
            "/api/v1/auth/password/reset",
            json={"token": reset_token, "password": password_2},
        )
        require_status(replay, 400, "password reset token replay")
        reset_token = ""

        old_password_login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password_1},
        )
        require_status(old_password_login, 401, "old password after reset")
        assert_access_revoked(access_1, "pre-reset access session revocation")
        assert_refresh_revoked(refresh_1, "pre-reset refresh session revocation")
        access_1 = ""
        refresh_1 = ""

        access_2, refresh_2 = login(client, email=email, password=password_2, phase="post-reset login")
        response = client.post(
            "/api/v1/auth/password/change",
            headers={"Authorization": f"Bearer {access_2}"},
            json={"current_password": password_2, "new_password": password_3},
        )
        require_status(response, 200, "password change")
        if client.cookies.get(REFRESH_COOKIE_NAME):
            raise CertificationError("password change did not clear the FAIR CRM refresh cookie")

        old_password_login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password_2},
        )
        require_status(old_password_login, 401, "old password after change")
        assert_access_revoked(access_2, "pre-change access session revocation")
        assert_refresh_revoked(refresh_2, "pre-change refresh session revocation")
        access_2 = ""
        refresh_2 = ""

        final_access, final_refresh = login(
            client,
            email=email,
            password=password_3,
            phase="final login",
        )
        if not final_access or not final_refresh:
            raise CertificationError("final login session material missing")


def main() -> int:
    # Prevent SMTP library chatter from exposing message material if a future
    # dependency changes its default log level.
    logging.getLogger("aiosmtpd").setLevel(logging.CRITICAL)
    logging.getLogger("mail.log").setLevel(logging.CRITICAL)

    mailbox = MemoryMailbox()
    controller = Controller(MemorySmtpHandler(mailbox), hostname=SMTP_HOST, port=SMTP_PORT)

    try:
        controller.start()
        run_certification(mailbox)
    except CertificationError as exc:
        print(f"[FAIL] P0.2 identity lifecycle certification — {exc}")
        return 1
    except Exception as exc:  # Never print exception details: providers may embed sensitive material.
        print(f"[FAIL] P0.2 identity lifecycle certification — unexpected {type(exc).__name__}")
        return 1
    finally:
        try:
            controller.stop()
        except Exception:
            pass

    print("[PASS] P0.2 identity lifecycle certification")
    print("       signup -> activation -> login -> forgot/reset -> login -> change-password -> login")
    print("       one-time tokens and pre-credential-change access/refresh sessions were rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
