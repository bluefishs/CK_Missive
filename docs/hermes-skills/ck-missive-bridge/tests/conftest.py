"""
pytest conftest — skill 回歸測試共用設定。

執行：
    cd CK_Missive/docs/hermes-skills/ck-missive-bridge
    python -m pytest tests/ -q

依賴（於 CK_Missive venv 或獨立 venv）：
    pip install pytest httpx
"""
from __future__ import annotations

import sys
from pathlib import Path

# 讓測試可以直接 `import tools`（與 skill runtime 相同載入方式）
SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))
