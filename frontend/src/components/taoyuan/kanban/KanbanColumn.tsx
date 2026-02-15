/**
 * KanbanColumn - 看板作業類別欄位
 *
 * 一個作業類別 = 一個欄位，包含彩色標題、可滾動的卡片區域、底部新增按鈕。
 *
 * @version 1.1.0 - 使用 Antd theme token 取代硬編碼色彩
 * @date 2026-02-13
 */

import React, { useCallback } from 'react';
import { Badge, Button, Typography, theme } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

import type { KanbanColumnData } from './kanbanConstants';
import { KanbanCard } from './KanbanCard';

const { Text } = Typography;

interface KanbanColumnProps {
  data: KanbanColumnData;
  onCardClick: (dispatchId: number) => void;
  onAddNew?: (workType: string) => void;
  canEdit?: boolean;
}

const KanbanColumnInner: React.FC<KanbanColumnProps> = ({ data, onCardClick, onAddNew, canEdit }) => {
  const { workType, color, cards } = data;
  const { token } = theme.useToken();

  const handleAdd = useCallback(() => {
    onAddNew?.(workType);
  }, [onAddNew, workType]);

  return (
    <div
      style={{
        width: 280,
        minWidth: 280,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 10,
        background: token.colorBgLayout,
        border: `1px solid ${token.colorBorderSecondary}`,
        overflow: 'hidden',
      }}
    >
      {/* 彩色標題區 */}
      <div
        style={{
          padding: '10px 12px',
          background: `linear-gradient(135deg, ${color}22, ${color}11)`,
          borderBottom: `2px solid ${color}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Text strong style={{ fontSize: 13, color: color }}>
          {workType}
        </Text>
        <Badge
          count={cards.length}
          showZero
          style={{
            backgroundColor: cards.length > 0 ? color : token.colorTextDisabled,
            fontSize: 11,
          }}
        />
      </div>

      {/* 可滾動卡片區 */}
      <div
        style={{
          flex: 1,
          padding: '8px 8px 4px',
          overflowY: 'auto',
          maxHeight: 'calc(100vh - 360px)',
          minHeight: 100,
        }}
      >
        {cards.map((card) => (
          <KanbanCard key={card.dispatch.id} data={card} onClick={onCardClick} />
        ))}
      </div>

      {/* 底部新增按鈕 */}
      {canEdit && onAddNew && (
        <div style={{ padding: '4px 8px 8px' }}>
          <Button
            type="text"
            icon={<PlusOutlined />}
            onClick={handleAdd}
            block
            style={{
              color: token.colorTextSecondary,
              borderRadius: 6,
              height: 32,
              fontSize: 12,
            }}
          >
            新增派工
          </Button>
        </div>
      )}
    </div>
  );
};

export const KanbanColumn = React.memo(KanbanColumnInner);
