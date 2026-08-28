# -*- coding: utf-8 -*-
"""異地備份完整性稽核 —— 問的是「現在真的還原得回來嗎」（2026-08-10）。

## 為什麼要有這一支

2026-08-10 owner 問「確認 NAS 有完整備份」，查下去答案是**沒有**：

    公文資料  → NAS 30 份 dump          ✓
    公文附件  → **一份都沒有**            ✗  異地同步腳本第 97 行寫死 robocopy "*.sql"
    金鑰憑證  → **一份都沒有**            ✗  .env 95 項含 15 把金鑰，只有 D 槽一份

而本機那份附件備份也早就停了：`attachments_latest` 最後更新 2026-05-18，
**84 天沒動過**，落後 317 檔 / 362MB —— 根因是 scheduler 裡根本沒有附件備份的排程，
它只能從 /admin/backup 手動觸發，而最後一次按是 05-18。
所以在那天之前，那 317 個附件在全世界只有一份。

三個缺口沒有任何一個會報錯。`remote_backup.json` 顯示 `last_sync_result: success`、
Windows 排程 `LastTaskResult=0`、NAS 上檔案一天比一天多 —— **全都是綠的**。
因為沒有任何人在問「備份的東西夠不夠還原出一套能跑的系統」。

## 判準：四類缺一不可

  1. 資料庫 dump   —— 份數、最新一份的新鮮度、**尾端完整性**
  2. 里程碑快照     —— 存在即可（不輪替，是回得去某時間點的錨點）
  3. 公文附件       —— 涵蓋率（本機每一個檔都要在 NAS 有對應）
  4. 金鑰與憑證     —— 加密檔的新鮮度

**尾端完整性是刻意加的**：截斷的 dump 症狀是「檔案在、大小看起來也還好、
還原到一半才斷」。只看檔案存不存在、大小合不合理，抓不到它。
pg_dump 的輸出結尾一定是 `PostgreSQL database dump complete`。

## 這支不做什麼

不做完整還原測試（500MB × 每週太貴）。完整還原測試是**月度**動作，
程序寫在 `docs/runbooks/disaster-recovery.md`。
本檔只回答「素材齊不齊、有沒有腐爛」，不回答「還原出來的系統對不對」——
後者 2026-08-10 實測過一次，發現兩個缺陷（見該 runbook）。

## 用法

  python scripts/checks/offsite_backup_completeness_audit.py
  python scripts/checks/offsite_backup_completeness_audit.py --self-test
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

REPO = Path(__file__).resolve().parents[2]
NAS = Path(r"\\CKNAS\CK_Project\#Project_data")

DB_DIR = NAS / "missive_databsae"
MS_DIR = DB_DIR / "_milestones"
ATTACH_DIR = NAS / "missive_attachments"
SECRETS_DIR = NAS / "missive_secrets"
LOCAL_UPLOADS = REPO / "backend" / "uploads"

MIN_DUMPS = 20            # 保留 30 份，低於 20 代表輪替或同步出問題
DUMP_MAX_AGE_H = 30       # 每日 02:00 產、03:00 同步 → 逾 30h 就是漏了一天
SECRETS_MAX_AGE_H = 30
DUMP_TAIL_MARKER = b"PostgreSQL database dump complete"


def _age_hours(p: Path) -> float:
    return (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)).total_seconds() / 3600


def check_db(reds: list[str], rows: list[str]) -> None:
    if not DB_DIR.exists():
        reds.append(f"資料庫備份目錄不存在: {DB_DIR}")
        rows.append("  [RED  ] 資料庫 dump        目錄不存在")
        return
    dumps = sorted(DB_DIR.glob("ck_missive_backup_*.sql"), key=lambda p: p.stat().st_mtime)
    if len(dumps) < MIN_DUMPS:
        reds.append(f"資料庫 dump 只有 {len(dumps)} 份（低於 {MIN_DUMPS}）")
    if not dumps:
        rows.append("  [RED  ] 資料庫 dump        0 份")
        return
    latest = dumps[-1]
    age = _age_hours(latest)
    if age > DUMP_MAX_AGE_H:
        reds.append(f"最新 dump 已 {age:.1f}h 未更新（{latest.name}）")

    # 尾端完整性：截斷的 dump 大小看起來正常，只有結尾看得出來
    tail_ok = False
    try:
        with open(latest, "rb") as fh:
            fh.seek(max(0, latest.stat().st_size - 4096))
            tail_ok = DUMP_TAIL_MARKER in fh.read()
    except OSError as exc:
        reds.append(f"無法讀取最新 dump 尾端: {exc}")
    if not tail_ok:
        reds.append(f"最新 dump 尾端缺少完成標記 → 可能截斷（{latest.name}）")

    size_mb = latest.stat().st_size / 1024 / 1024
    rows.append(f"  [{'GREEN' if tail_ok and age <= DUMP_MAX_AGE_H else 'RED  '}] "
                f"資料庫 dump        {len(dumps)} 份｜最新 {latest.name[-19:-4]} "
                f"({size_mb:.0f}MB, {age:.1f}h 前)｜尾端{'完整' if tail_ok else '不完整'}")


def check_milestones(reds: list[str], rows: list[str]) -> None:
    if not MS_DIR.exists():
        reds.append("里程碑快照目錄不存在（PREUPGRADE / pre_pm2 等回得去的錨點）")
        rows.append("  [RED  ] 里程碑快照        目錄不存在")
        return
    files = [p for p in MS_DIR.iterdir() if p.is_file()]
    if not files:
        reds.append("里程碑快照目錄是空的")
    total_mb = sum(p.stat().st_size for p in files) / 1024 / 1024
    rows.append(f"  [{'GREEN' if files else 'RED  '}] 里程碑快照        "
                f"{len(files)} 份 / {total_mb:.0f}MB")


def check_attachments(reds: list[str], rows: list[str]) -> None:
    if not LOCAL_UPLOADS.exists():
        reds.append(f"本機附件目錄不存在: {LOCAL_UPLOADS}")
        return
    if not ATTACH_DIR.exists():
        reds.append(f"附件異地目錄不存在: {ATTACH_DIR} —— 附件沒有任何異地備份")
        rows.append("  [RED  ] 公文附件          異地目錄不存在")
        return
    local = sum(1 for _ in LOCAL_UPLOADS.rglob("*") if _.is_file())
    archive_dir = ATTACH_DIR / "_longname_archive"
    remote = 0
    archived_zips = 0
    for p in ATTACH_DIR.rglob("*"):
        if not p.is_file():
            continue
        if archive_dir in p.parents:
            archived_zips += 1
        else:
            remote += 1
    # 長檔名（>255 bytes，中文約 85 字）存不進 Linux/Samba，改打包上傳。
    # 因此本機檔數 > NAS 直接檔數是預期的，差額必須被 zip 覆蓋。
    gap = local - remote
    ok = gap == 0 or (gap > 0 and archived_zips > 0)
    if not ok:
        reds.append(f"附件涵蓋不全：本機 {local} 檔、NAS {remote} 檔、缺 {gap} 且無打包封存")
    rows.append(f"  [{'GREEN' if ok else 'RED  '}] 公文附件          "
                f"本機 {local}｜NAS 直接 {remote}｜打包封存 {archived_zips} "
                f"({'涵蓋完整' if ok else f'缺 {gap}'})")


def check_secrets(reds: list[str], rows: list[str]) -> None:
    if not SECRETS_DIR.exists():
        reds.append(f"金鑰異地目錄不存在: {SECRETS_DIR} —— "
                    "沒有它，資料還原回來系統仍然起不來")
        rows.append("  [RED  ] 金鑰與憑證        異地目錄不存在")
        return
    encs = sorted(SECRETS_DIR.glob("secrets_*.enc"), key=lambda p: p.stat().st_mtime)
    if not encs:
        reds.append("金鑰異地目錄是空的")
        rows.append("  [RED  ] 金鑰與憑證        0 份")
        return
    latest = encs[-1]
    age = _age_hours(latest)
    if age > SECRETS_MAX_AGE_H:
        reds.append(f"最新金鑰備份已 {age:.1f}h 未更新（{latest.name}）")
    rows.append(f"  [{'GREEN' if age <= SECRETS_MAX_AGE_H else 'RED  '}] 金鑰與憑證        "
                f"{len(encs)} 份｜最新 {latest.name} ({age:.1f}h 前)")


def self_test() -> int:
    """判準若不會動，看起來會跟很乾淨一模一樣。用假資料驗它會不會紅。"""
    import tempfile
    print("=== 判準鑑別力自我測試 ===")
    failed = 0
    tmp = Path(tempfile.mkdtemp())

    # 尾端完整性：完整 vs 截斷
    good = tmp / "good.sql"
    good.write_bytes(b"x" * 100 + b"--\n-- PostgreSQL database dump complete\n--\n")
    bad = tmp / "bad.sql"
    bad.write_bytes(b"x" * 200)
    for label, f, expect in (("完整 dump 不該紅", good, False), ("截斷 dump 必須紅", bad, True)):
        with open(f, "rb") as fh:
            fh.seek(max(0, f.stat().st_size - 4096))
            has = DUMP_TAIL_MARKER in fh.read()
        got = not has
        mark = "✓" if got == expect else "✗"
        if got != expect:
            failed += 1
        print(f"  {mark} {label:<28} 預期紅={int(expect)} 實際={int(got)}")

    # 附件涵蓋率判準
    cases = [
        ("本機=NAS 不該紅", 100, 100, 0, False),
        ("缺檔但有打包 不該紅", 100, 98, 1, False),
        ("缺檔且無打包 必須紅", 100, 98, 0, True),
        ("NAS 全空 必須紅", 100, 0, 0, True),
    ]
    for label, local, remote, zips, expect in cases:
        gap = local - remote
        ok = gap == 0 or (gap > 0 and zips > 0)
        got = not ok
        mark = "✓" if got == expect else "✗"
        if got != expect:
            failed += 1
        print(f"  {mark} {label:<28} 預期紅={int(expect)} 實際={int(got)}")

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    if failed:
        print(f"\n✗ 判準有 {failed} 項不符預期")
        return 2
    print("\n✓ 判準有鑑別力（正向 3 例、負向 3 例）")
    return 0


#: portfolio 各專案在 NAS 上的目錄。**這一段只報不判紅** ——
#: 我不知道別的 repo 的備份頻率與意圖，判紅會製造我修不了的噪音。
#: 但「完全沒有人在問這個專案有沒有備份」是更糟的狀態：
#: 2026-08-23 遞迴掃描發現 **CK_Website 與 dataform 在 NAS 上完全沒有目錄**，
#: 而 CK_Website 是四個系統的 IdP。那不是誰做錯，是**沒有任何東西在問**。
#: ⇒ 這一段的價值不在判定，在讓缺口每週被看見一次。
#: (NAS 目錄, 標籤, 負責的 Windows 排程名)
#:
#: ⚠️⚠️ **「目的地最新檔年齡」對鏡像型備份有歧義**（CK_AaaP 2026-08-23 在我這支
#: 剛推的程式碼上抓到，而且是在**我自己的目錄**上）：robocopy 保留來源 mtime，
#: 所以目的地最新檔 43 小時前，意思是「**來源 43 小時沒有新東西**」，
#: 不是「備份 43 小時沒跑」。他們的狀態檔白紙黑字寫著
#: `ran_at 08-23T04:00 成功` 而 `newest_file 08-22T00:01` —— 備份是好的。
#:
#: ⇒ 依 CK_AaaP CONVENTIONS §11：**`ran_at` 與 `newest_file` 要分開記**。
#:    前者答「它有沒有在跑」，後者答「有沒有東西可搬」。
#:    只有其中一個，43.1 小時那一題就無解 —— 而我第一版只有後者。
#: 這裡的 `ran_at` 取自 Windows 排程的 `LastRunTime`（作業系統自己的紀錄，
#: 不另建第二份事實）。取不到就明講取不到，不用 newest_file 頂替。
PORTFOLIO_EXPECTED = {
    "missive_databsae": ("CK_Missive 資料庫", "CK-Missive-Offsite-Backup"),
    "missive_attachments": ("CK_Missive 公文附件", "CK-Missive-Offsite-Backup"),
    "missive_secrets": ("CK_Missive 金鑰憑證", "CK-Missive-Offsite-Backup"),
    "lvrland_database": ("CK_lvrland_Webmap", "CK_lvrland_Webmap-Offsite-Backup"),
    "pilemgmt_database": ("CK_PileMgmt", "CK_PileMgmt_DB_Backup"),
    "digitaltunnel_minio": ("CK_DigitalTunnel MinIO", "CK_DigitalTunnel-MinIO-Offsite"),
    "governance_records": ("CK_AaaP 治理紀錄", "CK_AaaP_GovernanceRecordsBackup"),
    "CK_FacilityDev_Backups": ("CK_FacilityDev", None),
    # 2026-08-28 實測移入：目錄 21 檔、排程 CK_lvrland_dataform-Offsite-Backup
    # rc=0 當日 13:45 跑過 ⇒ 原本列在 PORTFOLIO_MISSING 的「沒有排程」已過期。
    "dataform_workspace": ("CK_lvrland_dataform", "CK_lvrland_dataform-Offsite-Backup"),
    # 2026-08-28 新增：先前**兩邊清單都沒有它** —— 而本檔註解自己寫著
    # 「空著等於默認它不存在」。NAS 上 20 檔但**最新停在 2026-06-30**，
    # 且全機掃不到任何對應排程（它不是 ^CK 開頭，_task_last_run 本來也抓不到）。
    # FT_StorageTank 的 STATUS 記「異地備份機制實測通過、**NAS 路徑待填**」
    # ⇒ 那 20 檔是一次性手動放的，之後沒有自動化在維護。
    # 列進來是為了讓它每週被問一次，不是為了判它紅。
    "StorageTank_database": ("FT_StorageTank", None),
    # 2026-08-28 移入：CK_Website 當日補上備份第四段（`backup_CKProject.bat`
    # 的 WebsiteSecrets 段），我方獨立清點 45 檔 / 1.94 MB / 40 份 KV 快照
    # / RS256 私鑰在。⚠️ 它**沒有** `_backup-status.json`，所以這一列會退回
    # ran_at + newest 推論 —— 那是誠實的降級，不是故障。
    "ckwebsite_secrets": ("CK_Website 金鑰與 KV 快照", "CKProject_DailyBackup"),
}


def _task_last_run() -> dict:
    """讀 Windows 排程的 LastRunTime／LastTaskResult —— 這是 `ran_at`。

    取自作業系統自己的紀錄，**不另建第二份事實**（本專案已立的判準）。
    讀不到就回空 dict，呼叫端要明講「取不到」而不是拿 newest_file 頂替。
    """
    import json as _j
    import subprocess as _sp
    ps = (
        "Get-ScheduledTask | Where-Object {$_.TaskName -match '^CK'} | "
        "ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; "
        "[pscustomobject]@{n=$_.TaskName; "
        "r=(($i.LastRunTime).ToString('o')); c=$i.LastTaskResult} } | "
        "ConvertTo-Json -Compress"
    )
    try:
        out = _sp.run(["powershell", "-NoProfile", "-Command", ps],
                      capture_output=True, timeout=60)
        data = _j.loads((out.stdout or b"").decode("utf-8", "replace") or "[]")
    except Exception:
        return {}
    if isinstance(data, dict):
        data = [data]
    return {d["n"]: (d.get("r"), d.get("c")) for d in data if d.get("n")}
#: 已知缺口 —— 列出來才有人補。空著等於默認它不存在。
#: ⚠️ 2026-08-28 實測更正兩處，**兩處都是「清單本身過期」而不是備份出事**：
#:   ① `CK_lvrland_dataform` 已移入 EXPECTED —— `dataform_workspace` 21 檔、
#:      排程 `CK_lvrland_dataform-Offsite-Backup` rc=0 當日 13:45 跑過。
#:      原記「Windows 排程也沒有對應任務」在 08-23 寫時為真，5 天後就過期了。
#:   ② `FT_StorageTank` 先前**兩邊清單都沒有** ⇒ 沒有任何人在問它。
#:      NAS 20 檔但最新停在 2026-06-30，且掃不到對應排程。
#: ⇒ 判準：**這份清單本身需要有人定期對帳，否則它會安靜地過期**——
#:   一個過期的「已知缺口」清單，與沒有清單的差別只在於它看起來像有人在管。
#: ⚠️ 2026-08-24 措辭更正 —— 這台環境有**兩個備份區，用途不同**（owner 澄清）：
#:   `\CKNAS\CK_Project\#Project_data`（192.168.50.250）＝**異地備份區**
#:                                                          （專案資料庫與附件）
#:   `\192.168.50.212\CKProject_Backup`                  ＝**本機專案備份區**
#: 本稽核只掃 250 —— 那是「異地」的定義所在，掃它是對的。
#: 但先前寫「完全沒有異地備份」語意過強：CK_Website 在 212 上**有備份**
#: （他們 08-24 指正，我查證 X: 確實對應 212 且分享名是 CKProject_Backup 不是
#: 我猜的 CK_Website）。⇒ 正確說法是「**不在異地備份區**」，不是「沒有備份」。
#: 這個區分很實際：本機備份與被保護的資料**在同一個場所**，
#: 場所級事故（火、竊、電力）會一起沒有 —— 那正是異地備份要防的。
#: 2026-08-28 CK_Website 已補上 —— 這一條的歷史值得留著，因為**缺口的形狀被修正過兩次**：
#:   08-11 記「kv-snapshot 失敗、備份停在 07-18」→ 08-18 他們修好，記載過期；
#:   08-24 我記「完全沒有異地備份」→ 語意過強，他們在本機備份區（212）有；
#:   08-28 他們再指出「沒有異地備份」仍高估 —— **程式碼有 GitHub 這個異地副本**，
#:         真正沒有異地的是 **KV 快照**（四系統的員工名冊／身份權威）
#:         與 **RS256 私鑰**（JWKS 簽發根，遺失即四系統 SSO 要重來）。
#:   ⇒ 判準：**「有沒有備份」問不出東西，要問「哪一份不見了會怎樣」** ——
#:     前者的答案在三次修正裡都是「有」，而那三次講的是不同的東西。
PORTFOLIO_MISSING: dict[str, str] = {}
STALE_HOURS = 72.0


def check_portfolio(rows: list[str]) -> list[str]:
    """掃 portfolio 各專案的 NAS 目錄新鮮度（**遞迴**）。

    ⚠️ 一定要遞迴：2026-08-23 第一版只數頂層檔案，於是 missive_attachments／
    lvrland_database／digitaltunnel_minio 全部顯示「空」—— **五個假警報**，
    因為那幾類是放在子目錄的。差一點就通報五個專案「你們沒有備份」。
    量測方法沒先驗，結論就不可信。
    """
    import json as _json
    import time as _t
    from datetime import datetime as _dt
    notes: list[str] = []
    tasks = _task_last_run()
    rows.append("")
    rows.append("  ── portfolio 各專案（只報不判紅，我不知道別人的備份意圖）──")
    rows.append("     ran_at＝排程上次執行（有沒有在跑）｜"
                "newest＝目的地最新檔（有沒有東西可搬）")
    for d, (label, task) in PORTFOLIO_EXPECTED.items():
        base = NAS / d
        if not base.exists():
            rows.append(f"  [?    ] {label:<22} 目錄不存在")
            notes.append(f"{label}：NAS 目錄不存在")
            continue
        n, newest = 0, 0.0
        for dp, _dirs, files in os.walk(base):
            for f in files:
                try:
                    st = os.stat(os.path.join(dp, f))
                    n += 1
                    newest = max(newest, st.st_mtime)
                except OSError:
                    pass
        if n == 0:
            rows.append(f"  [?    ] {label:<22} 完全沒有檔案")
            notes.append(f"{label}：目錄在但沒有任何檔案")
            continue
        age = (_t.time() - newest) / 3600

        # ── 優先讀目的地狀態檔 ──
        # CK_AaaP 2026-08-23：我原本說「跨 repo 觀察者只有兩個外部可見的數字」，
        # 他們指出**那不是限制、是他們的漏洞** —— 狀態檔只寫在本機是可以改的，
        # 於是把同一份也寫到 `<dest>/_backup-status.json`（刻意在資料寫完之後
        # 才寫，使它不會早於它所描述的那批資料）。
        # ⇒ 有這支就不必猜「來源沒變還是同步空跑」，產出端自己說了。
        # 沒有也不算錯（其他 repo 還沒跟進），退回下面的 ran_at + newest 推論。
        st = base / "_backup-status.json"
        if st.exists():
            try:
                sd = _json.loads(st.read_text(encoding="utf-8-sig"))
                res = str(sd.get("result", "?"))
                saved = sd.get("saved", sd.get("files", "?"))
                sa = _dt.fromisoformat(str(sd.get("ran_at", "")).split(".")[0])
                sa_age = (_dt.now() - sa).total_seconds() / 3600
                tag = "ok   " if (res == "ok" and sa_age <= STALE_HOURS) else "STALE"
                rows.append(f"  [{tag}] {label:<22} {n:>5} 檔｜狀態檔 result={res}"
                            f" ran {sa_age:.1f}h 前 files={saved}")
                if tag != "ok   ":
                    notes.append(f"{label}：狀態檔 result={res}、ran {sa_age:.0f}h 前")
                continue
            except Exception as e:
                # 狀態檔壞掉不得靜靜退回年齡判準 —— 那會讓「狀態檔壞了」隱形
                # （CK_AaaP 同日的第三點，他們自己也踩到）。
                print(f"  [WARN] {label} 狀態檔讀取失敗，退回年齡判準："
                      f"{type(e).__name__}: {e}", file=sys.stderr)

        # ran_at —— 排程有沒有在跑。取不到就說取不到，不用 newest 頂替。
        ran_txt, ran_age, rc = "ran_at 取不到", None, None
        if task and task in tasks:
            iso, rc = tasks[task]
            try:
                ran = _dt.fromisoformat((iso or "").split(".")[0])
                ran_age = (_dt.now() - ran).total_seconds() / 3600
                ran_txt = f"ran {ran_age:.1f}h 前 rc={rc}"
            except Exception:
                ran_txt = f"ran_at 無法解析({iso})"

        # 判準：**先看 ran_at**。它有跑且成功 ⇒ newest 舊只代表來源沒新東西，
        # 那是合理空不是故障（CK_AaaP 08-23 在我這支程式碼上抓到的歧義）。
        ran_ok = ran_age is not None and ran_age <= STALE_HOURS and rc == 0
        if age <= STALE_HOURS:
            tag = "ok   "
        elif ran_ok:
            # 排程有跑且成功，但目的地很久沒有新東西。
            # **我分不出這是「來源真的沒變」還是「同步空跑」** ——
            # 那要產出端自己說（CK_AaaP §11：`saved: N`），而我拿不到別的
            # repo 的狀態檔。⇒ 誠實的做法是把兩個數字並陳、標成待確認，
            # 不宣稱故障，也不因為 rc=0 就當作沒事。
            # 08-23 實例：DT MinIO `ran 17.2h rc=0` 但 `newest 89.2h`，
            # 而我通報後他們一跑就產生新檔 ⇒ 那次確實不是「合理空」。
            tag = "待確認"
            notes.append(f"{label}：排程有跑（{ran_txt}）但目的地最新已 {age:.0f}h"
                         f" —— 是來源沒變還是同步空跑？需該 repo 回報搬了幾個物件")
        else:
            tag = "STALE"
            why = f"排程 {ran_txt}" if ran_age is not None else "且查不到對應排程"
            notes.append(f"{label}：目的地最新 {age:.0f}h、{why}")
        rows.append(f"  [{tag}] {label:<22} {n:>5} 檔｜newest {age:>6.1f}h｜{ran_txt}")
    for repo, why in PORTFOLIO_MISSING.items():
        rows.append(f"  [缺口 ] {repo:<24} NAS 上沒有任何目錄")
        notes.append(f"{repo}：沒有異地備份 —— {why}")
    return notes


def _print_scope_limits() -> None:
    """把這支檢查**不驗**的東西印出來。

    2026-08-28：CK_Website 的 `ckwebsite_secrets` 同時發生三件事 ——
    少了 5 個檔、缺了 SSO 簽章私鑰（`.pem`）、40 檔**全部未加密** ——
    而本檔對它回報 `[ok]`。**三件一件都看不出來**，因為它只數檔案數與新鮮度。

    ⇒ 我驗的是「有沒有備份、新不新鮮」，要保證的卻是「災難時還原得回來」。
      **一份缺了簽章私鑰的備份，在檔案數與新鮮度上完全健康。**

    刻意**不**把本檔改成驗內容（那會讓它變成另一個東西，而且我不該替各 repo
    決定哪些檔是關鍵）。改為誠實聲明邊界 ——
    **一個說出自己不驗什麼的檢查，比一個看起來什麼都驗的檢查有用，
    因為讀的人知道還缺什麼。**
    """
    print("  註：本檔只驗素材齊不齊，不驗還原出來對不對。")
    print("      完整還原測試是月度動作，見 docs/runbooks/disaster-recovery.md")
    print("  ⚠️ 本檔**不驗**「關鍵檔在不在」與「是否加密」——")
    print("      這兩者由各 repo 自己的檢查負責"
          "（CK_Website ＝ `check-secrets-offsite.cjs`）。")
    print("      2026-08-28 實例：某目錄少了簽章私鑰且全未加密，本檔仍報 [ok]。")


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    print("=" * 70)
    print("異地備份完整性稽核 —— 現在真的還原得回來嗎")
    print("=" * 70)

    if not NAS.exists():
        print(f"\n✗ NAS 不可達: {NAS}")
        print("  拒絕執行 —— 「連不上」不得被讀成「備份沒問題」。")
        return 2

    reds: list[str] = []
    rows: list[str] = []
    check_db(reds, rows)
    check_milestones(reds, rows)
    check_attachments(reds, rows)
    check_secrets(reds, rows)
    portfolio_notes = check_portfolio(rows)

    print()
    for r in rows:
        print(r)

    print("\n" + "=" * 70)
    if reds:
        print(f"RED: {len(reds)} 項")
        for r in reds:
            print(f"  · {r}")
        print("\n  四類缺一不可 —— 少任何一類，災難時就是「資料回得來、系統起不來」。")
        return 2
    if portfolio_notes:
        print(f"YELLOW（portfolio，非本 repo 故障）: {len(portfolio_notes)} 項")
        for n in portfolio_notes:
            print(f"  · {n}")
        print()
        print("  這一段只報不判紅 —— 但**沒有人在問**才是最糟的狀態，"
              "所以它每週都會出現在這裡直到被處理。")
        print()
        # 2026-08-28：原本印完「YELLOW: N 項」仍 `return 0`，
        # 而 run_fitness_weekly 的 run_step **只讀退出碼、不讀輸出**
        # ⇒ 那 N 項在 weekly 摘要裡完全不存在，
        # 上一行「每週都會出現在這裡直到被處理」的前提從來沒有被滿足。
        #
        # 修法用本 repo 既有的三態語意：0=GREEN / 1=YELLOW / 2+=RED。
        # 回 1 之後它會進 weekly 的 WARN_STEPS（摘要看得見），
        # 而 weekly 的 exit 1 只由 FAIL_COUNT 觸發 ⇒ **cron 不會因此失敗**。
        #
        # 「不替別的 repo 判紅」這個克制是對的，保留；
        # 但**不判紅與不可見不是同一件事**，區分它們的成本只是這個退出碼。
        # （判準來自 CK_AaaP §41 的同型修法：「摘要行要帶覆蓋數 ——
        #   drift 只印這一行，缺口若只在明細裡等於沒印」。）
        print(f"GREEN（本 repo 四類）: 齊全且新鮮（資料庫／里程碑／附件／金鑰）"
              f" —— 但 portfolio 另有 {len(portfolio_notes)} 項待確認，見上")
        _print_scope_limits()
        return 1
    print("GREEN: 四類異地備份齊全且新鮮（資料庫／里程碑／附件／金鑰）")
    _print_scope_limits()
    return 0


if __name__ == "__main__":
    sys.exit(main())
