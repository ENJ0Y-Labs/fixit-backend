from app.core.security import digest_secret, hash_password, new_secret, verify_password

def test_argon2_password_hash_verifies_and_is_not_plaintext() -> None:
    password = "correct horse battery staple"
    encoded = hash_password(password)
    assert encoded != password
    assert encoded.startswith("$argon2id$")
    assert verify_password(encoded, password)
    assert not verify_password(encoded, "wrong password")

def test_auth_secrets_are_random_and_only_digests_are_persisted() -> None:
    first = new_secret()
    second = new_secret()
    assert first != second
    assert digest_secret(first) != first
    assert digest_secret(first) != digest_secret(second)
