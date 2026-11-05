"""Autentifikatsiya, OTP va REST API testlari."""
from unittest.mock import AsyncMock, patch
import pytest

from app.models import Staff
from app.services import auth_service
from app.utils.enums import StaffRole


@pytest.mark.asyncio
async def test_auth_request_code_and_login(async_client, db_session, super_admin: Staff, fake_redis):
    # Telegram bot xabar yuborishini mock qilamiz
    with patch("app.api.auth.send_login_code", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        # 1. Kod so'rash
        resp = await async_client.post(
            "/api/auth/request-code",
            json={"telegram_id": super_admin.telegram_id},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert mock_send.called

        # Mock chaqiruvidan kodni olamiz
        called_args = mock_send.call_args[0]
        sent_code = called_args[2]
        assert len(sent_code) == 6

        # 2. Kodni kiritib tizimga kirish
        login_resp = await async_client.post(
            "/api/auth/login",
            json={"telegram_id": super_admin.telegram_id, "code": sent_code},
        )
        assert login_resp.status_code == 200
        data = login_resp.json()
        assert data["ok"] is True
        assert "access_token" in data
        assert data["staff"]["role"] == StaffRole.SUPER_ADMIN.value

        # 3. /me endpointi
        token = data["access_token"]
        me_resp = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["telegram_id"] == super_admin.telegram_id


@pytest.mark.asyncio
async def test_unknown_telegram_id_rejected(async_client):
    resp = await async_client.post(
        "/api/auth/request-code",
        json={"telegram_id": 99999999999},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_with_password(async_client, db_session, super_admin: Staff):
    # Parol o'rnatamiz
    super_admin.username = "test_admin"
    super_admin.password_hash = auth_service.hash_password("secret123")
    await db_session.flush()

    # To'g'ri login va parol
    resp = await async_client.post(
        "/api/auth/login-password",
        json={"login": "test_admin", "password": "secret123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["staff"]["username"] == "test_admin"

    # Xato parol
    bad_resp = await async_client.post(
        "/api/auth/login-password",
        json={"login": "test_admin", "password": "wrong_password"},
    )
    assert bad_resp.status_code == 400


@pytest.mark.asyncio
async def test_magic_login(async_client, fake_redis, super_admin: Staff):
    # Magic token generatsiya qilamiz
    token = await auth_service.create_magic_token(fake_redis, super_admin.id)

    # Magic link orqali kirish
    resp = await async_client.get(f"/api/auth/magic-login?token={token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["staff"]["id"] == super_admin.id

    # Token bir marta ishlatilgach o'chirilishi kerak
    second_resp = await async_client.get(f"/api/auth/magic-login?token={token}")
    assert second_resp.status_code == 400


@pytest.mark.asyncio
async def test_update_profile(async_client, super_admin: Staff):
    # JWT token olamiz
    token, _, _ = auth_service.create_access_token(super_admin.id, super_admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Profil va parolni yangilash
    resp = await async_client.put(
        "/api/auth/profile",
        json={
            "full_name": "Anvar Yangilangan",
            "username": "anvar_new",
            "password": "new_secret_password_2026",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["staff"]["username"] == "anvar_new"
    assert data["staff"]["full_name"] == "Anvar Yangilangan"
