/**
 * AI Prompt 版本管理頁面
 *
 * 管理 AI 功能的 Prompt 版本，支援新增、啟用/停用、比較差異。
 *
 * @version 1.0.0
 * @created 2026-02-08
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { ResponsiveContent } from '../components/common';
import {
  Card,
  List,
  Tag,
  Button,
  Switch,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Typography,
  message,
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
import { aiApi } from '../api/aiApi';
import type {
  PromptVersionItem,
  PromptListResponse,
  PromptCreateRequest,
  PromptCompareResponse,
} from '../api/aiApi';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

/** 功能名稱對應的中文標籤 */
const FEATURE_LABELS: Record<string, string> = {
  summary: '摘要生成',
  classify: '分類建議',
  keywords: '關鍵字提取',
  search_intent: '搜尋意圖解析',
  match_agency: '機關匹配',
};

export const AIPromptManagementPage: React.FC = () => {
  // 狀態
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<PromptListResponse | null>(null);
  const [selectedFeature, setSelectedFeature] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [compareModalVisible, setCompareModalVisible] = useState(false);
  const [compareResult, setCompareResult] = useState<PromptCompareResponse | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareIds, setCompareIds] = useState<{ a: number | null; b: number | null }>({
    a: null,
    b: null,
  });
  const [createForm] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  // 載入資料
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await aiApi.listPrompts(selectedFeature || undefined);
      setData(result);
    } catch (error) {
      message.error('載入 Prompt 版本失敗');
    } finally {
      setLoading(false);
    }
  }, [selectedFeature]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 篩選後的項目
  const filteredItems = useMemo(() => {
    if (!data) return [];
    return data.items;
  }, [data]);

  // 按功能分組
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

  // 功能列表（包含沒有版本的功能）
  const allFeatures = useMemo(() => {
    return data?.features || Object.keys(FEATURE_LABELS);
  }, [data]);

  // 啟用/停用
  const handleActivate = useCallback(
    async (id: number) => {
      try {
        const result = await aiApi.activatePrompt(id);
        message.success(result.message);
        await fetchData();
      } catch (error) {
        message.error('啟用失敗');
      }
    },
    [fetchData]
  );

  // 新增版本
  const handleCreate = useCallback(async () => {
    try {
      const values = await createForm.validateFields();
      setSubmitting(true);
      const request: PromptCreateRequest = {
        feature: values.feature,
        system_prompt: values.system_prompt,
        user_template: values.user_template || null,
        description: values.description || null,
        activate: values.activate || false,
      };
      const result = await aiApi.createPrompt(request);
      message.success(result.message);
      setCreateModalVisible(false);
      createForm.resetFields();
      await fetchData();
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        return; // 表單驗證失敗
      }
      message.error('新增 Prompt 版本失敗');
    } finally {
      setSubmitting(false);
    }
  }, [createForm, fetchData]);

  // 比較版本
  const handleCompare = useCallback(async () => {
    if (!compareIds.a || !compareIds.b) {
      message.warning('請選擇兩個版本進行比較');
      return;
    }
    setCompareLoading(true);
    try {
      const result = await aiApi.comparePrompts(compareIds.a, compareIds.b);
      setCompareResult(result);
    } catch (error) {
      message.error('比較版本失敗');
    } finally {
      setCompareLoading(false);
    }
  }, [compareIds]);

  // 開啟新增 Modal 時預填功能
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
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
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
            >
              {allFeatures.map((f) => (
                <Select.Option key={f} value={f}>
                  {FEATURE_LABELS[f] || f}
                </Select.Option>
              ))}
            </Select>
            <Text type="secondary">
              共 {filteredItems.length} 個版本
            </Text>
          </Space>

          {/* 版本列表 */}
          <Spin spinning={loading}>
            {filteredItems.length === 0 && !loading ? (
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
                  <List
                    dataSource={items}
                    renderItem={(item) => (
                      <List.Item
                        key={item.id}
                        actions={[
                          <Tooltip
                            title={item.is_active ? '目前已啟用' : '點擊啟用此版本'}
                            key="activate"
                          >
                            <Switch
                              checked={item.is_active}
                              onChange={() => {
                                if (!item.is_active) {
                                  Modal.confirm({
                                    title: '確認啟用',
                                    content: `啟用 ${FEATURE_LABELS[item.feature] || item.feature} v${item.version}？同功能的其他版本將自動停用。`,
                                    onOk: () => handleActivate(item.id),
                                  });
                                }
                              }}
                              checkedChildren="啟用"
                              unCheckedChildren="停用"
                            />
                          </Tooltip>,
                          <Button
                            key="expand"
                            type="link"
                            size="small"
                            onClick={() =>
                              setExpandedId(expandedId === item.id ? null : item.id)
                            }
                          >
                            {expandedId === item.id ? '收合' : '查看'}
                          </Button>,
                        ]}
                      >
                        <List.Item.Meta
                          avatar={
                            item.is_active ? (
                              <CheckCircleOutlined
                                style={{ fontSize: 20, color: '#52c41a' }}
                              />
                            ) : (
                              <ClockCircleOutlined
                                style={{ fontSize: 20, color: '#d9d9d9' }}
                              />
                            )
                          }
                          title={
                            <Space>
                              <Text strong>v{item.version}</Text>
                              {item.is_active && (
                                <Tag color="success">目前使用中</Tag>
                              )}
                              {item.description && (
                                <Text type="secondary">{item.description}</Text>
                              )}
                            </Space>
                          }
                          description={
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
                          }
                        />
                      </List.Item>
                    )}
                  />
                  {/* 展開的 Prompt 內容 */}
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
                        >
                          <Descriptions.Item label="系統提示詞">
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
                          </Descriptions.Item>
                          {item.user_template && (
                            <Descriptions.Item label="使用者提示詞模板">
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
                            </Descriptions.Item>
                          )}
                        </Descriptions>
                      </div>
                    ))}
                </Card>
              ))
            )}
          </Spin>
        </Space>
      </Card>

      {/* 新增 Prompt 版本 Modal */}
      <Modal
        title="新增 Prompt 版本"
        open={createModalVisible}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
        }}
        confirmLoading={submitting}
        width={720}
        okText="新增"
        cancelText="取消"
        forceRender
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="feature"
            label="功能名稱"
            rules={[{ required: true, message: '請選擇功能名稱' }]}
          >
            <Select placeholder="選擇功能">
              {allFeatures.map((f) => (
                <Select.Option key={f} value={f}>
                  {FEATURE_LABELS[f] || f}（{f}）
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="system_prompt"
            label="系統提示詞"
            rules={[{ required: true, message: '請輸入系統提示詞' }]}
          >
            <TextArea
              rows={10}
              placeholder="輸入系統提示詞（支援 {variable} 佔位符）"
              style={{ fontFamily: 'monospace', fontSize: 13 }}
            />
          </Form.Item>

          <Form.Item name="user_template" label="使用者提示詞模板（選填）">
            <TextArea
              rows={4}
              placeholder="輸入使用者提示詞模板（選填）"
              style={{ fontFamily: 'monospace', fontSize: 13 }}
            />
          </Form.Item>

          <Form.Item name="description" label="版本說明（選填）">
            <Input placeholder="簡述這個版本的修改內容" maxLength={500} />
          </Form.Item>

          <Form.Item name="activate" valuePropName="checked" initialValue={false}>
            <Switch checkedChildren="立即啟用" unCheckedChildren="暫不啟用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 版本比較 Modal */}
      <Modal
        title="版本比較"
        open={compareModalVisible}
        onCancel={() => {
          setCompareModalVisible(false);
          setCompareResult(null);
          setCompareIds({ a: null, b: null });
        }}
        footer={null}
        width={900}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Row gutter={16}>
            <Col span={10}>
              <Select
                style={{ width: '100%' }}
                placeholder="選擇版本 A"
                value={compareIds.a}
                onChange={(v) => setCompareIds((prev) => ({ ...prev, a: v }))}
              >
                {filteredItems.map((item) => (
                  <Select.Option key={item.id} value={item.id}>
                    [{FEATURE_LABELS[item.feature] || item.feature}] v{item.version}
                    {item.is_active ? ' (啟用中)' : ''}
                  </Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={4} style={{ textAlign: 'center', lineHeight: '32px' }}>
              <SwapOutlined style={{ fontSize: 20 }} />
            </Col>
            <Col span={10}>
              <Select
                style={{ width: '100%' }}
                placeholder="選擇版本 B"
                value={compareIds.b}
                onChange={(v) => setCompareIds((prev) => ({ ...prev, b: v }))}
              >
                {filteredItems.map((item) => (
                  <Select.Option key={item.id} value={item.id}>
                    [{FEATURE_LABELS[item.feature] || item.feature}] v{item.version}
                    {item.is_active ? ' (啟用中)' : ''}
                  </Select.Option>
                ))}
              </Select>
            </Col>
          </Row>

          <Button
            type="primary"
            onClick={handleCompare}
            loading={compareLoading}
            disabled={!compareIds.a || !compareIds.b}
            block
          >
            比較
          </Button>

          {compareResult && (
            <div>
              <Divider />
              {compareResult.diffs.map((diff) => (
                <Card
                  key={diff.field}
                  size="small"
                  title={
                    <Space>
                      <Text strong>{diff.field}</Text>
                      {diff.changed ? (
                        <Tag color="orange">有差異</Tag>
                      ) : (
                        <Tag color="green">相同</Tag>
                      )}
                    </Space>
                  }
                  style={{ marginBottom: 12 }}
                >
                  {diff.changed ? (
                    <Row gutter={16}>
                      <Col span={12}>
                        <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
                          版本 A (v{compareResult.version_a.version})
                        </Text>
                        <div
                          style={{
                            background: '#fff2f0',
                            padding: 8,
                            borderRadius: 4,
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'monospace',
                            fontSize: 12,
                            maxHeight: 200,
                            overflow: 'auto',
                          }}
                        >
                          {diff.value_a || '(空)'}
                        </div>
                      </Col>
                      <Col span={12}>
                        <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
                          版本 B (v{compareResult.version_b.version})
                        </Text>
                        <div
                          style={{
                            background: '#f6ffed',
                            padding: 8,
                            borderRadius: 4,
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'monospace',
                            fontSize: 12,
                            maxHeight: 200,
                            overflow: 'auto',
                          }}
                        >
                          {diff.value_b || '(空)'}
                        </div>
                      </Col>
                    </Row>
                  ) : (
                    <Paragraph
                      style={{
                        whiteSpace: 'pre-wrap',
                        fontFamily: 'monospace',
                        fontSize: 12,
                        maxHeight: 200,
                        overflow: 'auto',
                        margin: 0,
                      }}
                    >
                      {diff.value_a || '(空)'}
                    </Paragraph>
                  )}
                </Card>
              ))}
            </div>
          )}
        </Space>
      </Modal>
    </ResponsiveContent>
  );
};

export default AIPromptManagementPage;
