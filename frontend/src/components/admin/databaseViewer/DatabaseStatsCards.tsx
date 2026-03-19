/**
 * 資料庫統計卡片
 * @description 顯示資料庫大小、表數量、記錄數等統計資訊
 */
import React from 'react';
import { Card, Statistic, Row, Col } from 'antd';
import {
  DatabaseOutlined, TableOutlined,
  InfoCircleOutlined, BranchesOutlined
} from '@ant-design/icons';
import type { EnhancedTableInfo } from './types';

interface DatabaseStatsCardsProps {
  databaseSize: string;
  tableCount: number;
  totalRecords: number;
  tablesWithFrontend: number;
}

/** 從增強表格列表計算統計資料的工具函數 */
// eslint-disable-next-line react-refresh/only-export-components
export function buildStatsFromTables(
  databaseSize: string,
  enhancedTables: EnhancedTableInfo[],
  totalRecords: number
): DatabaseStatsCardsProps {
  return {
    databaseSize,
    tableCount: enhancedTables.length,
    totalRecords,
    tablesWithFrontend: enhancedTables.filter(t => t.frontend_pages.length > 0).length,
  };
}

export const DatabaseStatsCards: React.FC<DatabaseStatsCardsProps> = ({
  databaseSize,
  tableCount,
  totalRecords,
  tablesWithFrontend,
}) => (
  <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
    <Col xs={12} md={6}>
      <Card>
        <Statistic
          title="資料庫大小"
          value={databaseSize}
          prefix={<DatabaseOutlined style={{ color: '#1976d2' }} />}
        />
      </Card>
    </Col>
    <Col xs={12} md={6}>
      <Card>
        <Statistic
          title="資料表數量"
          value={tableCount}
          prefix={<TableOutlined style={{ color: '#52c41a' }} />}
        />
      </Card>
    </Col>
    <Col xs={12} md={6}>
      <Card>
        <Statistic
          title="總記錄數"
          value={totalRecords}
          prefix={<InfoCircleOutlined style={{ color: '#faad14' }} />}
        />
      </Card>
    </Col>
    <Col xs={12} md={6}>
      <Card>
        <Statistic
          title="有前端對應"
          value={tablesWithFrontend}
          prefix={<BranchesOutlined style={{ color: '#722ed1' }} />}
        />
      </Card>
    </Col>
  </Row>
);
