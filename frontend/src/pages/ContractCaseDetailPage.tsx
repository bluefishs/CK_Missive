import React, { useState, useEffect } from 'react';
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Spin,
  message,
  Row,
  Col,
  Progress,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ContractCase,
  ContractCaseType,
  CONTRACT_CASE_TYPE_LABELS,
  CONTRACT_CASE_TYPE_COLORS,
  CONTRACT_CASE_STATUS_LABELS,
  CONTRACT_CASE_STATUS_COLORS,
} from '../types/contractCase';
import { ROUTES } from '../router/types';

const { Title } = Typography;

// 模擬數據
const mockData: ContractCase = {
  id: 1,
  year: '2024',
  project_name: '數位測繪技術創新專案',
  client_unit: '內政部國土測繪中心',
  contract_period_start: '2024-01-15',
  contract_period_end: '2024-12-31',
  responsible_staff: '王小明',
  partner_vendor: '精密測量科技有限公司',
  case_type: ContractCaseType.INNOVATION,
  case_status: 'in_progress',
  contract_amount: 5000000,
  description: '開發新一代數位測繪技術，包含點雲資料處理、三維建模、精度驗證等功能模組。本專案旨在提升測繪作業效率與精度，降低人力成本，建立智慧化測繪作業流程。',
  notes: '需要配合新採購的測繪設備進行整合測試。',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

export const ContractCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ContractCase | null>(null);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    setLoading(true);
    try {
      // 模擬API調用
      await new Promise(resolve => setTimeout(resolve, 500));
      // 這裡未來會替換為真實的API調用
      setData(mockData);
    } catch (error) {
      message.error('載入數據失敗');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    navigate(ROUTES.CONTRACT_CASE_EDIT.replace(':id', id!));
  };

  const handleDelete = () => {
    // 這裡應該顯示確認對話框並調用刪除API
    message.success('刪除成功');
    navigate(ROUTES.CONTRACT_CASES);
  };

  const handleBack = () => {
    navigate(ROUTES.CONTRACT_CASES);
  };

  // 計算項目進度 (模擬)
  const calculateProgress = () => {
    if (!data) return 0;
    
    const startDate = new Date(data.contract_period_start);
    const endDate = new Date(data.contract_period_end);
    const currentDate = new Date();
    
    if (currentDate < startDate) return 0;
    if (currentDate > endDate) return 100;
    
    const totalDays = endDate.getTime() - startDate.getTime();
    const passedDays = currentDate.getTime() - startDate.getTime();
    
    return Math.round((passedDays / totalDays) * 100);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Title level={4}>案件不存在</Title>
          <Button type="primary" onClick={handleBack}>
            返回列表
          </Button>
        </div>
      </Card>
    );
  }

  const progress = calculateProgress();

  return (
    <div>
      {/* 頁面標題和操作 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button 
              type="text" 
              icon={<ArrowLeftOutlined />}
              onClick={handleBack}
            >
              返回
            </Button>
            <div>
              <Title level={3} style={{ margin: 0 }}>
                {data.project_name}
              </Title>
              <div style={{ marginTop: 8 }}>
                <Tag color={CONTRACT_CASE_TYPE_COLORS[data.case_type]}>
                  {CONTRACT_CASE_TYPE_LABELS[data.case_type]}
                </Tag>
                <Tag color={CONTRACT_CASE_STATUS_COLORS[data.case_status]}>
                  {CONTRACT_CASE_STATUS_LABELS[data.case_status]}
                </Tag>
              </div>
            </div>
          </div>
          <Space>
            <Button type="primary" icon={<EditOutlined />} onClick={handleEdit}>
              編輯
            </Button>
            <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
              刪除
            </Button>
          </Space>
        </div>
      </Card>

      {/* 進度顯示 */}
      {data.case_status === 'in_progress' && (
        <Card title="執行進度" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            <Col span={18}>
              <Progress 
                percent={progress} 
                status={progress === 100 ? "success" : "active"} 
              />
            </Col>
            <Col span={6} style={{ textAlign: 'right' }}>
              <div>完成度: {progress}%</div>
              <div style={{ color: '#666', fontSize: '12px' }}>
                根據契約期程計算
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {/* 基本資訊 */}
      <Card title="基本資訊" style={{ marginBottom: 16 }}>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="專案名稱" span={2}>
            {data.project_name}
          </Descriptions.Item>
          <Descriptions.Item label="年度別">
            {data.year}年
          </Descriptions.Item>
          <Descriptions.Item label="案件性質">
            <Tag color={CONTRACT_CASE_TYPE_COLORS[data.case_type]}>
              {CONTRACT_CASE_TYPE_LABELS[data.case_type]}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="委託單位">
            {data.client_unit}
          </Descriptions.Item>
          <Descriptions.Item label="案件狀態">
            <Tag color={CONTRACT_CASE_STATUS_COLORS[data.case_status]}>
              {CONTRACT_CASE_STATUS_LABELS[data.case_status]}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="承辦同仁">
            {data.responsible_staff}
          </Descriptions.Item>
          <Descriptions.Item label="協力廠商">
            {data.partner_vendor}
          </Descriptions.Item>
          <Descriptions.Item label="契約金額">
            {data.contract_amount ? `NT$ ${data.contract_amount.toLocaleString()}` : '未填寫'}
          </Descriptions.Item>
          <Descriptions.Item label="契約期程" span={2}>
            {data.contract_period_start} ~ {data.contract_period_end}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 詳細說明 */}
      {data.description && (
        <Card title="案件說明" style={{ marginBottom: 16 }}>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
            {data.description}
          </div>
        </Card>
      )}

      {/* 備註 */}
      {data.notes && (
        <Card title="備註">
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, color: '#666' }}>
            {data.notes}
          </div>
        </Card>
      )}
    </div>
  );
};

export default ContractCaseDetailPage;