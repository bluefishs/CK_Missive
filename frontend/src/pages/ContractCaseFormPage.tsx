import React, { useState, useEffect } from 'react';
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
  message,
  Spin,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import {
  ContractCase,
  ContractCaseType,
  ContractCaseStatus,
  CONTRACT_CASE_TYPE_LABELS,
  CONTRACT_CASE_STATUS_LABELS,
} from '../types/contractCase';
import { ROUTES } from '../router/types';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

// 模擬現有數據（編輯時使用）
const mockExistingData: ContractCase = {
  id: 1,
  year: '2024',
  project_name: '數位測繪技術創新專案',
  client_unit: '內政部國土測繪中心',
  contract_period_start: '2024-01-15',
  contract_period_end: '2024-12-31',
  responsible_staff: '王小明',
  partner_vendor: '精密測量科技有限公司',
  case_type: ContractCaseType.INNOVATION,
  case_status: ContractCaseStatus.IN_PROGRESS,
  contract_amount: 5000000,
  description: '開發新一代數位測繪技術，包含點雲資料處理、三維建模、精度驗證等功能模組。',
  notes: '需要配合新採購的測繪設備進行整合測試。',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

export const ContractCaseFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  const isEdit = Boolean(id);
  const title = isEdit ? '編輯承攬案件' : '新增承攬案件';

  useEffect(() => {
    if (isEdit) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    setLoading(true);
    try {
      // 模擬API調用
      await new Promise(resolve => setTimeout(resolve, 500));
      // 這裡未來會替換為真實的API調用
      const data = mockExistingData;
      
      form.setFieldsValue({
        ...data,
        contract_period: [
          dayjs(data.contract_period_start),
          dayjs(data.contract_period_end)
        ],
      });
    } catch (error) {
      message.error('載入數據失敗');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      // 處理日期範圍
      const [startDate, endDate] = values.contract_period || [];
      const submitData = {
        ...values,
        contract_period_start: startDate ? startDate.format('YYYY-MM-DD') : '',
        contract_period_end: endDate ? endDate.format('YYYY-MM-DD') : '',
      };
      delete submitData.contract_period;

      // 模擬API調用
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 這裡未來會替換為真實的API調用
      console.log('Submitting data:', submitData);
      
      message.success(isEdit ? '更新成功' : '新增成功');
      navigate(ROUTES.CONTRACT_CASES);
    } catch (error) {
      message.error(isEdit ? '更新失敗' : '新增失敗');
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

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      {/* 頁面標題 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Button 
            type="text" 
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
          >
            返回
          </Button>
          <Title level={3} style={{ margin: 0 }}>
            {title}
          </Title>
        </div>
      </Card>

      {/* 表單 */}
      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            year: new Date().getFullYear().toString(),
            case_status: ContractCaseStatus.PLANNED,
          }}
        >
          <Row gutter={[16, 0]}>
            {/* 第一行：專案名稱（全寬） */}
            <Col span={24}>
              <Form.Item
                label="專案名稱"
                name="project_name"
                rules={[{ required: true, message: '請輸入專案名稱' }]}
              >
                <Input placeholder="請輸入專案名稱" />
              </Form.Item>
            </Col>

            {/* 第二行：年度、案件性質 */}
            <Col xs={24} sm={12}>
              <Form.Item
                label="年度別"
                name="year"
                rules={[{ required: true, message: '請選擇年度' }]}
              >
                <Select placeholder="請選擇年度">
                  {generateYearOptions().map(year => (
                    <Option key={year} value={year}>
                      {year}年
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label="案件性質"
                name="case_type"
                rules={[{ required: true, message: '請選擇案件性質' }]}
              >
                <Select placeholder="請選擇案件性質">
                  {Object.entries(CONTRACT_CASE_TYPE_LABELS).map(([key, label]) => (
                    <Option key={key} value={parseInt(key)}>
                      {label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            {/* 第三行：委託單位、案件狀態 */}
            <Col xs={24} sm={12}>
              <Form.Item
                label="委託單位"
                name="client_unit"
                rules={[{ required: true, message: '請輸入委託單位' }]}
              >
                <Input placeholder="請輸入委託單位" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label="案件狀態"
                name="case_status"
                rules={[{ required: true, message: '請選擇案件狀態' }]}
              >
                <Select placeholder="請選擇案件狀態">
                  {Object.entries(CONTRACT_CASE_STATUS_LABELS).map(([key, label]) => (
                    <Option key={key} value={key}>
                      {label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            {/* 第四行：承辦同仁、協力廠商 */}
            <Col xs={24} sm={12}>
              <Form.Item
                label="承辦同仁"
                name="responsible_staff"
                rules={[{ required: true, message: '請輸入承辦同仁' }]}
              >
                <Input placeholder="請輸入承辦同仁" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label="協力廠商"
                name="partner_vendor"
              >
                <Input placeholder="請輸入協力廠商" />
              </Form.Item>
            </Col>

            {/* 第五行：契約期程、契約金額 */}
            <Col xs={24} sm={16}>
              <Form.Item
                label="契約期程"
                name="contract_period"
                rules={[{ required: true, message: '請選擇契約期程' }]}
              >
                <RangePicker 
                  style={{ width: '100%' }}
                  placeholder={['開始日期', '結束日期']}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={8}>
              <Form.Item
                label="契約金額 (新台幣)"
                name="contract_amount"
              >
                <InputNumber
                  style={{ width: '100%' }}
                  formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value!.replace(/\$\s?|(,*)/g, '')}
                  placeholder="請輸入契約金額"
                  min={0}
                />
              </Form.Item>
            </Col>

            {/* 第六行：案件說明 */}
            <Col span={24}>
              <Form.Item
                label="案件說明"
                name="description"
              >
                <TextArea
                  rows={4}
                  placeholder="請輸入案件說明"
                />
              </Form.Item>
            </Col>

            {/* 第七行：備註 */}
            <Col span={24}>
              <Form.Item
                label="備註"
                name="notes"
              >
                <TextArea
                  rows={3}
                  placeholder="請輸入備註"
                />
              </Form.Item>
            </Col>

            {/* 操作按鈕 */}
            <Col span={24}>
              <Form.Item>
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
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>
    </div>
  );
};

export default ContractCaseFormPage;