import React from 'react';
import { Card, Badge, Button, Space, Typography, Flex } from 'antd';
import dayjs from 'dayjs';
import type { SystemAlert } from '../../types/api';

const { Text } = Typography;

interface SystemAlertsCardProps {
  alerts: SystemAlert[];
}

const SystemAlertsCard: React.FC<SystemAlertsCardProps> = ({ alerts }) => {
  if (alerts.length === 0) return null;

  return (
    <Card title="系統通知" extra={<Badge count={alerts.length} />}>
      <Flex vertical>
        {alerts.map((alert, index) => (
          <Flex
            key={index}
            align="center"
            justify="space-between"
            style={{ padding: '12px 0', borderBottom: index < alerts.length - 1 ? '1px solid #f0f0f0' : undefined }}
          >
            <Flex align="flex-start" gap={12} style={{ flex: 1 }}>
              <Badge
                status={
                  alert.type === 'error' ? 'error' :
                  alert.type === 'warning' ? 'warning' : 'processing'
                }
              />
              <div>
                <Text strong>{alert.title}</Text>
                <Space vertical size={0}>
                  <Text>{alert.description}</Text>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {dayjs(alert.timestamp).fromNow()}
                  </Text>
                </Space>
              </div>
            </Flex>
            {alert.action && alert.actionText && (
              <Button type="link" onClick={alert.action}>
                {alert.actionText}
              </Button>
            )}
          </Flex>
        ))}
      </Flex>
    </Card>
  );
};

export default SystemAlertsCard;
