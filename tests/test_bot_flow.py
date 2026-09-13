import pytest
import os
from unittest.mock import AsyncMock, MagicMock

from database.db import save_job, get_job, save_user, get_user
from utils.ai_helper import ai_suggest_improvements, ai_generate_professional_cv
from keyboards.keyboards import get_ai_cv_collect_keyboard

@pytest.fixture(autouse=True)
def setup_db_path(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test.db")
    from database.db import init_db
    init_db()

def test_save_job_no_filler():
    job_id = save_job({})
    job = get_job(job_id)
    assert job["title"] != "وظيفة غير محددة"
    assert "غير محدد" not in job["title"]

def test_ai_helper_no_filler():
    user = {"full_name_ar": "محمد", "email": "test@example.com"}
    suggestion = ai_suggest_improvements(user)
    assert "غير محدد" not in suggestion
    assert "غير محددة" not in suggestion

    cv = ai_generate_professional_cv(user, "خبرة 3 سنوات في البرمجة")
    assert "غير محدد" not in cv
    assert "غير محددة" not in cv

def test_ai_cv_collect_keyboard_no_premature_design():
    keyboard = get_ai_cv_collect_keyboard()
    button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
    assert not any("اختيار تصميم" in text for text in button_texts)
    assert any("انتهيت" in text for text in button_texts)
