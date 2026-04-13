/**
 * AI Prompt 版本管理面板
 *
 * v1.1.0: 拆分 PromptCreateModal + PromptCompareModal
 *
 * @version 1.1.0
 * @created 2026-02-08
 * @updated 2026-03-18
 */

import React, { useState, useCallback, useMemo } from 'react';
import {
  App,
  Card,
  Flex,
  Tag,
  Button,
  Switch,
  Form,
  Select,
  Space,
  Typography,
  Descriptions,
  Spin,
  Empty,
  Tooltip,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  SwapOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  RobotOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import {
  useAIPrompts,
  useCreatePrompt,
  useActivatePrompt,
  useComparePrompts,
} from '../../../hooks';
import type {
  PromptVersionItem,
  PromptCreateRequest,
  PromptCompareResponse,
} from '../../../types/ai';
import { PromptCreateModal } from './PromptCreateModal';
import { PromptCompareModal } from './PromptCompareModal';

const { Title, Text, Paragraph } = Typography;

const FEATURE_LABELS: Record<string, string> = {
  summary: '摘要生成',
  classify: '分類建議',
  keywords: '關鍵字提取',
  search_intent: '搜尋意圖解析',
  match_agency: '機關匹配',
};

export const PromptManagementContent: React.FC = () => {
  const { message, modal } = App.useApp();

  const [selectedFeature, setSelectedFeature] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [compareModalVisible, setCompareModalVisible] = useState(false);
  const [compareResult, setCompareResult] = useState<PromptCompareResponse | null>(null);
  const [compareIds, setCompareIds] = useState<{ a: number | null; b: number | null }>({
    a: null,
    b: null,
  });
  const [createForm] = Form.useForm();

  const promptsQuery = useAIPrompts(selectedFeature);
  const createMutation = useCreatePrompt();
  const activateMutation = useActivatePrompt();
  const compareMutation = useComparePrompts();

  const data = promptsQuery.data ?? null;

  const filteredItems = useMemo(() => {
    if (!data) return [];
    return data.items;
  }, [data]);

  const groupedByFeature = useMemo(() => {
    const groups: Record<string, PromptVersionItem[]> = {};
    for (const item of filteredItems) {
      if (!groups[item.feature]) {
        groups[item.feature] = [];
      }
      const featureGroup = groups[item.feature];
      if (featureGroup) {
        featureGroup.push(item);
      }
    }
    return groups;
  }, [filteredItems]);

  const allFeatures = useMemo(() => {
    return data?.features || Object.keys(FEATURE_LABELS);
  }, [data]);

  const handleActivate = useCallback(
    async (id: number) => {
      try {
        const result = await activateMutation.mutateAsync(id);
        message.success(result.message);
      } catch {
        message.error('啟用失敗');
      }
    },
    [activateMutation, message]
  );

  const handleCreate = useCallback(async () => {
    try {
      const values = await createForm.validateFields();
      const request: PromptCreateRequest = {
        feature: values.feature,
        system_prompt: values.system_prompt,
        user_template: values.user_template || null,
        description: values.description || null,
        activate: values.activate || false,
      };
      const result = await createMutation.mutateAsync(request);
      message.success(result.message);
      setCreateModalVisible(false);
      createForm.resetFields();
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return;
      }
      message.error('新增 Prompt 版本失敗');
    }
  }, [createForm, createMutation, message]);

  const handleCompare = useCallback(async () => {
    if (!compareIds.a || !compareIds.b) {
      message.warning('請選擇兩個版本進行比較');
      return;
    }
    try {
      const result = await compareMutation.mutateAsync({ idA: compareIds.a, idB: compareIds.b });
      setCompareResult(result);
    } catch {
      message.error('比較版本失敗');
    }
  }, [compareIds, compareMutation, message]);

  const openCreateModal = useCallback(
    (feature?: string) => {
      createForm.resetFields();
      if (feature) {
        createForm.setFieldsValue({ feature });
      }
      setCreateModalVisible(true);
    },
    [createForm]
  );

  return (
    <>
      <Card>
        <Space vertical size="large" style={{ width: '100%' }}>
          {/* 標題列 */}
          <Row justify="space-between" align="middle">
            <Col>
              <Space>
                <RobotOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                <Title level={3} style={{ margin: 0 }}>
                  AI Prompt 版本管理
                </Title>
              </Space>
            </Col>
            <Col>
              <Space>
                <Button
                  icon={<SwapOutlined />}
                  onClick={() => setCompareModalVisible(true)}
                  disabled={filteredItems.length < 2}
                >
                  版本比較
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => openCreateModal(selectedFeature || undefined)}
                >
                  新增版本
                </Button>
              </Space>
            </Col>
          </Row>

          {/* 功能篩選 */}
          <Space>
            <Text strong>功能篩選：</Text>
            <Select
              style={{ width: 200 }}
              allowClear
              placeholder="全部功能"
              value={selectedFeature}
              onChange={(v) => setSelectedFeature(v || null)}
              options={allFeatures.map((f) => ({
                value: f,
                label: FEATURE_LABELS[f] || f,
              }))}
            />
            <Text type="secondary">
              共 {filteredItems.length} 個版本
            </Text>
          </Space>

          {/* 版本列表 */}
          <Spin spinning={promptsQuery.isLoading}>
            {filteredItems.length === 0 && !promptsQuery.isLoading ? (
              <Empty description="尚無 Prompt 版本，請點擊「新增版本」開始建立" />
            ) : (
              Object.entries(groupedByFeature).map(([feature, items]) => (
                <Card
                  key={feature}
                  title={
                    <Space>
                      <FileTextOutlined />
                      <span>{FEATURE_LABELS[feature] || feature}</span>
                      <Tag color="blue">{feature}</Tag>
                      <Tag color="green">{items.length} 個版本</Tag>
                    </Space>
                  }
                  size="small"
                  style={{ marginBottom: 16 }}
                  extra={
                    <Button
                      size="small"
                      type="link"
                      icon={<PlusOutlined />}
                      onClick={() => openCreateModal(feature)}
                    >
                      新增
                    </Button>
                  }
                >
                  <Flex vertical gap={0}>
                    {items.map((item) => (
                      <div
                        key={item.id}
                        style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #f0f0f0' }}
                      >
                        <div style={{ marginRight: 12, flexShrink: 0 }}>
                          {item.is_active ? (
                            <CheckCircleOutlined
                              style={{ fontSize: 20, color: '#52c41a' }}
                            />
                          ) : (
                            <ClockCircleOutlined
                              style={{ fontSize: 20, color: '#d9d9d9' }}
                            />
                          )}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div>
                            <Space>
                              <Text strong>v{item.version}</Text>
                              {item.is_active && (
                                <Tag color="success">目前使用中</Tag>
                              )}
                              {item.description && (
                                <Text type="secondary">{item.description}</Text>
                              )}
                            </Space>
                          </div>
                          <div>
                            <Space size="large">
                              <Text type="secondary">
                                建立者：{item.created_by || '系統'}
                              </Text>
                              <Text type="secondary">
                                建立時間：
                                {item.created_at
                                  ? new Date(item.created_at).toLocaleString('zh-TW')
                                  : '-'}
                              </Text>
                            </Space>
                          </div>
                        </div>
                        <Space style={{ flexShrink: 0, marginLeft: 12 }}>
                          <Tooltip
                            title={item.is_active ? '目前已啟用' : '點擊啟用此版本'}
                          >
                            <Switch
                              checked={item.is_active}
                              onChange={() => {
                                if (!item.is_active) {
                                  modal.confirm({
                                    title: '確認啟用',
                                    content: `啟用 ${FEATURE_LABELS[item.feature] || item.feature} v${item.version}？同功能的其他版本將自動停用。`,
                                    onOk: () => handleActivate(item.id),
                                  });
                                }
                              }}
                              checkedChildren="啟用"
                              unCheckedChildren="停用"
                            />
                          </Tooltip>
                          <Button
                            type="link"
                            size="small"
                            onClick={() =>
                              setExpandedId(expandedId === item.id ? null : item.id)
                            }
                          >
                            {expandedId === item.id ? '收合' : '查看'}
                          </Button>
                        </Space>
                      </div>
                    ))}
                  </Flex>
                  {items
                    .filter((item) => expandedId === item.id)
                    .map((item) => (
                      <div key={`detail-${item.id}`} style={{ marginTop: 8 }}>
                        <Divider style={{ margin: '8px 0' }} />
                        <Descriptions
                          column={1}
                          size="small"
                          bordered
                          title={`v${item.version} Prompt 內容`}
                          items={[
                            {
                              key: '系統提示詞',
                              label: '系統提示詞',
                              children: (
                                <Paragraph
                                  copyable
                                  style={{
                                    whiteSpace: 'pre-wrap',
                                    margin: 0,
                                    maxHeight: 300,
                                    overflow: 'auto',
                                    fontFamily: 'monospace',
                                    fontSize: 13,
                                  }}
                                >
                                  {item.system_prompt}
                                </Paragraph>
                              ),
                            },
                            ...(item.user_template ? [{
                              key: '使用者提示詞模板',
                              label: '使用者提示詞模板',
                              children: (
                                <Paragraph
                                  copyable
                                  style={{
                                    whiteSpace: 'pre-wrap',
                                    margin: 0,
                                    maxHeight: 200,
                                    overflow: 'auto',
                                    fontFamily: 'monospace',
                                    fontSize: 13,
                                  }}
                                >
                                  {item.user_template}
                                </Paragraph>
                              ),
                            }] : []),
                          ]}
                        />
                      </div>
                    ))}
                </Card>
              ))
            )}
          </Spin>
        </Space>
      </Card>

      <PromptCreateModal
        open={createModalVisible}
        form={createForm}
        allFeatures={allFeatures}
        loading={createMutation.isPending}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
        }}
      />

      <PromptCompareModal
        open={compareModalVisible}
        items={filteredItems}
        compareIds={compareIds}
        compareResult={compareResult}
        comparing={compareMutation.isPending}
        onCompareIdsChange={setCompareIds}
        onCompare={handleCompare}
        onClose={() => {
          setCompareModalVisible(false);
          setCompareResult(null);
          setCompareIds({ a: null, b: null });
        }}
      />
    </>
  );
};
