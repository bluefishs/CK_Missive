#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""async 路徑上的同步 I/O（weekly 112）——一支同步呼叫會把整個事件迴圈、也就是全站一起卡住。

2026-09-05 實例：`digital_twin_service._get_health` 在 async 裡呼叫同步的 `list_available_systems()`，
內含對已廢止主機 `nemoclaw_tower` 的 httpx.Client 呼叫 ⇒ DNS 失敗 4 秒；那 4 秒內**同時進來的每一支請求**
（navigation/action 也）都變 4.5 秒。探針全綠、後端 p50 正常——只有在同時有人開那一頁時才看得到。

## 判準（AST，不是 grep）

RED    `async def` 函式本體內直接呼叫：`requests.<verb>(`、`httpx.Client(`、`urllib.request.urlopen(`、
       `subprocess.run/call/check_output(`、`time.sleep(`、`socket.create_connection(`
       —— 且不在 `asyncio.to_thread(` / `run_in_executor(` / `loop.run_in_executor(` 的參數裡
YELLOW 同步 `open(` 讀寫大檔／`shutil.copy*`／`os.walk`／`Path.rglob` 直接在 async 裡（小檔可接受，但要知道）
存量走基線 `.async_sync_io_baseline.txt`（檔:函式:呼叫），新增才 RED。

掃描範圍：backend/app/**（排除 tests）。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "backend" / "app"
BASELINE = ROOT / "scripts" / "checks" / ".async_sync_io_baseline.txt"

RED_CALLS = {
    ("requests", None): "requests.*",
    ("httpx", "Client"): "httpx.Client",
    ("urllib.request", "urlopen"): "urlopen",
    ("subprocess", "run"): "subprocess.run", ("subprocess", "call"): "subprocess.call",
    ("subprocess", "check_output"): "subprocess.check_output", ("subprocess", "Popen"): "subprocess.Popen",
    ("time", "sleep"): "time.sleep",
    ("socket", "create_connection"): "socket.create_connection",
}
YELLOW_NAMES = {"walk": "os.walk", "rglob": "Path.rglob", "copytree": "shutil.copytree", "copy2": "shutil.copy2", "copyfile": "shutil.copyfile"}
OFFLOADERS = {"to_thread", "run_in_executor", "run_sync"}


def _dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _is_offloaded(call: ast.Call, parents: list[ast.AST]) -> bool:
    for p in parents:
        if isinstance(p, ast.Call) and _dotted(p.func).split(".")[-1] in OFFLOADERS:
            return True
    return False


def scan_file(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception:
        return [], []
    reds, yels = [], []
    rel = path.relative_to(ROOT).as_posix()

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack: list[ast.AST] = []
            self.in_async: list[str] = []

        def generic_visit(self, node):
            self.stack.append(node)
            super().generic_visit(node)
            self.stack.pop()

        def visit_AsyncFunctionDef(self, node):
            self.in_async.append(node.name)
            self.generic_visit(node)
            self.in_async.pop()

        def visit_FunctionDef(self, node):
            # 巢狀的同步 def（例如丟給 to_thread 的 _scan_files）不算 async 路徵
            saved = self.in_async; self.in_async = []
            self.generic_visit(node)
            self.in_async = saved

        def visit_Call(self, node):
            if self.in_async:
                name = _dotted(node.func)
                head, _, tail = name.rpartition(".")
                key = None
                if head == "requests" or name.startswith("requests."):
                    key = "requests.*"
                for (mod, attr), label in RED_CALLS.items():
                    if attr and name.endswith(f"{mod}.{attr}") or (attr and name == f"{mod.split('.')[-1]}.{attr}"):
                        key = label
                if key and not _is_offloaded(node, self.stack):
                    reds.append(f"{rel}:{node.lineno} {self.in_async[-1]} → {key}")
                elif tail in YELLOW_NAMES and not _is_offloaded(node, self.stack):
                    yels.append(f"{rel}:{node.lineno} {self.in_async[-1]} → {YELLOW_NAMES[tail]}")
            self.generic_visit(node)

    V().visit(tree)
    return reds, yels


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=== async 路徑上的同步 I/O（weekly 112）===")
    reds, yels = [], []
    for f in APP.rglob("*.py"):
        if "tests" in f.parts or "__pycache__" in f.parts:
            continue
        r, y = scan_file(f); reds += r; yels += y
    base = set(BASELINE.read_text(encoding="utf-8").splitlines()) if BASELINE.exists() else set()
    key = lambda s: s.split(" ", 1)[0].rsplit(":", 1)[0] + " " + s.split(" ", 1)[1]  # 去掉行號比對基線
    new_reds = [r for r in reds if key(r) not in base]
    print(f"async 內同步 I/O：RED {len(reds)}（基線 {len(base)}、新增 {len(new_reds)}）／YELLOW {len(yels)}")
    for r in new_reds[:15]:
        print(f"  [RED] {r}")
    for y in yels[:8]:
        print(f"  [YELLOW] {y}")
    if not BASELINE.exists():
        print("  [YELLOW] 沒有基線檔——首跑；以本次 RED 建立 .async_sync_io_baseline.txt（存量不判紅、新增才紅）")
        return 1
    if new_reds:
        print(f"[RED] {len(new_reds)} 處新增的同步 I/O 在 async 路徑上——一支卡全站")
        return 2
    if yels or reds:
        print("[YELLOW] 見上（存量 RED 走基線，仍該逐一改成 to_thread）")
        return 1
    print("[GREEN] async 路徑無同步 I/O")
    return 0


if __name__ == "__main__":
    sys.exit(main())
