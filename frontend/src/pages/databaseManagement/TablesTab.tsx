import React from 'react';
import { Table, Button, Space, Badge, Tag, Typography, Tooltip } from 'antd';
import { TableOutlined, SearchOutlined, DownloadOutlined } from '@ant-design/icons';
import type { TableInfo } from '../../types/api';

const { Text } = Typography;

interface TablesTabProps {
  tables: TableInfo[];
  onFetchTableData: (tableName: string) => void;
  onExportTableData: (tableName: string) => void;
}

export const TablesTab: React.FC<TablesTabProps> = ({
  tables,
  onFetchTableData,
  onExportTableData,
}) => {
  const columns = [
    {
      title: '表格名稱',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <Button type="link" onClick={() => onFetchTableData(name)} style={{ padding: 0 }}>
            <TableOutlined /> {name}
          </Button>
        </Space>
      )
    },
    {
      title: '記錄數量',
      dataIndex: 'recordCount',
      key: 'recordCount',
      render: (count: number) => (
        <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
      )
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: string) => <Tag color="blue">{size}</Tag>
    },
    {
      title: '最後修改',
      dataIndex: 'lastModified',
      key: 'lastModified',
      render: (time: string) => <Text type="secondary">{time}</Text>
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: TableInfo) => (
        <Space size="small">
          <Tooltip title="查看數據">
            <Button
              type="text"
              size="small"
              icon={<SearchOutlined />}
              onClick={() => onFetchTableData(record.name)}
            />
          </Tooltip>
          <Tooltip title="匯出 CSV">
            <Button
              type="text"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => onExportTableData(record.name)}
            />
          </Tooltip>
        </Space>
      )
    }
  ];

  return (
    <Table
      columns={columns}
      dataSource={tables}
      size="small"
      pagination={false}
      rowKey="name"
    />
  );
};
