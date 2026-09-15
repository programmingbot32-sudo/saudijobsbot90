"""
🤖 بوت التوظيف السعودي - نقطة البداية الرئيسية
Saudi Jobs Telegram Bot - Main Entry Point

التشغيل:
    pip install python-telegram-bot==21.3
    python main.py
"""

import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, PicklePersistence, filters, ContextTypes
)

from config.settings import (
    BOT_TOKEN, CHANNEL_ID, ADMIN_ID, WEBHOOK_URL, WEBHOOK_SECRET, PORT, LOG_LEVEL
)
from database.db import init_db
from handlers.registration import (
    cmd_start, handle_text_input, handle_cv_upload
)
from handlers.callbacks import handle_callback
from handlers.edit_profile import handle_edit_text_input
from utils.email_sender import handle_email_setup_text
from utils.notifier import process_channel_message
from app import server
from utils.errors import error_handler
from utils.security import escape_md
from handlers.main_menu import handle_main_menu_text, handle_custom_amount_text
from database.db import get_user, update_user_field

async def handle_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    موزّع الرسائل النصية:
    يوجّه للمعالج الصح حسب الحالة الحالية
    """
    from config.settings import States

    state = context.user_data.get("state", "")

    # إلغاء عربي واضح يعمل في أي خطوة، بما فيها خدمات AI.
    if (update.message.text or "").strip() in ("الغاء", "إلغاء", "إلغاء العملية"):
        await cmd_cancel(update, context)
        return

    if state == States.ADMIN_EDIT_PLAN:
        from handlers.callbacks import handle_admin_plan_text
        if await handle_admin_plan_text(update, context):
            return

    if state in (
        States.AI_CV_COLLECT, States.AI_CV_NAME, States.AI_CV_PHONE,
        States.AI_CV_EMAIL, States.AI_CV_EDUCATION, States.AI_CV_SKILLS,
        States.AI_CV_EXPERIENCE, States.AI_CV_LANGUAGES, States.AI_CV_SUMMARY
    ):
        from handlers.ai_features import collect_ai_cv_text
        if await collect_ai_cv_text(update, context):
            return
    if state == States.AI_JOB_SEARCH:
        from handlers.ai_features import collect_ai_job_query
        if await collect_ai_job_query(update, context):
            return

    # 0) القوائم الرئيسية والشاشات التجارية
    handled = await handle_custom_amount_text(update, context)
    if handled:
        return
    if state == States.MESSAGE_CONTENT:
        update_user_field(update.effective_user.id, "message_content", update.message.text.strip())
        context.user_data["state"] = States.MAIN_MENU
        await update.message.reply_text("✅ تم حفظ محتوى الرسالة.", reply_markup=None)
        return
    handled = await handle_main_menu_text(update, context)
    if handled:
        return

    # 1) وضع إعداد إيميل التقديم التلقائي
    if state in (States.EMAIL_SETUP_ADDRESS, States.EMAIL_SETUP_PASSWORD):
        handled = await handle_email_setup_text(update, context)
        if handled:
            return

    # 2) وضع تعديل الملف الشخصي (نصوص: اسم، إيميل، LinkedIn)
    handled = await handle_edit_text_input(update, context)
    if handled:
        return

    # 3) خطوات التسجيل الأولي
    await handle_text_input(update, context)


# ─────────────────────────────────────────
# إعداد السجل (Logging)
# ─────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
# لا تسجل مكتبات HTTP عناوين Telegram لأنها تتضمن التوكن داخل الرابط.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# معالج رسائل القناة
# ─────────────────────────────────────────
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة منشورات القناة وتحويلها لوظائف"""
    message = update.channel_post
    if not message or not message.text:
        return

    channel = message.chat.username or str(message.chat.id)
    logger.info(f"📥 منشور جديد من القناة @{channel}")

    await process_channel_message(
        context.bot,
        message.text,
        message.message_id,
        channel
    )


# ─────────────────────────────────────────
# معالج الأوامر الإضافية
# ─────────────────────────────────────────
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help"""
    await update.message.reply_text(
        "📖 *الأوامر المتاحة:*\n\n"
        "/start - بدء البوت أو القائمة الرئيسية\n"
        "/profile - عرض ملفك الشخصي\n"
        "/jobs - آخر الوظائف\n"
        "/settings - الإعدادات\n"
        "/cancel - إلغاء العملية الحالية\n"
        "/help - المساعدة",
        parse_mode="Markdown"
    )


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /profile"""
    from database.db import get_user
    from keyboards.keyboards import get_edit_profile_keyboard
    user = get_user(update.effective_user.id)
    if user and user.get("registration_complete"):
        await update.message.reply_text(
            f"👤 مرحباً *{escape_md(user.get('full_name_ar', ''))}*\n\nاضغط لعرض ملفك:",
            parse_mode="Markdown",
            reply_markup=get_edit_profile_keyboard()
        )
    else:
        await update.message.reply_text(
            "لم تُكمل التسجيل بعد.\nاضغط /start للبدء"
        )


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /jobs"""
    from database.db import get_recent_jobs
    from keyboards.keyboards import get_job_card_keyboard
    from telegram.constants import ParseMode
    from utils.notifier import build_job_card_text

    jobs = get_recent_jobs(5)
    if not jobs:
        await update.message.reply_text("📭 لا توجد وظائف حالياً. سنُشعرك فور نزول وظائف جديدة!")
        return

    await update.message.reply_text(f"💼 *آخر {len(jobs)} وظائف:*", parse_mode=ParseMode.MARKDOWN)
    for job in jobs:
        await update.message.reply_text(
            build_job_card_text(job),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_job_card_keyboard(job["id"], job.get("apply_link"), job.get("apply_email"))
        )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم المشرف - /admin"""
    user_id = update.effective_user.id
    if not ADMIN_ID or user_id != ADMIN_ID:
        # بدون ADMIN_ID محدد تبقى اللوحة مغلقة على الجميع (لا صلاحيات افتراضية).
        await update.message.reply_text("⛔ هذا الأمر للمشرف فقط.")
        return
    from handlers.callbacks import show_admin_dashboard
    await show_admin_dashboard(update, context, message=update.message)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /cancel - الخروج من أي خطوة عالقة والعودة للقائمة."""
    from config.settings import States
    from keyboards.keyboards import get_main_reply_keyboard

    context.user_data.pop("state", None)
    context.user_data.pop("editing_field", None)
    context.user_data.pop("ai_cv_items", None)
    context.user_data.pop("ai_job_query", None)
    context.user_data["state"] = States.MAIN_MENU
    await update.message.reply_text(
        "✅ تم إلغاء العملية الحالية.\nاستخدم القائمة بالأسفل أو /start.",
        reply_markup=get_main_reply_keyboard()
    )


async def post_init(app: Application):
    """تسجيل قائمة الأوامر داخل تليجرام + إشعار المشرف بالتشغيل."""
    from telegram import BotCommand, BotCommandScopeDefault

    await app.bot.set_my_commands(
        [
            BotCommand("start", "بدء البوت والقائمة الرئيسية"),
            BotCommand("jobs", "آخر الوظائف المتاحة"),
            BotCommand("profile", "ملفي الشخصي"),
            BotCommand("cancel", "إلغاء العملية الحالية"),
            BotCommand("help", "المساعدة"),
        ],
        scope=BotCommandScopeDefault(),
    )
    me = await app.bot.get_me()
    logger.info("✅ تم تسجيل أوامر البوت @%s", me.username)

    if ADMIN_ID:
        try:
            mode = "Webhook" if WEBHOOK_URL else "Polling"
            await app.bot.send_message(ADMIN_ID, f"✅ البوت يعمل الآن ({mode}).")
        except Exception:
            logger.debug("تعذّر إشعار المشرف بالتشغيل", exc_info=True)


# ─────────────────────────────────────────
# نقطة البداية
# ─────────────────────────────────────────
def main():
    """تشغيل البوت"""

    if not BOT_TOKEN:
        logger.error("❌ لم يُحدد BOT_TOKEN! أضف المتغير في الإعدادات.")
        print("❌ خطأ: BOT_TOKEN غير موجود. أضفه كمتغير بيئة.")
        return

    # تهيئة قاعدة البيانات
    init_db()
    logger.info("✅ تم تهيئة قاعدة البيانات")

    # إنشاء التطبيق: حالات المحادثة تُحفظ على القرص كي لا تضيع عند إعادة التشغيل
    persistence = PicklePersistence(filepath="bot_state.pickle")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )

    # ─── أوامر ───
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    # ─── أزرار Inline ───
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ─── رسائل نصية (تسجيل + تعديل + إعداد إيميل) ───
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.ChatType.CHANNEL,
        handle_all_text
    ))

    # ─── رفع الملفات (CV) ───
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO,
        handle_cv_upload
    ))

    # ─── منشورات القناة ───
    app.add_handler(MessageHandler(
        filters.ChatType.CHANNEL,
        handle_channel_post
    ))

    # ─── معالج الأخطاء العام ───
    app.add_error_handler(error_handler)

    logger.info("🚀 البوت يعمل الآن...")
    print("=" * 50)
    print("🤖 بوت التوظيف السعودي")
    print("✅ جاهز للعمل!")
    print("=" * 50)

    if WEBHOOK_URL:
        # تشغيل عبر Webhook: أنسب للاستضافة الدائمة ولا يحتاج استعلاماً مستمراً.
        logger.info("🌐 وضع Webhook على %s", WEBHOOK_URL)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="telegram-webhook",
            webhook_url=f"{WEBHOOK_URL}/telegram-webhook",
            secret_token=WEBHOOK_SECRET or None,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
        )
    else:
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
        )


if __name__ == "__main__":
    # خدمة الفحص الصحي تعمل فقط في وضع Polling (وضع Webhook يستخدم نفس المنفذ).
    if not WEBHOOK_URL:
        server()
    main()
