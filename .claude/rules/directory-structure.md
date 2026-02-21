# Claude Code 配置目錄結構

```
.claude/
├── commands/                    # Slash Commands
│   ├── pre-dev-check.md        # ⚠️ 開發前強制檢查 (必用)
│   ├── route-sync-check.md     # 前後端路由一致性檢查
│   ├── api-check.md            # API 端點一致性檢查
│   ├── type-sync.md            # 型別同步檢查
│   ├── dev-check.md            # 開發環境檢查
│   ├── data-quality-check.md   # 資料品質檢查
│   ├── db-backup.md            # 資料庫備份管理
│   ├── csv-import-validate.md  # CSV 匯入驗證
│   ├── security-audit.md       # 資安審計檢查
│   ├── performance-check.md    # 效能診斷檢查
│   ├── verify.md               # 綜合驗證
│   ├── tdd.md                  # TDD 工作流
│   ├── checkpoint.md           # 長對話進度保存
│   ├── code-review.md          # 程式碼審查
│   ├── build-fix.md            # 構建修復
│   └── superpowers/            # Superpowers 指令
│       ├── brainstorm.md
│       ├── write-plan.md
│       └── execute-plan.md
├── skills/                      # 領域知識 Skills
│   ├── [16 個專案特定 skills]
│   └── _shared/                # 共享 Skills 庫
│       ├── shared/             # 通用 skills + superpowers
│       └── react/              # React 專用 skills
├── agents/                      # 專業代理
│   ├── code-review.md
│   ├── api-design.md
│   ├── bug-investigator.md
│   ├── build-error-resolver.md
│   └── e2e-runner.md
├── hooks/                       # 自動化鉤子
│   ├── session-start.ps1       # SessionStart: 專案上下文
│   ├── auto-approve.ps1        # PermissionRequest: 自動核准
│   ├── typescript-check.ps1    # PostToolUse: TypeScript 檢查
│   ├── python-lint.ps1         # PostToolUse: Python 檢查
│   ├── validate-file-location.ps1 # PreToolUse: 檔案位置驗證
│   ├── route-sync-check.ps1    # 手動: 路徑同步檢查
│   ├── api-serialization-check.ps1 # 手動: API 序列化
│   ├── link-id-check.ps1       # 手動: Link ID 檢查
│   └── performance-check.ps1   # 手動: 效能檢查
├── rules/                       # 自動載入規範 (與 CLAUDE.md 同級)
│   ├── security.md             # 安全規範
│   ├── testing.md              # 測試規範
│   ├── skills-inventory.md     # Skills/Commands/Agents 清單
│   ├── hooks-guide.md          # Hooks 配置指南
│   ├── ci-cd.md                # CI/CD 工作流
│   ├── auth-environment.md     # 認證與環境
│   ├── development-rules.md    # 開發強制規範
│   ├── architecture.md         # 專案結構
│   └── directory-structure.md  # 本文件
├── DEVELOPMENT_GUIDELINES.md   # 開發指引
├── MANDATORY_CHECKLIST.md      # 強制性開發檢查清單
├── CHANGELOG.md                # 版本更新記錄
├── settings.json               # 專案配置 (hooks, skills inherit)
└── settings.local.json         # 本地權限設定
```
