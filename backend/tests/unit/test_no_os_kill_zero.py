# -*- coding: utf-8 -*-
"""回歸鎖：不得有 `os.kill(<pid>, 0)`（bpo-14484）。

Windows 上 signal.CTRL_C_EVENT == 0，`os.kill(pid, 0)` 不是探測存活而是對該 console 行程群送 Ctrl-C。
2026-09-06 AaaP 全 monorepo 掃描：本 repo `backend/startup.py` 拿**別的** startup 的 pid 呼叫——會殺掉正在跑的舊進程。
PileMgmt 同日以非互動排程實證（pytest 收到 KeyboardInterrupt、整棵行程樹被殺、互動 shell 看不到）。
豁免標記：行尾 `# windows-footgun: ok`（必須說明只在 POSIX 呼叫）。
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _hits_in(path: Path) -> list:
    """用 AST 找 os.kill(<x>, 0) 的**呼叫**——不是 grep：判準的掃描範圍不得包含描述它的註解與 docstring（本檔首版就抓到自己）。"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "kill" and isinstance(f.value, ast.Name) and f.value.id == "os":
            sig = node.args[1]
            if isinstance(sig, ast.Constant) and sig.value == 0:
                line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
                if "windows-footgun: ok" not in line:
                    out.append(f"{path.relative_to(ROOT)}:{node.lineno}: {line.strip()}")
    return out


def test_no_os_kill_zero_outside_posix_guard():
    hits = []
    for f in ROOT.rglob("*.py"):
        if any(part in ("tests", "__pycache__", "_archived", ".venv", "venv") for part in f.parts):
            continue
        hits += _hits_in(f)
    assert not hits, "os.kill(pid, 0) 在 Windows 上是送 Ctrl-C，不是探測：" + chr(10) + chr(10).join(hits)
