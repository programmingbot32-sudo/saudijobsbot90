import unittest
import os

TEST_DB = "/tmp/test_saudi_jobs.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["DB_PATH"] = TEST_DB

from database.db import (
    init_db, ensure_default_subscription, get_subscription, get_plans,
    update_plan, consume_subscription_usage, restore_subscription_usage
)
from services.subscriptions import account_text, plans_text


class TestSubscriptionServices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_default_subscription_creation(self):
        user_id = 123456789
        sub = ensure_default_subscription(user_id)
        self.assertIsNotNone(sub)
        self.assertEqual(sub["telegram_id"], user_id)
        self.assertEqual(sub["plan_code"], "free")
        self.assertGreaterEqual(sub["points_balance"], 0)

    def test_account_text_formatting(self):
        user_id = 987654321
        ensure_default_subscription(user_id)
        text = account_text(user_id)
        self.assertIn("بطاقة تفاصيل الاشتراك والرصيد", text)
        self.assertIn("الباقة الحالية:", text)
        self.assertIn("النقاط العامة:", text)
        self.assertIn("كوتة التقديم اليومي:", text)
        self.assertIn("كوتة إيميلات HR والشركات:", text)

    def test_plans_text_formatting(self):
        plans = get_plans()
        self.assertTrue(len(plans) > 0)
        text = plans_text(plans)
        self.assertIn("قائمة الباقات والاشتراكات المتاحة", text)
        for plan in plans:
            self.assertIn(plan["name"], text)

    def test_update_plan(self):
        plan_code = "starter"
        # Update price
        success = update_plan(plan_code, "price", 59)
        self.assertTrue(success)

        # Update name
        success_name = update_plan(plan_code, "name", "باقة البداية المحدثة")
        self.assertTrue(success_name)

        # Verify
        plans = get_plans()
        starter_plan = next((p for p in plans if p["code"] == plan_code), None)
        self.assertIsNotNone(starter_plan)
        self.assertEqual(starter_plan["price"], 59)
        self.assertEqual(starter_plan["name"], "باقة البداية المحدثة")

    def test_consume_and_restore_usage(self):
        user_id = 555666777
        sub = ensure_default_subscription(user_id)
        initial_points = sub["points_balance"]

        if initial_points > 0:
            ok, msg = consume_subscription_usage(user_id, "application", "job", "1")
            self.assertTrue(ok)

            updated_sub = get_subscription(user_id)
            self.assertEqual(updated_sub["points_balance"], initial_points - 1)

            # Restore
            restored = restore_subscription_usage(user_id, "application", "job", "1")
            self.assertTrue(restored)

            final_sub = get_subscription(user_id)
            self.assertEqual(final_sub["points_balance"], initial_points)


if __name__ == "__main__":
    unittest.main()
