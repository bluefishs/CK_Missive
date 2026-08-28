"""附件備份掃描容錯回歸測試（A38 根因）

`_safe_rglob` 的 docstring 宣稱「每次 next() 包 try/except，跳過壞 entry，
不中斷主流程」。但它包的是一個 **generator**——generator 一旦拋出非
StopIteration 的例外就進入 closed 狀態，後續 next() 只會得到 StopIteration。

⇒ 那個 `continue` 從來沒有讓它繼續過：第一個壞 entry 就是掃描的終點，
而日誌只留下一行「跳過無法讀取的 entry」，看起來像只漏了一個。

實測（2026-08-28，ck_missive_backend 容器內）：
    _safe_rglob 走訪 233 entry 後停在 2026/02/doc_884/…
    warning 1 次：[Errno 5] Input/output error: '/app/uploads/2026/02/doc_885'
    os.walk(onerror=…) 實際可掃到 1,550 檔
    manifest_20260828 記 total_files=120 ⇒ 1,430 檔靜默消失

測試把「doc_885 讀不到」這個**物理故障**同時注入兩種走訪機制
（rglob 的 iterator／os.walk 的 onerror），因此與 _safe_rglob 的實作選擇無關。
"""

import os
from pathlib import Path

from app.services.backup.attachment_backup import _safe_rglob

BAD_DIR = "dir_01"


def _build_tree(root: Path, n_dirs: int = 4, per_dir: int = 3) -> int:
    total = 0
    for i in range(n_dirs):
        d = root / f"dir_{i:02d}"
        d.mkdir(parents=True, exist_ok=True)
        for j in range(per_dir):
            (d / f"f{j}.bin").write_bytes(b"x")
            total += 1
    return total


def _inject_unreadable_dir(monkeypatch, root: Path) -> None:
    """讓 root/dir_01 在任一走訪機制下都表現為 Errno 5 不可讀。"""
    bad_path = root / BAD_DIR
    real_walk = os.walk
    real_rglob = Path.rglob

    def walk_with_fault(top, *a, **kw):
        onerror = kw.get("onerror")
        for dirpath, dirnames, filenames in real_walk(top, *a, **kw):
            if Path(dirpath) == bad_path:
                if onerror is not None:
                    onerror(OSError(5, "Input/output error", dirpath))
                continue
            yield dirpath, dirnames, filenames

    def rglob_with_fault(self, pattern, *a, **kw):
        # 重現正式環境：iterator 走到壞目錄時於 next() 拋 OSError
        for entry in real_rglob(self, pattern, *a, **kw):
            if bad_path in entry.parents or entry == bad_path:
                raise OSError(5, "Input/output error", str(bad_path))
            yield entry

    monkeypatch.setattr(os, "walk", walk_with_fault)
    monkeypatch.setattr(Path, "rglob", rglob_with_fault)


def test_safe_rglob_survives_unreadable_directory(tmp_path, monkeypatch):
    """壞目錄之後的檔案必須仍然被掃到——這是 A38 的 1,430 檔缺口。"""
    expected = _build_tree(tmp_path)
    _inject_unreadable_dir(monkeypatch, tmp_path)

    found = [p for p in _safe_rglob(tmp_path) if p.is_file()]
    names = {p.parent.name for p in found}

    # dir_01 讀不到是可接受的降級；dir_02/dir_03 整個消失才是 A38 的災難
    assert "dir_02" in names, "壞 entry 之後的目錄整個消失了（A38 復發）"
    assert "dir_03" in names, "壞 entry 之後的目錄整個消失了（A38 復發）"
    assert len(found) == expected - 3, (
        f"應只損失壞目錄的 3 個檔，實際掃到 {len(found)}／預期 {expected - 3}"
    )


def test_safe_rglob_scans_everything_when_healthy(tmp_path):
    """沒有壞 entry 時必須一個不漏。"""
    expected = _build_tree(tmp_path)
    found = [p for p in _safe_rglob(tmp_path) if p.is_file()]
    assert len(found) == expected


def test_safe_rglob_yields_directories_too(tmp_path):
    """呼叫端用 is_file() 過濾，故產出須與 rglob('*') 同樣包含目錄。"""
    _build_tree(tmp_path, n_dirs=2, per_dir=1)
    found = list(_safe_rglob(tmp_path))
    assert any(p.is_dir() for p in found), "產出必須包含目錄，與 rglob('*') 語意一致"
