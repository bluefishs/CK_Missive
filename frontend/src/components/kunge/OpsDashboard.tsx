/**
 * OpsDashboard — 坤哥運維儀表板（ADR-0031）
 *
 * ⚠️ 2026-08-02 更正：原註解寫「pages/UnifiedAgentPage.tsx 保留為 re-export stub」，
 * 但**方向是相反的** —— 實作在 `pages/UnifiedAgentPage.tsx`，本檔才是 re-export。
 * 保持現狀不搬動（搬檔會動到 /agent/dashboard 與 /admin/ai-assistant 兩條既有路由），
 * 只把敘述改成與實作一致。
 *
 * 內容分組（2026-08-02，owner：資訊過多、營運核心雜亂）：
 *   營運    — 晨報與推播、派工進度
 *   系統    — 儀表板（admin 另有 服務狀態／資料管線／數據分析）
 *   AI 診斷 — 自省、追蹤、健康進化、拓撲（admin 另有 Agent 效能／DualMode）
 *
 * @version 2.1.0
 */

import UnifiedAgentPage from '../../pages/UnifiedAgentPage';

export default UnifiedAgentPage;
