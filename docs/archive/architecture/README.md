# docs/architecture 歷史歸檔

這裡放**已完成任務、不再被引用**的一次性報告與計畫。

## 為什麼歸檔而不是刪除

它們記錄了當時的判斷與量測，覆盤時仍可能需要回頭看。
但留在 `docs/architecture/` 會有兩個代價：

1. 每次找文件都要在一堆歷史紀錄裡撈現行規範
2. `doc_reference_integrity_audit` 的反向檢查會一直把它們報成「無人引用」——
   而那個訊號應該留給**真正該被索引卻沒被索引**的現行文件

## 歸檔判準（2026-08-09 立）

| 條件 | 處置 |
|---|---|
| 無任何引用 **且** 是一次性報告／已完成計畫 | 移入本目錄 |
| 無任何引用 **但** 內容仍在生效（契約／協定） | **接進索引**，不歸檔 |
| 日期型檔名（`*_20260530`、`*_2026Q1`） | 留在原地，反向檢查本來就不計它們 |

## 2026-08-09 首批（4 份）

| 檔案 | 最後更新 | 為何歸檔 |
|---|---|---|
| `KG_MISSING_LINKS_BACKLOG.md` | 2026-05-03 | 一次性 backlog，wiki↔KG 連結率已由 `wiki_kg_link_audit`（weekly 2）持續監看 |
| `KUNGE_EVOLUTION_STORY.md` | 2026-05-01 | 給人讀的敘事，非規範 |
| `KUNGE_LEARNING_VERIFICATION_V2.md` | 2026-04-30 | v5.11 的一次性驗證報告 |
| `PROJECT_OPTIMIZATION_INTEGRATION_PLAN.md` | 2025-12-30 | 執行日期 2025-09-10，早已完成 |

**未歸檔**：`SOUL_CROSS_REPO_PROTOCOL.md` 與 `WS_D_BOUNDARY_CONTRACT.md` ——
前者引用的 `sync_soul_to_hermes.sh` 與 `soul_mirror_drift_check.py` 都還在跑（weekly 1），
後者是 CK_Missive 側的邊界契約仍在生效。兩份改為接進索引。
