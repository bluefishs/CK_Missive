# -*- coding: utf-8 -*-
"""啟動時預熱哪些模型 —— 2026-09-09。

## 為什麼把預熱清單與必備清單拆開

`REQUIRED_MODELS` 原本同時扮演兩個角色：「這台機器上要有這些模型」（啟動時自動拉取）
與「開機就把它們載進記憶體」。**這是兩件事**，而混在一起的代價與**重啟次數成正比**：
每次重啟重新釘住約 5 GB。

實測（06:0x）：ollama 佔 10.37 GiB / 23.47 GiB，而 `ollama ps` 只有 Hermes 常駐的
`qwen2.5:7b-ctx64k`（8.7 GB）—— 我們預熱的 `qwen2.5:7b` 是**另一個模型**，
且啟動後不久就被 TTL 釋放（＝之後沒人用它）。`gemma4:e2b`（視覺）同樣。

⚠️ 這**不是**「預熱造成核心故障」的修法——那個因果沒有被證明（CK_Website 自己也這樣標）。
這是拿掉一筆**已證實存在、而效益未證實**的成本。

## 這支測試守什麼

1. 預設只預熱嵌入模型（KG／RAG 每次檢索都要，效益明確）。
2. `REQUIRED_MODELS` **不得**被這個改動縮小 —— 自動拉取仍要涵蓋三個模型，
   否則「不預熱」會變成「模型不見了」，那是完全不同的故障。
3. 三個逃生口都要work：`all` 恢復舊行為、`none` 全關、逗號清單指定。
"""
import importlib

import pytest


def _reload(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("OLLAMA_WARMUP_MODELS", raising=False)
    else:
        monkeypatch.setenv("OLLAMA_WARMUP_MODELS", value)
    import app.core.ai_connector as m
    return importlib.reload(m)


def test_default_warms_only_embedding(monkeypatch):
    m = _reload(monkeypatch, None)
    assert m.WARMUP_MODELS == {"nomic-embed-text"}


def test_required_models_unchanged(monkeypatch):
    """不預熱 ≠ 不需要。自動拉取的涵蓋範圍不得縮小。"""
    m = _reload(monkeypatch, None)
    assert {"nomic-embed-text", "gemma4:e2b"} <= m.REQUIRED_MODELS
    assert len(m.REQUIRED_MODELS) == 3


@pytest.mark.parametrize("value,expected", [
    ("all", None),                       # None ＝ 等於 REQUIRED_MODELS
    ("none", set()),
    ("off", set()),
    ("nomic-embed-text,gemma4:e2b", {"nomic-embed-text", "gemma4:e2b"}),
    ("  nomic-embed-text ,, ", {"nomic-embed-text"}),   # 空白與空項要吃掉
])
def test_env_overrides(monkeypatch, value, expected):
    m = _reload(monkeypatch, value)
    assert m.WARMUP_MODELS == (m.REQUIRED_MODELS if expected is None else expected)


def test_case_insensitive_keywords(monkeypatch):
    assert _reload(monkeypatch, "ALL").WARMUP_MODELS == _reload(monkeypatch, "all").WARMUP_MODELS
    assert _reload(monkeypatch, "NONE").WARMUP_MODELS == set()


def test_cleanup(monkeypatch):
    """把模組還原成預設，避免污染同一輪的其他測試（模組層常數是全域狀態）。"""
    m = _reload(monkeypatch, None)
    assert m.WARMUP_MODELS == {"nomic-embed-text"}
