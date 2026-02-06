/**
 * 匯入預覽卡片
 */

import React from 'react';
import {
  Alert,
  Button,
  Space,
  Typography,
  Divider,
  List,
  Tag,
  Table,
  Tooltip,
  Card,
} from 'antd';
import {
  FileExcelOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import type { PreviewResult, PreviewRow } from './types';

const { Text, Title } = Typography;

interface ImportPreviewCardProps {
  previewResult: PreviewResult;
  importing: boolean;
  onReset: () => void;
  onImport: () => void;
}

const previewColumns = [
  {
    title: '列',
    dataIndex: 'row',
    key: 'row',
    width: 50,
  },
  {
    title: '操作',
    dataIndex: 'action',
    key: 'action',
    width: 70,
    render: (action: string) => (
      <Tag color={action === 'insert' ? 'green' : 'blue'}>
        {action === 'insert' ? '新增' : '更新'}
      </Tag>
    ),
  },
  {
    title: '公文字號',
    key: 'doc_number',
    width: 180,
    render: (_: unknown, record: PreviewRow) => record.data['公文字號'] || '-',
  },
  {
    title: '主旨',
    key: 'subject',
    ellipsis: true,
    render: (_: unknown, record: PreviewRow) => record.data['主旨'] || '-',
  },
  {
    title: '狀態',
    key: 'status',
    width: 100,
    render: (_: unknown, record: PreviewRow) => {
      if (record.issues.length > 0) {
        return (
          <Tooltip title={record.issues.join('; ')}>
            <Tag icon={<WarningOutlined />} color="warning">
              警告
            </Tag>
          </Tooltip>
        );
      }
      return (
        <Tag icon={<CheckCircleOutlined />} color="success">
          正常
        </Tag>
      );
    },
  },
];

const ImportPreviewCardInner: React.FC<ImportPreviewCardProps> = ({
  previewResult,
  importing,
  onReset,
  onImport,
}) => {
  const { success, filename, total_rows, preview_rows, validation, errors } = previewResult;

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Alert
          type={success ? 'info' : 'error'}
          message={
            <Space>
              <FileExcelOutlined />
              <Text strong>{filename}</Text>
              <Text type="secondary">({total_rows} 筆資料)</Text>
            </Space>
          }
          description={
            errors.length > 0 ? (
              <List
                size="small"
                dataSource={errors}
                renderItem={(item) => (
                  <List.Item>
                    <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                    {item}
                  </List.Item>
                )}
              />
            ) : null
          }
        />

        <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center', padding: '16px 0' }}>
          <div>
            <Text type="secondary">預計新增</Text>
            <Title level={4} style={{ color: '#52c41a', margin: 0 }}>{validation.will_insert}</Title>
          </div>
          <div>
            <Text type="secondary">預計更新</Text>
            <Title level={4} style={{ color: '#1890ff', margin: 0 }}>{validation.will_update}</Title>
          </div>
          {validation.duplicate_doc_numbers.length > 0 && (
            <div>
              <Text type="secondary">檔案內重複</Text>
              <Title level={4} style={{ color: '#faad14', margin: 0 }}>{validation.duplicate_doc_numbers.length}</Title>
            </div>
          )}
          {validation.existing_in_db && validation.existing_in_db.length > 0 && (
            <div>
              <Tooltip title="這些公文字號已存在於資料庫中，新增時會被跳過">
                <Text type="secondary">資料庫已存在</Text>
                <Title level={4} style={{ color: '#ff4d4f', margin: 0 }}>{validation.existing_in_db.length}</Title>
              </Tooltip>
            </div>
          )}
        </div>

        {preview_rows.length > 0 && (
          <>
            <Divider orientation="left">資料預覽（前 {preview_rows.length} 筆）</Divider>
            <Table
              dataSource={preview_rows}
              columns={previewColumns}
              rowKey="row"
              size="small"
              pagination={false}
              scroll={{ y: 200 }}
            />
          </>
        )}

        <Divider />
        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
          <Button onClick={onReset}>取消</Button>
          <Button
            type="primary"
            icon={<CloudUploadOutlined />}
            onClick={onImport}
            loading={importing}
            disabled={!success || errors.length > 0}
          >
            確認匯入
          </Button>
        </Space>
      </Space>
    </Card>
  );
};

export const ImportPreviewCard = React.memo(ImportPreviewCardInner);
