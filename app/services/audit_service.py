"""Audit jurnali: barcha muhim harakatlarni yozib boradi."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Staff, User
from app.utils.enums import ActorType

logger = logging.getLogger(__name__)


class AuditAction:
    # Foydalanuvchi harakatlari
    USER_START = "user.start"
    APPEAL_CREATED = "appeal.created"
    APPEAL_STATUS_CHECKED = "appeal.status_checked"
    APPEAL_FOLLOWUP = "appeal.followup_sent"
    # Xodim harakatlari
    LOGIN_CODE_REQUESTED = "auth.code_requested"
    LOGIN_SUCCESS = "auth.login"
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    APPEAL_VIEWED = "appeal.viewed"
    APPEAL_STATUS_CHANGED = "appeal.status_changed"
    APPEAL_ASSIGNED = "appeal.assigned"
    APPEAL_REPLIED = "appeal.replied"
    APPEAL_INFO_REQUESTED = "appeal.info_requested"
    ATTACHMENT_DOWNLOADED = "attachment.downloaded"
    REPORT_EXPORTED = "report.exported"
    STAFF_CREATED = "staff.created"
    STAFF_UPDATED = "staff.updated"
    STAFF_DEACTIVATED = "staff.deactivated"
    USER_BLOCKED = "user.blocked"
    USER_UNBLOCKED = "user.unblocked"
    SETTINGS_UPDATED = "settings.updated"


async def log_action(
    session: AsyncSession,
    action: str,
    *,
    staff: Staff | None = None,
    user: User | None = None,
    entity_type: str | None = None,
    entity_id: Any = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    actor_telegram_id: int | None = None,
) -> AuditLog:
    """Audit yozuvini sessiyaga qo'shadi (commit chaqiruvchi tomonidan bajariladi)."""
    if staff is not None:
        actor_type, actor_id = ActorType.STAFF, staff.id
        tg_id, name = staff.telegram_id, staff.full_name
    elif user is not None:
        actor_type, actor_id = ActorType.USER, user.id
        tg_id, name = user.telegram_id, user.full_name or user.first_name
    else:
        actor_type, actor_id, tg_id, name = ActorType.SYSTEM, None, actor_telegram_id, None

    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        actor_telegram_id=tg_id,
        actor_name=name,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details,
        ip_address=ip_address,
    )
    session.add(entry)
    logger.info("AUDIT %s actor=%s:%s entity=%s:%s", action, actor_type.value, actor_id, entity_type, entity_id)
    return entry
