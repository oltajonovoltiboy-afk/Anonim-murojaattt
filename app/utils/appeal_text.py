"""Murojaat ma'lumotlarini Telegram xabari ko'rinishida zamonaviy formatlash (HTML, ekranlangan).

Zamonaviy Telegram 2024+ blockquote va kod formatlaridan foydalanadi.
"""
from __future__ import annotations

from app.models import Appeal
from app.utils.enums import (
    CATEGORY_LABELS,
    USER_TYPE_LABELS,
    AppealCategory,
    AppealStatus,
    MessageDirection,
    UserType,
    status_label,
)
from app.utils.formatting import esc, fmt_dt, truncate


def draft_summary(data: dict, files_count: int) -> str:
    """Tasdiqlash oldidan foydalanuvchiga ko'rsatiladigan qisqacha ma'lumot kartochkasi."""
    category_str = CATEGORY_LABELS.get(AppealCategory(data['category']), data['category'])
    user_type_str = USER_TYPE_LABELS.get(UserType(data['user_type']), data['user_type'])

    return (
        f"👤 <b>Murojaatchi:</b> {esc(data['full_name'])}\n"
        f"📞 <b>Telefon:</b> <code>{esc(data['phone'])}</code>\n"
        f"👥 <b>Maqomi:</b> {esc(user_type_str)}\n"
        f"📂 <b>Yo‘nalish:</b> {esc(category_str)}\n"
        f"🏷 <b>Mavzu:</b> {esc(data['subject'])}\n"
        f"📎 <b>Biriktirilgan fayllar:</b> {files_count} ta\n\n"
        f"✍️ <b>Murojaat matni:</b>\n"
        f"<blockquote>{esc(truncate(data['text'], 2500))}</blockquote>\n"
    )


def appeal_details_for_user(appeal: Appeal, with_history: bool = True) -> str:
    category_str = CATEGORY_LABELS.get(AppealCategory(appeal.category), appeal.category)
    user_type_str = USER_TYPE_LABELS.get(UserType(appeal.user_type), appeal.user_type)

    lines = [
        f"📋 <b>Murojaat kartochkasi</b>",
        f"🆔 Raqam: <code>{esc(appeal.number)}</code>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"👤 <b>F.I.Sh:</b> {esc(appeal.full_name)} ({esc(user_type_str)})",
        f"📂 <b>Yo‘nalish:</b> {esc(category_str)}",
        f"🏷 <b>Mavzu:</b> {esc(appeal.subject)}",
        f"📌 <b>Holat:</b> {status_label(appeal.status)}",
        f"📅 <b>Yuborilgan sana:</b> {fmt_dt(appeal.created_at)}",
        f"🕓 <b>Oxirgi harakat:</b> {fmt_dt(appeal.updated_at)}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📝 <b>Murojaatingiz matni:</b>",
        f"<blockquote>{esc(truncate(appeal.text, 2000))}</blockquote>",
    ]

    if with_history and appeal.history:
        lines.append("\n📜 <b>Ijro tarixi va o‘zgarishlar:</b>")
        for h in appeal.history[-6:]:
            item = f"• {fmt_dt(h.created_at)} — {status_label(h.new_status)}"
            if h.comment and AppealStatus(h.new_status) in (AppealStatus.REJECTED, AppealStatus.RESOLVED, AppealStatus.INFO_REQUESTED):
                item += f"\n   <blockquote>{esc(truncate(h.comment, 300))}</blockquote>"
            lines.append(item)

    staff_msgs = [m for m in appeal.messages if MessageDirection(m.direction) == MessageDirection.STAFF_TO_USER]
    if staff_msgs:
        last = staff_msgs[-1]
        lines.append(f"\n💬 <b>Litsey mas'ulining javobi ({fmt_dt(last.created_at)}):</b>\n<blockquote>{esc(truncate(last.text, 2000))}</blockquote>")

    return "\n".join(lines)


def status_changed_text(appeal: Appeal, comment: str | None) -> str:
    st = AppealStatus(appeal.status)
    category_str = CATEGORY_LABELS.get(AppealCategory(appeal.category), appeal.category)

    text = (
        "🔔 <b>Murojaatingiz holati yangilandi!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Raqam: <code>{esc(appeal.number)}</code>\n"
        f"🏷 <b>Mavzu:</b> {esc(truncate(appeal.subject, 150))}\n"
        f"📂 <b>Yo‘nalish:</b> {esc(category_str)}\n"
        f"📌 <b>Yangi holat:</b> {status_label(st)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )

    if comment:
        title = {
            AppealStatus.INFO_REQUESTED: "❓ <b>So‘ralayotgan qo‘shimcha ma'lumot:</b>",
            AppealStatus.REJECTED: "⛔ <b>Rad etish asosi va sababi:</b>",
            AppealStatus.RESOLVED: "✅ <b>Ko‘rib chiqish natijasi:</b>",
        }.get(st, "💬 <b>Mas'ul izohi:</b>")
        text += f"\n{title}\n<blockquote>{esc(truncate(comment, 3000))}</blockquote>\n"

    if st == AppealStatus.INFO_REQUESTED:
        text += "\n💡 <i>Iltimos, pastdagi «✍️ Javob yozish» tugmasini bosib, so‘ralgan ma'lumotni yuboring.</i>"
    elif st == AppealStatus.RESOLVED:
        text += (
            "\n👏 <i>Murojaatingiz o‘rganib chiqildi va ijobiy hal etildi. Litseyimiz faoliyatiga befarq bo‘lmaganingiz uchun tashakkur!</i>\n\n"
            "⭐ <b>Xizmat sifatini baholang:</b>\n"
            "<i>Mas'ul xodimimiz faoliyati va murojaat yechimidan mamnunmisiz? Pastdagi tugmalar orqali baho bering 👇</i>"
        )

    return text


def staff_reply_text(appeal: Appeal, reply: str) -> str:
    return (
        "💬 <b>Murojaatingizga rasmiy javob keldi</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Raqam: <code>{esc(appeal.number)}</code>\n"
        f"🏷 <b>Mavzu:</b> {esc(truncate(appeal.subject, 150))}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✍️ <b>Litsey ma'muriyati javobi:</b>\n"
        f"<blockquote>{esc(truncate(reply, 3500))}</blockquote>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Savol yoki qo‘shimcha takliflaringiz bo‘lsa, yangi murojaat yuborishingiz mumkin.</i>"
    )


def new_appeal_for_staff(appeal: Appeal, files_count: int, title: str = "🆕 Yangi murojaat kelib tushdi") -> str:
    category_str = CATEGORY_LABELS.get(AppealCategory(appeal.category), appeal.category)
    user_type_str = USER_TYPE_LABELS.get(UserType(appeal.user_type), appeal.user_type)

    return (
        f"🏛 <b>{title}</b>\n"
        f"🆔 Raqam: <code>{esc(appeal.number)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Fuqaro:</b> {esc(appeal.full_name)}\n"
        f"👥 <b>Maqomi:</b> {esc(user_type_str)}\n"
        f"📞 <b>Telefon:</b> <code>{esc(appeal.phone)}</code>\n"
        f"📂 <b>Yo‘nalish:</b> {esc(category_str)}\n"
        f"🏷 <b>Mavzu:</b> {esc(truncate(appeal.subject, 150))}\n"
        f"📎 <b>Fayllar:</b> {files_count} ta biriktirilgan\n"
        f"📅 <b>Vaqti:</b> {fmt_dt(appeal.created_at)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Murojaat mazmuni:</b>\n"
        f"<blockquote>{esc(truncate(appeal.text, 2000))}</blockquote>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Tezkor amalni pastdagi tugmalar orqali bajaring:</i>"
    )
