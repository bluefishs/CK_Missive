/**
 * 派工詳情 - 工程關聯 Tab
 *
 * 負責顯示與管理派工單的工程關聯，包含：
 * - 新增工程關聯（Select + 搜尋）
 * - 已關聯工程列表
 * - 移除工程關聯
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import {
  Spin,
  Card,
  Row,
  Col,
  Select,
  Button,
  Empty,
  List,
  Descriptions,
  Tag,
  Space,
  Popconfirm,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { TaoyuanProject } from '../../../types/api';

/** 關聯工程型別（包含 link_id 用於刪除操作） */
export type LinkedProject = TaoyuanProject & { link_id: number; project_id: number };

/** DispatchProjectsTab Props */
export interface DispatchProjectsTabProps {
  /** 是否載入中 */
  isLoading: boolean;
  /** 是否可編輯 */
  canEdit: boolean;
  /** 已關聯的工程列表 */
  linkedProjects: LinkedProject[];
  /** 可選的工程列表（過濾已關聯） */
  filteredProjects: TaoyuanProject[];
  /** 選中的工程 ID */
  selectedProjectId: number | undefined;
  /** 設定選中的工程 ID */
  setSelectedProjectId: (id: number | undefined) => void;
  /** 建立關聯處理函數 */
  onLinkProject: () => void;
  /** 建立關聯中 */
  linkProjectLoading: boolean;
  /** 移除關聯處理函數 */
  onUnlinkProject: (linkId: number, projectId: number, proj: LinkedProject) => void;
  /** 移除關聯中 */
  unlinkProjectLoading: boolean;
  /** 導航函數 */
  navigate: (path: string) => void;
  /** 錯誤訊息函數 */
  messageError: (content: string) => void;
  /** 重新載入函數 */
  refetch: () => void;
}

/**
 * 派工詳情 - 工程關聯 Tab 元件
 */
export const DispatchProjectsTab: React.FC<DispatchProjectsTabProps> = ({
  isLoading,
  canEdit,
  linkedProjects,
  filteredProjects,
  selectedProjectId,
  setSelectedProjectId,
  onLinkProject,
  linkProjectLoading,
  onUnlinkProject,
  unlinkProjectLoading,
  navigate,
  messageError,
  refetch,
}) => {
  return (
    <Spin spinning={isLoading}>
      {/* 新增關聯區塊 */}
      {canEdit && (
        <Card size="small" style={{ marginBottom: 16 }} title="新增工程關聯">
          <Row gutter={[12, 12]} align="middle">
            <Col span={16}>
              <Select
                showSearch
                allowClear
                placeholder="搜尋工程名稱..."
                style={{ width: '100%' }}
                value={selectedProjectId}
                onChange={setSelectedProjectId}
                filterOption={(input, option) =>
                  String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                notFoundContent={
                  filteredProjects.length === 0 ? (
                    <Empty description="無可關聯的工程" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : undefined
                }
                options={filteredProjects.map((proj: TaoyuanProject) => ({
                  value: proj.id,
                  label: `${proj.project_name}${proj.district ? ` (${proj.district})` : ''}`,
                }))}
              />
            </Col>
            <Col span={8}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={onLinkProject}
                loading={linkProjectLoading}
                disabled={!selectedProjectId}
              >
                建立關聯
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 已關聯工程列表 */}
      {linkedProjects.length > 0 ? (
        <List
          dataSource={linkedProjects}
          renderItem={(proj: LinkedProject) => (
            <Card size="small" style={{ marginBottom: 12 }}>
              <Descriptions size="small" column={2}>
                <Descriptions.Item label="工程名稱" span={2}>
                  {proj.project_name || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="分案名稱">
                  {proj.sub_case_name || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="行政區">
                  {proj.district || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="案件承辦">
                  {proj.case_handler || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="案件類型">
                  {proj.case_type ? <Tag color="blue">{proj.case_type}</Tag> : '-'}
                </Descriptions.Item>
              </Descriptions>
              <Space style={{ marginTop: 8 }}>
                <Button
                  type="link"
                  size="small"
                  onClick={() => navigate(`/taoyuan/project/${proj.project_id || proj.id}`)}
                >
                  查看工程詳情
                </Button>
                {canEdit && (
                  <Popconfirm
                    title="確定要移除此關聯嗎？"
                    onConfirm={() => {
                      // 必須使用 link_id（關聯記錄 ID），不可使用 id（工程 ID）
                      const linkId = proj.link_id;
                      const projectId = proj.project_id ?? proj.id;

                      // 嚴格驗證：link_id 必須存在且不等於 project_id
                      if (linkId === undefined || linkId === null) {
                        messageError('關聯資料缺少 link_id，請重新整理頁面後再試');
                        console.error('[unlinkProject] link_id 缺失:', {
                          proj,
                          link_id: proj.link_id,
                          project_id: proj.project_id,
                          id: proj.id,
                        });
                        refetch(); // 自動重新載入數據
                        return;
                      }

                      if (!projectId) {
                        messageError('工程資料不完整，請重新整理頁面');
                        console.error('[unlinkProject] project_id 缺失:', proj);
                        return;
                      }

                      console.debug('[unlinkProject] 執行移除:', { linkId, projectId, proj });
                      onUnlinkProject(linkId, projectId, proj);
                    }}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button
                      type="link"
                      size="small"
                      danger
                      loading={unlinkProjectLoading}
                    >
                      移除關聯
                    </Button>
                  </Popconfirm>
                )}
              </Space>
            </Card>
          )}
        />
      ) : (
        <Empty description="此派工單尚無關聯工程" image={Empty.PRESENTED_IMAGE_SIMPLE}>
          {!canEdit && (
            <Button type="link" onClick={() => navigate('/taoyuan/dispatch')}>
              返回派工列表
            </Button>
          )}
        </Empty>
      )}
    </Spin>
  );
};

export default DispatchProjectsTab;
