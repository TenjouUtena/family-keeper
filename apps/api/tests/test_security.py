import uuid

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("mysecretpassword")
        assert hashed != "mysecretpassword"
        assert verify_password("mysecretpassword", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("mysecretpassword")
        assert not verify_password("wrongpassword", hashed)

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses unique salts


class TestJWT:
    def test_create_access_token(self):
        user_id = uuid.uuid4()
        token, jti = create_access_token(user_id)
        assert token
        assert jti

        payload = decode_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert payload["jti"] == jti

    def test_create_refresh_token(self):
        user_id = uuid.uuid4()
        raw, token_hash = create_refresh_token(user_id)
        assert raw
        assert token_hash

        payload = decode_token(raw)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        with pytest.raises(Exception):
            decode_token("garbage.token.here")

    def test_hash_token_deterministic(self):
        token = "some-raw-token"
        assert hash_token(token) == hash_token(token)

    def test_hash_token_different_for_different_inputs(self):
        assert hash_token("token-a") != hash_token("token-b")


class TestTokenBlacklist:
    async def test_blacklist_and_check(self):
        from app.core.security import blacklist_token, is_token_blacklisted

        jti = "test-jti-123"
        assert not await is_token_blacklisted(jti)
        await blacklist_token(jti, 300)
        assert await is_token_blacklisted(jti)

    async def test_non_blacklisted_token(self):
        from app.core.security import is_token_blacklisted

        assert not await is_token_blacklisted("never-blacklisted")
