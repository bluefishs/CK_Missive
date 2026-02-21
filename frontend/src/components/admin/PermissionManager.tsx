import React, { useState, useMemo } from 'react';
import {
  Card,
  Badge,
  Space,
  Typography,
  Divider,
  Row,
  Col,
  Checkbox,
  Button,
  Select,
  App
} from 'antd';
import {
  SecurityScanOutlined,
  FileTextOutlined,
  ProjectOutlined,
  BankOutlined,
  ShopOutlined,
  CalendarOutlined,
  BarChartOutlined,
  SettingOutlined
} from '@ant-design/icons';

import { PERMISSION_CATEGORIES } from '../../constants/permissions';

const { Title, Text } = Typography;
const { Option } = Select;

interface PermissionManagerProps {
  userPermissions?: string[];
  onPermissionChange?: (permissions: string[]) => void;
  readOnly?: boolean;
}

const categoryIcons: Record<string, React.ReactNode> = {
  documents: <FileTextOutlined />,
  projects: <ProjectOutlined />,
  agencies: <BankOutlined />,
  vendors: <ShopOutlined />,
  calendar: <CalendarOutlined />,
  reports: <BarChartOutlined />,
  system_docs: <FileTextOutlined style={{ color: '#722ed1' }} />,
  admin: <SettingOutlined />
};

export const PermissionManager: React.FC<PermissionManagerProps> = ({
  userPermissions = [],
  onPermissionChange,
  readOnly = false
}) => {
  const { message } = App.useApp();
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>(userPermissions);
  const [language, setLanguage] = useState<'zh' | 'en'>('zh');
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- reserved for future tree view rendering
  const _treeData = useMemo(() => {
    return Object.entries(PERMISSION_CATEGORIES).map(([categoryKey, category]) => ({
      title: (
        <Space>
          {categoryIcons[categoryKey]}
          <Text strong>
            {language === 'zh' ? category.name_zh : category.name_en}
          </Text>
          <Badge
            count={category.permissions.length}
            size="small"
            color="blue"
          />
        </Space>
      ),
      key: categoryKey,
      selectable: false,
      children: category.permissions.map(permission => ({
        title: (
          <Space direction="vertical" size={0}>
            <Text>
              {language === 'zh' ? permission.name_zh : permission.name_en}
            </Text>
            {permission.description_zh && permission.description_en && (
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {language === 'zh' ? permission.description_zh : permission.description_en}
              </Text>
            )}
          </Space>
        ),
        key: permission.key
      }))
    }));
  }, [language]);

  const handlePermissionToggle = (permissionKey: string, checked: boolean) => {
    if (readOnly) return;

    const newPermissions = checked 
      ? [...selectedPermissions, permissionKey]
      : selectedPermissions.filter(p => p !== permissionKey);
    
    setSelectedPermissions(newPermissions);
    onPermissionChange?.(newPermissions);
  };

  const handleCategoryToggle = (categoryKey: string, checked: boolean) => {
    if (readOnly) return;

    const category = PERMISSION_CATEGORIES[categoryKey];
    if (!category) return;

    const categoryPermissions = category.permissions.map(p => p.key);
    let newPermissions: string[];

    if (checked) {
      // 添加整個分類的權限
      newPermissions = [...selectedPermissions];
      categoryPermissions.forEach(perm => {
        if (!newPermissions.includes(perm)) {
          newPermissions.push(perm);
        }
      });
    } else {
      // 移除整個分類的權限
      newPermissions = selectedPermissions.filter(
        perm => !categoryPermissions.includes(perm)
      );
    }

    setSelectedPermissions(newPermissions);
    onPermissionChange?.(newPermissions);
  };

  const isCategorySelected = (categoryKey: string) => {
    const category = PERMISSION_CATEGORIES[categoryKey];
    if (!category) return false;
    
    const categoryPermissions = category.permissions.map(p => p.key);
    return categoryPermissions.every(perm => selectedPermissions.includes(perm));
  };

  const isCategoryPartialSelected = (categoryKey: string) => {
    const category = PERMISSION_CATEGORIES[categoryKey];
    if (!category) return false;
    
    const categoryPermissions = category.permissions.map(p => p.key);
    const selectedCount = categoryPermissions.filter(perm => 
      selectedPermissions.includes(perm)
    ).length;
    
    return selectedCount > 0 && selectedCount < categoryPermissions.length;
  };

  const handleSelectAll = () => {
    if (readOnly) return;

    const allPermissions = Object.values(PERMISSION_CATEGORIES)
      .flatMap(category => category.permissions.map(p => p.key));
    
    setSelectedPermissions(allPermissions);
    onPermissionChange?.(allPermissions);
    message.success(language === 'zh' ? '已選擇全部權限' : 'All permissions selected');
  };

  const handleDeselectAll = () => {
    if (readOnly) return;

    setSelectedPermissions([]);
    onPermissionChange?.([]);
    message.success(language === 'zh' ? '已清除全部權限' : 'All permissions cleared');
  };

  return (
    <Card>
      <div style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4}>
              <SecurityScanOutlined /> {language === 'zh' ? '權限管理' : 'Permission Management'}
            </Title>
          </Col>
          <Col>
            <Space>
              <Select
                value={language}
                onChange={setLanguage}
                style={{ width: 120 }}
              >
                <Option value="zh">中文</Option>
                <Option value="en">English</Option>
              </Select>
              {!readOnly && (
                <>
                  <Button size="small" onClick={handleSelectAll}>
                    {language === 'zh' ? '全選' : 'Select All'}
                  </Button>
                  <Button size="small" onClick={handleDeselectAll}>
                    {language === 'zh' ? '清除' : 'Clear All'}
                  </Button>
                </>
              )}
            </Space>
          </Col>
        </Row>
      </div>

      <Divider />

      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">
          {language === 'zh' 
            ? `已選擇 ${selectedPermissions.length} 個權限`
            : `${selectedPermissions.length} permissions selected`
          }
        </Text>
      </div>

      <Row gutter={[16, 16]}>
        {Object.entries(PERMISSION_CATEGORIES).map(([categoryKey, category]) => (
          <Col xs={24} sm={12} lg={8} key={categoryKey}>
            <Card 
              size="small"
              title={
                <Space>
                  {categoryIcons[categoryKey]}
                  <Text strong>
                    {language === 'zh' ? category.name_zh : category.name_en}
                  </Text>
                  <Badge
                    count={`${category.permissions.filter(p => selectedPermissions.includes(p.key)).length}/${category.permissions.length}`}
                    size="small"
                    color="blue"
                  />
                </Space>
              }
              extra={
                !readOnly && (
                  <Checkbox
                    checked={isCategorySelected(categoryKey)}
                    indeterminate={isCategoryPartialSelected(categoryKey)}
                    onChange={(e) => handleCategoryToggle(categoryKey, e.target.checked)}
                  >
                    {language === 'zh' ? '全選' : 'All'}
                  </Checkbox>
                )
              }
            >
              <Space direction="vertical" style={{ width: '100%' }} size={8}>
                {category.permissions.map(permission => (
                  <div key={permission.key} style={{ display: 'flex', alignItems: 'flex-start' }}>
                    <Checkbox
                      checked={selectedPermissions.includes(permission.key)}
                      onChange={(e) => handlePermissionToggle(permission.key, e.target.checked)}
                      disabled={readOnly}
                      style={{ marginRight: 8, marginTop: 2 }}
                    />
                    <div style={{ flex: 1 }}>
                      <div>
                        <Text style={{ fontSize: '14px' }}>
                          {language === 'zh' ? permission.name_zh : permission.name_en}
                        </Text>
                      </div>
                      {permission.description_zh && permission.description_en && (
                        <div>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {language === 'zh' ? permission.description_zh : permission.description_en}
                          </Text>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  );
};

export default PermissionManager;