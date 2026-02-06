/**
 * 匯入結果卡片
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
  Card,
  Result,
} from 'antd';
import { CloseCircleOutlined } from '@ant-design/icons';
import type { ImportResult } from './types';

const { Text, Title } = Typography;

interface ImportResultCardProps {
  importResult: ImportResult;
  onClose: () => void;
  onReset: () => void;
}

const ImportResultCardInner: React.FC<ImportResultCardProps> = ({
  importResult,
  onClose,
  onReset,
}) => {
  const { success, filename, total_rows, inserted, updated, skipped, errors, details } = importResult;

  return (
    <Card style={{ marginTop: 16 }}>
      <Result
        status={success ? 'success' : 'warning'}
        title={success ? '匯入完成' : '匯入完成（有警告）'}
        subTitle={`檔案: ${filename}`}
        extra={[
          <Button key="close" onClick={onClose}>關閉</Button>,
          <Button key="reset" type="primary" onClick={onReset}>繼續匯入</Button>,
        ]}
      />

      <Divider />

      <Space direction="vertical" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
          <div>
            <Text type="secondary">總筆數</Text>
            <Title level={3}>{total_rows}</Title>
          </div>
          <div>
            <Text type="success">新增</Text>
            <Title level={3} style={{ color: '#52c41a' }}>{inserted}</Title>
          </div>
          <div>
            <Text type="warning">更新</Text>
            <Title level={3} style={{ color: '#faad14' }}>{updated}</Title>
          </div>
          <div>
            <Text type="secondary">跳過</Text>
            <Title level={3} style={{ color: '#8c8c8c' }}>{skipped}</Title>
          </div>
        </div>

        {errors && errors.length > 0 && (
          <>
            <Divider />
            <Alert
              type="error"
              message={`${errors.length} 個錯誤`}
              description={
                <List
                  size="small"
                  dataSource={errors.slice(0, 10)}
                  renderItem={(item) => (
                    <List.Item>
                      <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                      {item}
                    </List.Item>
                  )}
                />
              }
            />
          </>
        )}

        {details && details.length > 0 && (
          <>
            <Divider />
            <Text strong>處理明細（前 20 筆）</Text>
            <List
              size="small"
              dataSource={details.slice(0, 20)}
              renderItem={(item) => (
                <List.Item>
                  <Space>
                    <Tag>{`第 ${item.row} 列`}</Tag>
                    <Tag color={
                      item.status === 'inserted' ? 'green' :
                      item.status === 'updated' ? 'blue' :
                      item.status === 'skipped' ? 'default' : 'red'
                    }>
                      {item.status === 'inserted' ? '新增' :
                       item.status === 'updated' ? '更新' :
                       item.status === 'skipped' ? '跳過' : '錯誤'}
                    </Tag>
                    <Text ellipsis style={{ maxWidth: 300 }}>{item.message}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </>
        )}
      </Space>
    </Card>
  );
};

export const ImportResultCard = React.memo(ImportResultCardInner);
