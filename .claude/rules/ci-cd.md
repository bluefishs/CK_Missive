# CI/CD 自動化

## GitHub Actions CI 整合

> **⚠️ 所有 GitHub Actions 自動觸發已停用 (2026-03-09) — 收費問題**
> 所有 workflow 僅保留 `workflow_dispatch` 手動觸發。

位於 `.github/workflows/ci.yml`，觸發條件：僅手動觸發 (workflow_dispatch)。

| Job | 說明 |
|-----|------|
| `frontend-check` | TypeScript + ESLint (max-warnings=0) + 單元測試 |
| `backend-check` | Python 語法 + 模組匯入驗證 + pytest + 整合測試 (soft-fail) + MyPy (soft-fail) |
| `config-consistency` | .env 配置一致性 (禁止 backend/.env) |
| `skills-sync-check` | Skills/Commands/Hooks 同步驗證 (42 項) |
| `security-scan` | npm/pip audit + Bandit + 硬編碼檢測 |
| `docker-build` | Docker 映像建置驗證 |
| `test-coverage` | 前後端測試覆蓋率 (後端 70%+ 閾值) |
| `migration-check` | Alembic 遷移一致性 (單一 HEAD) |
| `bundle-size-check` | 前端 Bundle 大小限制 (10.5MB raw / 3.5MB gzip / 1.5MB per file) |
| `ai-config-check` | AI 服務配置驗證 |

## CD 自動部署

位於 `.github/workflows/cd.yml`。

| 流程 | 觸發條件 |
|------|---------|
| ~~`develop` → Staging~~ | ~~Push to develop~~ (已停用) |
| ~~`main` → Production~~ | ~~Push to main~~ (已停用) |
| 手動觸發 | workflow_dispatch (唯一有效方式) |

**部署步驟**: prepare → test → build (Docker) → deploy → notify

詳細配置: `docs/DEPLOYMENT_GUIDE.md`

## 本地驗證

```powershell
# Skills 同步檢查 (42 項)
powershell -File scripts/checks/skills-sync-check.ps1

# 架構驗證 (7 項)
cd backend && python ../scripts/checks/verify_architecture.py
```
