"""Biriktiriladigan fayllarni tekshirish (format va hajm)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from app.utils.enums import AttachmentType

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        # rasmlar
        "jpg", "jpeg", "png", "webp", "heic",
        # videolar
        "mp4", "mov",
        # ovozli xabarlar va audio
        "ogg", "oga", "mp3", "wav", "m4a", "aac",
        # hujjatlar
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt",
    }
)

ALLOWED_MIME_PREFIXES: tuple[str, ...] = ("image/", "video/", "audio/")
ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
    }
)

# Bajariladigan yoki xavfli fayllar — hech qachon qabul qilinmaydi
BLOCKED_EXTENSIONS: frozenset[str] = frozenset(
    {"exe", "bat", "cmd", "com", "msi", "scr", "js", "vbs", "ps1", "sh", "apk", "jar", "html", "htm", "svg"}
)


@dataclass
class FileInfo:
    file_type: AttachmentType
    file_id: str
    file_unique_id: str
    file_name: str | None
    mime_type: str | None
    file_size: int | None

    def to_dict(self) -> dict:
        return {
            "file_type": self.file_type.value,
            "file_id": self.file_id,
            "file_unique_id": self.file_unique_id,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileInfo":
        return cls(
            file_type=AttachmentType(data["file_type"]),
            file_id=data["file_id"],
            file_unique_id=data["file_unique_id"],
            file_name=data.get("file_name"),
            mime_type=data.get("mime_type"),
            file_size=data.get("file_size"),
        )


class FileValidationError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code  # "too_large" | "bad_format"


def _extension(file_name: str | None) -> str:
    if not file_name:
        return ""
    return os.path.splitext(file_name)[1].lower().lstrip(".")


def validate_file(info: FileInfo, max_size_bytes: int) -> None:
    """Fayl hajmi va formatini tekshiradi; muammo bo'lsa FileValidationError ko'taradi."""
    if info.file_size is not None and info.file_size > max_size_bytes:
        raise FileValidationError("too_large")

    if info.file_type == AttachmentType.PHOTO:
        return  # Telegram suratlarni har doim JPEG ga o'giradi

    ext = _extension(info.file_name)
    mime = (info.mime_type or "").lower()

    if ext in BLOCKED_EXTENSIONS:
        raise FileValidationError("bad_format")

    if info.file_type == AttachmentType.VIDEO:
        if mime.startswith("video/") or ext in {"mp4", "mov"}:
            return
        raise FileValidationError("bad_format")

    # Hujjat: kengaytma ham, MIME turi ham tekshiriladi
    ext_ok = ext in ALLOWED_EXTENSIONS
    mime_ok = (not mime) or mime in ALLOWED_MIME_TYPES or mime.startswith(ALLOWED_MIME_PREFIXES) \
        or mime == "application/octet-stream"
    if not (ext_ok and mime_ok):
        raise FileValidationError("bad_format")


def extract_file_info(message) -> FileInfo | None:  # noqa: ANN001 - aiogram Message
    """aiogram Message obyektidan fayl ma'lumotlarini ajratib oladi."""
    if message.photo:
        photo = message.photo[-1]  # eng yuqori sifatli variant
        return FileInfo(
            AttachmentType.PHOTO, photo.file_id, photo.file_unique_id,
            f"photo_{photo.file_unique_id}.jpg", "image/jpeg", photo.file_size,
        )
    if message.video:
        v = message.video
        return FileInfo(
            AttachmentType.VIDEO, v.file_id, v.file_unique_id,
            v.file_name or f"video_{v.file_unique_id}.mp4", v.mime_type, v.file_size,
        )
    if message.document:
        d = message.document
        return FileInfo(
            AttachmentType.DOCUMENT, d.file_id, d.file_unique_id, d.file_name, d.mime_type, d.file_size,
        )
    if message.voice:
        v = message.voice
        return FileInfo(
            AttachmentType.DOCUMENT, v.file_id, v.file_unique_id,
            f"voice_{v.file_unique_id}.ogg", "audio/ogg", v.file_size,
        )
    if message.audio:
        a = message.audio
        return FileInfo(
            AttachmentType.DOCUMENT, a.file_id, a.file_unique_id,
            a.file_name or f"audio_{a.file_unique_id}.mp3", a.mime_type or "audio/mpeg", a.file_size,
        )
    return None
