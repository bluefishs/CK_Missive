"""Regression test — _parse_frontmatter 正確處理 quoted string（ADR-0028 根本修復）

2026-04-24 事故複查：
  custom YAML parser `val.isdigit() → int(val)` 會把純數字字串誤推為 int，
  混入 str hash 造成 sorted TypeError → nebula/graph 500。

修復：quoted string 優先保留為 str，不做型別推斷。
覆蓋兩個 parser：
  - backend/app/api/endpoints/ai/memory.py::_parse_frontmatter（核心）
  - backend/app/services/memory/crystallizer.py::_parse_pattern_meta
"""
from app.api.endpoints.ai.memory import _parse_frontmatter


def _frontmatter(body: str) -> str:
    return f"---\n{body}\n---\nbody content here"


def test_quoted_digit_string_stays_str():
    """純數字加雙引號 → str（本次根因修復）"""
    meta = _parse_frontmatter(_frontmatter('template_hash: "8692128536"'))
    assert meta["template_hash"] == "8692128536"
    assert isinstance(meta["template_hash"], str)


def test_quoted_single_quote_string_stays_str():
    """單引號同樣視為 str"""
    meta = _parse_frontmatter(_frontmatter("pattern_id: '123456'"))
    assert meta["pattern_id"] == "123456"
    assert isinstance(meta["pattern_id"], str)


def test_bare_digit_still_int_for_counts():
    """純數字無引號 → 仍 int（如 hit_count、success_count 應為計數）"""
    meta = _parse_frontmatter(_frontmatter("hit_count: 4"))
    assert meta["hit_count"] == 4
    assert isinstance(meta["hit_count"], int)


def test_alphanumeric_hash_stays_str():
    """含字母 hash 本來就是 str"""
    meta = _parse_frontmatter(_frontmatter("template_hash: 158e35547b"))
    assert meta["template_hash"] == "158e35547b"
    assert isinstance(meta["template_hash"], str)


def test_mixed_patterns_no_type_mixing():
    """模擬 nebula/graph 場景：quoted 純數字 + 字母 hash 混合，sorted 不爆"""
    h1 = _parse_frontmatter(_frontmatter('template_hash: "8692128536"'))["template_hash"]
    h2 = _parse_frontmatter(_frontmatter("template_hash: 158e35547b"))["template_hash"]
    # 應都是 str，sorted 不爆
    assert isinstance(h1, str)
    assert isinstance(h2, str)
    result = sorted([h1, h2])  # 不應 raise TypeError
    assert result == ["158e35547b", "8692128536"]


def test_float_and_bool_still_work():
    """其他型別推斷（float、bool）不受影響"""
    meta = _parse_frontmatter(
        _frontmatter("success_rate: 0.85\ncrystallization_candidate: True")
    )
    assert meta["success_rate"] == 0.85
    assert meta["crystallization_candidate"] is True


def test_crystallizer_parses_quoted_hash():
    """crystallizer._parse_pattern_meta 應剝除引號"""
    import tempfile
    from pathlib import Path
    from app.services.memory.crystallizer import Crystallizer

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md", encoding="utf-8") as f:
        f.write('---\ntemplate_hash: "8692128536"\nhit_count: 5\n---\n# Pattern\n')
        tmp_path = Path(f.name)
    try:
        meta = Crystallizer._parse_pattern_meta(tmp_path)
        assert meta is not None
        # 引號必須被剝除才能與檔名 / DB 其他記錄 match
        assert meta["template_hash"] == "8692128536"
        assert '"' not in meta["template_hash"]
    finally:
        tmp_path.unlink(missing_ok=True)
