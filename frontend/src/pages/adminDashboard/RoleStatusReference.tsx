import React from 'react';
import { Card, Row, Col, Badge, Space, Typography, Flex } from 'antd';
import { USER_ROLES, USER_STATUSES } from '../../constants/permissions';

const { Text } = Typography;

const RoleStatusReference: React.FC = () => (
  <Row gutter={16}>
    <Col xs={24} md={12}>
      <Card title="系統角色說明">
        <Flex vertical>
          {Object.entries(USER_ROLES).map(([key, role]) => (
            <Flex
              key={key}
              align="flex-start"
              gap={12}
              style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}
            >
              <Badge status={role.can_login ? 'success' : 'error'} />
              <div>
                <Text strong>{role.name_zh}</Text>
                <Space vertical size={0}>
                  <Text type="secondary">{role.description_zh}</Text>
                  <Text type="secondary" style={{ fontSize: '11px' }}>
                    權限數量: {role.default_permissions.length}
                    {!role.can_login && ' \u2022 無法登入'}
                  </Text>
                </Space>
              </div>
            </Flex>
          ))}
        </Flex>
      </Card>
    </Col>
    <Col xs={24} md={12}>
      <Card title="使用者狀態說明">
        <Flex vertical>
          {Object.entries(USER_STATUSES).map(([key, status]) => (
            <Flex
              key={key}
              align="flex-start"
              gap={12}
              style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}
            >
              <Badge status={status.can_login ? 'success' : 'error'} />
              <div>
                <Text strong>{status.name_zh}</Text>
                <Space vertical size={0}>
                  <Text type="secondary">{status.description_zh}</Text>
                  {!status.can_login && (
                    <Text type="secondary" style={{ fontSize: '11px', color: '#f5222d' }}>
                      此狀態下無法登入系統
                    </Text>
                  )}
                </Space>
              </div>
            </Flex>
          ))}
        </Flex>
      </Card>
    </Col>
  </Row>
);

export default RoleStatusReference;
