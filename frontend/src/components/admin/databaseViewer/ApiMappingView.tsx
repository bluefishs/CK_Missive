/**
 * API 對應表檢視
 * @description 顯示資料表與 API 端點、前端頁面的對應關係
 */
import React from 'react';
import { Table, Space, Typography, Tag } from 'antd';
import { getCategoryColor } from '../../../config/databaseMetadata';
import type { EnhancedTableInfo } from './types';

const { Text } = Typography;

interface ApiMappingViewProps {
  enhancedTables: EnhancedTableInfo[];
  showChineseNames: boolean;
}

interface ApiMappingItem {
  table_name: string;
  chinese_name: string;
  api_endpoint: string;
  frontend_pages: string[];
  category: string;
}

export const ApiMappingView: React.FC<ApiMappingViewProps> = ({
  enhancedTables,
  showChineseNames,
}) => {
  const apiMappings: ApiMappingItem[] = [];

  enhancedTables.forEach(table => {
    table.api_endpoints.forEach((api: string) => {
      apiMappings.push({
        table_name: table.name,
        chinese_name: table.chinese_name,
        api_endpoint: api,
        frontend_pages: table.frontend_pages,
        category: table.category,
      });
    });
  });

  const apiColumns = [
    {
      title: '資料表',
      dataIndex: 'chinese_name',
      key: 'chinese_name',
      render: (text: string, record: ApiMappingItem) => (
        <Space vertical size="small">
          <Text strong>{showChineseNames ? text : record.table_name}</Text>
          <Tag color={getCategoryColor(record.category)} style={{ fontSize: '12px' }}>{record.category}</Tag>
        </Space>
      ),
    },
    {
      title: 'API 端點',
      dataIndex: 'api_endpoint',
      key: 'api_endpoint',
      render: (api: string) => {
        const [method, path] = api.split(' ');
        return (
          <Space>
            <Tag color={method === 'GET' ? 'blue' : method === 'POST' ? 'green' : method === 'PUT' ? 'orange' : 'red'}>
              {method}
            </Tag>
            <Text code>{path}</Text>
          </Space>
        );
      },
    },
    {
      title: '對應前端頁面',
      dataIndex: 'frontend_pages',
      key: 'frontend_pages',
      render: (pages: string[]) => (
        <Space wrap>
          {pages.map((page, index) => (
            <Tag key={index} color="blue" style={{ fontSize: '12px' }}>{page}</Tag>
          ))}
        </Space>
      ),
    },
  ];

  return (
    <Table
      columns={apiColumns}
      dataSource={apiMappings}
      size="small"
      pagination={{ pageSize: 30 }}
      rowKey={(record) => `${record.table_name}-${record.api_endpoint}`}
    />
  );
};
