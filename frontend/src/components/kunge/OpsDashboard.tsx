/**
 * OpsDashboard — 坤哥運維儀表板子元件（ADR-0031）
 *
 * 原為 pages/UnifiedAgentPage.tsx，v5.8.1 降格為 kunge/OpsTab 的子元件。
 * 本檔是新的 primary location；原 pages/UnifiedAgentPage.tsx 保留為 re-export stub（v6.1.0 移除）。
 *
 * 雙模式：
 * - mode="user"  → 7 子 tab：對話 / 自省 / 追蹤 / 派工 / 儀表板 / 進化 / 拓撲
 * - mode="admin" → 12 子 tab（+ 效能 / 數據 / 管線 / 服務狀態 / DualMode）
 *
 * @version 2.0.0 — ADR-0031 rename from UnifiedAgentPage
 */

import UnifiedAgentPage from '../../pages/UnifiedAgentPage';

export default UnifiedAgentPage;
