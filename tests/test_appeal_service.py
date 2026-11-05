"""Murojaat yaratish, holat o'zgartirish va yozishmalar xizmati testlari."""
import pytest

from app.models import Staff, User
from app.services import appeal_service
from app.services.exceptions import ValidationFailedError
from app.utils.enums import AppealCategory, AppealStatus, UserType


@pytest.mark.asyncio
async def test_create_appeal(db_session, test_user: User):
    draft = appeal_service.AppealDraft(
        full_name="Aliyev Vali Karimovich",
        phone="+998901234567",
        user_type=UserType.STUDENT,
        category=AppealCategory.EDUCATION_QUALITY,
        subject="Fizika fani bo‘yicha qo‘shimcha to‘garak",
        text="Hurmatli litsey rahbariyati, fizika fanidan qo‘shimcha amaliy to‘garaklar tashkil etilishini so‘raymiz.",
    )
    appeal = await appeal_service.create_appeal(db_session, test_user, draft)
    await db_session.commit()

    assert appeal.id is not None
    assert appeal.number.startswith("URG-")
    assert appeal.status == AppealStatus.NEW
    assert appeal.full_name == "Aliyev Vali Karimovich"
    assert appeal.user_id == test_user.id


@pytest.mark.asyncio
async def test_assign_appeal(db_session, test_user: User, super_admin: Staff, test_staff: Staff):
    draft = appeal_service.AppealDraft(
        full_name="Olimov Bekzod",
        phone="+998912345678",
        user_type=UserType.PARENT,
        category=AppealCategory.INFRASTRUCTURE,
        subject="Litsey oshxonasidagi sharoitlar",
        text="Assalomu alaykum. Oshxonada yangi o‘rindiqlar o‘rnatilishi rejalashtirilganmi?",
    )
    appeal = await appeal_service.create_appeal(db_session, test_user, draft)

    # Super admin mas'ul xodimga biriktiradi
    history = await appeal_service.assign_appeal(db_session, appeal, test_staff, by_staff=super_admin)
    await db_session.commit()

    assert appeal.assigned_staff_id == test_staff.id
    # 'Yangi' holatidagi murojaat biriktirilganda avtomatik 'Qabul qilindi' holatiga o'tadi
    assert appeal.status == AppealStatus.ACCEPTED
    assert history is not None
    assert history.new_status == AppealStatus.ACCEPTED


@pytest.mark.asyncio
async def test_change_status_and_reply(db_session, test_user: User, super_admin: Staff, test_staff: Staff):
    draft = appeal_service.AppealDraft(
        full_name="Salimov Jasur",
        phone="+998933334455",
        user_type=UserType.TEACHER,
        category=AppealCategory.SUGGESTION,
        subject="Kutubxonaga elektron kitoblar bazasini ulash",
        text="Hurmatli rahbariyat, o‘quvchilar uchun xalqaro elektron kutubxona tizimlariga obuna bo‘lishni taklif qilaman.",
    )
    appeal = await appeal_service.create_appeal(db_session, test_user, draft)
    await appeal_service.assign_appeal(db_session, appeal, test_staff, by_staff=super_admin)

    # Holatni 'Ko'rib chiqilmoqda'ga o'tkazish
    await appeal_service.change_status(
        db_session, appeal, AppealStatus.IN_REVIEW, test_staff, comment="Taklif o‘rganilmoqda"
    )
    assert appeal.status == AppealStatus.IN_REVIEW

    # Foydalanuvchiga javob yozish
    msg = await appeal_service.add_staff_reply(
        db_session, appeal, test_staff, "Taklifingiz ma'qullandi va rejalashtirildi. Tashakkur!"
    )
    assert msg.id is not None
    assert msg.text.startswith("Taklifingiz")

    # Murojaatni 'Hal qilindi' qilish
    await appeal_service.change_status(
        db_session, appeal, AppealStatus.RESOLVED, test_staff, comment="Elektron kutubxona yo‘lga qo‘yildi."
    )
    assert appeal.status == AppealStatus.RESOLVED
    assert appeal.closed_at is not None


@pytest.mark.asyncio
async def test_auto_assign_by_category(db_session, test_user: User, test_staff: Staff):
    # test_staff ga yo'nalish biriktiramiz
    test_staff.assigned_category = AppealCategory.EDUCATION_QUALITY.value
    await db_session.flush()

    draft = appeal_service.AppealDraft(
        full_name="Nodirbek Boboyev",
        phone="+998901112233",
        user_type=UserType.STUDENT,
        category=AppealCategory.EDUCATION_QUALITY,
        subject="Kimyo fanidan olimpiada to'garagi",
        text="Kimyo olimpiadasiga tayyorgarlik uchun qo'shimcha darslar kerak.",
    )
    appeal = await appeal_service.create_appeal(db_session, test_user, draft)
    await db_session.commit()

    # Murojaat avtomatik ushbu xodimga biriktirilgan va holati ACCEPTED bo'lgan bo'lishi kerak
    assert appeal.assigned_staff_id == test_staff.id
    assert appeal.status == AppealStatus.ACCEPTED


@pytest.mark.asyncio
async def test_appeal_rating(db_session, test_user: User):
    draft = appeal_service.AppealDraft(
        full_name="Zafar Ergashev",
        phone="+998909998877",
        user_type=UserType.PARENT,
        category=AppealCategory.OTHER,
        subject="Litsey kutubxonasi ish tartibi",
        text="Kutubxona shanba kunlari ham ishlaydimi?",
    )
    appeal = await appeal_service.create_appeal(db_session, test_user, draft)
    assert appeal.rating is None

    # Fuqaro 5 yulduz baho qo'ydi
    appeal.rating = 5
    appeal.rating_comment = "Tezkor va aniq javob berildi, katta rahmat!"
    await db_session.commit()

    assert appeal.rating == 5
    assert "rahmat" in appeal.rating_comment
