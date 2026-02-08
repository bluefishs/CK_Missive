/**
 * 桃園轄管工程新增頁面
 *
 * 導航式新增頁面，提供完整表單讓使用者建立新工程
 * 欄位對應 Excel「1.轄管工程清單」工作表
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContent } from '../components/common';
import {
  Form,
  Input,
  Select,
  Button,
  App,
  Card,
  InputNumber,
  DatePicker,
  Typography,
  Space,
  Divider,
} from 'antd';
import { ResponsiveFormRow } from '../components/common/ResponsiveFormRow';
import {
  ProjectOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  EnvironmentOutlined,
  HomeOutlined,
  DollarOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { taoyuanProjectsApi } from '../api/taoyuanDispatchApi';
import { getProjectAgencyContacts, type ProjectAgencyContact } from '../api/projectAgencyContacts';
import { projectVendorsApi, type ProjectVendor } from '../api/projectVendorsApi';
import type { TaoyuanProjectCreate } from '../types/api';
import {
  CASE_TYPE_OPTIONS,
  DISTRICT_OPTIONS,
  TAOYUAN_CONTRACT,
} from '../constants/taoyuanOptions';

const { Title, Text } = Typography;
const { Option } = Select;

export const TaoyuanProjectCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 查詢機關承辦清單（來自承攬案件 /contract-cases/21）
  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => getProjectAgencyContacts(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const agencyContacts = agencyContactsData?.items ?? [];

  // 查詢協力廠商清單（用於查估單位，來自承攬案件）
  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => projectVendorsApi.getProjectVendors(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const projectVendors = vendorsData?.associations ?? [];

  // 新增 mutation
  const createMutation = useMutation({
    mutationFn: (data: TaoyuanProjectCreate) => taoyuanProjectsApi.create(data),
    onSuccess: (result) => {
      message.success('工程新增成功');
      queryClient.invalidateQueries({ queryKey: ['taoyuan-projects'] });
      // 導航到新建立的工程詳情頁
      navigate(`/taoyuan/project/${result.id}`);
    },
    onError: (error: Error) => {
      message.error(error?.message || '新增失敗');
    },
  });

  // 儲存
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const data: TaoyuanProjectCreate = {
        ...values,
        contract_project_id: TAOYUAN_CONTRACT.PROJECT_ID,
        completion_date: values.completion_date?.format('YYYY-MM-DD') || null,
      };
      createMutation.mutate(data);
    } catch {
      message.error('請檢查表單欄位');
    }
  };

  // 返回列表
  const handleCancel = () => {
    navigate('/taoyuan/dispatch');
  };

  return (
    <ResponsiveContent maxWidth={1200} padding="medium" centered>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={handleCancel}>
              返回
            </Button>
            <Title level={4} style={{ margin: 0 }}>
              <ProjectOutlined /> 新增轄管工程
            </Title>
          </Space>
          <Space>
            <Button onClick={handleCancel}>取消</Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={createMutation.isPending}
              disabled={createMutation.isPending}
              onClick={handleSave}
            >
              儲存
            </Button>
          </Space>
        </div>
      </Card>

      <Form form={form} layout="vertical">
        {/* 基本資訊 */}
        <Card
          title={
            <Space>
              <ProjectOutlined />
              <span>基本資訊</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Form.Item
            name="project_name"
            label="工程名稱"
            rules={[{ required: true, message: '請輸入工程名稱' }]}
          >
            <Input placeholder="請輸入工程名稱" />
          </Form.Item>
          <ResponsiveFormRow>
            <Form.Item name="review_year" label="審議年度">
              <InputNumber style={{ width: '100%' }} placeholder="例: 115" />
            </Form.Item>
            <Form.Item name="case_type" label="案件類型">
              <Select placeholder="選擇案件類型" allowClear>
                {CASE_TYPE_OPTIONS.map((opt) => (
                  <Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="district" label="行政區">
              <Select placeholder="選擇行政區" allowClear showSearch>
                {DISTRICT_OPTIONS.map((opt) => (
                  <Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="sub_case_name" label="分案名稱">
              <Input />
            </Form.Item>
          </ResponsiveFormRow>
          <ResponsiveFormRow>
            <Form.Item
              name="case_handler"
              label="案件承辦"
              tooltip="從機關承辦清單選擇（來源：承攬案件機關承辦）"
            >
              <Select
                placeholder="選擇案件承辦"
                allowClear
                showSearch
                optionFilterProp="label"
              >
                {agencyContacts.map((contact) => (
                  <Option
                    key={contact.id}
                    value={contact.contact_name}
                    label={contact.contact_name}
                  >
                    {contact.contact_name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item
              name="survey_unit"
              label="查估單位"
              tooltip="從協力廠商清單選擇（來源：承攬案件協力廠商）"
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
                    {vendor.vendor_name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="proposer" label="提案人">
              <Input />
            </Form.Item>
          </ResponsiveFormRow>
        </Card>

        {/* 工程範圍 */}
        <Card
          title={
            <Space>
              <EnvironmentOutlined />
              <span>工程範圍</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <ResponsiveFormRow>
            <Form.Item name="start_point" label="工程起點">
              <Input placeholder="例: 永安路與中山路口" />
            </Form.Item>
            <Form.Item name="start_coordinate" label="起點坐標(經緯度)">
              <Input placeholder="例: 24.9876,121.1234" />
            </Form.Item>
          </ResponsiveFormRow>
          <ResponsiveFormRow>
            <Form.Item name="end_point" label="工程迄點">
              <Input placeholder="例: 永安路與民生路口" />
            </Form.Item>
            <Form.Item name="end_coordinate" label="迄點坐標(經緯度)">
              <Input placeholder="例: 24.9888,121.1256" />
            </Form.Item>
          </ResponsiveFormRow>
          <ResponsiveFormRow>
            <Form.Item name="road_length" label="道路長度(公尺)">
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>
            <Form.Item name="current_width" label="現況路寬(公尺)">
              <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
            </Form.Item>
            <Form.Item name="planned_width" label="計畫路寬(公尺)">
              <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
            </Form.Item>
          </ResponsiveFormRow>
          <Form.Item name="urban_plan" label="都市計畫">
            <Input />
          </Form.Item>
        </Card>

        {/* 土地建物 */}
        <Card
          title={
            <Space>
              <HomeOutlined />
              <span>土地建物</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <ResponsiveFormRow>
            <Form.Item name="public_land_count" label="公有土地(筆)">
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>
            <Form.Item name="private_land_count" label="私有土地(筆)">
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>
            <Form.Item name="rc_count" label="RC數量(棟)">
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>
            <Form.Item name="iron_sheet_count" label="鐵皮屋數量(棟)">
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>
          </ResponsiveFormRow>
        </Card>

        {/* 經費估算 */}
        <Card
          title={
            <Space>
              <DollarOutlined />
              <span>經費估算</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <ResponsiveFormRow>
            <Form.Item name="construction_cost" label="工程費(元)">
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              />
            </Form.Item>
            <Form.Item name="land_cost" label="用地費(元)">
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              />
            </Form.Item>
            <Form.Item name="compensation_cost" label="補償費(元)">
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              />
            </Form.Item>
            <Form.Item name="total_cost" label="總經費(元)">
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              />
            </Form.Item>
          </ResponsiveFormRow>
        </Card>

        {/* 審議狀態 */}
        <Card
          title={
            <Space>
              <FileTextOutlined />
              <span>審議狀態</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <ResponsiveFormRow>
            <Form.Item name="review_result" label="審議結果">
              <Input />
            </Form.Item>
            <Form.Item name="completion_date" label="完工日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </ResponsiveFormRow>
          <Form.Item name="remark" label="備註">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Card>

        {/* 底部操作按鈕 */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button onClick={handleCancel}>取消</Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={createMutation.isPending}
              disabled={createMutation.isPending}
              onClick={handleSave}
            >
              儲存並查看
            </Button>
          </div>
        </Card>
      </Form>
    </ResponsiveContent>
  );
};

export default TaoyuanProjectCreatePage;
