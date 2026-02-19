import React, { useState, useRef, useEffect } from 'react';
import {
  Input,
  Button,
  Space,
  Typography,
  Tooltip,
  Popover,
  Tag,
  Card,
  List,
  Avatar,
  message
} from 'antd';
import {
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  HistoryOutlined,
  UserOutlined,
  ClockCircleOutlined,
  MessageOutlined,
  ExpandOutlined,
  CompressOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

export interface RemarkHistory {
  id: string;
  content: string;
  author: string;
  authorName: string;
  timestamp: string;
  action: 'create' | 'update' | 'delete';
}

export interface RemarksFieldProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  maxLength?: number;
  showHistory?: boolean;
  allowRichText?: boolean;
  autoSize?: boolean | { minRows?: number; maxRows?: number };
  history?: RemarkHistory[];
  onSave?: (content: string) => void;
  currentUser?: {
    id: string;
    name: string;
  };
  inline?: boolean; // 是否行內編輯模式
  compact?: boolean; // 緊湊模式
}

const RemarksField: React.FC<RemarksFieldProps> = ({
  value = '',
  onChange,
  placeholder = '點擊添加備註說明...',
  disabled = false,
  maxLength = 1000,
  showHistory = true,
  allowRichText = false,
  autoSize = { minRows: 3, maxRows: 8 },
  history = [],
  onSave,
  currentUser = { id: '1', name: '當前使用者' },
  inline = false,
  compact = false
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [currentContent, setCurrentContent] = useState(value);
  const [expanded, setExpanded] = useState(false);
  const textAreaRef = useRef<any>(null);

  useEffect(() => {
    setCurrentContent(value);
  }, [value]);

  useEffect(() => {
    if (isEditing && textAreaRef.current) {
      textAreaRef.current.focus();
    }
  }, [isEditing]);

  const handleEdit = () => {
    setIsEditing(true);
    setCurrentContent(value);
  };

  const handleSave = () => {
    if (currentContent !== value) {
      onChange?.(currentContent);
      onSave?.(currentContent);
      message.success('備註已保存');
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setCurrentContent(value);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  // 歷史記錄內容
  const historyContent = (
    <div style={{ width: 400, maxHeight: 400, overflow: 'auto' }}>
      <div style={{ marginBottom: 12 }}>
        <Text strong>備註歷史記錄</Text>
      </div>
      <List
        size="small"
        dataSource={history}
        renderItem={(item) => (
          <List.Item>
            <List.Item.Meta
              avatar={<Avatar size="small" icon={<UserOutlined />} />}
              title={
                <Space>
                  <Text style={{ fontSize: 12 }}>{item.authorName}</Text>
                  <Tag color={
                    item.action === 'create' ? 'green' :
                    item.action === 'update' ? 'blue' : 'red'
                  }>
                    {item.action === 'create' ? '新增' : 
                     item.action === 'update' ? '修改' : '刪除'}
                  </Tag>
                </Space>
              }
              description={
                <div>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {dayjs(item.timestamp).format('YYYY-MM-DD HH:mm')}
                  </Text>
                  <Paragraph
                    style={{ margin: 0, fontSize: 12 }}
                    ellipsis={{ rows: 2, expandable: true }}
                  >
                    {item.content}
                  </Paragraph>
                </div>
              }
            />
          </List.Item>
        )}
        locale={{ emptyText: '暫無歷史記錄' }}
      />
    </div>
  );

  // 緊湊模式渲染
  if (compact) {
    return (
      <Space.Compact style={{ width: '100%' }}>
        <Input
          value={currentContent}
          onChange={(e) => setCurrentContent(e.target.value)}
          onBlur={handleSave}
          placeholder={placeholder}
          disabled={disabled}
          maxLength={maxLength}
          suffix={
            <Space size={4}>
              {showHistory && history.length > 0 && (
                <Popover content={historyContent} trigger="click" placement="bottomRight">
                  <Button type="text" size="small" icon={<HistoryOutlined />} aria-label="查看歷史記錄" />
                </Popover>
              )}
              <Text type="secondary" style={{ fontSize: 11 }}>
                {currentContent.length}/{maxLength}
              </Text>
            </Space>
          }
        />
      </Space.Compact>
    );
  }

  // 行內編輯模式
  if (inline) {
    if (!isEditing) {
      return (
        <div
          onClick={!disabled ? handleEdit : undefined}
          style={{
            minHeight: 32,
            padding: '8px 12px',
            border: '1px dashed #d9d9d9',
            borderRadius: 6,
            cursor: disabled ? 'default' : 'pointer',
            backgroundColor: disabled ? '#f5f5f5' : '#fafafa',
            transition: 'all 0.2s'
          }}
        >
          {value ? (
            <Paragraph
              ellipsis={{ rows: 2, expandable: true }}
              style={{ margin: 0 }}
            >
              {value}
            </Paragraph>
          ) : (
            <Text type="secondary">{placeholder}</Text>
          )}
        </div>
      );
    }

    return (
      <div>
        <TextArea
          ref={textAreaRef}
          value={currentContent}
          onChange={(e) => setCurrentContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoSize={autoSize}
          maxLength={maxLength}
          showCount
        />
        <div style={{ marginTop: 8, textAlign: 'right' }}>
          <Space>
            <Button size="small" onClick={handleCancel} icon={<CloseOutlined />}>
              取消
            </Button>
            <Button
              size="small"
              type="primary"
              onClick={handleSave}
              icon={<SaveOutlined />}
            >
              保存 (Ctrl+Enter)
            </Button>
          </Space>
        </div>
      </div>
    );
  }

  // 標準模式
  return (
    <Card
      size="small"
      title={
        <Space>
          <MessageOutlined />
          <Text>備註說明</Text>
          {value && (
            <Text type="secondary">
              ({currentContent.length} 字)
            </Text>
          )}
        </Space>
      }
      extra={
        <Space>
          {showHistory && history.length > 0 && (
            <Popover content={historyContent} trigger="click" placement="bottomLeft">
              <Tooltip title="查看歷史記錄">
                <Button
                  type="text"
                  size="small"
                  icon={<HistoryOutlined />}
                  aria-label="查看歷史記錄"
                />
              </Tooltip>
            </Popover>
          )}
          <Tooltip title={expanded ? "收起" : "展開"}>
            <Button
              type="text"
              size="small"
              icon={expanded ? <CompressOutlined /> : <ExpandOutlined />}
              onClick={() => setExpanded(!expanded)}
              aria-label={expanded ? '收起' : '展開'}
            />
          </Tooltip>
          {!isEditing && !disabled && (
            <Tooltip title="編輯備註">
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={handleEdit}
                aria-label="編輯備註"
              />
            </Tooltip>
          )}
        </Space>
      }
    >
      {!isEditing ? (
        <div style={{ minHeight: expanded ? 'auto' : 60 }}>
          {value ? (
            <Paragraph
              ellipsis={!expanded ? { rows: 2, expandable: false } : false}
              style={{ margin: 0 }}
            >
              {value}
            </Paragraph>
          ) : (
            <div
              onClick={!disabled ? handleEdit : undefined}
              style={{
                padding: 16,
                textAlign: 'center',
                color: '#bfbfbf',
                cursor: disabled ? 'default' : 'pointer',
                border: '1px dashed #d9d9d9',
                borderRadius: 6,
                backgroundColor: '#fafafa'
              }}
            >
              <Text type="secondary">{placeholder}</Text>
            </div>
          )}
        </div>
      ) : (
        <div>
          <TextArea
            ref={textAreaRef}
            value={currentContent}
            onChange={(e) => setCurrentContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            autoSize={expanded ? { minRows: 6, maxRows: 12 } : autoSize}
            maxLength={maxLength}
            showCount
          />
          <div style={{ marginTop: 12, textAlign: 'right' }}>
            <Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                <ClockCircleOutlined /> Ctrl+Enter 快速保存，Esc 取消
              </Text>
              <Button size="small" onClick={handleCancel}>
                取消
              </Button>
              <Button
                size="small"
                type="primary"
                onClick={handleSave}
                disabled={currentContent === value}
              >
                保存
              </Button>
            </Space>
          </div>
        </div>
      )}
    </Card>
  );
};

export default RemarksField;