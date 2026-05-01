#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architecture Fitness Function: Wiki Unicode 重名偵測（v6.2 Phase C3）

防 wiki_compiler 寫入 NFC 與 CJK Compatibility Ideograph 兩種正規化的同名檔。

實例（2026-05-01 發現）：
  wiki/entities/南投縣埔里地政事務所.md  ← 兩個檔
    - 1465 bytes：含 U+91CC「里」（NFC 標準）+ kg_entity_id=130（canonical）
    - 691  bytes：含 U+F9E9「里」（CJK Compatibility）+ kg_entity_id=None（孤兒）

風險：
  - 排程 wiki_compile 反覆寫入會無限累積 dup
  - 看起來連結率 OK，實際上 compatibility variant 永遠拿不到 kg_entity_id
  - I4 backfill 看似 missing 5，實則是 dup pollution 4 + 真缺 4

修復方向（root cause）：
  - wiki_compiler 寫檔前 unicodedata.normalize('NFC', filename)
  - entity_extractor canonical_name 同時 NFC 化

用法：
    python scripts/checks/wiki_unicode_dup_check.py
    python scripts/checks/wiki_unicode_dup_check.py --ci

Version: 1.0.0 (2026-05-01)
關聯: I4 wiki↔KG backfill / KG_WIKI_INTEGRATION_REVIEW.md
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

WIKI_DIRS = [
    Path("wiki/entities"),
    Path("wiki/topics"),
    Path("wiki/synthesis"),
]


def main(ci: bool) -> int:
    print("=== Wiki Unicode 重名偵測（v6.2 C3）===\n")

    total_dups = 0
    total_files = 0

    for wiki_dir in WIKI_DIRS:
        if not wiki_dir.exists():
            continue

        # 以 NFC 化的檔名為 key 分組
        by_nfc: dict[str, list[Path]] = defaultdict(list)
        for f in wiki_dir.iterdir():
            if not f.is_file() or f.suffix != ".md":
                continue
            total_files += 1
            nfc_name = unicodedata.normalize("NFC", f.name)
            by_nfc[nfc_name].append(f)

        # 找 collision
        collisions = {n: paths for n, paths in by_nfc.items() if len(paths) > 1}
        if collisions:
            print(f"[FAIL] {wiki_dir}: {len(collisions)} 個 NFC 重名")
            for nfc_name, paths in collisions.items():
                print(f"  NFC: {nfc_name!r}")
                for p in paths:
                    raw_bytes = p.name.encode("utf-8")
                    is_nfc = raw_bytes == nfc_name.encode("utf-8")
                    size = p.stat().st_size
                    flag = "NFC" if is_nfc else "COMPAT"
                    print(f"    [{flag:6}] {size:5} bytes  hex={raw_bytes.hex()[:40]}...")
                total_dups += 1
        else:
            print(f"[OK]  {wiki_dir}: 0 NFC 重名（{len(by_nfc)} 個 unique pages）")

    print()
    if total_dups > 0:
        print(f"[FAIL] 共 {total_dups} 個 NFC 重名 — wiki_compiler 寫入 compatibility variant")
        print("  修法：1) 跑 unicodedata.normalize('NFC') 把舊檔合併")
        print("        2) wiki_compiler 寫檔前先 NFC 化檔名")
        return 1 if ci else 0

    print(f"[OK] 全部 {total_files} 個 wiki 檔無 NFC 衝突")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()
    sys.exit(main(args.ci))
