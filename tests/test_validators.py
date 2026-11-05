"""Validatsiya va matnni tozalash funksiyalari testlari."""
import pytest

from app.utils.validators import (
    format_appeal_number,
    normalize_appeal_number,
    normalize_phone,
    validate_appeal_text,
    validate_full_name,
    validate_phone,
    validate_subject,
)


def test_validate_full_name():
    assert validate_full_name("Aliyev Vali").ok
    assert validate_full_name("Olimov O‘ktam G‘aniyevich").ok
    assert not validate_full_name("Vali").ok  # faqat bitta so'z
    assert not validate_full_name("").ok
    assert not validate_full_name("Aliyev 123").ok  # raqamlar bo'lmasligi kerak


def test_normalize_phone():
    assert normalize_phone("+998 90 123 45 67") == "+998901234567"
    assert normalize_phone("901234567") == "+998901234567"
    assert normalize_phone("+998(93) 987-65-43") == "+998939876543"
    assert normalize_phone("invalid") is None
    assert normalize_phone("123") is None


def test_validate_phone():
    assert validate_phone("+998901234567").ok
    assert validate_phone("901234567").ok
    assert not validate_phone("1234").ok


def test_validate_subject():
    assert validate_subject("Sport zalidagi to‘plar haqida").ok
    assert not validate_subject("abc").ok  # juda qisqa


def test_validate_appeal_text():
    assert validate_appeal_text(
        "Assalomu alaykum. Litsey kutubxonasida yangi darsliklar yetishmayapti. Iltimos ko‘rib chiqsangiz."
    ).ok
    assert not validate_appeal_text("Juda qisqa").ok


def test_normalize_appeal_number():
    assert normalize_appeal_number("URG-2026-000001") == "URG-2026-000001"
    assert normalize_appeal_number("urg 2026 1") == "URG-2026-000001"
    assert normalize_appeal_number("URG-2026-15") == "URG-2026-000015"
    assert normalize_appeal_number("invalid-num") is None


def test_format_appeal_number():
    assert format_appeal_number("URG", 2026, 42) == "URG-2026-000042"
