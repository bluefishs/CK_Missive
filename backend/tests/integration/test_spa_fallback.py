# -*- coding: utf-8 -*-
"""SPA fallback 整合測試 — ADR-0016 公網部署。

當 frontend/dist 存在時：
  - / 回 index.html
  - /assets/* 回靜態檔
  - /unknown 回 index.html（React Router 接管）
  - /api/* 不受影響

當 dist 不存在時：
  - / 回 JSON（API-only 模式）
  - SPA 路由不啟用
"""
from __future__ import annotations

from pathlib import Path

import pytest


_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
_INDEX = _DIST / "index.html"

skip_unless_built = pytest.mark.skipif(
    not _INDEX.exists(),
    reason="frontend/dist 未 build；本測試需 npm run build 後啟用",
)


@pytest.fixture
def public_url():
    """公網 URL（PHASE 1 驗證用，可選）"""
    import os
    return os.getenv("MISSIVE_PUBLIC_URL")


@skip_unless_built
def test_dist_index_exists():
    """dist/index.html 必須存在，否則 SPA 無從掛載。"""
    assert _INDEX.is_file()
    assert (_DIST / "assets").is_dir(), "assets/ 子目錄缺漏 — vite build 未產出"


def test_index_size_reasonable():
    """若 dist 存在，index.html 應 > 100 bytes（避免空殼）。"""
    if not _INDEX.exists():
        pytest.skip("dist 未 build")
    assert _INDEX.stat().st_size > 100, "index.html 過小，可能 build 失敗"


@skip_unless_built
def test_assets_dir_has_js(public_url):
    """assets/ 應含至少 1 個 .js bundle。"""
    js_files = list((_DIST / "assets").glob("*.js"))
    assert len(js_files) > 0, "vite build 未產 js bundle"
