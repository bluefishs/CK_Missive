/**
 * SessionGate — 在 app 根部統一解析登入狀態，resolve 完才渲染路由。
 *
 * 這是 SSO 治本（2026-06-15）的關鍵：啟動時 status='resolving' 期間顯示 loading、
 * 不渲染任何路由 → 任何守衛（ProtectedRoute/useAuthGuard）都不會在 session 尚未
 * 確認時就 redirect → 從源頭消滅「瞬態未認證 → 跳 entry → 跳回」迴圈。
 */
import React, { useEffect } from 'react';
import { useSessionStore } from '../../store/sessionStore';
import { PageLoading } from './PageLoading';

export const SessionGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const status = useSessionStore((s) => s.status);
  const bootstrap = useSessionStore((s) => s.bootstrap);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  if (status === 'resolving') {
    return <PageLoading message="驗證登入狀態中..." />;
  }
  return <>{children}</>;
};

export default SessionGate;
