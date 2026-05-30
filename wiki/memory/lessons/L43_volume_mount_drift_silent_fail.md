---
title: L43 — Docker volume mount drift silent dormant (10h 災難級事故)
type: lesson
date: 2026-05-21
fqid: CK_Missive#L43
family: cross-file-ssot
related: [L41, L44, L45, L52]
---

# L43 — Docker volume mount drift silent fail

> **日期**：2026-05-21 14:35（修法完成）
> **觸發**：owner Google login 後業務 API 連環 500 (calendar / dispatch / digital-twin)
> **dormant**：~10 小時
> **規模**：4h 完整恢復 / 6 commits / 雙 dump 備份 + NAS 異地

---

## 5 重 silent fallback 疊加

1. `docker-compose.production.yml:216` 寫 `name: ck_missive_postgres_data` (空殼 17 tables/502 docs)
2. `docker-compose.dev.yml` / `infra.yml` / `pre_upgrade_backup.sh:33` 用 `ck_missive_postgres_dev_data` (真實 75 tables/1788 docs/24061 KG)
3. postgres init.sql 不報錯（空 volume 自動 init）
4. alembic 推進不需資料
5. `/health` 只驗 connection 不檢業務量
6. Prometheus 無 row count alert
7. session-start hook 顯示 healthy

→ 5/21 ~04:00 切 production compose 時 silent 掛錯 volume，dormant ~10h 直到 owner 觸發

---

## Plan A 10 步完整恢復 (14:30~14:35)

- 雙 dump 備份 (122K 空殼 + 77M 真實) + MD5 雙端驗證
- compose volume 改 `ck_missive_postgres_dev_data` + `external: true`
- 真實 DB 補跑 alembic `20260521a001` (department/position 欄位)
- backend 0 UndefinedColumn / business endpoints 200

---

## 5 層防禦落地

| 防禦層 | 檔案 | commit |
|---|---|---|
| alembic migration | `20260521a001` (idempotent ADD COLUMN IF NOT EXISTS) | `e1d7d3e7` |
| `/health` business_data_present 503 防禦 | row count < threshold → cloudflared healthcheck fail | `097cdf68` |
| fitness step 38 | `docker_compose_volume_consistency.py` 揭發同型 redis chronic drift | `ad4451b8` |
| NAS 異地備份 | `Z:/.../#systembackup/CK_Missive_INCIDENT_20260521_volume_mount_drift/` | `acbd3e49` |
| session record | `session_20260521_l43_volume_drift_recovery.md` | （memory）|

---

## 治理立法（首例 L4x family 跨檔 SSOT）

L43 = 跨檔 SSOT 治理失效第一案，後續觸發：
- L41 JWT secret 跨 repo drift
- L44 SSO frontend session lock cookie storage 不同步
- L45 compose healthcheck override Dockerfile HEALTHCHECK
- L52 paths.py vs compose mount target drift

最終立法：`.claude/rules/cross-file-ssot-governance.md` §1-§6 規範

---

## 元洞察

「process up」≠「業務真活」。healthcheck 必須驗業務量（row count threshold），不只連線通。
這是 L43 真正最深的教訓 — 觀測層必須 reflect 業務層。
