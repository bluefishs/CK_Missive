import React from 'react';
import {
  Form,
  Row,
  Col,
  InputNumber,
  Divider,
  Alert,
} from 'antd';

const WORK_TYPE_AMOUNT_MAPPING: Record<
  string,
  { amountField: string; label: string }
> = {
  '01.地上物查估作業': { amountField: 'work_01_amount', label: '01.地上物查估' },
  '02.土地協議市價查估作業': { amountField: 'work_02_amount', label: '02.土地協議市價查估' },
  '03.土地徵收市價查估作業': { amountField: 'work_03_amount', label: '03.土地徵收市價查估' },
  '04.相關計畫書製作': { amountField: 'work_04_amount', label: '04.相關計畫書製作' },
  '05.測量作業': { amountField: 'work_05_amount', label: '05.測量作業' },
  '06.樁位測釘作業': { amountField: 'work_06_amount', label: '06.樁位測釘作業' },
  '07.辦理教育訓練': { amountField: 'work_07_amount', label: '07.辦理教育訓練' },
};

interface DispatchPaymentFieldsProps {
  mode: 'create' | 'edit' | 'quick';
  watchedWorkTypes: string[];
}

export const DispatchPaymentFields: React.FC<DispatchPaymentFieldsProps> = ({
  mode,
  watchedWorkTypes,
}) => {
  const validWorkTypes = watchedWorkTypes.filter(
    (wt) => WORK_TYPE_AMOUNT_MAPPING[wt]
  );

  return (
    <>
      <Divider titlePlacement="left">契金資訊</Divider>

      {mode === 'edit' ? (
        validWorkTypes.length > 0 ? (
          <Row gutter={16}>
            {validWorkTypes.map((wt) => {
              const mapping = WORK_TYPE_AMOUNT_MAPPING[wt];
              if (!mapping) return null;
              return (
                <Col span={8} key={wt}>
                  <Form.Item
                    name={mapping.amountField}
                    label={`${mapping.label} 金額`}
                  >
                    <InputNumber
                      style={{ width: '100%' }}
                      min={0}
                      precision={0}
                      formatter={(value) =>
                        `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                      }
                      parser={(value) =>
                        Number(value?.replace(/\$\s?|(,*)/g, '') || 0) as unknown as 0
                      }
                      placeholder="輸入金額"
                    />
                  </Form.Item>
                </Col>
              );
            })}
          </Row>
        ) : (
          <Alert
            title="請先選擇作業類別"
            description="選擇作業類別後，將顯示對應的金額輸入欄位"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )
      ) : (
        <Row gutter={[16, 16]}>
          {Object.entries(WORK_TYPE_AMOUNT_MAPPING).map(([, mapping]) => (
            <Col span={6} key={mapping.amountField}>
              <Form.Item name={mapping.amountField} label={mapping.label}>
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  precision={0}
                  formatter={(value) =>
                    `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                  }
                  parser={(value) =>
                    Number(value?.replace(/\$\s?|(,*)/g, '') || 0) as unknown as 0
                  }
                  placeholder="輸入金額"
                />
              </Form.Item>
            </Col>
          ))}
        </Row>
      )}
    </>
  );
};
