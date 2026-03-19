import React from 'react';
import { Card, Select, Button, Space, Tag, Typography } from 'antd';
import { ForkOutlined } from '@ant-design/icons';
import type { KGShortestPathResponse } from '../../types/ai';
import { getMergedNodeConfig } from '../../config/graphNodeConfig';

const { Text } = Typography;

interface ShortestPathFinderProps {
  pathSourceId: number | null;
  pathTargetId: number | null;
  pathResult: KGShortestPathResponse | null;
  entityOptions: Array<{ label: string; value: number }>;
  onSourceChange: (val: number | null) => void;
  onTargetChange: (val: number | null) => void;
  onSearch: (query: string) => void;
  onFindPath: () => void;
  isLoading: boolean;
}

const ShortestPathFinder: React.FC<ShortestPathFinderProps> = ({
  pathSourceId,
  pathTargetId,
  pathResult,
  entityOptions,
  onSourceChange,
  onTargetChange,
  onSearch,
  onFindPath,
  isLoading,
}) => {
  return (
    <Card
      size="small"
      title={
        <span style={{ fontSize: 13 }}>
          <ForkOutlined /> 最短路徑
        </span>
      }
      styles={{ body: { padding: '8px 12px' } }}
    >
      <Space vertical style={{ width: '100%' }} size={6}>
        <Select
          showSearch
          allowClear
          placeholder="起點實體"
          filterOption={false}
          onSearch={onSearch}
          onChange={(val) => onSourceChange(val ?? null)}
          options={entityOptions}
          size="small"
          style={{ width: '100%' }}
          notFoundContent={null}
        />
        <Select
          showSearch
          allowClear
          placeholder="終點實體"
          filterOption={false}
          onSearch={onSearch}
          onChange={(val) => onTargetChange(val ?? null)}
          options={entityOptions}
          size="small"
          style={{ width: '100%' }}
          notFoundContent={null}
        />
        <Button
          block
          size="small"
          type="primary"
          icon={<ForkOutlined />}
          loading={isLoading}
          disabled={!pathSourceId || !pathTargetId || pathSourceId === pathTargetId}
          onClick={onFindPath}
        >
          查找路徑
        </Button>
        {pathResult?.found && (
          <div style={{ fontSize: 12, padding: '4px 0' }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              路徑深度: {pathResult.depth} 跳
            </Text>
            <div style={{ marginTop: 4 }}>
              {pathResult.path.map((node, idx) => (
                <span key={node.id}>
                  <Tag color={getMergedNodeConfig(node.type).color} style={{ fontSize: 11, marginBottom: 2 }}>
                    {node.name}
                  </Tag>
                  {idx < pathResult.path.length - 1 && (
                    <span style={{ fontSize: 10, color: '#999', margin: '0 2px' }}>
                      —{pathResult.relations[idx] || ''}→{' '}
                    </span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}
      </Space>
    </Card>
  );
};

export default ShortestPathFinder;
