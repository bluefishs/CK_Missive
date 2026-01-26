/**
 * 派工安排 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Row,
  Col,
  Tag,
  Popconfirm,
  Spin,
  Empty,
  Alert,
  Divider,
  Typography,
  App,
} from 'antd';
import {
  FileTextOutlined,
  SendOutlined,
  PlusOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { isReceiveDocument } from '../../../types/api';
import type {
  DispatchOrder,
  OfficialDocument,
  DocumentDispatchLink,
} from '../../../types/api';
import type { ProjectAgencyContact } from '../../../api/projectAgencyContacts';
import type { ProjectVendor } from '../../../api/projectVendorsApi';
import { dispatchOrdersApi } from '../../../api/taoyuanDispatchApi';
import { logger } from '../../../utils/logger';
import { TAOYUAN_WORK_TYPES_LIST } from './constants';

const { Option } = Select;
const { Text } = Typography;

interface DocumentDispatchTabProps {
  documentId: number | null;
  document: OfficialDocument | null;
  isEditing: boolean;
  dispatchLinks: DocumentDispatchLink[];
  dispatchLinksLoading: boolean;
  agencyContacts: ProjectAgencyContact[];
  projectVendors: ProjectVendor[];
  availableDispatches: DispatchOrder[];
  onCreateDispatch: (formValues: Record<string, unknown>) => Promise<void>;
  onLinkDispatch: (dispatchId: number) => Promise<void>;
  onUnlinkDispatch: (linkId: number) => Promise<void>;
}

export const DocumentDispatchTab: React.FC<DocumentDispatchTabProps> = ({
  document,
  isEditing,
  dispatchLinks,
  dispatchLinksLoading,
  agencyContacts,
  projectVendors,
  availableDispatches,
  onCreateDispatch,
  onLinkDispatch,
  onUnlinkDispatch,
}) => {
  const navigate = useNavigate();
  const { message } = App.useApp();

  // 在組件內部創建 form，避免父組件的 useForm 警告
  const [dispatchForm] = Form.useForm();

  // 搜尋派工紀錄的狀態
  const [selectedDispatchId, setSelectedDispatchId] = useState<number | undefined>();
  const [linkingDispatch, setLinkingDispatch] = useState(false);

  // 編輯模式時自動載入下一個派工單號
  useEffect(() => {
    if (isEditing) {
      const loadNextDispatchNo = async () => {
        try {
          const result = await dispatchOrdersApi.getNextDispatchNo();
          if (result.success && result.next_dispatch_no) {
            dispatchForm.setFieldsValue({ dispatch_no: result.next_dispatch_no });
          }
        } catch (error) {
          logger.error('[loadNextDispatchNo] 載入派工單號失敗:', error);
        }
      };
      loadNextDispatchNo();
    }
  }, [isEditing, dispatchForm]);

  // 判斷當前公文類型 (收文/發文)
  const isReceiveDoc = isReceiveDocument(document?.category);

  // 已關聯的派工 ID 列表，用於過濾
  const linkedDispatchIds = dispatchLinks.map(link => link.dispatch_order_id);

  // 過濾掉已關聯的派工
  const filteredDispatches = availableDispatches.filter(
    (dispatch: DispatchOrder) => !linkedDispatchIds.includes(dispatch.id)
  );

  // 關聯已有派工
  const handleLinkExistingDispatch = async () => {
    if (!selectedDispatchId) {
      message.warning('請選擇要關聯的派工紀錄');
      return;
    }
    setLinkingDispatch(true);
    try {
      await onLinkDispatch(selectedDispatchId);
      setSelectedDispatchId(undefined);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : '關聯失敗';
      message.error(errorMessage);
    } finally {
      setLinkingDispatch(false);
    }
  };

  // 移除關聯
  const handleUnlinkDispatch = async (linkId: number) => {
    if (linkId === undefined || linkId === null) {
      message.error('關聯資料缺少 link_id，請重新整理頁面');
      logger.error('[handleUnlinkDispatch] link_id 缺失:', linkId);
      return;
    }
    await onUnlinkDispatch(linkId);
  };

  return (
    <Spin spinning={dispatchLinksLoading}>
      {/* 已關聯派工列表 - 完整顯示派工資訊 */}
      {dispatchLinks.length > 0 && (
        <Card
          size="small"
          title={
            <Space>
              <SendOutlined />
              <span>已關聯派工（{dispatchLinks.length} 筆）</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          {dispatchLinks.map((item, index) => (
            <Card
              key={item.link_id}
              size="small"
              type="inner"
              style={{ marginBottom: index < dispatchLinks.length - 1 ? 12 : 0 }}
              title={
                <Space>
                  <SendOutlined style={{ color: item.link_type === 'agency_incoming' ? '#1890ff' : '#52c41a' }} />
                  <Tag color={item.link_type === 'agency_incoming' ? 'blue' : 'green'}>
                    {item.dispatch_no}
                  </Tag>
                  <span>{item.project_name || '(無工程名稱)'}</span>
                  <Tag>{item.link_type === 'agency_incoming' ? '機關來函派工' : '乾坤發文派工'}</Tag>
                </Space>
              }
              extra={
                <Space>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate(`/taoyuan/dispatch/${item.dispatch_order_id}`)}
                  >
                    查看詳情
                  </Button>
                  {isEditing && (
                    <Popconfirm
                      title="確定要移除此派工關聯嗎？"
                      onConfirm={() => handleUnlinkDispatch(item.link_id)}
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
              {/* 派工基本資訊 - 使用 Row/Col 布局 */}
              <Row gutter={[16, 8]} style={{ marginBottom: 12 }}>
                <Col xs={24} sm={8}>
                  <Text type="secondary">作業類別：</Text>
                  <Text strong>{item.work_type || '-'}</Text>
                </Col>
                <Col xs={24} sm={8}>
                  <Text type="secondary">履約期限：</Text>
                  <Text strong style={{ color: '#fa8c16' }}>{item.deadline || '-'}</Text>
                </Col>
                <Col xs={24} sm={8}>
                  <Text type="secondary">建立時間：</Text>
                  <Text>{item.created_at ? dayjs(item.created_at).format('YYYY-MM-DD HH:mm') : '-'}</Text>
                </Col>
              </Row>

              {/* 承辦資訊 */}
              <Row gutter={[16, 8]} style={{ marginBottom: 12 }}>
                <Col xs={24} sm={8}>
                  <Text type="secondary">案件承辦：</Text>
                  <Text>{item.case_handler || '-'}</Text>
                </Col>
                <Col xs={24} sm={8}>
                  <Text type="secondary">查估單位：</Text>
                  <Text>{item.survey_unit || '-'}</Text>
                </Col>
                <Col xs={24} sm={8}>
                  <Text type="secondary">分案名稱：</Text>
                  <Text>{item.sub_case_name || '-'}</Text>
                </Col>
              </Row>

              {/* 聯絡備註 - 獨立顯示 */}
              {item.contact_note && (
                <div style={{ marginBottom: 12, padding: '8px 12px', backgroundColor: '#fffbe6', borderRadius: 4 }}>
                  <Text type="secondary">聯絡備註：</Text>
                  <div style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{item.contact_note}</div>
                </div>
              )}

              {/* 資料夾連結 */}
              <Row gutter={[16, 8]} style={{ marginBottom: 12 }}>
                <Col xs={24} sm={12}>
                  <Text type="secondary">雲端資料夾：</Text>
                  {item.cloud_folder ? (
                    <a href={item.cloud_folder} target="_blank" rel="noopener noreferrer" style={{ wordBreak: 'break-all' }}>
                      {item.cloud_folder}
                    </a>
                  ) : <Text type="secondary">-</Text>}
                </Col>
                <Col xs={24} sm={12}>
                  <Text type="secondary">專案資料夾：</Text>
                  <Text copyable={!!item.project_folder} style={{ wordBreak: 'break-all' }}>
                    {item.project_folder || '-'}
                  </Text>
                </Col>
              </Row>

              {/* 公文關聯 */}
              <Divider style={{ margin: '8px 0' }} />
              <Row gutter={[16, 8]}>
                <Col xs={24} sm={12}>
                  <Text type="secondary">機關函文號：</Text>
                  <Text>{item.agency_doc_number || '-'}</Text>
                </Col>
                <Col xs={24} sm={12}>
                  <Text type="secondary">乾坤函文號：</Text>
                  <Text>{item.company_doc_number || '-'}</Text>
                </Col>
              </Row>
            </Card>
          ))}
        </Card>
      )}

      {/* 新增派工表單 - Form 始終渲染以避免 useForm 警告 */}
      <Form form={dispatchForm} layout="vertical" size="small">
        {isEditing && (
          <Card
            size="small"
            title={
              <Space>
                <PlusOutlined />
                <span>新增派工</span>
              </Space>
            }
          >
            {/* 第一行：派工單號 + 工程名稱/派工事項 */}
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  name="dispatch_no"
                  label="派工單號"
                  rules={[{ required: true, message: '請輸入派工單號' }]}
                >
                  <Input placeholder="例: TY-2026-001" />
                </Form.Item>
              </Col>
              <Col span={16}>
                <Form.Item name="project_name" label="工程名稱/派工事項">
                  <Input placeholder="派工事項說明" />
                </Form.Item>
              </Col>
            </Row>

            {/* 第二行：作業類別 + 分案名稱/派工備註 + 履約期限 */}
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="work_type" label="作業類別">
                  <Select allowClear placeholder="選擇作業類別">
                    {TAOYUAN_WORK_TYPES_LIST.map((type) => (
                      <Option key={type} value={type}>
                        {type}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="sub_case_name" label="分案名稱/派工備註">
                  <Input />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="deadline" label="履約期限">
                  <Input placeholder="例: 114/12/31" />
                </Form.Item>
              </Col>
            </Row>

            {/* 第三行：案件承辦 + 查估單位 + 聯絡備註 */}
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  name="case_handler"
                  label="案件承辦"
                  tooltip="從機關承辦清單選擇"
                >
                  <Select
                    placeholder="選擇案件承辦"
                    allowClear
                    showSearch
                    optionFilterProp="label"
                  >
                    {agencyContacts.map((contact: ProjectAgencyContact) => (
                      <Option
                        key={contact.id}
                        value={contact.contact_name}
                        label={contact.contact_name}
                      >
                        <div style={{ lineHeight: 1.4 }}>
                          <div>{contact.contact_name}</div>
                          {(contact.position || contact.department) && (
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              {[contact.position, contact.department].filter(Boolean).join(' / ')}
                            </Text>
                          )}
                        </div>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="survey_unit"
                  label="查估單位"
                  tooltip="從協力廠商清單選擇"
                >
                  <Select
                    placeholder="選擇查估單位"
                    allowClear
                    showSearch
                    optionFilterProp="label"
                  >
                    {projectVendors.map((vendor: ProjectVendor) => (
                      <Option
                        key={vendor.vendor_id}
                        value={vendor.vendor_name}
                        label={vendor.vendor_name}
                      >
                        <div style={{ lineHeight: 1.4 }}>
                          <div>{vendor.vendor_name}</div>
                          {(vendor.role || vendor.vendor_business_type) && (
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              {[vendor.role, vendor.vendor_business_type].filter(Boolean).join(' / ')}
                            </Text>
                          )}
                        </div>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="contact_note" label="聯絡備註">
                  <Input />
                </Form.Item>
              </Col>
            </Row>

            {/* 第四行：雲端資料夾 + 專案資料夾 */}
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="cloud_folder" label="雲端資料夾">
                  <Input placeholder="Google Drive 連結" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="project_folder" label="專案資料夾">
                  <Input placeholder="本地路徑" />
                </Form.Item>
              </Col>
            </Row>

            {/* 公文關聯區塊 - 自動帶入當前公文 */}
            <Divider style={{ margin: '16px 0' }} />
            <div style={{ marginBottom: 16 }}>
              <Space>
                <FileTextOutlined />
                <span style={{ fontWeight: 500 }}>公文關聯</span>
                <Tag color={isReceiveDoc ? 'blue' : 'green'}>
                  {isReceiveDoc ? '收文' : '發文'}
                </Tag>
              </Space>
            </div>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  label="機關函文號"
                  tooltip={isReceiveDoc ? '自動帶入當前公文文號' : '如需關聯機關函文，請至派工紀錄編輯'}
                >
                  <Input
                    value={isReceiveDoc ? document?.doc_number : undefined}
                    disabled
                    style={{ backgroundColor: '#f5f5f5' }}
                    placeholder={isReceiveDoc ? '' : '(非機關來函)'}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="乾坤函文號"
                  tooltip={!isReceiveDoc ? '自動帶入當前公文文號' : '如需關聯乾坤函文，請至派工紀錄編輯'}
                >
                  <Input
                    value={!isReceiveDoc ? document?.doc_number : undefined}
                    disabled
                    style={{ backgroundColor: '#f5f5f5' }}
                    placeholder={!isReceiveDoc ? '' : '(非乾坤發文)'}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item style={{ marginBottom: 0, marginTop: 16 }}>
              <Space>
                <Button
                  type="primary"
                  onClick={async () => {
                    try {
                      const values = await dispatchForm.validateFields();
                      await onCreateDispatch(values);
                      dispatchForm.resetFields();
                    } catch (error) {
                      // 表單驗證失敗，不做額外處理
                    }
                  }}
                >
                  建立派工
                </Button>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  或點擊右上角「儲存」按鈕一併建立
                </Text>
              </Space>
            </Form.Item>
          </Card>
        )}
      </Form>

      {/* 關聯已有派工 - 編輯模式才顯示 */}
      {isEditing && (
        <Card
          size="small"
          title={
            <Space>
              <LinkOutlined />
              <span>關聯已有派工</span>
            </Space>
          }
          style={{ marginTop: 16 }}
        >
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Select
                showSearch
                allowClear
                placeholder="搜尋並選擇已有的派工紀錄"
                value={selectedDispatchId}
                onChange={setSelectedDispatchId}
                filterOption={(input, option) =>
                  String(option?.label || '').toLowerCase().includes(input.toLowerCase())
                }
                style={{ width: '100%' }}
                notFoundContent={filteredDispatches.length === 0 ? '無可關聯的派工紀錄' : '輸入關鍵字搜尋'}
                options={filteredDispatches.map((dispatch: DispatchOrder) => ({
                  value: dispatch.id,
                  label: `${dispatch.dispatch_no} - ${dispatch.project_name || '(無工程名稱)'} ${dispatch.work_type ? `- ${dispatch.work_type}` : ''}`,
                }))}
              />
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<LinkOutlined />}
                onClick={handleLinkExistingDispatch}
                loading={linkingDispatch}
                disabled={!selectedDispatchId}
              >
                關聯
              </Button>
            </Col>
          </Row>
          <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
            提示：選擇已存在的派工紀錄進行關聯，該派工的「{isReceiveDoc ? '機關函文號' : '乾坤函文號'}」將自動更新為當前公文文號
          </div>
        </Card>
      )}

      {/* 非編輯模式提示 */}
      {!isEditing && dispatchLinks.length === 0 && (
        <Empty
          description="此公文尚無關聯派工"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Text type="secondary">點擊右上方「編輯」按鈕可新增派工關聯</Text>
        </Empty>
      )}
    </Spin>
  );
};

export default DocumentDispatchTab;
