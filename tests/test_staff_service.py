"""Xodimlarni boshqarish va huquqlar (RBAC) testlari."""
import pytest

from app.models import Staff
from app.services import staff_service
from app.services.exceptions import ConflictError, PermissionDeniedError, ValidationFailedError
from app.utils.enums import StaffRole


@pytest.mark.asyncio
async def test_create_staff(db_session, super_admin: Staff):
    data = staff_service.StaffInput(
        telegram_id=555666777,
        full_name="Yangi Xodim Dilshod",
        position="Kutubxonachi",
        phone="+998901112233",
        role=StaffRole.STAFF,
    )
    new_staff = await staff_service.create_staff(db_session, super_admin, data)
    await db_session.commit()

    assert new_staff.id is not None
    assert new_staff.role == StaffRole.STAFF
    assert new_staff.full_name == "Yangi Xodim Dilshod"


@pytest.mark.asyncio
async def test_duplicate_telegram_id(db_session, super_admin: Staff):
    data = staff_service.StaffInput(
        telegram_id=super_admin.telegram_id,  # Allaqachon mavjud ID
        full_name="Boshqa Odam",
        role=StaffRole.STAFF,
    )
    with pytest.raises(ConflictError):
        await staff_service.create_staff(db_session, super_admin, data)


@pytest.mark.asyncio
async def test_staff_cannot_create_staff(db_session, test_staff: Staff):
    data = staff_service.StaffInput(
        telegram_id=888999000,
        full_name="O‘qituvchi",
        role=StaffRole.STAFF,
    )
    # Oddiy STAFF yangi xodim qo'sha olmaydi
    with pytest.raises(PermissionDeniedError):
        await staff_service.create_staff(db_session, test_staff, data)


@pytest.mark.asyncio
async def test_ensure_super_admins(db_session):
    ids = [10001, 10002]
    added = await staff_service.ensure_super_admins(db_session, ids)
    assert added == 2

    # Ikkinchi marta chaqirganda qayta qo'shilmasligi kerak (idempotent)
    added_again = await staff_service.ensure_super_admins(db_session, ids)
    assert added_again == 0


@pytest.mark.asyncio
async def test_delete_staff(db_session, super_admin: Staff, test_staff: Staff):
    deleted = await staff_service.delete_staff(db_session, super_admin, test_staff.id)
    await db_session.commit()
    assert deleted.id == test_staff.id

    # O'chirilgach, topilmasligi kerak
    assert await db_session.get(Staff, test_staff.id) is None


@pytest.mark.asyncio
async def test_cannot_delete_self(db_session, super_admin: Staff):
    with pytest.raises(ValidationFailedError):
        await staff_service.delete_staff(db_session, super_admin, super_admin.id)


@pytest.mark.asyncio
async def test_staff_cannot_delete_staff(db_session, test_staff: Staff, super_admin: Staff):
    with pytest.raises(PermissionDeniedError):
        await staff_service.delete_staff(db_session, test_staff, super_admin.id)

