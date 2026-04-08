"""
引用核實模組 — 驗證合成答案中的引用是否與工具結果一致

Extracted from agent_synthesis.py
"""

import re
from typing import Any, Dict, List


def validate_citations(
    answer: str,
    tool_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    驗證合成答案的引用品質。

    檢查項目：
    1. [公文N] 標記數量 vs 實際可用公文數
    2. [派工單N] 標記數量 vs 實際可用派工單數
    3. 答案長度合理性
    4. 推理洩漏殘留

    Returns:
        {
            "valid": bool,
            "citation_count": int,
            "citation_verified": int,
            "warnings": List[str],
        }
    """
    warnings: List[str] = []

    # 統計答案中的引用標記
    doc_refs = re.findall(r"\[公文(\d+)\]", answer)
    dispatch_refs = re.findall(r"\[派工單(\d+)\]", answer)
    entity_refs = re.findall(r"\[實體(?:\d+)?\]", answer)
    citation_count = len(doc_refs) + len(dispatch_refs) + len(entity_refs)

    # 統計工具結果中的可用資料
    available_docs = 0
    available_dispatches = 0
    for tr in tool_results:
        tool = tr.get("tool", "")
        result = tr.get("result", {})
        if result.get("error"):
            continue
        if tool in ("search_documents", "find_similar"):
            available_docs += len(result.get("documents", []))
        elif tool == "search_dispatch_orders":
            available_dispatches += len(result.get("dispatch_orders", []))

    # 核實引用數量不超過可用資料
    verified = 0
    for ref_num in doc_refs:
        idx = int(ref_num)
        if 1 <= idx <= available_docs:
            verified += 1
        else:
            warnings.append(f"[公文{ref_num}] 超出可用範圍 (共 {available_docs} 篇)")

    for ref_num in dispatch_refs:
        idx = int(ref_num)
        if 1 <= idx <= available_dispatches:
            verified += 1
        else:
            warnings.append(f"[派工單{ref_num}] 超出可用範圍 (共 {available_dispatches} 筆)")

    verified += len(entity_refs)

    # 答案品質檢查
    stripped = answer.strip()
    if len(stripped) < 10:
        warnings.append("答案過短 (<10 字)")

    _THINKING_RESIDUE = ("首先", "我需要", "規則要求", "讓我分析")
    if any(m in stripped[:50] for m in _THINKING_RESIDUE):
        warnings.append("推理洩漏殘留")

    return {
        "valid": len(warnings) == 0,
        "citation_count": citation_count,
        "citation_verified": verified,
        "warnings": warnings,
    }
