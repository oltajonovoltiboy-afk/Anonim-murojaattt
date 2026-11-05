"""FastAPI barcha asosiy endpointlari testlari."""
from unittest.mock import AsyncMock, patch
import pytest

from app.models import Appeal, Staff, User
from app.services import appeal_service, auth_service
from app.utils.enums import AppealCategory, AppealStatus, StaffRole, UserType


@pytest.mark.asyncio
async def test_appeals_api_flow(async_client, db_session, super_admin: Staff, test_user: User):
    # 1. Murojaat yaratamiz
    draft = appeal_service.AppealDraft(
        full_name="Mahmudov Anvar",
        phone="+998905556677",
        user_type=UserType.STUDENT,
        category=AppealCategory.EDUCATION_QUALITY,
        subject="Dars jadvalidagi o‘zgarishlar",
        text="Assalomu alaykum, dars jadvalini optimallashtirish bo‘yicha taklifim bor edi.",
    )
    appeal = await appeal_service.create_appeal(db_session, test_user, draft)
    await db_session.commit()

    # Super admin uchun token
    token, _, _ = auth_service.create_access_token(super_admin.id, super_admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ro'yxatni olish
    list_resp = await async_client.get("/api/appeals", headers=headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] == 1
    assert data["items"][0]["number"] == appeal.number

    # 3. Murojaat tafsilotlarini olish
    detail_resp = await async_client.get(f"/api/appeals/{appeal.id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["subject"] == appeal.subject

    # 4. Holatni o'zgartirish
    with patch("app.services.notification_service.notify_status_changed", new_callable=AsyncMock) as mock_notify:
        status_resp = await async_client.post(
            f"/api/appeals/{appeal.id}/status",
            headers=headers,
            json={"status": "IN_REVIEW", "comment": "Murojaat ko‘rib chiqilmoqda"},
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["ok"] is True

    # 5. Dashboard statistikasini tekshirish
    dash_resp = await async_client.get("/api/stats/dashboard?period=day", headers=headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["total"] == 1
    assert dash_data["in_review"] == 1

    # 6. Excel hisobot eksporti
    excel_resp = await async_client.get("/api/reports/excel", headers=headers)
    assert excel_resp.status_code == 200
    assert excel_resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(excel_resp.content) > 1000

    # 7. PDF hisobot eksporti
    pdf_resp = await async_client.get("/api/reports/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")
