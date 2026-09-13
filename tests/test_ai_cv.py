import unittest
from unittest.mock import MagicMock, patch
from utils.ai_helper import (
    _sanitize_source_text,
    _extract_contacts_from_text,
    ai_generate_professional_cv,
)


class TestAICVGeneration(unittest.TestCase):

    def test_sanitize_source_text(self):
        raw_pdf_junk = (
            "ar-EG Canva Canva D:20240524121436+00'00' D:20240524121436+00'00' "
            "DAGGI6MHUdI,BAEiJ8AMK4g nawaf alshahrani 0542922316 hendyabd37@gmail.com "
            "Do/fގ a}}ӿlr8M7>]j\\J Adobe Identity Adobe Identity W uQ 6 eUt 6O "
            "a8}>MG 3, 5}~D? X2}R:Oӿ }/ Ja8G '3y"
        )
        clean = _sanitize_source_text(raw_pdf_junk)
        self.assertNotIn("Adobe Identity", clean)
        self.assertNotIn("Canva Canva", clean)
        self.assertIn("nawaf alshahrani", clean)
        self.assertIn("0542922316", clean)
        self.assertIn("hendyabd37@gmail.com", clean)

    def test_extract_contacts_from_text(self):
        text = "nawaf alshahrani\n0542922316\nhendyabd37@gmail.com\nlinkedin.com/in/nawaf-alshahrani"
        contacts = _extract_contacts_from_text(text)
        self.assertEqual(contacts.get("email"), "hendyabd37@gmail.com")
        self.assertEqual(contacts.get("phone"), "0542922316")
        self.assertEqual(contacts.get("name"), "nawaf alshahrani")
        self.assertIn("linkedin.com/in/nawaf-alshahrani", contacts.get("linkedin_url", ""))

    def test_fallback_cv_generation(self):
        user = {
            "full_name_ar": "",
            "email": "",
            "phone": "",
            "region": "الرياض",
            "category": "تقنية المعلومات",
            "specialization": "برمجة بايثون",
            "education_level": "بكالوريوس",
            "experience_level": "3 سنوات",
            "work_type": "دوام كامل",
        }
        source_text = (
            "ar-EG Canva Canva D:20240524121436+00'00' "
            "nawaf alshahrani 0542922316 hendyabd37@gmail.com Adobe Identity"
        )
        cv = ai_generate_professional_cv(user, source_text)

        # Check extracted info was populated
        self.assertIn("nawaf alshahrani", cv)
        self.assertIn("0542922316", cv)
        self.assertIn("hendyabd37@gmail.com", cv)

        # Check section headers
        self.assertIn("المنطقة: الرياض", cv)
        self.assertIn("الملخص المهني", cv)
        self.assertIn("المهارات والكفاءات الرئيسية", cv)
        self.assertIn("الخبرات والمهام العملية", cv)
        self.assertIn("التعليم والمؤهلات", cv)

        # Ensure PDF metadata noise is absent
        self.assertNotIn("Adobe Identity", cv)
        self.assertNotIn("Canva Canva", cv)

    @patch("utils.ai_helper.get_groq_client")
    def test_ai_cv_generation_with_groq(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="==================================================\nنواف الشهراني\nسيرة ذاتية احترافية بـ AI\n=================================================="))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        user = {"full_name_ar": "نواف الشهراني", "category": "تقنية المعلومات"}
        cv = ai_generate_professional_cv(user, "خبرة 3 سنوات في تطوير البرمجيات")
        self.assertIn("نواف الشهراني", cv)
        self.assertIn("سيرة ذاتية احترافية", cv)


if __name__ == "__main__":
    unittest.main()
