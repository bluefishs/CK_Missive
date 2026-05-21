/**
 * Example: React EntryPage / Landing 整合 ck-sso-js
 *
 * Consumer 場景：lvrland / pile / digitaltwin 等 *.cksurvey.tw 子網域 React app
 * 在「未登入時的入口頁」自動觸發 SSO bridge，成功則進 dashboard，失敗則 fall through
 * 到原本的 LINE/Google 登入 UI。
 *
 * 此檔僅範例，consumer 複製後自行調整 import path / route 名。
 */
import { useNavigate } from 'react-router-dom';
import { useSSOBridge } from 'ck-sso-js/react';
// 或：import { useSSOBridge } from '../lib/ck-sso-js/src/react/useSSOBridge';

// ↓ consumer 自己的 component
import LoginPanel from '../components/LoginPanel';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export default function EntryPage(): JSX.Element {
  const navigate = useNavigate();

  // 自動嘗試 SSO bridge — 成功則跳 dashboard，失敗則顯示登入 UI
  const { state, result, retry } = useSSOBridge({
    apiBaseURL: API_BASE_URL,
    endpoint: '/auth/sso-bridge',
    onSuccess: () => {
      window.dispatchEvent(new CustomEvent('user-logged-in'));
      navigate('/dashboard');
    },
  });

  if (state === 'loading') {
    return (
      <div style={{ padding: 60, textAlign: 'center' }}>
        <p>正在驗證您的乾坤 SSO 身份⋯</p>
      </div>
    );
  }

  // SSO 失敗或被略過 → 顯示原本登入面板
  return (
    <div>
      <LoginPanel />
      {result?.reason === 'locked' && (
        <button onClick={retry} style={{ marginTop: 12, fontSize: 13 }}>
          重試 SSO（清除 session 鎖）
        </button>
      )}
      {result?.reason === 'terminal' && result.status === 403 && (
        <p>您的員工權限不包含本系統，請聯繫管理員。</p>
      )}
      {result?.reason === 'terminal' && result.status === 404 && (
        <p>您的 SSO 帳號尚未在本系統建立，請先用原 Google/LINE 登入一次。</p>
      )}
    </div>
  );
}
