/**
 * LINE Login OAuth Callback 頁面
 *
 * LINE 授權後重導向至此頁面，自動擷取 code 並完成登入流程。
 *
 * @version 1.1.0
 * @date 2026-03-22
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, Spin, Result, Typography, App } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { ROUTES } from '../router/types';
import authService, { MFARequiredError } from '../services/authService';
import { LINE_LOGIN_REDIRECT_URI } from '../config/env';
import { logger } from '../utils/logger';
// 2026-07-29：改用共用 SSOT（原本此檔有一份區域性複製）
import { isValidReturnUrl } from '../utils/returnUrl';

const { Text } = Typography;

/** 清理 LINE Login 相關的 sessionStorage */
const cleanupSessionStorage = () => {
  sessionStorage.removeItem('line_login_state');
  sessionStorage.removeItem('line_login_return_url');
};



/**
 * 回報前端層登入失敗（2026-07-31）
 *
 * 為何需要：前端的 state 驗證在打後端之前就擋下，**伺服端零紀錄** ——
 * owner 回報「一選 LINE 登入就錯誤」時，後端近 3 小時查無任何請求，
 * 只能靠口述推測。事後查出是從 LINE App 內開啟（in-app 瀏覽器與桌機
 * 不同 context，sessionStorage 的 state 帶不過去）。
 * 有這筆回報，下次同類問題就有紀錄可查，不必再麻煩使用者描述。
 *
 * fail-open：回報失敗不得影響錯誤畫面呈現。
 */
async function reportLoginFailure(reason: string, hasSavedState: boolean) {
  try {
    const ua = navigator.userAgent || '';
    await fetch('/api/auth/line/login-failure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reason,
        has_saved_state: hasSavedState,
        // LINE App 內建瀏覽器的 UA 會含 Line/；用它區分情境
        in_app: /\bLine\//i.test(ua),
        ua: ua.slice(0, 120),
      }),
    });
  } catch { /* fail-open：診斷回報不得影響使用者看到的錯誤 */ }
}

const LineCallbackPage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string>('');
  const processedRef = useRef(false);

  useEffect(() => {
    // StrictMode 防護：防止雙重 mount 導致第二次執行時 sessionStorage 已被清除
    if (processedRef.current) return;
    processedRef.current = true;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const errorParam = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    // LINE 授權錯誤
    if (errorParam) {
      logger.error('[LINE] OAuth error:', errorParam, errorDescription);
      void reportLoginFailure('oauth_error', false);
      cleanupSessionStorage();
      setError(errorDescription || 'LINE 授權失敗');
      return;
    }

    // 缺少 code
    if (!code) {
      cleanupSessionStorage();
      setError('LINE 授權回應缺少 authorization code');
      return;
    }

    // CSRF state 嚴格驗證
    const savedState = sessionStorage.getItem('line_login_state');
    if (!savedState || state !== savedState) {
      logger.error('[LINE] State mismatch:', { saved: savedState, received: state });
      void reportLoginFailure('state_mismatch', Boolean(savedState));
      cleanupSessionStorage();
      setError(
        /\bLine\//i.test(navigator.userAgent)
          ? '安全驗證失敗：請改用手機或電腦的瀏覽器開啟系統後再登入（LINE 內建瀏覽器無法帶入驗證資訊）'
          : '安全驗證失敗 (state mismatch)，請重新登入',
      );
      return;
    }

    // 取得 returnUrl 並清理 sessionStorage
    const returnUrl = sessionStorage.getItem('line_login_return_url');
    cleanupSessionStorage();

    // 執行登入
    const doLogin = async () => {
      try {
        const result = await authService.lineLogin(code, LINE_LOGIN_REDIRECT_URI);
        message.success('LINE 登入成功！');
        window.dispatchEvent(new CustomEvent('user-logged-in'));

        const targetUrl = (returnUrl && isValidReturnUrl(returnUrl))
          ? decodeURIComponent(returnUrl)
          : (result.user_info.is_admin ? ROUTES.ADMIN_DASHBOARD : ROUTES.DASHBOARD);
        navigate(targetUrl);
      } catch (err: unknown) {
        if (err instanceof MFARequiredError) {
          message.info('請完成雙因素認證');
          navigate(ROUTES.MFA_VERIFY, {
            state: { mfa_token: err.mfa_token, returnUrl: returnUrl || undefined },
          });
          return;
        }
        logger.error('[LINE] Login failed:', err);
        // 從 AxiosError response 或 Error message 提取錯誤訊息
        const axiosErr = err as { response?: { data?: { detail?: string; error?: { message?: string } } } };
        const errorMsg = axiosErr.response?.data?.detail
          || axiosErr.response?.data?.error?.message
          || (err instanceof Error ? err.message : 'LINE 登入失敗，請稍後再試');
        setError(errorMsg);
      }
    };

    doLogin();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
        padding: '20px',
      }}>
        <Card style={{ maxWidth: 420, width: '100%' }}>
          <Result
            status="error"
            title="LINE 登入失敗"
            subTitle={error}
            extra={
              <a href={ROUTES.LOGIN}>
                <Text style={{ color: '#c9a962' }}>返回登入頁面</Text>
              </a>
            }
          />
        </Card>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    }}>
      <Card style={{ textAlign: 'center', padding: '40px' }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />} />
        <div style={{ marginTop: 16 }}>
          <Text style={{ fontSize: 16 }}>LINE 登入處理中...</Text>
        </div>
      </Card>
    </div>
  );
};

export default LineCallbackPage;
