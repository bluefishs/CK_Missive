#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`/api/health` 的 `verdict_inputs` 是**跨 repo 契約**，鍵名不是本 repo 的自由選擇。

## 為什麼有這一支

2026-08-29 與 CK_AaaP 跨 session 收斂：兩邊的公開健康端點各自加了
「明說綠燈涵蓋什麼」的欄位，**而鍵名一開始不一樣**
（他們 `informational`／我 `not_covered`）—— 而那個欄位的**整個目的**
正是「跨 repo 探針不必為每個站寫一份解析」。

由他們改成與我一致（成本低的一方讓：我已上公網、他們還沒有消費者），
並各自加測試釘住。**這一支就是我這邊的釘子。**

⚠️ 改這裡的鍵名前要先跟 CK_AaaP 講 —— 不是改個字串而已，
是改一份兩個 repo 都在讀的契約。

## 為什麼不是只驗「欄位存在」

存在但內容錯（例如 `deciding` 列了實際上不參與判定的項目）比不存在更糟：
它是一句**看起來可信的假宣告**。所以本測試同時驗
「`deciding` 列的項目確實會影響判定」。
"""
import pytest

from app.api.endpoints import health as health_module


#: 跨 repo 契約：這三個鍵名與 CK_AaaP 的公開健康端點一致
REQUIRED_KEYS = {"deciding", "not_covered", "note"}

#: 判定輸入 —— 必須與 `basic_health_check` 裡實際參與 `healthy` 計算的一致
EXPECTED_DECIDING = ["database", "business_data"]


def _verdict_inputs_source() -> str:
    """取 `basic_health_check` 的原始碼 —— 驗的是程式碼，不是文件。"""
    import inspect
    return inspect.getsource(health_module.basic_health_check)


def test_verdict_inputs_keys_are_the_cross_repo_contract():
    """三個鍵名一個都不能少、不能改名。"""
    src = _verdict_inputs_source()
    assert '"verdict_inputs"' in src, (
        "`/api/health` 少了 `verdict_inputs` —— 那是跨 repo 探針讀的欄位，"
        "沒有它，讀的人會以為綠燈涵蓋了它其實沒看的東西")
    for key in REQUIRED_KEYS:
        assert f'"{key}"' in src, (
            f"`verdict_inputs` 少了 `{key}` 鍵。⚠️ 這是與 CK_AaaP 對齊過的契約，"
            "改名前要先跟他們講")


def test_deciding_matches_what_actually_decides():
    """`deciding` 宣告的項目，必須真的參與 `healthy` 的計算。

    ⚠️ 這一條比「欄位存在」重要：**存在但內容錯，是一句看起來可信的假宣告**。
    """
    src = _verdict_inputs_source()
    # 實際判定式：healthy = db_status == "connected" and business.get("ok", False)
    assert 'healthy = db_status == "connected"' in src, (
        "判定式變了 —— 請同步檢查 `verdict_inputs.deciding` 是否仍然正確")
    assert 'business.get("ok"' in src, (
        "業務量檢查不再參與判定，而 `deciding` 仍宣告它 —— 那會變成假宣告")
    for item in EXPECTED_DECIDING:
        assert f'"{item}"' in src, f"`deciding` 應包含 {item}"


def test_not_covered_items_do_not_gate():
    """`not_covered` 列的項目不得出現在判定式裡。

    若某天把 AI 納入判定卻忘了從 `not_covered` 移除，那個宣告就會說謊 ——
    而它說的謊剛好是「這個綠燈跟 AI 無關」，讀的人會據此不去查 AI。
    """
    src = _verdict_inputs_source()
    verdict_line = next(
        (ln for ln in src.splitlines() if "healthy = db_status" in ln), "")
    assert verdict_line, "找不到判定式"
    for item in ("ai_services", "kg_federation", "connection_pool", "system_resources"):
        assert item not in verdict_line, (
            f"`{item}` 出現在判定式裡，但 `verdict_inputs.not_covered` 說它不影響判定 "
            "—— 兩者必須同時改")


@pytest.mark.parametrize("endpoint_name,should_touch_db", [
    ("basic_health_check", True),      # 公網探針讀 —— 必須真的查
    ("detailed_health_check", True),   # admin 讀
])
def test_health_endpoints_actually_check_something(endpoint_name, should_touch_db):
    """健康端點必須真的做檢查，不能是靜態 dict。

    ⚠️ 2026-08-29 之前 `basic_health_check` **就是一個靜態 dict**，
    postgres 掛掉它照樣回 healthy，而公網探的正是它（L106）。
    """
    import inspect
    fn = getattr(health_module, endpoint_name)
    src = inspect.getsource(fn)
    if should_touch_db:
        assert "db" in src and ("execute" in src or "check_database" in src), (
            f"`{endpoint_name}` 沒有任何 DB 存取 —— 它會在依賴掛掉時照樣回 healthy")
