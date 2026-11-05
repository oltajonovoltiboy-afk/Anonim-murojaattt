"""Foydalanuvchi kiritgan ma'lumotlarni tekshirish va normallashtirish."""
from __future__ import annotations

import re
from dataclasses import dataclass

# Ism-familiya: lotin/kirill harflari, o'zbekcha apostrof belgilari, defis va bo'sh joy
_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʻʼ‘’'`\- .]+$")
_PHONE_CLEAN_RE = re.compile(r"[\s\-()]")
_APPEAL_NUMBER_RE = re.compile(r"^([A-Z]{2,10})-(\d{4})-(\d{6})$")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

NAME_MIN, NAME_MAX = 5, 100
SUBJECT_MIN, SUBJECT_MAX = 5, 200
TEXT_MIN, TEXT_MAX = 20, 3500
FOLLOWUP_MIN, FOLLOWUP_MAX = 3, 3500
STAFF_TEXT_MIN, STAFF_TEXT_MAX = 2, 3500


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    value: str = ""
    error: str = ""


def clean_text(value: str | None) -> str:
    """Boshqaruv belgilarini olib tashlaydi va bo'shliqlarni qisqartiradi."""
    if not value:
        return ""
    value = _CONTROL_CHARS_RE.sub("", value)
    # Satr ichidagi ortiqcha bo'shliqlar, lekin yangi qatorlar saqlanadi
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def validate_full_name(value: str | None) -> ValidationResult:
    name = clean_text(value).replace("\n", " ")
    name = re.sub(r"\s+", " ", name)
    if not (NAME_MIN <= len(name) <= NAME_MAX):
        return ValidationResult(False, error=f"Ism va familiya {NAME_MIN}–{NAME_MAX} belgidan iborat bo‘lishi kerak.")
    if not _NAME_RE.match(name):
        return ValidationResult(False, error="Ism va familiyada faqat harflar bo‘lishi mumkin.")
    if len([p for p in name.split(" ") if len(p) >= 2]) < 2:
        return ValidationResult(False, error="Iltimos, ism va familiyangizni to‘liq kiriting (masalan: Aliyev Vali).")
    return ValidationResult(True, value=name)


def normalize_phone(value: str | None) -> str | None:
    """Telefon raqamini +998XXXXXXXXX (yoki xalqaro +XXXXXXXXXX) ko'rinishiga keltiradi."""
    if not value:
        return None
    raw = _PHONE_CLEAN_RE.sub("", value.strip())
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    has_plus = raw.startswith("+")
    digits = raw[1:] if has_plus else raw
    if not digits.isdigit():
        return None
    if len(digits) == 9 and not has_plus:  # 901234567
        return "+998" + digits
    if digits.startswith("998"):
        return "+" + digits if len(digits) == 12 else None
    if has_plus and 10 <= len(digits) <= 15:
        return "+" + digits
    if not has_plus and 11 <= len(digits) <= 15:
        return "+" + digits
    return None


def validate_phone(value: str | None) -> ValidationResult:
    phone = normalize_phone(value)
    if not phone:
        return ValidationResult(
            False, error="Telefon raqami noto‘g‘ri. Namuna: +998901234567 yoki 901234567."
        )
    return ValidationResult(True, value=phone)


def validate_length(value: str | None, min_len: int, max_len: int, field: str) -> ValidationResult:
    text = clean_text(value)
    if len(text) < min_len:
        return ValidationResult(False, error=f"{field} kamida {min_len} ta belgidan iborat bo‘lishi kerak.")
    if len(text) > max_len:
        return ValidationResult(False, error=f"{field} {max_len} ta belgidan oshmasligi kerak (hozir: {len(text)}).")
    return ValidationResult(True, value=text)


def validate_subject(value: str | None) -> ValidationResult:
    res = validate_length(value, SUBJECT_MIN, SUBJECT_MAX, "Mavzu")
    if res.ok:
        return ValidationResult(True, value=res.value.replace("\n", " "))
    return res


def validate_appeal_text(value: str | None) -> ValidationResult:
    return validate_length(value, TEXT_MIN, TEXT_MAX, "Murojaat matni")


def normalize_appeal_number(value: str | None) -> str | None:
    """'urg 2026 000001', 'URG-2026-1' kabi kiritishlarni standart ko'rinishga keltiradi."""
    if not value:
        return None
    raw = value.strip().upper().replace(" ", "-").replace("_", "-").replace("–", "-")
    raw = re.sub(r"-+", "-", raw)
    parts = raw.split("-")
    if len(parts) == 3 and parts[0].isalpha() and parts[1].isdigit() and parts[2].isdigit():
        if len(parts[1]) == 4 and 1 <= len(parts[2]) <= 6:
            raw = f"{parts[0]}-{parts[1]}-{int(parts[2]):06d}"
    return raw if _APPEAL_NUMBER_RE.match(raw) else None


def format_appeal_number(prefix: str, year: int, seq: int) -> str:
    return f"{prefix}-{year}-{seq:06d}"
