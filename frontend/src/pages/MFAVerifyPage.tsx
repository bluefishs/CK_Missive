/**
 * MFA 驗證頁面
 *
 * 登入流程第二步：使用者輸入 TOTP 驗證碼或備用碼。
 * 接收 location.state 中的 mfa_token，驗證成功後完成登入。
 *
 * @version 1.0.0
 * @date 2026-02-08
 */
import React, { useState, useRef, useEffect } from 'react';
import type { InputRef } from 'antd';
import {
  Card,
  Input,
  Button,
  Typography,
  Alert,
  Space,
  App,
} from 'antd';
import {
  SafetyOutlined,
  KeyOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import authService from '../services/authService';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { useResponsive } from '../hooks';

const { Title, Text, Paragraph } = Typography;

interface MFALocationState {
  mfa_token: string;
  returnUrl?: string;
}

const MFAVerifyPage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const { isMobile, responsiveValue } = useResponsive();
  const cardPadding = responsiveValue({ mobile: '24px 16px', tablet: '32px 24px', desktop: '40px 32px' });

  const state = location.state as MFALocationState | null;
  const mfaToken = state?.mfa_token;
  const returnUrl = state?.returnUrl;

  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [useBackupCode, setUseBackupCode] = useState(false);

  const inputRef = useRef<InputRef>(null);

  // 若無 mfa_token，重導向到登入頁
  useEffect(() => {
    if (!mfaToken) {
      navigate('/login', { replace: true });
    }
  }, [mfaToken, navigate]);

  // 自動聚焦輸入框
  useEffect(() => {
    inputRef.current?.focus();
  }, [useBackupCode]);

  const handleSubmit = async () => {
    if (!code.trim()) {
      setError(useBackupCode ? '請輸入備用碼' : '請輸入 6 位數驗證碼');
      return;
    }

    if (!useBackupCode && (code.length !== 6 || !/^\d{6}$/.test(code))) {
      setError('請輸入 6 位數字驗證碼');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await apiClient.post<{
        access_token: string;
        token_type: string;
        expires_in: number;
        refresh_token?: string;
        user_info: Record<string, unknown>;
      }>(API_ENDPOINTS.AUTH.MFA_VALIDATE, {
        mfa_token: mfaToken,
        code: code.trim(),
      });

      // MFA 驗證成功，儲存認證資料
      if (response.user_info) {
        authService.setUserInfo(response.user_info as ReturnType<typeof authService.getUserInfo> & Record<string, unknown>);
      }

      message.success('驗證成功，歡迎登入!');
      window.dispatchEvent(new CustomEvent('user-logged-in'));

      const targetUrl = returnUrl
        ? decodeURIComponent(returnUrl)
        : '/dashboard';
      navigate(targetUrl, { replace: true });
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '驗證失敗，請重試';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 按 Enter 提交
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  if (!mfaToken) {
    return null;
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      padding: isMobile ? '12px' : '20px',
    }}>
      <Card
        style={{
          width: '100%',
          maxWidth: isMobile ? '100%' : 420,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          borderRadius: isMobile ? '12px' : '16px',
          border: '1px solid rgba(201, 169, 98, 0.2)',
        }}
        styles={{ body: { padding: cardPadding } }}
      >
        {/* 標題區 */}
        <div style={{ textAlign: 'center', marginBottom: isMobile ? '16px' : '24px' }}>
          <SafetyOutlined style={{ fontSize: 48, color: '#c9a962', marginBottom: 12 }} />
          <Title level={isMobile ? 4 : 3} style={{ color: '#c9a962', marginBottom: '4px' }}>
            雙因素認證
          </Title>
          <Text style={{ color: '#8c8c8c', fontSize: isMobile ? 13 : 14 }}>
            {useBackupCode
              ? '請輸入備用碼'
              : '請輸入驗證器 App 顯示的 6 位數驗證碼'}
          </Text>
        </div>

        {/* 錯誤訊息 */}
        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: '20px' }}
            closable
            onClose={() => setError('')}
          />
        )}

        {/* 驗證碼輸入 */}
        <div style={{ marginBottom: 24 }}>
          {useBackupCode ? (
            <Input
              ref={inputRef}
              prefix={<KeyOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="輸入備用碼"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              onKeyDown={handleKeyDown}
              size={isMobile ? 'middle' : 'large'}
              maxLength={20}
              autoComplete="one-time-code"
              style={{ textAlign: 'center', letterSpacing: '2px', fontSize: 16 }}
            />
          ) : (
            <Input
              ref={inputRef}
              prefix={<SafetyOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="000000"
              value={code}
              onChange={(e) => {
                const val = e.target.value.replace(/\D/g, '');
                if (val.length <= 6) setCode(val);
              }}
              onKeyDown={handleKeyDown}
              size={isMobile ? 'middle' : 'large'}
              maxLength={6}
              autoComplete="one-time-code"
              inputMode="numeric"
              style={{ textAlign: 'center', letterSpacing: '8px', fontSize: 24, fontFamily: 'monospace' }}
            />
          )}
        </div>

        {/* 提交按鈕 */}
        <Button
          type="primary"
          block
          size={isMobile ? 'middle' : 'large'}
          loading={loading}
          onClick={handleSubmit}
          disabled={!code.trim()}
          style={{ height: isMobile ? '40px' : '48px', marginBottom: 16 }}
        >
          驗證
        </Button>

        {/* 切換備用碼 / TOTP */}
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <Button
            type="link"
            onClick={() => {
              setUseBackupCode(!useBackupCode);
              setCode('');
              setError('');
            }}
            style={{ color: '#c9a962' }}
          >
            {useBackupCode ? '使用驗證器 App' : '使用備用碼'}
          </Button>
        </div>

        {/* 返回登入 */}
        <div style={{ textAlign: 'center' }}>
          <Link to="/login" style={{ color: '#8c8c8c' }}>
            <Space>
              <ArrowLeftOutlined />
              返回登入
            </Space>
          </Link>
        </div>

        {/* 提示文字 */}
        {!useBackupCode && (
          <Paragraph style={{ color: '#595959', fontSize: 12, textAlign: 'center', marginTop: 16, marginBottom: 0 }}>
            開啟 Google Authenticator 或 Microsoft Authenticator，
            輸入目前顯示的 6 位數驗證碼。
          </Paragraph>
        )}
      </Card>
    </div>
  );
};

export default MFAVerifyPage;
