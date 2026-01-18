import React from 'react';
import { Form, Input, Select, Button, Card, Row, Col, App } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { logger } from '../utils/logger';

const { TextArea } = Input;
const { Option } = Select;

export const DocumentCreatePage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const onFinish = (values: any) => {
    logger.debug('Form values:', values);
    message.success('公文建立成功！');
    navigate('/documents');
  };

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        
        <div style={{ marginBottom: 24 }}>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate('/documents')}
            style={{ marginRight: 16 }}
          >
            返回列表
          </Button>
          <span style={{ fontSize: 20, fontWeight: 'bold', color: '#1976d2' }}>
            新增公文
          </span>
        </div>

        <Card title="公文基本資訊">
          <Form
            form={form}
            layout="vertical"
            onFinish={onFinish}
            initialValues={{
              type: 'official',
              priority: 'medium',
              status: 'draft'
            }}
          >
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  label="公文標題"
                  name="title"
                  rules={[{ required: true, message: '請輸入公文標題' }]}
                >
                  <Input placeholder="請輸入公文標題" />
                </Form.Item>
              </Col>
              
              <Col xs={24} md={12}>
                <Form.Item
                  label="公文類型"
                  name="type"
                  rules={[{ required: true, message: '請選擇公文類型' }]}
                >
                  <Select placeholder="請選擇公文類型">
                    <Option value="official">正式公文</Option>
                    <Option value="internal">內部簽呈</Option>
                    <Option value="meeting">會議紀錄</Option>
                    <Option value="report">報告書</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  label="承辦機關"
                  name="agency"
                  rules={[{ required: true, message: '請選擇承辦機關' }]}
                >
                  <Select placeholder="請選擇承辦機關">
                    <Option value="內政部國土測繪中心">內政部國土測繪中心</Option>
                    <Option value="臺北市政府">臺北市政府</Option>
                    <Option value="經濟部">經濟部</Option>
                    <Option value="交通部">交通部</Option>
                  </Select>
                </Form.Item>
              </Col>

              <Col xs={24} md={12}>
                <Form.Item
                  label="優先等級"
                  name="priority"
                  rules={[{ required: true, message: '請選擇優先等級' }]}
                >
                  <Select placeholder="請選擇優先等級">
                    <Option value="high">高</Option>
                    <Option value="medium">中</Option>
                    <Option value="low">低</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24}>
                <Form.Item
                  label="關聯承攬案件"
                  name="contract_case"
                  help="選擇與此公文相關的承攬案件"
                >
                  <Select 
                    mode="multiple"
                    placeholder="請選擇相關承攬案件"
                    showSearch
                    optionFilterProp="children"
                    allowClear
                  >
                    <Option value="數位測繪技術創新專案">數位測繪技術創新專案</Option>
                    <Option value="地籍圖重測委辦計畫">地籍圖重測委辦計畫</Option>
                    <Option value="都市計畫圖協辦計畫">都市計畫圖協辦計畫</Option>
                    <Option value="測量儀器校正案件">測量儀器校正案件</Option>
                    <Option value="工程測量服務案">工程測量服務案</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              label="公文內容"
              name="content"
              rules={[{ required: true, message: '請輸入公文內容' }]}
            >
              <TextArea 
                rows={6} 
                placeholder="請輸入公文詳細內容..."
              />
            </Form.Item>

            <Form.Item
              label="備註"
              name="notes"
            >
              <TextArea 
                rows={3} 
                placeholder="其他備註事項..."
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
              <Button 
                onClick={() => navigate('/documents')} 
                style={{ marginRight: 8 }}
              >
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                建立公文
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </div>
  );
};