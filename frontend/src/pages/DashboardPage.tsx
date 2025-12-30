import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Button, Space, Typography, message, Spin } from 'antd';
import {
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  EyeOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { httpClient } from '../services/httpClient'; // 直接使用 httpClient

const { Title } = Typography;

// 定義儀表板 API 回應的型別
interface DashboardStats {
  total: number;
  approved: number;
  pending: number;
  rejected: number;
}

interface RecentDocument {
  id: number;
  doc_number: string;
  subject: string;
  doc_type: string;
  status: string;
  sender: string;
  creator: string;
  created_at: string;
  receive_date: string;
}

export const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<DashboardStats>({
    total: 0,
    approved: 0,
    pending: 0,
    rejected: 0,
  });
  const [recentDocuments, setRecentDocuments] = useState<any[]>([]);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // 使用現有的文件統計API
      console.log('=== 儀表板: 開始載入統計數據 ===');
      const [statsResponse, documentsResponse] = await Promise.all([
        httpClient.get('/dashboard/stats').catch((error) => {
          console.error('統計 API 錯誤:', error);
          return { data: { stats: { total: 0, approved: 0, pending: 0, rejected: 0 }, recent_documents: [] } };
        }),
        httpClient.get('/documents-enhanced/integrated-search?limit=10').catch((error) => {
          console.error('文檔查詢 API 錯誤:', error);
          return { data: { items: [] } };
        })
      ]);
      console.log('=== 儀表板: 收到統計數據 ===', statsResponse.data);

      // 處理統計數據
      const statsData = statsResponse?.data || {};
      console.log('=== 統計數據類型檢查 ===', typeof statsData, statsData);
      // 適配後端返回的數據格式：{stats: {total, approved, pending, rejected}}
      const stats = statsData.stats || statsData;
      console.log('=== 統計數據內容 ===', stats);
      setStats({
        total: stats?.total || statsData?.total_documents || 0,
        approved: stats?.approved || statsData?.send_count || 0,
        pending: stats?.pending || statsData?.current_year_count || 0,
        rejected: stats?.rejected || statsData?.receive_count || 0
      });

      // 處理近期公文數據
      // 適配後端返回的數據格式：{stats: {...}, recent_documents: [...]}
      const documents = statsData.recent_documents || documentsResponse?.data?.items || documentsResponse?.data || [];
      console.log('=== 文檔數據 ===', documents);
      if (documents && Array.isArray(documents)) {
        const formattedDocs = documents.map((doc: any, index: number) => ({
          key: doc.id || index,
          id: doc.doc_number || `DOC-${doc.id}`,
          title: doc.subject || '無標題',
          type: doc.doc_type || '一般公文',
          status: doc.status || '收文完成',
          agency: doc.sender || '未指定機關',
          creator: doc.creator || '系統使用者',
          createDate: doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '',
          deadline: doc.receive_date ? new Date(doc.receive_date).toLocaleDateString() : ''
        }));
        setRecentDocuments(formattedDocs);
      }

    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      console.error('Error details:', error.message, error.response);
      message.error(`載入儀表板資料失敗: ${error.message || '未知錯誤'}`);
      // 重置狀態
      setStats({ total: 0, approved: 0, pending: 0, rejected: 0 });
      setRecentDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap = {
      '收文完成': { color: 'orange', text: '收文完成' },
      '使用者確認': { color: 'green', text: '使用者確認' },
      '收文異常': { color: 'red', text: '收文異常' }
    };
    const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns = [
    { title: '公文編號', dataIndex: 'id', key: 'id', width: 120 },
    { title: '標題', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '類型', dataIndex: 'type', key: 'type', width: 100 },
    { title: '狀態', dataIndex: 'status', key: 'status', width: 120, render: getStatusTag },
    { title: '發文單位', dataIndex: 'agency', key: 'agency', ellipsis: true },
    { title: '建立日期', dataIndex: 'createDate', key: 'createDate', width: 110 },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: () => (
        <Space size="small">
          <Button type="link" icon={<EyeOutlined />} size="small">查看</Button>
          <Button type="link" icon={<EditOutlined />} size="small">編輯</Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <Title level={2} style={{ marginBottom: 24, color: '#1976d2' }}>儀表板總覽</Title>
        <Spin spinning={loading}>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={12} md={6} lg={6}>
              <Card><Statistic title="總公文數" value={stats.total} prefix={<FileTextOutlined />} /></Card>
            </Col>
            <Col xs={12} sm={12} md={6} lg={6}>
              <Card><Statistic title="已核准" value={stats.approved} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} /></Card>
            </Col>
            <Col xs={12} sm={12} md={6} lg={6}>
              <Card><Statistic title="待處理" value={stats.pending} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#faad14' }} /></Card>
            </Col>
            <Col xs={12} sm={12} md={6} lg={6}>
              <Card><Statistic title="已駁回" value={stats.rejected} prefix={<ExclamationCircleOutlined />} valueStyle={{ color: '#ff4d4f' }} /></Card>
            </Col>
          </Row>
          <Card title="近期公文" extra={<Button type="primary" icon={<PlusOutlined />}>新增公文</Button>}>
            <Table
              columns={columns}
              dataSource={recentDocuments}
              pagination={false} // 直接顯示 API 回傳的幾筆，不需分頁
              scroll={{ x: 1000 }}
            />
          </Card>
        </Spin>
      </div>
    </div>
  );
};
