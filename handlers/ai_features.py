"""تدفقات خدمات الذكاء الاصطناعي: بناء السيرة والبحث عن الوظائف."""

import io
import re
import zipfile
from html import unescape
from typing import Dict, List

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config.settings import States
from database.db import get_user, get_jobs_page, update_user_field
from keyboards.keyboards import (
    get_ai_cv_collect_keyboard,
    get_cv_design_selection_keyboard,
    get_ai_job_more_keyboard,
    get_ai_job_search_keyboard,
)
from utils.ai_helper import ai_generate_professional_cv, ai_generate_english_cv
from utils.pdf_generator import generate_pdf_cv
from utils.matching import score_match


def _is_cancel(text: str) -> bool:
    return (text or "").strip().lower() in {
        "الغاء", "إلغاء", "الغاء العملية", "إلغاء العملية", "/cancel"
    }


async def start_ai_cv_builder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء جلسة بناء السيرة الذاتية بالتسلسل المباشر."""
    context.user_data["cv_data"] = {}
    context.user_data["cv_design_id"] = 1
    context.user_data["state"] = States.AI_CV_NAME

    message = "🤖 *بناء السيرة الذاتية الاحترافية*\n\nما اسمك؟"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            message, parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            message, parse_mode=ParseMode.MARKDOWN
        )


async def prompt_next_cv_step(update: Update, context: ContextTypes.DEFAULT_TYPE, next_state: str):
    """إرسال السؤال التالي في سلسلة بناء السيرة الذاتية."""
    from keyboards.keyboards import get_ai_cv_skip_keyboard
    context.user_data["state"] = next_state
    target = update.message or (update.callback_query.message if update.callback_query else None)

    if next_state == States.AI_CV_PHONE:
        msg = "رقم الجوال"
        markup = None
    elif next_state == States.AI_CV_EMAIL:
        msg = "اكتب ايميلك"
        markup = get_ai_cv_skip_keyboard("ai_cv_skip_email")
    elif next_state == States.AI_CV_EDUCATION:
        msg = "تعليمك ( الدرجة - الجامعة - السنة)"
        markup = get_ai_cv_skip_keyboard("ai_cv_skip_education")
    elif next_state == States.AI_CV_SKILLS:
        msg = "مهاراتك"
        markup = get_ai_cv_skip_keyboard("ai_cv_skip_skills")
    elif next_state == States.AI_CV_EXPERIENCE:
        msg = "خبراتك (اسم الشركة والفترة )"
        markup = get_ai_cv_skip_keyboard("ai_cv_skip_experience")
    elif next_state == States.AI_CV_LANGUAGES:
        msg = "اللغات (مثلا اللغة العربية ، جيد باللغة الانجليزية)"
        markup = get_ai_cv_skip_keyboard("ai_cv_skip_languages")
    elif next_state == States.AI_CV_SUMMARY:
        await show_ai_cv_summary(update, context)
        return

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            msg, reply_markup=markup
        )
    elif target:
        await target.reply_text(
            msg, reply_markup=markup
        )


async def show_ai_cv_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض مراجعة البيانات للعميل مع زر إكمال وتعديل."""
    from keyboards.keyboards import get_ai_cv_summary_keyboard
    context.user_data["state"] = States.AI_CV_SUMMARY
    cv = context.user_data.get("cv_data", {})
    name = cv.get("name") or "غير محدد"
    phone = cv.get("phone") or "غير محدد"
    email = cv.get("email") or "لم يضف"
    education = cv.get("education") or "لم يضف"
    skills = cv.get("skills") or "لم يضف"
    experience = cv.get("experience") or "لم يضف"
    languages = cv.get("languages") or "لم يضف"

    msg = (
        "📌 *تأكيد بيانات السيرة الذاتية:*\n\n"
        f"👤 *الاسم:* {name}\n"
        f"📱 *الجوال:* {phone}\n"
        f"📧 *البريد الإلكتروني:* {email}\n"
        f"🎓 *التعليم:* {education}\n"
        f"💡 *المهارات:* {skills}\n"
        f"💼 *الخبرات:* {experience}\n"
        f"🌐 *اللغات:* {languages}\n\n"
        "يرجى مراجعة بياناتك ثم اختيار *إكمال* للاختيار بين تصاميم السيرة أو *تعديل* لإعادة إدخال البيانات."
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_ai_cv_summary_keyboard()
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_ai_cv_summary_keyboard()
        )


async def collect_ai_cv_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """حفظ إجابة المستخدم والانتقال للخطوة التالية."""
    state = context.user_data.get("state")
    cv_states = {
        States.AI_CV_COLLECT, States.AI_CV_NAME, States.AI_CV_PHONE,
        States.AI_CV_EMAIL, States.AI_CV_EDUCATION, States.AI_CV_SKILLS,
        States.AI_CV_EXPERIENCE, States.AI_CV_LANGUAGES, States.AI_CV_SUMMARY
    }
    if state not in cv_states:
        return False

    text = (update.message.text or "").strip()
    if _is_cancel(text):
        await cancel_ai_cv(update, context)
        return True

    cv_data = context.user_data.setdefault("cv_data", {})

    if state == States.AI_CV_NAME:
        cv_data["name"] = text
        await prompt_next_cv_step(update, context, States.AI_CV_PHONE)
        return True

    elif state == States.AI_CV_PHONE:
        cv_data["phone"] = text
        await prompt_next_cv_step(update, context, States.AI_CV_EMAIL)
        return True

    elif state == States.AI_CV_EMAIL:
        cv_data["email"] = text
        await prompt_next_cv_step(update, context, States.AI_CV_EDUCATION)
        return True

    elif state == States.AI_CV_EDUCATION:
        cv_data["education"] = text
        await prompt_next_cv_step(update, context, States.AI_CV_SKILLS)
        return True

    elif state == States.AI_CV_SKILLS:
        cv_data["skills"] = text
        await prompt_next_cv_step(update, context, States.AI_CV_EXPERIENCE)
        return True

    elif state == States.AI_CV_EXPERIENCE:
        cv_data["experience"] = text
        await prompt_next_cv_step(update, context, States.AI_CV_LANGUAGES)
        return True

    elif state == States.AI_CV_LANGUAGES:
        cv_data["languages"] = text
        await prompt_next_cv_step(update, context, States.AI_CV_SUMMARY)
        return True

    elif state in {States.AI_CV_COLLECT, States.AI_CV_SUMMARY}:
        await show_ai_cv_summary(update, context)
        return True

    return False


async def collect_ai_cv_file(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """تنبيه المستخدم بعدم الحاجة لرفع صورة أو ملفات."""
    state = context.user_data.get("state")
    cv_states = {
        States.AI_CV_COLLECT, States.AI_CV_NAME, States.AI_CV_PHONE,
        States.AI_CV_EMAIL, States.AI_CV_EDUCATION, States.AI_CV_SKILLS,
        States.AI_CV_EXPERIENCE, States.AI_CV_LANGUAGES, States.AI_CV_SUMMARY
    }
    if state in cv_states:
        await update.message.reply_text(
            "ℹ️ لا يلزم رفع صور أو ملفات. يرجى كتابة البيانات المطلوبة نصياً مباشرة."
        )
        return True
    return False


def _docx_text(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", "ignore")
        return re.sub(r"<[^>]+>", " ", unescape(xml)).replace("\\n", " ")
    except Exception:
        return ""


def _pdf_text(raw: bytes) -> str:
    # استخراج بسيط للنص المتاح داخل PDF، ولا يجعل غياب مكتبة PDF عائقاً للتدفق.
    chunks = re.findall(rb"\(([^()]{2,400})\)", raw)
    return " ".join(
        chunk.decode("utf-8", "ignore") for chunk in chunks
    )


async def _collect_file_context(bot, items: List[Dict]) -> str:
    parts = []
    for item in items:
        if item["kind"] != "file":
            continue
        filename = item.get("filename", "ملف")
        try:
            telegram_file = await bot.get_file(item["file_id"])
            raw = bytes(await telegram_file.download_as_bytearray())
            if filename.lower().endswith(".docx"):
                extracted = _docx_text(raw)
            elif filename.lower().endswith(".pdf"):
                extracted = _pdf_text(raw)
            else:
                extracted = ""
            if extracted.strip():
                parts.append(f"من {filename}:\n{extracted[:5000]}")
            else:
                parts.append(f"تم إرفاق {filename} (راجعه ضمن الملفات المرفقة).")
        except Exception:
            parts.append(f"تم إرفاق {filename}.")
    return "\n\n".join(parts)


async def show_cv_design_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض خيارات تصاميم PDF الثلاثة للمستخدم."""
    target = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
    selected_design = context.user_data.get("cv_design_id", 1)
    msg = (
        "🎨 *اختر تصميم السيرة الذاتية (PDF):*\n\n"
        "1️⃣ *كلاسيكي عصري (Modern Classic)*\n"
        "   - هيدر كحلي مميز، خطوط واضحة، مناسب لجميع التخصصات.\n\n"
        "2️⃣ *إبداعي بعمودين (Creative Two-Column)*\n"
        "   - جانب كحلي للمعلومات والمهارات + قسم عريض للخبرات.\n\n"
        "3️⃣ *تنفيذي أنيق (Executive Elegant)*\n"
        "   - شريط علوي تنفيذي بالرمادي الداكن والعناوين الذهبية."
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cv_design_selection_keyboard(selected_design)
        )
    else:
        await target.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cv_design_selection_keyboard(selected_design)
        )


async def set_cv_design(update: Update, context: ContextTypes.DEFAULT_TYPE, design_id: int):
    """تحديد التصميم المختار وإنشاء السيرة الذاتية مباشرة."""
    context.user_data["cv_design_id"] = design_id
    if update.callback_query:
        await update.callback_query.answer(f"جاري إنشاء التصميم {design_id}...")
    await finish_ai_cv(update, context)


async def finish_ai_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
    cv_data = context.user_data.get("cv_data", {})
    if not cv_data.get("name"):
        await start_ai_cv_builder(update, context)
        return

    design_id = context.user_data.get("cv_design_id", 1)
    context.user_data["state"] = States.MAIN_MENU
    await target.reply_text("⏳ جاري ترتيب معلوماتك وتصميم السيرة الذاتية PDF باللغتين العربية والإنجليزية...")

    # بناء نص المصدر من الإجابات المعطاة
    parts = []
    if cv_data.get("name"):
        parts.append(f"الاسم: {cv_data['name']}")
    if cv_data.get("phone"):
        parts.append(f"الجوال: {cv_data['phone']}")
    if cv_data.get("email"):
        parts.append(f"البريد الإلكتروني: {cv_data['email']}")
    if cv_data.get("education"):
        parts.append(f"التعليم: {cv_data['education']}")
    if cv_data.get("skills"):
        parts.append(f"المهارات: {cv_data['skills']}")
    if cv_data.get("experience"):
        parts.append(f"الخبرات: {cv_data['experience']}")
    if cv_data.get("languages"):
        parts.append(f"اللغات: {cv_data['languages']}")

    source = "\n".join(parts)
    user = get_user(update.effective_user.id) or {}
    if cv_data.get("name"):
        user["full_name_ar"] = cv_data["name"]
    if cv_data.get("phone"):
        user["phone"] = cv_data["phone"]
    if cv_data.get("email"):
        user["email"] = cv_data["email"]

    # 1. النسخة العربية
    cv_text_ar = ai_generate_professional_cv(user, source)
    pdf_bytes_ar = generate_pdf_cv(user, cv_text_ar, design_id=design_id, lang="ar")

    # 2. النسخة الإنجليزية
    cv_text_en = ai_generate_english_cv(user, source)
    pdf_bytes_en = generate_pdf_cv(user, cv_text_en, design_id=design_id, lang="en")

    design_names = {1: "الكلاسيكي العصري", 2: "الإبداعي بعمودين", 3: "التنفيذي الأنيق"}
    selected_name = design_names.get(design_id, "الاحترافي")

    update_user_field(update.effective_user.id, "ai_cv_text", cv_text_ar)
    update_user_field(update.effective_user.id, "ai_cv_filename", f"saudi-cv-design{design_id}-ar.pdf")

    # إرسال النسخة العربية
    stream_ar = io.BytesIO(pdf_bytes_ar)
    stream_ar.name = f"CV_Arabic_Design_{design_id}.pdf"
    sent_doc_ar = await target.reply_document(
        document=stream_ar,
        caption=f"📄 *سيرتك الذاتية (النسخة العربية)*\nالتصميم: *{selected_name}* 🚀",
        parse_mode=ParseMode.MARKDOWN
    )

    # إرسال النسخة الإنجليزية
    stream_en = io.BytesIO(pdf_bytes_en)
    stream_en.name = f"CV_English_Design_{design_id}.pdf"
    await target.reply_document(
        document=stream_en,
        caption=f"📄 *English Resume (النسخة الإنجليزية)*\nDesign: *{selected_name}* 🚀",
        parse_mode=ParseMode.MARKDOWN
    )

    if sent_doc_ar and sent_doc_ar.document:
        update_user_field(
            update.effective_user.id,
            "cv_file_id",
            sent_doc_ar.document.file_id,
        )
        update_user_field(
            update.effective_user.id,
            "cv_filename",
            f"CV_Arabic_Design_{design_id}.pdf",
        )


async def cancel_ai_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = States.MAIN_MENU
    context.user_data.pop("cv_data", None)
    context.user_data.pop("ai_cv_items", None)
    target = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
    await target.reply_text(
        "↩️ تم إلغاء إنشاء السيرة.",
        reply_markup=get_ai_job_more_keyboard(False),
    )


async def start_ai_job_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = States.AI_JOB_SEARCH
    context.user_data.pop("ai_job_query", None)
    message = (
        "🤖 *بحث عن وظيفة ب AI*\n\n"
        "أرسل أهم ما تبحث عنه في رسالة واحدة، مثل:\n"
        "«مطور Python، الرياض أو عن بعد، خبرة 3 سنوات، دوام كامل»\n\n"
        "سأستخدم بيانات ملفك الشخصي مع هذه التفاصيل للعثور على الأنسب لك."
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            message, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_ai_job_search_keyboard(),
        )
    else:
        await update.message.reply_text(
            message, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_ai_job_search_keyboard(),
        )


def _rank_jobs(user: Dict, query: str) -> List[Dict]:
    words = {word.lower() for word in re.findall(r"[\w\u0600-\u06ff]+", query) if len(word) > 2}
    jobs = get_jobs_page(1000, 0)
    ranked = []
    for job in jobs:
        haystack = " ".join(str(job.get(key) or "") for key in (
            "title", "company", "region", "category", "specialization",
            "description", "requirements", "work_type",
        )).lower()
        keyword_hits = sum(1 for word in words if word in haystack)
        score, reasons = score_match(user, job)
        if keyword_hits or score >= 55:
            job["match_score"] = min(99, score + min(30, keyword_hits * 8))
            job["match_reasons"] = reasons
            ranked.append(job)
    return sorted(ranked, key=lambda job: job.get("match_score", 0), reverse=True)


async def collect_ai_job_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if context.user_data.get("state") != States.AI_JOB_SEARCH:
        return False
    text = (update.message.text or "").strip()
    if _is_cancel(text):
        context.user_data["state"] = States.MAIN_MENU
        await update.message.reply_text("↩️ تم إلغاء البحث.")
        return True
    context.user_data["ai_job_query"] = text
    context.user_data["ai_job_offset"] = 0
    context.user_data["state"] = States.MAIN_MENU
    await send_ai_job_results(update, context, 0)
    return True


async def send_ai_job_results(
    update: Update, context: ContextTypes.DEFAULT_TYPE, offset: int
):
    query = context.user_data.get("ai_job_query", "")
    user = get_user(update.effective_user.id) or {}
    jobs = _rank_jobs(user, query)
    page = jobs[offset:offset + 5]
    context.user_data["ai_job_offset"] = offset
    if not page:
        text = "📭 لم أجد وظائف إضافية بهذه المواصفات. جرّب كلمات بحث أوسع."
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=get_ai_job_more_keyboard(False)
            )
        else:
            await update.message.reply_text(text, reply_markup=get_ai_job_more_keyboard(False))
        return
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            f"🤖 *نتائج البحث الذكي* ({offset + 1}-{offset + len(page)} من {len(jobs)})",
            parse_mode=ParseMode.MARKDOWN,
        )
        chat_id = update.effective_chat.id
    else:
        await update.message.reply_text(
            f"🤖 *نتائج البحث الذكي* ({offset + 1}-{offset + len(page)} من {len(jobs)})",
            parse_mode=ParseMode.MARKDOWN,
        )
        chat_id = update.effective_chat.id
    from keyboards.keyboards import get_job_card_keyboard
    from utils.notifier import build_job_card_text
    for job in page:
        await context.bot.send_message(
            chat_id=chat_id,
            text=build_job_card_text(job),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_job_card_keyboard(
                job["id"], job.get("apply_link"), job.get("apply_email")
            ),
        )
    await context.bot.send_message(
        chat_id=chat_id,
        text="اختر وظيفة للتفاصيل أو اطلب المزيد من النتائج:",
        reply_markup=get_ai_job_more_keyboard(offset + 5 < len(jobs)),
    )