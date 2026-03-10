/**
 * 工程關聯 Tab
 *
 * @version 1.1.0 - 新增「快速新增工程」功能
 * @date 2026-03-05
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
  Modal,
  Form,
  Input,
  InputNumber,
} from 'antd';
import {
  EnvironmentOutlined,
  LinkOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import type { TaoyuanProject, DocumentProjectLink, OfficialDocument } from '../../../types/api';
import type { TaoyuanProjectCreate } from '../../../types/taoyuan';
import { logger } from '../../../utils/logger';
import {
  CASE_TYPE_OPTIONS,
  DISTRICT_OPTIONS,
} from '../../../constants/taoyuanOptions';

const { Text } = Typography;
const { Option } = Select;

interface DocumentProjectLinkTabProps {
  documentId: number | null;
  document: OfficialDocument | null;
  isEditing: boolean;
  projectLinks: DocumentProjectLink[];
  projectLinksLoading: boolean;
  availableProjects: TaoyuanProject[];
  onLinkProject: (projectId: number) => Promise<void>;
  onUnlinkProject: (linkId: number) => Promise<void>;
  onCreateAndLinkProject?: (data: TaoyuanProjectCreate) => Promise<void>;
}

export const DocumentProjectLinkTab: React.FC<DocumentProjectLinkTabProps> = ({
  document: _document,
  isEditing,
  projectLinks,
  projectLinksLoading,
  availableProjects,
  onLinkProject,
  onUnlinkProject,
  onCreateAndLinkProject,
}) => {
  const navigate = useNavigate();
  const { message } = App.useApp();

  const [selectedProjectId, setSelectedProjectId] = useState<number | undefined>();
  const [linkingProject, setLinkingProject] = useState(false);

  // 快速新增工程 Modal
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createForm] = Form.useForm<TaoyuanProjectCreate>();

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

  // 快速新增工程並關聯
  const handleCreateProject = async () => {
    if (!onCreateAndLinkProject) return;
    try {
      const values = await createForm.validateFields();
      setCreating(true);
      await onCreateAndLinkProject({
        ...values,
        contract_project_id: _document?.contract_project_id || undefined,
      });
      message.success('工程新增並關聯成功');
      createForm.resetFields();
      setCreateModalOpen(false);
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'errorFields' in error) return; // 表單驗證失敗
      const errorMessage = error instanceof Error ? error.message : '新增工程失敗';
      message.error(errorMessage);
    } finally {
      setCreating(false);
    }
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
                <Space>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate(`/taoyuan/project/${item.project_id}`)}
                  >
                    查看詳情
                  </Button>
                  {isEditing && (
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
                  )}
                </Space>
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

      {/* 關聯已有工程 / 新增工程 - 編輯模式才顯示 */}
      {isEditing && (
        <Card
          size="small"
          title={
            <Space>
              <LinkOutlined />
              <span>關聯工程</span>
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
            {onCreateAndLinkProject && (
              <Col>
                <Button
                  icon={<PlusOutlined />}
                  onClick={() => setCreateModalOpen(true)}
                >
                  新增工程
                </Button>
              </Col>
            )}
          </Row>
          <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
            提示：選擇已存在的工程進行關聯；若無對應工程，可點擊「新增工程」快速建立並自動關聯
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

      {/* 快速新增工程 Modal */}
      <Modal
        title="快速新增工程"
        open={createModalOpen}
        onOk={handleCreateProject}
        onCancel={() => { setCreateModalOpen(false); createForm.resetFields(); }}
        confirmLoading={creating}
        okText="新增並關聯"
        cancelText="取消"
        width={600}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="project_name"
            label="工程名稱"
            rules={[{ required: true, message: '請輸入工程名稱' }]}
          >
            <Input placeholder="請輸入工程名稱" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="review_year" label="審議年度">
                <InputNumber style={{ width: '100%' }} min={100} max={200} placeholder="如 115" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="case_type" label="案件類型">
                <Select placeholder="選擇類型" allowClear>
                  {CASE_TYPE_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="district" label="行政區">
                <Select placeholder="選擇行政區" allowClear showSearch>
                  {DISTRICT_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="start_point" label="工程起點">
                <Input placeholder="請輸入起點" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="end_point" label="工程迄點">
                <Input placeholder="請輸入迄點" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="case_handler" label="案件承辦">
                <Input placeholder="承辦人" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="survey_unit" label="查估單位">
                <Input placeholder="查估單位" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sub_case_name" label="分案名稱">
                <Input placeholder="分案名稱" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </Spin>
  );
};

export default DocumentProjectLinkTab;
