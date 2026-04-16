/**
 * 作業歷程表單頁面（導航模式）
 *
 * 支援新建與編輯模式：
 * - 新建: /taoyuan/dispatch/:dispatchId/workflow/create
 * - 編輯: /taoyuan/dispatch/:dispatchId/workflow/:recordId/edit
 *
 * v3.1.0: 公文選項 + 表單邏輯提取至 hooks
 *
 * @version 3.1.0
 * @date 2026-03-18
 */

import React, { useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Space,
  App,
  Typography,
  Row,
  Col,
  Radio,
  Empty,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  HistoryOutlined,
} from '@ant-design/icons';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { TAOYUAN_DISPATCH_ENDPOINTS } from '../api/endpoints';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  WORK_CATEGORY_GROUPS,
  CHAIN_STATUS_OPTIONS,
} from '../components/taoyuan/workflow';
import { useWorkRecordDocOptions } from './workRecordForm/useWorkRecordDocOptions';
import { useWorkRecordFormLogic } from './workRecordForm/useWorkRecordFormLogic';

const { TextArea } = Input;
const { Title, Text } = Typography;

const WorkRecordFormPage: React.FC = () => {
  const { dispatchId, recordId } = useParams<{
    dispatchId: string;
    recordId: string;
  }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const { message } = App.useApp();

  const isNew = !recordId;
  const dispatchOrderId = parseInt(dispatchId || '0', 10);
  const workRecordId = recordId ? parseInt(recordId, 10) : undefined;

  const returnTo = searchParams.get('returnTo');
  const returnPath = returnTo || `/taoyuan/dispatch/${dispatchId}?tab=correspondence`;

  const urlDocumentId = searchParams.get('document_id')
    || searchParams.get('incoming_doc_id')
    || searchParams.get('outgoing_doc_id');
  const urlParentRecordId = searchParams.get('parent_record_id');
  const urlWorkCategory = searchParams.get('work_category');

  // 取得 dispatch 的 work_type_items（所屬作業選擇器用）
  const { data: dispatchDetail } = useQuery({
    queryKey: ['dispatch-detail', dispatchOrderId],
    queryFn: () =>
      apiClient.post<{ work_type_items?: { id: number; work_type: string }[] }>(
        TAOYUAN_DISPATCH_ENDPOINTS.DISPATCH_ORDERS_DETAIL(dispatchOrderId), {}
      ),
    enabled: dispatchOrderId > 0,
    staleTime: 300_000,
  });
  const workTypeItems = dispatchDetail?.work_type_items ?? [];

  // 公文選項 (extracted hook)
  const {
    docOptions,
    linkedDocs,
    searchedDocsResult,
    setDocSearchKeyword,
    searchingDocs,
    docSearchKeyword,
  } = useWorkRecordDocOptions(dispatchOrderId, undefined); // record loaded separately

  // 表單邏輯 (extracted hook)
  const {
    record,
    isLoading,
    parentRecordOptions,
    handleDocumentChange,
    handleSave,
    isSaving,
  } = useWorkRecordFormLogic({
    dispatchOrderId,
    workRecordId,
    isNew,
    form,
    message,
    navigate,
    returnPath,
    urlDocumentId,
    urlParentRecordId,
    urlWorkCategory,
    linkedDocs,
    searchedDocsResult,
  });

  // Re-init doc options with actual record once loaded
  const {
    docOptions: docOptionsWithRecord,
  } = useWorkRecordDocOptions(dispatchOrderId, record);

  const finalDocOptions = record ? docOptionsWithRecord : docOptions;

  const handleBack = useCallback(() => {
    navigate(returnPath);
  }, [navigate, returnPath]);

  return (
    <ResponsiveContent>
      <div style={{ maxWidth: 600, margin: '0 auto', padding: '24px 0' }}>
        {/* Header */}
        <div style={{ marginBottom: 16 }}>
          <Button
            type="link"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
            style={{ padding: 0, marginBottom: 8 }}
          >
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            <HistoryOutlined style={{ marginRight: 8 }} />
            {isNew ? '新增作業紀錄' : '編輯作業紀錄'}
          </Title>
        </div>

        {/* Form */}
        <Card loading={!isNew && isLoading}>
          <Form form={form} layout="vertical" size="middle">
            <Form.Item name="document_id" label="關聯公文">
              <Select
                placeholder="輸入公文字號或主旨搜尋..."
                options={finalDocOptions}
                allowClear
                showSearch
                filterOption={false}
                onSearch={setDocSearchKeyword}
                onChange={handleDocumentChange}
                loading={searchingDocs}
                notFoundContent={
                  docSearchKeyword ? (
                    <Empty description="無符合的公文" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : (
                    <Text type="secondary">輸入關鍵字搜尋公文</Text>
                  )
                }
              />
            </Form.Item>

            {/* 作業分類區塊 — 縮排呈現 */}
            <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}
                  title={<Text type="secondary" style={{ fontSize: 13 }}>作業分類</Text>}>
              {/* 所屬作業（多 work_type 時顯示） */}
              {workTypeItems.length >= 2 && (
                <Form.Item
                  name="work_type_id"
                  label="所屬作業"
                  tooltip="派工通知、行政等共用紀錄可選「共用」；成果回函請選對應作業"
                >
                  <Select
                    placeholder="共用 (全部作業)"
                    allowClear
                    options={[
                      { value: null as unknown as number, label: '共用 (全部作業)' },
                      ...workTypeItems.map(wt => ({
                        value: wt.id,
                        label: wt.work_type,
                      })),
                    ]}
                  />
                </Form.Item>
              )}

              <Row gutter={12}>
                <Col span={14}>
                  <Form.Item
                    name="work_category"
                    label="作業類別"
                    rules={[{ required: true, message: '請選擇作業類別' }]}
                  >
                    <Select
                      placeholder="請選擇"
                      options={WORK_CATEGORY_GROUPS.map((group) => ({
                        label: group.group,
                        options: group.items.map((item) => ({
                          value: item.value,
                          label: item.label,
                        })),
                      }))}
                    />
                  </Form.Item>
                </Col>
                <Col span={10}>
                  <Form.Item
                    name="status"
                    label="狀態"
                    rules={[{ required: true, message: '請選擇狀態' }]}
                  >
                    <Radio.Group>
                      {CHAIN_STATUS_OPTIONS.map((opt) => (
                        <Radio.Button key={opt.value} value={opt.value}>
                          {opt.label}
                        </Radio.Button>
                      ))}
                    </Radio.Group>
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            <Row gutter={12}>
              <Col span={14}>
                <Form.Item name="parent_record_id" label="前序紀錄">
                  <Select
                    placeholder="自動預選最後一筆"
                    options={parentRecordOptions}
                    allowClear
                    showSearch
                    optionFilterProp="label"
                    notFoundContent="尚無其他紀錄"
                  />
                </Form.Item>
              </Col>
              <Col span={10}>
                <Form.Item name="deadline_date" label="期限日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="description" label="事項描述">
              <TextArea rows={3} placeholder="選擇公文後自動帶入主旨，可自行修改補充" />
            </Form.Item>

            {/* 隱藏欄位 */}
            <Form.Item name="milestone_type" hidden><Input /></Form.Item>
            <Form.Item name="incoming_doc_id" hidden><Input /></Form.Item>
            <Form.Item name="outgoing_doc_id" hidden><Input /></Form.Item>

            <div style={{ textAlign: 'right', marginTop: 8 }}>
              <Space>
                <Button onClick={handleBack}>取消</Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  loading={isSaving}
                  onClick={handleSave}
                >
                  {isNew ? '建立' : '儲存'}
                </Button>
              </Space>
            </div>
          </Form>
        </Card>
      </div>
    </ResponsiveContent>
  );
};

export default WorkRecordFormPage;
