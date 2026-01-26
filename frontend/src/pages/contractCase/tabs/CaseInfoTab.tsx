/**
 * 案件資訊 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Progress,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
} from 'antd';
import { EditOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { CaseInfoTabProps } from './types';
import {
  CATEGORY_OPTIONS,
  CASE_NATURE_OPTIONS,
  STATUS_OPTIONS,
} from './constants';

const { Text } = Typography;
const { Option } = Select;

// 輔助函數
const getStatusTagColor = (status?: string) => {
  const statusOption = STATUS_OPTIONS.find(s => s.value === status);
  return statusOption?.color || 'default';
};

const getStatusTagText = (status?: string) => {
  const statusOption = STATUS_OPTIONS.find(s => s.value === status);
  return statusOption?.label || status || '未設定';
};

const getCategoryTagColor = (category?: string) => {
  const categoryOption = CATEGORY_OPTIONS.find(c => c.value === category);
  return categoryOption?.color || 'default';
};

const getCategoryTagText = (category?: string) => {
  const categoryOption = CATEGORY_OPTIONS.find(c => c.value === category);
  return categoryOption?.label || category || '未分類';
};

const getCaseNatureTagColor = (caseNature?: string) => {
  const option = CASE_NATURE_OPTIONS.find(c => c.value === caseNature);
  return option?.color || 'default';
};

const getCaseNatureTagText = (caseNature?: string) => {
  const option = CASE_NATURE_OPTIONS.find(c => c.value === caseNature);
  return option?.label || caseNature || '未設定';
};

const formatAmount = (amount?: number) => {
  if (!amount) return '-';
  return new Intl.NumberFormat('zh-TW').format(amount);
};

export const CaseInfoTab: React.FC<CaseInfoTabProps> = ({
  data,
  isEditing,
  setIsEditing,
  form,
  onSave,
  calculateProgress,
}) => {
  const progress = calculateProgress();

  const startEdit = () => {
    const dateRange = (data.start_date && data.end_date)
      ? [dayjs(data.start_date), dayjs(data.end_date)]
      : undefined;

    form.setFieldsValue({
      project_name: data.project_name,
      year: data.year,
      client_agency: data.client_agency,
      contract_doc_number: data.contract_doc_number,
      project_code: data.project_code,
      category: data.category,
      case_nature: data.case_nature,
      contract_amount: data.contract_amount,
      winning_amount: data.winning_amount,
      date_range: dateRange,
      status: data.status,
      progress: data.progress,
      project_path: data.project_path,
      notes: data.notes,
    });
    setIsEditing(true);
  };

  return (
    <div>
      {/* 進度顯示 */}
      <Card title="執行進度" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={18}>
            <Progress
              percent={data.progress ?? progress}
              status={data.status === '已結案' ? 'success' : data.status === '暫停' ? 'exception' : 'active'}
            />
          </Col>
          <Col span={6} style={{ textAlign: 'right' }}>
            <div>完成度: {data.progress ?? progress}%</div>
            <div style={{ color: '#666', fontSize: '12px' }}>
              {data.progress !== undefined ? '手動設定' : '根據契約期程計算'}
            </div>
          </Col>
        </Row>
      </Card>

      {/* 基本資訊 */}
      <Card
        title="基本資訊"
        style={{ marginBottom: 16 }}
        extra={
          isEditing ? (
            <Space>
              <Button size="small" onClick={() => setIsEditing(false)}>取消</Button>
              <Button size="small" type="primary" onClick={() => form.submit()}>儲存</Button>
            </Space>
          ) : (
            <Button size="small" icon={<EditOutlined />} onClick={startEdit}>編輯</Button>
          )
        }
      >
        {isEditing ? (
          <Form form={form} layout="vertical" onFinish={onSave}>
            <Row gutter={16}>
              <Col span={24}>
                <Form.Item name="project_name" label="案件名稱" rules={[{ required: true, message: '請輸入案件名稱' }]}>
                  <Input placeholder="請輸入案件名稱" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="year" label="年度" rules={[{ required: true, message: '請選擇年度' }]}>
                  <InputNumber style={{ width: '100%' }} min={2020} max={2050} placeholder="西元年" />
                </Form.Item>
              </Col>
              <Col span={18}>
                <Form.Item name="client_agency" label="委託單位">
                  <Input placeholder="請輸入委託單位" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="contract_doc_number" label="契約文號">
                  <Input placeholder="請輸入契約文號" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="project_code"
                  label="專案編號"
                  tooltip="格式: CK{年度6碼}_{類別2碼}_{性質2碼}_{流水號3碼}"
                >
                  <Input placeholder="留空自動產生" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="category" label="案件類別">
                  <Select placeholder="請選擇案件類別">
                    {CATEGORY_OPTIONS.map(opt => (
                      <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="case_nature" label="案件性質">
                  <Select placeholder="請選擇案件性質">
                    {CASE_NATURE_OPTIONS.map(opt => (
                      <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="contract_amount" label="契約金額">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="請輸入契約金額"
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
                    addonBefore="NT$"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="winning_amount" label="得標金額">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="請輸入得標金額"
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
                    addonBefore="NT$"
                  />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="date_range" label="契約期程">
                  <DatePicker.RangePicker
                    style={{ width: '100%' }}
                    placeholder={['開始日期', '結束日期']}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="status" label="執行狀態">
                  <Select placeholder="請選擇執行狀態">
                    {STATUS_OPTIONS.map(opt => (
                      <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="progress" label="完成進度 (%)" tooltip="當狀態設為「已結案」時，進度自動設為 100%">
                  <InputNumber style={{ width: '100%' }} min={0} max={100} placeholder="0-100" />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="project_path" label="專案路徑">
                  <Input placeholder="請輸入專案資料夾路徑 (可選)" />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="notes" label="備註">
                  <Input.TextArea rows={3} placeholder="請輸入備註說明" />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        ) : (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="案件名稱" span={2}>
              <Text strong>{data.project_name}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="年度">{data.year}年</Descriptions.Item>
            <Descriptions.Item label="委託單位">{data.client_agency || '-'}</Descriptions.Item>
            <Descriptions.Item label="契約文號">{data.contract_doc_number || '-'}</Descriptions.Item>
            <Descriptions.Item label="專案編號">
              {data.project_code ? <Text code>{data.project_code}</Text> : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="案件類別">
              <Tag color={getCategoryTagColor(data.category)}>
                {getCategoryTagText(data.category)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="案件性質">
              <Tag color={getCaseNatureTagColor(data.case_nature)}>
                {getCaseNatureTagText(data.case_nature)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="契約金額">
              {data.contract_amount ? `NT$ ${formatAmount(data.contract_amount)}` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="得標金額">
              {data.winning_amount ? `NT$ ${formatAmount(data.winning_amount)}` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="開始日期">
              {data.start_date ? dayjs(data.start_date).format('YYYY/MM/DD') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="結束日期">
              {data.end_date ? dayjs(data.end_date).format('YYYY/MM/DD') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="執行狀態">
              <Tag color={getStatusTagColor(data.status)}>
                {getStatusTagText(data.status)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="完成進度">
              {data.progress !== undefined ? `${data.progress}%` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="專案路徑" span={2}>
              {data.project_path ? <Text type="secondary">{data.project_path}</Text> : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="備註" span={2}>
              {data.notes || '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      {/* 專案說明 */}
      {!isEditing && data.description && (
        <Card title="專案說明" style={{ marginBottom: 16 }}>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{data.description}</div>
        </Card>
      )}
    </div>
  );
};

export default CaseInfoTab;
