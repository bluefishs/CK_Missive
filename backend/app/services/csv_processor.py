# -*- coding: utf-8 -*-
"""
公文CSV處理器 - 完整17欄位對應版本
確保與資料庫模型完全對應的CSV匯入處理器
"""
import logging
import pandas as pd
import io
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DocumentCSVProcessor:
    """文件 CSV 處理器 - 完整17欄位版本"""
    
    def __init__(self):
        # 根據資料庫模型的17個必要欄位設計對應
        self.field_mappings = {
            # 17個核心欄位對應
            '流水號': 'auto_serial',
            '文件類型': 'doc_type', 
            '公文字號': 'doc_number',  # 最終組合後的完整公文字號
            '日期': 'doc_date',       # 西元日期
            '公文日期': 'roc_date',   # 民國日期（原始）
            '類別': 'doc_class',
            '字': 'doc_word',         # 來自 CSV
            '文號': 'legacy_doc_number', # 來自 CSV，用於組合公文字號
            '主旨': 'subject',
            '發文單位': 'sender',
            '受文單位': 'receiver',
            '收發狀態': 'status',
            '收文日期': 'receive_date',
            '發文形式': 'dispatch_type',
            '備註': 'notes',
            '承攬案件': 'contract_case',
            '系統輸出日期': 'system_output_date',
            
            # 相容性欄位對應（不同CSV檔案可能使用的欄位名）
            '序號': 'auto_serial',
            '編號': 'auto_serial',
            '狀態': 'status',
            '辦理情形': 'status',
            '發文日期': 'doc_date',
            '使用者確認': 'system_output_date',
            '類型': 'doc_type',
            '收發類型': 'doc_type'
        }
        
        # 標準17欄位輸出順序
        self.final_columns = [
            'auto_serial',         # 1. 流水號
            'doc_type',           # 2. 文件類型  
            'doc_number',         # 3. 公文字號
            'doc_date',           # 4. 日期
            'roc_date',           # 5. 公文日期
            'doc_class',          # 6. 類別
            'doc_word',           # 7. 字
            'legacy_doc_number',  # 8. 文號
            'subject',            # 9. 主旨
            'sender',             # 10. 發文單位
            'receiver',           # 11. 受文單位
            'status',             # 12. 收發狀態
            'receive_date',       # 13. 收文日期
            'dispatch_type',      # 14. 發文形式
            'notes',              # 15. 備註
            'contract_case',      # 16. 承攬案件
            'system_output_date'  # 17. 系統輸出日期
        ]
        
        self.supported_encodings = ['utf-8', 'utf-8-sig', 'big5', 'cp950']

    def _detect_encoding(self, content: bytes) -> str:
        for encoding in self.supported_encodings:
            try:
                content.decode(encoding)
                logger.debug(f"成功檢測到編碼: {encoding}")
                return encoding
            except UnicodeDecodeError:
                continue
        logger.warning("無法檢測到特定編碼，將使用 utf-8 作為預設。")
        return 'utf-8'

    def _clean_text(self, text: Any) -> str:
        """基本的文字清理，只做最小必要的處理"""
        if pd.isna(text) or text is None:
            return ""
        return str(text).strip()

    def _parse_date(self, date_str: Any) -> Optional[str]:
        """解析民國日期並轉換為西元日期"""
        if pd.isna(date_str) or date_str is None:
            return None
        
        date_str = str(date_str).strip()
        if not date_str:
            return None
        
        # 匹配民國年格式: 中華民國114年9月2日
        match_roc = re.search(r'中華民國(\d{2,3})年(\d{1,2})月(\d{1,2})日', date_str)
        if match_roc:
            roc_year, month, day = map(int, match_roc.groups())
            ad_year = roc_year + 1911
            try:
                return datetime(ad_year, month, day).strftime('%Y-%m-%d')
            except ValueError:
                logger.warning(f"無效的民國日期: {date_str}")
                return None
        
        # 如果無法解析民國年，嘗試直接解析
        try:
            return pd.to_datetime(date_str).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            logger.warning(f"無法解析日期: {date_str}")
            return None

    def _determine_doc_type(self, filename: str, sender: str) -> str:
        """根據檔名和發文單位判斷文件類型"""
        filename_lower = filename.lower()
        if 'send' in filename_lower or '發文' in filename_lower:
            return '發文'
        if 'receive' in filename_lower or '收文' in filename_lower:
            return '收文'
        
        # 根據發文單位判斷
        sender_clean = str(sender).strip()
        if '乾坤' in sender_clean or '本公司' in sender_clean:
            return '發文'
        return '收文'

    def load_csv_data(self, content: bytes, filename: str) -> pd.DataFrame:
        """載入 CSV 檔案並找到標頭行"""
        encoding = self._detect_encoding(content)
        try:
            decoded_content = content.decode(encoding)
        except UnicodeDecodeError:
            logger.error(f"使用檢測到的編碼 '{encoding}' 解碼檔案 '{filename}' 失敗。")
            return pd.DataFrame()

        lines = decoded_content.splitlines()
        header_row_index = -1
        
        # 尋找包含 '序號' 和 ('主旨' 或 '文號') 的標頭行
        for i, line in enumerate(lines[:10]):
            if '序號' in line and ('主旨' in line or '文號' in line):
                header_row_index = i
                logger.info(f"在檔案 '{filename}' 的第 {i+1} 行找到標頭。")
                break
        
        if header_row_index == -1:
            logger.error(f"在檔案 '{filename}' 中找不到有效的標頭行。")
            return pd.DataFrame()

        try:
            # 從標頭行開始讀取
            csv_for_pandas = io.StringIO('\n'.join(lines[header_row_index:]))
            df = pd.read_csv(csv_for_pandas, dtype=str, skipinitialspace=True)
            
            # 清理欄位名稱
            df.columns = [col.strip() for col in df.columns]
            
            # 移除完全空白的行
            df.dropna(how='all', inplace=True)
            
            # 篩選有效資料行（至少主旨或文號有內容）
            if '主旨' in df.columns:
                condition = df['主旨'].astype(str).str.strip().ne('')
                df = df[condition].copy()
            elif '文號' in df.columns:
                condition = df['文號'].astype(str).str.strip().ne('')
                df = df[condition].copy()
            
            logger.info(f"成功從 '{filename}' 載入 {len(df)} 筆有效記錄。")
            return df
            
        except Exception as e:
            logger.error(f"讀取 CSV '{filename}' 時發生錯誤: {e}", exc_info=True)
            return pd.DataFrame()

    def prepare_data(self, df: pd.DataFrame, filename: str) -> pd.DataFrame:
        """準備和標準化資料"""
        if df.empty:
            return pd.DataFrame()

        # 1. 欄位重新命名
        df_renamed = df.copy()
        
        # 直接重新命名欄位
        rename_map = {}
        for csv_col in df.columns:
            if csv_col in self.field_mappings:
                rename_map[csv_col] = self.field_mappings[csv_col]
        
        df_renamed = df_renamed.rename(columns=rename_map)
        
        logger.debug(f"重新命名後的欄位: {df_renamed.columns.tolist()}")
        
        # 2. 組合公文字號（關鍵步驟）- 格式：{字}字第{文號}號
        if 'doc_word' in df_renamed.columns and 'legacy_doc_number' in df_renamed.columns:
            df_renamed['doc_number'] = df_renamed.apply(
                lambda row: f"{self._clean_text(row.get('doc_word', ''))}字第{self._clean_text(row.get('legacy_doc_number', ''))}號"
                if self._clean_text(row.get('doc_word', '')) and self._clean_text(row.get('legacy_doc_number', ''))
                else '',
                axis=1
            )
            logger.debug("已組合公文字號（格式：字第...號）")
        else:
            df_renamed['doc_number'] = ''
            logger.warning("無法組合公文字號：缺少 '字' 或 '文號' 欄位")
        
        # 3. 處理日期
        if 'roc_date' in df_renamed.columns:
            # 轉換民國日期為西元日期
            df_renamed['doc_date'] = df_renamed['roc_date'].apply(self._parse_date)
            # 保留原始民國日期
            df_renamed['roc_date'] = df_renamed['roc_date'].apply(self._clean_text)
        else:
            df_renamed['doc_date'] = ''
            df_renamed['roc_date'] = ''
        
        # 4. 清理其他欄位
        for col in df_renamed.columns:
            if col not in ['doc_date', 'doc_number']:  # 跳過已處理的欄位
                df_renamed[col] = df_renamed[col].apply(self._clean_text)
        
        # 5. 決定文件類型
        if 'sender' in df_renamed.columns:
            df_renamed['doc_type'] = df_renamed['sender'].apply(
                lambda sender: self._determine_doc_type(filename, sender)
            )
        else:
            df_renamed['doc_type'] = self._determine_doc_type(filename, '')
        
        # 6. 確保所有必要欄位存在
        for col in self.final_columns:
            if col not in df_renamed.columns:
                df_renamed[col] = ''
        
        # 7. 按指定順序選擇最終欄位
        final_df = df_renamed[self.final_columns].copy()
        
        logger.info(f"資料準備完成，最終欄位: {final_df.columns.tolist()}")
        logger.info(f"最終資料筆數: {len(final_df)}")
        
        return final_df

    def process_csv_content(self, file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """主要的CSV處理流程"""
        logger.info(f"開始處理 CSV 檔案: {filename}")
        
        # 1. 載入CSV資料
        df = self.load_csv_data(file_content, filename)
        if df.empty:
            logger.warning(f"檔案 '{filename}' 載入後為空，處理中止。")
            return []
        
        logger.info(f"檔案 '{filename}' 成功載入 {len(df)} 筆記錄")
        
        # 2. 準備資料
        prepared_df = self.prepare_data(df, filename)
        if prepared_df.empty:
            logger.warning(f"檔案 '{filename}' 準備資料後為空，處理中止。")
            return []
        
        logger.info(f"資料準備完成，共 {len(prepared_df)} 筆記錄")
        
        # 3. 轉換為字典格式
        dict_records = prepared_df.fillna('').to_dict('records')
        
        # 4. 確保所有鍵都是字串
        final_records = [{str(k): str(v) for k, v in record.items()} for record in dict_records]
        
        logger.info(f"成功處理完畢，共回傳 {len(final_records)} 筆記錄")
        return final_records

    def read_csv_file(self, file_path: str, encoding: str = "utf-8", delimiter: str = ",") -> pd.DataFrame:
        """讀取CSV檔案"""
        try:
            # 如果沒有指定編碼，自動檢測
            if encoding == "utf-8" or encoding is None:
                with open(file_path, 'rb') as f:
                    sample = f.read(1024)
                detected_encoding = self._detect_encoding(sample)
                if detected_encoding:
                    encoding = detected_encoding

            # 讀取CSV檔案
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                na_values=['', 'NULL', 'null', 'None'],
                keep_default_na=False,
                dtype=str  # 將所有欄位讀取為字串，避免自動轉換問題
            )

            logger.info(f"成功讀取CSV檔案: {file_path}, 共 {len(df)} 行, {len(df.columns)} 欄")
            return df

        except UnicodeDecodeError as e:
            logger.error(f"編碼錯誤: {e}, 嘗試使用 utf-8-sig 編碼")
            try:
                df = pd.read_csv(
                    file_path,
                    encoding="utf-8-sig",  # 處理BOM
                    delimiter=delimiter,
                    na_values=['', 'NULL', 'null', 'None'],
                    keep_default_na=False,
                    dtype=str
                )
                return df
            except Exception as e2:
                logger.error(f"重試讀取失敗: {e2}")
                raise e
        except Exception as e:
            logger.error(f"讀取CSV檔案失敗: {e}")
            raise e

    def process_row(self, row_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """處理單行CSV資料，轉換為資料庫格式"""
        try:
            # 初始化結果字典
            result = {}

            # 基本資料處理
            for csv_field, db_field in self.field_mappings.items():
                if csv_field in row_data:
                    value = row_data[csv_field]

                    # 基本清理
                    if pd.isna(value) or value is None or str(value).strip() == '':
                        result[db_field] = None
                    else:
                        result[db_field] = self._clean_text(value)

            # 特殊處理
            # 1. 流水號處理
            if 'auto_serial' in result and result['auto_serial']:
                try:
                    result['auto_serial'] = int(result['auto_serial'])
                except (ValueError, TypeError):
                    result['auto_serial'] = None

            # 2. 日期處理
            if 'doc_date' in result and result['doc_date']:
                result['doc_date'] = self._parse_date(result['doc_date'])

            if 'receive_date' in result and result['receive_date']:
                # 收文日期通常包含時間，需要特殊處理
                receive_date = result['receive_date']
                if receive_date and len(receive_date) > 10:
                    # 如果包含時間，只取日期部分
                    try:
                        parsed_date = pd.to_datetime(receive_date)
                        result['receive_date'] = parsed_date.strftime('%Y-%m-%d')
                    except:
                        result['receive_date'] = self._parse_date(receive_date)
                else:
                    result['receive_date'] = self._parse_date(receive_date)

            if 'system_output_date' in result and result['system_output_date']:
                result['system_output_date'] = self._parse_date(result['system_output_date'])

            # 3. 公文字號組合處理
            if not result.get('doc_number') and result.get('doc_word') and result.get('legacy_doc_number'):
                result['doc_number'] = f"{result['doc_word']}字第{result['legacy_doc_number']}號"

            # 4. 必要欄位檢查
            if not result.get('doc_number'):
                logger.warning(f"缺少公文字號: {row_data}")
                return None

            if not result.get('subject'):
                logger.warning(f"缺少主旨: {row_data}")
                return None

            # 5. 設定預設值
            if not result.get('doc_type'):
                result['doc_type'] = '收文'  # 預設為收文

            if not result.get('status'):
                result['status'] = '待處理'  # 預設狀態

            # 添加建立時間
            result['created_at'] = datetime.now().isoformat()

            return result

        except Exception as e:
            logger.error(f"處理行資料時發生錯誤: {e}, 資料: {row_data}")
            return None