/**
 * 統計報表頁面
 *
 * @version 3.0.0 - 模組化重構：Hook 提取 + 子元件拆分
 * @date 2026-01-28
 */

import React from 'react';
import { Card, Typography, Tabs } from 'antd';
import { DollarOutlined, FileTextOutlined } from '@ant-design/icons';
import { useResponsive } from '../../hooks';
import BudgetAnalysisTab from './BudgetAnalysisTab';
import DocumentAnalysisTab from './DocumentAnalysisTab';

const { Title } = Typography;

const ReportsPage: React.FC = () => {
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  return (
    <div style={{ padding: pagePadding }}>
      <Title level={isMobile ? 4 : 2} style={{ marginBottom: 16 }}>
        統計報表
      </Title>

      <Card>
        <Tabs
          defaultActiveKey="budget"
          size={isMobile ? 'small' : 'middle'}
          items={[
            {
              key: 'budget',
              label: (
                <span>
                  <DollarOutlined /> 經費分析
                </span>
              ),
              children: <BudgetAnalysisTab isMobile={isMobile} />,
            },
            {
              key: 'documents',
              label: (
                <span>
                  <FileTextOutlined /> 公文數量
                </span>
              ),
              children: <DocumentAnalysisTab isMobile={isMobile} />,
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default ReportsPage;
