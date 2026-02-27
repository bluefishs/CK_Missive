/**
 * authApi 單元測試
 * authApi Unit Tests
 *
 * 測試認證相關 API 服務（Email 驗證）
 *
 * 執行方式:
 *   cd frontend && npx vitest run src/api/__tests__/authApi.test.ts
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock apiClient
vi.mock('../client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

// Mock endpoints
vi.mock('../endpoints', () => ({
  AUTH_ENDPOINTS: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    ME: '/auth/me',
    PROFILE_UPDATE: '/auth/profile/update',
    PASSWORD_CHANGE: '/auth/password/change',
    PASSWORD_RESET: '/auth/password-reset',
    PASSWORD_RESET_CONFIRM: '/auth/password-reset-confirm',
    SEND_VERIFICATION: '/auth/send-verification',
    VERIFY_EMAIL: '/auth/verify-email',
    LOGIN_HISTORY: '/auth/login-history',
    SESSIONS: '/auth/sessions',
    SESSION_REVOKE: '/auth/sessions/revoke',
    SESSION_REVOKE_ALL: '/auth/sessions/revoke-all',
    MFA_SETUP: '/auth/mfa/setup',
    MFA_VERIFY: '/auth/mfa/verify',
    MFA_DISABLE: '/auth/mfa/disable',
    MFA_VALIDATE: '/auth/mfa/validate',
    MFA_STATUS: '/auth/mfa/status',
  },
}));

import { apiClient } from '../client';
import { sendVerificationEmail, verifyEmail } from '../authApi';

// ============================================================================
// sendVerificationEmail 測試
// ============================================================================

describe('sendVerificationEmail - 發送 Email 驗證信', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功發送驗證信應回傳 message', async () => {
    const mockResponse = { message: '驗證信已寄出，請檢查您的信箱' };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await sendVerificationEmail();

    expect(apiClient.post).toHaveBeenCalledWith('/auth/send-verification');
    expect(result.message).toBe('驗證信已寄出，請檢查您的信箱');
  });

  it('Email 已驗證時後端回傳提示', async () => {
    const mockResponse = { message: '您的 Email 已經驗證過了' };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await sendVerificationEmail();

    expect(result.message).toBe('您的 Email 已經驗證過了');
  });

  it('未登入時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Unauthorized'));

    await expect(sendVerificationEmail()).rejects.toThrow('Unauthorized');
  });

  it('伺服器錯誤時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Internal Server Error'));

    await expect(sendVerificationEmail()).rejects.toThrow('Internal Server Error');
  });

  it('應不帶任何參數呼叫端點', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ message: 'ok' });

    await sendVerificationEmail();

    // post 只傳一個參數 (URL)，沒有 body
    expect(apiClient.post).toHaveBeenCalledTimes(1);
    expect(apiClient.post).toHaveBeenCalledWith('/auth/send-verification');
  });

  it('網路錯誤時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Network Error'));

    await expect(sendVerificationEmail()).rejects.toThrow('Network Error');
  });
});

// ============================================================================
// verifyEmail 測試
// ============================================================================

describe('verifyEmail - 驗證 Email', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('成功驗證 Email 應回傳 verified: true', async () => {
    const mockResponse = {
      message: 'Email 驗證成功',
      verified: true,
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await verifyEmail('valid-token-abc123');

    expect(apiClient.post).toHaveBeenCalledWith('/auth/verify-email', { token: 'valid-token-abc123' });
    expect(result.message).toBe('Email 驗證成功');
    expect(result.verified).toBe(true);
  });

  it('Token 已使用過時應回傳 already_verified', async () => {
    const mockResponse = {
      message: '此 Email 已經驗證過',
      already_verified: true,
    };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await verifyEmail('used-token-xyz');

    expect(result.already_verified).toBe(true);
    expect(result.verified).toBeUndefined();
  });

  it('無效 Token 時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Invalid token'));

    await expect(verifyEmail('invalid-token')).rejects.toThrow('Invalid token');
  });

  it('過期 Token 時應拋出錯誤', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('Token expired'));

    await expect(verifyEmail('expired-token')).rejects.toThrow('Token expired');
  });

  it('應正確傳遞 token 參數', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ message: 'ok' });

    await verifyEmail('my-special-token-123');

    expect(apiClient.post).toHaveBeenCalledWith(
      '/auth/verify-email',
      { token: 'my-special-token-123' }
    );
  });

  it('空字串 Token 應仍然呼叫 API', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ message: 'ok' });

    await verifyEmail('');

    expect(apiClient.post).toHaveBeenCalledWith('/auth/verify-email', { token: '' });
  });

  it('伺服器錯誤時應正確拋出', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error('500 Internal Server Error'));

    await expect(verifyEmail('any-token')).rejects.toThrow('500 Internal Server Error');
  });

  it('回應僅含 message 時其餘欄位應為 undefined', async () => {
    const mockResponse = { message: '處理中' };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await verifyEmail('token');

    expect(result.message).toBe('處理中');
    expect(result.verified).toBeUndefined();
    expect(result.already_verified).toBeUndefined();
  });

  it('應只呼叫一次 API', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ message: 'ok' });

    await verifyEmail('token');

    expect(apiClient.post).toHaveBeenCalledTimes(1);
  });

  it('網路錯誤時應正確拋出', async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(verifyEmail('token')).rejects.toThrow('Failed to fetch');
  });
});
