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
from utils.ai_helper import ai_generate_professional_cv
from utils.pdf_generator import generate_pdf_cv
from utils.matching import score_match


def _is_cancel(text: str) -> bool:
    return (text or "").strip().lower() in {
        "الغاء", "إلغاء", "الغاء العملية", "إلغاء العملية", "/cancel"
    }


async def start_ai_cv_builder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء جلسة جمع مواد السيرة الذاتية."""
    context.user_data["state"] = States.AI_CV_COLLECT
    context.user_data["ai_cv_items"] = []
    context.user_data["cv_design_id"] = 1
    context.user_data["cv_design_selected"] = False
    message = (
        "🤖 *إنشاء السيرة الذاتية الاحترافية PDF*\n\n"
        "📋 *طريقة العمل:*\n"
        "1️⃣ أرسل سيرتك الذاتية القديمة إن وجدت (PDF أو Word).\n"
        "2️⃣ أو اكتب بياناتك وخبراتك ومؤهلاتك في رسائل نصية.\n"
        "3️⃣ اضغط *انتهيت* لاختيار تصميم PDF المناسب وإنشاء السيرة.\n\n"
        "💡 _ملاحظة: البوت يعتمد التنسيق المهني الأكاديمي والعملي، ولا يستلزم رفع صورة شخصية._\n\n"
        "أرسل معلوماتك وسيرتك هنا، وعند الانتهاء اضغط «انتهيت — اختر التصميم» 👇"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            message, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_ai_cv_collect_keyboard(),
        )
    else:
        await update.message.reply_text(
            message, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_ai_cv_collect_keyboard(),
        )


async def collect_ai_cv_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """حفظ نص من المستخدم ضمن مواد السيرة."""
    if context.user_data.get("state") != States.AI_CV_COLLECT:
        return False
    text = (update.message.text or "").strip()
    if _is_cancel(text):
        await cancel_ai_cv(update, context)
        return True
    if text in {"انتهيت", "انتهيت.", "تم", "جاهز", "خلصت"}:
        await finish_ai_cv(update, context)
        return True
    if text:
        context.user_data.setdefault("ai_cv_items", []).append({
            "kind": "text",
            "value": text,
        })
        await update.message.reply_text(
            "✅ تم حفظ هذه المعلومة. أرسل المزيد أو اضغط «انتهيت».",
            reply_markup=get_ai_cv_collect_keyboard(),
        )
    return True


async def collect_ai_cv_file(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """حفظ ملف PDF/Word أو صورة ضمن جلسة بناء السيرة."""
    if context.user_data.get("state") != States.AI_CV_COLLECT:
        return False
    document = update.message.document
    photo = update.message.photo
    if document:
        filename = document.file_name or "cv-file"
        mime = (document.mime_type or "").lower()
        extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if extension not in {"pdf", "doc", "docx"} and mime not in {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }:
            await update.message.reply_text("⚠️ أرسل PDF أو Word فقط في هذه الخطوة.")
            return True
        file_id = document.file_id
    elif photo:
        filename = "cv-image.jpg"
        file_id = photo[-1].file_id
    else:
        return False

    context.user_data.setdefault("ai_cv_items", []).append({
        "kind": "file",
        "file_id": file_id,
        "filename": filename,
    })
    await update.message.reply_text(
        f"✅ تم استقبال {filename}. أرسل المزيد أو اضغط «انتهيت».",
        reply_markup=get_ai_cv_collect_keyboard(),
    )
    return True


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
        try:
            await update.callback_query.edit_message_text(
                msg, parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_cv_design_selection_keyboard(selected_design)
            )
        except Exception:
            await target.reply_text(
                msg, parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_cv_design_selection_keyboard(selected_design)
            )
    else:
        await target.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cv_design_selection_keyboard(selected_design)
        )


async def set_cv_design(update: Update, context: ContextTypes.DEFAULT_TYPE, design_id: int):
    """تحديد التصميم المختار."""
    context.user_data["cv_design_id"] = design_id
    if update.callback_query:
        await update.callback_query.answer(f"تم اختيار التصميم {design_id}")
    await show_cv_design_options(update, context)


async def finish_ai_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
    items = context.user_data.get("ai_cv_items", [])
    if not items:
        await target.reply_text(
            "📎 أرسل ملف السيرة القديمة أو اكتب معلوماتك أولاً، ثم اضغط «انتهيت».",
            reply_markup=get_ai_cv_collect_keyboard(),
        )
        return

    # الخطوة الأخيرة: عرض خيارات التصميم قبل التوليد إن لم تكن عُرِضت
    if not context.user_data.get("cv_design_selected"):
        context.user_data["cv_design_selected"] = True
        await show_cv_design_options(update, context)
        return

    design_id = context.user_data.get("cv_design_id", 1)
    context.user_data["state"] = States.MAIN_MENU
    await target.reply_text("⏳ جاري ترتيب معلوماتك وتصميم السيرة الذاتية PDF احترافياً...")

    text_parts = [item["value"] for item in items if item["kind"] == "text"]
    file_text = await _collect_file_context(context.bot, items)
    source = "\n\n".join(text_parts + ([file_text] if file_text else []))
    user = get_user(update.effective_user.id) or {}

    cv_text = ai_generate_professional_cv(user, source)
    pdf_bytes = generate_pdf_cv(user, cv_text, design_id=design_id)

    design_names = {1: "الكلاسيكي العصري", 2: "الإبداعي بعمودين", 3: "التنفيذي الأنيق"}
    selected_name = design_names.get(design_id, "الاحترافي")

    update_user_field(update.effective_user.id, "ai_cv_text", cv_text)
    update_user_field(update.effective_user.id, "ai_cv_filename", f"saudi-cv-design{design_id}.pdf")

    pdf_stream = io.BytesIO(pdf_bytes)
    pdf_stream.name = f"CV_Professional_Design_{design_id}.pdf"

    sent_document = await target.reply_document(
        document=pdf_stream,
        caption=f"📄 *تم إنشاء سيرتك الذاتية PDF بنجاح!*\nالتصميم: *{selected_name}* 🚀",
        parse_mode=ParseMode.MARKDOWN
    )

    if sent_document and sent_document.document:
        update_user_field(
            update.effective_user.id,
            "cv_file_id",
            sent_document.document.file_id,
        )
        update_user_field(
            update.effective_user.id,
            "cv_filename",
            f"CV_Professional_Design_{design_id}.pdf",
        )


async def cancel_ai_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = States.MAIN_MENU
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