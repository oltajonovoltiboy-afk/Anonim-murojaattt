"""Rollarga asoslangan ruxsatlar (RBAC).

SUPER ADMIN  — hamma narsa, shu jumladan sozlamalar va boshqa adminlarni boshqarish.
ADMINISTRATOR — barcha murojaatlarni ko'radi, taqsimlaydi, nazorat qiladi,
                mas'ul xodimlarni boshqaradi, hisobot va audit jurnalini ko'radi.
MAS'UL XODIM — faqat o'ziga biriktirilgan murojaatlarni ko'radi va ular ustida ishlaydi.
"""
from __future__ import annotations

from app.models import Appeal, Staff
from app.services.exceptions import PermissionDeniedError
from app.utils.enums import StaffRole


def can_view_all_appeals(staff: Staff) -> bool:
    return staff.is_admin


def can_view_appeal(staff: Staff, appeal: Appeal) -> bool:
    return staff.is_admin or appeal.assigned_staff_id == staff.id


def can_work_on_appeal(staff: Staff, appeal: Appeal) -> bool:
    """Holat o'zgartirish, javob yozish, qo'shimcha ma'lumot so'rash."""
    return staff.is_admin or appeal.assigned_staff_id == staff.id


def can_assign(staff: Staff) -> bool:
    return staff.is_admin


def can_reopen(staff: Staff) -> bool:
    return staff.is_admin


def can_export_reports(staff: Staff) -> bool:
    return staff.is_admin


def can_view_audit(staff: Staff) -> bool:
    return staff.is_admin


def can_manage_users(staff: Staff) -> bool:
    """Telegram foydalanuvchilarini bloklash/blokdan chiqarish."""
    return staff.is_admin


def can_edit_settings(staff: Staff) -> bool:
    return staff.is_super_admin


def can_view_staff_list(staff: Staff) -> bool:
    return staff.is_admin


def can_manage_staff_role(actor: Staff, role: StaffRole) -> bool:
    """actor shu roldagi xodimni yaratishi/tahrirlashi mumkinmi."""
    if actor.is_super_admin:
        return True
    if actor.role == StaffRole.ADMIN:
        return role == StaffRole.STAFF
    return False


def require(condition: bool, message: str = "Bu amal uchun ruxsatingiz yo‘q.") -> None:
    if not condition:
        raise PermissionDeniedError(message)
