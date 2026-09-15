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

    # Test PDF generation for all designs
    for d in (1, 2, 3):
        pdf_ar = generate_pdf_cv(user, cv_ar, design_id=d, lang='ar')
        pdf_en = generate_pdf_cv(user, cv_en, design_id=d, lang='en')
        assert len(pdf_ar) > 1000
        assert len(pdf_en) > 1000
