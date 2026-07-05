from app.shared.secret_encryption import decrypt_secret, encrypt_secret, is_encrypted_secret


def test_encrypt_secret_roundtrip():
    encrypted = encrypt_secret("my-smtp-password")
    assert encrypted is not None
    assert is_encrypted_secret(encrypted)
    assert decrypt_secret(encrypted) == "my-smtp-password"


def test_decrypt_legacy_plaintext_passthrough():
    assert decrypt_secret("legacy-plain") == "legacy-plain"
    assert not is_encrypted_secret("legacy-plain")


def test_encrypt_none_and_empty():
    assert encrypt_secret(None) is None
    assert encrypt_secret("") == ""
