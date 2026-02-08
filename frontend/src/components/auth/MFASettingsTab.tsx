/**
 * MFA 設定 Tab 元件
 *
 * 在個人資料頁面中顯示 MFA 雙因素認證的設定介面：
 * - 啟用/停用 MFA
 * - 掃描 QR code
 * - 備用碼顯示與下載
 *
 * @version 1.0.0
 * @date 2026-02-08
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Typography,
  Input,
  Alert,
  Space,
  Tag,
  Modal,
  App,
  Divider,
  List,
} from 'antd';
import {
  SafetyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CopyOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import type { MFASetupData, MFAStatus } from '../../types/api';

const { Title, Text, Paragraph } = Typography;

export const MFASettingsTab: React.FC = () => {
  const { message, modal } = App.useApp();

  const [mfaStatus, setMfaStatus] = useState<MFAStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [setupData, setSetupData] = useState<MFASetupData | null>(null);
  const [setupStep, setSetupStep] = useState<'idle' | 'qrcode' | 'verify' | 'done'>('idle');
  const [verifyCode, setVerifyCode] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [disableModalVisible, setDisableModalVisible] = useState(false);
  const [disablePassword, setDisablePassword] = useState('');
  const [disableLoading, setDisableLoading] = useState(false);

  const loadMFAStatus = useCallback(async () => {
    try {
      setLoading(true);
      const status = await apiClient.post<MFAStatus>(API_ENDPOINTS.AUTH.MFA_STATUS, {});
      setMfaStatus(status);
    } catch {
      // MFA 狀態查詢失敗時，假設未啟用
      setMfaStatus({ mfa_enabled: false, backup_codes_remaining: 0 });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMFAStatus();
  }, [loadMFAStatus]);

  // 開始設定 MFA
  const handleSetup = async () => {
    try {
      const data = await apiClient.post<MFASetupData>(API_ENDPOINTS.AUTH.MFA_SETUP, {});
      setSetupData(data);
      setSetupStep('qrcode');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'MFA 設定失敗';
      message.error(errorMessage);
    }
  };

  // 驗證 TOTP 並啟用
  const handleVerify = async () => {
    if (!verifyCode || verifyCode.length !== 6) {
      message.warning('請輸入 6 位數驗證碼');
      return;
    }

    setVerifyLoading(true);
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.MFA_VERIFY, { code: verifyCode });
      message.success('MFA 已成功啟用!');
      setSetupStep('done');
      await loadMFAStatus();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '驗證碼不正確';
      message.error(errorMessage);
    } finally {
      setVerifyLoading(false);
    }
  };

  // 停用 MFA
  const handleDisable = async () => {
    if (!disablePassword) {
      message.warning('請輸入密碼');
      return;
    }

    setDisableLoading(true);
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.MFA_DISABLE, { password: disablePassword });
      message.success('MFA 已停用');
      setDisableModalVisible(false);
      setDisablePassword('');
      setSetupData(null);
      setSetupStep('idle');
      await loadMFAStatus();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '停用失敗';
      message.error(errorMessage);
    } finally {
      setDisableLoading(false);
    }
  };

  // 複製備用碼
  const handleCopyBackupCodes = () => {
    if (!setupData?.backup_codes) return;
    const text = setupData.backup_codes.join('\n');
    navigator.clipboard.writeText(text).then(() => {
      message.success('備用碼已複製到剪貼簿');
    });
  };

  // 下載備用碼
  const handleDownloadBackupCodes = () => {
    if (!setupData?.backup_codes) return;
    const content = [
      'CK_Missive MFA 備用碼',
      '========================',
      '請妥善保管以下備用碼，每組只能使用一次。',
      '',
      ...setupData.backup_codes.map((code, i) => `${i + 1}. ${code}`),
      '',
      `生成時間: ${new Date().toLocaleString()}`,
    ].join('\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ck-missive-mfa-backup-codes.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    message.success('備用碼已下載');
  };

  // 確認停用 MFA
  const confirmDisable = () => {
    modal.confirm({
      title: '停用雙因素認證',
      icon: <ExclamationCircleOutlined />,
      content: '停用後將降低帳戶安全性。確定要停用嗎？',
      okText: '確定停用',
      cancelText: '取消',
      okType: 'danger',
      onOk: () => setDisableModalVisible(true),
    });
  };

  if (loading) {
    return <Card loading />;
  }

  return (
    <div>
      <Title level={4}>
        <SafetyOutlined style={{ marginRight: 8 }} />
        雙因素認證 (MFA)
      </Title>

      <Paragraph type="secondary">
        啟用雙因素認證後，登入時除了密碼外，還需要輸入驗證器 App（如 Google Authenticator、Microsoft Authenticator）產生的一次性驗證碼，大幅提升帳戶安全性。
      </Paragraph>

      {/* 目前狀態 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Text strong>目前狀態：</Text>
          {mfaStatus?.mfa_enabled ? (
            <Tag icon={<CheckCircleOutlined />} color="success">已啟用</Tag>
          ) : (
            <Tag icon={<CloseCircleOutlined />} color="default">未啟用</Tag>
          )}
          {mfaStatus?.mfa_enabled && mfaStatus.backup_codes_remaining > 0 && (
            <Text type="secondary">
              (剩餘 {mfaStatus.backup_codes_remaining} 組備用碼)
            </Text>
          )}
        </Space>
      </Card>

      {/* 未啟用 - 顯示啟用按鈕 */}
      {!mfaStatus?.mfa_enabled && setupStep === 'idle' && (
        <Button
          type="primary"
          icon={<SafetyOutlined />}
          onClick={handleSetup}
          size="large"
        >
          啟用雙因素認證
        </Button>
      )}

      {/* 步驟 1: 掃描 QR Code */}
      {setupStep === 'qrcode' && setupData && (
        <Card title="步驟 1：掃描 QR Code" style={{ marginTop: 16 }}>
          <Alert
            message="請使用驗證器 App 掃描以下 QR Code"
            description="支援 Google Authenticator、Microsoft Authenticator 等 TOTP 標準驗證器。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <div style={{ textAlign: 'center', marginBottom: 16 }}>
            <img
              src={`data:image/png;base64,${setupData.qr_code_base64}`}
              alt="MFA QR Code"
              style={{ width: 200, height: 200, border: '1px solid #d9d9d9', borderRadius: 8 }}
            />
          </div>

          <Paragraph type="secondary" style={{ textAlign: 'center' }}>
            無法掃描？手動輸入以下金鑰：
          </Paragraph>
          <div style={{
            textAlign: 'center',
            background: '#f5f5f5',
            padding: '8px 16px',
            borderRadius: 4,
            fontFamily: 'monospace',
            fontSize: 14,
            letterSpacing: 2,
            marginBottom: 16,
            wordBreak: 'break-all',
          }}>
            {setupData.secret}
          </div>

          <Divider />

          <Title level={5}>備用碼</Title>
          <Alert
            message="請妥善保管以下備用碼"
            description="當您無法使用驗證器 App 時，可以使用備用碼登入。每組備用碼只能使用一次。此為唯一一次顯示機會。"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <List
            grid={{ gutter: 8, column: 2 }}
            dataSource={setupData.backup_codes}
            renderItem={(code) => (
              <List.Item>
                <div style={{
                  fontFamily: 'monospace',
                  fontSize: 16,
                  textAlign: 'center',
                  padding: '4px 8px',
                  background: '#fafafa',
                  border: '1px solid #f0f0f0',
                  borderRadius: 4,
                }}>
                  {code}
                </div>
              </List.Item>
            )}
          />

          <Space style={{ marginTop: 16 }}>
            <Button icon={<CopyOutlined />} onClick={handleCopyBackupCodes}>
              複製
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleDownloadBackupCodes}>
              下載
            </Button>
          </Space>

          <Divider />

          <Title level={5}>步驟 2：輸入驗證碼</Title>
          <Paragraph type="secondary">
            在驗證器 App 中找到 CK_Missive 的條目，輸入顯示的 6 位數驗證碼：
          </Paragraph>

          <Space.Compact style={{ width: '100%', maxWidth: 300 }}>
            <Input
              placeholder="000000"
              value={verifyCode}
              onChange={(e) => {
                const val = e.target.value.replace(/\D/g, '');
                if (val.length <= 6) setVerifyCode(val);
              }}
              onPressEnter={handleVerify}
              maxLength={6}
              inputMode="numeric"
              style={{ textAlign: 'center', letterSpacing: '6px', fontSize: 20, fontFamily: 'monospace' }}
            />
            <Button
              type="primary"
              onClick={handleVerify}
              loading={verifyLoading}
              disabled={verifyCode.length !== 6}
            >
              驗證並啟用
            </Button>
          </Space.Compact>

          <div style={{ marginTop: 16 }}>
            <Button
              type="link"
              onClick={() => {
                setSetupStep('idle');
                setSetupData(null);
                setVerifyCode('');
              }}
            >
              取消設定
            </Button>
          </div>
        </Card>
      )}

      {/* 步驟完成 */}
      {setupStep === 'done' && (
        <Alert
          message="MFA 已成功啟用!"
          description="下次登入時，您需要在輸入密碼後提供驗證器 App 的驗證碼。"
          type="success"
          showIcon
          style={{ marginTop: 16 }}
        />
      )}

      {/* 已啟用 - 顯示停用按鈕 */}
      {mfaStatus?.mfa_enabled && setupStep !== 'qrcode' && (
        <div style={{ marginTop: 16 }}>
          <Button
            danger
            icon={<CloseCircleOutlined />}
            onClick={confirmDisable}
          >
            停用雙因素認證
          </Button>
        </div>
      )}

      {/* 停用 MFA Modal */}
      <Modal
        title="停用雙因素認證"
        open={disableModalVisible}
        onCancel={() => {
          setDisableModalVisible(false);
          setDisablePassword('');
        }}
        footer={null}
        destroyOnHidden
      >
        <Paragraph>
          請輸入您的帳號密碼以確認身份：
        </Paragraph>
        <Input.Password
          prefix={<LockOutlined />}
          placeholder="請輸入密碼"
          value={disablePassword}
          onChange={(e) => setDisablePassword(e.target.value)}
          onPressEnter={handleDisable}
          style={{ marginBottom: 16 }}
        />
        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
          <Button onClick={() => {
            setDisableModalVisible(false);
            setDisablePassword('');
          }}>
            取消
          </Button>
          <Button
            type="primary"
            danger
            loading={disableLoading}
            onClick={handleDisable}
          >
            確認停用
          </Button>
        </Space>
      </Modal>
    </div>
  );
};
