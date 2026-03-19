/**
 * 表格詳情 Modal
 * @description 顯示單一資料表的完整資訊（基本資料、欄位、API、關聯頁面）
 */
import React from 'react';
import {
  Modal, Card, Space, Typography, Tag,
  Descriptions, Divider, Badge,
} from 'antd';
import {
  FieldTimeOutlined, FileTextOutlined,
} from '@ant-design/icons';
import type { EnhancedTableInfo } from './types';

const { Text } = Typography;

interface TableDetailModalProps {
  open: boolean;
  onClose: () => void;
  table: EnhancedTableInfo | undefined;
}

export const TableDetailModal: React.FC<TableDetailModalProps> = ({
  open,
  onClose,
  table,
}) => (
  <Modal
    title={table ? `${table.name} 詳細資訊` : ''}
    open={open}
    onCancel={onClose}
    footer={null}
    width={800}
  >
    {table && <TableDetailContent table={table} />}
  </Modal>
);

/** Modal 內部內容 */
const TableDetailContent: React.FC<{ table: EnhancedTableInfo }> = ({ table }) => (
  <div>
    <Descriptions title="基本資訊" bordered size="small" column={2} items={[
      { key: '中文名稱', label: '中文名稱', children: table.chinese_name },
      { key: '英文名稱', label: '英文名稱', children: table.name },
      { key: '資料表類型', label: '資料表類型', children: (<Tag color={table.color}>{table.category}</Tag>) },
      { key: '記錄數量', label: '記錄數量', children: (<Badge count={table.recordCount} style={{ backgroundColor: '#52c41a' }} />) },
      { key: '資料大小', label: '資料大小', children: table.size },
      { key: '最後修改', label: '最後修改', children: table.lastModified },
      { key: '描述', label: '描述', span: 2, children: table.description },
    ]} />

    <Divider titlePlacement="left">主要欄位</Divider>
    <Space wrap>
      {table.main_fields.map((field: string, index: number) => (
        <Tag key={index} color="cyan">
          <FieldTimeOutlined style={{ marginRight: 4 }} />
          {field}
        </Tag>
      ))}
    </Space>

    <Divider titlePlacement="left">API 端點</Divider>
    <Space vertical style={{ width: '100%' }}>
      {table.api_endpoints.map((api: string, index: number) => {
        const [method, path] = api.split(' ');
        return (
          <Card key={index} size="small">
            <Space>
              <Tag color={method === 'GET' ? 'blue' : method === 'POST' ? 'green' : method === 'PUT' ? 'orange' : 'red'}>
                {method}
              </Tag>
              <Text code>{path}</Text>
            </Space>
          </Card>
        );
      })}
    </Space>

    <Divider titlePlacement="left">關聯前端頁面</Divider>
    <Space wrap>
      {table.frontend_pages.map((page: string, index: number) => (
        <Tag key={index} color="blue">
          <FileTextOutlined style={{ marginRight: 4 }} />
          {page}
        </Tag>
      ))}
    </Space>
  </div>
);
