/**
 * ApiDocsPage.tsx - API 文件頁面
 *
 * @version 1.1.0
 * @date 2026-01-11
 */
import React from 'react';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import { Card, Typography, Spin, Alert } from 'antd';
import { API_BASE_URL, VITE_API_BASE_URL } from '../config/env';

const { Title, Paragraph } = Typography;

export const ApiDocumentationPage: React.FC = () => {
  // 使用共用的 API base URL
  const baseUrl = VITE_API_BASE_URL; // 不含 /api 後綴
  const swaggerUrl = `${baseUrl}/openapi.json`; // Backend OpenAPI JSON endpoint

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>API 文件與測試介面</Title>
      <Paragraph>
        本頁面整合了後端 API 的 Swagger UI 文件，您可以直接在此處檢視所有 API 端點並進行測試。
      </Paragraph>

      <Card style={{ minHeight: '600px' }}>
        <SwaggerUI url={swaggerUrl} />
      </Card>
    </div>
  );
};

export default ApiDocumentationPage;
