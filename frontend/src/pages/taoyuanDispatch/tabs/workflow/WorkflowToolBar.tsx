/**
 * WorkflowToolBar - 作業歷程工具列
 *
 * 包含：
 * - 新增紀錄按鈕
 * - 查看工程總覽按鈕（可多工程）
 * - 視圖切換 Segmented（時間軸 / 公文對照 / 表格）
 *
 * @version 1.0.0
 * @date 2026-02-21
 */

import React from 'react';
import {
  Button,
  Space,
  Segmented,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  ProjectOutlined,
  LinkOutlined,
  FileTextOutlined,
  OrderedListOutlined,
  DownloadOutlined,
} from '@ant-design/icons';

type ViewMode = 'chain' | 'correspondence' | 'table';

export interface WorkflowToolBarProps {
  /** 當前視圖模式 */
  viewMode: ViewMode;
  /** 視圖模式變更回調 */
  onViewModeChange: (mode: ViewMode) => void;
  /** 是否可編輯 */
  canEdit: boolean;
  /** 新增紀錄回調 */
  onAdd: () => void;
  /** 關聯的工程列表 */
  linkedProjects?: { project_id: number; project_name?: string }[];
  /** 前往工程總覽回調 */
  onGoToProjectOverview: (projectId: number) => void;
  /** 匯出矩陣回調 */
  onExport?: () => void;
  /** 匯出中 */
  exporting?: boolean;
}

const WorkflowToolBarInner: React.FC<WorkflowToolBarProps> = ({
  viewMode,
  onViewModeChange,
  canEdit,
  onAdd,
  linkedProjects,
  onGoToProjectOverview,
  onExport,
  exporting,
}) => {
  return (
    <div
      style={{
        marginBottom: 12,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 8,
      }}
    >
      <Space wrap>
        {canEdit && (
          <Button type="primary" icon={<PlusOutlined />} onClick={onAdd}>
            新增紀錄
          </Button>
        )}
        {linkedProjects && linkedProjects.length > 0 && (
          <>
            {linkedProjects.map((proj) => (
              <Tooltip
                key={proj.project_id}
                title={`前往「${proj.project_name || '工程'}」總覽，查看本派工在整體工程中的進度`}
              >
                <Button
                  icon={<ProjectOutlined />}
                  onClick={() => onGoToProjectOverview(proj.project_id)}
                >
                  查看工程總覽
                </Button>
              </Tooltip>
            ))}
          </>
        )}
        {onExport && (
          <Tooltip title="匯出公文對照矩陣為 Excel">
            <Button
              icon={<DownloadOutlined />}
              onClick={onExport}
              loading={exporting}
            >
              匯出矩陣
            </Button>
          </Tooltip>
        )}
      </Space>

      <Segmented
        value={viewMode}
        onChange={(val) => onViewModeChange(val as ViewMode)}
        options={[
          {
            value: 'chain',
            label: '時間軸',
            icon: <LinkOutlined />,
          },
          {
            value: 'correspondence',
            label: '公文對照',
            icon: <FileTextOutlined />,
          },
          {
            value: 'table',
            label: '表格',
            icon: <OrderedListOutlined />,
          },
        ]}
      />
    </div>
  );
};

export const WorkflowToolBar = React.memo(WorkflowToolBarInner);
WorkflowToolBar.displayName = 'WorkflowToolBar';
