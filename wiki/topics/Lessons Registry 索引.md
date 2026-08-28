---
title: Lessons Registry 索引
type: topic
created: 2026-06-08
sources: [docs/architecture/LESSONS_REGISTRY.md]
tags: [架構, lessons, 治理, auto-compiled]
confidence: high
---

# Lessons Registry 索引

**統計來源**: docs/architecture/LESSONS_REGISTRY.md
**編譯時間**: 2026-08-24 05:00
**Lessons 總數**: 82

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
| L77 | 標案 enrichment 死結：openfun 需 org_id、org_id 只在被反爬限流的 PCC 詳情頁（勿重試爬蟲路徑 / 2026-06-17） |
| L76 | Windows Docker backend recreate/restart 易留殭屍埠轉發 socket → 公網 502（部署後必驗 host→8001  |
| L75 | 推薦相關性：機關關係 ≠ 工項相關；粗放機關信號 + 粗粒度（府級）比對＝噪音源（標案業務推薦 / 2026-06-16） |
| L74 | 單一狀態欄被多個 async 來源 last-writer-wins 競寫 + 破壞性副作用＝經典 race（SSO「第一次停 entry、重刷才好」/ 202 |
| L90 | 一次異常關機讓 12 個排程整批沒跑，而三層存活稽核沒有一層問「這一次它跑了沒有」（2026-08-12） |
| L93 | ORM mapper 初始化失敗＝整個系統無法登入，而 /health 仍是 200（2026-08-16） |
| L92 | 檢核在「要報問題的那一刻」崩掉，而平常看起來好好的（2026-08-15） |
| L91 | 在 Windows 上執行帶容器絕對路徑的程式碼不會失敗，它會靜靜讀寫 D:\app\（2026-08-12） |
| L89 | 跨 repo 共用腳本帶著自己的退出碼約定進到別人的 runner，會被靜靜降級成「未驗完」（2026-08-09） |
| L87 | 「多給一種憑證」不是保險，是多開一條會失敗的路；而剛上線的檢核最不該被信任（2026-08-09） |
| L88 | 檢核把自己的退出碼判成異常：自我循環讓 weekly 永遠不可能綠（2026-08-09） |
| L86 | 連續猜錯五次之後：讓工具「說出它看到什麼」，比再猜第六次有效（2026-08-08） |
| L85 | 破壞性指令的作用範圍必須先確認；而且答案往往早就寫在文件裡（2026-08-08） |
| L84 | 「設定寫得很嚴謹」與「它跑得起來」是兩件事：從未啟動成功過的服務，會逼出一條更差的替代路徑（2026-08-08） |
| L83 | 「我送出了什麼」與「對方收到了什麼」是兩件事：中間層會靜靜改寫，而單元測試斷言的是前者（2026-08-07） |
| L81 | 換了出口就要換整條鏈：把通知從 A 管道改到 B 管道時，閘門、測試安全網、測試斷言都會留在 A（2026-08-04） |
| L82 | 「還沒到門檻」與「永遠到不了門檻」長得一模一樣：資料深度被保留期釘住，而腳本每次都禮貌地說資料不足（2026-08-04） |
| L80 | SSO 反覆回歸的底層＝「後端 token 生命週期層」：SSO 沒有可用的透明 refresh 路徑（前端不變式救不了 / 2026-07-21） |
| L79 | Session 收尾不完整＝功能「存在於硬碟但不存在於系統」：寫好＋測試綠 ≠ commit ≠ 部署（2026-07-08） |
| L78 | 「今日 OK、明日又壞」＝復原路徑有多入口且散落破壞性副作用，happy-path 驗證必漏（SSO 反覆回歸元覆盤 / 2026-07-03） |
| L73 | In-container writer 盲視 host/cross-repo 資源 → silent 寫錯值（治理工具自身亦中招 / 2026-06-12） |
| L72 | 排程「註冊 ≠ 真在跑」：scheduler liveness 對賬揪 silent dormant cron（擴大治理至坤哥/Hermes/排程 / 2026 |
| L71 | 程式圖譜是「結構地圖」抓不到 config/語意/runtime 三類問題 → 用 AST 橋接治理（2026-06-11） |
| L70 | GOOGLE_CALENDAR_ID config-drift：1044 事件靜默推進「服務帳號私人日曆」無人可見（L51 同族 / 2026-06-11） |
| L69 | secureApiService single-flight 讓並發共用「單次」CSRF token → nav 選單 403（修 L49 反效果 / 2026 |
| L68 | CSRF refresh 死結：csrf cookie 過期→refresh 被 CSRF 擋→全站 403「權限不足」（OWASP / 2026-06-10） |
| L66 | 跨子域 SSO 消費端 self-heal gate 漏掉 cookie-session（顯示「訪客」race / 2026-06-10） |
| L67 | 前端 baseURL 已含 /api 卻硬編 /api 前綴 → double-prefix 404（半接通 / 2026-06-10） |
| L64 | LINE 推播鏈交易污染復發（吞錯不 rollback + 缺方法 + 重複掃描 / 2026-06-03） |
| L63 | 學習閉環需 aging alert 才能突破 owner 健忘（2026-05-31） |
| L62 | 整合連通 = 持續驗證機制，不是一次性 endpoint（2026-05-31） |
| L61 | 下游反治理（PileMgmt R18 案例 / L60 真活驗證範本）（2026-05-31） |
| L60 | 平衡 = 結構正常化（非中間值）（2026-05-30，meta-治理第 8 句立法） |
| L59 | 治理架構倒置（上游 meta 缺 audit / 業務 source 反向 audit 子專案）（2026-05-30） |
| L58 | 治理範本污染風險（強推 132 檔 57% 為本專案特定）（2026-05-30） |
| L57 | BACKEND_DIR/logs vs compose mount 子路徑漂移（L52 family 第七案）（2026-05-30） |
| L54 | 跨 repo 套用 ≠ 落實（install-template apply vs commit gap）（2026-05-30） |
| L53 | Facade over-engineering 30 天實證裁判（ADR-0036 ROI 失敗）（2026-05-30） |
| L52 | paths.py PROJECT_ROOT vs compose mount target 漂移（L4x family 第六案）（2026-05-30） |
| L51 | Container image freshness family（L51.5/L51.7 系列，2026-05-30） |
| L50 | Multi-source identifier ≠ entity link（2026-05-28） |
| L49 | Container Host Dependency Family (PM2 → Docker 遷移 5 重 silent regression / 2026-0 |


## 完整內容

見 [LESSONS_REGISTRY.md](../../docs/architecture/LESSONS_REGISTRY.md)
