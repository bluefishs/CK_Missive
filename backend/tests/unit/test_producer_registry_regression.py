# -*- coding: utf-8 -*-
"""producer 判定的單一實作 —— 壞掉時必須拒絕執行，不得印綠燈（2026-08-05 回歸鎖）。

背景：這份判定原本有兩個獨立實作（host watchdog / 容器內 cron），
同一份 registry 兩套解讀，08-04 咬過一次（容器端只認 3 種 signal，
認不得就靜靜跳過 → 那些 producer 在無人值守的自動告警裡等於不存在）。

更嚴重的是**載入端**：host 端在 registry 讀不到時會靜靜退回一份 07-18 的舊副本，
那份還含著已證實會遮蔽 ezbid 死亡 48 天的合併監控 ——
專門偵測沉默失敗的工具，自己有一條沉默退化的路。

以下每一支對應一種「壞法」，共同要求是：**絕不能是綠的**。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 引擎/稽核模組在 scripts/checks/ —— 容器內是 /app/scripts/checks（ro 掛載），
# host 上則在 repo 根。寫死其中一個，另一邊會在 **collection 階段**就 ImportError，
# 而 pytest 的 collection 錯誤會**中斷整套**（2026-08-05 實測，由 test_suite_health 抓到）。
_CHECKS = [Path("/app/scripts/checks"), Path(__file__).resolve().parents[3] / "scripts" / "checks"]
for _c in _CHECKS:
    if (_c / "producer_registry.py").exists():
        sys.path.insert(0, str(_c))
        break

from producer_registry import (  # noqa: E402
    SCHEMA_VERSION,
    RegistryUnavailable,
    build_count_sql,
    judge,
    load_registry,
)


def _write(tmp_path: Path, payload) -> Path:
    p = tmp_path / "registry.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


# ── 載入端：四種壞法都必須拋例外（＝未驗完），不得回退 ────────────────────

def test_missing_file_raises(tmp_path):
    with pytest.raises(RegistryUnavailable):
        load_registry(tmp_path / "不存在.json")


def test_malformed_json_raises(tmp_path):
    p = tmp_path / "registry.json"
    p.write_text("{ 這不是 JSON", encoding="utf-8")
    with pytest.raises(RegistryUnavailable):
        load_registry(p)


def test_empty_producers_raises(tmp_path):
    """0 個 producer 不等於全部健康 —— 這是設定壞掉，不是系統很乾淨"""
    with pytest.raises(RegistryUnavailable):
        load_registry(_write(tmp_path, {"schema_version": SCHEMA_VERSION, "producers": []}))


def test_unknown_schema_version_raises(tmp_path):
    """版本不符時用舊語意解讀新資料，會產生**看起來正常**的錯誤結論"""
    payload = {"schema_version": SCHEMA_VERSION + 99, "producers": [
        {"name": "x", "signal": "file_fresh", "path": "wiki", "max_h": 30}]}
    with pytest.raises(RegistryUnavailable):
        load_registry(_write(tmp_path, payload))


def test_unknown_signal_raises(tmp_path):
    """認不得的 signal 若被跳過，那些 producer 在自動告警裡等於不存在"""
    payload = {"schema_version": SCHEMA_VERSION, "producers": [
        {"name": "未來型別", "signal": "some_future_signal"}]}
    with pytest.raises(RegistryUnavailable) as ei:
        load_registry(_write(tmp_path, payload))
    assert "some_future_signal" in str(ei.value)


def test_valid_registry_loads(tmp_path):
    """正向：合法 registry 要能載入（否則上面幾支只是「永遠會拋」而無鑑別力）"""
    payload = {"schema_version": SCHEMA_VERSION, "producers": [
        {"name": "x", "signal": "file_fresh", "path": "wiki", "max_h": 30}]}
    assert len(load_registry(_write(tmp_path, payload))) == 1


# ── 判定端 ──────────────────────────────────────────────────────────

def test_cron_detail_missing_key_is_a_problem():
    """註冊為 producer 卻完全不回報 → 必須是紅的。

    先前寫法 `detail.get(key) == 0`，而 None != 0，於是「job 根本不回 detail」
    一路綠燈 —— 那正是要抓的沉默成功。
    """
    spec = {"name": "某 job", "signal": "cron_detail", "job": "j", "key": "delivered"}
    assert judge(spec, latest_event={"detail": {}}) is not None
    assert judge(spec, latest_event={"detail": None}) is not None
    assert judge(spec, latest_event={"detail": {"delivered": 1}}) is None


def test_cron_detail_zero_needs_a_declared_reason():
    spec = {"name": "某 job", "signal": "cron_detail", "job": "j",
            "key": "records", "ok_zero_reasons": ["weekend_no_publish"]}
    assert judge(spec, latest_event={"detail": {"records": 0, "reason": None}}) is not None
    assert judge(
        spec, latest_event={"detail": {"records": 0, "reason": "weekend_no_publish"}}
    ) is None


def test_db_value_none_is_not_healthy():
    """查不到＝未驗完，不能當成正常（先前容器端會讓例外吞掉整筆）"""
    spec = {"name": "t", "signal": "db_table_today", "table": "t", "date_col": "c"}
    assert judge(spec, db_value=None) is not None


def test_db_table_today_weekend_exemption():
    spec = {"name": "t", "signal": "db_table_today", "table": "t",
            "date_col": "c", "weekend_legit": True}
    assert judge(spec, db_value=0, is_weekend=True) is None
    assert judge(spec, db_value=0, is_weekend=False) is not None


def test_json_result_min_key_catches_scanned_nothing(tmp_path):
    """只驗 fail=0 會讓「掃到 0 條」也判綠 —— min_key 是必要的（08-03 立法）"""
    f = tmp_path / "ui-sweep.json"
    f.write_text(json.dumps({"fail": 0, "pass": 0}), encoding="utf-8")
    spec = {"name": "掃描", "signal": "json_result", "path": "x.json",
            "fail_key": "fail", "min_key": "pass", "min_value": 60}
    assert judge(spec, json_files=[f]) is not None

    f.write_text(json.dumps({"fail": 0, "pass": 86}), encoding="utf-8")
    assert judge(spec, json_files=[f]) is None


def test_json_result_missing_file_is_a_problem():
    spec = {"name": "掃描", "signal": "json_result", "path": "x.json", "fail_key": "fail"}
    assert judge(spec, json_files=[]) is not None


def test_where_clause_is_parenthesised():
    """host 版原本加括號、容器版沒有 —— `a=1 OR b=2` 會讓兩邊得出不同答案，
    而症狀是「兩邊各自給出綠燈」，不會有任何錯誤訊息。"""
    spec = {"signal": "db_table_today", "table": "t", "date_col": "c",
            "where": "a=1 OR b=2"}
    assert "AND (a=1 OR b=2)" in build_count_sql(spec)


def test_test_producers_rejected_from_production_registry(tmp_path):
    """`__` 前綴的假 producer 不得留在正式 registry。

    2026-08-04 實際發生：負向測試把兩筆假 producer 加進正式 registry 並觸發 job，
    告警寫進正式 digest buffer，隔天 07:30 推給了 owner。
    驗證機制污染正式輸出 —— 與「測試把假告警寫進晨報緩衝區」同型。
    """
    payload = {"schema_version": SCHEMA_VERSION, "producers": [
        {"name": "正常的", "signal": "file_fresh", "path": "wiki", "max_h": 30},
        {"name": "__負向測試_不存在檔", "signal": "file_fresh", "path": "x", "max_h": 1},
    ]}
    with pytest.raises(RegistryUnavailable) as ei:
        load_registry(_write(tmp_path, payload))
    assert "__負向測試_不存在檔" in str(ei.value)
