"""Hisobotlarni Excel (XLSX) va PDF formatida yaratish."""
from __future__ import annotations

import io
import logging
import os
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.models import Appeal
from app.utils.enums import CATEGORY_LABELS, STATUS_LABELS, USER_TYPE_LABELS, AppealStatus
from app.utils.formatting import fmt_dt, human_duration, truncate
from config.settings import get_settings

logger = logging.getLogger(__name__)

HEADERS = [
    "№", "Murojaat raqami", "Sana", "F.I.Sh.", "Telefon", "Foydalanuvchi turi",
    "Yo‘nalish", "Mavzu", "Holat", "Mas'ul xodim", "Birinchi javob", "Yopilgan sana", "Matn",
]


def _row(i: int, a: Appeal) -> list:
    return [
        i,
        a.number,
        fmt_dt(a.created_at),
        a.full_name,
        a.phone,
        USER_TYPE_LABELS[a.user_type],
        CATEGORY_LABELS[a.category],
        a.subject,
        STATUS_LABELS[a.status],
        a.assigned_staff.full_name if a.assigned_staff else "—",
        fmt_dt(a.first_response_at),
        fmt_dt(a.closed_at),
        a.text,
    ]


def _safe_cell(value):
    """Excel formula injection (CSV injection) dan himoya."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def build_excel(appeals: list[Appeal], stats: dict | None, filters_desc: str) -> bytes:
    settings = get_settings()
    wb = Workbook()
    ws = wb.active
    ws.title = "Murojaatlar"

    header_fill = PatternFill("solid", fgColor="1E3A8A")
    header_font = Font(bold=True, color="FFFFFF")
    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.append([settings.org_name])
    ws.append([f"Murojaatlar hisoboti — {datetime.now(settings.tz).strftime('%d.%m.%Y %H:%M')}"])
    ws.append([f"Filtrlar: {filters_desc}"])
    ws.append([])
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"].font = Font(bold=True, size=12)
    ws["A3"].font = Font(italic=True, color="475569")
    ws.append(HEADERS)
    header_row = ws.max_row
    for col in range(1, len(HEADERS) + 1):
        c = ws.cell(row=header_row, column=col)
        c.fill, c.font, c.border = header_fill, header_font, border
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for i, a in enumerate(appeals, start=1):
        ws.append([_safe_cell(v) for v in _row(i, a)])
        for col in range(1, len(HEADERS) + 1):
            cell = ws.cell(row=ws.max_row, column=col)
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=col in (4, 8, 13))

    widths = [5, 18, 17, 28, 16, 16, 26, 36, 22, 24, 17, 17, 70]
    for idx, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = w
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(HEADERS))}{ws.max_row}"

    if stats:
        _excel_stats_sheet(wb, stats, header_fill, header_font, border)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _excel_stats_sheet(wb: Workbook, stats: dict, fill, font, border) -> None:
    ws = wb.create_sheet("Statistika")
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 18
    for col in "CDEFGH":
        ws.column_dimensions[col].width = 18

    def section(title: str, rows: list[tuple]) -> None:
        ws.append([title])
        ws.cell(row=ws.max_row, column=1).font = Font(bold=True, size=12)
        for r in rows:
            ws.append(list(r))
        ws.append([])

    section("Umumiy ko‘rsatkichlar", [
        ("Jami murojaatlar", stats["total"]),
        ("Yangi", stats["new"]),
        ("Jarayonda (qabul qilingan, ko‘rib chiqilayotgan, ma'lumot so‘ralgan)", stats["in_progress"]),
        ("Hal qilingan", stats["resolved"]),
        ("Rad etilgan", stats["rejected"]),
        ("O‘rtacha javob berish vaqti", human_duration(stats["avg_response_seconds"])),
        ("O‘rtacha hal qilish vaqti", human_duration(stats["avg_resolution_seconds"])),
    ])
    section("Holatlar bo‘yicha", [(STATUS_LABELS[AppealStatus(k)], v) for k, v in stats["by_status"].items()])
    section("Yo‘nalishlar bo‘yicha", [(stats["labels"]["category"][k], v) for k, v in stats["by_category"].items()])
    section("Foydalanuvchi turlari bo‘yicha", [(stats["labels"]["user_type"][k], v) for k, v in stats["by_user_type"].items()])

    ws.append(["Xodimlar samaradorligi"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True, size=12)
    hdr = ["Xodim", "Biriktirilgan", "Hal qilingan", "Rad etilgan", "Jarayonda", "Yakunlash, %", "O‘rt. javob", "O‘rt. hal qilish"]
    ws.append(hdr)
    for col in range(1, len(hdr) + 1):
        c = ws.cell(row=ws.max_row, column=col)
        c.fill, c.font, c.border = fill, font, border
    for p in stats["staff_performance"]:
        ws.append([
            p["full_name"], p["assigned"], p["resolved"], p["rejected"], p["open"], p["completion_rate"],
            human_duration(p["avg_response_seconds"]), human_duration(p["avg_resolution_seconds"]),
        ])


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
_FONT_NAME: str | None = None


def _register_font() -> str:
    """Kirill/lotin va ‘ belgilarini to'g'ri ko'rsatish uchun TTF shrift ro'yxatdan o'tkaziladi."""
    global _FONT_NAME
    if _FONT_NAME:
        return _FONT_NAME
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        get_settings().pdf_font_path,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("AppFont", path))
                bold_path = path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf").replace("arial.ttf", "arialbd.ttf")
                if bold_path != path and os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("AppFont-Bold", bold_path))
                else:
                    pdfmetrics.registerFont(TTFont("AppFont-Bold", path))
                _FONT_NAME = "AppFont"
                return _FONT_NAME
            except Exception:  # pragma: no cover
                logger.exception("Shriftni yuklab bo‘lmadi: %s", path)
    logger.warning("TTF shrift topilmadi, Helvetica ishlatiladi")
    _FONT_NAME = "Helvetica"
    return _FONT_NAME


def build_pdf(appeals: list[Appeal], stats: dict | None, filters_desc: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image as RLImage
    from xml.sax.saxutils import escape

    settings = get_settings()
    font = _register_font()
    bold = "AppFont-Bold" if font == "AppFont" else "Helvetica-Bold"

    title = ParagraphStyle("t", fontName=bold, fontSize=14, leading=18, spaceAfter=4)
    sub = ParagraphStyle("s", fontName=font, fontSize=10, leading=13, textColor=colors.HexColor("#475569"))
    h2 = ParagraphStyle("h2", fontName=bold, fontSize=11, leading=14, spaceBefore=8, spaceAfter=4)
    cell = ParagraphStyle("c", fontName=font, fontSize=7.5, leading=9.5)
    cell_h = ParagraphStyle("ch", fontName=bold, fontSize=7.5, leading=9.5, textColor=colors.white)

    def P(text, style=cell):
        return Paragraph(escape(str(text if text is not None else "")), style)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
        title="Murojaatlar hisoboti", author=settings.org_name,
    )

    logo_path = os.path.join(os.path.dirname(__file__), "..", "admin", "static", "logo.png")
    if os.path.exists(logo_path):
        header_table = Table(
            [[
                RLImage(logo_path, width=16 * mm, height=16 * mm),
                [
                    P(settings.org_name, title),
                    P(f"Murojaatlar hisoboti — {datetime.now(settings.tz).strftime('%d.%m.%Y %H:%M')}", sub),
                    P(f"Filtrlar: {filters_desc}", sub),
                ]
            ]],
            colWidths=[20 * mm, 255 * mm],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (1, 0), (1, 0), 6),
        ]))
        story = [header_table, Spacer(1, 6)]
    else:
        story = [
            P(settings.org_name, title),
            P(f"Murojaatlar hisoboti — {datetime.now(settings.tz).strftime('%d.%m.%Y %H:%M')}", sub),
            P(f"Filtrlar: {filters_desc}", sub),
            Spacer(1, 6),
        ]

    grid = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
    ])

    if stats:
        story.append(P("Umumiy ko‘rsatkichlar", h2))
        summary = [
            [P("Jami", cell_h), P("Yangi", cell_h), P("Jarayonda", cell_h), P("Hal qilingan", cell_h),
             P("Rad etilgan", cell_h), P("O‘rt. javob vaqti", cell_h), P("O‘rt. hal qilish vaqti", cell_h)],
            [P(stats["total"]), P(stats["new"]), P(stats["in_progress"]), P(stats["resolved"]),
             P(stats["rejected"]), P(human_duration(stats["avg_response_seconds"])),
             P(human_duration(stats["avg_resolution_seconds"]))],
        ]
        t = Table(summary, colWidths=[38 * mm] * 7)
        t.setStyle(grid)
        story += [t, Spacer(1, 4)]

        cat_rows = [[P("Yo‘nalish", cell_h), P("Soni", cell_h)]] + [
            [P(stats["labels"]["category"][k]), P(v)] for k, v in stats["by_category"].items()
        ]
        t = Table(cat_rows, colWidths=[80 * mm, 25 * mm])
        t.setStyle(grid)
        story += [P("Yo‘nalishlar bo‘yicha", h2), t]

        if stats["staff_performance"]:
            perf = [[P(h, cell_h) for h in ("Xodim", "Biriktirilgan", "Hal qilingan", "Rad etilgan",
                                             "Jarayonda", "Yakunlash, %", "O‘rt. javob", "O‘rt. hal qilish")]]
            for p in stats["staff_performance"]:
                perf.append([P(p["full_name"]), P(p["assigned"]), P(p["resolved"]), P(p["rejected"]),
                             P(p["open"]), P(p["completion_rate"]), P(human_duration(p["avg_response_seconds"])),
                             P(human_duration(p["avg_resolution_seconds"]))])
            t = Table(perf, colWidths=[60 * mm] + [27 * mm] * 7)
            t.setStyle(grid)
            story += [P("Xodimlar samaradorligi", h2), t]

    story.append(P(f"Murojaatlar ro‘yxati ({len(appeals)} ta)", h2))
    headers = ["№", "Raqam", "Sana", "F.I.Sh.", "Telefon", "Turi", "Yo‘nalish", "Mavzu", "Holat", "Mas'ul xodim"]
    rows = [[P(h, cell_h) for h in headers]]
    for i, a in enumerate(appeals, start=1):
        rows.append([
            P(i), P(a.number), P(fmt_dt(a.created_at)), P(a.full_name), P(a.phone),
            P(USER_TYPE_LABELS[a.user_type]), P(CATEGORY_LABELS[a.category]), P(truncate(a.subject, 120)),
            P(STATUS_LABELS[a.status]), P(a.assigned_staff.full_name if a.assigned_staff else "—"),
        ])
    widths = [9, 27, 24, 38, 25, 20, 36, 52, 26, 20]
    t = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1)
    t.setStyle(grid)
    story.append(t)

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(font, 7)
        canvas.drawRightString(doc_.pagesize[0] - 10 * mm, 6 * mm, f"Sahifa {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
