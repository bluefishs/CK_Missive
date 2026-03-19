import React from 'react';
import { Card, Typography } from 'antd';
import { NodeIndexOutlined } from '@ant-design/icons';
import { getAllMergedConfigs } from '../../config/graphNodeConfig';

const { Text } = Typography;

interface EntityTypeDistributionProps {
  distribution: Record<string, number>;
}

const EntityTypeDistribution: React.FC<EntityTypeDistributionProps> = ({ distribution }) => {
  const configs = getAllMergedConfigs();

  return (
    <Card
      size="small"
      title={
        <span style={{ fontSize: 13 }}>
          <NodeIndexOutlined /> 實體類型分佈
        </span>
      }
      styles={{ body: { padding: '8px 12px' } }}
    >
      {Object.entries(distribution).map(([type, count]) => {
        const cfg = configs[type];
        const label = cfg?.label || type;
        const color = cfg?.color || '#999';
        return (
          <div
            key={type}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '3px 0',
              fontSize: 12,
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: color,
                  display: 'inline-block',
                }}
              />
              {label}
            </span>
            <Text type="secondary" style={{ fontSize: 12 }}>{count}</Text>
          </div>
        );
      })}
    </Card>
  );
};

export default EntityTypeDistribution;
