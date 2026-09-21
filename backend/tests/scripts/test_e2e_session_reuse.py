import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from e2e_validation import reuse_seed_login_token  # noqa: E402


def test_reuse_seed_login_token_when_role_is_the_same_user():
    assert (
        reuse_seed_login_token(
            seed_email="dev@example.com",
            role_email="dev@example.com",
            current_token="jwt-1",
        )
        == "jwt-1"
    )


def test_reuse_seed_login_token_logs_in_when_role_email_differs():
    assert (
        reuse_seed_login_token(
            seed_email="dev@example.com",
            role_email="admin@example.com",
            current_token="jwt-1",
        )
        is None
    )
