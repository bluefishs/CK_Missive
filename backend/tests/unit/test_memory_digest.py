"""S3 段 A regression — GET /api/ai/memory/digest（坤哥成長摘要，M2M 唯讀）

契約來源：CK_Hermes/docs/plans/s3-meta-federation-briefing-design.md §2 段A
- X-Service-Token 認證（同 kunge/snapshot；Hermes bridge memory_digest action 已預寫）
- 回 platform/consciousness/as_of/window/growth{diary_highlights,new_patterns,
  open_uncertainties,metrics}/digest_text（150-400 字繁中，LLM-friendly）
- 唯讀、冪等；單一資料源故障不拖垮整體（fault isolation，對齊 S3 段C 精神）
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints.ai import memory_digest as md
from app.db.database import get_async_db

TOKEN = "test-service-token"


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeSession:
    """依序回應 scalar 查詢：documents 總數 → 總實體 → window 新增實體"""

    def __init__(self, values):
        self._values = list(values)

    async def execute(self, *_a, **_kw):
        return _FakeResult(self._values.pop(0))


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture()
def memory_tree(tmp_path, monkeypatch):
    """建立 wiki/memory 假資料樹並 patch 模組目錄常數。"""
    today = date.today()
    d1 = today - timedelta(days=1)
    old = today - timedelta(days=30)

    # diary：window 內 2 篇（含 frontmatter 應被跳過）+ window 外 1 篇
    _write(tmp_path / "diary" / f"{d1.isoformat()}.md",
           "---\ncreated: x\n---\n\n## 修復 SSO 停登入頁\n細節……\n")
    _write(tmp_path / "diary" / f"{today.isoformat()}.md",
           "## 標案韌性方案A上線\n內文\n")
    _write(tmp_path / "diary" / f"{old.isoformat()}.md", "## 舊事\n")

    # patterns：1 新（mtime=now，剛寫入即新）
    _write(tmp_path / "patterns" / "pattern-abc123.md",
           "---\nhit_count: 9\nsuccess_rate: 1.0\n---\n# 派工進度查詢\n")

    # crystals：1 新
    _write(tmp_path / "crystals" / "crystal-20260703-212231.md", "# SOUL 自省結晶\n")

    # proposals：1 pending + 1 applied
    _write(tmp_path / "proposals" / "crystal-intent-x.md",
           "---\nstatus: pending\n---\n# Intent 提案：進度路由\n")
    _write(tmp_path / "proposals" / "soul-done.md",
           "---\nstatus: applied\n---\n# 已套用\n")

    monkeypatch.setattr(md, "DIARY_DIR", tmp_path / "diary")
    monkeypatch.setattr(md, "PATTERNS_DIR", tmp_path / "patterns")
    monkeypatch.setattr(md, "CRYSTALS_DIR", tmp_path / "crystals")
    monkeypatch.setattr(md, "PROPOSALS_DIR", tmp_path / "proposals")
    return tmp_path


def _client(db_values=(1898, 35126, 120)):
    app = FastAPI()
    app.include_router(md.router, prefix="/api/ai")
    app.dependency_overrides[get_async_db] = lambda: _FakeSession(db_values)
    return TestClient(app)


def test_requires_service_token(memory_tree, monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("DEVELOPMENT_MODE", "false")
    r = _client().get("/api/ai/memory/digest")
    assert r.status_code == 401


def test_digest_contract_shape(memory_tree, monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", TOKEN)
    r = _client().get("/api/ai/memory/digest",
                      headers={"X-Service-Token": TOKEN})
    assert r.status_code == 200, r.text
    body = r.json()

    # S3 契約頂層欄位
    assert body["platform"] == "missive"
    assert body["consciousness"] == "坤哥"
    assert body["as_of"]
    assert body["window"]["since"] and body["window"]["until"]

    g = body["growth"]
    # diary：window 內 2 篇入選、frontmatter 被跳過、舊檔排除
    assert len(g["diary_highlights"]) == 2
    assert any("SSO" in h for h in g["diary_highlights"])
    assert not any("---" in h or "created:" in h for h in g["diary_highlights"])
    # patterns / crystals（mtime 剛寫入 → 在 window 內）
    assert any("pattern-abc123" in p or "派工進度" in p for p in g["new_patterns"])
    assert any("crystal-20260703" in c or "自省" in c for c in g["new_crystals"])
    # open_uncertainties：只含 pending
    assert len(g["open_uncertainties"]) == 1
    assert "進度路由" in g["open_uncertainties"][0]
    # metrics（fake db 依序：documents/entities/new_entities）
    assert g["metrics"] == {"documents": 1898, "entities": 35126, "new_entities": 120}

    # digest_text：繁中、非空、貼近 150-400 字約定（下限放寬避免脆測）
    assert len(body["digest_text"]) >= 80
    assert "坤哥" in body["digest_text"]
    assert "1898" in body["digest_text"] or "1,898" in body["digest_text"]


def test_digest_since_param(memory_tree, monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", TOKEN)
    since = (date.today() - timedelta(days=60)).isoformat()
    r = _client().get(f"/api/ai/memory/digest?since={since}",
                      headers={"X-Service-Token": TOKEN})
    assert r.status_code == 200
    body = r.json()
    assert body["window"]["since"] == since
    # 60 天 window → 舊 diary 也入選（共 3 篇，limit 內）
    assert len(body["growth"]["diary_highlights"]) == 3


@pytest.mark.asyncio
async def test_metrics_passes_date_object_not_str(memory_tree):
    """asyncpg 要 datetime 參數非 str（live 曾因傳 isoformat 字串 DataError → metrics 空）。"""
    from datetime import datetime as dt

    captured = []

    class _Spy:
        async def execute(self, _q, params=None):
            if params:
                captured.append(params.get("since"))
            return _FakeResult(5)

    out = await md._collect_metrics(_Spy(), date.today() - timedelta(days=7))
    assert out == {"documents": 5, "entities": 5, "new_entities": 5}
    assert captured and isinstance(captured[0], (dt, date)) and not isinstance(captured[0], str)


def test_diary_highlight_skips_generic_h1(tmp_path, monkeypatch):
    """diary 首行常為通用 H1「Agent 日記 — YYYY-MM-DD」（零資訊）→ 應取第一個 H2/H3 真亮點。"""
    today = date.today()
    _write(tmp_path / "diary" / f"{today.isoformat()}.md",
           f"# Agent 日記 — {today.isoformat()}\n\n## 修復標案韌性\n內文\n")
    monkeypatch.setattr(md, "DIARY_DIR", tmp_path / "diary")
    out = md._diary_highlights(today - timedelta(days=1), today, 5)
    assert len(out) == 1
    assert "修復標案韌性" in out[0]
    assert "Agent 日記" not in out[0]


def test_diary_highlights_dedup_repeated_headline(tmp_path, monkeypatch):
    """cron 條目（如 06:10 自我感知）每日相同 → 相同亮點只保留最新一筆，不洗版 digest。"""
    today = date.today()
    for i in range(3):
        d = today - timedelta(days=i)
        _write(tmp_path / "diary" / f"{d.isoformat()}.md",
               "## 06:10:05 — 🩺 自我感知（self_diagnosis）\n")
    monkeypatch.setattr(md, "DIARY_DIR", tmp_path / "diary")
    out = md._diary_highlights(today - timedelta(days=7), today, 7)
    assert len(out) == 1
    assert out[0].startswith(today.strftime("%m-%d"))


def test_db_failure_degrades_not_500(memory_tree, monkeypatch):
    """DB 故障 → metrics 缺席但其餘照回（fault isolation），不 500。"""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", TOKEN)

    class _Boom:
        async def execute(self, *_a, **_kw):
            raise RuntimeError("db down")

    app = FastAPI()
    app.include_router(md.router, prefix="/api/ai")
    app.dependency_overrides[get_async_db] = lambda: _Boom()
    r = TestClient(app).get("/api/ai/memory/digest",
                            headers={"X-Service-Token": TOKEN})
    assert r.status_code == 200
    body = r.json()
    assert body["growth"]["metrics"] == {}
    assert body["digest_text"]  # 摘要仍產出
