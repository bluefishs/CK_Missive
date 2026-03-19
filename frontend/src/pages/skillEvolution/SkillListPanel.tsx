/**
 * Skill List Panel - Left sidebar with category-grouped skill list
 *
 * @version 1.0.0
 */

import React, { useMemo } from 'react';
import { Collapse, Tag, Typography, Tooltip, Flex } from 'antd';
import { StarFilled, StarOutlined } from '@ant-design/icons';
import type { SkillNode, CategoryInfo } from './types';

const { Text } = Typography;

interface SkillListPanelProps {
  nodes: SkillNode[];
  categories: Record<string, CategoryInfo>;
  onSkillClick?: (nodeId: number) => void;
}

/** Render maturity stars */
const MaturityStars: React.FC<{ level: number }> = ({ level }) => (
  <span style={{ fontSize: 10 }}>
    {Array.from({ length: 5 }, (_, i) =>
      i < level
        ? <StarFilled key={i} style={{ color: '#fadb14', marginRight: 1 }} />
        : <StarOutlined key={i} style={{ color: '#555', marginRight: 1 }} />
    )}
  </span>
);

const sourceTagColor: Record<string, string> = {
  auto: 'green',
  manual: 'blue',
  merged: 'gold',
  planned: 'default',
};

export const SkillListPanel: React.FC<SkillListPanelProps> = ({
  nodes,
  categories,
  onSkillClick,
}) => {
  const grouped = useMemo(() => {
    const map = new Map<string, SkillNode[]>();
    for (const node of nodes) {
      const list = map.get(node.category) || [];
      list.push(node);
      map.set(node.category, list);
    }
    return map;
  }, [nodes]);

  const collapseItems = useMemo(() => {
    return Array.from(grouped.entries()).map(([cat, skills]) => {
      const info = categories[cat];
      const color = info?.color || '#888';
      return {
        key: cat,
        label: (
          <Flex align="center" gap={6}>
            <span style={{
              display: 'inline-block', width: 10, height: 10,
              borderRadius: '50%', background: color, flexShrink: 0,
            }} />
            <Text strong style={{ fontSize: 13 }}>
              {info?.label || cat}
            </Text>
            <Tag style={{ marginLeft: 'auto', fontSize: 11 }}>{skills.length}</Tag>
          </Flex>
        ),
        children: (
          <Flex vertical gap={4}>
            {skills.map(skill => (
              <Tooltip key={skill.id} title={skill.description} placement="right">
                <Flex
                  align="center"
                  gap={6}
                  style={{
                    padding: '4px 8px',
                    borderRadius: 4,
                    cursor: 'pointer',
                    transition: 'background 0.2s',
                  }}
                  className="skill-list-item"
                  onClick={() => onSkillClick?.(skill.id)}
                >
                  <Text
                    style={{
                      fontSize: 12, flex: 1, minWidth: 0,
                      opacity: skill.source === 'planned' ? 0.5 : 1,
                    }}
                    ellipsis
                  >
                    {skill.name}
                  </Text>
                  <Tag
                    color={sourceTagColor[skill.source] || 'default'}
                    style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}
                  >
                    {skill.version}
                  </Tag>
                  <MaturityStars level={skill.maturity} />
                </Flex>
              </Tooltip>
            ))}
          </Flex>
        ),
      };
    });
  }, [grouped, categories, onSkillClick]);

  return (
    <div style={{
      width: 280, height: '100%', overflowY: 'auto',
      borderRight: '1px solid #303050',
      background: '#12122a', padding: '8px 0',
    }}>
      <Text strong style={{ color: '#ccc', fontSize: 13, padding: '4px 12px', display: 'block' }}>
        技能列表
      </Text>
      <Collapse
        items={collapseItems}
        defaultActiveKey={Array.from(grouped.keys()).slice(0, 3)}
        size="small"
        ghost
        style={{ background: 'transparent' }}
      />
      <style>{`
        .skill-list-item:hover { background: rgba(255,255,255,0.06) !important; }
        .ant-collapse-ghost > .ant-collapse-item > .ant-collapse-header { color: #aaa !important; padding: 6px 12px !important; }
        .ant-collapse-ghost > .ant-collapse-item > .ant-collapse-content > .ant-collapse-content-box { padding: 0 8px 8px !important; }
      `}</style>
    </div>
  );
};
