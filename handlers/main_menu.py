"""تدفقات الشريط السفلي والقوائم التجارية الجديدة."""

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config.settings import States
from database.db import create_purchase_order, get_user
from keyboards.keyboards import (
    get_main_reply_keyboard, get_subscription_menu_keyboard,
    get_jobs_menu_keyboard, get_applications_menu_keyboard,
    get_settings_keyboard, get_preferences_keyboard,
    get_back_to_menu_keyboard, get_payment_keyboard
)


async def send_main_menu(bot, chat_id: int, name: str = "صديقي"):
    await bot.send_message(
        chat_id=chat_id,
        text=f"مرحباً *{name}* 👋\nاختر الخدمة من القائمة السفلية:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_reply_keyboard(),
    )


async def handle_main_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """يعالج أزرار Reply Keyboard ويرشد المستخدم الجديد إلى التسجيل."""
    text = (update.message.text or "").strip()
    user = get_user(update.effective_user.id) or {}

    if text in ("⬅️ رجوع", "رجوع"):
        context.user_data["state"] = States.MAIN_MENU
        context.user_data.pop("ai_cv_items", None)
        context.user_data.pop("ai_job_query", None)
        await send_main_menu(context.bot, update.effective_chat.id,
                             user.get("full_name_ar") or "صديقي")
    elif text in ("اشتراكي", "💳 اشتراكي"):
        await update.message.reply_text(
            "💳 *اشتراكي*\n\nاختر الخدمة التي تريدها:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_subscription_menu_keyboard(),
        )
    elif text in ("آخر الوظائف", "🔍 آخر الوظائف"):
        await update.message.reply_text(
            "🔍 *آخر الوظائف*\n\nاختر نوع العرض:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_jobs_menu_keyboard(),
        )
    elif text in ("تقديماتي", "📋 تقديماتي"):
        await update.message.reply_text(
            "📋 *تقديماتي*\n\nاختر نوع التقديمات:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_applications_menu_keyboard(),
        )
    elif text in ("إعداداتي", "⚙️ إعداداتي"):
        from handlers.callbacks import show_settings_menu
        await show_settings_menu(update, context, message=update.message)
    elif text in ("تفضيلاتي", "🎯 تفضيلاتي"):
        await update.message.reply_text(
            "🎯 *تفضيلاتي*\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_preferences_keyboard(user),
        )
    elif text in ("الدعم", "💬 الدعم"):
        await update.message.reply_text(
            "💬 *الدعم*\n\n"
            "إذا واجهت مشكلة أو تحتاج مساعدة، أرسل رسالتك هنا وسيتم الرد عليك قريباً.\n\n"
            "يمكنك أيضاً استخدام /help لعرض التعليمات.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard(),
        )
    elif text in ("إلغاء الاشتراك", "🚫 إلغاء الاشتراك"):
        from keyboards.keyboards import get_unsubscribe_keyboard
        await update.message.reply_text(
            "🚫 *إلغاء الاشتراك*\n\nهل تريد إيقاف التقديم التلقائي والتنبيهات؟",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_unsubscribe_keyboard(),
        )
    elif text in ("صمم سيرتي", "📄 صمم سيرتي"):
        from handlers.ai_features import start_ai_cv_builder
        await start_ai_cv_builder(update, context)
    elif text in ("بحث عن وظيفة ب AI", "🔍 بحث عن وظيفة ب AI"):
        from handlers.ai_features import start_ai_job_search
        await start_ai_job_search(update, context)
    elif text in ("تجارب العملاء", "⭐ تجارب العملاء"):
        await update.message.reply_text(
            "⭐ *تجارب العملاء*\n\n"
            "نساعد الباحثين عن عمل في الوصول إلى فرص أكثر، تنظيم التقديمات، "
            "وتحسين ظهور سيرهم لدى الشركات.\n\n"
            "كن أول من يشارك تجربته بعد استخدام الخدمة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard(),
        )
    else:
        return False
    return True


async def handle_custom_amount_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    state = context.user_data.get("state")
    if state not in (States.TOPUP_CUSTOM_AMOUNT, States.BLAST_CUSTOM_COUNT):
        return False
    try:
        value = int((update.message.text or "").replace(",", "").strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ أدخل رقماً صحيحاً أكبر من صفر:")
        return True

    telegram_id = update.effective_user.id
    if state == States.TOPUP_CUSTOM_AMOUNT:
        points = value * 5
        order_id = create_purchase_order(telegram_id, "points_custom", value, points)
        context.user_data["state"] = States.MAIN_MENU
        await update.message.reply_text(
            f"✅ *تم إنشاء طلب شراء {points} نقطة*\n\n"
            f"المبلغ: {value} ر.س\nالنقاط: {points}\n\n"
            "اضغط ادفع الحين لإتمام العملية.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_payment_keyboard(order_id),
        )
    else:
        context.user_data["blast_custom_count"] = value
        context.user_data["state"] = States.MAIN_MENU
        await update.message.reply_text(
            f"📨 العدد المخصص: *{value} شركة*\n\n"
            "سيتم حساب النقاط المطلوبة بعد التأكد من المجالات المختارة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard(),
        )
    return True