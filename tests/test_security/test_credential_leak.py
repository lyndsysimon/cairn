"""Tests for CredentialLeakDetector middleware."""

import base64

import pytest

from cairn.security.credential_leak import CredentialLeakDetector


@pytest.fixture
def detector():
    return CredentialLeakDetector()


class TestInspectOutbound:
    async def test_redacts_literal_credential(self, detector):
        prompt = "Use API key sk-abc123xyz to authenticate"
        result = await detector.inspect_outbound(prompt, ["sk-abc123xyz"])
        assert "sk-abc123xyz" not in result
        assert "[REDACTED]" in result
        assert "Use API key [REDACTED] to authenticate" == result

    async def test_redacts_multiple_credentials(self, detector):
        prompt = "key1=secret-aaa key2=secret-bbb"
        result = await detector.inspect_outbound(prompt, ["secret-aaa", "secret-bbb"])
        assert "secret-aaa" not in result
        assert "secret-bbb" not in result
        assert result == "key1=[REDACTED] key2=[REDACTED]"

    async def test_redacts_multiple_occurrences(self, detector):
        prompt = "token=ABCD1234 and also ABCD1234 again"
        result = await detector.inspect_outbound(prompt, ["ABCD1234"])
        assert result.count("[REDACTED]") == 2
        assert "ABCD1234" not in result

    async def test_skips_short_credentials(self, detector):
        prompt = "set x=abc and y=de"
        # "abc" is 3 chars → skipped (min is 4). "de" is 2 → skipped.
        result = await detector.inspect_outbound(prompt, ["abc", "de"])
        assert result == prompt  # unchanged

    async def test_four_char_credential_is_detected(self, detector):
        prompt = "key=abcd"
        result = await detector.inspect_outbound(prompt, ["abcd"])
        assert result == "key=[REDACTED]"

    async def test_case_sensitive(self, detector):
        prompt = "Token is MySecret not mysecret"
        result = await detector.inspect_outbound(prompt, ["MySecret"])
        assert "MySecret" not in result
        assert "mysecret" in result  # lowercase not redacted

    async def test_longer_credential_redacted_first(self, detector):
        # "secret-long-key" contains "secret" as substring.
        # Longer value should be redacted first to avoid partial match.
        prompt = "cred=secret-long-key"
        result = await detector.inspect_outbound(prompt, ["secret", "secret-long-key"])
        assert result == "cred=[REDACTED]"

    async def test_no_credentials(self, detector):
        prompt = "just a normal prompt"
        result = await detector.inspect_outbound(prompt, [])
        assert result == prompt

    async def test_empty_prompt(self, detector):
        result = await detector.inspect_outbound("", ["secret"])
        assert result == ""

    async def test_no_leak_returns_unchanged(self, detector):
        prompt = "a normal prompt with no secrets"
        result = await detector.inspect_outbound(prompt, ["not-present-value"])
        assert result == prompt


class TestBase64Detection:
    async def test_redacts_base64_encoded_credential(self, detector):
        secret = "my-api-key-12345"
        encoded = base64.b64encode(secret.encode()).decode()
        prompt = f"Authorization: Basic {encoded}"
        result = await detector.inspect_outbound(prompt, [secret])
        assert encoded not in result
        assert "[REDACTED]" in result

    async def test_redacts_urlsafe_base64(self, detector):
        # A secret that produces different output for urlsafe vs standard b64
        secret = "key+with/special=chars"
        urlsafe = base64.urlsafe_b64encode(secret.encode()).decode()
        standard = base64.b64encode(secret.encode()).decode()
        prompt = f"token={urlsafe} also {standard}"
        result = await detector.inspect_outbound(prompt, [secret])
        assert urlsafe not in result
        assert standard not in result

    async def test_redacts_base64_without_padding(self, detector):
        secret = "test-secret"
        encoded = base64.b64encode(secret.encode()).decode()
        stripped = encoded.rstrip("=")
        # Ensure stripping actually removed something for this test to be meaningful
        assert stripped != encoded or len(encoded) % 4 == 0
        prompt = f"data={stripped}"
        result = await detector.inspect_outbound(prompt, [secret])
        assert stripped not in result


class TestInboundPassthrough:
    async def test_returns_content_unchanged(self, detector):
        content, warnings = await detector.inspect_inbound("anything here")
        assert content == "anything here"
        assert warnings == []
