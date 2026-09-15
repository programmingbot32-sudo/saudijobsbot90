"""
مولد السيرة الذاتية PDF بثلاثة تصاميم احترافية باللغتين العربية والإنجليزية
"""

import os
import io
import re
from typing import Dict, Any, Optional

import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
REGULAR_FONT_PATH = os.path.join(FONT_DIR, "Amiri-Regular.ttf")
BOLD_FONT_PATH = os.path.join(FONT_DIR, "Amiri-Bold.ttf")

FONT_NAME = "Amiri"
FONT_BOLD_NAME = "Amiri-Bold"

_fonts_registered = False


def _register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    if os.path.exists(REGULAR_FONT_PATH) and os.path.exists(BOLD_FONT_PATH):
        pdfmetrics.registerFont(TTFont(FONT_NAME, REGULAR_FONT_PATH))
        pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, BOLD_FONT_PATH))
        _fonts_registered = True


def ar(text: Optional[str], lang: str = "ar") -> str:
    """إعادة تشكيل وتوجيه أي نص يتضمن حروفاً عربية لتجنب عكس الأحرف أو انفصالها."""
    if not text or not isinstance(text, str):
        return ""
    cleaned = text.strip()
    if cleaned in {"غير محدد", "غير محددة", "لم يُضف", "لم يحدد", "null", "None", ""}:
        return ""

    has_arabic = bool(re.search(r"[\u0600-\u06FF]", cleaned))
    if not has_arabic and lang == "en":
        return cleaned

    try:
        reshaped = arabic_reshaper.reshape(cleaned)
        return get_display(reshaped)
    except Exception:
        return cleaned


def is_valid_val(val: Optional[str]) -> bool:
    if not val or not isinstance(val, str):
        return False
    v = val.strip()
    return v != "" and v not in {"غير محدد", "غير محددة", "لم يُضف", "لم يحدد", "null", "None"}


def parse_cv_text_to_sections(cv_text: str) -> Dict[str, str]:
    """تفصيل نص السيرة الذاتية إلى أقسام معالجة بدقة باللغتين العربية والإنجليزية."""
    sections = {}
    current_section = "الملخص المهني"
    lines = cv_text.splitlines()
    buffer = []

    header_patterns = [
        ("الاسم", r"^(Name|الاسم|Contact Information|بيانات التواصل)"),
        ("الملخص المهني", r"^(Professional Summary|Summary|الملخص المهني|الملخص|نبذة)"),
        ("الخبرات العملية", r"^(Work Experience|Experience|الخبرات العملية|الخبرات|السجل المهني)"),
        ("المهارات", r"^(Skills & Competencies|Skills|المهارات والقدرات|المهارات)"),
        ("التعليم", r"^(Education & Qualifications|Education|التعليم والمؤهلات|التعليم)"),
        ("الشهادات والدورات", r"^(Certifications & Courses|Certifications|الشهادات والدورات|الشهادات)"),
        ("اللغات", r"^(Languages|اللغات)"),
    ]

    for line in lines:
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("━━━━"):
            continue

        matched_header = None
        for canonical_name, pattern in header_patterns:
            if re.match(pattern, clean_line, re.IGNORECASE) and (len(clean_line) < 45 or clean_line.endswith(":")):
                matched_header = canonical_name
                break

        if matched_header:
            if buffer:
                sections[current_section] = "\n".join(buffer).strip()
                buffer = []
            current_section = matched_header
            if ":" in clean_line:
                after_colon = clean_line.split(":", 1)[1].strip()
                if after_colon:
                    buffer.append(after_colon)
        else:
            buffer.append(clean_line)

    if buffer:
        sections[current_section] = "\n".join(buffer).strip()

    return sections


def generate_pdf_cv(user: Dict[str, Any], cv_text: str = "", design_id: int = 1, lang: str = "ar") -> bytes:
    """توليد ملف PDF احترافي كامل الصفحة بحسب التصميم واللغة المحددة."""
    _register_fonts()
    buffer = io.BytesIO()

    font_regular = FONT_NAME if _fonts_registered else "Helvetica"
    font_bold = FONT_BOLD_NAME if _fonts_registered else "Helvetica-Bold"

    parsed = parse_cv_text_to_sections(cv_text) if cv_text else {}

    default_name = "Professional Resume" if lang == "en" else "سيرة ذاتية احترافية"
    name = user.get("full_name_en" if lang == "en" else "full_name_ar") or user.get("full_name_ar") or parsed.get("الاسم") or default_name
    email = user.get("email") if is_valid_val(user.get("email")) else ""
    phone = user.get("phone") if is_valid_val(user.get("phone")) else ""
    region = user.get("region") if is_valid_val(user.get("region")) else ""
    specialization = user.get("specialization") or user.get("category") if is_valid_val(user.get("specialization") or user.get("category")) else ""
    education = user.get("education_level") if is_valid_val(user.get("education_level")) else ""
    linkedin = user.get("linkedin_url") if is_valid_val(user.get("linkedin_url")) else ""

    summary = parsed.get("الملخص المهني") or parsed.get("الملخص") or ""
    skills = parsed.get("المهارات") or ""
    exp_details = parsed.get("الخبرات العملية") or parsed.get("الخبرات") or ""
    edu_details = parsed.get("التعليم") or parsed.get("التعليم والشهادات") or (f"• {education}" if education else "")
    certs = parsed.get("الشهادات والدورات") or parsed.get("الشهادات") or ""
    languages = parsed.get("اللغات") or ""

    if design_id == 2:
        return _build_design_2(buffer, name, specialization, phone, email, region, linkedin, education, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold, lang)
    elif design_id == 3:
        return _build_design_3(buffer, name, specialization, phone, email, region, linkedin, education, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold, lang)
    else:
        return _build_design_1(buffer, name, specialization, phone, email, region, linkedin, education, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold, lang)


def _build_design_1(buffer, name, specialization, phone, email, region, linkedin, education, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold, lang="ar"):
    """تصميم 1: كلاسيكي عصري (Modern Classic Banner Header)"""
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=20,
        bottomMargin=36
    )

    primary_color = colors.HexColor("#1A365D")   # Deep Navy
    teal_accent = colors.HexColor("#0D9488")     # Teal Accent
    text_dark = colors.HexColor("#1F2937")       # Charcoal

    body_align = 0 if lang == "en" else 2

    header_name_style = ParagraphStyle(
        'D1Name', fontName=font_bold, fontSize=24, leading=28, textColor=colors.white, alignment=1
    )
    header_title_style = ParagraphStyle(
        'D1Title', fontName=font_bold, fontSize=13, leading=17, textColor=colors.HexColor("#5EEAD4"), alignment=1
    )
    header_contact_style = ParagraphStyle(
        'D1Contact', fontName=font_regular, fontSize=10, leading=14, textColor=colors.HexColor("#F1F5F9"), alignment=1
    )
    sec_header_style = ParagraphStyle(
        'D1SecHeader', fontName=font_bold, fontSize=14, leading=18, textColor=primary_color, alignment=body_align
    )
    body_style = ParagraphStyle(
        'D1BodyText', fontName=font_regular, fontSize=10.5, leading=16, textColor=text_dark, alignment=body_align
    )

    header_flowables = [Spacer(1, 10), Paragraph(ar(name, lang), header_name_style)]
    if specialization:
        header_flowables.append(Paragraph(ar(specialization, lang), header_title_style))
    header_flowables.append(Spacer(1, 6))

    contact_parts = []
    if phone: contact_parts.append(f"📱 {phone}")
    if email: contact_parts.append(f"📧 {email}")
    if region: contact_parts.append(f"📍 {region}")
    if linkedin: contact_parts.append(f"🔗 {linkedin}")

    if contact_parts:
        header_flowables.append(Paragraph(ar("  |  ".join(contact_parts), lang), header_contact_style))
    header_flowables.append(Spacer(1, 12))

    header_table = Table([[header_flowables]], colWidths=[522])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), primary_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))

    story = [header_table, Spacer(1, 18)]

    if lang == "en":
        sections_data = [
            ("Professional Summary", summary),
            ("Work Experience", exp_details),
            ("Skills & Competencies", skills),
            ("Education & Qualifications", edu_details or education),
            ("Certifications & Courses", certs),
            ("Languages", languages),
        ]
    else:
        sections_data = [
            ("الملخص المهني", summary),
            ("الخبرات العملية والمهنية", exp_details),
            ("المهارات والقدرات", skills),
            ("التعليم والمؤهلات الأكاديمية", edu_details or education),
            ("الدورات والشهادات التخصصية", certs),
            ("إتقان اللغات", languages),
        ]

    for sec_title, content in sections_data:
        if content and content.strip():
            story.append(Paragraph(ar(sec_title, lang), sec_header_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=teal_accent, spaceBefore=3, spaceAfter=8))
            for line in content.splitlines():
                if line.strip():
                    bullet = "• " if not line.strip().startswith("•") else ""
                    story.append(Paragraph(ar(f"{bullet}{line.strip()}", lang), body_style))
            story.append(Spacer(1, 14))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


def _build_design_2(buffer, name, specialization, phone, email, region, linkedin, education, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold, lang="ar"):
    """تصميم 2: إبداعي بعمودين (Creative Two-Column Layout)"""
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    sidebar_bg = colors.HexColor("#1E293B")
    main_header_color = colors.HexColor("#0284C7")
    text_dark = colors.HexColor("#1F2937")
    text_white = colors.HexColor("#FFFFFF")

    body_align = 0 if lang == "en" else 2

    sidebar_header_style = ParagraphStyle(
        'D2SideHeader', fontName=font_bold, fontSize=12, leading=16, textColor=colors.HexColor("#38BDF8"), alignment=body_align
    )
    sidebar_text_style = ParagraphStyle(
        'D2SideText', fontName=font_regular, fontSize=9.5, leading=14, textColor=text_white, alignment=body_align
    )
    main_name_style = ParagraphStyle(
        'D2MainName', fontName=font_bold, fontSize=24, leading=28, textColor=main_header_color, alignment=body_align
    )
    main_title_style = ParagraphStyle(
        'D2MainTitle', fontName=font_bold, fontSize=13, leading=17, textColor=colors.HexColor("#475569"), alignment=body_align
    )
    main_sec_style = ParagraphStyle(
        'D2MainSec', fontName=font_bold, fontSize=13, leading=17, textColor=main_header_color, alignment=body_align
    )
    main_body_style = ParagraphStyle(
        'D2MainBody', fontName=font_regular, fontSize=10, leading=15, textColor=text_dark, alignment=body_align
    )

    sidebar_elements = []
    contact_title = "Contact Information" if lang == "en" else "معلومات التواصل"
    skills_title = "Skills & Competencies" if lang == "en" else "المهارات والقدرات"
    lang_title = "Languages" if lang == "en" else "اللغات"
    edu_title = "Education" if lang == "en" else "المؤهل الأكاديمي"

    sidebar_elements.append(Paragraph(ar(contact_title, lang), sidebar_header_style))
    sidebar_elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#38BDF8"), spaceBefore=2, spaceAfter=6))
    if phone: sidebar_elements.append(Paragraph(ar(f"📱 {phone}", lang), sidebar_text_style))
    if email: sidebar_elements.append(Paragraph(ar(f"📧 {email}", lang), sidebar_text_style))
    if region: sidebar_elements.append(Paragraph(ar(f"📍 {region}", lang), sidebar_text_style))
    if linkedin: sidebar_elements.append(Paragraph(ar(f"🔗 {linkedin}", lang), sidebar_text_style))
    sidebar_elements.append(Spacer(1, 16))

    if skills:
        sidebar_elements.append(Paragraph(ar(skills_title, lang), sidebar_header_style))
        sidebar_elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#38BDF8"), spaceBefore=2, spaceAfter=6))
        for line in skills.splitlines():
            if line.strip():
                sidebar_elements.append(Paragraph(ar(f"• {line.strip()}", lang), sidebar_text_style))
        sidebar_elements.append(Spacer(1, 16))

    if languages:
        sidebar_elements.append(Paragraph(ar(lang_title, lang), sidebar_header_style))
        sidebar_elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#38BDF8"), spaceBefore=2, spaceAfter=6))
        for line in languages.splitlines():
            if line.strip():
                sidebar_elements.append(Paragraph(ar(f"• {line.strip()}", lang), sidebar_text_style))
        sidebar_elements.append(Spacer(1, 16))

    if edu_details or education:
        sidebar_elements.append(Paragraph(ar(edu_title, lang), sidebar_header_style))
        sidebar_elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#38BDF8"), spaceBefore=2, spaceAfter=6))
        content = edu_details if edu_details else education
        for line in content.splitlines():
            if line.strip():
                sidebar_elements.append(Paragraph(ar(f"• {line.strip()}", lang), sidebar_text_style))

    main_elements = []
    main_elements.append(Paragraph(ar(name, lang), main_name_style))
    if specialization:
        main_elements.append(Paragraph(ar(specialization, lang), main_title_style))
    main_elements.append(Spacer(1, 12))

    summary_title = "Professional Summary" if lang == "en" else "الملخص المهني"
    exp_title = "Work Experience" if lang == "en" else "الخبرات العملية والمهنية"
    cert_title = "Certifications & Courses" if lang == "en" else "الدورات والشهادات"

    if summary:
        main_elements.append(Paragraph(ar(summary_title, lang), main_sec_style))
        main_elements.append(HRFlowable(width="100%", thickness=1.5, color=main_header_color, spaceBefore=2, spaceAfter=6))
        for line in summary.splitlines():
            if line.strip():
                main_elements.append(Paragraph(ar(line.strip(), lang), main_body_style))
        main_elements.append(Spacer(1, 16))

    if exp_details:
        main_elements.append(Paragraph(ar(exp_title, lang), main_sec_style))
        main_elements.append(HRFlowable(width="100%", thickness=1.5, color=main_header_color, spaceBefore=2, spaceAfter=6))
        for line in exp_details.splitlines():
            if line.strip():
                main_elements.append(Paragraph(ar(f"• {line.strip()}", lang), main_body_style))
        main_elements.append(Spacer(1, 16))

    if certs:
        main_elements.append(Paragraph(ar(cert_title, lang), main_sec_style))
        main_elements.append(HRFlowable(width="100%", thickness=1.5, color=main_header_color, spaceBefore=2, spaceAfter=6))
        for line in certs.splitlines():
            if line.strip():
                main_elements.append(Paragraph(ar(f"• {line.strip()}", lang), main_body_style))

    # In English (LTR), Sidebar is on the left (col 0) and Main is on the right (col 1)
    # In Arabic (RTL), Main is on the right (col 1) and Sidebar is on the left (col 0)
    table_data = [[sidebar_elements, main_elements]]
    table = Table(table_data, colWidths=[180, 370], rowHeights=[750])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), sidebar_bg),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 18),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
        ('LEFTPADDING', (0, 0), (0, 0), 14),
        ('RIGHTPADDING', (0, 0), (0, 0), 14),
        ('LEFTPADDING', (1, 0), (1, 0), 16),
        ('RIGHTPADDING', (1, 0), (1, 0), 16),
    ]))

    doc.build([table])
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


def _build_design_3(buffer, name, specialization, phone, email, region, linkedin, education, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold, lang="ar"):
    """تصميم 3: تنفيذي أنيق (Executive Dark Header & Gold Dividers)"""
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=0,
        bottomMargin=36
    )

    primary_dark = colors.HexColor("#0F172A")    # Slate 900
    gold_accent = colors.HexColor("#D97706")     # Amber Gold
    text_dark = colors.HexColor("#334155")

    body_align = 0 if lang == "en" else 2

    header_name_style = ParagraphStyle(
        'D3Name', fontName=font_bold, fontSize=24, leading=28, textColor=colors.white, alignment=1
    )
    header_title_style = ParagraphStyle(
        'D3Title', fontName=font_bold, fontSize=13, leading=17, textColor=gold_accent, alignment=1
    )
    header_contact_style = ParagraphStyle(
        'D3Contact', fontName=font_regular, fontSize=9.5, leading=14, textColor=colors.HexColor("#E2E8F0"), alignment=1
    )
    sec_title_style = ParagraphStyle(
        'D3SecTitle', fontName=font_bold, fontSize=13, leading=17, textColor=primary_dark, alignment=body_align
    )
    body_style = ParagraphStyle(
        'D3BodyText', fontName=font_regular, fontSize=10.5, leading=16, textColor=text_dark, alignment=body_align
    )

    header_elements = [Spacer(1, 15), Paragraph(ar(name, lang), header_name_style)]
    if specialization:
        header_elements.append(Paragraph(ar(specialization, lang), header_title_style))
    header_elements.append(Spacer(1, 6))

    contact_parts = []
    if phone: contact_parts.append(f"📱 {phone}")
    if email: contact_parts.append(f"📧 {email}")
    if region: contact_parts.append(f"📍 {region}")
    if linkedin: contact_parts.append(f"🔗 {linkedin}")

    if contact_parts:
        header_elements.append(Paragraph(ar("  •  ".join(contact_parts), lang), header_contact_style))
    header_elements.append(Spacer(1, 15))

    header_table = Table([[header_elements]], colWidths=[522])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), primary_dark),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))

    story = [header_table, Spacer(1, 20)]

    if lang == "en":
        sections_data = [
            ("📌 Professional Summary", summary),
            ("💼 Work Experience", exp_details),
            ("⭐ Core Competencies & Skills", skills),
            ("🎓 Education & Qualifications", edu_details or education),
            ("📜 Certifications & Courses", certs),
            ("🌐 Languages", languages),
        ]
    else:
        sections_data = [
            ("📌 الملخص التنفيذي", summary),
            ("💼 السجل المهني والخبرات", exp_details),
            ("⭐ المهارات والقدرات الأساسية", skills),
            ("🎓 التأهيل الأكاديمي والتعليم", edu_details or education),
            ("📜 الدورات والشهادات التخصصية", certs),
            ("🌐 اللغات", languages),
        ]

    for sec_title, content in sections_data:
        if content and content.strip():
            story.append(Paragraph(ar(sec_title, lang), sec_title_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=gold_accent, spaceBefore=3, spaceAfter=8))
            for line in content.splitlines():
                if line.strip():
                    bullet = "• " if not line.strip().startswith("•") else ""
                    story.append(Paragraph(ar(f"{bullet}{line.strip()}", lang), body_style))
            story.append(Spacer(1, 14))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
