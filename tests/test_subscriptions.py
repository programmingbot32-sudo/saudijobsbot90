import pytest
import os
import sqlite3
from database.db import init_db, get_plans, get_plan
from services.subscriptions import plans_text, plan_features

def test_plan_points_and_limits():
    init_db()
    plans = get_plans()
    assert len(plans) >= 4
    for plan in plans:
        # Check that total points equal applications_limit + companies_limit
        assert plan["points"] == plan["applications_limit"] + plan["companies_limit"]

def test_no_duplicate_descriptions_or_features():
    init_db()
    plans = get_plans()
    text = plans_text(plans)

    # Check starter plan formatting specifically
    starter = get_plan("starter")
    assert starter["points"] == 600
    assert starter["applications_limit"] == 100
    assert starter["companies_limit"] == 500

    features = plan_features(starter)
    # Features should not contain duplicate stat lines like "50 نقطة" or "10 تقديمات تلقائية"
    assert "50 نقطة" not in features
    assert "10 تقديمات تلقائية" not in features
