import React, { useState } from 'react';
import { Layout, Space, Card, Statistic, Row, Col } from 'antd';
import { FileTextOutlined, InboxOutlined, SendOutlined, CalendarOutlined } from '@ant-design/icons';

// 匯入元件
import DocumentImport from '../components/Documents/DocumentImport';
import DocumentList from '../components/Documents/DocumentList';
import FilterPanel from '../components/Documents/FilterPanel';
import ExportButton from '../components/Documents/ExportButton';
import { documentsApi } from '../../api/documentsApi';

const { Content } = Layout;

const DocumentManagement = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [currentFilters, setCurrentFilters] = useState({});
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState({
    total_documents: 0,
    receive_count: 0,
    send_count: 0,
    current_year_count: 0
  });

  // 匯入成功回調
  const handleImportSuccess = (result) => {
    setRefreshTrigger(prev => prev + 1);
    loadStatistics();
  };

  // 篩選變更
  const handleFilterChange = (filters) => {
    setCurrentFilters(filters);
  };

  // 載入統計資訊
  const loadStatistics = async () => {
    try {
      const stats = await documentsApi.getStatistics();
      setStatistics({
        total_documents: stats.total_documents || stats.total || 0,
        receive_count: stats.receive_count || stats.receive || 0,
        send_count: stats.send_count || stats.send || 0,
        current_year_count: stats.current_year_count || 0,
      });
    } catch (error) {
      console.error('載入統計失敗:', error);
    }
  };

  // 初始載入統計
  React.useEffect(() => {
    loadStatistics();
  }, []);

  return (
    <Layout style={{ minHeight: '100vh', backgroundColor: '#f0f2f5' }}>
      <Content style={{ padding: '24px' }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          
          {/* 統計卡片 */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="總文件數"
                  value={statistics.total_documents}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="收文數量"
                  value={statistics.receive_count}
                  prefix={<InboxOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="發文數量"
                  value={statistics.send_count}
                  prefix={<SendOutlined />}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="本年度文件"
                  value={statistics.current_year_count}
                  prefix={<CalendarOutlined />}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
          </Row>

          {/* 匯入區域 */}
          <DocumentImport onImportSuccess={handleImportSuccess} />

          {/* 篩選面板 */}
          <FilterPanel 
            onFilter={handleFilterChange}
            loading={loading}
          />

          {/* 操作按鈕區 */}
          <Card>
            <Space>
              <ExportButton filters={currentFilters} />
            </Space>
          </Card>

          {/* 文件列表 */}
          <DocumentList 
            refreshTrigger={refreshTrigger}
            filters={currentFilters}
          />

        </Space>
      </Content>
    </Layout>
  );
};

export default DocumentManagement;
