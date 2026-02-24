/**
 * ApiDocsPage.tsx - API 文件頁面
 *
 * @version 1.1.0
 * @date 2026-01-11
 */
import React, { lazy, Suspense } from 'react';
import { Card, Typography, Spin } from 'antd';
import 'swagger-ui-react/swagger-ui.css';

const SwaggerUI = lazy(() => import('swagger-ui-react'));
import { ResponsiveContent } from '../components/common';
import { SERVER_BASE_URL } from '../api/client';

const { Title, Paragraph } = Typography;

export const ApiDocumentationPage: React.FC = () => {
  // 使用共用的 API base URL
  const baseUrl = SERVER_BASE_URL; // 動態計算，不含 /api 後綴
  const swaggerUrl = `${baseUrl}/openapi.json`; // Backend OpenAPI JSON endpoint

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Title level={2}>API 文件與測試介面</Title>
      <Paragraph>
        本頁面整合了後端 API 的 Swagger UI 文件，您可以直接在此處檢視所有 API 端點並進行測試。
      </Paragraph>

      <Card style={{ minHeight: '600px' }}>
        <Suspense fallback={<Spin tip="載入 Swagger UI..." style={{ display: 'block', margin: '40px auto' }} />}>
          <SwaggerUI url={swaggerUrl} />
        </Suspense>
      </Card>
    </ResponsiveContent>
  );
};

export default ApiDocumentationPage;
