/**
 * ApiDocumentationPage.tsx - API 文件頁面
 *
 * @version 1.1.0
 * @date 2026-01-11
 */
import React, { useState, useEffect } from 'react';
import { Card, Typography, Alert, Spin, Space, Button, Divider } from 'antd';
import { ApiOutlined, ReloadOutlined, ExportOutlined } from '@ant-design/icons';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import { VITE_API_BASE_URL } from '../config/env';
import './ApiDocumentationPage.css';

const { Title, Paragraph, Text } = Typography;

const ApiDocumentationPage: React.FC = () => {
  const [spec, setSpec] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 從後端獲取 OpenAPI 規範
  const fetchApiSpec = async () => {
    try {
      setLoading(true);
      setError(null);

      // 使用共用的 API base URL
      const baseUrl = VITE_API_BASE_URL;
      const timestamp = new Date().getTime();
      const response = await fetch(`${baseUrl}/openapi.json?t=${timestamp}`, {
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      console.log('OpenAPI response status:', response.status);
      console.log('OpenAPI response headers:', response.headers);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type');
      console.log('Content-Type:', contentType);

      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Received non-JSON response:', text.substring(0, 200));
        throw new Error(`Expected JSON but got ${contentType}. Response: ${text.substring(0, 100)}...`);
      }

      const apiSpec = await response.json();
      console.log('OpenAPI spec loaded:', apiSpec);

      // 驗證 OpenAPI 規範格式
      if (!apiSpec.openapi && !apiSpec.swagger) {
        throw new Error('Invalid OpenAPI specification: missing openapi or swagger version field');
      }

      setSpec(apiSpec);
    } catch (err) {
      setError(err instanceof Error ? err.message : '載入 API 文件失敗');
      console.error('Error fetching API spec:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApiSpec();
  }, []);

  // 自定義 Swagger UI 設定
  const swaggerConfig = {
    spec,
    docExpansion: 'list' as const, // 預設展開方式
    defaultModelsExpandDepth: 1,
    defaultModelExpandDepth: 1,
    displayOperationId: false,
    filter: true, // 啟用搜尋功能
    showExtensions: true,
    showCommonExtensions: true,
    tryItOutEnabled: true, // 啟用 "Try it out" 功能
    requestInterceptor: (request: any) => {
      // 可以在這裡添加認證 header 等
      console.log('API Request:', request);
      return request;
    },
    responseInterceptor: (response: any) => {
      console.log('API Response:', response);
      return response;
    },
    onComplete: () => {
      console.log('Swagger UI loaded successfully');
    },
    layout: 'BaseLayout',
    deepLinking: true,
    displayRequestDuration: true,
    supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
  };

  const handleOpenInNewTab = () => {
    window.open('/api/docs', '_blank');
  };

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>
          <Text>載入 API 文件中...</Text>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="載入失敗"
          description={`無法載入 API 文件：${error}`}
          type="error"
          showIcon
          action={
            <Button size="small" danger onClick={fetchApiSpec}>
              重新載入
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        
        {/* 頁面標題 */}
        <Card>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space align="center">
              <ApiOutlined style={{ fontSize: '32px', color: '#1890ff' }} />
              <Title level={2} style={{ margin: 0 }}>API 文件</Title>
            </Space>
            
            <Paragraph>
              乾坤測繪公文管理系統的完整 API 文件。您可以在這裡查看所有可用的 API 端點、
              請求參數、回應格式，並直接測試 API 功能。
            </Paragraph>

            <Space>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={fetchApiSpec}
                type="default"
              >
                重新載入
              </Button>
              <Button 
                icon={<ExportOutlined />} 
                onClick={handleOpenInNewTab}
                type="primary"
              >
                在新視窗開啟原生 Swagger UI
              </Button>
            </Space>
          </Space>
        </Card>

        {/* API 文件統計 */}
        {spec && (
          <Card title="API 概覽" size="small">
            <Space direction="horizontal" size="large">
              <div>
                <Text strong>API 版本：</Text>
                <Text code>{spec.info?.version || 'N/A'}</Text>
              </div>
              <div>
                <Text strong>端點數量：</Text>
                <Text code>
                  {Object.values(spec.paths || {}).reduce((total: number, path: any) => 
                    total + Object.keys(path).length, 0
                  )}
                </Text>
              </div>
              <div>
                <Text strong>伺服器：</Text>
                <Text code>{spec.servers?.[0]?.url || 'localhost:8001'}</Text>
              </div>
            </Space>
          </Card>
        )}

        <Divider />

        {/* Swagger UI 主體 */}
        <Card 
          title="API 端點文件" 
          style={{ minHeight: '800px' }}
          styles={{ body: { padding: 0 } }}
        >
          <div style={{ padding: '16px' }} className="swagger-container">
            {spec ? (
              <SwaggerUI {...swaggerConfig} />
            ) : (
              <Alert
                message="無法載入 API 規範"
                type="warning"
                showIcon
              />
            )}
          </div>
        </Card>

        {/* 使用說明 */}
        <Card title="使用說明" size="small">
          <Space direction="vertical">
            <Paragraph>
              <Text strong>🔍 搜尋功能：</Text>
              使用上方的搜尋框可以快速找到特定的 API 端點。
            </Paragraph>
            <Paragraph>
              <Text strong>🧪 測試功能：</Text>
              點選任何端點的 "Try it out" 按鈕可以直接測試 API。
            </Paragraph>
            <Paragraph>
              <Text strong>📋 參數說明：</Text>
              每個端點都包含詳細的參數說明、範例和可能的回應格式。
            </Paragraph>
            <Paragraph>
              <Text strong>🔐 認證：</Text>
              某些 API 需要認證。請確保您已登入系統或提供有效的 API 金鑰。
            </Paragraph>
          </Space>
        </Card>

      </Space>
    </div>
  );
};

export default ApiDocumentationPage;