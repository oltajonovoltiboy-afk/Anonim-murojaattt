"""Tizimdagi barcha sanab o'tiladigan qiymatlar (enum) va ularning o'zbekcha nomlari."""
from __future__ import annotations

import enum


class StrEnum(str, enum.Enum):
    def __str__(self) -> str:  # pragma: no cover - qulaylik uchun
        return self.value


class UserType(StrEnum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    PARENT = "PARENT"
    CITIZEN = "CITIZEN"


class AppealCategory(StrEnum):
    EDUCATION_QUALITY = "EDUCATION_QUALITY"
    TEACHERS = "TEACHERS"
    STUDENTS = "STUDENTS"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    SUGGESTION = "SUGGESTION"
    COMPLAINT = "COMPLAINT"
    OTHER = "OTHER"


class AppealStatus(StrEnum):
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    IN_REVIEW = "IN_REVIEW"
    INFO_REQUESTED = "INFO_REQUESTED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class StaffRole(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    STAFF = "STAFF"


class MessageDirection(StrEnum):
    STAFF_TO_USER = "STAFF_TO_USER"  # Xodim javobi / qo'shimcha ma'lumot so'rovi
    USER_TO_STAFF = "USER_TO_STAFF"  # Foydalanuvchining qo'shimcha ma'lumoti


class MessageKind(StrEnum):
    REPLY = "REPLY"
    INFO_REQUEST = "INFO_REQUEST"
    INFO_RESPONSE = "INFO_RESPONSE"


class AttachmentType(StrEnum):
    PHOTO = "PHOTO"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"


class ActorType(StrEnum):
    USER = "USER"
    STAFF = "STAFF"
    SYSTEM = "SYSTEM"


USER_TYPE_LABELS: dict[UserType, str] = {
    UserType.STUDENT: "🎓 O‘quvchi",
    UserType.TEACHER: "👨‍🏫 O‘qituvchi",
    UserType.PARENT: "👨‍👩‍👧 Ota-ona",
    UserType.CITIZEN: "🏛 Boshqa fuqaro",
}

CATEGORY_LABELS: dict[AppealCategory, str] = {
    AppealCategory.EDUCATION_QUALITY: "📚 Ta'lim sifati",
    AppealCategory.TEACHERS: "👨‍🏫 O‘qituvchilar faoliyati",
    AppealCategory.STUDENTS: "🎒 O‘quvchilar masalalari",
    AppealCategory.INFRASTRUCTURE: "🏢 Sharoit va infratuzilma",
    AppealCategory.SUGGESTION: "💡 Taklif",
    AppealCategory.COMPLAINT: "⚠️ Shikoyat",
    AppealCategory.OTHER: "📌 Boshqa masalalar",
}

STATUS_LABELS: dict[AppealStatus, str] = {
    AppealStatus.NEW: "Yangi",
    AppealStatus.ACCEPTED: "Qabul qilindi",
    AppealStatus.IN_REVIEW: "Ko‘rib chiqilmoqda",
    AppealStatus.INFO_REQUESTED: "Qo‘shimcha ma'lumot so‘raldi",
    AppealStatus.RESOLVED: "Hal qilindi",
    AppealStatus.REJECTED: "Rad etildi",
}

STATUS_EMOJI: dict[AppealStatus, str] = {
    AppealStatus.NEW: "🆕",
    AppealStatus.ACCEPTED: "📥",
    AppealStatus.IN_REVIEW: "🔄",
    AppealStatus.INFO_REQUESTED: "❓",
    AppealStatus.RESOLVED: "✅",
    AppealStatus.REJECTED: "⛔",
}

ROLE_LABELS: dict[StaffRole, str] = {
    StaffRole.SUPER_ADMIN: "Super admin",
    StaffRole.ADMIN: "Administrator",
    StaffRole.STAFF: "Mas'ul xodim",
}

# Yakunlangan (yopilgan) holatlar
CLOSED_STATUSES = frozenset({AppealStatus.RESOLVED, AppealStatus.REJECTED})
# Hali ishlov berilayotgan holatlar
OPEN_STATUSES = frozenset(set(AppealStatus) - CLOSED_STATUSES)


def status_label(status: AppealStatus | str) -> str:
    st = AppealStatus(status)
    return f"{STATUS_EMOJI[st]} {STATUS_LABELS[st]}"
