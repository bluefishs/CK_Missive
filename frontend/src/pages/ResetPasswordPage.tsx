/**
 * ResetPasswordPage - 密碼重設確認頁面
 *
 * 從 URL query param 取得 token，讓使用者設定新密碼。
 *
 * @version 1.0.0
 * @date 2026-02-08
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Typography,
  Result,
  Space,
  Row,
  Col,
  Progress,
  App,
} from 'antd';
import {
  LockOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import { AUTH_ENDPOINTS } from '../api/endpoints';

const { Title, Text } = Typography;

import type { ResetPasswordFormValues } from '../types/forms';

type ResetPasswordForm = ResetPasswordFormValues;

/**
 * 計算密碼強度分數與標籤
 */
function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  if (!password) return { score: 0, label: '', color: '#d9d9d9' };

  let score = 0;

  // 長度分數（最高 25）
  score += Math.min(password.length * 2, 25);

  // 字元類型分數（每種 15，最高 60）
  if (/[a-z]/.test(password)) score += 15;
  if (/[A-Z]/.test(password)) score += 15;
  if (/\d/.test(password)) score += 15;
  if (/[!@#$%^&*(),.?":{}|<>\-_=+[\]\\';/`~]/.test(password)) score += 15;

  // 混合度分數（最高 15）
  const uniqueChars = new Set(password).size;
  if (uniqueChars >= 10) score += 15;
  else if (uniqueChars >= 7) score += 10;
  else if (uniqueChars >= 5) score += 5;

  score = Math.min(score, 100);

  if (score < 40) return { score, label: '弱', color: '#ff4d4f' };
  if (score < 60) return { score, label: '中', color: '#faad14' };
  if (score < 80) return { score, label: '強', color: '#52c41a' };
  return { score, label: '非常強', color: '#1890ff' };
}

const ResetPasswordPage: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [passwordValue, setPasswordValue] = useState('');

  const token = searchParams.get('token');

  const strength = useMemo(() => getPasswordStrength(passwordValue), [passwordValue]);

  // 如果沒有 token，顯示錯誤
  if (!token) {
    return (
      <Row
        justify="center"
        align="middle"
        style={{
          minHeight: '100vh',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: '20px',
        }}
      >
        <Col xs={24} sm={20} md={16} lg={12} xl={8}>
          <Card
            style={{
              borderRadius: '12px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
              border: 'none',
            }}
          >
            <Result
              status="error"
              title="無效的重設連結"
              subTitle="此密碼重設連結無效或已過期。請重新申請密碼重設。"
              extra={[
                <Button
                  type="primary"
                  key="forgot"
                  onClick={() => navigate('/forgot-password')}
                >
                  重新申請
                </Button>,
                <Button
                  key="login"
                  onClick={() => navigate('/login')}
                >
                  返回登入
                </Button>,
              ]}
            />
          </Card>
        </Col>
      </Row>
    );
  }

  // 成功畫面
  if (success) {
    return (
      <Row
        justify="center"
        align="middle"
        style={{
          minHeight: '100vh',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: '20px',
        }}
      >
        <Col xs={24} sm={20} md={16} lg={12} xl={8}>
          <Card
            style={{
              borderRadius: '12px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
              border: 'none',
            }}
          >
            <Result
              status="success"
              title="密碼重設成功"
              subTitle="您的密碼已成功更新。所有裝置上的登入狀態已被登出，請使用新密碼重新登入。"
              extra={
                <Button
                  type="primary"
                  size="large"
                  onClick={() => navigate('/login')}
                >
                  前往登入
                </Button>
              }
            />
          </Card>
        </Col>
      </Row>
    );
  }

  const handleSubmit = async (values: ResetPasswordForm) => {
    setLoading(true);
    try {
      await apiClient.post(AUTH_ENDPOINTS.PASSWORD_RESET_CONFIRM, {
        token,
        new_password: values.new_password,
      });
      setSuccess(true);
    } catch (error: unknown) {
      const apiError = error as { message?: string };
      message.error(apiError?.message || '密碼重設失敗，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Row
      justify="center"
      align="middle"
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '20px',
      }}
    >
      <Col xs={24} sm={20} md={16} lg={12} xl={8}>
        <Card
          style={{
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
            border: 'none',
          }}
        >
          <Space
            direction="vertical"
            size="large"
            style={{ width: '100%' }}
          >
            <div style={{ textAlign: 'center' }}>
              <Title level={2} style={{ color: '#1890ff', marginBottom: 8 }}>
                設定新密碼
              </Title>
              <Text type="secondary">
                請輸入您的新密碼，密碼需至少 12 個字元
              </Text>
            </div>

            <Form
              form={form}
              name="resetPassword"
              onFinish={handleSubmit}
              autoComplete="off"
              layout="vertical"
              size="large"
            >
              <Form.Item
                label="新密碼"
                name="new_password"
                rules={[
                  { required: true, message: '請輸入新密碼！' },
                  { min: 12, message: '密碼長度至少需要 12 個字元' },
                  {
                    pattern: /[A-Z]/,
                    message: '密碼必須包含至少一個大寫字母',
                  },
                  {
                    pattern: /[a-z]/,
                    message: '密碼必須包含至少一個小寫字母',
                  },
                  {
                    pattern: /\d/,
                    message: '密碼必須包含至少一個數字',
                  },
                  {
                    pattern: /[!@#$%^&*(),.?":{}|<>\-_=+[\]\\';/`~]/,
                    message: '密碼必須包含至少一個特殊字元',
                  },
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="請輸入新密碼"
                  autoComplete="new-password"
                  onChange={(e) => setPasswordValue(e.target.value)}
                />
              </Form.Item>

              {/* 密碼強度指示器 */}
              {passwordValue && (
                <Form.Item style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Progress
                      percent={strength.score}
                      showInfo={false}
                      strokeColor={strength.color}
                      size="small"
                      style={{ flex: 1 }}
                    />
                    <Text
                      style={{
                        color: strength.color,
                        fontWeight: 'bold',
                        minWidth: 60,
                        textAlign: 'right',
                      }}
                    >
                      {strength.label}
                    </Text>
                  </div>
                  <Space
                    direction="vertical"
                    size={2}
                    style={{ marginTop: 8, fontSize: 12 }}
                  >
                    <Text
                      type={passwordValue.length >= 12 ? undefined : 'danger'}
                      style={{ fontSize: 12 }}
                    >
                      {passwordValue.length >= 12 ? <CheckCircleOutlined /> : null}{' '}
                      至少 12 個字元
                    </Text>
                    <Text
                      type={/[A-Z]/.test(passwordValue) ? undefined : 'danger'}
                      style={{ fontSize: 12 }}
                    >
                      {/[A-Z]/.test(passwordValue) ? <CheckCircleOutlined /> : null}{' '}
                      包含大寫字母
                    </Text>
                    <Text
                      type={/[a-z]/.test(passwordValue) ? undefined : 'danger'}
                      style={{ fontSize: 12 }}
                    >
                      {/[a-z]/.test(passwordValue) ? <CheckCircleOutlined /> : null}{' '}
                      包含小寫字母
                    </Text>
                    <Text
                      type={/\d/.test(passwordValue) ? undefined : 'danger'}
                      style={{ fontSize: 12 }}
                    >
                      {/\d/.test(passwordValue) ? <CheckCircleOutlined /> : null}{' '}
                      包含數字
                    </Text>
                    <Text
                      type={
                        /[!@#$%^&*(),.?":{}|<>\-_=+[\]\\';/`~]/.test(passwordValue)
                          ? undefined
                          : 'danger'
                      }
                      style={{ fontSize: 12 }}
                    >
                      {/[!@#$%^&*(),.?":{}|<>\-_=+[\]\\';/`~]/.test(passwordValue)
                        ? <CheckCircleOutlined />
                        : null}{' '}
                      包含特殊字元
                    </Text>
                  </Space>
                </Form.Item>
              )}

              <Form.Item
                label="確認新密碼"
                name="confirm_password"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: '請再次輸入新密碼！' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('兩次輸入的密碼不一致！'));
                    },
                  }),
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="請再次輸入新密碼"
                  autoComplete="new-password"
                />
              </Form.Item>

              <Form.Item style={{ marginBottom: 16 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  style={{ width: '100%' }}
                >
                  重設密碼
                </Button>
              </Form.Item>

              <div style={{ textAlign: 'center' }}>
                <Button
                  type="link"
                  icon={<ArrowLeftOutlined />}
                  onClick={() => navigate('/login')}
                  style={{ padding: 0 }}
                >
                  返回登入
                </Button>
              </div>
            </Form>
          </Space>
        </Card>
      </Col>
    </Row>
  );
};

export default ResetPasswordPage;
