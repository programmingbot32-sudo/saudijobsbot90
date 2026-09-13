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
        return "❌ تعذر إنشاء حساب الرصيد حالياً."
    ends = subscription.get("ends_at") or "مفتوح"
    plan_description = subscription.get("plan_description") or "الخدمات الأساسية"
    end_label = ends[:10] if ends != "مفتوح" else ends
    return (
        "💳 *اشتراكي ورصيدي*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📦 *الباقة الحالية:* {subscription.get('plan_name', 'مجانية')}\n"
        f"📝 {plan_description}\n\n"
        "📊 *الرصيد المتاح الآن*\n"
        f"⭐ النقاط: *{subscription.get('points_balance', 0)}*\n"
        f"🤖 التقديمات على الوظائف: *{subscription.get('applications_remaining', 0)}*\n"
        f"🏢 التقديمات على إيميلات HR: *{subscription.get('companies_remaining', 0)}*\n\n"
        f"📅 *تاريخ الانتهاء:* {end_label}\n"
        "━━━━━━━━━━━━━━━━\n"
        "اختر «شراء باقة» لزيادة رصيدك أو عرض تفاصيل الباقات."
    )


def plans_text(plans: List[Dict]) -> str:
    lines = [
        "💎 *الباقات المتاحة*",
        "اختر أي باقة لعرض تفاصيلها ثم إرسال طلب الشراء.",
        "━━━━━━━━━━━━━━━━",
    ]
    for plan in plans:
        price = "مجانية" if not plan["price"] else f"{plan['price']:.0f} ريال"
        period = (
            f" / {plan['billing_period_days']} يوم"
            if plan.get("billing_period_days") else ""
        )
        lines.extend([
            f"\n📦 *{plan['name']}*",
            f"💰 السعر: *{price}*{period}",
            f"📝 {plan.get('description') or 'خدمات أساسية'}",
            f"⭐ النقاط: *{plan['points']}*",
            f"🤖 تقديمات الوظائف: *{plan['applications_limit']}*",
            f"🏢 إيميلات HR والشركات: *{plan['companies_limit']}*",
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