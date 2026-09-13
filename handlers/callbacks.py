"""
معالج الأزرار - Callback Query Handler
يعالج جميع ضغطات الأزرار inline في البوت
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config.settings import ADMIN_ID

from config.settings import States
from keyboards.keyboards import (
    get_main_menu_keyboard, get_back_to_menu_keyboard,
    get_notification_settings_keyboard, get_edit_profile_keyboard,
    get_subscription_keyboard, get_plan_action_keyboard,
    get_account_keyboard, get_subscription_menu_keyboard,
    get_topup_keyboard, get_payment_keyboard, get_jobs_menu_keyboard,
    get_job_list_keyboard, get_job_detail_keyboard,
    get_applications_menu_keyboard, get_settings_keyboard,
    get_preferences_keyboard, get_blast_categories_keyboard,
    get_blast_packages_keyboard, get_hidden_jobs_keyboard,
    get_admin_dashboard_keyboard, get_admin_plans_keyboard,
    get_admin_plan_keyboard, get_admin_requests_keyboard
)
from database.db import (
    get_user, update_user_field, save_application,
    get_user_stats, get_recent_jobs, get_job, get_jobs_page,
    get_matching_jobs_page, count_jobs, create_purchase_order,
    create_cv_campaign, consume_subscription_usage, get_user_campaigns,
    get_hidden_jobs, hide_job, unhide_job, get_jobs_by_ids, save_job_for_user,
    update_plan, get_subscription_requests, approve_subscription_request
)
from handlers.registration import (
    start_registration, ask_region, ask_category, ask_specialization,
    ask_education, ask_experience, ask_work_type, ask_salary,
    ask_email, ask_phone, ask_cv, ask_linkedin,
    show_profile_summary, confirm_and_save_profile
)
from handlers.edit_profile import (
    edit_name, edit_region, edit_specialization, edit_education,
    edit_experience, edit_work_type, edit_salary,
    edit_email_field, edit_cv_field, edit_linkedin_field, edit_phone_field,
    handle_edit_callback
)
from utils.email_sender import (
    start_email_setup, execute_auto_apply,
    get_email_credentials, delete_email_credentials,
    _email_actions_keyboard
)
from database.db import get_plans, get_plan
from services.subscriptions import (
    account_text, history_text, plan_features, request_plan
)
from services.catalog import category_name
from utils.security import escape_md
from handlers.ai_features import (
    start_ai_cv_builder, finish_ai_cv, cancel_ai_cv,
    start_ai_job_search, send_ai_job_results,
)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموزّع الرئيسي لجميع callback queries"""
    query = update.callback_query
    data = query.data
    telegram_id = update.effective_user.id

    # ─── تمرير للمعالج الخاص بوضع التعديل أولاً ───
    editing_field = context.user_data.get("editing_field")
    if editing_field or data == "cancel_edit":
        handled = await handle_edit_callback(update, context)
        if handled:
            return

    # ─── زر الرجوع العام ───
    if data == "back":
        await query.answer()
        user = get_user(telegram_id)
        if user and user.get("registration_complete"):
            name = escape_md(user.get("full_name_ar") or "صديقي")
            await query.edit_message_text(
                f"مرحباً *{name}* 👋\nماذا تريد أن تفعل؟",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            from keyboards.keyboards import get_start_keyboard
            from config.settings import WELCOME_MESSAGE
            await query.edit_message_text(
                WELCOME_MESSAGE,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_start_keyboard()
            )
        return

    # ─── لوحة المشرف وإدارة الباقات ───
    elif data.startswith("admin_"):
        if not ADMIN_ID or telegram_id != ADMIN_ID:
            await query.answer("⛔ هذا القسم للمشرف فقط", show_alert=True)
            return
        if data == "admin_dashboard":
            await show_admin_dashboard(update, context)
        elif data == "admin_plans":
            await query.answer()
            await query.edit_message_text(
                "💎 *إدارة الباقات*\n\nاختر الباقة التي تريد تعديلها:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_admin_plans_keyboard(get_plans()),
            )
        elif data == "admin_requests":
            requests = get_subscription_requests()
            await query.answer()
            lines = ["🧾 *طلبات الاشتراك المعلقة*", "━━━━━━━━━━━━━━━━"]
            if requests:
                lines.extend(
                    f"• #{item['id']} — {item['plan_name']} — "
                    f"{item['price']:.0f} ريال — المستخدم `{item['telegram_id']}`"
                    for item in requests
                )
            else:
                lines.append("لا توجد طلبات معلقة حالياً.")
            await query.edit_message_text(
                "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_admin_requests_keyboard(requests),
            )
        elif data.startswith("admin_approve_request_"):
            request_id = int(data.rsplit("_", 1)[1])
            approved = approve_subscription_request(request_id)
            await query.answer(
                "تم اعتماد الاشتراك" if approved else "الطلب غير موجود أو تمت معالجته",
                show_alert=not bool(approved),
            )
            if approved:
                await context.bot.send_message(
                    approved["telegram_id"],
                    f"✅ تم تفعيل *{approved['plan_name']}* في حسابك.\n"
                    "يمكنك الآن استخدام الرصيد المتاح.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            requests = get_subscription_requests()
            lines = ["🧾 *طلبات الاشتراك المعلقة*", "━━━━━━━━━━━━━━━━"]
            lines.extend(
                f"• #{item['id']} — {item['plan_name']} — {item['price']:.0f} ريال"
                for item in requests
            )
            if not requests:
                lines.append("لا توجد طلبات معلقة حالياً.")
            await query.edit_message_text(
                "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_admin_requests_keyboard(requests),
            )
        elif data.startswith("admin_edit_"):
            _, _, field, plan_code = data.split("_", 3)
            context.user_data["state"] = States.ADMIN_EDIT_PLAN
            context.user_data["admin_plan_code"] = plan_code
            context.user_data["admin_plan_field"] = field
            labels = {
                "name": "اسم الباقة الجديد",
                "price": "السعر بالريال",
                "points": "عدد النقاط",
                "apps": "كوتة التقديمات اليومية",
                "companies": "كوتة الشركات وإيميلات HR",
                "description": "وصف الباقة",
            }
            await query.answer()
            await query.edit_message_text(
                f"✏️ أرسل {labels.get(field, field)} للباقة *{plan_code}*:\n\n"
                "اكتب /cancel للإلغاء.",
                parse_mode=ParseMode.MARKDOWN,
            )
        elif data.startswith("admin_plan_"):
            plan_code = data[len("admin_plan_"):]
            plan = get_plan(plan_code)
            if not plan:
                await query.answer("الباقة غير موجودة", show_alert=True)
                return
            await query.answer()
            await query.edit_message_text(
                f"💎 *{plan['name']}*\n"
                "━━━━━━━━━━━━━━━━\n"
                f"💰 السعر: *{plan['price']:.0f} ريال*\n"
                f"⭐ النقاط: *{plan['points']}*\n"
                f"🤖 كوتة التقديم: *{plan['applications_limit']}*\n"
                f"🏢 كوتة الشركات: *{plan['companies_limit']}*\n\n"
                f"📝 {plan.get('description') or 'بدون وصف'}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_admin_plan_keyboard(plan_code),
            )
        return

    # ─── التسجيل ───
    elif data == "start_registration":
        await start_registration(update, context)

    elif data == "back_to_categories":
        await ask_category(update, context)

    elif data == "confirm_profile":
        await confirm_and_save_profile(update, context)

    elif data == "edit_profile_before_save":
        context.user_data["state"] = States.MAIN_MENU
        await query.answer()
        await query.edit_message_text(
            "✏️ *تعديل الملف الشخصي*\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )

    # ─── اختيار المنطقة (في التسجيل) ───
    elif data.startswith("region_") and not editing_field:
        region = data[len("region_"):]
        context.user_data.setdefault("temp_profile", {})["region"] = region
        await query.answer(f"✅ {region}")
        await ask_category(update, context)

    # ─── اختيار التخصص الرئيسي (في التسجيل) ───
    elif data.startswith("cat_") and not editing_field:
        category = data[len("cat_"):]
        context.user_data.setdefault("temp_profile", {})["category"] = category
        await query.answer(f"✅ {category}")
        await ask_specialization(update, context, category)

    # ─── اختيار التخصص الفرعي (في التسجيل) ───
    elif data.startswith("spec_") and not editing_field:
        spec = data[len("spec_"):]
        context.user_data.setdefault("temp_profile", {})["specialization"] = spec
        await query.answer(f"✅ {spec}")
        await ask_education(update, context)

    # ─── اختيار المؤهل (في التسجيل) ───
    elif data.startswith("edu_") and not editing_field:
        edu = data[len("edu_"):]
        context.user_data.setdefault("temp_profile", {})["education_level"] = edu
        await query.answer(f"✅ {edu}")
        await ask_experience(update, context)

    # ─── اختيار الخبرة (في التسجيل) ───
    elif data.startswith("exp_") and not editing_field:
        exp = data[len("exp_"):]
        context.user_data.setdefault("temp_profile", {})["experience_level"] = exp
        await query.answer(f"✅ {exp}")
        await ask_work_type(update, context)

    # ─── نوع الدوام (في التسجيل) ───
    elif data.startswith("wtype_") and not editing_field:
        wtype = data[len("wtype_"):]
        context.user_data.setdefault("temp_profile", {})["work_type"] = wtype
        await query.answer(f"✅ {wtype}")
        await ask_salary(update, context)

    # ─── الراتب (في التسجيل) ───
    elif data.startswith("sal_") and not editing_field:
        sal = data[len("sal_"):]
        context.user_data.setdefault("temp_profile", {})["salary_range"] = sal
        await query.answer(f"✅ {sal}")
        await ask_email(update, context)

    # ─── تخطي الخطوات ───
    elif data == "skip_name_en":
        await ask_region(update, context)

    elif data == "skip_email":
        await ask_phone(update, context)

    elif data == "skip_phone":
        await ask_cv(update, context)

    elif data == "skip_cv":
        await ask_linkedin(update, context)

    elif data == "skip_linkedin":
        await show_profile_summary(update, context)

    # ─── رفع السيرة الذاتية ───
    elif data in ("upload_cv_pdf", "upload_cv_image"):
        context.user_data["state"] = States.REG_CV
        await query.edit_message_text(
            "📎 *أرسل ملف السيرة الذاتية الآن* 👇\n\n"
            "_يدعم البوت: PDF أو صورة JPG/PNG_",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "manual_cv":
        await query.answer()
        await query.edit_message_text(
            "✍️ *تعبئة البيانات يدوياً*\n\n"
            "هذه الخاصية قادمة قريباً!\n\n"
            "في الوقت الحالي يمكنك رفع ملف PDF أو تخطي هذه الخطوة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )

    # ─── القائمة الرئيسية ───
    elif data == "ai_cv_builder":
        await start_ai_cv_builder(update, context)

    elif data == "ai_cv_done":
        await finish_ai_cv(update, context)

    elif data == "ai_cv_cancel":
        await cancel_ai_cv(update, context)

    elif data == "ai_job_search":
        await start_ai_job_search(update, context)

    elif data == "ai_jobs_more":
        await send_ai_job_results(
            update, context, int(context.user_data.get("ai_job_offset", 0)) + 5
        )

    elif data == "ai_job_cancel":
        context.user_data["state"] = States.MAIN_MENU
        context.user_data.pop("ai_job_query", None)
        await query.answer()
        await query.edit_message_text(
            "↩️ تم إلغاء البحث عن الوظائف.",
            reply_markup=get_back_to_menu_keyboard(),
        )

    elif data == "main_menu":
        user = get_user(telegram_id)
        name = user.get("full_name_ar", "صديقي") if user else "صديقي"
        await query.edit_message_text(
            f"مرحباً *{name}* 👋\nالقائمة الرئيسية أصبحت في الشريط السفلي.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=None
        )
        await context.bot.send_message(
            telegram_id, "اختر الخدمة من القائمة السفلية:",
            reply_markup=__import__("keyboards.keyboards", fromlist=["get_main_reply_keyboard"]).get_main_reply_keyboard()
        )

    # ─── القوائم الرئيسية الجديدة ───
    elif data == "my_subscription_menu":
        await query.answer()
        await query.edit_message_text(
            account_text(telegram_id), parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_subscription_menu_keyboard()
        )

    elif data == "topup_points":
        await query.answer()
        await query.edit_message_text(
            "⚡ *شحن رصيد التقديم*\n\nاختر الباقة المناسبة لك:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=get_topup_keyboard()
        )

    elif data.startswith("topup_") and data not in ("topup_points",):
        parts = data.split("_")
        if len(parts) == 3:
            points, amount = int(parts[1]), int(parts[2])
            order_id = create_purchase_order(telegram_id, "points", amount, points)
            await query.answer()
            await query.edit_message_text(
                f"🧾 *طلب شراء نقاط #{order_id}*\n\n"
                f"النقاط: {points}\nالمبلغ: {amount} ر.س\n\n"
                "الطلب محفوظ بانتظار الدفع.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_payment_keyboard(order_id)
            )

    elif data == "custom_topup":
        context.user_data["state"] = States.TOPUP_CUSTOM_AMOUNT
        await query.answer()
        await query.edit_message_text(
            "✏️ أرسل المبلغ بالريال لإنشاء طلب شراء مخصص:",
            reply_markup=get_back_to_menu_keyboard()
        )

    elif data.startswith("pay_order_"):
        order_id = int(data.rsplit("_", 1)[1])
        await query.answer("الدفع الإلكتروني غير مربوط حالياً", show_alert=True)
        await query.edit_message_text(
            f"🧾 *طلب الشراء #{order_id}*\n\n"
            "حالة الطلب: ⏳ بانتظار الدفع\n"
            "سيتم تفعيل النقاط تلقائياً بعد ربط مزود الدفع.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_subscription_menu_keyboard()
        )

    elif data == "jobs_menu":
        await query.answer()
        await query.edit_message_text(
            "🔍 *آخر الوظائف*\n\nاختر طريقة عرض الوظائف:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=get_jobs_menu_keyboard()
        )

    elif data.startswith("jobs_mode_"):
        mode = data.rsplit("_", 1)[1]
        await show_jobs_page(update, context, mode, 0)

    elif data.startswith("jobs_page_"):
        _, _, mode, page = data.split("_")
        await show_jobs_page(update, context, mode, int(page))

    elif data.startswith("job_view_"):
        await show_job_detail(update, context, int(data.rsplit("_", 1)[1]))

    elif data.startswith("apply_job_"):
        job_id = int(data.rsplit("_", 1)[1])
        job = get_job(job_id)
        if not job:
            await query.answer("الوظيفة غير موجودة", show_alert=True)
        else:
            ok, message = consume_subscription_usage(
                telegram_id, "application", "job", str(job_id)
            )
            if ok and save_application(telegram_id, job_id, "manual"):
                await query.answer("تم حجز نقطة للتقديم")
                await query.edit_message_text(
                    f"✅ تم تسجيل تقديمك على: {job.get('title', 'الوظيفة')}\n\n"
                    f"📧 {job.get('apply_email') or 'راجع رابط التقديم'}",
                    reply_markup=get_back_to_menu_keyboard()
                )
            else:
                await query.answer(message or "تعذر إتمام التقديم", show_alert=True)

    elif data.startswith("apply_all_"):
        _, _, mode, page = data.split("_")
        user = get_user(telegram_id)
        hidden = get_hidden_jobs(telegram_id)
        jobs = (get_matching_jobs_page(user, 20, int(page) * 20, hidden)
                if mode == "matching" else get_jobs_page(20, int(page) * 20, hidden))
        applied = 0
        for job in jobs:
            ok, _ = consume_subscription_usage(telegram_id, "application", "job", str(job["id"]))
            if not ok:
                break
            if save_application(telegram_id, job["id"], "manual"):
                applied += 1
        await query.answer(f"تم تسجيل {applied} تقديم", show_alert=True)

    elif data == "applications_menu":
        await query.answer()
        await query.edit_message_text(
            "📋 *تقديماتي*\n\nاختر نوع التقديمات:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=get_applications_menu_keyboard()
        )

    elif data in ("applications_daily", "applications_blast"):
        campaigns = get_user_campaigns(telegram_id)
        label = "التقديم التلقائي اليومي" if data == "applications_daily" else "إرسال السيرة للشركات"
        lines = [f"📋 *{label}*", ""]
        lines.extend(
            f"• #{c['id']} — {c['status']} ({c['processed_count']}/{c['target_count']})"
            for c in campaigns
        )
        if not campaigns:
            lines.append("لا توجد عمليات مسجلة بعد.")
        await query.answer()
        await query.edit_message_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_applications_menu_keyboard()
        )

    elif data == "hidden_jobs":
        await query.answer()
        jobs = get_jobs_by_ids(get_hidden_jobs(telegram_id))
        if not jobs:
            await query.edit_message_text(
                "🚫 *الوظائف المخفية*\n\nلا توجد وظائف مخفية حالياً.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_hidden_jobs_keyboard([])
            )
        else:
            await query.edit_message_text(
                f"🚫 *الوظائف المخفية* ({len(jobs)})\n\nاضغط على أي وظيفة لإعادة إظهارها:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_hidden_jobs_keyboard(jobs)
            )

    elif data.startswith("unhide_job_"):
        job_id = int(data.rsplit("_", 1)[1])
        unhide_job(telegram_id, job_id)
        await query.answer("♻️ تم إعادة إظهار الوظيفة")
        jobs = get_jobs_by_ids(get_hidden_jobs(telegram_id))
        await query.edit_message_text(
            f"🚫 *الوظائف المخفية* ({len(jobs)})" if jobs
            else "🚫 *الوظائف المخفية*\n\nلا توجد وظائف مخفية حالياً.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_hidden_jobs_keyboard(jobs)
        )

    elif data == "settings_menu":
        await show_settings_menu(update, context)

    elif data == "preferences_menu":
        user = get_user(telegram_id)
        await query.answer()
        await query.edit_message_text(
            "🎯 *تفضيلاتي*\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_preferences_keyboard(user or {})
        )

    elif data == "edit_gender":
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        await query.answer()
        await query.edit_message_text(
            "⚧ اختر الجنس:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ذكر", callback_data="gender_ذكر"),
                 InlineKeyboardButton("أنثى", callback_data="gender_أنثى")],
                [InlineKeyboardButton("أفضل عدم التحديد", callback_data="gender_غير محدد")],
            ])
        )

    elif data.startswith("gender_"):
        update_user_field(telegram_id, "gender", data[len("gender_"):])
        await query.answer("تم حفظ التفضيل")
        await query.edit_message_text(
            "✅ تم تحديث الجنس.", reply_markup=get_preferences_keyboard(get_user(telegram_id) or {})
        )

    elif data == "toggle_general_jobs":
        user = get_user(telegram_id) or {}
        value = 0 if user.get("general_jobs_enabled", 1) else 1
        update_user_field(telegram_id, "general_jobs_enabled", value)
        await query.answer("تم تحديث الوظائف العامة")
        await query.edit_message_text(
            "🎯 *تفضيلاتي*", parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_preferences_keyboard(get_user(telegram_id) or {})
        )

    elif data == "message_content":
        context.user_data["state"] = States.MESSAGE_CONTENT
        await query.answer()
        await query.edit_message_text(
            "✏️ أرسل محتوى الرسالة التي تريد إرفاقها مع التقديمات:",
            reply_markup=get_back_to_menu_keyboard()
        )

    elif data == "blast_service":
        context.user_data["blast_categories"] = []
        await query.answer()
        await query.edit_message_text(
            "📨 *إرسال السيرة للشركات*\n\nاختر مجالاً أو أكثر:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_blast_categories_keyboard([])
        )

    elif data.startswith("blast_cat_"):
        code = data[len("blast_cat_"):]
        selected = context.user_data.setdefault("blast_categories", [])
        if code in selected:
            selected.remove(code)
        else:
            selected.append(code)
        await query.answer()
        await query.edit_message_reply_markup(get_blast_categories_keyboard(selected))

    elif data == "blast_all":
        context.user_data["blast_categories"] = ["all"]
        await query.answer("تم اختيار كل المجالات")
        await query.edit_message_reply_markup(get_blast_categories_keyboard(["all"]))

    elif data == "blast_next":
        if not context.user_data.get("blast_categories"):
            await query.answer("اختر مجالاً واحداً على الأقل", show_alert=True)
        else:
            await query.answer()
            await query.edit_message_text(
                "📨 *اختر عدد الشركات*\n\nسيتم إنشاء حملة مستمرة حتى اكتمال العدد:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_blast_packages_keyboard()
            )

    elif data.startswith("blast_plan_"):
        _, _, companies, points = data.split("_")
        await create_blast_campaign(update, context, int(companies), int(points))

    elif data == "blast_custom":
        context.user_data["state"] = States.BLAST_CUSTOM_COUNT
        await query.answer()
        await query.edit_message_text("✏️ أرسل عدد الشركات المطلوب:")

    elif data == "unsubscribe_yes":
        update_user_field(telegram_id, "auto_apply_enabled", 0)
        update_user_field(telegram_id, "notifications_enabled", 0)
        await query.answer("تم إيقاف الاشتراك")
        await query.edit_message_text(
            "✅ تم إيقاف التقديم التلقائي والتنبيهات.",
            reply_markup=get_back_to_menu_keyboard()
        )

    # ─── الملف الشخصي ───
    elif data == "profile":
        await show_profile(update, context)

    # ─── تعديل حقول الملف الشخصي ───
    elif data == "edit_preferences":
        await query.answer()
        await query.edit_message_text(
            "✏️ *تعديل الملف الشخصي*\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )

    elif data == "edit_name":
        await edit_name(update, context)

    elif data == "edit_region":
        await edit_region(update, context)

    elif data == "edit_specialization":
        await edit_specialization(update, context)

    elif data == "edit_education":
        await edit_education(update, context)

    elif data == "edit_experience":
        await edit_experience(update, context)

    elif data == "edit_work_type":
        await edit_work_type(update, context)

    elif data == "edit_salary":
        await edit_salary(update, context)

    elif data == "edit_phone":
        await edit_phone_field(update, context)

    elif data == "edit_email":
        await edit_email_field(update, context)

    elif data == "edit_cv":
        await edit_cv_field(update, context)

    elif data == "edit_linkedin":
        await edit_linkedin_field(update, context)

    # ─── إعداد الإيميل للتقديم التلقائي ───
    elif data == "email_setup":
        await start_email_setup(update, context)

    elif data == "setup_email":
        # إعادة توجيه لخطوة إدخال الإيميل
        from utils.email_sender import _ask_email_address
        context.user_data["state"] = States.EMAIL_SETUP_ADDRESS
        await _ask_email_address(query, context)

    elif data == "delete_email_creds":
        await query.answer()
        delete_email_credentials(telegram_id)
        await query.edit_message_text(
            "🗑️ *تم حذف بيانات الإيميل المحفوظة*\n\n"
            "يمكنك ربط إيميل جديد في أي وقت.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )

    elif data == "cancel_email_setup":
        await query.answer()
        context.user_data["state"] = States.MAIN_MENU
        context.user_data.pop("setup_email", None)
        await query.edit_message_text(
            "↩️ تم إلغاء إعداد الإيميل.",
            reply_markup=get_back_to_menu_keyboard()
        )

    # ─── إحصائيات المستخدم ───
    elif data == "my_stats":
        await show_stats(update, context)

    # ─── تصفح الوظائف ───
    elif data == "browse_jobs":
        await show_recent_jobs(update, context)

    # ─── إعدادات الإشعارات ───
    elif data == "notification_settings":
        await show_notification_settings(update, context)

    # ─── الخدمات والاشتراكات ───
    elif data == "account_balance":
        await show_account_balance(update, context)

    elif data == "subscriptions":
        await show_subscriptions(update, context)

    elif data == "points_history":
        await show_points_history(update, context)

    elif data.startswith("plan_"):
        await show_plan(update, context, data[len("plan_"):])

    elif data.startswith("subscribe_"):
        await request_plan_subscription(update, context, data[len("subscribe_"):])

    elif data == "toggle_notifications":
        user = get_user(telegram_id)
        current = user.get("notifications_enabled", 1)
        new_val = 0 if current else 1
        update_user_field(telegram_id, "notifications_enabled", new_val)
        status = "مفعّل 🔔" if new_val else "معطّل 🔕"
        await query.answer(f"الإشعارات: {status}")
        await show_notification_settings(update, context)

    elif data == "toggle_auto_apply":
        user = get_user(telegram_id)
        creds = get_email_credentials(telegram_id)
        if not creds:
            await query.answer()
            await query.edit_message_text(
                "⚠️ *يجب ربط إيميلك أولاً*\n\n"
                "اضغط الزر أدناه لربط Gmail وتفعيل التقديم التلقائي:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_email_actions_keyboard(has_creds=False)
            )
            return
        current = user.get("auto_apply_enabled", 0)
        new_val = 0 if current else 1
        update_user_field(telegram_id, "auto_apply_enabled", new_val)
        status = "مفعّل 🤖" if new_val else "معطّل"
        await query.answer(f"التقديم التلقائي: {status}")
        await show_settings_menu(update, context)

    # ─── التقديم على الوظائف ───
    elif data.startswith("mark_applied_"):
        job_id = int(data.split("_")[-1])
        if save_application(telegram_id, job_id, "manual"):
            await query.answer("✅ تم تسجيل تقديمك على هذه الوظيفة!")
        else:
            await query.answer("ℹ️ هذا التقديم مسجل مسبقاً")

    elif data.startswith("manual_apply_"):
        job_id = int(data.split("_")[-1])
        job = get_job(job_id)
        if not job:
            await query.answer("الوظيفة غير موجودة", show_alert=True)
        elif job.get("apply_link"):
            await query.answer("افتح رابط التقديم من الزر أدناه")
        elif job.get("apply_email"):
            await query.answer(f"البريد: {job['apply_email']}", show_alert=True)
        else:
            await query.answer("لا يوجد رابط أو بريد تقديم لهذه الوظيفة", show_alert=True)

    elif data.startswith("dismiss_job_"):
        job_id = int(data.rsplit("_", 1)[1])
        hide_job(telegram_id, job_id)
        await query.answer("🚫 تم إخفاء الوظيفة، تجدها في الإعدادات")
        await query.edit_message_reply_markup(reply_markup=None)

    elif data.startswith("auto_apply_"):
        job_id = int(data.split("_")[-1])
        from database.db import get_subscription
        subscription = get_subscription(telegram_id)
        if not subscription or subscription.get("applications_remaining", 0) <= 0:
            await query.answer("رصيد التقديم غير كافٍ. اختر باقة أولاً.", show_alert=True)
            await query.edit_message_reply_markup(
                reply_markup=get_subscription_keyboard(get_plans())
            )
            return
        await query.answer("⏳ جاري التقديم...")
        await execute_auto_apply(
            bot=context.bot,
            telegram_id=telegram_id,
            job_id=job_id,
            chat_id=update.effective_chat.id
        )

    elif data.startswith("save_job_"):
        job_id = int(data.rsplit("_", 1)[1])
        if save_job_for_user(telegram_id, job_id):
            await query.answer("💾 تم حفظ الوظيفة في قائمتك!")
        else:
            await query.answer("💾 الوظيفة محفوظة لديك مسبقاً")

    elif data.startswith("share_job_"):
        job_id = int(data.split("_")[-1])
        job = get_job(job_id)
        if job:
            share_text = f"💼 {job.get('title', 'وظيفة')}\n🏢 {job.get('company', '')}\n📍 {job.get('region', '')}"
            if job.get("apply_link"):
                share_text += f"\n🔗 {job['apply_link']}"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📤 *شارك هذه الوظيفة:*\n\n{share_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        await query.answer()

    elif data == "my_applications":
        await show_my_applications(update, context)

    # ─── إرسال السيرة الذاتية للمستخدم ───
    elif data == "send_my_cv":
        await send_cv_to_user(update, context)

    # ─── نصائح مهنية ───
    elif data == "career_tips":
        await show_career_tips(update, context)

    # ─── مساعدة ───
    elif data == "help":
        await show_help(update, context)

    # ─── عن البوت ───
    elif data == "about_bot":
        await show_about(update, context)

    # ─── cv menu ───
    elif data == "cv_menu":
        await show_cv_menu(update, context)

    else:
        await query.answer()
        await query.edit_message_text(
            "🚧 *هذه الخاصية قيد التطوير*\n\nستكون متاحة قريباً!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )


# ─────────────────────────────────────────
# دوال القوائم الجديدة
# ─────────────────────────────────────────

async def show_admin_dashboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE, message=None
):
    """لوحة مشرف آمنة داخل Telegram مع إدارة الباقات والطلبات."""
    if update.effective_user.id != ADMIN_ID or not ADMIN_ID:
        target = message or update.callback_query.message
        await target.reply_text("⛔ هذا القسم للمشرف فقط.")
        return
    from database.db import get_connection
    conn = get_connection()
    total_users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE registration_complete = 1"
    ).fetchone()[0]
    total_jobs = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE is_active = 1"
    ).fetchone()[0]
    total_apps = conn.execute(
        "SELECT COUNT(*) FROM applications"
    ).fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM subscription_requests WHERE status = 'pending'"
    ).fetchone()[0]
    conn.close()
    text = (
        "🛠️ *لوحة تحكم المشرف*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"👥 المستخدمون المسجلون: *{total_users}*\n"
        f"💼 الوظائف النشطة: *{total_jobs}*\n"
        f"📨 إجمالي التقديمات: *{total_apps}*\n"
        f"🧾 طلبات الاشتراك المعلقة: *{pending}*\n\n"
        "من هنا يمكنك إدارة أسعار الباقات، النقاط، وكوتة التقديم والشركات."
    )
    if update.callback_query:
        await update.callback_query.answer()
    target = message or (update.callback_query.message if update.callback_query else update.message)
    if update.callback_query and not message:
        await target.edit_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_dashboard_keyboard(),
        )
    else:
        await target.reply_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_dashboard_keyboard(),
        )


async def handle_admin_plan_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """استقبال قيمة واحدة من المشرف وتحديث الباقة بعد التحقق."""
    if update.effective_user.id != ADMIN_ID or not ADMIN_ID:
        context.user_data["state"] = States.MAIN_MENU
        await update.message.reply_text("⛔ هذا القسم للمشرف فقط.")
        return True
    plan_code = context.user_data.get("admin_plan_code")
    field = context.user_data.get("admin_plan_field")
    raw = (update.message.text or "").strip()
    numeric_fields = {
        "price": float,
        "points": int,
        "apps": int,
        "companies": int,
    }
    try:
        if field in numeric_fields:
            value = numeric_fields[field](raw.replace(",", ""))
            if value < 0:
                raise ValueError
        elif field in ("description", "name"):
            if not raw or len(raw) > 500:
                raise ValueError
            value = raw
        else:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ قيمة غير صحيحة. أرسل رقماً غير سالب، أو نصاً من 500 حرف كحد أقصى:"
        )
        return True

    db_field = {
        "name": "name",
        "price": "price",
        "points": "points",
        "apps": "applications_limit",
        "companies": "companies_limit",
        "description": "description",
    }[field]
    updated = update_plan(plan_code, db_field, value)
    context.user_data["state"] = States.MAIN_MENU
    context.user_data.pop("admin_plan_code", None)
    context.user_data.pop("admin_plan_field", None)
    plan = get_plan(plan_code)
    if updated and plan:
        await update.message.reply_text(
            f"✅ تم تحديث *{plan['name']}* بنجاح.\n\n"
            f"💰 السعر: {plan['price']:.0f} ريال\n"
            f"⭐ النقاط: {plan['points']}\n"
            f"🤖 كوتة التقديم: {plan['applications_limit']}\n"
            f"🏢 كوتة الشركات: {plan['companies_limit']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_plan_keyboard(plan_code),
        )
    else:
        await update.message.reply_text("❌ تعذر تحديث الباقة.")
    return True


async def show_settings_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, message=None
):
    telegram_id = update.effective_user.id
    user = get_user(telegram_id) or {}
    target = message or update.callback_query.message
    creds = get_email_credentials(telegram_id)
    await target.reply_text(
        "⚙️ *إعداداتي*\n\nتحكم في خدمات حسابك:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_settings_keyboard(
            user, bool(creds), bool(user.get("cv_file_id"))
        ),
    )


async def show_jobs_page(
    update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, page: int
):
    query = update.callback_query
    await query.answer()
    user = get_user(update.effective_user.id) or {}
    offset = page * 20
    hidden = get_hidden_jobs(update.effective_user.id)
    if mode == "matching":
        jobs = get_matching_jobs_page(user, 20, offset, hidden)
        total = count_jobs(user)
        title = "الوظائف المناسبة لي"
    else:
        jobs = get_jobs_page(20, offset, hidden)
        total = count_jobs()
        title = "كل الوظائف"
    if not jobs:
        await query.edit_message_text(
            f"📭 *{title}*\n\nلا توجد وظائف في هذه الصفحة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_jobs_menu_keyboard(),
        )
        return
    await query.edit_message_text(
        f"🔍 *{title}*\n\nصفحة {page + 1} — {len(jobs)} وظيفة",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_job_list_keyboard(jobs, page, mode, total),
    )


async def show_job_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, job_id: int):
    query = update.callback_query
    await query.answer()
    job = get_job(job_id)
    if not job:
        await query.edit_message_text("❌ الوظيفة غير موجودة.", reply_markup=get_jobs_menu_keyboard())
        return
    text = (
        f"💼 *{job.get('title', 'وظيفة')}*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🏢 الشركة: {job.get('company') or 'غير محدد'}\n"
        f"📍 الموقع: {job.get('location') or 'غير محدد'}\n"
        f"🎯 المجال: {job.get('category') or 'غير محدد'}\n\n"
        f"{(job.get('description') or 'لا يوجد وصف متاح.')[:1800]}"
    )
    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_job_detail_keyboard(job_id)
    )


async def create_blast_campaign(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    companies: int, points: int
):
    query = update.callback_query
    telegram_id = update.effective_user.id
    categories = context.user_data.get("blast_categories", [])
    ok, message = consume_subscription_usage(
        telegram_id, "company", "cv_campaign", f"{companies}:{points}"
    )
    if not ok:
        await query.answer(message, show_alert=True)
        return
    campaign_id = create_cv_campaign(telegram_id, categories, companies, points)
    await query.answer()
    await query.edit_message_text(
        f"✅ *تم إنشاء حملة إرسال السيرة #{campaign_id}*\n\n"
        f"المجالات: {', '.join(category_name(c) for c in categories)}\n"
        f"العدد المطلوب: {companies} شركة\n"
        "الحالة: ⏳ في الانتظار\n\n"
        "سيتم تنفيذها على دفعات حتى إكمال العدد المتاح.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_applications_menu_keyboard(),
    )


# ─────────────────────────────────────────
# دوال العرض
# ─────────────────────────────────────────

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الملف الشخصي"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await query.edit_message_text("❌ لم يُعثر على ملفك، ابدأ التسجيل أولاً")
        return

    cv_status = "✅ موجود" if user.get("cv_file_id") else "❌ لم يُرفع بعد"
    notif = "🔔 مفعّل" if user.get("notifications_enabled") else "🔕 معطّل"
    auto = "🤖 مفعّل" if user.get("auto_apply_enabled") else "❌ معطّل"
    creds = get_email_credentials(telegram_id)
    email_linked = f"✅ `{creds['sender_email']}`" if creds else "❌ لم يُربط"

    text = (
        "👤 *ملفك الشخصي*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📛 *الاسم:* {user.get('full_name_ar', '—')}\n"
        f"🌐 *(EN):* {user.get('full_name_en', '—')}\n"
        f"📍 *المنطقة:* {user.get('region', '—')}\n"
        f"🎯 *المجال:* {user.get('category', '—')}\n"
        f"🔍 *التخصص:* {user.get('specialization', '—')}\n"
        f"🎓 *المؤهل:* {user.get('education_level', '—')}\n"
        f"⭐ *الخبرة:* {user.get('experience_level', '—')}\n"
        f"🏢 *نوع الدوام:* {user.get('work_type', '—')}\n"
        f"💰 *الراتب:* {user.get('salary_range', '—')}\n"
        f"📄 *السيرة:* {cv_status}\n"
        f"📱 *الجوال:* {user.get('phone', '—')}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📧 *إيميل التقديم:* {email_linked}\n"
        f"🔔 *الإشعارات:* {notif}\n"
        f"🤖 *التقديم التلقائي:* {auto}\n"
    )

    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_edit_profile_keyboard()
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المستخدم مع اقتراح AI"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    stats = get_user_stats(telegram_id)
    user = get_user(telegram_id)

    # اقتراح AI لتحسين الملف الشخصي
    try:
        from utils.ai_helper import ai_suggest_improvements
        suggestion = ai_suggest_improvements(user) if user else ""
    except Exception:
        suggestion = ""

    text = (
        "📊 *إحصائياتك*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📨 *وظائف وصلتك:* {stats['total_notifications']}\n"
        f"✅ *تقديمات مكتملة:* {stats['total_applications']}\n"
        "━━━━━━━━━━━━━━━━\n"
        "_استمر في التقديم، النجاح قادم_ 💪"
    )

    if suggestion:
        text += f"\n\n{suggestion}"

    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )


async def show_recent_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض أحدث الوظائف"""
    query = update.callback_query
    await query.answer()
    jobs = get_recent_jobs(5)

    if not jobs:
        await query.edit_message_text(
            "📭 *لا توجد وظائف متاحة حالياً*\n\nسنُشعرك فور نزول وظائف جديدة 🔔",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )
        return

    from keyboards.keyboards import get_job_card_keyboard
    from utils.notifier import build_job_card_text

    await query.edit_message_text(
        f"💼 *أحدث {len(jobs)} وظائف:*",
        parse_mode=ParseMode.MARKDOWN
    )
    for job in jobs:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=build_job_card_text(job),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_job_card_keyboard(
                job["id"],
                job.get("apply_link"),
                job.get("apply_email")
            )
        )


async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إعدادات الإشعارات"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)
    creds = get_email_credentials(telegram_id)

    notif = bool(user.get("notifications_enabled", 1))
    auto = bool(user.get("auto_apply_enabled", 0))
    email_status = f"📧 `{creds['sender_email']}`" if creds else "📧 _لم يُربط بعد_"

    await query.edit_message_text(
        "🔔 *إعدادات الإشعارات والتقديم*\n\n"
        f"{email_status}\n\n"
        "اضغط للتبديل:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_notification_settings_keyboard(notif, auto)
    )


async def show_account_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        account_text(update.effective_user.id),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_account_keyboard()
    )


async def show_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plans = get_plans()
    from services.subscriptions import plans_text
    await query.edit_message_text(
        plans_text(plans),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_subscription_keyboard(plans)
    )


async def show_plan(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_code: str):
    query = update.callback_query
    await query.answer()
    plan = get_plan(plan_code)
    if not plan:
        await query.edit_message_text(
            "❌ هذه الباقة غير متاحة حالياً.",
            reply_markup=get_back_to_menu_keyboard()
        )
        return
    price = "مجانية" if not plan["price"] else f"{plan['price']:.0f} ريال"
    text = (
        f"📦 *{plan['name']}*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{plan.get('description') or ''}\n\n"
        f"💰 السعر: *{price}*\n"
        f"⭐ النقاط: *{plan['points']}*\n"
        f"🤖 التقديمات: *{plan['applications_limit']}*\n"
        f"🏢 الشركات: *{plan['companies_limit']}*\n\n"
        f"{plan_features(plan)}"
    )
    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_plan_action_keyboard(plan_code, not plan["price"])
    )


async def request_plan_subscription(
    update: Update, context: ContextTypes.DEFAULT_TYPE, plan_code: str
):
    query = update.callback_query
    await query.answer()
    plan = get_plan(plan_code)
    if not plan:
        await query.edit_message_text("❌ الباقة غير موجودة.")
        return
    if not plan["price"]:
        from database.db import ensure_default_subscription
        ensure_default_subscription(update.effective_user.id)
        await query.edit_message_text(
            "✅ *حسابك المجاني جاهز*\n\nيمكنك الآن استقبال التنبيهات واستخدام رصيد البداية.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_account_keyboard()
        )
        return
    request_id = request_plan(update.effective_user.id, plan_code)
    await query.edit_message_text(
        f"📝 *تم تسجيل طلبك رقم #{request_id}*\n\n"
        f"الباقة المطلوبة: *{plan['name']}*\n"
        f"القيمة: *{plan['price']:.0f} ريال*\n\n"
        "سيتم تفعيلها بعد إتمام الدفع والتحقق منه. "
        "لم يتم خصم أي مبلغ من حسابك في هذه المرحلة.\n\n"
        "لربط بوابة دفع إلكترونية، يمكن إضافة مزود الدفع لاحقاً دون تغيير نظام الاشتراكات.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_account_keyboard()
    )


async def show_my_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تقديمات المستخدم"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id

    from database.db import get_connection
    conn = get_connection()
    apps = conn.execute("""
        SELECT a.apply_method, a.applied_at, j.title, j.company, j.region
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.user_telegram_id = ?
        ORDER BY a.applied_at DESC
        LIMIT 10
    """, (telegram_id,)).fetchall()
    conn.close()

    if not apps:
        await query.edit_message_text(
            "📋 *تقديماتك*\n\nلم تقدّم على أي وظيفة بعد!\n\nابحث عن وظائف وقدّم عليها 💼",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )
        return

    method_icons = {"auto_email": "🤖", "manual": "✋", "link": "🔗"}
    text = "📋 *آخر تقديماتك:*\n\n"
    for app in apps:
        icon = method_icons.get(app["apply_method"], "📝")
        text += (
            f"{icon} *{app['company'] or 'غير محدد'}*\n"
            f"   💼 {app['title']}\n"
            f"   📍 {app['region'] or '—'} | 📅 {str(app['applied_at'])[:10]}\n"
            "─────────────\n"
        )

    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )


async def show_cv_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة السيرة الذاتية"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    from keyboards.keyboards import get_cv_options_keyboard
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    has_file_cv = bool(user and user.get("cv_file_id"))
    has_ai_cv = bool(user and user.get("ai_cv_text"))
    status = (
        "✅ *لديك سيرة ذاتية محفوظة*"
        if has_file_cv or has_ai_cv
        else "❌ *لا توجد سيرة ذاتية بعد*"
    )

    keyboard = [
        [InlineKeyboardButton("🤖 إنشاء سيرة جديدة بـ AI", callback_data="ai_cv_builder")],
        [InlineKeyboardButton("📎 رفع / تحديث السيرة الذاتية", callback_data="edit_cv")],
    ]
    if has_file_cv or has_ai_cv:
        keyboard.append([InlineKeyboardButton("📤 إرسال سيرتي لي", callback_data="send_my_cv")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="main_menu")])

    await query.edit_message_text(
        f"📄 *السيرة الذاتية*\n\n{status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_career_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نصائح مهنية مدعومة بالذكاء الاصطناعي"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    await query.edit_message_text(
        "🤖 _جاري توليد نصيحة مخصصة لك بالذكاء الاصطناعي..._",
        parse_mode=ParseMode.MARKDOWN
    )

    # نصائح احتياطية
    fallback_tips = [
        "📌 *خصّص سيرتك الذاتية لكل وظيفة*\nاجعل الكلمات المفتاحية تطابق الوصف الوظيفي.",
        "📌 *قدّم خلال أول 24 ساعة*\nالمتقدمون الأوائل يحظون باهتمام أكبر.",
        "📌 *أضف ملف LinkedIn قوي*\n85% من أصحاب العمل يتحققون من LinkedIn قبل المقابلة.",
        "📌 *لا تترك خانة الراتب فارغة*\nضع نطاقاً بحثت عنه مسبقاً في السوق.",
        "📌 *خطاب التقديم يُفرق*\nوظيفة مخصصة أفضل من عشر وظائف عشوائية.",
    ]

    try:
        from utils.ai_helper import get_groq_client, MODEL
        client = get_groq_client()

        if client and user:
            spec = user.get("specialization") or user.get("category") or "عام"
            exp = user.get("experience_level") or "غير محدد"
            region = user.get("region") or "السعودية"

            prompt = f"""أنت مستشار مهني خبير بسوق العمل السعودي.
قدم نصيحة مهنية عملية ومحددة لشخص يبحث عن عمل بهذه المواصفات:
- التخصص: {spec}
- الخبرة: {exp}
- المنطقة: {region}

اكتب نصيحة واحدة قصيرة ومفيدة (3-5 جمل) تتعلق بسوق العمل السعودي تحديداً.
ابدأها بـ 📌 ثم عنوان بارز، ثم الشرح."""

            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=200,
            )
            tip = response.choices[0].message.content.strip()
        else:
            import random
            tip = random.choice(fallback_tips)
    except Exception:
        import random
        tip = random.choice(fallback_tips)

    await query.edit_message_text(
        f"💡 *نصيحة مهنية مخصصة لك*\n\n{tip}\n\n_🤖 مدعوم بالذكاء الاصطناعي_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "❓ *كيف يعمل البوت؟*\n\n"
        "1️⃣ *أنشئ ملفك الشخصي* مع تحديد تخصصك ومنطقتك\n"
        "2️⃣ *ارفع سيرتك الذاتية* ليتمكن البوت من التقديم عنك\n"
        "3️⃣ *اربط Gmail* من الإعدادات للتقديم التلقائي\n"
        "4️⃣ *انتظر الإشعارات* وقدّم بضغطة واحدة!\n\n"
        "📞 للدعم تواصل مع المطوّر",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )


async def send_cv_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال السيرة الذاتية للمستخدم"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user or not user.get("cv_file_id") and not user.get("ai_cv_text"):
        await query.edit_message_text(
            "❌ *لا توجد سيرة ذاتية محفوظة*\n\nارفع سيرتك الذاتية أولاً.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )
        return

    try:
        if user.get("cv_file_id"):
            await context.bot.send_document(
                chat_id=telegram_id,
                document=user["cv_file_id"],
                caption="📄 *سيرتك الذاتية المحفوظة*",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            import io
            document = io.BytesIO(user["ai_cv_text"].encode("utf-8"))
            document.name = user.get("ai_cv_filename") or "saudi-ai-cv.txt"
            await context.bot.send_document(
                chat_id=telegram_id,
                document=document,
                caption="📄 *سيرتك الذاتية المصممة بـ AI*",
                parse_mode=ParseMode.MARKDOWN
            )
        await query.edit_message_text(
            "✅ *تم إرسال سيرتك الذاتية إليك!*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )
    except Exception as e:
        await query.edit_message_text(
            "❌ حدث خطأ في إرسال السيرة الذاتية. حاول مرة أخرى.",
            reply_markup=get_back_to_menu_keyboard()
        )


async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🤖 *بوت التوظيف السعودي*\n\n"
        "بوت ذكي يساعدك في إيجاد وظيفة أحلامك\n"
        "في المملكة العربية السعودية 🇸🇦\n\n"
        "🔸 يتابع قنوات التوظيف تلقائياً\n"
        "🔸 يُشعرك بالوظائف المناسبة فوراً\n"
        "🔸 يُقدّم بإيميلك الحقيقي تلقائياً\n"
        "🔸 يحفظ سيرتك الذاتية ويديرها\n\n"
        "_صُنع بـ 🤍 للباحثين عن عمل في السعودية_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )
