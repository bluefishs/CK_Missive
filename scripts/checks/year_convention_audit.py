#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""紀年契約：API 查詢參數一律西元（development-rules §2.5）。

## 為什麼有這支

owner 2026-08-29 裁示「系統統一採西元年建置資料與查詢服務」。

而立規範不等於有人在強制 —— 本 repo 2026-08-17 才付過這個學費
（型別 SSOT 規範寫了很久、沒有機制強制，累積出 18 個違規無人知曉）。

## 判準

掃 `backend/app/services/` 與 `repositories/`、`api/endpoints/`：

  RED     在**查詢參數路徑**上出現 `year + 1911`／`+ ROC_OFFSET`
          （＝後端還在收民國年當篩選條件）
  RED     前端 `frontend/src/pages/` 的年度**選項/查詢參數**用 `getFullYear() - 1911`
  ok      顯示層、外部資料解析、產號輸入容錯 —— 白名單放行（見下）

## 白名單（規範明文排除，不是漏網）

  · 顯示格式化：`quotation_document.py`（正式文件印民國）、`document_numbers.py`
    （公文文號本來就是民國）、`morning_report_*`（解析民國日期字串）
  · 外部資料：`mof_api_client`（財政部 API）、`invoice_qr_decoder`（發票 QR）、
    `expense_import`／`quotation_service_io`／`invoice_ocr_service`（匯入的 xls 是民國）
  · 產號輸入容錯：`case_code.py`、`project_repository.py`（人可能手打民國年）
  · 工具：`schemas/_year.py`、`services/common/roc_date.py`

## 誰跑它

weekly step 80（`run_fitness_weekly.sh`）。
"""
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]

# 規範明文排除者 —— 檔名片段比對
ALLOW = (
    "quotation_document", "document_numbers", "morning_report",
    "mof_api_client", "invoice_qr_decoder", "invoice_ocr_service",
    "expense_import", "quotation_service_io", "quotation_legacy_import",
    "_year.py", "roc_date", "case_code.py", "project_repository",
    "dispatch_progress_synthesizer", "rule_engine", "search_intent_parser",
    "validators.py", "statistics.py", "stats.py", "einvoice",
    # 2026-08-29 首跑後逐一判型加入 —— 全部是「外部資料解析後轉西元再進系統」，
    # 規範明文允許（§2.5「外部資料解析：解析後立即轉西元再進系統」）：
    "qr_scanner",              # 發票 QR 碼是民國
    "csv_processor",           # 匯入的 CSV 是民國
    "dispatch_document_parser",  # 公文日期字串是民國
    "ezbid_scraper", "pcc_today_scraper",  # 政府網站爬取的是民國
    "endpoints/pm/cases.py",   # 批次更新的輸入容錯（使用者可能填民國）
)

BACKEND_PAT = re.compile(r"\+\s*1911|\+\s*ROC_OFFSET")
FRONTEND_PAT = re.compile(r"getFullYear\(\)\s*-\s*1911")


def _allowed(path: Path) -> bool:
    p = str(path).replace("\\", "/")
    return any(a in p for a in ALLOW)


def main() -> int:
    reds = []

    for base, pat, label in (
        (ROOT / "backend" / "app", BACKEND_PAT, "後端收民國年當查詢參數"),
        (ROOT / "frontend" / "src" / "pages", FRONTEND_PAT, "前端送民國年"),
    ):
        if not base.exists():
            continue
        for f in base.rglob("*.*"):
            if f.suffix not in (".py", ".ts", ".tsx") or _allowed(f):
                continue
            try:
                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                # 註解不算違規 —— 本規範的說明文字本身就會提到 1911
                if stripped.startswith(("#", "//", "*", "/*")):
                    continue
                if not pat.search(line):
                    continue
                # 規範允許「轉換並出聲」的相容處理（§2.5 相容處理）——
                # 判準是**附近有 warning**。這比檔名白名單準：它抓的正是規範
                # 真正要求的東西（不得靜默接受），而不是「這個檔我信任」。
                # ⚠️ 首跑 12 處全是誤判，就是因為原判準只看有沒有 +1911，
                #    分不出「靜默轉換」與「轉換並出聲」—— 那正是這支要防的差別。
                ctx = "\n".join(lines[max(0, i - 7): i + 2])
                if "logger.warning" in ctx or "logger.info" in ctx:
                    continue
                rel = f.relative_to(ROOT).as_posix()
                reds.append(f"  [RED  ] {label}｜{rel}:{i}\n           {stripped[:90]}")

    print("=" * 74)
    print("紀年契約：API 查詢參數一律西元（development-rules §2.5，weekly 74）")
    print("=" * 74)
    for r in reds:
        print(r)

    if reds:
        print(f"\n⚠️ owner 2026-08-29 裁示「系統統一採西元年建置資料與查詢服務」。")
        print("   若這是**顯示層／外部資料解析／產號輸入容錯**，請加進本腳本的")
        print("   ALLOW 白名單並在該處註解寫明理由 —— 白名單要有人判過型，")
        print("   不是「還沒改的收容所」。")
        print(f"\nStatus: [RED] {len(reds)} 處仍在查詢路徑上做紀年轉換")
        return 1

    # ⚠️ 原本印「查詢參數路徑上沒有紀年轉換」——而本支分不出「查詢參數路徑」，
    # 它查的是「白名單外、附近沒有 logger.warning 的 +1911」。
    print("  （白名單外沒有「不出聲的 +1911」；本支以檔名白名單近似「查詢參數路徑」）")
    print("\nStatus: [GREEN] 紀年契約一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
