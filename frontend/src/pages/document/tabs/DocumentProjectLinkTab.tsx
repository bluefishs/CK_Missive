/**
 * 工程關聯 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React, { useState } from 'react';
import {
  Card,
  Select,
  Button,
  Space,
  Row,
  Col,
  Tag,
  Popconfirm,
  Spin,
  Empty,
  Descriptions,
  Typography,
  App,
} from 'antd';
import {
  EnvironmentOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { isReceiveDocument } from '../../../types/api';
import type { TaoyuanProject, DocumentProjectLink, OfficialDocument } from '../../../types/api';
import { logger } from '../../../utils/logger';

const { Text } = Typography;

interface DocumentProjectLinkTabProps {
  documentId: number | null;
  document: OfficialDocument | null;
  isEditing: boolean;
  projectLinks: DocumentProjectLink[];
  projectLinksLoading: boolean;
  availableProjects: TaoyuanProject[];
  onLinkProject: (projectId: number) => Promise<void>;
  onUnlinkProject: (linkId: number) => Promise<void>;
}

export const DocumentProjectLinkTab: React.FC<DocumentProjectLinkTabProps> = ({
  document,
  isEditing,
  projectLinks,
  projectLinksLoading,
  availableProjects,
  onLinkProject,
  onUnlinkProject,
}) => {
  const { message } = App.useApp();

  const [selectedProjectId, setSelectedProjectId] = useState<number | undefined>();
  const [linkingProject, setLinkingProject] = useState(false);

  // 已關聯的工程 ID 列表，用於過濾
  const linkedProjectIds = projectLinks.map(link => link.project_id);

  // 過濾掉已關聯的工程
  const filteredProjects = availableProjects.filter(
    (project: TaoyuanProject) => !linkedProjectIds.includes(project.id)
  );

  // 關聯已有工程
  const handleLinkExistingProject = async () => {
    if (!selectedProjectId) {
      message.warning('請選擇要關聯的工程');
      return;
    }
    setLinkingProject(true);
    try {
      await onLinkProject(selectedProjectId);
      setSelectedProjectId(undefined);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : '關聯失敗';
      message.error(errorMessage);
    } finally {
      setLinkingProject(false);
    }
  };

  // 移除關聯
  const handleUnlinkProject = async (linkId: number) => {
    if (linkId === undefined || linkId === null) {
      message.error('關聯資料缺少 link_id，請重新整理頁面');
      logger.error('[handleUnlinkProject] link_id 缺失:', linkId);
      return;
    }
    await onUnlinkProject(linkId);
  };

  return (
    <Spin spinning={projectLinksLoading}>
      {/* 已關聯工程列表 - 完整顯示工程資訊 */}
      {projectLinks.length > 0 && (
        <Card
          size="small"
          title={
            <Space>
              <EnvironmentOutlined />
              <span>已關聯工程（{projectLinks.length} 筆）</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          {projectLinks.map((item, index) => (
            <Card
              key={item.link_id}
              size="small"
              type="inner"
              style={{ marginBottom: index < projectLinks.length - 1 ? 12 : 0 }}
              title={
                <Space>
                  <EnvironmentOutlined style={{ color: '#52c41a' }} />
                  <Tag color="green">{item.district || '未分區'}</Tag>
                  <span>{item.project_name || '(無工程名稱)'}</span>
                  <Tag>{item.link_type === 'agency_incoming' ? '機關來函' : '乾坤發文'}</Tag>
                </Space>
              }
              extra={
                isEditing && (
                  <Popconfirm
                    title="確定要移除此工程關聯嗎？"
                    onConfirm={() => handleUnlinkProject(item.link_id)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button type="link" size="small" danger>
                      移除關聯
                    </Button>
                  </Popconfirm>
                )
              }
            >
              <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }} bordered>
                <Descriptions.Item label="審議年度">{item.review_year || '-'}</Descriptions.Item>
                <Descriptions.Item label="案件類型">{item.case_type || '-'}</Descriptions.Item>
                <Descriptions.Item label="行政區">{item.district || '-'}</Descriptions.Item>
                <Descriptions.Item label="分案名稱">{item.sub_case_name || '-'}</Descriptions.Item>
                <Descriptions.Item label="案件承辦">{item.case_handler || '-'}</Descriptions.Item>
                <Descriptions.Item label="查估單位">{item.survey_unit || '-'}</Descriptions.Item>
                <Descriptions.Item label="工程起點">{item.start_point || '-'}</Descriptions.Item>
                <Descriptions.Item label="工程迄點">{item.end_point || '-'}</Descriptions.Item>
                <Descriptions.Item label="道路長度">
                  {item.road_length ? `${item.road_length} 公尺` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="現況路寬">
                  {item.current_width ? `${item.current_width} 公尺` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="計畫路寬">
                  {item.planned_width ? `${item.planned_width} 公尺` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="審議結果">{item.review_result || '-'}</Descriptions.Item>
                {item.notes && (
                  <Descriptions.Item label="關聯備註" span={3}>{item.notes}</Descriptions.Item>
                )}
                <Descriptions.Item label="關聯時間">
                  {item.created_at ? dayjs(item.created_at).format('YYYY-MM-DD HH:mm') : '-'}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          ))}
        </Card>
      )}

      {/* 關聯已有工程 - 編輯模式才顯示 */}
      {isEditing && (
        <Card
          size="small"
          title={
            <Space>
              <LinkOutlined />
              <span>關聯已有工程</span>
            </Space>
          }
        >
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Select
                showSearch
                allowClear
                placeholder="搜尋並選擇已有的工程"
                value={selectedProjectId}
                onChange={setSelectedProjectId}
                filterOption={(input, option) =>
                  String(option?.label || '').toLowerCase().includes(input.toLowerCase())
                }
                style={{ width: '100%' }}
                notFoundContent={filteredProjects.length === 0 ? '無可關聯的工程' : '輸入關鍵字搜尋'}
                options={filteredProjects.map((project: TaoyuanProject) => ({
                  value: project.id,
                  label: `${project.district || '未分區'} - ${project.project_name || '(無工程名稱)'} ${project.review_year ? `- ${project.review_year}年度` : ''}`,
                }))}
              />
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<LinkOutlined />}
                onClick={handleLinkExistingProject}
                loading={linkingProject}
                disabled={!selectedProjectId}
              >
                關聯
              </Button>
            </Col>
          </Row>
          <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
            提示：選擇已存在的工程進行關聯，建立公文與工程的直接對應關係
          </div>
        </Card>
      )}

      {/* 非編輯模式提示 */}
      {!isEditing && projectLinks.length === 0 && (
        <Empty
          description="此公文尚無關聯工程"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Text type="secondary">點擊右上方「編輯」按鈕可新增工程關聯</Text>
        </Empty>
      )}
    </Spin>
  );
};

export default DocumentProjectLinkTab;
