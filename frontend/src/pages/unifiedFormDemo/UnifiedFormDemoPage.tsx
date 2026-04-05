/**
 * UnifiedFormDemoPage - 統一表單元件示範頁面
 *
 * 此頁面用於展示通用表單元件的使用方式，供開發人員參考。
 * 使用模擬數據，不與後端 API 連接。
 *
 * @version 1.1.0 (refactored: extracted constants + useDemoForm hook)
 * @status DEMO
 */
import React from 'react';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  Card,
  Typography,
  Space,
  Form,
  Input,
  Button,
  Select,
  InputNumber,
  Row,
  Col,
  Divider,
  Alert,
  Tag,
  App,
} from 'antd';
import {
  FormOutlined,
  TableOutlined,
  NumberOutlined,
  MessageOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';

import UnifiedTable from '../../components/common/UnifiedTable';
import SequenceNumberGenerator from '../../components/common/SequenceNumberGenerator';
import RemarksField from '../../components/common/RemarksField';
import { DEMO_COLUMNS, DEMO_FILTER_CONFIGS } from './constants';
import { useDemoForm } from './useDemoForm';

const { Title, Text } = Typography;
const { Option } = Select;

const UnifiedFormDemoPage: React.FC = () => {
  const { message } = App.useApp();
  const {
    form,
    demoData,
    formSequenceNumber,
    setFormSequenceNumber,
    formRemarks,
    setFormRemarks,
    handleFormSubmit,
    handleExport,
  } = useDemoForm(message);

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Space vertical style={{ width: '100%' }} size="large">
        {/* 頁面標題 */}
        <Card>
          <Space vertical style={{ width: '100%' }}>
            <Title level={2}>
              <FormOutlined style={{ marginRight: 8 }} />
              統一表單系統演示
            </Title>
            <Alert
              title="功能特色"
              description={
                <div>
                  <Text>此頁面展示了統一表單系統的核心功能：</Text>
                  <div style={{ marginTop: 8 }}>
                    <Tag color="blue">自動流水號生成</Tag>
                    <Tag color="green">智能篩選與排序</Tag>
                    <Tag color="orange">備註說明管理</Tag>
                    <Tag color="purple">數據導出功能</Tag>
                    <Tag color="red">響應式設計</Tag>
                  </div>
                </div>
              }
              type="info"
              showIcon
            />
          </Space>
        </Card>

        {/* 新增表單 */}
        <Card title={<><FormOutlined /> 新增記錄</>}>
          <Form form={form} layout="vertical" onFinish={handleFormSubmit}>
            <Row gutter={16}>
              <Col xs={24} md={8}>
                <Form.Item label="流水號" required>
                  <SequenceNumberGenerator
                    value={formSequenceNumber}
                    onChange={setFormSequenceNumber}
                    category="document"
                    autoGenerate={true}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={16}>
                <Form.Item
                  name="title"
                  label="標題"
                  rules={[{ required: true, message: '請輸入標題' }]}
                >
                  <Input placeholder="請輸入記錄標題" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="category"
                  label="類別"
                  rules={[{ required: true, message: '請選擇類別' }]}
                >
                  <Select placeholder="選擇類別">
                    <Option value="技術文件">技術文件</Option>
                    <Option value="設計文件">設計文件</Option>
                    <Option value="軟體開發">軟體開發</Option>
                    <Option value="合作夥伴">合作夥伴</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="priority" label="優先級" initialValue="中">
                  <Select>
                    <Option value="高">高</Option>
                    <Option value="中">中</Option>
                    <Option value="低">低</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="amount" label="預算金額">
                  <InputNumber style={{ width: '100%' }} placeholder="輸入金額" prefix="NT$" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item label="備註說明">
              <RemarksField
                value={formRemarks}
                onChange={setFormRemarks}
                placeholder="請輸入相關備註說明..."
                inline={true}
                maxLength={500}
              />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" size="large">
                <FormOutlined /> 新增記錄
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {/* 數據表格 */}
        <UnifiedTable
          title="記錄列表"
          subtitle="支持全文搜索、多欄位篩選、自定義排序等功能"
          columns={DEMO_COLUMNS}
          data={demoData}
          filterConfigs={DEMO_FILTER_CONFIGS}
          enableExport={true}
          enableSequenceNumber={true}
          onExport={handleExport}
          onRefresh={() => message.success('數據已刷新')}
          rowKey="id"
          customActions={
            <Button type="dashed">
              <DatabaseOutlined /> 自定義操作
            </Button>
          }
        />

        {/* 功能說明 */}
        <Card title="功能詳細說明">
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Card size="small" title={<><NumberOutlined /> 流水號系統</>}>
                <Space vertical style={{ width: '100%' }}>
                  <Text>支持自定義前綴、日期格式、分隔符</Text>
                  <Text>自動生成唯一流水號</Text>
                  <Text>支持手動編輯和複製功能</Text>
                  <Text>提供格式預覽</Text>
                </Space>
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card size="small" title={<><MessageOutlined /> 備註管理</>}>
                <Space vertical style={{ width: '100%' }}>
                  <Text>行內編輯模式</Text>
                  <Text>支持歷史記錄查看</Text>
                  <Text>快捷鍵操作 (Ctrl+Enter, Esc)</Text>
                  <Text>字數限制和統計</Text>
                </Space>
              </Card>
            </Col>
          </Row>

          <Divider />

          <Card size="small" title={<><TableOutlined /> 統一表格功能</>}>
            <Row gutter={16}>
              <Col xs={24} md={8}>
                <Space vertical style={{ width: '100%' }}>
                  <Text strong>篩選功能:</Text>
                  <Text>全文搜索、下拉篩選、日期區間、自動完成</Text>
                </Space>
              </Col>
              <Col xs={24} md={8}>
                <Space vertical style={{ width: '100%' }}>
                  <Text strong>排序功能:</Text>
                  <Text>多欄位排序、升降序切換、智能排序</Text>
                </Space>
              </Col>
              <Col xs={24} md={8}>
                <Space vertical style={{ width: '100%' }}>
                  <Text strong>其他功能:</Text>
                  <Text>數據導出、序號生成、響應式布局</Text>
                </Space>
              </Col>
            </Row>
          </Card>
        </Card>
      </Space>
    </ResponsiveContent>
  );
};

export default UnifiedFormDemoPage;
