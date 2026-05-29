"""ADR-0046 Phase 4 LINE 通報格式 unit tests (L51, 2026-05-28)

升 ADR-0046 L1 → L2 配套：對 `_format_recommendation_line` 純函數鎖定。

LINE 訊息格式為 admin 直接收到的字串，任何欄位順序/icon/URL 變更
都會影響業務體驗。本 test 鎖定既有格式不漏一段。
"""
import pytest

from app.services.tender.business_recommendation import (
    _format_recommendation_line,
    DEFAULT_BUDGET_MIN,
    DEFAULT_DAYS_BACK,
    MAX_RECOMMEND_PER_RUN,
)


# =============================================================================
# Constants — 防 silent threshold drift
# =============================================================================

def test_default_budget_min_is_1m():
    """預算門檻 100 萬不可悄悄改（業務面影響大）"""
    assert DEFAULT_BUDGET_MIN == 1_000_000


def test_default_days_back_is_1():
    """每日跑只看近 1 日新增（避刷屏）"""
    assert DEFAULT_DAYS_BACK == 1


def test_max_recommend_per_run_is_20():
    """每次最多推 20 個案件（避 LINE 刷屏）"""
    assert MAX_RECOMMEND_PER_RUN == 20


# =============================================================================
# Format: 必要欄位 + 結構
# =============================================================================

def _sample_rec(**overrides):
    """測試用標準 recommendation dict"""
    base = {
        "unit_id": "A.15.3.2",
        "job_number": "115-703",
        "title": "道路鋪面工程",
        "unit_name": "苗栗縣公館鄉公所",
        "budget": 1_500_000,
        "announce_date": "2026-05-28",
        "agency_match_count": 3,
    }
    base.update(overrides)
    return base


def test_format_contains_all_emoji_icons():
    """5 個 emoji icon 必須齊全（業務識別度）"""
    msg = _format_recommendation_line(_sample_rec())
    assert "🎯" in msg  # 業務推薦標案標題
    assert "📋" in msg  # 案號 + 標題
    assert "🏛" in msg  # 機關
    assert "💰" in msg  # 預算
    assert "📅" in msg  # 公告
    assert "🔗" in msg  # 連結


def test_format_contains_job_number_and_title():
    msg = _format_recommendation_line(_sample_rec())
    assert "[115-703]" in msg
    assert "道路鋪面工程" in msg


def test_format_contains_agency_name():
    msg = _format_recommendation_line(_sample_rec())
    assert "苗栗縣公館鄉公所" in msg


def test_format_budget_thousand_separator():
    """預算金額千分位逗號 ($1,500,000)"""
    msg = _format_recommendation_line(_sample_rec(budget=1_500_000))
    assert "$1,500,000" in msg


def test_format_budget_missing():
    """budget=None or 0 → 顯示「（預算未公開）」"""
    msg = _format_recommendation_line(_sample_rec(budget=0))
    assert "（預算未公開）" in msg


def test_format_announce_date():
    msg = _format_recommendation_line(_sample_rec(announce_date="2026-05-28"))
    assert "2026-05-28" in msg


def test_format_detail_url_uses_missive_subdomain():
    """連結 URL 必須是 missive.cksurvey.tw (ADR-0016 public subdomain)"""
    msg = _format_recommendation_line(_sample_rec())
    assert "https://missive.cksurvey.tw/tender/pcc/" in msg
    assert "A.15.3.2/115-703" in msg


# =============================================================================
# 合作機關計數顯示
# =============================================================================

def test_format_cooperation_count_above_1():
    """agency_match_count > 1 → 顯示「（合作 N 次）」"""
    msg = _format_recommendation_line(_sample_rec(agency_match_count=3))
    assert "合作 3 次" in msg


def test_format_cooperation_count_exactly_1():
    """count = 1 → 顯示「（合作機關）」(不出現「合作 1 次」避歧義)"""
    msg = _format_recommendation_line(_sample_rec(agency_match_count=1))
    assert "（合作機關）" in msg
    assert "合作 1 次" not in msg


def test_format_cooperation_count_zero_defaults_to_machine_keyword():
    """count = 0 也顯示「（合作機關）」(SQL 已 filter 出合作機關才進來)"""
    msg = _format_recommendation_line(_sample_rec(agency_match_count=0))
    assert "（合作機關）" in msg


# =============================================================================
# 邊角組合
# =============================================================================

@pytest.mark.parametrize("budget,expected_str", [
    (10_000_000, "$10,000,000"),  # 千萬
    (1_000, "$1,000"),  # 千
    (None, "（預算未公開）"),
    (0, "（預算未公開）"),
])
def test_format_budget_variants(budget, expected_str):
    msg = _format_recommendation_line(_sample_rec(budget=budget))
    assert expected_str in msg


def test_format_special_chars_in_title():
    """title 含特殊字（&/「」/空白）不應破壞 LINE 訊息"""
    msg = _format_recommendation_line(_sample_rec(
        title="A&B「特殊」採購案 (含空白)",
    ))
    assert "A&B「特殊」採購案 (含空白)" in msg
