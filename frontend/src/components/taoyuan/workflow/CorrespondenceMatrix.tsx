/**
 * CorrespondenceMatrix - 公文對照表視圖
 *
 * 對應 Excel 矩陣結構：以派工單為主軸，左右雙欄顯示機關來文/公司發文。
 * 批次色帶標示結案分期。
 *
 * 雙欄元件已抽取至 CorrespondenceBody.tsx 共用。
 *
 * @version 1.1.0 - 抽取 CorrespondenceBody 為獨立元件
 * @date 2026-02-13
 */

import React, { useEffect, useMemo, useRef } from 'react';
import {
  Collapse,
  Tag,
  Typography,
  Empty,
  Badge,
  Tooltip,
  Button,
} from 'antd';
import {
  FileTextOutlined,
  SendOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import type { WorkRecord } from '../../../types/taoyuan';
import type { DispatchCorrespondenceGroup } from './useProjectWorkData';
import {
  getBatchColor,
  statusLabel,
  statusColor,
} from './useProjectWorkData';
import { CorrespondenceBody } from './CorrespondenceBody';

const { Text } = Typography;

// ============================================================================
// Props
// ============================================================================

interface CorrespondenceMatrixProps {
  groups: DispatchCorrespondenceGroup[];
  highlightDispatchId?: number;
  onDispatchClick?: (dispatchId: number) => void;
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  canEdit?: boolean;
}

// ============================================================================
// 主元件
// ============================================================================

const CorrespondenceMatrixInner: React.FC<CorrespondenceMatrixProps> = ({
  groups,
  highlightDispatchId,
  onDispatchClick,
  onDocClick,
  onEditRecord,
  canEdit,
}) => {
  const panelRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // 展開鍵值：預設全展開有紀錄的面板，或高亮指定面板
  const defaultKeys = useMemo(
    () =>
      groups
        .filter((g) => g.allRecords.length > 0)
        .map((g) => String(g.dispatch.id)),
    [groups],
  );

  // 高亮時自動滾動到目標面板
  useEffect(() => {
    if (!highlightDispatchId) return;
    const timer = setTimeout(() => {
      const el = panelRefs.current.get(highlightDispatchId);
      el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 300);
    return () => clearTimeout(timer);
  }, [highlightDispatchId]);

  if (groups.length === 0) {
    return (
      <Empty
        description="尚未關聯任何派工單"
        style={{ padding: '60px 0' }}
      />
    );
  }

  const items = groups.map((group) => {
    const batchStyle = getBatchColor(group.batchNo);
    const isHighlighted = highlightDispatchId === group.dispatch.id;
    const title =
      group.dispatch.sub_case_name || group.dispatch.dispatch_no || `派工 #${group.dispatch.id}`;

    return {
      key: String(group.dispatch.id),
      label: (
        <div
          ref={(el) => {
            if (el) panelRefs.current.set(group.dispatch.id, el);
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexWrap: 'wrap',
          }}
        >
          {/* 項次 */}
          <Badge
            count={group.index}
            style={{
              backgroundColor: isHighlighted ? '#1677ff' : '#8c8c8c',
              fontSize: 11,
            }}
          />

          {/* 分案名稱 */}
          <Text
            strong
            style={{ fontSize: 13, maxWidth: 300 }}
            ellipsis={{ tooltip: title }}
          >
            {title}
          </Text>

          {/* 批次標籤 */}
          {group.batchNo !== null && (
            <Tag color={batchStyle.tag} style={{ fontSize: 11 }}>
              {group.batchLabel}
            </Tag>
          )}

          {/* 狀態 */}
          <Tag
            color={statusColor(group.computedStatus)}
            style={{ fontSize: 11 }}
          >
            {statusLabel(group.computedStatus)}
          </Tag>

          {/* 公文統計 */}
          <Text type="secondary" style={{ fontSize: 11 }}>
            <FileTextOutlined /> {group.incomingDocs.length} 來文
            {' / '}
            <SendOutlined /> {group.outgoingDocs.length} 發文
          </Text>

          {/* 關鍵日期 */}
          {group.keyDates.length > 0 && (
            <span>
              {group.keyDates.map((kd, i) => (
                <Tag
                  key={i}
                  color="purple"
                  style={{ fontSize: 10, lineHeight: '16px' }}
                >
                  {kd.label} {dayjs(kd.date).format('YYYY.MM.DD')}
                </Tag>
              ))}
            </span>
          )}

          {/* 派工單連結 */}
          {onDispatchClick && (
            <Tooltip title="前往派工單詳情">
              <Button
                type="text"
                size="small"
                icon={<LinkOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  onDispatchClick(group.dispatch.id);
                }}
              />
            </Tooltip>
          )}
        </div>
      ),
      children: (
        <CorrespondenceBody
          data={group}
          onDocClick={onDocClick}
          onEditRecord={onEditRecord}
          canEdit={canEdit}
        />
      ),
      style: {
        borderLeft: `4px solid ${batchStyle.border}`,
        marginBottom: 8,
        borderRadius: 6,
        ...(isHighlighted
          ? { background: '#e6f4ff', boxShadow: '0 0 0 2px #1677ff33' }
          : {}),
      },
    };
  });

  return (
    <Collapse
      defaultActiveKey={
        highlightDispatchId
          ? [String(highlightDispatchId)]
          : defaultKeys
      }
      items={items}
    />
  );
};

export const CorrespondenceMatrix = React.memo(CorrespondenceMatrixInner);
