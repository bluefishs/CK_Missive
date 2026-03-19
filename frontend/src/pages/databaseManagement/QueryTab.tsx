import React from 'react';
import { Space, Alert, Button, Table, Card, Typography, Input } from 'antd';
import { PlayCircleOutlined, CopyOutlined } from '@ant-design/icons';
import type { QueryResult } from '../../types/api';

const { Text } = Typography;
const { TextArea } = Input;

interface QueryTabProps {
  customQuery: string;
  onQueryChange: (query: string) => void;
  queryResult: QueryResult | null;
  loading: boolean;
  onExecuteQuery: () => void;
}

export const QueryTab: React.FC<QueryTabProps> = ({
  customQuery,
  onQueryChange,
  queryResult,
  loading,
  onExecuteQuery,
}) => {
  return (
    <Space vertical style={{ width: '100%' }}>
      <Alert
        title="SQL 查詢工具"
        description="僅支援 SELECT 查詢，禁止 DROP、DELETE、INSERT、UPDATE 等危險操作"
        type="info"
        showIcon
      />

      <div>
        <Space style={{ marginBottom: 8 }}>
          <Text strong>快速查詢模板：</Text>
          <Button
            size="small"
            onClick={() => onQueryChange('SELECT * FROM documents ORDER BY created_at DESC LIMIT 10;')}
          >
            最新文檔
          </Button>
          <Button
            size="small"
            onClick={() => onQueryChange('SELECT COUNT(*) as total FROM documents;')}
          >
            統計記錄
          </Button>
          <Button
            size="small"
            onClick={() => onQueryChange('SELECT category, COUNT(*) as count FROM documents GROUP BY category ORDER BY count DESC;')}
          >
            按類型統計
          </Button>
          <Button
            size="small"
            onClick={() => onQueryChange('SELECT status, COUNT(*) as count FROM documents GROUP BY status;')}
          >
            按狀態統計
          </Button>
          <Button
            size="small"
            onClick={() => onQueryChange('SELECT DATE(doc_date) as date, COUNT(*) as count FROM documents GROUP BY DATE(doc_date) ORDER BY date DESC LIMIT 30;')}
          >
            日期分佈
          </Button>
        </Space>

        <TextArea
          value={customQuery}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="輸入您的 SELECT 查詢語句..."
          rows={6}
          style={{ fontFamily: 'monospace' }}
        />

        <Space style={{ marginTop: 8 }}>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={onExecuteQuery}
            loading={loading}
          >
            執行查詢
          </Button>
          <Button
            icon={<CopyOutlined />}
            onClick={() => {
              navigator.clipboard.writeText(customQuery);
            }}
          >
            複製查詢
          </Button>
        </Space>
      </div>

      {queryResult && (
        <Card title={`查詢結果 (${queryResult.totalRows} 條記錄，耗時 ${queryResult.executionTime}ms)`}>
          <Table
            columns={queryResult.columns.map((col: string) => ({
              title: col,
              dataIndex: col,
              key: col,
              width: 150,
              ellipsis: true
            }))}
            dataSource={queryResult.rows.map((row: unknown[], index: number) => {
              const obj: Record<string, unknown> = { key: index };
              queryResult.columns.forEach((col: string, colIndex: number) => {
                obj[col] = row[colIndex];
              });
              return obj;
            })}
            size="small"
            pagination={{ pageSize: 20 }}
            scroll={{ x: 'max-content' }}
          />
        </Card>
      )}
    </Space>
  );
};
