/**
 * 承攬案件表單頁面
 *
 * RWD 優化版本
 * @version 1.2.0
 * @date 2026-01-26
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Spin,
  App,
  Modal,
  Divider,
  Alert,
} from 'antd';
import { logger } from '../utils/logger';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  PlusOutlined,
  BankOutlined,
} from '@ant-design/icons';
import debounce from 'lodash/debounce';
import { useParams, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { ROUTES } from '../router/types';
import { useResponsive } from '../hooks';
import { queryKeys } from '../config/queryConfig';

// API 服務
import { projectsApi } from '../api/projectsApi';
import { agenciesApi } from '../api/agenciesApi';
import { vendorsApi } from '../api/vendorsApi';
import { usersApi } from '../api/usersApi';
import type { AgencyOption, VendorOption, UserOption, Project } from '../types/api';

// 從 contractCase tabs 導入統一的常數
import {
  CATEGORY_OPTIONS,
  CASE_NATURE_OPTIONS,
  STATUS_OPTIONS,
} from './contractCase/tabs/constants';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

export const ContractCaseFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // 下拉選單選項狀態
  const [agencyOptions, setAgencyOptions] = useState<AgencyOption[]>([]);
  const [vendorOptions, setVendorOptions] = useState<VendorOption[]>([]);
  const [userOptions, setUserOptions] = useState<UserOption[]>([]);
  const [optionsLoading, setOptionsLoading] = useState(false);

  // 新增機關 Modal 狀態
  const [addAgencyModalVisible, setAddAgencyModalVisible] = useState(false);
  const [addAgencyForm] = Form.useForm();
  const [addAgencySubmitting, setAddAgencySubmitting] = useState(false);
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);

  // RWD 響應式
  const { isMobile } = useResponsive();

  const isEdit = Boolean(id);
  const title = isEdit ? '編輯承攬案件' : '新增承攬案件';

  // 載入下拉選單選項
  useEffect(() => {
    loadOptions();
  }, []);

  // 編輯模式載入資料
  useEffect(() => {
    if (isEdit && id) {
      loadData();
    }
  }, [id, isEdit]);

  const loadOptions = async () => {
    setOptionsLoading(true);
    try {
      const [agencies, vendors, users] = await Promise.all([
        agenciesApi.getAgencyOptions(),
        vendorsApi.getVendorOptions(),
        usersApi.getUserOptions(true), // 只取啟用的用戶
      ]);
      setAgencyOptions(agencies);
      setVendorOptions(vendors);
      setUserOptions(users);
    } catch (error) {
      logger.error('載入選項失敗:', error);
      message.error('載入選項失敗，部分下拉選單可能無法使用');
    } finally {
      setOptionsLoading(false);
    }
  };

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await projectsApi.getProject(parseInt(id, 10));

      // 設置表單值
      form.setFieldsValue({
        project_name: data.project_name,
        year: data.year,
        client_agency: data.client_agency,
        category: data.category,
        case_nature: data.case_nature,
        status: data.status,
        contract_doc_number: data.contract_doc_number,
        contract_amount: data.contract_amount,
        winning_amount: data.winning_amount,
        contract_period: (data.start_date && data.end_date)
          ? [dayjs(data.start_date), dayjs(data.end_date)]
          : undefined,
        progress: data.progress,
        project_path: data.project_path,
        notes: data.notes,
        description: data.description,
      });
    } catch (error) {
      logger.error('載入數據失敗:', error);
      message.error('載入數據失敗');
    } finally {
      setLoading(false);
    }
  };

  interface FormValues {
    project_name: string;
    year?: number;
    client_agency?: string;
    category?: string;
    case_nature?: string;
    status?: 'pending' | 'in_progress' | 'completed' | 'suspended';
    contract_doc_number?: string;
    contract_amount?: number;
    winning_amount?: number;
    contract_period?: [{ format: (fmt: string) => string }, { format: (fmt: string) => string }];
    progress?: number;
    project_path?: string;
    notes?: string;
    description?: string;
  }

  const handleSubmit = async (values: FormValues) => {
    setSubmitting(true);
    try {
      // 處理日期範圍
      const contractPeriod = values.contract_period;
      const startDate = contractPeriod?.[0];
      const endDate = contractPeriod?.[1];
      const submitData = {
        project_name: values.project_name,
        year: values.year,
        client_agency: values.client_agency,
        category: values.category,
        case_nature: values.case_nature,
        status: values.status,
        contract_doc_number: values.contract_doc_number,
        contract_amount: values.contract_amount,
        winning_amount: values.winning_amount,
        start_date: startDate ? startDate.format('YYYY-MM-DD') : undefined,
        end_date: endDate ? endDate.format('YYYY-MM-DD') : undefined,
        progress: values.progress,
        project_path: values.project_path,
        notes: values.notes,
        description: values.description,
      };

      logger.debug('Submitting data:', submitData);

      if (isEdit && id) {
        await projectsApi.updateProject(parseInt(id, 10), submitData);
        queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        message.success('更新成功');
      } else {
        const result = await projectsApi.createProject(submitData);
        queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        message.success('新增成功');
        // 新增成功後導航到詳情頁
        navigate(`${ROUTES.CONTRACT_CASES}/${result.id}`);
        return;
      }
      navigate(ROUTES.CONTRACT_CASES);
    } catch (error: unknown) {
      logger.error('提交失敗:', error);
      const errorMsg = error instanceof Error ? error.message : '操作失敗';
      message.error(isEdit ? `更新失敗: ${errorMsg}` : `新增失敗: ${errorMsg}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleBack = () => {
    navigate(ROUTES.CONTRACT_CASES);
  };

  // 生成年度選項
  const generateYearOptions = () => {
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let i = currentYear - 2; i <= currentYear + 2; i++) {
      years.push(i.toString());
    }
    return years;
  };

  // 檢查機關名稱是否重複（防呆）
  const checkAgencyDuplicate = useCallback(
    debounce(async (name: string) => {
      if (!name || name.length < 2) {
        setDuplicateWarning(null);
        return;
      }

      // 在現有選項中搜尋相似名稱
      const lowerName = name.toLowerCase();
      const similar = agencyOptions.filter(
        (a) =>
          a.agency_name.toLowerCase().includes(lowerName) ||
          lowerName.includes(a.agency_name.toLowerCase()) ||
          (a.agency_short_name && a.agency_short_name.toLowerCase().includes(lowerName))
      );

      if (similar.length > 0) {
        const names = similar.slice(0, 3).map((a) => a.agency_name).join('、');
        setDuplicateWarning(`已有相似機關：${names}`);
      } else {
        setDuplicateWarning(null);
      }
    }, 300),
    [agencyOptions]
  );

  // 處理新增機關名稱輸入
  const handleAgencyNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    checkAgencyDuplicate(e.target.value);
  };

  // 新增機關提交
  const handleAddAgencySubmit = async () => {
    try {
      const values = await addAgencyForm.validateFields();

      // 最終重複檢查
      const exactMatch = agencyOptions.find(
        (a) => a.agency_name.toLowerCase() === values.agency_name.toLowerCase()
      );
      if (exactMatch) {
        message.error(`機關「${exactMatch.agency_name}」已存在，請直接選擇`);
        return;
      }

      setAddAgencySubmitting(true);

      // 呼叫 API 建立機關
      const newAgency = await agenciesApi.createAgency({
        agency_name: values.agency_name,
        agency_short_name: values.agency_short_name || undefined,
        agency_type: values.agency_type || '政府機關',
      });

      message.success(`機關「${newAgency.agency_name}」建立成功`);
      queryClient.invalidateQueries({ queryKey: queryKeys.agencies.all });

      // 刷新選項列表
      const updatedAgencies = await agenciesApi.getAgencyOptions();
      setAgencyOptions(updatedAgencies);

      // 自動選中新建的機關
      form.setFieldValue('client_agency', newAgency.agency_name);

      // 關閉 Modal 並重置表單
      setAddAgencyModalVisible(false);
      addAgencyForm.resetFields();
      setDuplicateWarning(null);
    } catch (error: unknown) {
      logger.error('新增機關失敗:', error);
      const errorMsg = error instanceof Error ? error.message : '新增失敗';
      message.error(`新增機關失敗: ${errorMsg}`);
    } finally {
      setAddAgencySubmitting(false);
    }
  };

  // 開啟新增機關 Modal
  const openAddAgencyModal = () => {
    addAgencyForm.resetFields();
    setDuplicateWarning(null);
    setAddAgencyModalVisible(true);
  };

  if (loading) {
    return (
      <div style={{
        textAlign: 'center',
        padding: isMobile ? 24 : 50
      }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: isMobile ? '12px' : undefined }}>
      {/* 頁面標題 - RWD 響應式 */}
      <Card
        style={{ marginBottom: isMobile ? 12 : 16 }}
        size={isMobile ? 'small' : 'default'}
      >
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: isMobile ? 8 : 16
        }}>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
            size={isMobile ? 'small' : 'middle'}
          >
            {isMobile ? '返回' : '返回列表'}
          </Button>
          <Title level={isMobile ? 4 : 3} style={{ margin: 0 }}>
            {title}
          </Title>
        </div>
      </Card>

      {/* 表單 */}
      <Card
        size={isMobile ? 'small' : 'default'}
        styles={{
          body: { padding: isMobile ? 12 : 24 }
        }}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          size={isMobile ? 'middle' : 'large'}
          initialValues={{
            year: new Date().getFullYear(),
            status: '待執行',
          }}
        >
          <Spin spinning={optionsLoading} tip="載入選項中...">
          <Row gutter={[isMobile ? 8 : 16, 0]}>
            {/* 第一行：專案名稱（全寬） */}
            <Col span={24}>
              <Form.Item
                label="案件名稱"
                name="project_name"
                rules={[{ required: true, message: '請輸入案件名稱' }]}
              >
                <Input placeholder="請輸入案件名稱" />
              </Form.Item>
            </Col>

            {/* 第二行：年度、案件類別、案件性質 */}
            <Col xs={24} sm={8}>
              <Form.Item
                label="年度"
                name="year"
                rules={[{ required: true, message: '請選擇年度' }]}
              >
                <Select placeholder="請選擇年度">
                  {generateYearOptions().map(year => (
                    <Option key={year} value={parseInt(year)}>
                      {year}年
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item
                label="案件類別"
                name="category"
              >
                <Select placeholder="請選擇案件類別" allowClear>
                  {CATEGORY_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item
                label="案件性質"
                name="case_nature"
              >
                <Select placeholder="請選擇案件性質" allowClear>
                  {CASE_NATURE_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            {/* 第三行：委託單位（下拉選單 + 新增功能）、案件狀態 */}
            <Col xs={24} sm={12}>
              <Form.Item
                label="委託單位"
                name="client_agency"
                tooltip="從機關單位清單中選擇，或點擊下方新增"
              >
                <Select
                  placeholder="請選擇委託單位"
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  options={agencyOptions.map(agency => ({
                    value: agency.agency_name,
                    label: agency.agency_short_name
                      ? `${agency.agency_name} (${agency.agency_short_name})`
                      : agency.agency_name,
                  }))}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      <Divider style={{ margin: '8px 0' }} />
                      <Button
                        type="text"
                        icon={<PlusOutlined />}
                        onClick={openAddAgencyModal}
                        style={{ width: '100%', textAlign: 'left', color: '#1890ff' }}
                      >
                        新增機關單位
                      </Button>
                    </>
                  )}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label="執行狀態"
                name="status"
                rules={[{ required: true, message: '請選擇執行狀態' }]}
              >
                <Select placeholder="請選擇執行狀態">
                  {STATUS_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            {/* 第四行：契約期程 */}
            <Col xs={24} sm={16}>
              <Form.Item
                label="契約期程"
                name="contract_period"
              >
                <RangePicker
                  style={{ width: '100%' }}
                  placeholder={['開始日期', '結束日期']}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item
                label="完成進度 (%)"
                name="progress"
                tooltip="0-100，可留空"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  max={100}
                  placeholder="0-100"
                />
              </Form.Item>
            </Col>

            {/* 第五行：契約金額、得標金額 */}
            <Col xs={24} sm={12}>
              <Form.Item
                label="契約金額"
                name="contract_amount"
              >
                <InputNumber<number>
                  style={{ width: '100%' }}
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(value) => Number(value!.replace(/\$\s?|(,*)/g, ''))}
                  placeholder="請輸入契約金額"
                  min={0}
                  addonBefore="NT$"
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label="得標金額"
                name="winning_amount"
              >
                <InputNumber<number>
                  style={{ width: '100%' }}
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(value) => Number(value!.replace(/\$\s?|(,*)/g, ''))}
                  placeholder="請輸入得標金額"
                  min={0}
                  addonBefore="NT$"
                />
              </Form.Item>
            </Col>

            {/* 第六行：契約文號、專案路徑 */}
            <Col xs={24} sm={12}>
              <Form.Item
                label="契約文號"
                name="contract_doc_number"
              >
                <Input placeholder="請輸入契約文號" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label="專案路徑"
                name="project_path"
              >
                <Input placeholder="請輸入專案資料夾路徑 (可選)" />
              </Form.Item>
            </Col>

            {/* 第七行：案件說明 */}
            <Col span={24}>
              <Form.Item
                label="專案說明"
                name="description"
              >
                <TextArea
                  rows={isMobile ? 3 : 4}
                  placeholder="請輸入專案說明"
                />
              </Form.Item>
            </Col>

            {/* 第八行：備註 */}
            <Col span={24}>
              <Form.Item
                label="備註"
                name="notes"
              >
                <TextArea
                  rows={isMobile ? 2 : 3}
                  placeholder="請輸入備註"
                />
              </Form.Item>
            </Col>

            {/* 操作按鈕 - RWD 響應式 */}
            <Col span={24}>
              <Form.Item style={{ marginBottom: 0 }}>
                {isMobile ? (
                  // 手機版: 按鈕堆疊
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Button
                      type="primary"
                      htmlType="submit"
                      icon={<SaveOutlined />}
                      loading={submitting}
                      block
                    >
                      {isEdit ? '更新' : '新增'}
                    </Button>
                    <Button onClick={handleBack} block>
                      取消
                    </Button>
                  </Space>
                ) : (
                  // 桌面版: 按鈕並排
                  <Space>
                    <Button
                      type="primary"
                      htmlType="submit"
                      icon={<SaveOutlined />}
                      loading={submitting}
                    >
                      {isEdit ? '更新' : '新增'}
                    </Button>
                    <Button onClick={handleBack}>
                      取消
                    </Button>
                  </Space>
                )}
              </Form.Item>
            </Col>
          </Row>
          </Spin>
        </Form>
      </Card>

      {/* 新增機關 Modal */}
      <Modal
        title={
          <Space>
            <BankOutlined />
            <span>新增機關單位</span>
          </Space>
        }
        open={addAgencyModalVisible}
        onCancel={() => {
          setAddAgencyModalVisible(false);
          addAgencyForm.resetFields();
          setDuplicateWarning(null);
        }}
        onOk={handleAddAgencySubmit}
        confirmLoading={addAgencySubmitting}
        okText="建立"
        cancelText="取消"
        width={isMobile ? '95%' : 500}
        forceRender
      >
        <Form
          form={addAgencyForm}
          layout="vertical"
          style={{ marginTop: 16 }}
        >
          <Form.Item
            label="機關名稱"
            name="agency_name"
            rules={[
              { required: true, message: '請輸入機關名稱' },
              { min: 2, message: '機關名稱至少 2 個字' },
            ]}
            help={duplicateWarning && (
              <span style={{ color: '#faad14' }}>{duplicateWarning}</span>
            )}
            validateStatus={duplicateWarning ? 'warning' : undefined}
          >
            <Input
              placeholder="請輸入完整機關名稱"
              onChange={handleAgencyNameChange}
              maxLength={100}
              showCount
            />
          </Form.Item>

          <Form.Item
            label="機關簡稱"
            name="agency_short_name"
            tooltip="例如：國土署、地政局"
          >
            <Input
              placeholder="請輸入機關簡稱（選填）"
              maxLength={50}
            />
          </Form.Item>

          <Form.Item
            label="機關類型"
            name="agency_type"
            initialValue="政府機關"
          >
            <Select>
              <Option value="政府機關">政府機關</Option>
              <Option value="國營事業">國營事業</Option>
              <Option value="學術機構">學術機構</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Form.Item>

          {duplicateWarning && (
            <Alert
              message="提示"
              description="系統偵測到可能重複的機關，請確認是否需要新增。如果是同一機關，建議直接從下拉選單中選擇。"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default ContractCaseFormPage;