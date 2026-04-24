/**
 * LoginPage.tsx — v5.9.4 (2026-04-24) 資安改造
 *
 * ⚠️ 帳號密碼登入機制已全面關閉（ADR-0033）
 *
 * 本頁面過去為獨立帳密登入路徑（/login），v5.9.4 起因資安考量（避免暴力破解、
 * credential stuffing、憑證洩漏風險）統一由 /entry 處理 SSO 登入
 * （Google OAuth / LINE Login）。
 *
 * 此檔保留為 legacy redirect，避免既有書籤與外部連結失效。
 * 原本 367 行的帳密表單、MFA 驗證等邏輯已移除；MFA 流程改由 /mfa-verify 專屬頁。
 */
import React from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { ROUTES } from '../router/types';

const LoginPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const returnUrl = searchParams.get('returnUrl');
  const entryUrl = returnUrl
    ? `${ROUTES.ENTRY}?returnUrl=${encodeURIComponent(returnUrl)}`
    : ROUTES.ENTRY;
  return <Navigate to={entryUrl} replace />;
};

export default LoginPage;
