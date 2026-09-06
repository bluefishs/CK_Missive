# -*- coding: utf-8 -*-
"""回歸鎖：不得有 `os.kill(<pid>, 0)`（bpo-14484）。

Windows 上 signal.CTRL_C_EVENT == 0，`os.kill(pid, 0)` 不是探測存活而是對該 console 行程群送 Ctrl-C。
2026-09-06 AaaP 全 monorepo 掃描：本 repo `backend/startup.py` 拿**別的** startup 的 pid 呼叫——會殺掉正在跑的舊進程。
PileMgmt 同日以非互動排程實證（pytest 收到 KeyboardInterrupt、整棵行程樹被殺、互動 shell 看不到）。
豁免標記：行尾 `# windows-footgun: ok`（必須說明只在 POSIX 呼叫）。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERN = re.compile(r"os\.kill\(\s*[^,]+,\s*0\s*\)")


def test_no_os_kill_zero_outside_posix_guard():
    hits = []
    for f in list(ROOT.rglob("*.py")):
        if any(part in ("tests", "__pycache__", "_archived", ".venv", "venv") for part in f.parts):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if PATTERN.search(line) and "windows-footgun: ok" not in line:
                hits.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not hits, "os.kill(pid, 0) 在 Windows 上是送 Ctrl-C，不是探測：
" + "
".join(hits)
