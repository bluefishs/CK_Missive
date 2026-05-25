---
title: Lessons Registry 索引
type: topic
created: 2026-05-25
sources: [docs/architecture/LESSONS_REGISTRY.md]
tags: [架構, lessons, 治理, auto-compiled]
confidence: high
---

# Lessons Registry 索引

**統計來源**: docs/architecture/LESSONS_REGISTRY.md
**編譯時間**: 2026-05-25 05:00
**Lessons 總數**: 40

| ID | Lesson Title |
|----|--------------|
| L01 | SSOT 聲明 vs 實作斷鏈（Dead Doc 反模式） |
| L02 | Yaml config 聲明卻 0 reader（Dead Config） |
| L03 | Mock.patch 路徑遷移（Wave 1 sub-batch B） |
| L04 | Multi-line patch sed 失效（Wave 4 tender） |
| L05 | Class name collision（Wave 1 sub-batch C notification） |
| L06 | 內部循環 import → relative import（Wave 1 sub-batch A document） |
| L07 | Private function (_ 開頭) re-export（Wave 2 ERP） |
| L08 | Production caller 路徑同步（Wave 3 integration） |
| L09 | Async mock 斷鏈（pre-existing test failures） |
| L10 | Dead UI（後端實作但前端缺 UI） |
| L11 | React Query staleTime + 0 invalidate = 60s 不刷新 |
| L12 | Stub 算散戶 → entropy 短期不會降 |
| L13 | sed 替換漏掃 cross-cutting test 檔（Wave 8） |
| L14 | GitHub Actions 自動觸發產生雲端費用 |
| L15 | Telegram 個人號當主推播通道（ADR-0027） |
| L16 | 一個 dataclass 塞 100+ 設定欄位 |
| L17 | DDD 遷移看職責邊界不看行數 |
| L18 | Wiki dispatch backfill 不需 fuzzy match |
| L19 | KG embedding 維護需週期性 backfill |
| L21 | Agent evolution scheduler 整合斷鏈（redis counter 卡 0） |
| L24 | Self-evaluator 標準過鬆 / Pattern 門檻過緊（雙重失衡） |
| L25 | 鏈路驗證 vs 鏈路盤點（grep 關鍵字陷阱） |
| L20 | Lessons 散落 commit/ADR/PLAYBOOK → 需 SSOT |
| L23 | 領域驅動拆分 vs 行數驅動拆分（拒拆判準） |
| L26 | Half-Wired Anti-Pattern Stacking（多層 bug 疊加遮蔽） |
| L27 | Dev Mode Override Trap（VITE_AUTH_DISABLED 強制覆蓋真實用戶） |
| L29 | Domain score 寫入鏈再次中斷（dict key bug + 涵蓋率不足） |
| L28 | JSON-as-TEXT Schema Drift（DB Text 存 JSON 但忘 parse） |
| L30 | Pipeline Integration as Priority（環節不連通就是浪費） |
| L31 | ROI = entities × usage_rate（建表不等於用表） |
| L32 | Frontend UI Component 不適合 packaging（LR-015 終局教訓 / 2026-05-18） |
| L33 | Transitive Deps 缺失必致 Half-Wired（LR-015/016 配套） |
| L34 | 業務 specific 不可進 shared package（lvrland LR-020 對應 / 2026-05-18） |
| L35 | 採納前必過 baseline TS check（lvrland LR-019 對應 / 2026-05-18） |
| L36 | Repo Structure Assumption（install.sh 寫死目標路徑 / 2026-05-18） |
| L22 | 範本資產缺跨 repo 引用治理規範 |
| L37 | 覆盤報告自身也是「真活宣告 vs 真接通」候選（2026-05-19） |
| L39 | QueryKey Drift（React Query invalidate silent dead）（2026-05-20） |
| L38 | 平時保險（cron / 異地備份）也是 LR-015 反模式高發區（2026-05-19） |
| L41 | JWT Secret Drift Silent Fail（4 重疊加 / 2026-05-21） |


## 完整內容

見 [LESSONS_REGISTRY.md](../../docs/architecture/LESSONS_REGISTRY.md)
