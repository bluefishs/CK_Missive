"""
Thinking 過濾模組 — 從 LLM 回答中移除推理段落

5 階段策略：「答案提取」而非「推理過濾」
- Phase 1: 移除 <think> 標記
- Phase 2: 短回答快速通過
- Phase 3: 尋找答案邊界標記（「如下：」「以下是」等），取後半段
- Phase 4: 從末尾向前掃描，找最後一段含 [公文N]/[派工單N] 的區塊
- Phase 5: 逐行過濾（最後手段）

Extracted from agent_synthesis.py
"""

import re


_OBVIOUS_THINKING = ("首先", "我需要", "問題是", "規則要求", "讓我分析", "从资料")

_ANSWER_BOUNDARIES = (
    "如下：", "如下:", "重點如下", "資訊如下", "相關資訊如下",
    "可能的回應", "回答：", "回答:", "回覆：", "回覆:",
    "綜合以上", "以下是", "以下為",
)

_THINK_PREFIXES = (
    "首先", "我需要", "問題是", "讓我", "让我",
    "用户", "用戶", "規則要求", "規則說", "回答結構",
    "回答要", "日期格式", "我假設", "我将", "我將",
    "在公文資料中", "由於問題", "可能用戶",
    "但規則", "但問題", "回覆結構", "結構建議",
    "從資料看", "從檢索結果", "所以重點", "所以我",
    "列出每", "所有公文",
    "- 只根據", "- 引用來源", "- 如果資料不足",
    "- 使用繁體", "- 回答簡潔", "- 若問題涉及",
    "- 日期格式使用", "- 簡潔扼要", "- 用繁體",
    "在中文公文術語中", "這有點", "為了遵守",
    "我應該", "先提取", "現在，",
)

_REF_PATTERN = re.compile(r"\[(公文|派工單)\d+\]")


def strip_thinking_from_synthesis(raw: str) -> str:
    """
    從合成回答中提取真正的答案，丟棄 qwen3:4b 洩漏的推理段落。

    策略：「答案提取」而非「推理過濾」
    - Phase 1: 移除 <think> 標記
    - Phase 2: 短回答快速通過
    - Phase 3: 尋找答案邊界標記（「如下：」「以下是」等），取後半段
    - Phase 4: 從末尾向前掃描，找最後一段含 [公文N]/[派工單N] 的區塊
    - Phase 5: 逐行過濾（最後手段）
    """
    if not raw:
        return raw

    # Phase 1: 移除 <think> 標記
    cleaned = re.sub(r"<think>.*?</think>\s*", "", raw, flags=re.DOTALL).strip()

    # Phase 2: 短回答快速通過
    has_refs = bool(_REF_PATTERN.search(cleaned))

    if len(cleaned) < 300 and not has_refs and not any(m in cleaned for m in _OBVIOUS_THINKING):
        return cleaned

    lines = cleaned.split("\n")

    # Phase 3: 尋找答案邊界
    result = _find_answer_boundary(lines)
    if result is not None:
        return result

    # Phase 3.5: 找末尾的 intro + 結構化區塊
    result = _find_trailing_structured_block(lines)
    if result is not None:
        return result

    # Phase 4: 無明確邊界 → 找最後一段含 [公文N]/[派工單N] 的連續區塊
    result = _find_last_ref_block(lines)
    if result is not None:
        return result

    # Phase 5: 逐行過濾（最後手段）
    return _filter_lines(lines, cleaned)


def _find_answer_boundary(lines: list[str]) -> str | None:
    boundary_idx = None
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if any(marker in stripped for marker in _ANSWER_BOUNDARIES):
            boundary_idx = i
            break

    if boundary_idx is not None:
        answer_lines = lines[boundary_idx:]
        result = "\n".join(answer_lines).strip()
        if result and len(result) > 20:
            return result
    return None


def _find_trailing_structured_block(lines: list[str]) -> str | None:
    for i in range(len(lines) - 2, -1, -1):
        stripped = lines[i].strip()
        if stripped and (stripped.endswith("：") or stripped.endswith(":")):
            next_stripped = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if _REF_PATTERN.search(next_stripped) or next_stripped.startswith("-") or next_stripped.startswith("*"):
                answer_lines = lines[i:]
                result = "\n".join(answer_lines).strip()
                if result and len(result) > 20:
                    return result
    return None


def _find_last_ref_block(lines: list[str]) -> str | None:
    ref_blocks: list[tuple[int, int]] = []
    block_start = -1
    block_end = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        has_ref = bool(_REF_PATTERN.search(stripped))
        is_continuation = line.startswith("  ") or stripped.startswith("*") or not stripped

        if has_ref:
            if block_start == -1:
                block_start = i
            block_end = i
        elif block_start != -1:
            if is_continuation:
                block_end = i
            else:
                ref_blocks.append((block_start, block_end))
                block_start = -1

    if block_start != -1:
        ref_blocks.append((block_start, block_end))

    if ref_blocks:
        start, end = ref_blocks[-1]

        for back in range(1, 3):
            idx = start - back
            if idx >= 0:
                prev = lines[idx].strip()
                if prev and len(prev) < 100 and not any(
                    prev.startswith(m) for m in _OBVIOUS_THINKING
                ):
                    start = idx
                    break
                elif not prev:
                    break

        answer_lines = lines[start:end + 1]
        result = "\n".join(answer_lines).strip()
        if result and len(result) > 20:
            return result

    return None


def _filter_lines(lines: list[str], cleaned: str) -> str:
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        if any(stripped.startswith(m) for m in _THINK_PREFIXES):
            continue
        meta_count = sum(1 for m in ("分析", "假設", "應該", "需要",
                                      "結構", "格式", "簡潔") if m in stripped)
        if meta_count >= 3:
            continue
        kept.append(line)

    result = "\n".join(kept).strip()

    if not result or len(result) < 20:
        doc_lines = [ln for ln in lines if _REF_PATTERN.search(ln)]
        if doc_lines:
            return "\n".join(doc_lines).strip()
        return cleaned

    return result
