"""
أدوات الحماية والتنسيق الآمن.

1) تهريب رموز Markdown حتى لا تنكسر الرسائل بسبب أسماء المستخدمين.
2) تشفير كلمات مرور التطبيقات (App Passwords) قبل حفظها في قاعدة البيانات.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_MD_SPECIALS = ("_", "*", "`", "[", "]")
_ENC_PREFIX = "enc::v1::"


# ─────────────────────────────────────────
# Markdown آمن
# ─────────────────────────────────────────

def escape_md(text: Optional[str]) -> str:
    """تهريب رموز Markdown (النسخة الكلاسيكية) في نص قادم من المستخدم."""
    if not text:
        return ""
    safe = str(text)
    for char in _MD_SPECIALS:
        safe = safe.replace(char, "\\" + char)
    return safe


def mask_email(email: Optional[str]) -> str:
    """إظهار الإيميل جزئياً في الواجهات: mo***@gmail.com"""
    if not email or "@" not in email:
        return "غير محدد"
    name, domain = email.split("@", 1)
    visible = name[:2] if len(name) > 2 else name[:1]
    return f"{visible}***@{domain}"


# ─────────────────────────────────────────
# تشفير الأسرار المحفوظة
# ─────────────────────────────────────────

def _fernet():
    """مفتاح التشفير: ENCRYPTION_KEY وإلا يُشتق من BOT_TOKEN."""
    try:
        from cryptography.fernet import Fernet
    except Exception:  # المكتبة غير مثبتة
        return None

    raw = os.environ.get("ENCRYPTION_KEY", "").strip()
    if raw:
        try:
            return Fernet(raw.encode())
        except Exception:
            logger.warning("ENCRYPTION_KEY غير صالح، سيتم اشتقاق مفتاح من BOT_TOKEN")

    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        return None
    digest = hashlib.sha256(f"saudi-jobs-bot::{token}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    """تشفير سر قبل الحفظ. يعيد النص كما هو إذا تعذّر التشفير."""
    if not value:
        return value
    fernet = _fernet()
    if not fernet:
        logger.warning("⚠️ التشفير غير متاح، سيُحفظ السر كنص عادي")
        return value
    return _ENC_PREFIX + fernet.encrypt(value.encode()).decode()


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    """فك تشفير سر محفوظ، مع دعم القيم القديمة غير المشفرة."""
    if not value:
        return value
    if not value.startswith(_ENC_PREFIX):
        return value  # قيمة قديمة محفوظة قبل تفعيل التشفير
    fernet = _fernet()
    if not fernet:
        logger.error("❌ تعذّر فك تشفير السر: مفتاح التشفير غير متاح")
        return None
    try:
        return fernet.decrypt(value[len(_ENC_PREFIX):].encode()).decode()
    except Exception:
        logger.error("❌ تعذّر فك تشفير السر: المفتاح لا يطابق البيانات المحفوظة")
        return None
