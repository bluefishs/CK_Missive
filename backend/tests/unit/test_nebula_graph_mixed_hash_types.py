"""Regression test — nebula graph endpoint 不得因 YAML template_hash 型別混合爆 TypeError

2026-04-24: YAML 把純數字 template_hash 自動 parse 成 int，混入 str hash
時 sorted([int, str]) 爆 TypeError → 500 Internal Server Error（ADR-0028 違規）。

修復：
1. endpoint 讀端 str() 強制 coerce
2. pattern_extractor 寫端 template_hash 加引號
3. 既有壞資料 pattern-8692128536.md 改加引號
"""
import inspect
from pathlib import Path


def test_nebula_graph_coerces_template_hash_to_str():
    """endpoint 讀取時必須 str() coerce template_hash，防 YAML int/str 混合爆 sorted"""
    from app.api.endpoints.ai import memory
    src = inspect.getsource(memory.memory_nebula_graph)
    # 必須有顯式 str() cast
    assert 'str(meta["template_hash"])' in src or "str(meta['template_hash'])" in src, (
        "memory_nebula_graph 必須 str() coerce template_hash；"
        "否則純數字 hash（如 8692128536）被 YAML parse 為 int，"
        "sorted([int, str]) 會爆 TypeError 導致 500。"
    )


def test_pattern_extractor_quotes_template_hash():
    """pattern_extractor 寫入時必須為 template_hash 加引號"""
    from app.services.memory import pattern_extractor
    src = inspect.getsource(pattern_extractor)
    # f-string 裡必須是 "{p.template_hash}" 含引號
    assert 'template_hash: "{p.template_hash}"' in src, (
        "pattern_extractor 寫 YAML 時 template_hash 必須加雙引號，"
        "讓 YAML parse 永遠得到 str（即使 hash 全數字）"
    )


def test_existing_pattern_files_have_quoted_hash_or_alphanumeric():
    """已落地的 pattern 檔案：純數字 hash 必須加引號，含字母則 OK（自動 str）"""
    patterns_dir = Path(__file__).resolve().parents[3] / "wiki" / "memory" / "patterns"
    if not patterns_dir.exists():
        import pytest
        pytest.skip("patterns dir not available in this env")

    bad = []
    for path in patterns_dir.glob("pattern-*.md"):
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("template_hash:"):
                value = line.split(":", 1)[1].strip()
                # 若全數字且無引號 → 壞資料
                if value.isdigit():
                    bad.append(path.name)
                break
    assert not bad, (
        f"以下 pattern 檔 template_hash 純數字未加引號（會被 YAML parse 為 int）："
        f"{bad}；請加雙引號修正"
    )
