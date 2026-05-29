"""ADR-0046 enrichment HIGH guard unit tests (L51, 2026-05-28)

升 ADR-0046 L1 → L2 配套：對 `_passes_high_guard` 五重 guard 邊角組合鎖定。

Live apply (5/28) 揭發既有 trigram false positive 場景，本 test 確保未來
重構不漏一條 guard：
- title length < 12 → reject (short string trigram 高 sim 風險)
- agency similarity < 0.85 → reject
- date proximity < 1.0 → reject
- title 非 exact match → reject (即使 length ≥ 20 + 高 sim 也擋)
- 已驗證 false positive case：
  * 「30吋閘閥」vs「30吋對銲長徑彎頭」(短字串)
  * 「Danas-H-XX」同前綴序列號

每個 case 註明真實業務情境，避免未來「為過 test 改參數」反模式。
"""
import pytest

from app.services.tender.enrichment import (
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    GUARD_TITLE_SIM,
    GUARD_AGENCY_SIM,
    _passes_high_guard,
)


# =============================================================================
# Constants — 防 silent threshold drift
# =============================================================================

def test_high_threshold_is_0_85():
    """HIGH 門檻 0.85 不可悄悄改動（影響 233 已 link 案件範圍）。"""
    assert HIGH_CONFIDENCE_THRESHOLD == 0.85


def test_medium_threshold_is_0_70():
    """MEDIUM 門檻 0.70 為 review queue 入口（task E 將落地）。"""
    assert MEDIUM_CONFIDENCE_THRESHOLD == 0.70


def test_guard_thresholds_aligned_to_high():
    """title/agency guard 必須 >= HIGH 門檻（縱深防禦）。"""
    assert GUARD_TITLE_SIM >= HIGH_CONFIDENCE_THRESHOLD
    assert GUARD_AGENCY_SIM >= HIGH_CONFIDENCE_THRESHOLD


# =============================================================================
# Guard 1-3: 數值門檻
# =============================================================================

def test_guard_rejects_low_title_sim():
    """title_sim < 0.85 → reject"""
    assert _passes_high_guard(
        title_sim=0.84,
        agency_match=1.0,
        date_proximity=1.0,
        ezbid_title="完整長度足夠的標案名稱範例 ABC 12345",
        pcc_title="完整長度足夠的標案名稱範例 ABC 12345",
    ) is False


def test_guard_rejects_low_agency_match():
    """agency_match < 0.85 → reject (避不同機關誤判)"""
    assert _passes_high_guard(
        title_sim=1.0,
        agency_match=0.84,
        date_proximity=1.0,
        ezbid_title="完整長度足夠的標案名稱範例 ABC 12345",
        pcc_title="完整長度足夠的標案名稱範例 ABC 12345",
    ) is False


def test_guard_rejects_low_date_proximity():
    """date_proximity < 1.0 → reject (公告日差距越大越不可能同案)"""
    assert _passes_high_guard(
        title_sim=1.0,
        agency_match=1.0,
        date_proximity=0.99,
        ezbid_title="完整長度足夠的標案名稱範例 ABC 12345",
        pcc_title="完整長度足夠的標案名稱範例 ABC 12345",
    ) is False


# =============================================================================
# Guard 4: 短字串 length filter
# =============================================================================

def test_guard_rejects_short_ezbid_title():
    """ezbid title < 12 字 → reject (短字串 trigram 風險)"""
    # 「30吋閘閥」5 字
    assert _passes_high_guard(
        title_sim=1.0,
        agency_match=1.0,
        date_proximity=1.0,
        ezbid_title="30吋閘閥",
        pcc_title="30吋閘閥",
    ) is False


def test_guard_rejects_short_pcc_title():
    """pcc title < 12 字 → reject"""
    assert _passes_high_guard(
        title_sim=1.0,
        agency_match=1.0,
        date_proximity=1.0,
        ezbid_title="完整長度足夠的標案名稱範例 ABC",
        pcc_title="採購短案",
    ) is False


def test_guard_rejects_short_string_high_sim_false_positive():
    """L50 live 揭發 case：「30吋閘閥」對「30吋對銲長徑彎頭」trigram 高 sim 但不同物

    雖然這 case 不會 title_sim=1.0（trigram 約 0.5-0.7），但即使誤算到 0.85+
    也要因 length < 12 被擋下。
    """
    # 假設極端情況 sim 算到 0.9（trigram 對短字串有時會這樣）
    assert _passes_high_guard(
        title_sim=0.9,
        agency_match=1.0,
        date_proximity=1.0,
        ezbid_title="30吋閘閥",
        pcc_title="30吋對銲長徑彎頭",
    ) is False


# =============================================================================
# Guard 5: title exact match (最嚴格)
# =============================================================================

def test_guard_rejects_non_exact_title():
    """長字串但非 exact match → reject (即使 sim 1.0)

    pg_trgm similarity=1.0 不代表 exact match（whitespace/normalization 差異）
    """
    assert _passes_high_guard(
        title_sim=1.0,
        agency_match=1.0,
        date_proximity=1.0,
        ezbid_title="完整長度足夠的標案名稱範例 ABC 12345",
        pcc_title="完整長度足夠的標案名稱範例 ABC 12346",  # 末字差
    ) is False


def test_guard_rejects_danas_series_same_prefix():
    """L50 live 揭發 case：颱風代號系列短前綴 + 序列號（Danas-H-01, Danas-H-02...）

    這類序列題目共同前綴 + 數字後綴，trigram 給 0.85+ 高 sim 但實為不同案件。
    第 5 重 guard (exact match) 必須擋下。
    """
    assert _passes_high_guard(
        title_sim=0.88,
        agency_match=1.0,
        date_proximity=1.0,
        ezbid_title="Danas-H-01 颱風災害復建工程第一標",
        pcc_title="Danas-H-02 颱風災害復建工程第二標",
    ) is False


# =============================================================================
# Happy path: 所有 guard 都通過
# =============================================================================

def test_guard_accepts_perfect_match():
    """完整長度 + exact match + 所有門檻通過 → accept"""
    title = "高雄市政府工務局 105 年度道路鋪面修補工程"
    assert _passes_high_guard(
        title_sim=1.0,
        agency_match=1.0,
        date_proximity=1.0,
        ezbid_title=title,
        pcc_title=title,
    ) is True


def test_guard_accepts_threshold_exact_85():
    """title_sim/agency 剛好 0.85 + exact match → accept (邊界 case)"""
    title = "輸供電設備調度運轉管理系統委外維護案"
    assert _passes_high_guard(
        title_sim=0.85,
        agency_match=0.85,
        date_proximity=1.0,
        ezbid_title=title,
        pcc_title=title,
    ) is True


# =============================================================================
# 邊角組合 — 真實 false positive scenarios
# =============================================================================

@pytest.mark.parametrize("eb_title,pcc_title", [
    # 同前綴短編號（L50 揭發）
    ("Danas-H-01", "Danas-H-02"),
    # 短字串高 trigram sim 但不同物
    ("30吋閘閥", "30吋彎頭"),
    # 雙方都 < 12 字
    ("ABC 採購案", "ABC 採購案"),
])
def test_guard_rejects_known_false_positive_patterns(eb_title, pcc_title):
    """已知 false positive pattern 一律 reject（即使數值門檻通過）"""
    assert _passes_high_guard(
        title_sim=0.9,
        agency_match=1.0,
        date_proximity=1.0,
        ezbid_title=eb_title,
        pcc_title=pcc_title,
    ) is False
