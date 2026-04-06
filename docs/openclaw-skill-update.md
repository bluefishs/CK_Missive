# CK Missive Bridge Skill — Updated for v5.5.0

> Reference document for updating the OpenClaw container SKILL.md.
> NOT deployed automatically — requires manual copy to Docker container.
> Target: container `/home/node/.openclaw/workspace/skills/ck-missive-bridge/SKILL.md`

## New Capabilities (2026-04-05)

### Vision (Gemma 4 多模態)
- 發票圖片辨識: POST /api/agent/query/sync with image attachment
- 資產照片評估: POST /api/erp/assets/upload-photo
- 附件文件分析: Vision OCR for scanned documents

### 底價分析
- POST /api/tender/analytics/price-analysis — 單一標案底價分析
- POST /api/tender/analytics/price-trends — 同類標案價格趨勢

### NL 知識圖譜搜尋
- POST /api/ai/graph/smart-search — 自然語言搜尋知識圖譜

### Agent 自省
- POST /api/ai/digital-twin/introspection — 統一自省儀表板
- POST /api/ai/digital-twin/introspection/profile — 自我檔案

### Code Wiki
- POST /api/knowledge-base/code-wiki/module — 模組 Wiki 自動生成
- POST /api/knowledge-base/code-wiki/overview — 程式碼總覽

### Domain Events
- project.promoted — 成案觸發
- billing.paid — 收款入帳
- document.received — 自動 NER
- expense.approved — 費用核銷通知
- tender.awarded — 標案決標

### Sync Endpoint Enhanced
- Channel tracking (line/telegram/openclaw)
- Capabilities discovery in response
- Session handoff (30min idle → resume context)
