# CK Missive 文件中心

> 版本: 3.0.0 (分類索引改版)
> 最後更新: 2026-04-15
> 乾坤測繪公文管理系統 (CK_Missive) 技術文件索引

> 採分類索引策略：根目錄 50+ 檔不搬移（避免破壞外部引用），改以主題分類導覽。新文件建立時請歸屬對應主題並在本索引登記。

---

## 🔐 安全 (Security)

| 文件 | 說明 |
|------|------|
| [AUTH_FLOW_DIAGRAM.md](./AUTH_FLOW_DIAGRAM.md) | 登入流程 + middleware 順序 + 錯誤碼速查 |
| [SECURITY_THREAT_MODEL.md](./SECURITY_THREAT_MODEL.md) | STRIDE 威脅分析 + Top 5 優先項 |
| [INCIDENT_RESPONSE_PLAYBOOK.md](./INCIDENT_RESPONSE_PLAYBOOK.md) | 六大資安場景應變 SOP |
| [SECRET_ROTATION_SOP.md](./SECRET_ROTATION_SOP.md) | 密碼 / Token 輪換流程 |
| [PRODUCTION_SECURITY_CHECKLIST.md](./PRODUCTION_SECURITY_CHECKLIST.md) | 上線前安全檢查 |
| [SECURITY_AUDIT_REPORT.md](./SECURITY_AUDIT_REPORT.md) | 資安審計報告 |
| [SECURITY_CICD_RECOMMENDATIONS.md](./SECURITY_CICD_RECOMMENDATIONS.md) | CI/CD 安全建議 |
| [KG_FEDERATION_TOKEN_ROTATION_SOP.md](./KG_FEDERATION_TOKEN_ROTATION_SOP.md) | KG 聯邦 Token 輪換 SOP |
| [incidents/](./incidents/) | 事件紀錄目錄 |

## 🚀 部署 / 維運 (Deployment / Ops)

| 文件 | 說明 |
|------|------|
| [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | 部署主指南 |
| [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) | 部署前檢查 |
| [DEPLOYMENT_GAP_ANALYSIS.md](./DEPLOYMENT_GAP_ANALYSIS.md) | 部署落差分析 |
| [DEPLOYMENT_LESSONS_LEARNED.md](./DEPLOYMENT_LESSONS_LEARNED.md) | 部署教訓 |
| [PRODUCTION_DEPLOYMENT_GUIDE.md](./PRODUCTION_DEPLOYMENT_GUIDE.md) | 正式環境部署 |
| [MANUAL_DEPLOYMENT_GUIDE.md](./MANUAL_DEPLOYMENT_GUIDE.md) | 手動部署 |
| [NAS_DEPLOYMENT_GUIDE.md](./NAS_DEPLOYMENT_GUIDE.md) | NAS 部署 |
| [CLOUDFLARE_TUNNEL_SETUP.md](./CLOUDFLARE_TUNNEL_SETUP.md) | Cloudflare Tunnel 建置 |
| [CLOUDFLARE_TUNNEL_CKSURVEY.md](./CLOUDFLARE_TUNNEL_CKSURVEY.md) | cksurvey.tw 專用部署 |
| [CLOUDFLARE_ACCESS_BYPASS.md](./CLOUDFLARE_ACCESS_BYPASS.md) | Access Bypass Policy |
| [SIMPLE_RESTART_GUIDE.md](./SIMPLE_RESTART_GUIDE.md) | 快速重啟 |
| [SYSTEM_MAINTENANCE.md](./SYSTEM_MAINTENANCE.md) | 系統維護 |
| [SYSTEM_CONFIG_CHECKLIST.md](./SYSTEM_CONFIG_CHECKLIST.md) | 系統配置檢查 |
| [GITHUB_RUNNER_SETUP.md](./GITHUB_RUNNER_SETUP.md) | GitHub Runner 建置 |
| [GITOPS_EVALUATION.md](./GITOPS_EVALUATION.md) | GitOps 評估 |

## 🏗️ 架構 / 設計 (Architecture)

| 文件 | 說明 |
|------|------|
| [ARCHITECTURE_REVIEW_2026-04-15.md](./ARCHITECTURE_REVIEW_2026-04-15.md) | 最新架構健康度 (8.0/10) |
| [Architecture_Optimization_Recommendations.md](./Architecture_Optimization_Recommendations.md) | 架構優化建議 |
| [PROJECT_STRUCTURE_STANDARD.md](./PROJECT_STRUCTURE_STANDARD.md) | 專案結構標準 |
| [SERVICE_ARCHITECTURE_STANDARDS.md](./SERVICE_ARCHITECTURE_STANDARDS.md) | 服務架構標準 |
| [STRUCTURE.md](./STRUCTURE.md) | 結構總覽 |
| [DOCUMENT_AI_ARCHITECTURE.md](./DOCUMENT_AI_ARCHITECTURE.md) | 文件 AI 架構 |
| [DOCUMENT_CENTER_DESIGN.md](./DOCUMENT_CENTER_DESIGN.md) | 文管中心設計 |
| [CALENDAR_ARCHITECTURE.md](./CALENDAR_ARCHITECTURE.md) | 行事曆架構 |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | 資料庫結構 |
| [er-diagram.md](./er-diagram.md) | ER 圖 |
| [adr/](./adr/) | **架構決策紀錄目錄 (ADR 0001~0016)** |
| [architecture/](./architecture/) | 深度架構文件目錄 |

## 📘 開發規範 (Development)

| 文件 | 說明 |
|------|------|
| [DEVELOPMENT_STANDARDS.md](./DEVELOPMENT_STANDARDS.md) | 🔴 統一開發規範總綱 |
| [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) | 開發指南 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 貢獻指南 |
| [CSV_IMPORT_MAINTENANCE.md](./CSV_IMPORT_MAINTENANCE.md) | CSV 匯入維護 |
| [ERROR_HANDLING_GUIDE.md](./ERROR_HANDLING_GUIDE.md) | 錯誤處理指南 |
| [FRONTEND_API_MAPPING.md](./FRONTEND_API_MAPPING.md) | 前後端 API 對應 |
| [ALEMBIC_MIGRATION_GUIDE.md](./ALEMBIC_MIGRATION_GUIDE.md) | Alembic 遷移指南 |
| [ENV_MANAGEMENT_GUIDE.md](./ENV_MANAGEMENT_GUIDE.md) | 環境設定管理 |
| [UNIFIED_CONFIG_GUIDE.md](./UNIFIED_CONFIG_GUIDE.md) | 統一配置指南 |
| [specifications/](./specifications/) | **規範文件目錄 (型別/API/Schema 強制規範)** |

## 🤖 AI / Agent / 整合 (AI & Integration)

| 文件 | 說明 |
|------|------|
| [HERMES_MIGRATION_PLAN.md](./HERMES_MIGRATION_PLAN.md) | Hermes 4-Phase 遷移計畫 |
| [hermes-skills/](./hermes-skills/) | Hermes skill 部署包 |
| [LINE_OPENCLAW_OPERATIONAL_GUIDE.md](./LINE_OPENCLAW_OPERATIONAL_GUIDE.md) | LINE + OpenClaw 運維（將下線） |
| [LINE_BOT_SETUP_GUIDE.md](./LINE_BOT_SETUP_GUIDE.md) | LINE Bot 直連 |
| [MULTICHANNEL_SETUP_GUIDE.md](./MULTICHANNEL_SETUP_GUIDE.md) | 多頻道整合 |
| [OLLAMA_SETUP_GUIDE.md](./OLLAMA_SETUP_GUIDE.md) | Ollama 建置 |
| [Google_Calendar_Integration_Setup.md](./Google_Calendar_Integration_Setup.md) | Google Calendar 整合 |
| [openclaw-skill-update.md](./openclaw-skill-update.md) | OpenClaw skill 更新 |

## 📊 報告 / 優化 (Reports & Optimization)

| 文件 | 說明 |
|------|------|
| [SYSTEM_OPTIMIZATION_REPORT.md](./SYSTEM_OPTIMIZATION_REPORT.md) | 系統優化報告 |
| [OPTIMIZATION_ACTION_PLAN.md](./OPTIMIZATION_ACTION_PLAN.md) | 優化行動計畫 |
| [reports/](./reports/) | 歷史報告目錄 |
| [plans/](./plans/) | 規劃目錄 |
| [presentations/](./presentations/) | 簡報目錄 |
| [archive/](./archive/) | 已封存文件 |

## 🗺️ 知識系統 (Knowledge)

| 文件 | 說明 |
|------|------|
| [wiki/](./wiki/) | LLM Wiki (220 pages, Karpathy 4-Phase) |
| [knowledge-map/](./knowledge-map/) | 知識地圖生成輸出 |
| [diagrams/](./diagrams/) | Mermaid 架構圖 |
| [generated/](./generated/) | 自動生成文件 |
| [er-model.json](./er-model.json) | ER Model 結構化輸出 |

---

## 新增文件規範

1. 新文件**歸屬到既有主題**，放在 `docs/` 根或對應子目錄
2. 在本 `README.md` 對應表格新增一列
3. 命名採大寫底線 `SCREAMING_SNAKE_CASE.md`（既有慣例）
4. 引用路徑使用相對路徑，避免 hardcoded 絕對路徑
5. 一次性產出（事件 postmortem / migration 筆記）放 `archive/` 或 `incidents/`

## 相關索引

- [CLAUDE.md](../CLAUDE.md) — 專案主配置
- [.claude/rules/](../.claude/rules/) — 自動載入規範 (architecture / security / testing 等)
- [.claude/CHANGELOG.md](../.claude/CHANGELOG.md) — 完整版本紀錄
