"""SecurityAdminService 純函式 TDD — 統一 security score SSOT（取代檔內 3 套漂移公式）。"""
from app.services.system.security_admin_service import (
    compute_security_score,
    score_to_grade,
)


class TestComputeSecurityScore:
    def test_no_issues_is_100(self):
        assert compute_security_score(0, 0, 0, 0) == 100

    def test_weighted_deduction(self):
        # 1 critical(25) + 2 high(20) + 1 medium(3) + 5 low(5) = 53 扣 → 47
        assert compute_security_score(1, 2, 1, 5) == 100 - 25 - 20 - 3 - 5

    def test_floor_at_zero(self):
        assert compute_security_score(10, 0, 0, 0) == 0  # 250 扣 → 下限 0

    def test_low_default_zero(self):
        # low 省略時預設 0（相容舊 notifications 呼叫，但 SSOT 建議帶入）
        assert compute_security_score(0, 1, 0) == 90


class TestScoreToGrade:
    def test_grades(self):
        assert score_to_grade(95) == ("A", "優良")
        assert score_to_grade(90) == ("A", "優良")
        assert score_to_grade(70) == ("B", "尚可")
        assert score_to_grade(50) == ("C", "需改善")
        assert score_to_grade(49) == ("D", "危險")
        assert score_to_grade(0) == ("D", "危險")
