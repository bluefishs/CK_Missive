/**
 * 桃園查估派工 - 派工紀錄 Tab
 *
 * 導航模式設計：
 * - 新增派工單導航到獨立的新增頁面
 * - 點擊列表項目導航至派工單詳情頁進行編輯
 *
 * @version 1.4.0 - 提取欄位定義 (useDispatchOrderColumns) 和匯出邏輯 (useDispatchOrderExport)
 * @date 2026-02-27
 */

import React, { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Button,
  Space,
  Modal,
  App,
  Card,
  Tag,
  Input,
  Statistic,
  Row,
  Col,
  Upload,
  Tooltip,
  List,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  SendOutlined,
  LinkOutlined,
  RightOutlined,
} from '@ant-design/icons';

import { ResponsiveTable } from '../common';
import { dispatchOrdersApi } from '../../api/taoyuanDispatchApi';
import type { DispatchOrder } from '../../types/api';
import { useTableColumnSearch } from '../../hooks/utility/useTableColumnSearch';
import { useResponsive, useTaoyuanDispatchOrders } from '../../hooks';
import { useDispatchOrderColumns } from './dispatchOrders/useDispatchOrderColumns';
import { useDispatchOrderExport } from './dispatchOrders/useDispatchOrderExport';

const { Text } = Typography;
const { Search } = Input;

export interface DispatchOrdersTabProps {
  contractProjectId: number;
  contractCode: string;
}

export const DispatchOrdersTab: React.FC<DispatchOrdersTabProps> = ({
  contractProjectId,
  contractCode: _contractCode,
}) => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [searchText, setSearchText] = useState('');
  const [importModalVisible, setImportModalVisible] = useState(false);

  // RWD 響應式
  const { isMobile } = useResponsive();

  // 使用共用的表格搜尋 Hook
  const {
    searchText: columnSearchText,
    searchedColumn,
    getColumnSearchProps,
  } = useTableColumnSearch<DispatchOrder>();

  // 使用集中的 Hook 查詢派工紀錄
  const {
    dispatchOrders: orders,
    isLoading,
    refetch,
  } = useTaoyuanDispatchOrders({
    contract_project_id: contractProjectId,
    search: searchText || undefined,
    limit: 100,
  });

  // 動態篩選器
  const dispatchCaseHandlerFilters = useMemo(() =>
    [...new Set(orders.map((o) => o.case_handler).filter(Boolean))]
      .map((h) => ({ text: h as string, value: h as string })),
    [orders]
  );

  const dispatchSurveyUnitFilters = useMemo(() =>
    [...new Set(orders.map((o) => o.survey_unit).filter(Boolean))]
      .map((s) => ({ text: s as string, value: s as string })),
    [orders]
  );

  // 欄位定義 Hook
  const columns = useDispatchOrderColumns({
    columnSearchText,
    searchedColumn,
    getColumnSearchProps,
    navigate,
    dispatchCaseHandlerFilters,
    dispatchSurveyUnitFilters,
  });

  // 匯出邏輯 Hook
  const { exporting, exportProgress, handleExportMasterExcel } = useDispatchOrderExport({
    contractProjectId,
    searchText,
    orderCount: orders.length,
    message,
  });

  const handleCreate = useCallback(() => {
    navigate('/taoyuan/dispatch/create');
  }, [navigate]);

  const handleImport = useCallback(async (file: File) => {
    try {
      const result = await dispatchOrdersApi.importExcel(file, contractProjectId);
      if (result.success) {
        message.success(`匯入成功: ${result.imported_count} 筆`);
        refetch();
      } else {
        const errorMsg = result.errors.length > 0
          ? result.errors.map(e => e.message).join(', ')
          : '未知錯誤';
        message.error(`匯入失敗: ${errorMsg}`);
      }
    } catch (error) {
      message.error('匯入失敗');
    }
    setImportModalVisible(false);
  }, [contractProjectId, message, refetch]);

  const handleDownloadTemplate = useCallback(async () => {
    try {
      await dispatchOrdersApi.downloadImportTemplate();
    } catch (error) {
      message.error('下載範本失敗');
    }
  }, [message]);

  const handleRowClick = useCallback((record: DispatchOrder) => {
    navigate(`/taoyuan/dispatch/${record.id}`);
  }, [navigate]);

  // 手機版卡片清單
  const MobileDispatchList = () => (
    <List
      dataSource={orders}
      loading={isLoading}
      pagination={{
        size: 'small',
        pageSize: 10,
        showTotal: (total) => `共 ${total} 筆`,
      }}
      renderItem={(order) => (
        <Card
          size="small"
          style={{ marginBottom: 8, cursor: 'pointer' }}
          onClick={() => handleRowClick(order)}
          hoverable
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <Text strong style={{ color: '#1890ff', fontSize: 13 }}>
                {order.dispatch_no}
              </Text>
              <div style={{ fontSize: 13, marginTop: 2 }}>
                {order.project_name}
              </div>
              <Space wrap size={4} style={{ marginTop: 6 }}>
                {order.work_type && (
                  <Tag color="blue" style={{ fontSize: 11 }}>
                    {order.work_type.split(',')[0]}
                  </Tag>
                )}
                {order.case_handler && <Tag style={{ fontSize: 11 }}>{order.case_handler}</Tag>}
              </Space>
              {order.sub_case_name && (
                <div style={{ marginTop: 4, fontSize: 11, color: '#666' }}>
                  分案: {order.sub_case_name}
                </div>
              )}
              {order.contact_note && (
                <div style={{ fontSize: 11, color: '#888' }}>
                  備註: {order.contact_note}
                </div>
              )}
              <div style={{ marginTop: 6, fontSize: 11, color: '#999' }}>
                公文: {order.linked_documents?.length || 0} |
                工程: {order.linked_projects?.length || 0} |
                附件: {order.attachment_count || 0}
              </div>
            </div>
            <RightOutlined style={{ color: '#ccc', marginTop: 4 }} />
          </div>
        </Card>
      )}
    />
  );

  const stats = useMemo(() => ({
    total: orders.length,
    linkedDocs: orders.reduce((sum, o) => sum + (o.linked_documents?.length ?? 0), 0),
    linkedProjects: orders.reduce((sum, o) => sum + (o.linked_projects?.length ?? 0), 0),
    workTypes: new Set(orders.map((o) => o.work_type).filter(Boolean)).size,
  }), [orders]);

  return (
    <div>
      {/* 統計卡片 - RWD 響應式 */}
      <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={isMobile ? '總數' : '總派工單數'}
              value={stats.total}
              prefix={<SendOutlined />}
              valueStyle={{ fontSize: isMobile ? 18 : 24 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={isMobile ? '公文' : '關聯公文'}
              value={stats.linkedDocs}
              valueStyle={{ color: '#1890ff', fontSize: isMobile ? 18 : 24 }}
              prefix={<LinkOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={isMobile ? '工程' : '關聯工程'}
              value={stats.linkedProjects}
              valueStyle={{ color: '#52c41a', fontSize: isMobile ? 18 : 24 }}
              prefix={<LinkOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={isMobile ? '類別' : '作業類別數'}
              value={stats.workTypes}
              valueStyle={{ fontSize: isMobile ? 18 : 24 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 工具列 - RWD 響應式 */}
      <Row gutter={[8, 8]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={24} sm={12} md={8}>
          <Search
            placeholder={isMobile ? '搜尋派工單...' : '搜尋派工單號、工程名稱'}
            allowClear
            value={searchText}
            onChange={(e) => {
              const val = e.target.value;
              setSearchText(val);
              // 清空時立即觸發（allowClear 點擊時 value 會變成空字串）
              if (!val) setSearchText('');
            }}
            onSearch={setSearchText}
            style={{ width: '100%' }}
            size={isMobile ? 'middle' : 'middle'}
          />
        </Col>
        <Col xs={24} sm={12} md={16} style={{ textAlign: isMobile ? 'left' : 'right' }}>
          <Space wrap size={isMobile ? 'small' : 'middle'}>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refetch()}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '重新整理'}
            </Button>
            <Tooltip title={exportProgress ? `${exportProgress.progress}% — ${exportProgress.message}` : undefined}>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExportMasterExcel}
                loading={exporting}
                size={isMobile ? 'small' : 'middle'}
              >
                {isMobile ? '' : (exportProgress ? `${exportProgress.progress}%` : '匯出總表')}
              </Button>
            </Tooltip>
            <Button
              icon={<UploadOutlined />}
              onClick={() => setImportModalVisible(true)}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : 'Excel 匯入'}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '新增派工單'}
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 提示文字 - 手機版隱藏 */}
      {!isMobile && (
        <div style={{ marginBottom: 8, color: '#666', fontSize: 12 }}>
          <Text type="secondary">點擊列表項目可進入詳情頁進行編輯</Text>
        </div>
      )}

      {/* 派工紀錄 - RWD: 手機用卡片清單，桌面用表格 */}
      {isMobile ? (
        <MobileDispatchList />
      ) : (
        <ResponsiveTable
          columns={columns}
          dataSource={orders}
          rowKey="id"
          loading={isLoading}
          scroll={{ x: 1450 }}
          size="small"
          mobileHiddenColumns={['sub_case_name', 'contact_note', 'project_folder', 'survey_unit']}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total: number) => `共 ${total} 筆`,
          }}
          onRow={(record) => ({
            onClick: () => handleRowClick(record),
            style: { cursor: 'pointer' },
          })}
        />
      )}

      {/* Excel 匯入 Modal - RWD 響應式 */}
      <Modal
        title="Excel 匯入派工紀錄"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
        width={isMobile ? '95%' : 600}
      >
        <div style={{ marginBottom: 16 }}>
          <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
            下載匯入範本
          </Button>
          <span style={{ marginLeft: 8, color: '#666', fontSize: 12 }}>
            範本包含 13 個欄位：派工單號、機關函文號、工程名稱...等
          </span>
        </div>
        <Upload.Dragger
          accept=".xlsx,.xls"
          maxCount={1}
          beforeUpload={(file) => {
            handleImport(file);
            return false;
          }}
        >
          <p className="ant-upload-drag-icon">
            <FileExcelOutlined style={{ fontSize: 48, color: '#52c41a' }} />
          </p>
          <p className="ant-upload-text">點擊或拖曳 Excel 檔案至此區域</p>
          <p className="ant-upload-hint">
            支援 .xlsx, .xls 格式，對應原始需求 17 欄位設計
          </p>
        </Upload.Dragger>
        <div style={{ marginTop: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
          <Text strong>匯入欄位說明：</Text>
          <div style={{ marginTop: 8, fontSize: 12 }}>
            <Row gutter={[8, 4]}>
              <Col span={8}>1. 派工單號 *</Col>
              <Col span={8}>2. 機關函文號</Col>
              <Col span={8}>3. 工程名稱/派工事項</Col>
              <Col span={8}>4. 作業類別</Col>
              <Col span={8}>5. 分案名稱/派工備註</Col>
              <Col span={8}>6. 履約期限</Col>
              <Col span={8}>7. 案件承辦</Col>
              <Col span={8}>8. 查估單位</Col>
              <Col span={8}>9. 乾坤函文號</Col>
              <Col span={8}>10. 雲端資料夾</Col>
              <Col span={8}>11. 專案資料夾</Col>
              <Col span={8}>12. 聯絡備註</Col>
            </Row>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default DispatchOrdersTab;
