import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  App,
  Upload,
  Card,
  Space,
  Row,
  Col,
  Tag,
  Tabs,
  List,
  Popconfirm,
  Spin,
  Empty,
} from 'antd';
import {
  InboxOutlined,
  FileTextOutlined,
  SendOutlined,
  CopyOutlined,
  CalendarOutlined,
  DownloadOutlined,
  DeleteOutlined,
  PaperClipOutlined,
} from '@ant-design/icons';
import { Document } from '../../types';
import dayjs from 'dayjs';
import { calendarIntegrationService } from '../../services/calendarIntegrationService';
import { apiClient } from '../../api/client';
import { API_BASE_URL } from '../../api/client';

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
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [fileList, setFileList] = useState<any[]>([]);
  const [cases, setCases] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);
  // 附件相關狀態
  const [existingAttachments, setExistingAttachments] = useState<any[]>([]);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);

  const isReadOnly = operation === 'view';
  const isCreate = operation === 'create';
  const isCopy = operation === 'copy';

  // 專案同仁資料 (依專案 ID 快取)
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, any[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  // 專案同仁快取 ref（避免閉包問題）
  const projectStaffCacheRef = React.useRef<Record<number, any[]>>({});

  // 根據專案 ID 取得業務同仁列表
  const fetchProjectStaff = async (projectId: number): Promise<any[]> => {
    // 檢查快取 (使用 ref 避免閉包問題)
    if (projectStaffCacheRef.current[projectId]) {
      const cachedData = projectStaffCacheRef.current[projectId];
      // 確保 state 也有資料（觸發 re-render）
      setProjectStaffMap(prev => ({ ...prev, [projectId]: cachedData }));
      return cachedData;
    }

    setStaffLoading(true);
    try {
      const data = await apiClient.post<{
        staff?: any[];
        total?: number;
      }>(`/project-staff/project/${projectId}/list`, {});
      const staffData = data.staff || [];
      // 同時更新 ref 和 state
      projectStaffCacheRef.current[projectId] = staffData;
      setProjectStaffMap(prev => ({ ...prev, [projectId]: staffData }));
      return staffData;
    } catch (error) {
      console.error('Failed to fetch project staff:', error);
      return [];
    } finally {
      setStaffLoading(false);
    }
  };

  // 選擇專案後自動填入所有業務同仁
  const handleProjectChange = async (projectId: number | null | undefined) => {
    console.log('[handleProjectChange] 選擇專案:', projectId);

    // 處理 undefined (allowClear 時會傳入 undefined)
    const effectiveProjectId = projectId ?? null;

    // 先更新承攬案件欄位
    form.setFieldsValue({ contract_project_id: effectiveProjectId });

    if (!effectiveProjectId) {
      // 清除專案時，也清除業務同仁欄位
      setSelectedProjectId(null);
      form.setFieldsValue({ assignee: [] });
      return;
    }

    // 取得專案業務同仁資料
    const staffList = await fetchProjectStaff(effectiveProjectId);
    console.log('[handleProjectChange] 取得業務同仁:', staffList);

    // 直接填入所有業務同仁（不等待 state 更新）
    if (!staffList || staffList.length === 0) {
      setSelectedProjectId(effectiveProjectId);
      message.info('此專案尚無指派業務同仁');
      return;
    }

    const allStaffNames = staffList.map((s: any) => s.user_name);
    console.log('[handleProjectChange] 準備填入:', allStaffNames);

    // 同時更新 selectedProjectId 和 form 值
    // 使用函數式更新確保順序正確
    setSelectedProjectId(effectiveProjectId);

    // 延遲設定 form 值，等待 projectStaffMap 更新後 options 會包含正確選項
    setTimeout(() => {
      // 再次檢查確保有資料
      const currentStaff = projectStaffCacheRef.current[effectiveProjectId];
      if (currentStaff && currentStaff.length > 0) {
        const names = currentStaff.map((s: any) => s.user_name);
        form.setFieldsValue({ assignee: names });
        console.log('[handleProjectChange] 已填入業務同仁:', names);
        message.success(`已自動填入 ${names.length} 位業務同仁`);
      }
    }, 150);
  };

  // 取得公文附件列表 (POST-only 資安機制)
  const fetchAttachments = async (documentId: number) => {
    setAttachmentsLoading(true);
    try {
      const data = await apiClient.post<{
        document_id: number;
        attachments: any[];
      }>(`/files/document/${documentId}`, {});
      setExistingAttachments(data.attachments || []);
    } catch (error) {
      console.error('Failed to fetch attachments:', error);
      setExistingAttachments([]);
    } finally {
      setAttachmentsLoading(false);
    }
  };

  // 上傳檔案
  const uploadFiles = async (documentId: number, files: any[]) => {
    if (files.length === 0) return;

    const formData = new FormData();
    files.forEach(file => {
      if (file.originFileObj) {
        formData.append('files', file.originFileObj);
      }
    });

    try {
      const response = await fetch(`${API_BASE_URL}/files/upload?document_id=${documentId}`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      const result = await response.json();
      console.log('[uploadFiles] 上傳成功:', result);
      return result;
    } catch (error) {
      console.error('Failed to upload files:', error);
      throw error;
    }
  };

  // 下載附件 (POST-only 資安機制)
  const handleDownload = async (attachmentId: number, filename: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/files/${attachmentId}/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('下載失敗');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'download';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('下載附件失敗:', error);
      message.error('下載附件失敗');
    }
  };

  // 刪除附件 (POST-only 資安機制)
  const handleDeleteAttachment = async (attachmentId: number) => {
    try {
      await apiClient.post(`/files/${attachmentId}/delete`, {});
      message.success('附件刪除成功');
      // 重新載入附件列表
      if (document?.id) {
        fetchAttachments(document.id);
      }
    } catch (error) {
      console.error('Failed to delete attachment:', error);
      message.error('附件刪除失敗');
    }
  };

  // 載入承攬案件數據
  useEffect(() => {
    const fetchCases = async () => {
      setCasesLoading(true);
      try {
        // POST-only 資安機制 (使用 apiClient 確保正確的 base URL)
        const data = await apiClient.post<{
          projects?: any[];
          items?: any[];
          total?: number;
        }>('/projects/list', { page: 1, limit: 100 });
        // 適應新的API回應格式
        const projectsData = data.projects || data.items || [];
        setCases(Array.isArray(projectsData) ? projectsData : []);
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
        // POST-only 資安機制 (使用 apiClient 確保正確的 base URL)
        const data = await apiClient.post<{
          users?: any[];
          items?: any[];
          total?: number;
        }>('/users/list', { page: 1, limit: 100 });
        // 處理可能的不同回應格式
        const usersData = data.users || data.items || [];
        setUsers(Array.isArray(usersData) ? usersData : []);
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
      // 處理 assignee 欄位：字串轉陣列（支援逗號分隔）
      let assigneeArray: string[] = [];
      const rawAssignee = (document as any).assignee;
      if (rawAssignee) {
        if (Array.isArray(rawAssignee)) {
          assigneeArray = rawAssignee;
        } else if (typeof rawAssignee === 'string') {
          assigneeArray = rawAssignee.split(',').map((s: string) => s.trim()).filter(Boolean);
        }
      }

      const formValues = {
        ...document,
        doc_date: document.doc_date ? dayjs(document.doc_date) : null,
        receive_date: document.receive_date ? dayjs(document.receive_date) : null,
        send_date: document.send_date ? dayjs(document.send_date) : null,
        assignee: assigneeArray,
      };

      if (isCopy) {
        // 複製時清除ID和重複欄位
        delete (formValues as any).id;
        formValues.doc_number = `${document.doc_number}-副本`;
      }

      form.setFieldsValue(formValues);

      // 設定選中的專案 ID 並載入該專案的業務同仁
      const projectId = (document as any).contract_project_id;
      if (projectId) {
        setSelectedProjectId(projectId);
        // 載入專案業務同仁，如果公文沒有指定 assignee 則自動填入
        fetchProjectStaff(projectId).then(staffList => {
          if (staffList && staffList.length > 0 && assigneeArray.length === 0) {
            // 公文沒有指定業務同仁，自動從專案填入
            const allStaffNames = staffList.map((s: any) => s.user_name);
            setTimeout(() => {
              form.setFieldsValue({ assignee: allStaffNames });
              console.log('[載入公文] 自動填入專案業務同仁:', allStaffNames);
            }, 100);
          }
        });
      } else {
        setSelectedProjectId(null);
      }

      // 載入公文附件列表
      if (document.id && !isCopy) {
        fetchAttachments(document.id);
      }
    } else if (visible && isCreate) {
      form.resetFields();
      setSelectedProjectId(null);
      setExistingAttachments([]);
      setFileList([]);
    }
  }, [visible, document, form, isCreate, isCopy]);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();

      // 處理 assignee：陣列轉逗號分隔字串
      let assigneeStr = '';
      if (Array.isArray(values.assignee)) {
        assigneeStr = values.assignee.join(', ');
      } else if (values.assignee) {
        assigneeStr = values.assignee;
      }

      const documentData = {
        ...values,
        doc_date: values.doc_date?.format('YYYY-MM-DD'),
        receive_date: values.receive_date?.format('YYYY-MM-DD'),
        send_date: values.send_date?.format('YYYY-MM-DD'),
        assignee: assigneeStr,
      };

      await onSave(documentData);

      // 上傳新附件（僅限編輯既有公文）
      if (document?.id && fileList.length > 0) {
        try {
          await uploadFiles(document.id, fileList);
          message.success(`附件上傳成功（共 ${fileList.length} 個檔案）`);
          setFileList([]); // 清空上傳列表
        } catch (uploadError) {
          console.error('File upload failed:', uploadError);
          message.warning('公文儲存成功，但附件上傳失敗');
        }
      }

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
                        name="contract_project_id"
                      >
                        <Select
                          placeholder="請選擇承攬案件"
                          loading={casesLoading || staffLoading}
                          allowClear
                          showSearch
                          filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                          }
                          onChange={handleProjectChange}
                          options={Array.isArray(cases) ? cases.map(case_ => ({
                            value: case_.id,
                            label: case_.project_name || case_.case_name || '未命名案件',
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
                          mode="multiple"
                          placeholder="請選擇業務同仁（可複選）"
                          loading={usersLoading || staffLoading}
                          allowClear
                          showSearch
                          filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                          }
                          options={
                            // 優先顯示專案指定的業務同仁，若無則顯示全部使用者
                            selectedProjectId && projectStaffMap[selectedProjectId]?.length > 0
                              ? projectStaffMap[selectedProjectId].map(staff => ({
                                  value: staff.user_name,
                                  label: staff.role ? `${staff.user_name}(${staff.role})` : staff.user_name,
                                  key: staff.user_id || staff.id
                                }))
                              : Array.isArray(users) ? users.map(user => ({
                                  value: user.full_name || user.username,
                                  label: user.full_name || user.username,
                                  key: user.id
                                })) : []
                          }
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
              label: (
                <span>
                  附件上傳
                  {existingAttachments.length > 0 && (
                    <Tag color="blue" style={{ marginLeft: 8 }}>{existingAttachments.length}</Tag>
                  )}
                </span>
              ),
              children: (
                <Spin spinning={attachmentsLoading}>
                  {/* 既有附件列表 */}
                  {existingAttachments.length > 0 && (
                    <Card
                      size="small"
                      title={
                        <Space>
                          <PaperClipOutlined />
                          <span>已上傳附件（{existingAttachments.length} 個）</span>
                        </Space>
                      }
                      style={{ marginBottom: 16 }}
                    >
                      <List
                        size="small"
                        dataSource={existingAttachments}
                        renderItem={(item: any) => (
                          <List.Item
                            actions={[
                              <Button
                                key="download"
                                type="link"
                                size="small"
                                icon={<DownloadOutlined />}
                                onClick={() => handleDownload(item.id, item.original_filename)}
                              >
                                下載
                              </Button>,
                              !isReadOnly && (
                                <Popconfirm
                                  key="delete"
                                  title="確定要刪除此附件嗎？"
                                  onConfirm={() => handleDeleteAttachment(item.id)}
                                  okText="確定"
                                  cancelText="取消"
                                >
                                  <Button
                                    type="link"
                                    size="small"
                                    danger
                                    icon={<DeleteOutlined />}
                                  >
                                    刪除
                                  </Button>
                                </Popconfirm>
                              ),
                            ].filter(Boolean)}
                          >
                            <List.Item.Meta
                              avatar={<PaperClipOutlined style={{ fontSize: 20, color: '#1890ff' }} />}
                              title={item.original_filename || item.filename}
                              description={
                                <span style={{ fontSize: 12, color: '#999' }}>
                                  {item.file_size ? `${(item.file_size / 1024).toFixed(1)} KB` : ''}
                                  {item.created_at && ` · ${dayjs(item.created_at).format('YYYY-MM-DD HH:mm')}`}
                                </span>
                              }
                            />
                          </List.Item>
                        )}
                      />
                    </Card>
                  )}

                  {/* 上傳區域（非唯讀模式才顯示）*/}
                  {!isReadOnly ? (
                    <Form.Item label="上傳新附件">
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
                    existingAttachments.length === 0 && (
                      <Empty
                        description="此公文尚無附件"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                      />
                    )
                  )}
                </Spin>
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
                      {(document as any).creator || '系統'}
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
  const { message } = App.useApp();
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