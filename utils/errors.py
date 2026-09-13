"""
معالج الأخطاء العام: لا يترك المستخدم أمام شاشة صامتة، ويبلّغ المشرف.
"""

import html
import logging
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut
from telegram.ext import ContextTypes

from config.settings import ADMIN_ID

logger = logging.getLogger(__name__)

USER_MESSAGE = (
    "⚠️ حدث خطأ غير متوقع.\n"
    "تم تسجيل المشكلة وسيتم إصلاحها. اضغط /start للعودة للقائمة الرئيسية."
)

# أخطاء متوقعة لا تستحق إزعاج المستخدم أو المشرف
_QUIET = (
    "message is not modified",
    "query is too old",
    "message to edit not found",
    "message can't be deleted",
)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    text = str(error).lower()

    if isinstance(error, BadRequest) and any(part in text for part in _QUIET):
        logger.info("تم تجاهل خطأ متوقع: %s", error)
        return

    if isinstance(error, (TimedOut, NetworkError, RetryAfter)):
        logger.warning("مشكلة شبكة مؤقتة: %s", error)
        return

    if isinstance(error, Forbidden):
        logger.info("المستخدم حظر البوت: %s", error)
        return

    logger.error("خطأ أثناء معالجة التحديث", exc_info=error)

    # 1) رسالة مهذبة للمستخدم
    if isinstance(update, Update):
        try:
            if update.callback_query:
                await update.callback_query.answer("⚠️ حدث خطأ، حاول مرة أخرى", show_alert=False)
                await update.effective_chat.send_message(USER_MESSAGE)
            elif update.effective_chat:
                await update.effective_chat.send_message(USER_MESSAGE)
        except Exception:
            logger.debug("تعذّر إبلاغ المستخدم بالخطأ", exc_info=True)

    # 2) تقرير مختصر للمشرف
    if not ADMIN_ID:
        return
    try:
        trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        user = getattr(getattr(update, "effective_user", None), "id", "غير معروف")
        report = (
            "🚨 <b>خطأ في البوت</b>\n"
            f"👤 المستخدم: <code>{user}</code>\n"
            f"❌ <code>{html.escape(str(error))[:300]}</code>\n"
            f"<pre>{html.escape(trace[-1200:])}</pre>"
        )
        await context.bot.send_message(ADMIN_ID, report, parse_mode=ParseMode.HTML)
    except Exception:
        logger.debug("تعذّر إبلاغ المشرف بالخطأ", exc_info=True)
