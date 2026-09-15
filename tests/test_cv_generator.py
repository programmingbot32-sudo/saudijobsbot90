import re
from utils.ai_helper import ai_generate_professional_cv, ai_generate_english_cv
from utils.pdf_generator import generate_pdf_cv, parse_cv_text_to_sections

def test_multiline_cv_and_english_translation():
    user = {
        'full_name_ar': 'محمد',
        'full_name_en': 'Mohamed',
        'phone': '077899'
    }
    source = (
        "الاسم: Mohamed\n"
        "الجوال: 077899\n"
        "التعليم: بكالوريوس تجارة\nمجستير بالمحاسبة\n"
        "المهارات: برمجة بوتات\nتصميم مواقع\n"
        "الخبرات: شركة العلمين\nشركة برمجة\n"
        "اللغات: اللغة العربية\nاللغة الانجليزية جيد"
    )

    cv_ar = ai_generate_professional_cv(user, source)
    cv_en = ai_generate_english_cv(user, source)

    # Check that multiline education, skills, experience, languages are present in AR
    assert "بكالوريوس تجارة" in cv_ar
    assert "مجستير بالمحاسبة" in cv_ar
    assert "برمجة بوتات" in cv_ar
    assert "تصميم مواقع" in cv_ar
    assert "شركة العلمين" in cv_ar
    assert "شركة برمجة" in cv_ar

    # Check that multiline education, skills, experience, languages are translated in EN
    assert "Commerce" in cv_en
    assert "Accounting" in cv_en
    assert "Telegram & AI Bots" in cv_en or "Bots" in cv_en
    assert "Web Design" in cv_en
    assert "Al-Alamein" in cv_en
    assert "Company" in cv_en

    # Ensure no raw Arabic script remains in the English CV
    assert not bool(re.search(r'[\u0600-\u06FF]', cv_en))

def test_medical_and_skills_english_translation():
    user = {
        'full_name_ar': 'محمد علي',
        'full_name_en': 'Mohamed Ali',
        'phone': '055896433',
        'email': 'Ltfy37943@gmail.com'
    }
    source = (
        "الاسم: Mohamed Ali\n"
        "الجوال: 055896433\n"
        "التعليم: بكالوريوس الطب\nدكتوارة باطنة عامة\n"
        "المهارات: التعلم والابتكار\n"
        "الخبرات: خبير برمجة وتصاميم\nادارة المواقع\n"
        "اللغات: لغة عربية\nانجليزي متوسط"
    )

    cv_en = ai_generate_english_cv(user, source)

    assert "Bachelor of Medicine" in cv_en
    assert "Doctorate / Ph.D. in General Internal Medicine" in cv_en or "Internal Medicine" in cv_en
    assert "Learning & Innovation" in cv_en
    assert "Expert in Software & Web Design" in cv_en or "Programming" in cv_en
    assert "Website Management" in cv_en
    assert "Arabic (Native)" in cv_en
    assert "English (Intermediate)" in cv_en

    assert not bool(re.search(r'[\u0600-\u06FF]', cv_en))

    cv_ar = ai_generate_professional_cv(user, source)
    # Test PDF generation for all designs
    for d in (1, 2, 3):
        pdf_ar = generate_pdf_cv(user, cv_ar, design_id=d, lang='ar')
        pdf_en = generate_pdf_cv(user, cv_en, design_id=d, lang='en')
        assert len(pdf_ar) > 1000
        assert len(pdf_en) > 1000
