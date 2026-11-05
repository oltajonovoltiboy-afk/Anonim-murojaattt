"""Botdagi barcha matnlar va tugma nomlari (o'zbek tili, lotin yozuvi).

Zamonaviy va professional Telegram bot uslubida formatlangan:
- Blockquote va kod bloklari
- Vizual progress bar
- Tushunarli va chiroyli emojilar
- Rasmiy akademik standartlar
"""
from __future__ import annotations

# --- Asosiy menyu tugmalari ---------------------------------------------
BTN_NEW_APPEAL = "📝 Murojaat yuborish"
BTN_CHECK_STATUS = "🔎 Holatni tekshirish"
BTN_MY_APPEALS = "📋 Mening murojaatlarim"
BTN_FAQ = "❓ Ko‘p beriladigan savollar"
BTN_ABOUT = "ℹ️ Litsey haqida"
BTN_CONTACT = "📞 Bog‘lanish"

# --- Jarayon tugmalari ---------------------------------------------------
BTN_CANCEL = "❌ Bekor qilish"
BTN_BACK = "⬅️ Orqaga"
BTN_SHARE_CONTACT = "📱 Telefon raqamni ulashish"
BTN_CONTINUE = "✅ Davom etish"
BTN_SKIP_FILES = "⏭ Faylsiz davom etish"
BTN_SEND_FOLLOWUP = "📨 Yuborish"
BTN_MAIN_MENU = "🏠 Bosh menyu"

DEFAULT_ABOUT_TEXT = (
    "🏛 <b>Abu Rayhon Beruniy nomidagi Urganch davlat akademik litseyi</b>\n"
    "<i>Rasmiy murojaatlar va takliflar portali</i>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Ushbu bot orqali o‘quvchilar, ota-onalar, o‘qituvchilar va fuqarolar litsey "
    "rahbariyatiga murojaat, taklif, ariza va fikr-mulohazalarini to‘g‘ridan-to‘g‘ri yuborishlari mumkin.\n\n"
    "🛡 <b>Bizning tamoyillarimiz:</b>\n"
    "• Har bir murojaat qat'iy ro‘yxatga olinadi va maxsus raqam beriladi.\n"
    "• Anonimlikka yo‘l qo‘yilmaydi — bu murojaatni qonuniy va tezkor hal etish kafolatidir.\n"
    "• Mas'ul xodimlar tomonidan ko‘rib chiqiladi va bot orqali javob xati taqdim etiladi.\n"
    "• Holat har o‘zgarganda sizga avtomatik bildirishnoma keladi."
)

DEFAULT_CONTACT_TEXT = (
    "📞 <b>Bog‘lanish va aloqa ma'lumotlari</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🏛 <b>Urganch davlat akademik litseyi</b>\n"
    "📍 <b>Manzil:</b> Xorazm viloyati, Urganch shahri\n"
    "☎️ <b>Ishonch telefoni:</b> +998 (62) 228-00-00\n"
    "📧 <b>Elektron pochta:</b> info@urganchlitsey.uz\n"
    "🕘 <b>Ish tartibi:</b> Dushanba – Shanba, 08:30 – 17:00\n\n"
    "💬 <i>Murojaatlaringiz ushbu bot orqali 24/7 qabul qilinadi va ish vaqtida ijroga yo‘naltiriladi.</i>"
)


def welcome(name: str, org: str) -> str:
    return (
        f"🏛 <b>{org}</b>\n"
        f"<i>Rasmiy interaktiv murojaatlar tizimi</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Assalomu alaykum, <b>{name}</b>!\n\n"
        f"Ushbu portal orqali litsey rahbariyatiga o‘z murojaat, ariza yoki "
        f"takliflaringizni yuborishingiz va ularning ijro jarayonini onlayn kuzatishingiz mumkin.\n\n"
        f"👇 <b>Quyidagi menyudan kerakli bo‘limni tanlang:</b>"
    )


HELP = (
    "ℹ️ <b>Qo‘llanma va buyruqlar</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🔘 <b>Asosiy buyruqlar:</b>\n"
    "• /start — Bosh menyuni ochish\n"
    "• /new — Yangi murojaat yuborish\n"
    "• /my — Mening murojaatlarim ro‘yxati\n"
    "• /status — Murojaat holatini tekshirish\n"
    "• /cancel — Joriy amalni bekor qilish\n\n"
    "⚠️ <b>Eslatma:</b> Qonunchilikka binoan anonim murojaatlar qabul qilinmaydi. "
    "Murojaat yuborish uchun telefon raqami va F.I.Sh. tasdiqlangan bo‘lishi lozim."
)

MAIN_MENU = "🏠 <b>Bosh menyu</b>\nQuyidagi tugmalardan birini tanlang 👇"
CANCELLED = "❌ <b>Jarayon bekor qilindi.</b>\nBosh menyuga qaytildi."
UNKNOWN = "🤔 Buyruq tushunilmadi. Iltimos, menyudagi tugmalardan foydalaning."
BLOCKED = "⛔ <b>Sizning hisobingiz cheklangan.</b>\nBatafsil ma'lumot olish uchun litsey ma'muriyatiga bevosita murojaat qiling."
THROTTLED = "⏳ <b>Juda tez xabar yuboryapsiz.</b> Iltimos, bir oz kuting."
ERROR = "⚠️ <b>Texnik xatolik yuz berdi.</b> Iltimos, birozdan so‘ng qayta urinib ko‘ring."

# --- Murojaat yuborish bosqichlari -------------------------------------
STEP_NAME = (
    "📝 <b>Yangi murojaat</b>\n"
    "Progress: <code>[▰▱▱▱▱▱] 1/6</code> • Shaxsiy ma'lumot\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "👤 <b>To‘liq ism, familiyangiz va otangizning ismini kiriting:</b>\n\n"
    "<i>Namuna: Karimov Sardor Baxtiyorovich</i>"
)
STEP_NAME_SAVED_HINT = "\n\n💡 <i>Pastdagi tugma orqali profilingizdagi ismni tezkor tanlashingiz mumkin.</i>"

STEP_PHONE = (
    "📞 <b>Telefon raqamini tasdiqlash</b>\n"
    "Progress: <code>[▰▰▱▱▱▱] 2/6</code> • Aloqa ma'lumoti\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Pastdagi <b>«📱 Telefon raqamni ulashish»</b> tugmasini bosing yoki qo‘lda xalqaro formatda yozing:\n\n"
    "<i>Namuna: +998901234567</i>"
)

STEP_USER_TYPE = (
    "👥 <b>Foydalanuvchi toifasi</b>\n"
    "Progress: <code>[▰▰▱▱▱▱] 2/6</code> • Maqomingiz\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Litseyga qaysi maqomda murojaat qilmoqdasiz?\n"
    "👇 <b>Quyidagi variantlardan birini tanlang:</b>"
)

STEP_CATEGORY = (
    "📂 <b>Murojaat yo‘nalishi</b>\n"
    "Progress: <code>[▰▰▰▱▱▱] 3/6</code> • Yo‘nalish\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Murojaatingiz mazmuni qaysi soha yoki bo‘limga tegishli?\n"
    "👇 <b>Yo‘nalishni tanlang:</b>"
)

STEP_SUBJECT = (
    "🏷 <b>Murojaat mavzusi</b>\n"
    "Progress: <code>[▰▰▰▰▱▱] 4/6</code> • Mavzu\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Murojaatingizning qisqacha mazmunini yozing (5 tadan 200 tagacha belgi):\n\n"
    "<i>Namuna: Dars jadvalidagi o‘zgarishlar va laboratoriya mashg‘ulotlari</i>"
)

STEP_TEXT = (
    "✍️ <b>Batafsil murojaat matni</b>\n"
    "Progress: <code>[▰▰▰▰▰▱] 5/6</code> • Matn\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Muammoni, taklifni yoki iltimosingizni aniq, lo‘nda va batafsil bayon qiling.\n"
    "Iloji bo‘lsa sana, guruh, fan yoki daxldor shaxslarni ko‘rsating (kamida 20 ta belgi):\n"
)


def step_files(max_files: int, max_mb: int) -> str:
    return (
        "📎 <b>Hujjat va fayllar biriktirish</b>\n"
        "Progress: <code>[▰▰▰▰▰▰] 6/6</code> • Hujjatlar\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Murojaatga asos bo‘luvchi rasm, video yoki PDF hujjatlarni yuborishingiz mumkin "
        f"(ko‘pi bilan <b>{max_files} ta</b>, har biri <b>{max_mb} MB</b> gacha).\n\n"
        f"Agar fayl bo‘lmasa yoki yuklab bo‘lgan bo‘lsangiz, "
        f"pastdagi <b>«{BTN_CONTINUE}»</b> tugmasini bosing."
    )


def file_accepted(count: int, max_files: int) -> str:
    return (
        f"✅ <b>Fayl qabul qilindi ({count}/{max_files})</b>\n\n"
        f"Yana fayl yuborishingiz yoki <b>«{BTN_CONTINUE}»</b> tugmasini bosishingiz mumkin."
    )


def file_limit_reached(max_files: int) -> str:
    return f"⚠️ <b>Limitga yetildi:</b> Ko‘pi bilan {max_files} ta fayl biriktirish mumkin. Iltimos, «{BTN_CONTINUE}» tugmasini bosing."


def file_too_large(max_mb: int) -> str:
    return f"⚠️ <b>Fayl hajmi katta:</b> Har bir fayl ko‘pi bilan {max_mb} MB bo‘lishi mumkin."


FILE_BAD_FORMAT = (
    "⚠️ <b>Qabul qilinmaydigan format</b>\n"
    "Ruxsat berilgan fayl turlari: JPG, PNG, WEBP, MP4, MOV, PDF, DOC, DOCX, XLS, XLSX."
)
EXPECT_FILE_OR_CONTINUE = f"📎 Fayl yuboring yoki «{BTN_CONTINUE}» tugmasini bosing."
EXPECT_TEXT = "✍️ Iltimos, matn ko‘rinishida yozing."
EXPECT_CHOICE = "👆 Iltimos, yuqoridagi tugmalardan birini bosing."
CONTACT_NOT_OWN = "⚠️ Iltimos, faqat o‘zingizning telefon raqamingizni yuboring."
CONFIRM_TITLE = (
    "📋 <b>Murojaatni tekshirish va tasdiqlash</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
)
CONFIRM_FOOTER = (
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Agar barcha ma'lumotlar to‘g‘ri bo‘lsa, <b>«✅ Tasdiqlash va yuborish»</b> tugmasini bosing:"
)
DAILY_LIMIT = "⚠️ <b>Kunlik limit:</b> Bir kunda ko‘pi bilan {limit} ta murojaat yuborish mumkin. Iltimos, ertaga qayta urinib ko‘ring."
SESSION_EXPIRED = "⚠️ Sessiya muddati tugadi. Iltimos, murojaatni qaytadan boshlang."


def appeal_created(number: str) -> str:
    return (
        "🎉 <b>Murojaatingiz muvaffaqiyatli qabul qilindi!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Maxsus ro‘yxat raqami: <code>{number}</code>\n\n"
        "💡 <i>Ushbu raqam orqali murojaatingiz holatini istalgan vaqtda tekshirishingiz mumkin. "
        "Murojaat mas'ul xodimga yo‘naltirildi. Holat o‘zgarganda sizga ushbu bot orqali xabar beriladi.</i>"
    )


# --- Holatni tekshirish va ro'yxat -------------------------------------
ASK_NUMBER = (
    "🔎 <b>Murojaat holatini tekshirish</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Murojaat qilganingizda berilgan maxsus raqamni kiriting:\n\n"
    "<i>Namuna:</i> <code>URG-2026-000001</code>"
)
BAD_NUMBER = "⚠️ Murojaat raqami noto‘g‘ri formatda. Namuna: <code>URG-2026-000001</code>"
APPEAL_NOT_FOUND = "❌ Ushbu raqamli murojaat topilmadi yoki u sizning hisobingizga tegishli emas."
NO_APPEALS = (
    "📭 <b>Sizda hali yuborilgan murojaatlar mavjud emas.</b>\n\n"
    "Yangi murojaat yuborish uchun <b>«📝 Murojaat yuborish»</b> tugmasini bosing."
)
MY_APPEALS_TITLE = (
    "📋 <b>Sizning barcha murojaatlaringiz</b> (Jami: {total} ta)\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "Tafsilotlarni ko‘rish uchun kerakli murojaatni tanlang:"
)

# --- Qo'shimcha ma'lumot ------------------------------------------------
FOLLOWUP_ASK = (
    "✍️ <b>Qo‘shimcha ma'lumot yuborish</b>\n"
    "Murojaat raqami: <code>{number}</code>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Mas'ul xodim so‘ragan ma'lumotni to‘liq bayon qiling.\n"
    "Avval matnni yozib yuboring, so‘ng kerak bo‘lsa fayllar ilova qilishingiz mumkin."
)
FOLLOWUP_NOT_ALLOWED = "⚠️ Bu murojaat bo‘yicha hozirda qo‘shimcha ma'lumot talab qilinmagan."
FOLLOWUP_FILES = (
    "📎 <b>Hujjat biriktirish</b>\n\n"
    "Agar mavjud bo‘lsa rasm yoki hujjat yuboring.\n"
    f"Tayyor bo‘lgach <b>«{BTN_SEND_FOLLOWUP}»</b> tugmasini bosing."
)
FOLLOWUP_SENT = (
    "✅ <b>Qo‘shimcha ma'lumotingiz qabul qilindi!</b>\n"
    "Ma'lumot <code>{number}</code> raqamli murojaatga biriktirildi va ko‘rib chiqishga yo‘naltirildi."
)
