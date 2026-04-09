/**
 * 今日晨報卡片
 *
 * 預覽與推送每日晨報。
 */
import React, { useState } from 'react';
import { Card, Typography, Button, Space } from 'antd';
import { FileTextOutlined, SendOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { AI_ENDPOINTS } from '../../api/endpoints';

const { Text } = Typography;

export const MorningReportCard: React.FC = () => {
  const [report, setReport] = useState<string | null>(null);

  const loadReport = useMutation({
    mutationFn: () =>
      apiClient.post<{ success: boolean; summary: string }>(
        AI_ENDPOINTS.MORNING_REPORT_PREVIEW, {}
      ),
    onSuccess: (d) => setReport(d.summary),
  });

  const pushReport = useMutation({
    mutationFn: () =>
      apiClient.post<{ success: boolean; pushed_to: string[]; message: string }>(
        AI_ENDPOINTS.MORNING_REPORT_PUSH, {}
      ),
    onSuccess: (d) => {
      setReport((prev) => prev ? `${prev}\n\n--- ${d.message}` : d.message);
    },
  });

  return (
    <Card
      size="small"
      title={<span style={{ fontSize: 13 }}><FileTextOutlined /> 今日晨報</span>}
      style={{ marginTop: 12 }}
      extra={
        <Space size={4}>
          <Button size="small" type="text" icon={<FileTextOutlined />}
            onClick={() => loadReport.mutate()} loading={loadReport.isPending}>
            預覽
          </Button>
          <Button size="small" type="text" icon={<SendOutlined />}
            onClick={() => pushReport.mutate()} loading={pushReport.isPending} disabled={!report}>
            推送
          </Button>
        </Space>
      }
    >
      <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>
        {report || '點擊「預覽」查看今日晨報'}
      </Text>
    </Card>
  );
};
