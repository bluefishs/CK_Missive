/**
 * ApiDocumentationPage.tsx - API 文件頁面
 *
 * @version 2.0.0
 * @date 2026-03-11
 */
import React, { lazy, Suspense, useMemo } from 'react';
import { Card, Typography, Alert, Spin, Space, Button, Divider } from 'antd';
import { ApiOutlined, ReloadOutlined, ExportOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';

// swagger-ui-react 延遲載入（~500KB，僅管理員使用）
const SwaggerUI = lazy(() =>
  import('swagger-ui-react').then(m => {
    // CSS 隨元件一起延遲載入
    import('swagger-ui-react/swagger-ui.css');
    return m;
  })
);
import { ResponsiveContent } from '../components/common';
import { SERVER_BASE_URL } from '../api/client';
import { logger } from '../utils/logger';

const { Title, Paragraph, Text } = Typography;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function fetchOpenApiSpec(): Promise<Record<string, any>> {
  const baseUrl = SERVER_BASE_URL;
  const response = await fetch(`${baseUrl}/openapi.json`, {
    cache: 'no-cache',
    headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const contentType = response.headers.get('content-type');
  if (!contentType || !contentType.includes('application/json')) {
    const text = await response.text();
    logger.error('Received non-JSON response:', text.substring(0, 200));
    throw new Error(`Expected JSON but got ${contentType}`);
  }

  const apiSpec = await response.json();
  if (!apiSpec.openapi && !apiSpec.swagger) {
    throw new Error('Invalid OpenAPI specification');
  }

  return apiSpec;
}

const ApiDocumentationPage: React.FC = () => {
  const { data: spec, isLoading, error, refetch } = useQuery({
    queryKey: ['openapi-spec'],
    queryFn: fetchOpenApiSpec,
    staleTime: 5 * 60 * 1000, // 5 分鐘
    retry: 1,
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const swaggerConfig = useMemo(() => ({
    spec,
    docExpansion: 'list' as const,
    defaultModelsExpandDepth: 1,
    defaultModelExpandDepth: 1,
    displayOperationId: false,
    filter: true,
    showExtensions: true,
    showCommonExtensions: true,
    tryItOutEnabled: true,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    requestInterceptor: (request: any) => {
      logger.debug('API Request:', request);
      return request;
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    responseInterceptor: (response: any) => {
      logger.debug('API Response:', response);
      return response;
    },
    onComplete: () => {
      logger.debug('Swagger UI loaded successfully');
    },
    layout: 'BaseLayout',
    deepLinking: true,
    displayRequestDuration: true,
    supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
  }), [spec]);

  const handleOpenInNewTab = () => {
    window.open('/api/docs', '_blank');
  };

  if (isLoading) {
    return (
      <ResponsiveContent maxWidth="full" padding="medium" style={{ textAlign: 'center' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>
          <Text>載入 API 文件中...</Text>
        </div>
      </ResponsiveContent>
    );
  }

  if (error) {
    return (
      <ResponsiveContent maxWidth="full" padding="medium">
        <Alert
          message="載入失敗"
          description={`無法載入 API 文件：${error instanceof Error ? error.message : '未知錯誤'}`}
          type="error"
          showIcon
          action={
            <Button size="small" danger onClick={() => refetch()}>
              重新載入
            </Button>
          }
        />
      </ResponsiveContent>
    );
  }

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
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
                onClick={() => refetch()}
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
                  {Object.values(spec.paths || {}).reduce((total: number, path: unknown) =>
                    total + Object.keys(path as Record<string, unknown>).length, 0
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
              <Suspense fallback={<Spin tip="載入 Swagger UI..." style={{ display: 'block', margin: '40px auto' }}><div style={{ padding: 40 }} /></Spin>}>
                <SwaggerUI {...swaggerConfig} />
              </Suspense>
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
              <Text strong>搜尋功能：</Text>
              使用上方的搜尋框可以快速找到特定的 API 端點。
            </Paragraph>
            <Paragraph>
              <Text strong>測試功能：</Text>
              點選任何端點的 &quot;Try it out&quot; 按鈕可以直接測試 API。
            </Paragraph>
            <Paragraph>
              <Text strong>參數說明：</Text>
              每個端點都包含詳細的參數說明、範例和可能的回應格式。
            </Paragraph>
            <Paragraph>
              <Text strong>認證：</Text>
              某些 API 需要認證。請確保您已登入系統或提供有效的 API 金鑰。
            </Paragraph>
          </Space>
        </Card>

      </Space>
    </ResponsiveContent>
  );
};

export default ApiDocumentationPage;
