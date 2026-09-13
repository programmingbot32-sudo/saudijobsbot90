"""
مولد السيرة الذاتية PDF بثلاثة تصاميم احترافية باللغة العربية
"""

import os
import io
import re
from typing import Dict, Any, Optional

import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
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
    else:
        # Fallback to Helvetica if font missing
        pass


def ar(text: Optional[str]) -> str:
    """إعادة تشكيل وتوجيه النص العربي مع استبعاد الكلمات التلقائية العشوائية."""
    if not text or not isinstance(text, str):
        return ""
    cleaned = text.strip()
    if cleaned in {"غير محدد", "غير محددة", "لم يُضف", "لم يحدد", "null", "None", ""}:
        return ""
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
    """تفصيل السيرة المصممة إلى أقسام معالجة."""
    sections = {}
    current_section = "ملخص"
    lines = cv_text.splitlines()
    buffer = []

    for line in lines:
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("━━━━"):
            continue

        # Check if line is a header
        header_match = re.match(r"^(الاسم|بيانات التواصل|الملخص المهني|الملخص|الخبرات العملية|الخبرات|المهارات|التعليم|الشهادات والدورات|الشهادات|اللغات|الروابط|ملاحظات التحسين)", clean_line)
        if header_match and len(clean_line) < 30:
            if buffer:
                sections[current_section] = "\n".join(buffer).strip()
                buffer = []
            current_section = header_match.group(1)
        else:
            buffer.append(clean_line)

    if buffer:
        sections[current_section] = "\n".join(buffer).strip()

    return sections


def generate_pdf_cv(user: Dict[str, Any], cv_text: str = "", design_id: int = 1) -> bytes:
    """
    توليد ملف PDF للسيرة الذاتية حسب التصميم المختار (1، 2، 3)
    تصميم 1: كلاسيكي عصري (Modern Classic)
    تصميم 2: إبداعي بعمودين (Creative Two-Column)
    تصميم 3: تنفيذي أنيق (Executive Elegant)
    """
    _register_fonts()
    buffer = io.BytesIO()

    font_regular = FONT_NAME if _fonts_registered else "Helvetica"
    font_bold = FONT_BOLD_NAME if _fonts_registered else "Helvetica-Bold"

    parsed = parse_cv_text_to_sections(cv_text) if cv_text else {}

    # Extract user info cleanly without "غير محدد"
    name = user.get("full_name_ar") or user.get("full_name_en") or parsed.get("الاسم") or "سيرة ذاتية"
    email = user.get("email") if is_valid_val(user.get("email")) else ""
    phone = user.get("phone") if is_valid_val(user.get("phone")) else ""
    region = user.get("region") if is_valid_val(user.get("region")) else ""
    specialization = user.get("specialization") or user.get("category") if is_valid_val(user.get("specialization") or user.get("category")) else ""
    education = user.get("education_level") if is_valid_val(user.get("education_level")) else ""
    experience = user.get("experience_level") if is_valid_val(user.get("experience_level")) else ""
    linkedin = user.get("linkedin_url") if is_valid_val(user.get("linkedin_url")) else ""

    summary = parsed.get("الملخص المهني") or parsed.get("الملخص") or ""
    skills = parsed.get("المهارات") or ""
    exp_details = parsed.get("الخبرات العملية") or parsed.get("الخبرات") or parsed.get("المهارات والخبرات") or ""
    edu_details = parsed.get("التعليم") or parsed.get("التعليم والشهادات") or (f"• {education}" if education else "")
    certs = parsed.get("الشهادات والدورات") or parsed.get("الشهادات") or ""
    languages = parsed.get("اللغات") or ""

    if design_id == 2:
        return _build_design_2(buffer, name, specialization, phone, email, region, linkedin, education, experience, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold)
    elif design_id == 3:
        return _build_design_3(buffer, name, specialization, phone, email, region, linkedin, education, experience, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold)
    else:
        return _build_design_1(buffer, name, specialization, phone, email, region, linkedin, education, experience, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold)


def _build_design_1(buffer, name, specialization, phone, email, region, linkedin, education, experience, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold):
    """تصميم 1: كلاسيكي عصري (Modern Classic)"""
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    primary_color = colors.HexColor("#1A365D")   # Deep Navy
    accent_color = colors.HexColor("#0D9488")    # Teal Accent
    text_dark = colors.HexColor("#1F2937")       # Charcoal

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        'HeaderName',
        fontName=font_bold,
        fontSize=24,
        leading=28,
        textColor=primary_color,
        alignment=2 # Right
    )

    title_style = ParagraphStyle(
        'HeaderTitle',
        fontName=font_regular,
        fontSize=14,
        leading=18,
        textColor=accent_color,
        alignment=2
    )

    contact_style = ParagraphStyle(
        'HeaderContact',
        fontName=font_regular,
        fontSize=10,
        leading=14,
        textColor=text_dark,
        alignment=2
    )

    sec_header_style = ParagraphStyle(
        'SecHeader',
        fontName=font_bold,
        fontSize=14,
        leading=18,
        textColor=primary_color,
        alignment=2
    )

    body_style = ParagraphStyle(
        'BodyTextAr',
        fontName=font_regular,
        fontSize=10,
        leading=15,
        textColor=text_dark,
        alignment=2
    )

    story = []

    # Header Name & Specialization
    story.append(Paragraph(ar(name), name_style))
    if specialization:
        story.append(Paragraph(ar(specialization), title_style))
    story.append(Spacer(1, 8))

    # Contact line
    contact_parts = []
    if phone: contact_parts.append(f"📱 {phone}")
    if email: contact_parts.append(f"📧 {email}")
    if region: contact_parts.append(f"📍 {region}")
    if linkedin: contact_parts.append(f"🔗 {linkedin}")

    if contact_parts:
        contact_line = " | ".join(contact_parts)
        story.append(Paragraph(ar(contact_line), contact_style))
        story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceBefore=4, spaceAfter=15))

    # Professional Summary
    if summary:
        story.append(Paragraph(ar("الملخص المهني"), sec_header_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=2, spaceAfter=6))
        for line in summary.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))
        story.append(Spacer(1, 12))

    # Experience
    if exp_details:
        story.append(Paragraph(ar("الخبرات العملية والمهنية"), sec_header_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=2, spaceAfter=6))
        for line in exp_details.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))
        story.append(Spacer(1, 12))

    # Education
    if edu_details or education:
        story.append(Paragraph(ar("التعليم والشهادات الأكاديمية"), sec_header_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=2, spaceAfter=6))
        content = edu_details if edu_details else f"• {education}"
        for line in content.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))
        story.append(Spacer(1, 12))

    # Skills
    if skills:
        story.append(Paragraph(ar("المهارات والقدرات"), sec_header_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=2, spaceAfter=6))
        for line in skills.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))
        story.append(Spacer(1, 12))

    # Certifications & Courses
    if certs:
        story.append(Paragraph(ar("الدورات والشهادات التخصصية"), sec_header_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=2, spaceAfter=6))
        for line in certs.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))
        story.append(Spacer(1, 12))

    # Languages
    if languages:
        story.append(Paragraph(ar("اللغات"), sec_header_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=2, spaceAfter=6))
        for line in languages.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


def _build_design_2(buffer, name, specialization, phone, email, region, linkedin, education, experience, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold):
    """تصميم 2: إبداعي بعمودين (Creative Two-Column Layout)"""
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    sidebar_bg = colors.HexColor("#2C3E50")
    main_header_color = colors.HexColor("#16A085")
    text_dark = colors.HexColor("#2C3E50")
    text_white = colors.HexColor("#FFFFFF")

    styles = getSampleStyleSheet()

    sidebar_header_style = ParagraphStyle(
        'SideHeader',
        fontName=font_bold,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1ABC9C"),
        alignment=2
    )

    sidebar_text_style = ParagraphStyle(
        'SideText',
        fontName=font_regular,
        fontSize=9.5,
        leading=14,
        textColor=text_white,
        alignment=2
    )

    main_name_style = ParagraphStyle(
        'MainName',
        fontName=font_bold,
        fontSize=22,
        leading=26,
        textColor=main_header_color,
        alignment=2
    )

    main_title_style = ParagraphStyle(
        'MainTitle',
        fontName=font_regular,
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#7F8C8D"),
        alignment=2
    )

    main_sec_style = ParagraphStyle(
        'MainSec',
        fontName=font_bold,
        fontSize=13,
        leading=17,
        textColor=main_header_color,
        alignment=2
    )

    main_body_style = ParagraphStyle(
        'MainBody',
        fontName=font_regular,
        fontSize=10,
        leading=15,
        textColor=text_dark,
        alignment=2
    )

    # Build Left/Right contents (Arabic: Right column is main, Left column is sidebar or vice versa)
    sidebar_elements = []

    # Contact in Sidebar
    sidebar_elements.append(Paragraph(ar("معلومات التواصل"), sidebar_header_style))
    sidebar_elements.append(Spacer(1, 4))
    if phone: sidebar_elements.append(Paragraph(ar(f"📱 {phone}"), sidebar_text_style))
    if email: sidebar_elements.append(Paragraph(ar(f"📧 {email}"), sidebar_text_style))
    if region: sidebar_elements.append(Paragraph(ar(f"📍 {region}"), sidebar_text_style))
    if linkedin: sidebar_elements.append(Paragraph(ar(f"🔗 {linkedin}"), sidebar_text_style))
    sidebar_elements.append(Spacer(1, 14))

    if education or edu_details:
        sidebar_elements.append(Paragraph(ar("المؤهل الدراسي"), sidebar_header_style))
        sidebar_elements.append(Spacer(1, 4))
        content = edu_details if edu_details else education
        for l in content.splitlines():
            if l.strip():
                sidebar_elements.append(Paragraph(ar(l), sidebar_text_style))
        sidebar_elements.append(Spacer(1, 14))

    if skills:
        sidebar_elements.append(Paragraph(ar("المهارات"), sidebar_header_style))
        sidebar_elements.append(Spacer(1, 4))
        for l in skills.splitlines():
            if l.strip():
                sidebar_elements.append(Paragraph(ar(l), sidebar_text_style))
        sidebar_elements.append(Spacer(1, 14))

    if languages:
        sidebar_elements.append(Paragraph(ar("اللغات"), sidebar_header_style))
        sidebar_elements.append(Spacer(1, 4))
        for l in languages.splitlines():
            if l.strip():
                sidebar_elements.append(Paragraph(ar(l), sidebar_text_style))

    main_elements = []
    main_elements.append(Paragraph(ar(name), main_name_style))
    if specialization:
        main_elements.append(Paragraph(ar(specialization), main_title_style))
    main_elements.append(Spacer(1, 10))

    if summary:
        main_elements.append(Paragraph(ar("الملخص المهني"), main_sec_style))
        main_elements.append(HRFlowable(width="100%", thickness=1, color=main_header_color, spaceBefore=2, spaceAfter=6))
        for l in summary.splitlines():
            if l.strip():
                main_elements.append(Paragraph(ar(l), main_body_style))
        main_elements.append(Spacer(1, 12))

    if exp_details:
        main_elements.append(Paragraph(ar("الخبرات العملية"), main_sec_style))
        main_elements.append(HRFlowable(width="100%", thickness=1, color=main_header_color, spaceBefore=2, spaceAfter=6))
        for l in exp_details.splitlines():
            if l.strip():
                main_elements.append(Paragraph(ar(l), main_body_style))
        main_elements.append(Spacer(1, 12))

    if certs:
        main_elements.append(Paragraph(ar("الدورات والشهادات"), main_sec_style))
        main_elements.append(HRFlowable(width="100%", thickness=1, color=main_header_color, spaceBefore=2, spaceAfter=6))
        for l in certs.splitlines():
            if l.strip():
                main_elements.append(Paragraph(ar(l), main_body_style))

    # Place in a 2-column Table (Right: Main content, Left: Sidebar)
    table_data = [[sidebar_elements, main_elements]]
    table = Table(table_data, colWidths=[180, 370])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), sidebar_bg),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (0, 0), 12),
        ('RIGHTPADDING', (0, 0), (0, 0), 12),
        ('LEFTPADDING', (1, 0), (1, 0), 15),
        ('RIGHTPADDING', (1, 0), (1, 0), 15),
    ]))

    doc.build([table])
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


def _build_design_3(buffer, name, specialization, phone, email, region, linkedin, education, experience, summary, skills, exp_details, edu_details, certs, languages, font_regular, font_bold):
    """تصميم 3: تنفيذي أنيق (Executive Elegant Design)"""
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=0,
        bottomMargin=36
    )

    primary_dark = colors.HexColor("#1E293B")   # Slate 800
    gold_accent = colors.HexColor("#D97706")    # Amber/Gold
    text_dark = colors.HexColor("#334155")

    styles = getSampleStyleSheet()

    header_name_style = ParagraphStyle(
        'ExecName',
        fontName=font_bold,
        fontSize=24,
        leading=28,
        textColor=colors.white,
        alignment=1 # Center
    )

    header_title_style = ParagraphStyle(
        'ExecTitle',
        fontName=font_regular,
        fontSize=13,
        leading=17,
        textColor=gold_accent,
        alignment=1
    )

    header_contact_style = ParagraphStyle(
        'ExecContact',
        fontName=font_regular,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#E2E8F0"),
        alignment=1
    )

    sec_title_style = ParagraphStyle(
        'ExecSecTitle',
        fontName=font_bold,
        fontSize=13,
        leading=17,
        textColor=primary_dark,
        alignment=2
    )

    body_style = ParagraphStyle(
        'ExecBody',
        fontName=font_regular,
        fontSize=10,
        leading=15,
        textColor=text_dark,
        alignment=2
    )

    header_elements = []
    header_elements.append(Spacer(1, 15))
    header_elements.append(Paragraph(ar(name), header_name_style))
    if specialization:
        header_elements.append(Paragraph(ar(specialization), header_title_style))
    header_elements.append(Spacer(1, 6))

    contact_parts = []
    if phone: contact_parts.append(f"📱 {phone}")
    if email: contact_parts.append(f"📧 {email}")
    if region: contact_parts.append(f"📍 {region}")
    if linkedin: contact_parts.append(f"🔗 {linkedin}")

    if contact_parts:
        header_elements.append(Paragraph(ar("  •  ".join(contact_parts)), header_contact_style))
    header_elements.append(Spacer(1, 15))

    header_table = Table([[header_elements]], colWidths=[522])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), primary_dark),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))

    story = [header_table, Spacer(1, 20)]

    # Executive Summary
    if summary:
        story.append(Paragraph(ar("📌 نبذة executive"), sec_title_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=gold_accent, spaceBefore=3, spaceAfter=8))
        for line in summary.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))
        story.append(Spacer(1, 12))

    # Professional Experience
    if exp_details:
        story.append(Paragraph(ar("💼 السجل المهني والخبرات"), sec_title_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=gold_accent, spaceBefore=3, spaceAfter=8))
        for line in exp_details.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))
        story.append(Spacer(1, 12))

    # Education & Certifications
    if edu_details or education or certs:
        story.append(Paragraph(ar("🎓 التأهيل الأكاديمي والشهادات"), sec_title_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=gold_accent, spaceBefore=3, spaceAfter=8))
        content = edu_details if edu_details else education
        if content:
            for line in content.splitlines():
                if line.strip():
                    story.append(Paragraph(ar(line), body_style))
        if certs:
            for line in certs.splitlines():
                if line.strip():
                    story.append(Paragraph(ar(line), body_style))
        story.append(Spacer(1, 12))

    # Core Competencies & Skills
    if skills:
        story.append(Paragraph(ar("⭐ المهارات الأساسية"), sec_title_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=gold_accent, spaceBefore=3, spaceAfter=8))
        for line in skills.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))
        story.append(Spacer(1, 12))

    # Languages
    if languages:
        story.append(Paragraph(ar("🌐 اللغات"), sec_title_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=gold_accent, spaceBefore=3, spaceAfter=8))
        for line in languages.splitlines():
            if line.strip():
                story.append(Paragraph(ar(line), body_style))

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
