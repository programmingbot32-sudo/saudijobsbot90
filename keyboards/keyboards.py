"""
لوحات المفاتيح - Keyboards لجميع قوائم البوت
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from urllib.parse import quote
from config.settings import (
    SAUDI_REGIONS, JOB_CATEGORIES, EDUCATION_LEVELS,
    EXPERIENCE_LEVELS, WORK_TYPES, SALARY_RANGES
)


def get_main_menu_keyboard():
    """القائمة الرئيسية"""
    keyboard = [
        [
            InlineKeyboardButton("💳 اشتراكي", callback_data="account_balance"),
        ],
        [
            InlineKeyboardButton("👤 ملفي الشخصي", callback_data="profile"),
            InlineKeyboardButton("📄 سيرتي الذاتية", callback_data="cv_menu"),
        ],
        [
            InlineKeyboardButton("🔍 تصفح الوظائف", callback_data="browse_jobs"),
            InlineKeyboardButton("🤖 بحث عن وظيفة ب AI", callback_data="ai_job_search"),
            InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
        ],
        [
            InlineKeyboardButton("💳 اشتراكي ورصيدي", callback_data="account_balance"),
            InlineKeyboardButton("💎 الباقات والخدمات", callback_data="subscriptions"),
        ],
        [
            InlineKeyboardButton("🔔 إعدادات التنبيهات", callback_data="notification_settings"),
            InlineKeyboardButton("✏️ تعديل التفضيلات", callback_data="edit_preferences"),
        ],
        [
            InlineKeyboardButton("📋 تقديماتي", callback_data="my_applications"),
            InlineKeyboardButton("💡 نصائح مهنية", callback_data="career_tips"),
        ],
        [
            InlineKeyboardButton("❓ مساعدة", callback_data="help"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_main_reply_keyboard():
    """الشريط السفلي الدائم، وهو Reply Keyboard وليس Inline."""
    return ReplyKeyboardMarkup([
        [KeyboardButton("💳 اشتراكي")],
        [KeyboardButton("🔍 بحث عن وظيفة ب AI"), KeyboardButton("🔍 آخر الوظائف")],
        [KeyboardButton("📋 تقديماتي"), KeyboardButton("⚙️ إعداداتي")],
        [KeyboardButton("🎯 تفضيلاتي"), KeyboardButton("💬 الدعم")],
        [KeyboardButton("🚫 إلغاء الاشتراك"), KeyboardButton("📄 صمم سيرتي")],
        [KeyboardButton("⭐ تجارب العملاء"), KeyboardButton("⬅️ رجوع")],
    ], resize_keyboard=True, is_persistent=False, input_field_placeholder="اختر من القائمة 👇")


def get_start_keyboard():
    """زر البدء للمستخدمين الجدد"""
    keyboard = [
        [InlineKeyboardButton("🚀 إنشاء ملفي الشخصي", callback_data="start_registration")],
        [InlineKeyboardButton("ℹ️ عن البوت", callback_data="about_bot")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_regions_keyboard():
    """لوحة اختيار المنطقة"""
    keyboard = []
    row = []
    for i, region in enumerate(SAUDI_REGIONS):
        row.append(InlineKeyboardButton(region, callback_data=f"region_{region}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_categories_keyboard():
    """لوحة اختيار التخصص الرئيسي"""
    keyboard = []
    for category in JOB_CATEGORIES.keys():
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_specializations_keyboard(category: str):
    """لوحة اختيار التخصص الفرعي"""
    specs = JOB_CATEGORIES.get(category, [])
    keyboard = []
    for spec in specs:
        keyboard.append([InlineKeyboardButton(spec, callback_data=f"spec_{spec}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(keyboard)


def get_education_keyboard():
    """لوحة اختيار المؤهل الدراسي"""
    keyboard = []
    for edu in EDUCATION_LEVELS:
        keyboard.append([InlineKeyboardButton(edu, callback_data=f"edu_{edu}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_experience_keyboard():
    """لوحة اختيار سنوات الخبرة"""
    keyboard = []
    for exp in EXPERIENCE_LEVELS:
        keyboard.append([InlineKeyboardButton(exp, callback_data=f"exp_{exp}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_work_type_keyboard():
    """لوحة اختيار نوع الدوام"""
    keyboard = []
    row = []
    for i, wt in enumerate(WORK_TYPES):
        row.append(InlineKeyboardButton(wt, callback_data=f"wtype_{wt}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_salary_keyboard():
    """لوحة اختيار الراتب المتوقع"""
    keyboard = []
    for sal in SALARY_RANGES:
        keyboard.append([InlineKeyboardButton(sal, callback_data=f"sal_{sal}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_cv_options_keyboard():
    """خيارات إضافة السيرة الذاتية"""
    keyboard = [
        [InlineKeyboardButton("🤖 إنشاء سيرتي الذاتية بـ AI", callback_data="ai_cv_builder")],
        [InlineKeyboardButton("📎 رفع ملف PDF", callback_data="upload_cv_pdf")],
        [InlineKeyboardButton("🖼️ رفع صورة", callback_data="upload_cv_image")],
        [InlineKeyboardButton("✍️ تعبئة البيانات يدوياً", callback_data="manual_cv")],
        [InlineKeyboardButton("⏭️ تخطي الآن", callback_data="skip_cv")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_skip_keyboard(skip_data: str = "skip"):
    """زر تخطي"""
    keyboard = [
        [InlineKeyboardButton("⏭️ تخطي", callback_data=skip_data)],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_profile_keyboard():
    """تأكيد الملف الشخصي"""
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد وحفظ الملف", callback_data="confirm_profile")],
        [InlineKeyboardButton("✏️ تعديل", callback_data="edit_profile_before_save")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_job_card_keyboard(job_id: int, apply_link: str = None, apply_email: str = None):
    """أزرار بطاقة الوظيفة"""
    keyboard = []

    if apply_email:
        subject = quote("طلب توظيف")
        keyboard.append([
            InlineKeyboardButton("🤖 تقديم تلقائي", callback_data=f"auto_apply_{job_id}"),
            InlineKeyboardButton("✋ تقديم يدوي", url=f"mailto:{apply_email}?subject={subject}"),
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("✋ تقديم يدوي", callback_data=f"manual_apply_{job_id}"),
        ])
    if apply_link:
        keyboard.append([
            InlineKeyboardButton("🔗 فتح رابط التقديم", url=apply_link)
        ])

    keyboard.append([
        InlineKeyboardButton("✅ قدّمت عليها", callback_data=f"mark_applied_{job_id}"),
        InlineKeyboardButton("❌ لا تناسبني", callback_data=f"dismiss_job_{job_id}"),
    ])
    keyboard.append([
        InlineKeyboardButton("💾 حفظ الوظيفة", callback_data=f"save_job_{job_id}"),
        InlineKeyboardButton("📤 مشاركة", callback_data=f"share_job_{job_id}"),
    ])
    return InlineKeyboardMarkup(keyboard)


def get_subscription_keyboard(plans):
    """اختيار الباقات، مع إبقاء قرار الدفع خارج البوت حتى يتم ربط مزود دفع."""
    keyboard = []
    for plan in plans:
        label = f"{plan['name']} — {'مجاني' if not plan['price'] else str(int(plan['price'])) + ' ريال'}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"plan_{plan['code']}")])
    keyboard.extend([
        [InlineKeyboardButton("💳 رصيدي الحالي", callback_data="account_balance")],
        [InlineKeyboardButton("📜 تاريخ النقاط", callback_data="points_history")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
    ])
    return InlineKeyboardMarkup(keyboard)


def get_plan_action_keyboard(plan_code: str, is_free: bool = False):
    label = "✅ تفعيل الخطة المجانية" if is_free else "🛒 شراء هذه الباقة"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"subscribe_{plan_code}")],
        [InlineKeyboardButton("⬅️ جميع الباقات", callback_data="subscriptions")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
    ])


def get_account_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 عرض الباقات", callback_data="subscriptions")],
        [InlineKeyboardButton("📜 تاريخ النقاط", callback_data="points_history")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
    ])


def get_subscription_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 شراء باقة", callback_data="subscriptions")],
        [InlineKeyboardButton("⚡ شحن رصيد التقديم", callback_data="topup_points")],
        [InlineKeyboardButton("🔎 قدّم على الوظائف", callback_data="jobs_menu")],
        [InlineKeyboardButton("📨 أرسل سيرتك لمئات الشركات", callback_data="blast_service")],
        [InlineKeyboardButton("📜 تاريخ النقاط", callback_data="points_history")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")],
    ])


def get_ai_cv_skip_keyboard(skip_callback: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ تخطي", callback_data=skip_callback)],
        [InlineKeyboardButton("❌ إلغاء", callback_data="ai_cv_cancel")],
    ])


def get_ai_cv_summary_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ إكمال", callback_data="ai_cv_confirm_summary")],
        [InlineKeyboardButton("✏️ تعديل", callback_data="ai_cv_edit_summary")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="ai_cv_cancel")],
    ])


def get_ai_cv_collect_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎨 اختيار تصميم PDF للسيرة الذاتية", callback_data="ai_cv_select_design")],
        [InlineKeyboardButton("✅ انتهيت — صمم سيرتي", callback_data="ai_cv_done")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="ai_cv_cancel")],
    ])


def get_cv_design_selection_keyboard(selected_design: int = 1):
    d1 = "✨ كلاسيكي عصري" + (" (محدد)" if selected_design == 1 else "")
    d2 = "🎨 إبداعي بعمودين" + (" (محدد)" if selected_design == 2 else "")
    d3 = "👔 تنفيذي أنيق" + (" (محدد)" if selected_design == 3 else "")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(d1, callback_data="set_cv_design_1")],
        [InlineKeyboardButton(d2, callback_data="set_cv_design_2")],
        [InlineKeyboardButton(d3, callback_data="set_cv_design_3")],
        [InlineKeyboardButton("🚀 إنشاء السيرة الذاتية الآن", callback_data="ai_cv_done")],
        [InlineKeyboardButton("↩️ إرسال المزيد من البيانات", callback_data="ai_cv_continue_collect")],
    ])


def get_ai_job_search_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ إلغاء البحث", callback_data="ai_job_cancel")],
    ])


def get_ai_job_more_keyboard(has_more: bool = True):
    buttons = []
    if has_more:
        buttons.append([InlineKeyboardButton("➕ المزيد من الوظائف", callback_data="ai_jobs_more")])
    buttons.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def get_admin_dashboard_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 إدارة الباقات", callback_data="admin_plans")],
        [InlineKeyboardButton("🧾 طلبات الاشتراك", callback_data="admin_requests")],
        [InlineKeyboardButton("📊 تحديث الإحصائيات", callback_data="admin_dashboard")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
    ])


def get_admin_plans_keyboard(plans):
    keyboard = [
        [InlineKeyboardButton(
            f"{plan['name']} — {plan['price']:.0f} ريال",
            callback_data=f"admin_plan_{plan['code']}",
        )]
        for plan in plans
    ]
    keyboard.append([InlineKeyboardButton("⬅️ لوحة المشرف", callback_data="admin_dashboard")])
    return InlineKeyboardMarkup(keyboard)


def get_admin_plan_keyboard(plan_code: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 تعديل السعر", callback_data=f"admin_edit_price_{plan_code}")],
        [InlineKeyboardButton("⭐ تعديل النقاط", callback_data=f"admin_edit_points_{plan_code}")],
        [InlineKeyboardButton("🤖 تعديل كوتة التقديم", callback_data=f"admin_edit_apps_{plan_code}")],
        [InlineKeyboardButton("🏢 تعديل كوتة الشركات", callback_data=f"admin_edit_companies_{plan_code}")],
        [InlineKeyboardButton("📝 تعديل الوصف", callback_data=f"admin_edit_description_{plan_code}")],
        [InlineKeyboardButton("⬅️ كل الباقات", callback_data="admin_plans")],
    ])


def get_admin_requests_keyboard(requests):
    keyboard = []
    for request in requests:
        keyboard.append([InlineKeyboardButton(
            f"✅ اعتماد #{request['id']} — {request['plan_name']}",
            callback_data=f"admin_approve_request_{request['id']}",
        )])
    keyboard.append([InlineKeyboardButton("⬅️ لوحة المشرف", callback_data="admin_dashboard")])
    return InlineKeyboardMarkup(keyboard)


def get_topup_keyboard():
    from services.catalog import TOPUP_PACKAGES
    keyboard = []
    for item in TOPUP_PACKAGES:
        saving = f" ({item['saving']})" if item["saving"] else ""
        keyboard.append([InlineKeyboardButton(
            f"{item['points']} نقطة – {item['amount']} ر.س{saving}",
            callback_data=f"topup_{item['points']}_{item['amount']}"
        )])
    keyboard.extend([
        [InlineKeyboardButton("✏️ إدخال مبلغ يدوي", callback_data="custom_topup")],
        [InlineKeyboardButton("⬅️ رجوع BACK", callback_data="my_subscription_menu")],
    ])
    return InlineKeyboardMarkup(keyboard)


def get_payment_keyboard(order_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 ادفع الحين", callback_data=f"pay_order_{order_id}")],
        [InlineKeyboardButton("⬅️ رجوع BACK", callback_data="topup_points")],
    ])


def get_jobs_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 المناسبة لي", callback_data="jobs_mode_matching")],
        [InlineKeyboardButton("📋 كل الوظائف", callback_data="jobs_mode_all")],
        [InlineKeyboardButton("⬅️ رجوع BACK", callback_data="my_subscription_menu")],
    ])


def get_job_list_keyboard(jobs, page: int, mode: str, total: int):
    keyboard = [[InlineKeyboardButton(
        f"🚀 قدم على الجميع ({min(total, 20)})",
        callback_data=f"apply_all_{mode}_{page}"
    )]]
    for index, job in enumerate(jobs, start=page * 20 + 1):
        title = (job.get("title") or "وظيفة")[:34]
        keyboard.append([InlineKeyboardButton(
            f"{index}. {title}", callback_data=f"job_view_{job['id']}"
        )])
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton("← السابقة", callback_data=f"jobs_page_{mode}_{page - 1}"))
    if (page + 1) * 20 < total:
        navigation.append(InlineKeyboardButton("التالية →", callback_data=f"jobs_page_{mode}_{page + 1}"))
    if navigation:
        keyboard.append(navigation)
    keyboard.append([InlineKeyboardButton("⬅️ رجوع BACK", callback_data="jobs_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_job_detail_keyboard(job_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تقديم على الوظيفة", callback_data=f"apply_job_{job_id}")],
        [InlineKeyboardButton("🚫 مو من اهتمامي", callback_data=f"dismiss_job_{job_id}")],
        [InlineKeyboardButton("⬅️ رجوع للقائمة", callback_data="jobs_page_all_0")],
    ])


def get_applications_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 التقديم التلقائي اليومي", callback_data="applications_daily")],
        [InlineKeyboardButton("📨 أرسل سيرتي للشركات", callback_data="applications_blast")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")],
    ])


def get_settings_keyboard(user, email_linked: bool, has_cv: bool):
    auto = "✅ مفعل" if user.get("auto_apply_enabled") else "❌ معطل"
    email = "✅ مرتبط" if email_linked else "❌ لم يتم ربط بريد"
    cv = "✅ مرفوعة" if has_cv else "❌ لم ترفع"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🤖 التقديم التلقائي المستمر: {auto}", callback_data="toggle_auto_apply")],
        [InlineKeyboardButton(f"📧 البريد الإلكتروني: {email}", callback_data="email_setup")],
        [InlineKeyboardButton(f"📄 سيرتي الذاتية: {cv}", callback_data="cv_menu")],
        [InlineKeyboardButton("💳 اشتراكي", callback_data="account_balance")],
        [InlineKeyboardButton("✏️ محتوى الرسالة", callback_data="message_content")],
        [InlineKeyboardButton("🚫 الوظائف المخفية", callback_data="hidden_jobs")],
        [InlineKeyboardButton("🎯 تفضيلاتي", callback_data="preferences_menu")],
        [InlineKeyboardButton("🏠 الرئيسية BACK", callback_data="main_menu")],
    ])


def get_preferences_keyboard(user):
    general = "✅ مفعل" if user.get("general_jobs_enabled", 1) else "❌ معطل"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 تعديل المدن", callback_data="edit_region")],
        [InlineKeyboardButton("🎯 تعديل التخصصات", callback_data="edit_specialization")],
        [InlineKeyboardButton("🎓 تعديل الشهادة", callback_data="edit_education")],
        [InlineKeyboardButton("⚧ تعديل الجنس", callback_data="edit_gender")],
        [InlineKeyboardButton("⭐ عندي خبرة", callback_data="edit_experience")],
        [InlineKeyboardButton(f"🌐 الوظائف العامة: {general}", callback_data="toggle_general_jobs")],
        [InlineKeyboardButton("👤 تعديل الاسم", callback_data="edit_name")],
        [InlineKeyboardButton("📱 تعديل الجوال", callback_data="edit_phone")],
        [InlineKeyboardButton("🏠 الرئيسية BACK", callback_data="main_menu")],
    ])


def get_unsubscribe_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ نعم، أوقف الاشتراك", callback_data="unsubscribe_yes")],
        [InlineKeyboardButton("❌ تراجعت", callback_data="main_menu")],
    ])


def get_blast_categories_keyboard(selected):
    from services.catalog import BLAST_CATEGORIES
    keyboard = []
    for code, name in BLAST_CATEGORIES:
        mark = "✅ " if code in selected else ""
        keyboard.append([InlineKeyboardButton(
            mark + name, callback_data=f"blast_cat_{code}"
        )])
    keyboard.extend([
        [InlineKeyboardButton("🌐 كل المجالات", callback_data="blast_all")],
        [InlineKeyboardButton("التالي →", callback_data="blast_next")],
        [InlineKeyboardButton("⬅️ رجوع BACK", callback_data="my_subscription_menu")],
    ])
    return InlineKeyboardMarkup(keyboard)


def get_blast_packages_keyboard():
    from services.catalog import BLAST_PACKAGES
    keyboard = [[InlineKeyboardButton(
        f"{p['companies']} شركة — {p['points']} نقطة",
        callback_data=f"blast_plan_{p['companies']}_{p['points']}"
    )] for p in BLAST_PACKAGES]
    keyboard += [
        [InlineKeyboardButton("✏️ حدد عدد مخصص", callback_data="blast_custom")],
        [InlineKeyboardButton("⬅️ رجوع BACK", callback_data="blast_service")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_notification_settings_keyboard(notifications_on: bool, auto_apply_on: bool):
    """إعدادات الإشعارات"""
    notif_icon = "🔔 مفعّل" if notifications_on else "🔕 معطّل"
    auto_icon = "✅ مفعّل" if auto_apply_on else "❌ معطّل"

    keyboard = [
        [InlineKeyboardButton(
            f"الإشعارات: {notif_icon}",
            callback_data="toggle_notifications"
        )],
        [InlineKeyboardButton(
            f"التقديم التلقائي: {auto_icon}",
            callback_data="toggle_auto_apply"
        )],
        [InlineKeyboardButton(
            "📧 إعداد إيميل التقديم",
            callback_data="email_setup"
        )],
        [InlineKeyboardButton("⬅️ رجوع للقائمة", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_edit_profile_keyboard():
    """قائمة تعديل الملف الشخصي"""
    keyboard = [
        [
            InlineKeyboardButton("✏️ الاسم", callback_data="edit_name"),
            InlineKeyboardButton("📍 المنطقة", callback_data="edit_region"),
        ],
        [
            InlineKeyboardButton("🎯 التخصص", callback_data="edit_specialization"),
            InlineKeyboardButton("🎓 المؤهل", callback_data="edit_education"),
        ],
        [
            InlineKeyboardButton("⭐ الخبرة", callback_data="edit_experience"),
            InlineKeyboardButton("🏢 نوع الدوام", callback_data="edit_work_type"),
        ],
        [
            InlineKeyboardButton("💰 الراتب المتوقع", callback_data="edit_salary"),
            InlineKeyboardButton("📧 الإيميل", callback_data="edit_email"),
        ],
        [
            InlineKeyboardButton("📄 السيرة الذاتية", callback_data="edit_cv"),
            InlineKeyboardButton("🔗 LinkedIn", callback_data="edit_linkedin"),
        ],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard():
    """زر الرجوع للقائمة الرئيسية"""
    keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]]
    return InlineKeyboardMarkup(keyboard)


def get_hidden_jobs_keyboard(jobs):
    """قائمة الوظائف المخفية مع إمكانية إظهارها من جديد"""
    keyboard = []
    for job in jobs[:20]:
        title = (job.get("title") or "وظيفة")[:35]
        keyboard.append([
            InlineKeyboardButton(f"♻️ إظهار: {title}", callback_data=f"unhide_job_{job['id']}")
        ])
    keyboard.append([InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings_menu")])
    keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)
