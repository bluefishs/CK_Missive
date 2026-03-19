import React from 'react';
import { Card, Tag, Typography } from 'antd';
import { CrownOutlined } from '@ant-design/icons';
import type { KGEntityItem } from '../../types/ai';
import { getMergedNodeConfig } from '../../config/graphNodeConfig';

const { Text } = Typography;

interface TopEntitiesRankingProps {
  entities: KGEntityItem[];
}

const TopEntitiesRanking: React.FC<TopEntitiesRankingProps> = ({ entities }) => {
  return (
    <Card
      size="small"
      title={
        <span style={{ fontSize: 13 }}>
          <CrownOutlined /> 高頻實體排行
        </span>
      }
      styles={{ body: { padding: '4px 12px' } }}
    >
      {entities.map((entity, idx) => {
        const cfg = getMergedNodeConfig(entity.entity_type);
        return (
          <div
            key={entity.id}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '3px 0',
              fontSize: 12,
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Text type="secondary" style={{ fontSize: 11, width: 16 }}>
                {idx + 1}.
              </Text>
              <span
                style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: cfg.color, display: 'inline-block',
                }}
              />
              <span style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {entity.canonical_name}
              </span>
            </span>
            <Tag style={{ fontSize: 10, margin: 0, lineHeight: '16px' }}>
              {entity.mention_count}
            </Tag>
          </div>
        );
      })}
    </Card>
  );
};

export default TopEntitiesRanking;
