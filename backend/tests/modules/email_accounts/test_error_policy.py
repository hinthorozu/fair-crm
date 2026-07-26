"""Provider error policy unit tests."""

from __future__ import annotations

import pytest

from app.modules.email_accounts.domain.error_policy import (
    AccountErrorAction,
    DeliveryErrorAction,
    ErrorPolicyCategory,
    MessageErrorAction,
    ProviderErrorPolicy,
    ProviderErrorPolicyValidationError,
    evaluate_error_policy,
    normalize_error_identifiers,
)


def test_normalize_identifiers_trims_dedupes_and_accepts_strings():
    assert normalize_error_identifiers(" 401, 403,401, AccountSuspendedException , ") == [
        "401",
        "403",
        "AccountSuspendedException",
    ]
    assert normalize_error_identifiers(["429", " 500 ", "429"]) == ["429", "500"]


def test_policy_rejects_cross_group_duplicate_identifiers():
    with pytest.raises(ProviderErrorPolicyValidationError, match="cannot belong"):
        ProviderErrorPolicy.from_dict(
            {
                "groups": [
                    {
                        "category": "ACCOUNT_ERROR",
                        "identifiers": ["401", "403"],
                        "action": AccountErrorAction.FAIL.value,
                    },
                    {
                        "category": "DELIVERY_ERROR",
                        "identifiers": ["401", "503"],
                        "action": DeliveryErrorAction.AUTO_RETRY.value,
                    },
                    {
                        "category": "MESSAGE_ERROR",
                        "identifiers": ["422"],
                        "action": MessageErrorAction.FAIL.value,
                    },
                ]
            }
        )


def test_evaluate_matches_numeric_and_string_and_fail_closed():
    policy = ProviderErrorPolicy.from_dict(
        {
            "groups": [
                {
                    "category": "ACCOUNT_ERROR",
                    "identifiers": ["401", "AccountSuspendedException"],
                    "action": AccountErrorAction.DEACTIVATE_AND_FAIL.value,
                },
                {
                    "category": "DELIVERY_ERROR",
                    "identifiers": ["429", "503"],
                    "action": DeliveryErrorAction.AUTO_RETRY.value,
                },
                {
                    "category": "MESSAGE_ERROR",
                    "identifiers": ["422"],
                    "action": MessageErrorAction.SKIP.value,
                },
            ]
        }
    )

    account = evaluate_error_policy(policy, "401")
    assert account.category == ErrorPolicyCategory.ACCOUNT_ERROR
    assert account.deactivate_account is True
    assert account.retryable is False

    delivery = evaluate_error_policy(policy, "429")
    assert delivery.retryable is True
    assert delivery.category == ErrorPolicyCategory.DELIVERY_ERROR

    message = evaluate_error_policy(policy, "422")
    assert message.skip_message is True

    unknown = evaluate_error_policy(policy, "999")
    assert unknown.category is None
    assert unknown.retryable is False
    assert unknown.deactivate_account is False
