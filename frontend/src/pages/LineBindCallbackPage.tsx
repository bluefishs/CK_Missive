/**
 * LINE 帳號綁定 OAuth Callback 頁面
 *
 * 已登入使用者綁定 LINE 帳號後重導向至此頁面，
 * 自動擷取 code 並完成綁定流程。
 *
 * @version 1.1.0
 * @date 2026-03-22
 */
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, Spin, Result, Typography, App } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { ROUTES } from '../router/types';
import authService from '../services/authService';
import { LINE_BIND_REDIRECT_URI } from '../config/env';
import { logger } from '../utils/logger';

const { Text } = Typography;

const LineBindCallbackPage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const errorParam = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    if (errorParam) {
      logger.error('[LINE Bind] OAuth error:', errorParam, errorDescription);
      sessionStorage.removeItem('line_bind_state');
      setError(errorDescription || 'LINE 授權失敗');
      return;
    }

    if (!code) {
      sessionStorage.removeItem('line_bind_state');
      setError('LINE 授權回應缺少 authorization code');
      return;
    }

    // CSRF state 嚴格驗證
    const savedState = sessionStorage.getItem('line_bind_state');
    if (!savedState || state !== savedState) {
      logger.error('[LINE Bind] State mismatch');
      sessionStorage.removeItem('line_bind_state');
      setError('安全驗證失敗，請重新操作');
      return;
    }
    sessionStorage.removeItem('line_bind_state');

    const doBind = async () => {
      try {
        const result = await authService.bindLine(code, LINE_BIND_REDIRECT_URI);
        message.success(result.message);
        navigate(ROUTES.PROFILE);
      } catch (err) {
        logger.error('[LINE Bind] Failed:', err);
        const errorMsg = (err as { detail?: string })?.detail
          || (err instanceof Error ? err.message : 'LINE 綁定失敗');
        setError(errorMsg);
      }
    };

    doBind();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '20px',
      }}>
        <Card style={{ maxWidth: 420, width: '100%' }}>
          <Result
            status="error"
            title="LINE 綁定失敗"
            subTitle={error}
            extra={
              <a href={ROUTES.PROFILE}>
                <Text style={{ color: '#c9a962' }}>返回個人設定</Text>
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
    }}>
      <Card style={{ textAlign: 'center', padding: '40px' }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 36 }} spin />} />
        <div style={{ marginTop: 16 }}>
          <Text style={{ fontSize: 16 }}>LINE 帳號綁定中...</Text>
        </div>
      </Card>
    </div>
  );
};

export default LineBindCallbackPage;
