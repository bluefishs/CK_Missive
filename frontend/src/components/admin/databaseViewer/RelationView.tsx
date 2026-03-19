/**
 * 資料表關聯圖檢視
 * @description 依分類顯示各資料表的關聯與統計
 */
import React from 'react';
import { Card, Space, Typography, Row, Col, Badge } from 'antd';
import { getCategoryDisplayName, getCategoryColor } from '../../../config/databaseMetadata';
import type { EnhancedTableInfo } from './types';

const { Text } = Typography;

interface RelationViewProps {
  enhancedTables: EnhancedTableInfo[];
  showChineseNames: boolean;
}

export const RelationView: React.FC<RelationViewProps> = ({
  enhancedTables,
  showChineseNames,
}) => {
  const categorizedTables = enhancedTables.reduce<Record<string, EnhancedTableInfo[]>>((acc, table) => {
    const category = table.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category]!.push(table);
    return acc;
  }, {});

  return (
    <Row gutter={[16, 16]}>
      {Object.entries(categorizedTables).map(([category, tables]) => (
        <Col span={8} key={category}>
          <Card
            title={getCategoryDisplayName(category)}
            styles={{ header: { background: getCategoryColor(category), color: 'white' } }}
            size="small"
          >
            <Space vertical style={{ width: '100%' }}>
              {tables.map((table, index: number) => (
                <Card key={index} size="small" style={{ background: '#fafafa' }}>
                  <Space vertical size="small" style={{ width: '100%' }}>
                    <Text strong>{showChineseNames ? table.chinese_name : table.name}</Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>{table.description}</Text>
                    <div>
                      <Badge count={table.recordCount} style={{ backgroundColor: '#52c41a' }} />
                      <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
                        {table.api_endpoints.length} API, {table.frontend_pages.length} 頁面
                      </Text>
                    </div>
                  </Space>
                </Card>
              ))}
            </Space>
          </Card>
        </Col>
      ))}
    </Row>
  );
};
