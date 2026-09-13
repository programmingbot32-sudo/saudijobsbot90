"""
قاعدة البيانات - نماذج البيانات والعمليات الأساسية
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict


import os

DB_PATH = os.environ.get("DB_PATH", "saudi_jobs_bot.db")

_PRAGMAS_APPLIED = False


def get_connection():
    """اتصال SQLite مهيّأ للعمل تحت التزامن (WAL + مهلة انتظار)."""
    global _PRAGMAS_APPLIED
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    if not _PRAGMAS_APPLIED:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
        except sqlite3.Error:
            pass
        _PRAGMAS_APPLIED = True
    return conn


def init_db():
    """إنشاء جداول قاعدة البيانات"""
    conn = get_connection()
    cursor = conn.cursor()

    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name_ar TEXT,
            full_name_en TEXT,
            region TEXT,
            category TEXT,
            specialization TEXT,
            education_level TEXT,
            experience_level TEXT,
            work_type TEXT,
            salary_range TEXT,
            email TEXT,
            phone TEXT,
            linkedin_url TEXT,
            cv_file_id TEXT,
            cv_filename TEXT,
            is_active INTEGER DEFAULT 1,
            notifications_enabled INTEGER DEFAULT 1,
            auto_apply_enabled INTEGER DEFAULT 0,
            registration_complete INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # ترقية قواعد البيانات الموجودة دون حذف بيانات المستخدمين.
    for column, definition in (
        ("gender", "TEXT"),
        ("general_jobs_enabled", "INTEGER DEFAULT 1"),
        ("message_content", "TEXT"),
        ("hidden_jobs_json", "TEXT DEFAULT '[]'"),
        ("saved_jobs_json", "TEXT DEFAULT '[]'"),
        ("preferred_regions_json", "TEXT DEFAULT '[]'"),
        ("preferred_categories_json", "TEXT DEFAULT '[]'"),
        ("ai_cv_text", "TEXT"),
        ("ai_cv_filename", "TEXT"),
    ):
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError:
            pass

    # جدول الوظائف
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_message_id INTEGER UNIQUE,
            title TEXT NOT NULL,
            company TEXT,
            region TEXT,
            category TEXT,
            specialization TEXT,
            description TEXT,
            requirements TEXT,
            apply_link TEXT,
            apply_email TEXT,
            salary TEXT,
            work_type TEXT,
            deadline TEXT,
            is_active INTEGER DEFAULT 1,
            source_channel TEXT,
            raw_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول التقديمات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_telegram_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            apply_method TEXT,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (user_telegram_id) REFERENCES users (telegram_id),
            FOREIGN KEY (job_id) REFERENCES jobs (id),
            UNIQUE(user_telegram_id, job_id)
        )
    """)

    # جدول إشعارات الوظائف المرسلة
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_telegram_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            action TEXT DEFAULT 'sent',
            UNIQUE(user_telegram_id, job_id)
        )
    """)

    # جدول بيانات إيميل التقديم التلقائي
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_credentials (
            telegram_id INTEGER PRIMARY KEY,
            sender_email TEXT NOT NULL,
            app_password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # الخدمات والخطط والاشتراكات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            unit TEXT DEFAULT 'usage',
            is_active INTEGER DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL DEFAULT 0,
            currency TEXT DEFAULT 'SAR',
            billing_period_days INTEGER,
            points INTEGER DEFAULT 0,
            applications_limit INTEGER DEFAULT 0,
            companies_limit INTEGER DEFAULT 0,
            features_json TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            starts_at TEXT NOT NULL,
            ends_at TEXT,
            points_balance INTEGER DEFAULT 0,
            applications_remaining INTEGER DEFAULT 0,
            companies_remaining INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS point_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            description TEXT,
            reference_type TEXT,
            reference_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscription_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            order_type TEXT NOT NULL,
            amount REAL NOT NULL,
            points INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            provider_order_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            paid_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cv_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            categories_json TEXT NOT NULL,
            target_count INTEGER NOT NULL,
            points_cost INTEGER NOT NULL,
            status TEXT DEFAULT 'queued',
            processed_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaign_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            company TEXT,
            recipient_email TEXT NOT NULL,
            job_id INTEGER,
            status TEXT DEFAULT 'queued',
            attempted_at TEXT,
            UNIQUE(campaign_id, recipient_email),
            FOREIGN KEY (campaign_id) REFERENCES cv_campaigns(id)
        )
    """)

    services = [
        ("job_alerts", "تنبيهات الوظائف", "إشعارات الوظائف المناسبة", "notification"),
        ("auto_apply", "التقديم التلقائي", "التقديم عبر البريد نيابة عنك", "application"),
        ("cv_marketing", "تسويق السيرة الذاتية", "إرسال سيرتك للشركات", "company"),
        ("cv_improvement", "تحسين السيرة الذاتية", "تحسين السيرة بالذكاء الاصطناعي", "usage"),
        ("cover_letter", "خطاب التغطية", "إنشاء خطاب مخصص لكل وظيفة", "usage"),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO services (code, name, description, unit)
        VALUES (?, ?, ?, ?)
    """, services)
    plans = [
        ("free", "الخطة المجانية", "ابدأ باكتشاف الوظائف المناسبة", 0, 0, 1, 1, 0,
         json.dumps(["تنبيهات الوظائف اليومية"], ensure_ascii=False)),
        ("starter", "باقة البداية", "مناسبة للباحثين عن فرصة جديدة", 49, 30, 600, 100, 500,
         json.dumps(["تنبيهات الوظائف اليومية", "تقديم تلقائي وإيميلات HR"], ensure_ascii=False)),
        ("professional", "باقة 100 ريال", "2000 تقديم مباشر على قائمة إيميلات HR + 300 تقديم مباشر على الفرص اليومية", 100, 30, 2300, 300, 2000,
         json.dumps(["تقديم مباشر على إيميلات HR", "تقديم مباشر على الفرص اليومية", "بحث وظائف بالذكاء الاصطناعي"], ensure_ascii=False)),
        ("premium", "الباقة المميزة", "أقصى وصول وأولوية في التقديم", 199, 30, 880, 80, 800,
         json.dumps(["تقديم تلقائي وإيميلات HR", "أولوية في التقديم والدعم"], ensure_ascii=False)),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO plans
        (code, name, description, price, billing_period_days, points,
         applications_limit, companies_limit, features_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, plans)
    # تحديث بيانات الباقات لضمان تطابق النقاط مع التقديمات وتحديث المزايا
    cursor.execute("""
        UPDATE plans
        SET name = ?, description = ?, price = ?, billing_period_days = ?,
            points = ?, applications_limit = ?, companies_limit = ?,
            features_json = ?
        WHERE code = 'free'
    """, (
        "الخطة المجانية", "ابدأ باكتشاف الوظائف المناسبة", 0, 0, 1, 1, 0,
        json.dumps(["تنبيهات الوظائف اليومية"], ensure_ascii=False),
    ))
    cursor.execute("""
        UPDATE plans
        SET name = ?, description = ?, price = ?, billing_period_days = ?,
            points = ?, applications_limit = ?, companies_limit = ?,
            features_json = ?
        WHERE code = 'starter'
    """, (
        "باقة البداية", "مناسبة للباحثين عن فرصة جديدة", 49, 30, 600, 100, 500,
        json.dumps(["تنبيهات الوظائف اليومية", "تقديم تلقائي وإيميلات HR"], ensure_ascii=False),
    ))
    cursor.execute("""
        UPDATE plans
        SET name = ?, description = ?, price = ?, billing_period_days = ?,
            points = ?, applications_limit = ?, companies_limit = ?,
            features_json = ?
        WHERE code = 'professional'
    """, (
        "باقة 100 ريال",
        "2000 تقديم مباشر على قائمة إيميلات HR + 300 تقديم مباشر على الفرص اليومية",
        100, 30, 2300, 300, 2000,
        json.dumps([
            "تقديم مباشر على إيميلات HR",
            "تقديم مباشر على الفرص اليومية",
            "بحث وظائف بالذكاء الاصطناعي",
        ], ensure_ascii=False),
    ))
    cursor.execute("""
        UPDATE plans
        SET name = ?, description = ?, price = ?, billing_period_days = ?,
            points = ?, applications_limit = ?, companies_limit = ?,
            features_json = ?
        WHERE code = 'premium'
    """, (
        "الباقة المميزة", "أقصى وصول وأولوية في التقديم", 199, 30, 880, 80, 800,
        json.dumps(["تقديم تلقائي وإيميلات HR", "أولوية في التقديم والدعم"], ensure_ascii=False),
    ))
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status
        ON subscriptions (telegram_id, status, ends_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_user_date
        ON point_transactions (telegram_id, created_at)
    """)

    conn.commit()
    conn.close()
    print("✅ تم إنشاء قاعدة البيانات بنجاح")


# ─────────────────────────────────────────
# عمليات المستخدمين
# ─────────────────────────────────────────

def save_user(telegram_id: int, data: dict) -> bool:
    conn = get_connection()
    try:
        existing = get_user(telegram_id)
        if existing:
            fields = ", ".join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [datetime.now().isoformat(), telegram_id]
            conn.execute(
                f"UPDATE users SET {fields}, updated_at = ? WHERE telegram_id = ?",
                values
            )
        else:
            data["telegram_id"] = telegram_id
            data["created_at"] = datetime.now().isoformat()
            placeholders = ", ".join(["?" for _ in data])
            columns = ", ".join(data.keys())
            conn.execute(
                f"INSERT INTO users ({columns}) VALUES ({placeholders})",
                list(data.values())
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ خطأ في حفظ المستخدم: {e}")
        return False
    finally:
        conn.close()


def get_user(telegram_id: int) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_field(telegram_id: int, field: str, value) -> bool:
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE users SET {field} = ?, updated_at = ? WHERE telegram_id = ?",
            (value, datetime.now().isoformat(), telegram_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ خطأ في تحديث المستخدم: {e}")
        return False
    finally:
        conn.close()


def get_matching_users(job: dict) -> List[Dict]:
    """إيجاد المستخدمين المناسبين للوظيفة"""
    conn = get_connection()
    users = conn.execute("""
        SELECT * FROM users
        WHERE registration_complete = 1
        AND notifications_enabled = 1
        AND is_active = 1
    """).fetchall()
    conn.close()
    return [dict(u) for u in users]


def get_user_stats(telegram_id: int) -> Dict:
    conn = get_connection()
    apps = conn.execute(
        "SELECT COUNT(*) as total FROM applications WHERE user_telegram_id = ?",
        (telegram_id,)
    ).fetchone()
    notifications = conn.execute(
        "SELECT COUNT(*) as total FROM job_notifications WHERE user_telegram_id = ?",
        (telegram_id,)
    ).fetchone()
    conn.close()
    return {
        "total_applications": apps["total"] if apps else 0,
        "total_notifications": notifications["total"] if notifications else 0
    }


# ─────────────────────────────────────────
# عمليات الوظائف
# ─────────────────────────────────────────

def save_job(job_data: dict) -> Optional[int]:
    conn = get_connection()
    try:
        channel_msg_id = job_data.get("channel_message_id")

        # إذا كانت الوظيفة موجودة مسبقاً، أرجع id الصف الموجود
        if channel_msg_id:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE channel_message_id = ?",
                (channel_msg_id,)
            ).fetchone()
            if existing:
                conn.close()
                return existing["id"]

        cursor = conn.execute("""
            INSERT INTO jobs
            (channel_message_id, title, company, region, category, specialization,
             description, requirements, apply_link, apply_email, salary,
             work_type, deadline, source_channel, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            channel_msg_id,
            job_data.get("title", "وظيفة غير محددة"),
            job_data.get("company"),
            job_data.get("region"),
            job_data.get("category"),
            job_data.get("specialization"),
            job_data.get("description"),
            job_data.get("requirements"),
            job_data.get("apply_link"),
            job_data.get("apply_email"),
            job_data.get("salary"),
            job_data.get("work_type"),
            job_data.get("deadline"),
            job_data.get("source_channel"),
            job_data.get("raw_text")
        ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"❌ خطأ في حفظ الوظيفة: {e}")
        return None
    finally:
        conn.close()


def get_job(job_id: int) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_jobs(limit: int = 10) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE is_active = 1 ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_jobs_page(limit: int = 20, offset: int = 0, exclude_ids: Optional[List[int]] = None) -> List[Dict]:
    conn = get_connection()
    hidden = set(exclude_ids or [])
    rows = conn.execute("""
        SELECT * FROM jobs WHERE is_active = 1
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    jobs = [dict(row) for row in rows if dict(row)["id"] not in hidden]
    return jobs[offset:offset + limit]


def get_matching_jobs_page(user: dict, limit: int = 20, offset: int = 0, exclude_ids: Optional[List[int]] = None) -> List[Dict]:
    from utils.matching import score_match
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE is_active = 1 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    hidden = set(exclude_ids or [])
    matched = []
    for row in rows:
        job = dict(row)
        if job["id"] in hidden:
            continue
        score, reasons = score_match(user, job)
        if score >= 55:
            job["match_score"] = score
            job["match_reasons"] = reasons
            matched.append(job)
    return matched[offset:offset + limit]


def count_jobs(matching_user: Optional[dict] = None) -> int:
    if matching_user:
        from utils.matching import score_match
        conn = get_connection()
        rows = conn.execute("SELECT * FROM jobs WHERE is_active = 1").fetchall()
        conn.close()
        return sum(score_match(matching_user, dict(row))[0] >= 55 for row in rows)
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE is_active = 1"
    ).fetchone()[0]
    conn.close()
    return count


def save_application(
    user_id: int, job_id: int, method: str, status: str = "applied"
) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO applications
            (user_telegram_id, job_id, status, apply_method)
            VALUES (?, ?, ?, ?)
        """, (user_id, job_id, status, method))
        conn.commit()
        return cursor.rowcount == 1
    except Exception as e:
        print(f"❌ خطأ في حفظ التقديم: {e}")
        return False
    finally:
        conn.close()


def has_application(user_id: int, job_id: int) -> bool:
    conn = get_connection()
    row = conn.execute("""
        SELECT 1 FROM applications
        WHERE user_telegram_id = ? AND job_id = ?
        LIMIT 1
    """, (user_id, job_id)).fetchone()
    conn.close()
    return row is not None


def mark_notification_sent(user_id: int, job_id: int):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO job_notifications (user_telegram_id, job_id)
            VALUES (?, ?)
        """, (user_id, job_id))
        conn.commit()
    except:
        pass
    finally:
        conn.close()


def was_notified(user_id: int, job_id: int) -> bool:
    conn = get_connection()
    row = conn.execute("""
        SELECT 1 FROM job_notifications
        WHERE user_telegram_id = ? AND job_id = ?
    """, (user_id, job_id)).fetchone()
    conn.close()
    return row is not None


def create_purchase_order(
    telegram_id: int, order_type: str, amount: float, points: int
) -> Optional[int]:
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO purchase_orders (telegram_id, order_type, amount, points)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, order_type, amount, points))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_purchase_order(order_id: int) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM purchase_orders WHERE id = ?", (order_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_cv_campaign(
    telegram_id: int, categories: List[str], target_count: int, points_cost: int
) -> Optional[int]:
    """إنشاء حملة بطابور أهداف يمكن استكماله على دفعات."""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO cv_campaigns
            (telegram_id, categories_json, target_count, points_cost)
            VALUES (?, ?, ?, ?)
        """, (
            telegram_id, json.dumps(categories, ensure_ascii=False),
            target_count, points_cost
        ))
        campaign_id = cursor.lastrowid
        category_filter = [c for c in categories if c != "all"]
        rows = conn.execute("""
            SELECT id, company, apply_email, category
            FROM jobs
            WHERE apply_email IS NOT NULL AND apply_email != ''
            ORDER BY created_at DESC
        """).fetchall()
        seen = set()
        inserted = 0
        for row in rows:
            email = row["apply_email"]
            if inserted >= target_count or email in seen:
                continue
            if category_filter and not any(
                c in (row["category"] or "") for c in category_filter
            ):
                continue
            conn.execute("""
                INSERT OR IGNORE INTO campaign_targets
                (campaign_id, company, recipient_email, job_id)
                VALUES (?, ?, ?, ?)
            """, (campaign_id, row["company"], email, row["id"]))
            seen.add(email)
            inserted += 1
        conn.commit()
        return campaign_id
    finally:
        conn.close()


def get_user_campaigns(telegram_id: int, limit: int = 10) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM cv_campaigns
        WHERE telegram_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (telegram_id, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ─────────────────────────────────────────
# الخدمات والاشتراكات والنقاط
# ─────────────────────────────────────────

def get_plans() -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM plans WHERE is_active = 1 ORDER BY price ASC"
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["features"] = json.loads(item.get("features_json") or "[]")
        except json.JSONDecodeError:
            item["features"] = []
        result.append(item)
    return result


def get_plan(plan_code: str) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM plans WHERE code = ? AND is_active = 1", (plan_code,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    try:
        item["features"] = json.loads(item.get("features_json") or "[]")
    except json.JSONDecodeError:
        item["features"] = []
    return item


def ensure_default_subscription(telegram_id: int) -> Optional[Dict]:
    """إنشاء الاشتراك المجاني مرة واحدة للمستخدم الجديد."""
    conn = get_connection()
    try:
        active = conn.execute("""
            SELECT s.*, p.code AS plan_code, p.name AS plan_name
            FROM subscriptions s JOIN plans p ON p.id = s.plan_id
            WHERE s.telegram_id = ? AND s.status = 'active'
            ORDER BY s.id DESC LIMIT 1
        """, (telegram_id,)).fetchone()
        if active:
            return dict(active)
        plan = conn.execute(
            "SELECT * FROM plans WHERE code = 'free' AND is_active = 1"
        ).fetchone()
        if not plan:
            return None
        now = datetime.now().isoformat()
        cursor = conn.execute("""
            INSERT INTO subscriptions
            (telegram_id, plan_id, status, starts_at, points_balance,
             applications_remaining, companies_remaining)
            VALUES (?, ?, 'active', ?, ?, ?, ?)
        """, (
            telegram_id, plan["id"], now, plan["points"],
            plan["applications_limit"], plan["companies_limit"]
        ))
        conn.execute("""
            INSERT INTO point_transactions
            (telegram_id, amount, transaction_type, description, reference_type, reference_id)
            VALUES (?, ?, 'credit', ?, 'subscription', ?)
        """, (telegram_id, plan["points"], "رصيد البداية المجاني", str(cursor.lastrowid)))
        conn.commit()
        row = conn.execute("""
            SELECT s.*, p.code AS plan_code, p.name AS plan_name
            FROM subscriptions s JOIN plans p ON p.id = s.plan_id
            WHERE s.id = ?
        """, (cursor.lastrowid,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_subscription(telegram_id: int) -> Optional[Dict]:
    ensure_default_subscription(telegram_id)
    conn = get_connection()
    row = conn.execute("""
        SELECT s.*, p.code AS plan_code, p.name AS plan_name,
               p.description AS plan_description, p.billing_period_days
        FROM subscriptions s JOIN plans p ON p.id = s.plan_id
        WHERE s.telegram_id = ? AND s.status = 'active'
        ORDER BY s.id DESC LIMIT 1
    """, (telegram_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_point_transactions(telegram_id: int, limit: int = 10) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM point_transactions
        WHERE telegram_id = ?
        ORDER BY created_at DESC, id DESC LIMIT ?
    """, (telegram_id, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def request_subscription(telegram_id: int, plan_code: str) -> Optional[int]:
    plan = get_plan(plan_code)
    if not plan:
        return None
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO subscription_requests (telegram_id, plan_id)
            VALUES (?, ?)
        """, (telegram_id, plan["id"]))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_plan(plan_code: str, field: str, value) -> bool:
    """تحديث حقل آمن من حقول الباقة من لوحة المشرف."""
    allowed = {
        "price", "points", "applications_limit", "companies_limit",
        "description",
    }
    if field not in allowed:
        return False
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"UPDATE plans SET {field} = ? WHERE code = ? AND is_active = 1",
            (value, plan_code),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


def get_subscription_requests(status: str = "pending", limit: int = 30) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT r.id, r.telegram_id, r.status, r.created_at,
               p.code AS plan_code, p.name AS plan_name, p.price,
               p.points, p.applications_limit, p.companies_limit
        FROM subscription_requests r
        JOIN plans p ON p.id = r.plan_id
        WHERE r.status = ?
        ORDER BY r.created_at DESC, r.id DESC
        LIMIT ?
    """, (status, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def approve_subscription_request(request_id: int) -> Optional[Dict]:
    """اعتماد طلب اشتراك يدوياً بعد التحقق من الدفع."""
    conn = get_connection()
    try:
        request = conn.execute("""
            SELECT r.*, p.name AS plan_name, p.points,
                   p.applications_limit, p.companies_limit,
                   p.billing_period_days
            FROM subscription_requests r
            JOIN plans p ON p.id = r.plan_id
            WHERE r.id = ? AND r.status = 'pending'
        """, (request_id,)).fetchone()
        if not request:
            return None
        now = datetime.now()
        ends_at = None
        if request["billing_period_days"]:
            from datetime import timedelta
            ends_at = (now + timedelta(days=request["billing_period_days"])).isoformat()
        conn.execute(
            "UPDATE subscriptions SET status = 'replaced' "
            "WHERE telegram_id = ? AND status = 'active'",
            (request["telegram_id"],),
        )
        cursor = conn.execute("""
            INSERT INTO subscriptions
            (telegram_id, plan_id, status, starts_at, ends_at,
             points_balance, applications_remaining, companies_remaining)
            VALUES (?, ?, 'active', ?, ?, ?, ?, ?)
        """, (
            request["telegram_id"], request["plan_id"], now.isoformat(), ends_at,
            request["points"], request["applications_limit"],
            request["companies_limit"],
        ))
        conn.execute(
            "UPDATE subscription_requests SET status = 'approved' WHERE id = ?",
            (request_id,),
        )
        conn.execute("""
            INSERT INTO point_transactions
            (telegram_id, amount, transaction_type, description, reference_type, reference_id)
            VALUES (?, ?, 'credit', ?, 'subscription_request', ?)
        """, (
            request["telegram_id"], request["points"],
            f"تفعيل {request['plan_name']}", str(request_id),
        ))
        conn.commit()
        return {
            "telegram_id": request["telegram_id"],
            "plan_name": request["plan_name"],
            "subscription_id": cursor.lastrowid,
        }
    finally:
        conn.close()


def consume_subscription_usage(
    telegram_id: int, usage_type: str, reference_type: str, reference_id: str
) -> tuple[bool, str]:
    """خصم الاستخدام atomically، ولا يخصم شيئاً عند عدم كفاية الرصيد."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT s.*, p.name AS plan_name
            FROM subscriptions s JOIN plans p ON p.id = s.plan_id
            WHERE s.telegram_id = ? AND s.status = 'active'
            ORDER BY s.id DESC LIMIT 1
        """, (telegram_id,)).fetchone()
        if not row:
            return False, "لا يوجد اشتراك نشط"
        column = {
            "application": "applications_remaining",
            "company": "companies_remaining",
        }.get(usage_type, "points_balance")
        if row[column] <= 0 or row["points_balance"] <= 0:
            return False, "رصيدك غير كافٍ لهذه الخدمة"
        conn.execute(f"""
            UPDATE subscriptions
            SET points_balance = points_balance - 1,
                {column} = {column} - 1
            WHERE id = ? AND points_balance > 0 AND {column} > 0
        """, (row["id"],))
        if conn.total_changes != 1:
            return False, "تعذر خصم الرصيد، حاول مرة أخرى"
        conn.execute("""
            INSERT INTO point_transactions
            (telegram_id, amount, transaction_type, description, reference_type, reference_id)
            VALUES (?, -1, 'debit', ?, ?, ?)
        """, (telegram_id, f"استخدام خدمة {usage_type}", reference_type, str(reference_id)))
        conn.commit()
        return True, "تم خصم نقطة واحدة"
    finally:
        conn.close()


def restore_subscription_usage(
    telegram_id: int, usage_type: str, reference_type: str, reference_id: str
) -> bool:
    """إرجاع نقطة بعد فشل عملية حُجزت مسبقاً."""
    conn = get_connection()
    try:
        column = {
            "application": "applications_remaining",
            "company": "companies_remaining",
        }.get(usage_type, "points_balance")
        row = conn.execute("""
            SELECT id FROM subscriptions
            WHERE telegram_id = ? AND status = 'active'
            ORDER BY id DESC LIMIT 1
        """, (telegram_id,)).fetchone()
        if not row:
            return False
        conn.execute(f"""
            UPDATE subscriptions
            SET points_balance = points_balance + 1,
                {column} = {column} + 1
            WHERE id = ?
        """, (row["id"],))
        conn.execute("""
            INSERT INTO point_transactions
            (telegram_id, amount, transaction_type, description, reference_type, reference_id)
            VALUES (?, 1, 'refund', ?, ?, ?)
        """, (telegram_id, "إرجاع رصيد بعد فشل العملية", reference_type, str(reference_id)))
        conn.commit()
        return True
    finally:
        conn.close()


# ─────────────────────────────────────────
# الوظائف المخفية والمحفوظة
# ─────────────────────────────────────────

def _get_json_list(telegram_id: int, field: str) -> List[int]:
    user = get_user(telegram_id) or {}
    try:
        value = json.loads(user.get(field) or "[]")
        return [int(v) for v in value]
    except (ValueError, TypeError):
        return []


def get_hidden_jobs(telegram_id: int) -> List[int]:
    return _get_json_list(telegram_id, "hidden_jobs_json")


def hide_job(telegram_id: int, job_id: int) -> bool:
    ids = get_hidden_jobs(telegram_id)
    if job_id not in ids:
        ids.append(job_id)
    return update_user_field(telegram_id, "hidden_jobs_json", json.dumps(ids))


def unhide_job(telegram_id: int, job_id: int) -> bool:
    ids = [i for i in get_hidden_jobs(telegram_id) if i != job_id]
    return update_user_field(telegram_id, "hidden_jobs_json", json.dumps(ids))


def get_saved_jobs(telegram_id: int) -> List[int]:
    return _get_json_list(telegram_id, "saved_jobs_json")


def save_job_for_user(telegram_id: int, job_id: int) -> bool:
    ids = get_saved_jobs(telegram_id)
    if job_id in ids:
        return False
    ids.append(job_id)
    update_user_field(telegram_id, "saved_jobs_json", json.dumps(ids))
    return True


def get_jobs_by_ids(job_ids: List[int]) -> List[Dict]:
    if not job_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" for _ in job_ids)
    rows = conn.execute(
        f"SELECT * FROM jobs WHERE id IN ({placeholders}) ORDER BY created_at DESC",
        tuple(job_ids)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
