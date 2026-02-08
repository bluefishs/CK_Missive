import React, { useState, useEffect } from 'react';
import { ResponsiveContent } from '../components/common';
import {
  Card,
  Alert,
  Button,
  Space,
  Typography,
  Descriptions,
  Steps,
  List,
  Tag,
  Divider
} from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  GoogleOutlined,
  SettingOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;

const GoogleAuthDiagnosticPage: React.FC = () => {
  const [currentDomain, setCurrentDomain] = useState('');
  const [googleClientId, setGoogleClientId] = useState('');
  const [diagnosticResult, setDiagnosticResult] = useState<any>(null);

  useEffect(() => {
    // 檢測當前運行環境
    setCurrentDomain(window.location.origin);
    setGoogleClientId(import.meta.env.VITE_GOOGLE_CLIENT_ID || '');

    runDiagnostic();
  }, []);

  const runDiagnostic = () => {
    const result = {
      domain: window.location.origin,
      port: window.location.port,
      protocol: window.location.protocol,
      hostname: window.location.hostname,
      clientId: import.meta.env.VITE_GOOGLE_CLIENT_ID || '',
      issues: [] as string[],
      recommendations: [] as string[]
    };

    // 檢查常見問題
    if (!result.clientId) {
      result.issues.push('Google Client ID 未設定');
      result.recommendations.push('請在 .env.development 檔案中設定 VITE_GOOGLE_CLIENT_ID');
    }

    if (result.protocol !== 'https:' && result.hostname !== 'localhost') {
      result.issues.push('非HTTPS協定或非localhost環境');
      result.recommendations.push('Google OAuth 需要 HTTPS 或 localhost 環境');
    }

    if (result.port && result.port !== '3000') {
      result.issues.push(`當前端口為 ${result.port}，可能與 Google Console 設定不符`);
      result.recommendations.push('確保 Google Console 中的授權來源包含當前端口');
    }

    setDiagnosticResult(result);
  };

  const getStepStatus = (condition: boolean) => {
    return condition ? 'finish' : 'error';
  };

  const authorizedOrigins = [
    'http://localhost:3000',
    'http://localhost:8001',
    'https://yourdomain.com'
  ];

  const authorizedRedirectUris = [
    'http://localhost:3000/auth/callback',
    'http://localhost:8001/auth/callback',
    'https://yourdomain.com/auth/callback'
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 頁面標題 */}
        <Card>
          <Title level={2}>
            <GoogleOutlined style={{ color: '#4285f4', marginRight: 8 }} />
            Google OAuth 診斷工具
          </Title>
          <Paragraph>
            此工具幫助您診斷和解決 Google OAuth 登入問題，特別是"origin not allowed"錯誤。
          </Paragraph>
        </Card>

        {/* 當前狀態 */}
        {diagnosticResult && (
          <Card title="當前系統狀態">
            <Descriptions bordered>
              <Descriptions.Item label="當前域名">{diagnosticResult.domain}</Descriptions.Item>
              <Descriptions.Item label="協定">{diagnosticResult.protocol}</Descriptions.Item>
              <Descriptions.Item label="主機名稱">{diagnosticResult.hostname}</Descriptions.Item>
              <Descriptions.Item label="端口">{diagnosticResult.port || '無'}</Descriptions.Item>
              <Descriptions.Item label="Google Client ID" span={2}>
                {diagnosticResult.clientId ? (
                  <Text code>{diagnosticResult.clientId}</Text>
                ) : (
                  <Text type="danger">未設定</Text>
                )}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        )}

        {/* 診斷步驟 */}
        <Card title="診斷步驟">
          <Steps direction="vertical" current={-1}>
            <Step
              status={getStepStatus(!!googleClientId)}
              title="Google Client ID 配置"
              description={
                googleClientId ? (
                  <Text type="success">✓ Google Client ID 已設定</Text>
                ) : (
                  <Text type="danger">✗ Google Client ID 未設定</Text>
                )
              }
            />
            <Step
              status={getStepStatus(currentDomain.includes('localhost') || currentDomain.startsWith('https:'))}
              title="協定檢查"
              description={
                currentDomain.includes('localhost') || currentDomain.startsWith('https:') ? (
                  <Text type="success">✓ 使用安全協定或localhost</Text>
                ) : (
                  <Text type="danger">✗ 需要 HTTPS 或 localhost 環境</Text>
                )
              }
            />
            <Step
              status="process"
              title="Google Console 設定檢查"
              description="需要手動確認 Google Console 設定"
            />
          </Steps>
        </Card>

        {/* 問題和建議 */}
        {diagnosticResult?.issues?.length > 0 && (
          <Card title="發現的問題">
            <Alert
              message="需要修復的問題"
              type="error"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <List
              dataSource={diagnosticResult.issues}
              renderItem={(item: string) => (
                <List.Item>
                  <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                  {item}
                </List.Item>
              )}
            />
          </Card>
        )}

        {diagnosticResult?.recommendations?.length > 0 && (
          <Card title="修復建議">
            <Alert
              message="建議的解決方案"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <List
              dataSource={diagnosticResult.recommendations}
              renderItem={(item: string) => (
                <List.Item>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  {item}
                </List.Item>
              )}
            />
          </Card>
        )}

        {/* Google Console 設定指南 */}
        <Card title="Google Console 設定指南">
          <Alert
            message="重要提醒"
            description="以下設定需要在 Google Cloud Console 中的 OAuth 2.0 客戶端 ID 設定頁面進行配置"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
          
          <Divider orientation="left">授權的 JavaScript 來源</Divider>
          <List
            header="需要在 Google Console 中添加以下來源："
            bordered
            dataSource={authorizedOrigins}
            renderItem={item => (
              <List.Item>
                <Space>
                  <Tag color={item.includes(window.location.origin) ? 'green' : 'default'}>
                    {item}
                  </Tag>
                  {item.includes(window.location.origin) && <Text type="success">(當前)</Text>}
                </Space>
              </List.Item>
            )}
          />

          <Divider orientation="left">授權的重新導向 URI</Divider>
          <List
            header="需要在 Google Console 中添加以下重新導向 URI："
            bordered
            dataSource={authorizedRedirectUris}
            renderItem={item => (
              <List.Item>
                <Tag color="blue">{item}</Tag>
              </List.Item>
            )}
          />

          <Divider />
          
          <Alert
            message="設定步驟"
            description={
              <div>
                <ol>
                  <li>前往 <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer">Google Cloud Console</a></li>
                  <li>選擇您的專案</li>
                  <li>前往「API 和服務」→「憑證」</li>
                  <li>找到您的 OAuth 2.0 客戶端 ID: <code>{googleClientId}</code></li>
                  <li>點擊編輯，在「授權的 JavaScript 來源」中添加上述來源</li>
                  <li>在「授權的重新導向 URI」中添加上述 URI</li>
                  <li>保存設定並等待幾分鐘生效</li>
                </ol>
                <Divider />
                <p><strong>解決 Cross-Origin-Opener-Policy 錯誤：</strong></p>
                <ul>
                  <li>確保前端運行在 <code>http://localhost:3000</code></li>
                  <li>確保後端運行在 <code>http://localhost:8001</code></li>
                  <li>檢查瀏覽器是否阻止了彈出視窗</li>
                  <li>嘗試在無痕模式下測試</li>
                  <li>清除瀏覽器 cookies 和 localStorage</li>
                </ul>
              </div>
            }
            type="info"
            showIcon
          />
        </Card>

        {/* 測試按鈕 */}
        <Card title="測試工具">
          <Space>
            <Button 
              type="primary" 
              icon={<GoogleOutlined />}
              onClick={() => window.location.reload()}
            >
              重新檢測
            </Button>
            <Button 
              icon={<SettingOutlined />}
              href="/login"
            >
              前往登入頁面測試
            </Button>
          </Space>
        </Card>
      </Space>
    </ResponsiveContent>
  );
};

export default GoogleAuthDiagnosticPage;