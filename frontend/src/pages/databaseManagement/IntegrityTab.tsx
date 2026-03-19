import React from 'react';
import { Space, Alert, Button, Card, Tag, Typography } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import type { IntegrityResult } from '../../types/api';

const { Text } = Typography;

interface IntegrityTabProps {
  integrityResult: IntegrityResult | null;
  loading: boolean;
  onCheckIntegrity: () => void;
}

export const IntegrityTab: React.FC<IntegrityTabProps> = ({
  integrityResult,
  loading,
  onCheckIntegrity,
}) => {
  return (
    <Space vertical style={{ width: '100%' }}>
      <Alert
        title="數據完整性檢查"
        description="檢查資料庫表格完整性、外鍵約束和數據一致性"
        type="info"
        showIcon
      />

      <Button
        type="primary"
        icon={<PlayCircleOutlined />}
        onClick={onCheckIntegrity}
        loading={loading}
        size="large"
      >
        開始完整性檢查
      </Button>

      {integrityResult && (
        <Card title="檢查結果">
          <Space vertical style={{ width: '100%' }}>
            <div>
              <Text strong>檢查狀態：</Text>
              <Tag color={integrityResult.totalIssues === 0 ? 'green' : 'orange'}>
                {integrityResult.totalIssues === 0 ? '通過' : `發現 ${integrityResult.totalIssues} 個問題`}
              </Tag>
            </div>

            <div>
              <Text strong>檢查時間：</Text>
              <Text type="secondary">{new Date(integrityResult.checkTime).toLocaleString()}</Text>
            </div>

            {integrityResult.totalIssues === 0 ? (
              <Alert title="數據完整性檢查通過，未發現問題" type="success" showIcon />
            ) : (
              <Alert title="發現數據問題，請檢查以下項目" type="warning" showIcon />
            )}
          </Space>
        </Card>
      )}
    </Space>
  );
};
