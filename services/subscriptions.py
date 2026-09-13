"""خدمات الاشتراكات والرصيد والاستحقاقات."""

from typing import Dict, List, Optional

from database.db import (
    ensure_default_subscription,
    get_plan,
    get_plans,
    get_point_transactions,
    get_subscription,
    request_subscription,
)


def ensure_account(telegram_id: int) -> Optional[Dict]:
    return get_subscription(telegram_id) or ensure_default_subscription(telegram_id)


def plan_features(plan: Dict) -> str:
    features = plan.get("features") or []
    return "\n".join(f"• {feature}" for feature in features) or "• خدمات أساسية"


def request_plan(telegram_id: int, plan_code: str) -> Optional[int]:
    return request_subscription(telegram_id, plan_code)


def account_text(telegram_id: int) -> str:
    subscription = ensure_account(telegram_id)
    if not subscription:
        return "❌ تعذر إيجاد أو إنشاء تفاصيل الاشتراك حالياً."
    ends = subscription.get("ends_at") or "غير محدد (دائم)"
    plan_description = subscription.get("plan_description") or "خدمات التوظيف الأساسية"
    end_label = ends[:10] if ends != "غير محدد (دائم)" and len(ends) >= 10 else ends

    plan_name = subscription.get('plan_name', 'المجانية')
    points = subscription.get('points_balance', 0)
    apps = subscription.get('applications_remaining', 0)
    companies = subscription.get('companies_remaining', 0)

    return (
        "💳 *بطاقة تفاصيل الاشتراك والرصيد*\n"
        "✨ *Saudi Jobs Telegram Bot*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *الباقة الحالية:* {plan_name}\n"
        f"💬 *الوصف:* _{plan_description}_\n\n"
        "📊 *تفاصيل الكوتة والرصيد المتاح:*\n"
        f"  ⭐ *النقاط العامة:* `{points}` نقطة\n"
        f"  🤖 *كوتة التقديم اليومي:* `{apps}` تقديم\n"
        f"  🏢 *كوتة إيميلات HR والشركات:* `{companies}` شركة\n\n"
        f"📅 *تاريخ نهاية الاشتراك:* `{end_label}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *ملاحظة:* يمكنك ترقية باقتك أو زيادة كوتة التقديمات في أي وقت بالضغط على «شراء باقة»."
    )


def plans_text(plans: List[Dict]) -> str:
    lines = [
        "💎 *قائمة الباقات والاشتراكات المتاحة*",
        "اختر الباقة المناسبة لاحتياجاتك للحصول على أعلى كوتة تقديم للشركات وإيميلات HR:",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for plan in plans:
        price = "مجانية 🎁" if not plan["price"] else f"*{plan['price']:.0f} ريال*"
        period = (
            f" / {plan['billing_period_days']} يوم"
            if plan.get("billing_period_days") else ""
        )
        lines.extend([
            f"\n📦 *{plan['name']}*",
            f"💰 *السعر:* {price}{period}",
            f"📝 *التفاصيل:* _{plan.get('description') or 'خدمات أساسية'}_",
            f"⭐ *النقاط:* `{plan['points']}` | 🤖 *التقديم اليومي:* `{plan['applications_limit']}` | 🏢 *إيميلات HR:* `{plan['companies_limit']}`",
            "──────────────────────",
        ])
    return "\n".join(lines)


def history_text(telegram_id: int) -> str:
    rows = get_point_transactions(telegram_id, 12)
    if not rows:
        return "📜 *تاريخ النقاط*\n\nلا توجد عمليات مسجلة بعد."
    lines = ["📜 *تاريخ النقاط*", "━━━━━━━━━━━━━━━━"]
    for row in rows:
        sign = "+" if row["amount"] > 0 else ""
        lines.append(
            f"{sign}{row['amount']} نقطة — {row.get('description') or 'عملية'}\n"
            f"_{str(row['created_at'])[:16]}_"
        )
    return "\n".join(lines)