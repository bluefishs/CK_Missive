/**
 * 公文編輯頁面
 *
 * RWD 優化版本
 * @version 1.1.0
 * @date 2026-01-23
 */

import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, Card, Row, Col, Spin, App, Space } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useResponsive } from '../hooks';

const { TextArea } = Input;
const { Option } = Select;

interface DocumentFormValues {
  title?: string;
  type?: string;
  agency?: string;
  priority?: string;
  contract_case?: string[];
  content?: string;
  notes?: string;
}

export const DocumentEditPage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { id } = useParams();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [loadingDocument, setLoadingDocument] = useState(true);

  // RWD 響應式
  const { isMobile } = useResponsive();

  // 載入公文資料
  useEffect(() => {
    const loadDocument = async () => {
      setLoadingDocument(true);
      try {
        const response = await fetch(`/api/documents/${id}`);
        if (!response.ok) {
          throw new Error('Failed to load document');
        }

        const documentData = await response.json();

        // 格式化資料以符合表單格式
        const formData = {
          title: documentData.title || '',
          type: documentData.document_type || 'official',
          agency: documentData.agency || '',
          priority: documentData.priority || 'medium',
          contract_case: documentData.contract_cases || [],
          content: documentData.content || '',
          notes: documentData.notes || ''
        };

        form.setFieldsValue(formData);
      } catch (error) {
        console.error('Load document failed:', error);
        message.error('載入公文資料失敗');
      } finally {
        setLoadingDocument(false);
      }
    };

    if (id) {
      loadDocument();
    }
  }, [id, form]);

  const onFinish = async (values: DocumentFormValues) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/documents/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: values.title,
          document_type: values.type,
          agency: values.agency,
          priority: values.priority,
          contract_cases: values.contract_case,
          content: values.content,
          notes: values.notes
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update document');
      }

      message.success('公文更新成功！');
      navigate('/documents');
    } catch (error) {
      console.error('Update document failed:', error);
      message.error('更新公文失敗');
    } finally {
      setLoading(false);
    }
  };

  if (loadingDocument) {
    return (
      <div style={{
        padding: isMobile ? '12px' : '24px',
        background: '#f5f5f5',
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center'
      }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{
      padding: isMobile ? '12px' : '24px',
      background: '#f5f5f5',
      minHeight: '100vh'
    }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>

        {/* 頁面標題 - RWD 響應式 */}
        <div style={{
          marginBottom: isMobile ? 16 : 24,
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: isMobile ? 8 : 16
        }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/documents')}
            size={isMobile ? 'small' : 'middle'}
          >
            {isMobile ? '返回' : '返回列表'}
          </Button>
          <span style={{
            fontSize: isMobile ? 16 : 20,
            fontWeight: 'bold',
            color: '#1976d2'
          }}>
            編輯公文 #{id}
          </span>
        </div>

        <Card
          title="公文基本資訊"
          size={isMobile ? 'small' : 'default'}
          styles={{
            body: { padding: isMobile ? 12 : 24 }
          }}
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={onFinish}
            size={isMobile ? 'middle' : 'large'}
          >
            <Row gutter={[isMobile ? 8 : 16, 0]}>
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

            <Row gutter={[isMobile ? 8 : 16, 0]}>
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

            <Row gutter={[isMobile ? 8 : 16, 0]}>
              <Col xs={24}>
                <Form.Item
                  label="關聯承攬案件"
                  name="contract_case"
                  help={isMobile ? undefined : '選擇與此公文相關的承攬案件'}
                >
                  <Select
                    mode="multiple"
                    placeholder={isMobile ? '選擇承攬案件' : '請選擇相關承攬案件'}
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
                rows={isMobile ? 4 : 6}
                placeholder="請輸入公文詳細內容..."
              />
            </Form.Item>

            <Form.Item
              label="備註"
              name="notes"
            >
              <TextArea
                rows={isMobile ? 2 : 3}
                placeholder="其他備註事項..."
              />
            </Form.Item>

            {/* 表單操作按鈕 - RWD 響應式 */}
            <Form.Item style={{ marginBottom: 0 }}>
              {isMobile ? (
                // 手機版: 按鈕堆疊
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button type="primary" htmlType="submit" loading={loading} block>
                    更新公文
                  </Button>
                  <Button onClick={() => navigate('/documents')} block>
                    取消
                  </Button>
                </Space>
              ) : (
                // 桌面版: 按鈕並排靠右
                <div style={{ textAlign: 'right' }}>
                  <Button
                    onClick={() => navigate('/documents')}
                    style={{ marginRight: 8 }}
                  >
                    取消
                  </Button>
                  <Button type="primary" htmlType="submit" loading={loading}>
                    更新公文
                  </Button>
                </div>
              )}
            </Form.Item>
          </Form>
        </Card>
      </div>
    </div>
  );
};
