import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  message,
  Upload,
  Card,
  Divider,
  Space,
  Row,
  Col,
  Tag,
  Tabs,
} from 'antd';
import {
  InboxOutlined,
  FileTextOutlined,
  SendOutlined,
  CopyOutlined,
  FileZipOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import { Document } from '../../types';
import dayjs from 'dayjs';
import { calendarIntegrationService } from '../../services/calendarIntegrationService';

const { TextArea } = Input;
const { Option } = Select;
const { Dragger } = Upload;

interface DocumentOperationsProps {
  document: Document | null;
  operation: 'view' | 'edit' | 'create' | 'copy' | null;
  visible: boolean;
  onClose: () => void;
  onSave: (document: Partial<Document>) => Promise<void>;
}

export const DocumentOperations: React.FC<DocumentOperationsProps> = ({
  document,
  operation,
  visible,
  onClose,
  onSave,
}) => {
  // Force refresh timestamp: 2025-09-16-13:01
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [fileList, setFileList] = useState<any[]>([]);
  const [cases, setCases] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);

  const isReadOnly = operation === 'view';
  const isCreate = operation === 'create';
  const isCopy = operation === 'copy';

  // 載入承攬案件數據
  useEffect(() => {
    const fetchCases = async () => {
      setCasesLoading(true);
      try {
        const response = await fetch('/api/projects');
        if (response.ok) {
          const data = await response.json();
          // 適應新的API回應格式
          const projectsData = data.projects || data.items || data || [];
          setCases(Array.isArray(projectsData) ? projectsData : []);
        } else {
          setCases([]);
        }
      } catch (error) {
        console.error('Failed to fetch projects:', error);
        setCases([]);
      } finally {
        setCasesLoading(false);
      }
    };

    const fetchUsers = async () => {
      setUsersLoading(true);
      try {
        const response = await fetch('/api/users');
        if (response.ok) {
          const data = await response.json();
          // 處理可能的不同回應格式
          const usersData = data.users || data.items || data || [];
          setUsers(Array.isArray(usersData) ? usersData : []);
        } else {
          console.warn('Failed to fetch users from /api/users, status:', response.status);
          setUsers([]);
        }
      } catch (error) {
        console.error('Failed to fetch users:', error);
        setUsers([]);
      } finally {
        setUsersLoading(false);
      }
    };

    if (visible) {
      fetchCases();
      fetchUsers();
    }
  }, [visible]);

  React.useEffect(() => {
    if (visible && document) {
      const formValues = {
        ...document,
        doc_date: document.doc_date ? dayjs(document.doc_date) : null,
        receive_date: document.receive_date ? dayjs(document.receive_date) : null,
        send_date: document.send_date ? dayjs(document.send_date) : null,
      };

      if (isCopy) {
        // 複製時清除ID和重複欄位
        formValues.id = undefined;
        formValues.doc_number = `${document.doc_number}-副本`;
      }

      form.setFieldsValue(formValues);
    } else if (visible && isCreate) {
      form.resetFields();
    }
  }, [visible, document, form, isCreate, isCopy]);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      
      const documentData = {
        ...values,
        doc_date: values.doc_date?.format('YYYY-MM-DD'),
        receive_date: values.receive_date?.format('YYYY-MM-DD'),
        send_date: values.send_date?.format('YYYY-MM-DD'),
      };

      await onSave(documentData);
      message.success(`${getOperationText()}成功！`);
      onClose();
    } catch (error) {
      console.error('Save document failed:', error);
      message.error(`${getOperationText()}失敗`);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCalendar = async () => {
    if (!document) return;

    try {
      setCalendarLoading(true);
      await calendarIntegrationService.addDocumentToCalendar(document);
      // 成功訊息已在服務中處理
    } catch (error) {
      console.error('Add to calendar failed:', error);
      // 錯誤訊息已在服務中處理
    } finally {
      setCalendarLoading(false);
    }
  };

  const getOperationText = () => {
    switch (operation) {
      case 'create': return '新增公文';
      case 'edit': return '修改公文';
      case 'copy': return '複製公文';
      default: return '儲存';
    }
  };

  const getModalTitle = () => {
    const icons = {
      view: <FileTextOutlined />,
      edit: <FileTextOutlined />,
      create: <FileTextOutlined />,
      copy: <CopyOutlined />,
    };

    const titles = {
      view: '查看公文詳情',
      edit: '編輯公文',
      create: '新增公文',
      copy: '複製公文',
    };

    return (
      <Space>
        {operation && icons[operation]}
        {operation && titles[operation]}
      </Space>
    );
  };

  const uploadProps = {
    multiple: true,
    fileList,
    beforeUpload: () => false, // 阻止自動上傳，我們將手動處理
    onChange: ({ fileList: newFileList }: any) => {
      setFileList(newFileList);
    },
    onRemove: (file: any) => {
      const newFileList = fileList.filter(item => item.uid !== file.uid);
      setFileList(newFileList);
    },
    onPreview: (file: any) => {
      // 可以添加檔案預覽功能
      console.log('Preview file:', file.name);
    },
  };

  return (
    <Modal
      title={getModalTitle()}
      open={visible}
      onCancel={onClose}
      width={800}
      footer={
        isReadOnly ? (
          <Space>
            {document && (
              <Button
                icon={<CalendarOutlined />}
                loading={calendarLoading}
                onClick={handleAddToCalendar}
              >
                加入行事曆
              </Button>
            )}
            <Button onClick={onClose}>關閉</Button>
          </Space>
        ) : (
          <Space>
            <Button onClick={onClose}>取消</Button>
            <Button
              type="primary"
              loading={loading}
              onClick={handleSubmit}
            >
              {getOperationText()}
            </Button>
          </Space>
        )
      }
    >
      <Form
        form={form}
        layout="vertical"
        disabled={isReadOnly}
      >
        <Tabs
          defaultActiveKey="1"
          items={[
            {
              key: '1',
              label: '基本資料',
              children: (
                <>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        label="文件類型"
                        name="doc_type"
                        rules={[{ required: true, message: '請選擇文件類型' }]}
                      >
                        <Select placeholder="請選擇文件類型">
                          <Option value="函">函</Option>
                          <Option value="開會通知單">開會通知單</Option>
                          <Option value="會勘通知單">會勘通知單</Option>
                        </Select>
                      </Form.Item>
                    </Col>

                    <Col span={12}>
                      <Form.Item
                        label="公文字號"
                        name="doc_number"
                        rules={[{ required: true, message: '請輸入公文字號' }]}
                      >
                        <Input placeholder="如：乾坤字第1130001號" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        label="發文機關"
                        name="sender"
                        rules={[{ required: true, message: '請輸入發文機關' }]}
                      >
                        <Input placeholder="請輸入發文機關" />
                      </Form.Item>
                    </Col>

                    <Col span={12}>
                      <Form.Item
                        label="受文者"
                        name="receiver"
                      >
                        <Input placeholder="請輸入受文者" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item
                    label="主旨"
                    name="subject"
                    rules={[{ required: true, message: '請輸入主旨' }]}
                  >
                    <TextArea
                      rows={2}
                      placeholder="請輸入公文主旨"
                      maxLength={200}
                      showCount
                    />
                  </Form.Item>

                  <Form.Item
                    label="說明"
                    name="content"
                  >
                    <TextArea
                      rows={4}
                      placeholder="請輸入公文內容說明"
                      maxLength={1000}
                      showCount
                    />
                  </Form.Item>
                </>
              )
            },
            {
              key: '2',
              label: '日期與狀態',
              children: (
                <>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item
                        label="發文日期"
                        name="doc_date"
                      >
                        <DatePicker
                          style={{ width: '100%' }}
                          placeholder="請選擇發文日期"
                        />
                      </Form.Item>
                    </Col>

                    <Col span={8}>
                      <Form.Item
                        label="收文日期"
                        name="receive_date"
                      >
                        <DatePicker
                          style={{ width: '100%' }}
                          placeholder="請選擇收文日期"
                        />
                      </Form.Item>
                    </Col>

                    <Col span={8}>
                      <Form.Item
                        label="發送日期"
                        name="send_date"
                      >
                        <DatePicker
                          style={{ width: '100%' }}
                          placeholder="請選擇發送日期"
                        />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        label="優先等級"
                        name="priority"
                      >
                        <Select placeholder="請選擇優先等級">
                          <Option value={1}>
                            <Tag color="blue">1 - 最高</Tag>
                          </Option>
                          <Option value={2}>
                            <Tag color="green">2 - 高</Tag>
                          </Option>
                          <Option value={3}>
                            <Tag color="orange">3 - 普通</Tag>
                          </Option>
                          <Option value={4}>
                            <Tag color="red">4 - 低</Tag>
                          </Option>
                          <Option value={5}>
                            <Tag color="purple">5 - 最低</Tag>
                          </Option>
                        </Select>
                      </Form.Item>
                    </Col>

                    <Col span={12}>
                      <Form.Item
                        label="處理狀態"
                        name="status"
                      >
                        <Select placeholder="請選擇處理狀態">
                          <Option value="收文完成">收文完成</Option>
                          <Option value="使用者確認">使用者確認</Option>
                          <Option value="收文異常">收文異常</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                  </Row>
                </>
              )
            },
            {
              key: '3',
              label: '案件與人員',
              children: (
                <>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        label="承攬案件"
                        name="contract_case"
                      >
                        <Select
                          placeholder="請選擇承攬案件"
                          loading={casesLoading}
                          allowClear
                          showSearch
                          filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                          }
                          options={Array.isArray(cases) ? cases.map(case_ => ({
                            value: case_.project_name || case_.case_name,
                            label: case_.project_code
                              ? `${case_.project_code} - ${case_.project_name}`
                              : (case_.case_number
                                ? `${case_.case_number} - ${case_.case_name}`
                                : case_.project_name || case_.case_name),
                            key: case_.id
                          })) : []}
                        />
                      </Form.Item>
                    </Col>

                    <Col span={12}>
                      <Form.Item
                        label="業務同仁"
                        name="assignee"
                      >
                        <Select
                          placeholder="請選擇業務同仁"
                          loading={usersLoading}
                          allowClear
                          showSearch
                          filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                          }
                          options={Array.isArray(users) ? users.map(user => ({
                            value: user.full_name || user.username,
                            label: user.full_name ? `${user.full_name} (${user.username})` : user.username,
                            key: user.id
                          })) : []}
                        />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item
                    label="備註"
                    name="notes"
                  >
                    <TextArea
                      rows={3}
                      placeholder="請輸入備註"
                      maxLength={500}
                      showCount
                    />
                  </Form.Item>
                </>
              )
            },
            {
              key: '4',
              label: '附件上傳',
              children: (
                <>
                  {!isReadOnly ? (
                    <Form.Item label="附件上傳">
                      <Dragger {...uploadProps}>
                        <p className="ant-upload-drag-icon">
                          <InboxOutlined />
                        </p>
                        <p className="ant-upload-text">點擊或拖拽文件到此區域上傳</p>
                        <p className="ant-upload-hint">
                          支援單次或批量上傳，支援 PDF、DOC、DOCX、JPG、PNG 等格式
                        </p>
                      </Dragger>
                    </Form.Item>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                      查看模式下無法上傳附件
                    </div>
                  )}
                </>
              )
            },
            ...(isReadOnly && document ? [{
              key: '5',
              label: '系統資訊',
              children: (
                <Card size="small" title="系統資訊" type="inner">
                  <Row gutter={16}>
                    <Col span={8}>
                      <strong>建立時間:</strong><br />
                      {document.created_at ? dayjs(document.created_at).format('YYYY-MM-DD HH:mm') : '未知'}
                    </Col>
                    <Col span={8}>
                      <strong>修改時間:</strong><br />
                      {document.updated_at ? dayjs(document.updated_at).format('YYYY-MM-DD HH:mm') : '未知'}
                    </Col>
                    <Col span={8}>
                      <strong>建立者:</strong><br />
                      {document.creator || '系統'}
                    </Col>
                  </Row>
                </Card>
              )
            }] : [])
          ]}
        />
      </Form>
    </Modal>
  );
};

// 發送公文Modal
interface DocumentSendModalProps {
  document: Document | null;
  visible: boolean;
  onClose: () => void;
  onSend: (sendData: any) => Promise<void>;
}

export const DocumentSendModal: React.FC<DocumentSendModalProps> = ({
  document,
  visible,
  onClose,
  onSend,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      await onSend(values);
      message.success('公文發送成功！');
      onClose();
    } catch (error) {
      console.error('Send document failed:', error);
      message.error('公文發送失敗');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={
        <Space>
          <SendOutlined />
          發送公文
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" loading={loading} onClick={handleSend}>
            發送
          </Button>
        </Space>
      }
    >
      {document && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <strong>公文字號:</strong> {document.doc_number}
            </Col>
            <Col span={12}>
              <strong>主旨:</strong> {document.subject}
            </Col>
          </Row>
        </Card>
      )}

      <Form form={form} layout="vertical">
        <Form.Item
          label="收件人"
          name="recipients"
          rules={[{ required: true, message: '請選擇收件人' }]}
        >
          <Select
            mode="multiple"
            placeholder="請選擇收件人"
            options={[
              { label: '張三', value: 'zhang.san@example.com' },
              { label: '李四', value: 'li.si@example.com' },
              { label: '王五', value: 'wang.wu@example.com' },
            ]}
          />
        </Form.Item>

        <Form.Item
          label="發送方式"
          name="sendMethod"
          initialValue="email"
        >
          <Select>
            <Option value="email">電子郵件</Option>
            <Option value="internal">內部系統</Option>
            <Option value="both">兩者皆是</Option>
          </Select>
        </Form.Item>

        <Form.Item
          label="發送備註"
          name="sendNotes"
        >
          <TextArea rows={3} placeholder="請輸入發送備註" />
        </Form.Item>
      </Form>
    </Modal>
  );
};