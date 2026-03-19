/**
 * WorkRecordStatsCard - 作業紀錄統計儀表板（共用元件）
 *
 * 統一 dispatch StatsCards 和 project 統計區塊，
 * 透過 mode prop 切換兩種顯示模式。
 *
 * @version 1.1.0 - 消除 type assertions，改用 early narrowing
 * @date 2026-03-05
 */

import React, { useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  LinkOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  SendOutlined,
  OrderedListOutlined,
  RocketOutlined,
} from '@ant-design/icons';

import { getWorkTypeColor, STATUS_CONFIG } from '../kanban/kanbanConstants';
import type { WorkTypeStageInfo } from './useProjectWorkData';

const { Text } = Typography;

// ============================================================================
// Types
// ============================================================================

/** 共用統計欄位 */
interface BaseStats {
  total: number;
  completed: number;
  inProgress: number;
  incomingDocs: number;
  outgoingDocs: number;
  currentStage: string;
}

/** 派工單模式附加欄位 */
interface DispatchModeProps {
  mode: 'dispatch';
  onHold?: number;
  linkedDocCount?: number;
  unassignedDocCount?: number;
  workType?: string;
}

/** 專案總覽模式附加欄位 */
interface ProjectModeProps {
  mode: 'project';
  dispatchCount?: number;
  workTypeStages?: WorkTypeStageInfo[];
}

export type WorkRecordStatsCardProps = {
  stats: BaseStats;
} & (DispatchModeProps | ProjectModeProps);

// ============================================================================
// 主元件
// ============================================================================

const WorkRecordStatsCardInner: React.FC<WorkRecordStatsCardProps> = (props) => {
  const { stats, mode } = props;

  // Early narrowing：提取模式專屬欄位，避免重複 type assertion
  const onHold = mode === 'dispatch' ? props.onHold : undefined;
  const linkedDocCount = mode === 'dispatch' ? props.linkedDocCount : undefined;
  const unassignedDocCount = mode === 'dispatch' ? props.unassignedDocCount : undefined;
  const workTypeStr = mode === 'dispatch' ? props.workType : undefined;
  const dispatchCount = mode === 'project' ? props.dispatchCount : undefined;
  const workTypeStages = mode === 'project' ? props.workTypeStages : undefined;

  // 計算整體狀態
  const statusKey = useMemo(() => {
    if (stats.currentStage === '全部完成') return 'completed' as const;
    if (stats.inProgress > 0) return 'in_progress' as const;
    return 'pending' as const;
  }, [stats.currentStage, stats.inProgress]);

  // 解析作業類別列表（dispatch 模式）
  const workTypes = useMemo(() => {
    if (!workTypeStr) return [];
    return workTypeStr.split(',').map((t) => t.trim()).filter(Boolean);
  }, [workTypeStr]);

  return (
    <Card size="small" style={{ marginBottom: 12 }}>
      <Row gutter={[16, 8]} align="middle">

        {/* 派工數（僅 project 模式） */}
        {mode === 'project' && dispatchCount !== undefined && (
          <Col xs={12} sm={6} md={3}>
            <Statistic
              title="派工數"
              value={dispatchCount}
              prefix={<OrderedListOutlined />}
            />
          </Col>
        )}

        {/* 作業紀錄統計 */}
        <Col xs={24} sm={12} md={6}>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              作業紀錄
            </Text>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <Text strong style={{ fontSize: 20 }}>{stats.total}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>筆</Text>
              <Tag color="success" style={{ margin: 0 }}>
                <CheckCircleOutlined /> {stats.completed} 完成
              </Tag>
              {stats.inProgress > 0 && (
                <Tag color="processing" style={{ margin: 0 }}>
                  <ClockCircleOutlined /> {stats.inProgress} 進行中
                </Tag>
              )}
              {onHold !== undefined && onHold > 0 && (
                <Tag color="warning" style={{ margin: 0 }}>
                  {onHold} 暫緩
                </Tag>
              )}
            </div>
          </div>
        </Col>

        {/* 公文統計 */}
        <Col xs={24} sm={12} md={mode === 'dispatch' ? 6 : 3}>
          <div>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              關聯公文
            </Text>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              {linkedDocCount !== undefined && (
                <Statistic
                  value={linkedDocCount}
                  prefix={<LinkOutlined />}
                  styles={{ content: { fontSize: 20 } }}
                />
              )}
              <Tooltip title="不重複來文數">
                <Tag icon={<FileTextOutlined />} style={{ margin: 0 }}>
                  來文 {stats.incomingDocs}
                </Tag>
              </Tooltip>
              <Tooltip title="不重複發文數">
                <Tag icon={<SendOutlined />} style={{ margin: 0 }}>
                  發文 {stats.outgoingDocs}
                </Tag>
              </Tooltip>
              {unassignedDocCount !== undefined && unassignedDocCount > 0 && (
                <Tooltip title="已關聯但未指派到作業紀錄">
                  <Tag color="warning" icon={<ExclamationCircleOutlined />} style={{ margin: 0 }}>
                    未指派 {unassignedDocCount}
                  </Tag>
                </Tooltip>
              )}
            </div>
          </div>
        </Col>

        {/* 作業進度 */}
        <Col xs={24} sm={24} md={12}>
          <div>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>
              <RocketOutlined style={{ marginRight: 4 }} />
              作業進度
            </Text>

            {workTypeStages && workTypeStages.length > 0 ? (
              // 專案模式：按作業類別分組顯示
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {workTypeStages.map((wts) => {
                  const statusText = STATUS_CONFIG[wts.status]?.label || wts.status;
                  const detail = wts.total > 1
                    ? `${statusText}（${wts.completed}/${wts.total} 件結案）`
                    : statusText;
                  return (
                    <div key={wts.workType} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Tag
                        color={getWorkTypeColor(wts.workType)}
                        style={{ margin: 0, fontSize: 12, lineHeight: '20px' }}
                      >
                        {wts.workType.replace(/^\d+\./, '')}
                      </Tag>
                      <Text style={{ fontSize: 13 }}>{wts.stage}</Text>
                      <Tag
                        color={STATUS_CONFIG[wts.status]?.color || '#d9d9d9'}
                        style={{ margin: 0, fontSize: 11, lineHeight: '18px', border: 'none' }}
                      >
                        {detail}
                      </Tag>
                    </div>
                  );
                })}
              </div>
            ) : workTypes.length > 0 ? (
              // 派工單模式：單一派工單的作業類別
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {workTypes.map((wt) => (
                  <div key={wt} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Tag
                      color={getWorkTypeColor(wt)}
                      style={{ margin: 0, fontSize: 12, lineHeight: '20px' }}
                    >
                      {wt.replace(/^\d+\./, '')}
                    </Tag>
                    <Text style={{ fontSize: 13 }}>{stats.currentStage}</Text>
                    <Tag
                      color={STATUS_CONFIG[statusKey]?.color || '#d9d9d9'}
                      style={{ margin: 0, fontSize: 11, lineHeight: '18px', border: 'none' }}
                    >
                      {STATUS_CONFIG[statusKey]?.label || stats.currentStage}
                    </Tag>
                  </div>
                ))}
              </div>
            ) : (
              <Text style={{ fontSize: 14 }}>{stats.currentStage}</Text>
            )}
          </div>
        </Col>
      </Row>
    </Card>
  );
};

export const WorkRecordStatsCard = React.memo(WorkRecordStatsCardInner);
WorkRecordStatsCard.displayName = 'WorkRecordStatsCard';
