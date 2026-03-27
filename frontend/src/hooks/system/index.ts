/**
 * 系統功能 Hooks
 *
 * 包含行事曆、儀表板、管理員等系統層級功能
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

// 行事曆
export * from './useCalendar';
export * from './useCalendarIntegration';

// 儀表板
export * from './useDashboard';
export * from './useDashboardCalendar';

// 管理員
export * from './useAdminUsers';

// 文件統計
export * from './useDocumentStats';

// 通知中心
export * from './useNotifications';

// 部門選項
export * from './useDepartments';

// AI 管理
export * from './useAISynonyms';
export * from './useAIPrompts';
export * from './useDocumentAnalysis';

// AI SSE 串流
export * from './useStreamingChat';
export * from './useAgentSSE';
export * from './useLiveActivitySSE';
export * from './useDigitalTwinSSE';
