from __future__ import annotations

from uuid import UUID, uuid4

from app.modules.email_accounts.application.account_ref import (
    coalesce_account_id,
    resolve_email_account_id,
    stamp_email_account_id,
)


def test_coalesce_parses_email_account_id():
    email_id = uuid4()

    assert coalesce_account_id(email_account_id=email_id) == email_id


def test_coalesce_returns_none_when_missing():
    assert coalesce_account_id() is None
    assert coalesce_account_id(email_account_id=None) is None


def test_coalesce_parses_string_uuids():
    email_id = uuid4()

    assert coalesce_account_id(email_account_id=str(email_id)) == email_id


def test_resolve_reads_email_account_id_only():
    email_id = uuid4()
    payload = {
        "email_account_id": str(email_id),
        "template_id": str(uuid4()),
    }

    assert resolve_email_account_id(payload) == email_id


def test_resolve_returns_none_for_empty_payload():
    assert resolve_email_account_id(None) is None
    assert resolve_email_account_id({}) is None


def test_stamp_writes_email_account_id():
    account_id = uuid4()
    payload = {"other": 1}

    stamped = stamp_email_account_id(payload, account_id)

    assert stamped["email_account_id"] == str(account_id)
    assert stamped["other"] == 1
    assert payload.get("email_account_id") is None  # original unchanged


def test_stamp_none_account_id():
    stamped = stamp_email_account_id({"other": 1}, None)

    assert stamped["email_account_id"] is None
    assert stamped["other"] == 1


def test_stamp_returns_new_dict():
    original = {"a": 1}
    stamped = stamp_email_account_id(original, uuid4())

    assert stamped is not original
    assert isinstance(stamped["email_account_id"], str)
    UUID(stamped["email_account_id"])  # valid UUID string
