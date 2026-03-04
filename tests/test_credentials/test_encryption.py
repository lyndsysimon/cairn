"""Tests for the Fernet-based credential encryption module."""

import pytest

from cairn.credentials.encryption import decrypt_value, derive_key, encrypt_value


class TestDeriveKey:
    def test_returns_bytes(self):
        key = derive_key("my-secret")
        assert isinstance(key, bytes)

    def test_deterministic(self):
        k1 = derive_key("passphrase")
        k2 = derive_key("passphrase")
        assert k1 == k2

    def test_different_passphrases_produce_different_keys(self):
        k1 = derive_key("alpha")
        k2 = derive_key("bravo")
        assert k1 != k2

    def test_empty_passphrase_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            derive_key("")


class TestEncryptDecryptRoundTrip:
    def test_roundtrip(self):
        key = derive_key("test-key")
        plaintext = "super-secret-api-key-12345"
        ciphertext = encrypt_value(plaintext, key)
        assert ciphertext != plaintext.encode("utf-8")
        assert decrypt_value(ciphertext, key) == plaintext

    def test_different_keys_cannot_decrypt(self):
        key_a = derive_key("key-a")
        key_b = derive_key("key-b")
        ciphertext = encrypt_value("secret", key_a)
        with pytest.raises(Exception):
            decrypt_value(ciphertext, key_b)

    def test_unicode_values(self):
        key = derive_key("key")
        plaintext = "p\u00e4ssw\u00f6rd-\U0001f511"
        assert decrypt_value(encrypt_value(plaintext, key), key) == plaintext

    def test_empty_value(self):
        key = derive_key("key")
        # Empty string is a valid plaintext (though unusual for credentials).
        assert decrypt_value(encrypt_value("", key), key) == ""

    def test_ciphertext_is_bytes(self):
        key = derive_key("key")
        ct = encrypt_value("hello", key)
        assert isinstance(ct, bytes)

    def test_each_encryption_produces_different_ciphertext(self):
        key = derive_key("key")
        ct1 = encrypt_value("same", key)
        ct2 = encrypt_value("same", key)
        # Fernet uses a random IV each time.
        assert ct1 != ct2
