"""Provider error policy — user-configured identifier groups and actions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable


class ErrorPolicyCategory(StrEnum):
    ACCOUNT_ERROR = "ACCOUNT_ERROR"
    DELIVERY_ERROR = "DELIVERY_ERROR"
    MESSAGE_ERROR = "MESSAGE_ERROR"


class AccountErrorAction(StrEnum):
    FAIL = "fail"
    DEACTIVATE_AND_FAIL = "deactivate_and_fail"
    RECORD_AND_FAIL = "record_and_fail"


class DeliveryErrorAction(StrEnum):
    AUTO_RETRY = "auto_retry"
    FAIL = "fail"


class MessageErrorAction(StrEnum):
    FAIL = "fail"
    SKIP = "skip"


_CATEGORY_ACTIONS: dict[ErrorPolicyCategory, frozenset[str]] = {
    ErrorPolicyCategory.ACCOUNT_ERROR: frozenset(a.value for a in AccountErrorAction),
    ErrorPolicyCategory.DELIVERY_ERROR: frozenset(a.value for a in DeliveryErrorAction),
    ErrorPolicyCategory.MESSAGE_ERROR: frozenset(a.value for a in MessageErrorAction),
}

_DEFAULT_ACTIONS: dict[ErrorPolicyCategory, str] = {
    ErrorPolicyCategory.ACCOUNT_ERROR: AccountErrorAction.FAIL.value,
    ErrorPolicyCategory.DELIVERY_ERROR: DeliveryErrorAction.FAIL.value,
    ErrorPolicyCategory.MESSAGE_ERROR: MessageErrorAction.FAIL.value,
}


class ProviderErrorPolicyValidationError(ValueError):
    """Raised when error-policy identifiers or actions are invalid."""


def normalize_error_identifiers(raw: Iterable[str] | str | None) -> list[str]:
    """Normalize comma-separated or list identifiers: trim, drop empties, dedupe (order-preserving)."""
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = raw.replace(";", ",").split(",")
    else:
        parts = []
        for item in raw:
            if item is None:
                continue
            parts.extend(str(item).replace(";", ",").split(","))

    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        token = part.strip()
        if not token:
            continue
        if token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


@dataclass(frozen=True)
class ErrorPolicyGroup:
    category: ErrorPolicyCategory
    identifiers: tuple[str, ...]
    action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "identifiers": list(self.identifiers),
            "action": self.action,
        }


@dataclass(frozen=True)
class ProviderErrorPolicy:
    groups: tuple[ErrorPolicyGroup, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"groups": [group.to_dict() for group in self.groups]}

    def identifiers_for(self, category: ErrorPolicyCategory) -> tuple[str, ...]:
        for group in self.groups:
            if group.category == category:
                return group.identifiers
        return ()

    def action_for(self, category: ErrorPolicyCategory) -> str:
        for group in self.groups:
            if group.category == category:
                return group.action
        return _DEFAULT_ACTIONS[category]

    @classmethod
    def default(cls) -> ProviderErrorPolicy:
        return cls(
            groups=tuple(
                ErrorPolicyGroup(
                    category=category,
                    identifiers=(),
                    action=_DEFAULT_ACTIONS[category],
                )
                for category in ErrorPolicyCategory
            )
        )

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> ProviderErrorPolicy:
        if not raw:
            return cls.default()
        groups_raw = raw.get("groups")
        if groups_raw is None and any(key in raw for key in ErrorPolicyCategory):
            # Flat shape: {ACCOUNT_ERROR: {identifiers, action}, ...}
            groups_raw = [
                {
                    "category": category.value,
                    "identifiers": (raw.get(category.value) or {}).get("identifiers", []),
                    "action": (raw.get(category.value) or {}).get(
                        "action", _DEFAULT_ACTIONS[category]
                    ),
                }
                for category in ErrorPolicyCategory
            ]
        if not isinstance(groups_raw, list):
            raise ProviderErrorPolicyValidationError("error_policy.groups must be a list")

        by_category: dict[ErrorPolicyCategory, ErrorPolicyGroup] = {}
        identifier_owners: dict[str, ErrorPolicyCategory] = {}

        for item in groups_raw:
            if not isinstance(item, dict):
                raise ProviderErrorPolicyValidationError("error_policy group must be an object")
            try:
                category = ErrorPolicyCategory(str(item.get("category", "")).strip())
            except ValueError as exc:
                raise ProviderErrorPolicyValidationError(
                    f"Unknown error_policy category: {item.get('category')!r}"
                ) from exc

            if category in by_category:
                raise ProviderErrorPolicyValidationError(
                    f"Duplicate error_policy category: {category.value}"
                )

            identifiers = normalize_error_identifiers(item.get("identifiers"))
            action = str(item.get("action") or _DEFAULT_ACTIONS[category]).strip()
            if action not in _CATEGORY_ACTIONS[category]:
                raise ProviderErrorPolicyValidationError(
                    f"Invalid action {action!r} for {category.value}"
                )

            for identifier in identifiers:
                owner = identifier_owners.get(identifier)
                if owner is not None and owner != category:
                    raise ProviderErrorPolicyValidationError(
                        f"Error identifier {identifier!r} cannot belong to both "
                        f"{owner.value} and {category.value}"
                    )
                identifier_owners[identifier] = category

            by_category[category] = ErrorPolicyGroup(
                category=category,
                identifiers=tuple(identifiers),
                action=action,
            )

        groups = tuple(
            by_category.get(
                category,
                ErrorPolicyGroup(
                    category=category,
                    identifiers=(),
                    action=_DEFAULT_ACTIONS[category],
                ),
            )
            for category in ErrorPolicyCategory
        )
        return cls(groups=groups)


@dataclass(frozen=True)
class ErrorPolicyDecision:
    category: ErrorPolicyCategory | None
    action: str
    retryable: bool
    deactivate_account: bool
    skip_message: bool
    matched_identifier: str | None


def evaluate_error_policy(
    policy: ProviderErrorPolicy | None,
    error_identifier: str | None,
) -> ErrorPolicyDecision:
    """Map a raw provider error identifier to a configured action.

    Unknown / unmatched identifiers fail closed (non-retryable fail).
    """
    resolved = policy or ProviderErrorPolicy.default()
    token = (error_identifier or "").strip()
    if not token:
        return ErrorPolicyDecision(
            category=None,
            action=AccountErrorAction.FAIL.value,
            retryable=False,
            deactivate_account=False,
            skip_message=False,
            matched_identifier=None,
        )

    for group in resolved.groups:
        if token in group.identifiers:
            action = group.action
            return ErrorPolicyDecision(
                category=group.category,
                action=action,
                retryable=action == DeliveryErrorAction.AUTO_RETRY.value,
                deactivate_account=action == AccountErrorAction.DEACTIVATE_AND_FAIL.value,
                skip_message=action == MessageErrorAction.SKIP.value,
                matched_identifier=token,
            )

    return ErrorPolicyDecision(
        category=None,
        action=AccountErrorAction.FAIL.value,
        retryable=False,
        deactivate_account=False,
        skip_message=False,
        matched_identifier=token,
    )
