# CI/CD 自動化

## GitHub Actions CI 整合

位於 `.github/workflows/ci.yml`，觸發條件：PR to main/develop、每夜排程、手動觸發。

| Job | 說明 |
|-----|------|
| `frontend-check` | TypeScript + ESLint + 單元測試 |
| `backend-check` | Python 語法 + 模組匯入驗證 + pytest |
| `config-consistency` | .env 配置一致性 (禁止 backend/.env) |
| `skills-sync-check` | Skills/Commands/Hooks 同步驗證 (42 項) |
| `security-scan` | npm/pip audit + Bandit + 硬編碼檢測 |
| `docker-build` | Docker 映像建置驗證 |
| `test-coverage` | 前後端測試覆蓋率 + Codecov |
| `migration-check` | Alembic 遷移一致性 (單一 HEAD) |
| `ai-config-check` | AI 服務配置驗證 |

## CD 自動部署

位於 `.github/workflows/cd.yml`。

| 流程 | 觸發條件 |
|------|---------|
| `develop` → Staging | Push to develop |
| `main` → Production | Push to main |
| 手動觸發 | workflow_dispatch |

**部署步驟**: prepare → test → build (Docker) → deploy → notify

詳細配置: `docs/DEPLOYMENT_GUIDE.md`

## 本地驗證

```powershell
# Skills 同步檢查 (42 項)
powershell -File scripts/skills-sync-check.ps1

# 架構驗證 (7 項)
cd backend && python ../scripts/verify_architecture.py
```
