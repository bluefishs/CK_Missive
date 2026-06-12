"""Calendar Sync Reconciliation Audit — runtime 狀態對賬（2026-06-11，強化圖譜治理 第三支柱）

一般化「DB status 說 synced 但外部真實不符」的 runtime-drift 類（L70 核心病灶）：
DB `google_sync_status='synced'` 不代表 Google 端真有事件——本次揭發整批 synced 但 Google 404
（因 calendar_id drift 推進隱形日曆）。靜默 dormant 直到 owner 報「看不到」。

此 audit 抽樣 N 筆 synced 事件，用服務帳號查證 Google 端是否真存在，回報 drift 率。
治理意義：凡「寫一次 status 就不再回頭驗證」的欄位都該有對賬機制。需服務帳號（容器內 cron）。

Usage（容器內）：
  python /app/scripts/checks/calendar_sync_reconciliation_audit.py [--sample 30] [--strict]
"""
from __future__ import annotations

# cp950 host robustness (L49.8): printing CJK to Windows terminal raises UnicodeEncodeError
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import argparse
import os
import sys

SAMPLE_DEFAULT = 30
DRIFT_THRESHOLD_PCT = 10.0  # synced 但 Google 不存在 > 10% → RED


def main(sample: int = SAMPLE_DEFAULT, strict: bool = False) -> int:
    try:
        import psycopg2  # type: ignore
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except Exception as e:
        print(f"[SKIP] 依賴不可用（host 端）— 此 audit 需於容器內跑: {e}")
        return 0

    url = (os.environ.get("DATABASE_URL") or "").replace("postgresql+asyncpg://", "postgresql://")
    cred_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "./GoogleCalendarAPIKEY.json")
    if not os.path.isabs(cred_path):
        cred_path = os.path.join("/app", cred_path.lstrip("./"))
    cal_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
    if not url or not os.path.exists(cred_path):
        print("[SKIP] 無 DATABASE_URL 或憑證")
        return 0

    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, google_event_id FROM document_calendar_events "
            "WHERE google_sync_status='synced' AND google_event_id IS NOT NULL "
            "ORDER BY RANDOM() LIMIT %s", (sample,)
        )
        rows = cur.fetchall()
        cur.close(); conn.close()
    except Exception as e:
        print(f"[SKIP] DB 失敗: {e}")
        return 0

    if not rows:
        print("[INFO] 無 synced 事件可抽樣")
        return 0

    creds = service_account.Credentials.from_service_account_file(
        cred_path, scopes=["https://www.googleapis.com/auth/calendar"])
    svc = build("calendar", "v3", credentials=creds)

    found = missing = 0
    miss_ids = []
    for eid, gid in rows:
        try:
            svc.events().get(calendarId=cal_id, eventId=gid).execute()
            found += 1
        except Exception:
            missing += 1
            miss_ids.append(eid)

    total = found + missing
    pct = missing / total * 100 if total else 0
    print("=== Calendar Sync Reconciliation Audit（runtime 狀態對賬）===")
    print(f"  抽樣 {total} 筆 synced | Google 端存在 {found} | 消失(synced≠real) {missing} ({pct:.1f}%)")
    print(f"  目標日曆: {cal_id[:40]}")
    if miss_ids:
        print(f"  消失事件 id: {miss_ids[:15]}")

    status = "GREEN" if pct <= DRIFT_THRESHOLD_PCT else "RED"
    print(f"\nStatus: {status}（門檻 ≤{DRIFT_THRESHOLD_PCT}%）")
    if status == "RED":
        print("[WARN] synced 但 Google 不存在超門檻 → 檢查 calendar_id drift / 事件被刪 → 重推同步")
        if strict:
            return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=SAMPLE_DEFAULT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    sys.exit(main(sample=args.sample, strict=args.strict))
