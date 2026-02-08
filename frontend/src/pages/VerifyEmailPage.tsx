/**
 * Email 驗證頁面
 *
 * 從 URL query param 取得 token，自動呼叫 /auth/verify-email 驗證。
 * - 成功：顯示成功訊息，3 秒後導向首頁
 * - 失敗：顯示錯誤訊息（已過期/無效）
 *
 * @version 1.0.0
 * @date 2026-02-08
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Result, Button, Spin, Card } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { verifyEmail } from '../api/authApi';
import { ROUTES } from '../router/types';

type VerifyState = 'loading' | 'success' | 'already_verified' | 'error';

const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [state, setState] = useState<VerifyState>('loading');
  const [errorMessage, setErrorMessage] = useState('');

  const token = searchParams.get('token');

  const doVerify = useCallback(async (verifyToken: string) => {
    try {
      const result = await verifyEmail(verifyToken);

      if (result.already_verified) {
        setState('already_verified');
      } else {
        setState('success');
      }

      // 3 秒後導向首頁
      setTimeout(() => {
        navigate(ROUTES.DASHBOARD, { replace: true });
      }, 3000);
    } catch (err: unknown) {
      setState('error');
      // 從 ApiException 取得錯誤訊息
      const errorObj = err as { message?: string };
      setErrorMessage(
        errorObj?.message || '驗證失敗，請重新發送驗證信'
      );
    }
  }, [navigate]);

  useEffect(() => {
    if (!token) {
      setState('error');
      setErrorMessage('缺少驗證 token，請從驗證信中的連結存取此頁面');
      return;
    }

    doVerify(token);
  }, [token, doVerify]);

  const renderContent = () => {
    switch (state) {
      case 'loading':
        return (
          <Result
            icon={<Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />}
            title="正在驗證您的 Email..."
            subTitle="請稍候"
          />
        );

      case 'success':
        return (
          <Result
            status="success"
            icon={<CheckCircleOutlined />}
            title="Email 驗證成功"
            subTitle="您的電子郵件已成功驗證。3 秒後將自動跳轉至首頁..."
            extra={[
              <Button
                type="primary"
                key="home"
                onClick={() => navigate(ROUTES.DASHBOARD, { replace: true })}
              >
                前往首頁
              </Button>,
            ]}
          />
        );

      case 'already_verified':
        return (
          <Result
            status="info"
            icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            title="Email 已經驗證"
            subTitle="您的電子郵件已經驗證完成，無需重複驗證。3 秒後將自動跳轉至首頁..."
            extra={[
              <Button
                type="primary"
                key="home"
                onClick={() => navigate(ROUTES.DASHBOARD, { replace: true })}
              >
                前往首頁
              </Button>,
            ]}
          />
        );

      case 'error':
        return (
          <Result
            status="error"
            icon={<CloseCircleOutlined />}
            title="Email 驗證失敗"
            subTitle={errorMessage}
            extra={[
              <Button
                type="primary"
                key="login"
                onClick={() => navigate(ROUTES.LOGIN, { replace: true })}
              >
                前往登入頁
              </Button>,
            ]}
          />
        );
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#f0f2f5',
      }}
    >
      <Card
        style={{
          maxWidth: 600,
          width: '100%',
          margin: '0 16px',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        }}
      >
        {renderContent()}
      </Card>
    </div>
  );
};

export default VerifyEmailPage;
