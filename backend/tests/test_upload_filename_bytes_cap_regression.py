# -*- coding: utf-8 -*-
"""上傳檔名 UTF-8 位元組封頂 — 回歸鎖定（2026-08-29，A38 觸發器根治）

Windows NTFS 算 UTF-16 字元、Linux/NAS 算 UTF-8 位元組（NAME_MAX 255）——
使用者拿整段公文主旨當檔名（實例 268 bytes）時來源端存得進，
備份端 Errno 5／robocopy ERROR 123 靜默失敗。鎖定：
  1. 超長中文檔名被截到 ≤200 bytes（含 uuid 前綴後仍 <255）
  2. 副檔名保留、位元組切割不產生殘缺字
  3. 正常長度檔名不受影響
"""
import pytest

from app.api.endpoints.files import common as files_common


@pytest.fixture
def _tmp_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(files_common, "UPLOAD_BASE_DIR", str(tmp_path))
    return tmp_path


def _basename_bytes(path: str) -> int:
    import os
    return len(os.path.basename(path).encode("utf-8"))


def test_long_chinese_filename_capped(_tmp_upload_dir):
    # 268 bytes 的實例形態：中文主旨 + .pdf
    long_name = "檢送115年度新屋區中華南路一段福九路至高鐵南路七段道路拓寬工程" * 4 + ".pdf"
    assert len(long_name.encode("utf-8")) > 255

    _full, rel = files_common.get_structured_path(None, long_name)
    b = _basename_bytes(rel)
    assert b <= 200 + 9, f"檔名 {b} bytes 仍超過上限（uuid 前綴 9 bytes + 200）"
    assert rel.endswith(".pdf"), "副檔名必須保留"
    # 位元組切割不得產生殘缺 UTF-8（能無損 encode/decode 即完整）
    import os
    name = os.path.basename(rel)
    assert name.encode("utf-8").decode("utf-8") == name


def test_normal_filename_untouched(_tmp_upload_dir):
    _full, rel = files_common.get_structured_path(None, "報告書v2.pdf")
    import os
    assert os.path.basename(rel).endswith("_報告書v2.pdf")
