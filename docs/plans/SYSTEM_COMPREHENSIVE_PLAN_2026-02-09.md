# 系統整體性建議規劃事項 (System Comprehensive Planning Recommendations)

> **建立日期**: 2026-02-09
> **版本**: v1.0.0
> **專案階段**: 後期優化與自動化部署關鍵期 (Post-Launch Optimization & Automation Phase)

---

## 壹、 現況分析總結 (Executive Summary)

目前的系統核心功能已具備，特別是近期針對**派工單與公文的多對多關聯修復**以及**資料遷移腳本**的建立，顯著提升了資料的一致性與可靠性。然而，系統正面臨從「開發環境」邁向「生產環境自動化」的關鍵轉折點。

**當前核心挑戰**：
1.  **部署瓶頸**：QNAP NAS 的 SSH 連線問題阻礙了自動化部署流程，目前仍依賴半手動操作。
2.  **維運效率**：缺乏完整的 CI/CD 自動化（GitOps），導致部署耗時且容易產生人為失誤。
3.  **程式碼品質**：前端仍存有大量 `console.log` 與 `any` 型別，後端測試覆蓋率雖有提升但仍需加強 E2E 整合測試。

---

## 貳、 關鍵議題與立即行動方案 (Critical Issues & Immediate Actions)

### 2.1 生產環境部署阻礙 (High Criticality)
**問題描述**：QNAP SSH Port 22 無法連線，導致 Ansible/GitHub Actions 無法直接部署。
**行動方案**：
1.  **短期解法 (本週)**：
    *   **Container Station 手動部署**：作為暫時替代方案，確保新版本 (v1.33.0) 能上線。
    *   **Sidecar SSH Container**：嘗試在 Docker Compose 中加入一個專門的 SSH 服務容器，繞過 QNAP 本機 SSH 限制，作為部署跳板。
2.  **根本解法 (兩週內)**：
    *   排查 QNAP 防火牆規則與 `AllowUsers` 設定。
    *   若 QNAP 限制無法解除，評估改用 **Portainer Agent** 進行部署管理。

### 2.2 資料一致性遷移 (High Criticality)
**問題描述**：派工單與公文的關聯資料需同步至新表結構。
**行動方案**：
1.  **執行遷移腳本**：在生產環境執行 `backend/app/scripts/sync_dispatch_document_links.py`。
2.  **驗證機制**：執行後務必使用 `--verify` 參數確認資料完整性，並抽查 3-5 筆複雜關聯案件。

---

## 參、 系統架構優化建議 (Architecture Optimization)

### 3.1 後端架構 (Backend - Python/FastAPI)
*   **ORM 關聯增強**：
    *   建議在 `OfficialDocument` 模型中補全 `back_populates`，確保雙向查詢的便利性（如從公文直接查詢相關聯的派工單）。
*   **API 文件與規範**：
    *   建立統一的 API Response Model，確保所有錯誤訊息（Error Handling）格式一致。
    *   針對複雜查詢 API 增加 Swagger/OpenAPI 的範例回應 (Example Responses)。

### 3.2 前端架構 (Frontend - React/Vite)
*   **型別安全 (Type Safety)**：
    *   **目標**：將 `any` 型別使用率降至 5% 以下。
    *   **策略**：優先處理 `api/` 目錄下的型別定義，確保前後端介接的資料結構精確。
*   **程式碼清理 (Code Hygiene)**：
    *   移除所有 `console.log`，改用統一的 `Logger` 工具或移除。
    *   導入 `husky` 與 `lint-staged`，在 commit 前自動執行 ESLint 修復。

### 3.3 資料庫 (Database - PostgreSQL)
*   **關聯完整性**：
    *   針對所有多對多 (Many-to-Many) 關聯表，確保設定 `ON DELETE CASCADE`，避免主資料刪除後留下孤兒紀錄 (Orphan Records)。
*   **備份策略**：
    *   現有備份腳本需加入「異地備份」或「雲端同步」機制（如同步至 Google Drive 或另一台 NAS），以防硬體單點故障。

---

## 肆、 DevOps 與自動化部署 (DevOps & Automation)

### 4.1 GitOps 轉型計畫
目標是實現 **"Push to Master -> Auto Deploy"** 的流暢體驗。

1.  **Self-Hosted Runner 建置**：
    *   在 QNAP NAS 上運行 GitHub Actions Runner (Docker 容器)，解決內網穿透問題。
    *   此舉可繞過 SSH 連線限制，讓 Runner 直接在內網執行 Docker Compose 指令。

2.  **CI/CD Pipeline 優化**：
    *   **CI 階段**：加入 Backend Unit Tests (Pytest) 與 Frontend Build Check。
    *   **CD 階段**：
        1.  Build Docker Image (加上 Git Commit SHA Tag)。
        2.  Update Deployment Config。
        3.  Trigger Watchtower 或重啟服務。

### 4.2 監控與日誌 (Observability)
*   **集中式日誌**：建議導入輕量級日誌收集器 (如 Loki + Grafana 或單純的 Filebeat)，將 Backend 與 Nginx 日誌統一管理。
*   **健康檢查 (Health Check)**：
    *   強化 `/health` 端點，除了回傳 `status: ok`，應包含：
        *   資料庫連線狀態。
        *   Redis (若有) 連線狀態。
        *   目前版本號 (Git SHA)。

---

## 伍、 品質保證 (Quality Assurance)

### 5.1 測試策略 (Testing Strategy)
*   **單元測試 (Unit Test)**：保持後端核心邏輯 (Service Layer) 測試覆蓋率 > 80%。
*   **端對端測試 (E2E Test)**：
    *   導入 **Playwright**。
    *   優先撰寫「關鍵路徑」測試：登入 -> 建立公文 -> 建立派工單 -> 結案。
    *   設定 CI 排程，每日凌晨自動執行 E2E 測試。

---

## 陸、 未來藍圖 (Roadmap)

| 階段 | 時間點 | 重點目標 | 關鍵產出 |
| :--- | :--- | :--- | :--- |
| **短期 (Phase 1)** | 2週內 | **部署穩定化** | 解決 SSH 問題、完成資料遷移、Self-hosted Runner 上線 |
| **中期 (Phase 2)** | 1個月內 | **品質自動化** | E2E 測試整合 CI、前端型別優化、建立 Staging 環境 |
| **長期 (Phase 3)** | 3個月內 | **維運智慧化** | 監控告警系統 (Prometheus/Grafana)、效能調優 |

---

## 柒、 結語

本系統已具備扎實的功能基礎，目前的痛點主要集中在「最後一哩路」的部署與維運自動化。建議優先集中資源解決 **NAS SSH 連線** 與 **Self-hosted Runner** 的建置，這將是提升團隊開發效率與系統穩定性的最高槓桿行動。
