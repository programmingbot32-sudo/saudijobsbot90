"""
مساعد الذكاء الاصطناعي - Groq AI Integration
يستخدم Groq للتحليل الذكي للوظائف والمطابقة وتوليد خطابات التقديم
"""

import os
import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL = "llama-3.1-8b-instant"


def get_groq_client():
    """إنشاء عميل Groq"""
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"❌ فشل إنشاء عميل Groq: {e}")
        return None


def ai_parse_job(text: str) -> Optional[dict]:
    """
    تحليل ذكي لنص إعلان الوظيفة باستخدام Groq
    يستخرج: المسمى، الشركة، المنطقة، التخصص، الراتب، الموعد النهائي
    """
    client = get_groq_client()
    if not client:
        return None

    prompt = f"""أنت محلل وظائف خبير في السوق السعودي. حلل النص التالي واستخرج معلومات الوظيفة بدقة.

النص:
\"\"\"
{text[:2000]}
\"\"\"

أرجع JSON فقط بهذا الشكل (لا تضف أي نص آخر):
{{
  "title": "المسمى الوظيفي بالعربية",
  "company": "اسم الشركة أو المؤسسة",
  "region": "المدينة أو المنطقة في السعودية (مثل: الرياض، جدة، الدمام، عن بُعد)",
  "category": "التخصص الرئيسي (مثل: تقنية المعلومات، الهندسة، الصحة، الإدارة، التعليم)",
  "specialization": "التخصص الدقيق (مثل: مطور بايثون، محاسب، ممرض)",
  "salary": "الراتب أو النطاق المذكور أو null",
  "work_type": "نوع الدوام: حضوري أو عن بُعد أو هجين أو دوام جزئي",
  "deadline": "الموعد النهائي للتقديم أو null",
  "requirements": "أهم متطلبات الوظيفة في جملة أو جملتين",
  "is_job_post": true
}}

إذا لم يكن النص إعلان وظيفة، أرجع: {{"is_job_post": false}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()

        # استخراج JSON من الرد
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        data = json.loads(raw)
        return data if data.get("is_job_post", True) else None

    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ فشل تحليل JSON من Groq: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ خطأ في Groq AI parse: {e}")
        return None


def ai_match_score(user: dict, job: dict) -> int:
    """
    حساب درجة تطابق ذكية بين المستخدم والوظيفة (0-100)
    يأخذ بعين الاعتبار: التخصص، الخبرة، المنطقة، نوع الدوام، الراتب
    """
    client = get_groq_client()
    if not client:
        return _basic_match_score(user, job)

    user_profile = f"""
- التخصص: {user.get('category', '')} / {user.get('specialization', '')}
- الخبرة: {user.get('experience_level', '')}
- المنطقة: {user.get('region', '')}
- المؤهل: {user.get('education_level', '')}
- نوع الدوام المفضل: {user.get('work_type', '')}
- الراتب المتوقع: {user.get('salary_range', '')}
""".strip()

    job_info = f"""
- المسمى: {job.get('title', '')}
- الشركة: {job.get('company', '')}
- التخصص: {job.get('category', '')} / {job.get('specialization', '')}
- المنطقة: {job.get('region', '')}
- الراتب: {job.get('salary', '')}
- نوع الدوام: {job.get('work_type', '')}
- المتطلبات: {job.get('requirements', '')}
""".strip()

    prompt = f"""قيّم مدى تطابق هذا المرشح مع هذه الوظيفة في السوق السعودي.

ملف المرشح:
{user_profile}

تفاصيل الوظيفة:
{job_info}

أرجع رقماً فقط من 0 إلى 100 يمثل نسبة التطابق. لا تضف أي نص آخر."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
        )
        score_text = response.choices[0].message.content.strip()
        score = int(''.join(filter(str.isdigit, score_text))[:3])
        return min(100, max(0, score))
    except Exception as e:
        logger.warning(f"⚠️ فشل حساب درجة التطابق: {e}")
        return _basic_match_score(user, job)


def _basic_match_score(user: dict, job: dict) -> int:
    """حساب درجة تطابق بسيطة بدون AI"""
    score = 50
    if user.get("category") and user.get("category") == job.get("category"):
        score += 30
    if user.get("region") == job.get("region"):
        score += 15
    elif user.get("region") in ("أي منطقة", "عن بُعد (Remote)"):
        score += 5
    if user.get("work_type") and job.get("work_type") and \
       user.get("work_type") in (job.get("work_type", ""), "🔄 أي نوع"):
        score += 5
    return min(100, score)


def ai_generate_cover_letter(user: dict, job: dict) -> str:
    """
    توليد خطاب تقديم مخصص باستخدام Groq AI
    """
    client = get_groq_client()
    if not client:
        return _default_cover_letter(user, job)

    prompt = f"""اكتب خطاب تقديم وظيفة احترافي باللغة العربية للمعلومات التالية.

معلومات المتقدم:
- الاسم: {user.get('full_name_ar', 'المتقدم')}
- التخصص: {user.get('specialization', user.get('category', ''))}
- الخبرة: {user.get('experience_level', '')}
- المؤهل: {user.get('education_level', '')}

تفاصيل الوظيفة:
- المسمى: {job.get('title', 'الوظيفة')}
- الشركة: {job.get('company', 'الشركة')}
- المنطقة: {job.get('region', '')}
- المتطلبات: {job.get('requirements', '')}

اكتب خطاباً قصيراً ومحترفاً (3-4 فقرات) يبرز:
1. سبب التقديم واهتمام المتقدم بالوظيفة
2. أبرز مؤهلاته وخبراته المرتبطة
3. دعوة للمقابلة

الخطاب يجب أن يبدأ بـ "السلام عليكم ورحمة الله وبركاته" وينتهي بالتوقيع."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ خطأ في توليد خطاب التقديم: {e}")
        return _default_cover_letter(user, job)


def _default_cover_letter(user: dict, job: dict) -> str:
    """خطاب تقديم افتراضي بدون AI"""
    name = user.get('full_name_ar') or user.get('full_name_en') or 'المتقدم'
    job_title = job.get('title', 'الوظيفة')
    company = job.get('company', 'الشركة')
    spec = user.get('specialization') or user.get('category', '')
    exp = user.get('experience_level', '')
    edu = user.get('education_level', '')

    return f"""السلام عليكم ورحمة الله وبركاته،

أتقدم بطلبي للانضمام إلى فريقكم المتميز في وظيفة {job_title} بـ{company}.

أنا {name}، أحمل {edu} في مجال {spec}، ولدي {exp} من الخبرة العملية. أؤمن بأن مؤهلاتي وخبراتي تتوافق مع متطلبات هذه الوظيفة، وأنا متحمس للمساهمة في نجاح مؤسستكم.

أرجو مراجعة سيرتي الذاتية المرفقة، وأنا مستعد لأي مقابلة في الوقت المناسب لكم.

مع خالص التقدير والاحترام،
{name}"""


def ai_suggest_improvements(user: dict) -> str:
    """
    اقتراحات ذكية لتحسين الملف الشخصي
    """
    client = get_groq_client()
    if not client:
        return "💡 أكمل ملفك الشخصي وارفع سيرتك الذاتية لزيادة فرصك!"

    profile_completeness = []
    if not user.get("cv_file_id"):
        profile_completeness.append("لا توجد سيرة ذاتية")
    if not user.get("linkedin_url"):
        profile_completeness.append("لا يوجد رابط LinkedIn")
    if not user.get("email"):
        profile_completeness.append("لا يوجد بريد إلكتروني")

    if not profile_completeness:
        return "✅ ملفك الشخصي مكتمل! استمر في التقديم على الوظائف."

    prompt = f"""باحث وظيفي في السعودية، تخصصه {user.get('specialization', user.get('category', 'غير محدد'))}, 
خبرته {user.get('experience_level', 'غير محددة')}.

نواقص في ملفه: {', '.join(profile_completeness)}

اكتب نصيحة واحدة قصيرة (جملة أو جملتين) بالعربية تشجعه على إكمال ملفه وتوضح فائدة ذلك."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150,
        )
        return "💡 " + response.choices[0].message.content.strip()
    except Exception:
        return "💡 أكمل ملفك الشخصي وارفع سيرتك الذاتية لزيادة فرصك!"


def _sanitize_source_text(text: str) -> str:
    """تطهير وتنقية النص من مخلفات ملفات PDF والرموز وبيانات Meta غير المفهومة."""
    if not text:
        return ""

    noise_patterns = [
        r'Adobe\s+Identity',
        r'Adobe\s+UCS',
        r'Canva\s+Canva',
        r'D:\d{14}[+\-\d\']+',
        r'DAGGI[A-Za-z0-9,]+',
        r'\/B\s+1\s+\*\\q',
    ]
    cleaned = text
    for pat in noise_patterns:
        cleaned = re.sub(pat, ' ', cleaned, flags=re.IGNORECASE)

    lines = cleaned.splitlines()
    filtered_lines = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        printable_count = len(re.findall(r'[\u0600-\u06FFa-zA-Z0-9\s.,@\-:\/+=]', line_str))
        if len(line_str) > 5 and (printable_count / len(line_str)) < 0.5:
            continue
        if any(term in line_str.lower() for term in ['adobe identity', 'adobe ucs', 'canva d:']):
            continue
        filtered_lines.append(line_str)

    result = "\n".join(filtered_lines)
    result = re.sub(r'[ \t]+', ' ', result)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


def _extract_contacts_from_text(text: str) -> dict:
    """استخراج بيانات التواصل من النص المرفق إذا لم تكن موجودة في ملف المستخدم."""
    extracted = {}
    if not text:
        return extracted

    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match:
        extracted['email'] = email_match.group(0)

    phone_match = re.search(r'(?:05|\+?9665)\d{8}', text)
    if phone_match:
        extracted['phone'] = phone_match.group(0)

    linkedin_match = re.search(r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/[a-zA-Z0-9%_\-]+', text, re.IGNORECASE)
    if linkedin_match:
        extracted['linkedin_url'] = linkedin_match.group(0)

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:8]:
        if re.match(r'^[A-Za-z\s]{3,30}$', line) and not any(kw in line.lower() for kw in ['adobe', 'canva', 'curriculum', 'resume', 'cv']):
            extracted['name'] = line
            break
        elif re.match(r'^[\u0600-\u06FF\s]{5,30}$', line) and not any(kw in line for kw in ['سيرة', 'ذاتية', 'ملف', 'خبرات', 'تضمين']):
            extracted['name'] = line
            break

    return extracted


def _generate_fallback_cv(
    name: str,
    email: str,
    phone: str,
    region: str,
    category: str,
    specialization: str,
    education: str,
    experience: str,
    work_type: str,
    linkedin: str,
    clean_source: str,
) -> str:
    """توليد سيرة ذاتية احترافية متنسقة عند عدم توفر خدمة الذكاء الاصطناعي."""
    job_title = specialization if specialization != 'غير محدد' else (category if category != 'غير محدد' else 'متخصص مهني')

    if clean_source and len(clean_source) > 10:
        extracted_lines = [l.strip() for l in clean_source.splitlines() if l.strip() and len(l.strip()) > 5]
        skills_experience_block = "\n".join([f"• {line}" for line in extracted_lines[:10]])
    else:
        skills_experience_block = (
            "• إتقان المهارات التخصصية والمهنية ذات الصلة بالمجال.\n"
            "• القدرة على العمل الجماعي والتواصل الفعال وتأدية المهام بدقة.\n"
            "• الالتزام بمعايير الجودة والعمل في بيئة ديناميكية."
        )

    return f"""==================================================
                 {name}
         {job_title}
==================================================
📱 الجوال: {phone} | ✉️ البريد: {email}
📍 المنطقة: {region} | 🔗 لينكدإن: {linkedin}
💼 نوع الدوام: {work_type} | 🎯 سنوات الخبرة: {experience}

━━━━━━ 📄 الملخص المهني ━━━━━━
{job_title} طموح ومتمكن في مجال {category}، يمتلك خبرة قدرها ({experience}) ويتميز بالمهارات العملية والتعليمية المقترنة بالمؤهل ({education}). يسعى للانضمام إلى بيئة عمل احترافية في السوق السعودي لتحقيق أهداف المؤسسة وتطوير مساره المهني.

━━━━━━ 🛠️ المهارات والكفاءات الرئيسية ━━━━━━
• المهارات التخصصية: الكفاءة في مجال {specialization if specialization != 'غير محدد' else category}.
• المهارات الشخصية: التواصل الفعال، حل المشكلات، إدارة الوقت، والعمل بروح الفريق.
• الأدوات والتقنيات: استخدام البرامج والأدوات الحديثة الخاصة بالتخصص.

━━━━━━ 💼 الخبرات والمهام العملية ━━━━━━
{skills_experience_block}

━━━━━━ 🎓 التعليم والمؤهلات ━━━━━━
• المؤهل العلمي: {education}
• التخصص: {specialization if specialization != 'غير محدد' else category}

━━━━━━ 📜 الشهادات والدورات التدريبية ━━━━━━
• دورات تطويرية وتخصصية في مجال {category} (يُضاف التفاصيل لاحقاً).

━━━━━━ 🌐 اللغات والروابط ━━━━━━
• اللغة العربية: اللغة الأم (إتقان تام).
• اللغة الإنجليزية: مستوى جيد جداً / مهني.
• رابط الأعمال / LinkedIn: {linkedin}
==================================================
💡 تنبيه: يمكنك تحديث بياناتك أو إرسال تفاصيل إضافية لتحديث السيرة الذاتية تلقائياً.
""".strip()


def ai_generate_professional_cv(user: dict, source_text: str) -> str:
    """إنشاء سيرة ذاتية عربية احترافية بتنسيق عصري ومنظم."""
    clean_source = _sanitize_source_text(source_text)
    extracted = _extract_contacts_from_text(clean_source or source_text)

    name = (
        user.get('full_name_ar') or
        user.get('full_name_en') or
        extracted.get('name') or
        'غير محدد'
    )
    email = user.get('email') or extracted.get('email') or 'غير محدد'
    phone = user.get('phone') or extracted.get('phone') or 'غير محدد'
    region = user.get('region') or 'السعودية'
    category = user.get('category') or 'غير محدد'
    specialization = user.get('specialization') or 'غير محدد'
    education = user.get('education_level') or 'غير محدد'
    experience = user.get('experience_level') or 'غير محددة'
    work_type = user.get('work_type') or 'غير محدد'
    linkedin = user.get('linkedin_url') or extracted.get('linkedin_url') or 'غير مضاف'

    profile = f"""
- الاسم: {name}
- البريد الإلكتروني: {email}
- رقم الجوال: {phone}
- المنطقة / المدينة: {region}
- المجال الوظيفي: {category}
- التخصص الدقيق: {specialization}
- المستوى التعليمي: {education}
- سنوات الخبرة: {experience}
- نوع الدوام المفضل: {work_type}
- رابط لينكدإن: {linkedin}
""".strip()

    client = get_groq_client()
    if client:
        prompt = f"""أنت خبير واستشاري أول في بناء السير الذاتية وصياغتها لسوق العمل السعودي ومطابقة أنظمة ATS.
المطلوب: صياغة وتصميم سيرة ذاتية احترافية وعصرية باللغة العربية بناءً على بيانات المرشح والمعلومات المرفقة.

تعليمات التنسيق والصياغة الهامة:
1. صمم الهيكل بتنسيق بصري عصري وواضح يسهل قراءته بالعين ومناسب لأنظمة الفرز الآلي ATS.
2. استخدم فاصل الأقسام الجذاب بأسلوب نقي مثل (==================================================) و(━━━━━━ 📄 العنوان ━━━━━━).
3. تجنب تماماً طباعة أي رموز غريبة أو مخلفات ملفات PDF أو نصوص البرمجة أو كلمات مثل Adobe / Canva / Identity.
4. صغ ملخصاً مهنياً قوياً وموجزاً (3-4 أسطر) يعكس تخصص المرشح وشغفه وسعيه للنمو في السوق السعودي.
5. استخرج المهارات والخبرات بدقة من المعلومات المرفقة ورتبها في نقاط مركزة ومبوبة (مهارات تقنية، مهارات شخصية، أدوات وبرامج).
6. نسق الخبرات العملية بوضوح مع المسمى الوظيفي والجهة والمهام الأساسية.
7. لا تخترع أرقاماً أو شهادات غير موجودة؛ إذا كانت هناك معلومة ناقصة استخدم "يُضاف لاحقاً" أو استنتجها بلباقة دون اختلاق.

بيانات المرشح:
{profile}

المعلومات المرفقة والنصوص المستخرجة (نقية):
{clean_source[:12000] if clean_source else "لا توجد ملفات مرفقة إضافية."}

أخرج النص النهائي للسيرة الذاتية فقط بالترتيب التنسيقي التالي:
1. الترويسة الرئيسية (الاسم واللقب المهني) وبيانات التواصل مباشرة أسفلها.
2. الملخص المهني (Executive Summary).
3. المهارات والكفاءات (Skills & Core Competencies).
4. الخبرات العملية (Work Experience).
5. المؤهلات التعليمية (Education).
6. الشهادات والدورات التدريبية (Certifications & Training).
7. اللغات والروابط (Languages & Links).
"""
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2200,
            )
            result = response.choices[0].message.content.strip()
            if result and len(result) > 100:
                return result
        except Exception as exc:
            logger.warning("فشل إنشاء السيرة بالذكاء الاصطناعي: %s", exc)

    return _generate_fallback_cv(
        name=name,
        email=email,
        phone=phone,
        region=region,
        category=category,
        specialization=specialization,
        education=education,
        experience=experience,
        work_type=work_type,
        linkedin=linkedin,
        clean_source=clean_source,
    )
