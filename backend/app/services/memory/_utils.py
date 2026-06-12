"""Memory 服務共用 util（57e SSOT，2026-06-12）

收斂 autobiography/pattern_extractor 各自重複的 `_parse_tools`（完全同碼）。
"""
import json
from typing import Any, List


def parse_tools(tools_used: Any) -> List[str]:
    """解析 tools_used → List[str]。

    None / 非法 JSON / 非 list → []；str 先 json.loads；list 過濾出 str 元素。
    """
    if tools_used is None:
        return []
    if isinstance(tools_used, str):
        try:
            tools_used = json.loads(tools_used)
        except Exception:
            return []
    if isinstance(tools_used, list):
        return [t for t in tools_used if isinstance(t, str)]
    return []
