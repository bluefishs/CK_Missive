# -*- coding: utf-8 -*-
# Officialdocument-Gemi.py (優化後)

# ==============================================================================
# 主要功能與修正歷程 V5 (Approx. 2025-04-12) - 已重構，使用統一的 CSV 處理邏輯
# ==============================================================================
# 1.  資料來源: 從指定資料夾讀取多種格式公文清單 CSV 檔案。
#     - 自動判斷文件類型 (收/發文) 與形式 (電子/紙本)。
#     - 兼容 UTF-8 及 Big5 編碼。
# 2.  數據處理: (現在由 app.services.csv_processor 統一處理)
#     - 清理欄位值 (去除空白)。
#     - 民國日期 ('公文日期') 轉換為西元日期 ('日期')。
#     - 處理跨日期重複數據：合併所有數據後，保留每個唯一記錄的最新版本。
#     - 為最終唯一記錄集生成從 1 開始的連續 '流水號'。
# 3.  Notion 同步 (Upsert):
#     - 使用 '公文字號'+'文件類型'+'受文單位' 作為唯一鍵檢查 Notion。
#     - 創建 Notion 中不存在的新記錄。
#     - 更新 Notion 中已存在且內容有變化的記錄 (包括流水號)。
#     - 跳過數據完全相同的記錄。
# 4.  Notion 清理 (歸檔):
#     - 自動歸檔 Notion 中存在但本地最新數據中已不存在的記錄。
# 5.  健壯性與配置:
#     - 使用 .env 檔案配置 Notion Token 和 Database ID。
#     - 使用 config.json 外部檔案配置檔案路徑、欄位映射、Notion 屬性名、日誌級別等。
#     - 包含 API 調用自動重試機制 (tenacity)。
#     - 提供詳細日誌輸出到 console 及 document_processing.log 文件。
# 6.  用戶體驗:
#     - 在處理文件、同步、歸檔等步驟顯示進度條 (tqdm)。
#     - 可選功能：自動生成 Word 格式的操作說明文件 (僅在文件不存在時)。
# ==============================================================================


import pandas as pd
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
from dotenv import load_dotenv
import json
from tqdm import tqdm

# 匯入統一的 CSV 處理器
from app.services.csv_processor import DocumentCSVProcessor


try:
    # import docx # ---!!! 需要安裝: pip install python-docx !!!---
    # from docx.shared import Pt
    # from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    DOCX_AVAILABLE = False
except ImportError:
    DOCX_AVAILABLE = False


# --- Setup Section ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO, # DEBUG for detailed logs
    format='%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] %(message)s',
    handlers=[
        logging.FileHandler("document_processing.log", encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("notion_client").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("tenacity").setLevel(logging.WARNING)

# --- Load Configuration ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "folder_path": "data",
    "log_level": "INFO",
    "rate_limit_delay": 0.4,
    "expected_source_columns": ['公文日期', '類別', '字', '文號', '主旨', '發文單位', '受文單位', '狀態', '收文日期', '使用者確認', '備註', '承攬案件'],
    "field_config": {
        'sent_electronic': {'receive_date_field': '使用者確認', 'status_field': '狀態'},
        'receive_electronic': {'receive_date_field': '收文日期', 'status_field': '狀態'},
        'sent_paper': {'receive_date_field': '使用者確認', 'status_field': '狀態'},
        'receive_paper': {'receive_date_field': '收文日期', 'status_field': '狀態'},
    },
    "final_columns": ['流水號', '文件類型', '公文字號', '日期', '公文日期', '類別', '字', '文號', '主旨', '發文單位', '受文單位', '收發狀態', '收文日期', '發文形式', '備註', '承攬案件', '系統輸出日期'],
    "notion_property_names": {
        "流水號": "流水號", "文件類型": "文件類型", "公文字號": "公文字號", "日期": "日期",
        "公文日期": "公文日期", "類別": "類別", "字": "字", "文號": "文號", "主旨": "主旨",
        "發文單位": "發文單位", "受文單位": "受文單位", "收發狀態": "收發狀態", "收文日期": "收文日期",
        "發文形式": "發文形式", "備註": "備註", "承攬案件": "承攬案件", "系統輸出日期": "系統輸出日期",
        "archived": "archived"
    }
}
try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    for key, value in DEFAULT_CONFIG.items():
        config.setdefault(key, value)
    logger.info(f"成功從 {CONFIG_FILE} 載入設定。")
except FileNotFoundError:
    logger.warning(f"未找到設定檔 {CONFIG_FILE}，使用預設設定。")
    config = DEFAULT_CONFIG
except json.JSONDecodeError:
    logger.error(f"設定檔 {CONFIG_FILE} 格式錯誤。使用預設設定。")
    config = DEFAULT_CONFIG
except Exception as e:
    logger.error(f"讀取設定檔時發生錯誤: {e}，使用預設設定。")
    config = DEFAULT_CONFIG

log_level_str = config.get("log_level", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logging.getLogger().setLevel(log_level)


class DocumentImportProcessor:
    def __init__(self, config: Dict[str, Any]) -> None:
        """初始化 CSV 匯入處理器"""
        try:
            self.config = config
            self.folder_path = self.config['folder_path']
            self.rate_limit_delay = self.config.get('rate_limit_delay', 0.1) # 保留延遲以備未來使用

            if not os.path.isdir(self.folder_path):
                raise FileNotFoundError(f"指定的資料夾路徑不存在: {self.folder_path}")
            logger.info(f"設定資料夾路徑為: {self.folder_path}")
            
            # 實例化統一的 CSV 處理器
            self.csv_processor = DocumentCSVProcessor()
            self.csv_processor.expected_source_columns = self.config['expected_source_columns']
            self.csv_processor.final_columns = self.config['final_columns']

            logger.info("公文匯入處理器初始化完成")
        except Exception as e:
            logger.critical(f"初始化失敗: {e}", exc_info=True)
            raise

    def get_date_files(self) -> Dict[str, List[Dict[str, str]]]:
        """掃描資料夾"""
        date_files: Dict[str, List[Dict[str, str]]] = {}
        file_patterns = {"_receivelist.csv": "receive_electronic", "_sendlist.csv": "sent_electronic", "_preceivelist.csv": "receive_paper", "_psendlist.csv": "sent_paper"}
        if not os.path.isdir(self.folder_path):
            logger.error(f"指定的資料夾路徑不存在: {self.folder_path}")
            return {}
        try:
            all_items = os.listdir(self.folder_path)
            logger.info(f"掃描資料夾 '{self.folder_path}' 中的 {len(all_items)} 個項目...")
            for filename in tqdm(all_items, desc="掃描檔案", unit="項目", leave=False):
                fn_lower = filename.lower()
                matched_type = None
                for pattern, type_name in file_patterns.items():
                    if fn_lower.endswith(pattern):
                        matched_type = type_name
                        break
                if matched_type:
                    try:
                        date_str = filename[:10]
                        datetime.strptime(date_str, '%Y-%m-%d')
                        file_path = os.path.join(self.folder_path, filename)
                        if os.path.isfile(file_path):
                            if date_str not in date_files:
                                date_files[date_str] = []
                            date_files[date_str].append({"path": file_path, "type": matched_type})
                            logger.debug(f"找到檔案: {filename} (類型: {matched_type})")
                    except (ValueError, IndexError):
                        logger.warning(f"檔名格式錯誤: {filename}")
                    except Exception as e:
                        logger.error(f"處理檔名 '{filename}' 出錯: {e}")
        except Exception as e:
            logger.error(f"掃描 '{self.folder_path}' 出錯: {e}", exc_info=True)
            return {}
        total_file_count = sum(len(f) for f in date_files.values())
        logger.info(f"在 '{self.folder_path}' 找到 {len(date_files)} 個日期的共 {total_file_count} 個公文檔案。")
        return date_files

    def _parse_flexible_date(self, date_str: Any) -> Optional[str]:
        """解析日期為YYYY-MM-DD"""
        if pd.isna(date_str) or date_str is None:
            return None
        date_str = str(date_str).strip()
        if not date_str:
            return None
        formats_to_try = ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y-%m-%d', '%Y/%m/%d']
        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        try:  # ISO
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            logger.debug(f"無法解析日期格式: '{date_str}'")
            return None

    def process_documents(self) -> None:
        """主處理流程"""
        start_time = time.time()
        output_file = None # 初始化以避免未綁定錯誤
        try:
            logger.info("=== 開始公文匯入流程 ===")
            date_files = self.get_date_files()
            if not date_files:
                logger.info("資料夾中無公文檔案。")
                return
            all_processed_data_list = []
            logger.info("--- 階段 1: 讀取和準備本地 CSV 數據 ---")
            # total_files = sum(len(files) for files in date_files.values()) # F841: Local variable `total_files` is assigned to but never used
            processed_files = 0
            files_to_process = []
            for date_str, file_list in sorted(date_files.items()):
                for file_info in file_list:
                    files_to_process.append((date_str, file_info))
            for date_str, file_info in tqdm(files_to_process, desc="處理 CSV 檔案", unit="file", leave=False):
                processed_files += 1
                filename = os.path.basename(file_info["path"])
                doc_type_detail = file_info["type"]
                try:
                    # 使用統一的 CSV 處理器載入和準備數據
                    with open(file_info["path"], "rb") as f: # 讀取為 bytes
                        file_content = f.read()
                    df = self.csv_processor.load_csv_data(file_content, filename) # 傳入 bytes
                    if not df.empty:
                        prepared_df = self.csv_processor.prepare_data(df, doc_type_detail, date_str) # 使用統一的 prepare_data
                        if not prepared_df.empty:
                            all_processed_data_list.append(prepared_df)
                        else:
                            logger.warning(f"準備 {doc_type_detail} 數據失敗或結果為空: {filename}")
                except Exception as e:
                    logger.error(f"處理 {doc_type_detail} 檔案時發生嚴重錯誤: {filename}, 錯誤: {e}", exc_info=True)

            if not all_processed_data_list:
                logger.warning("所有檔案處理後均無有效數據。")
                return

            try:
                combined_raw_df = pd.concat(all_processed_data_list, ignore_index=True).fillna('')
                logger.info(f"數據合併完成，合併後總共 {len(combined_raw_df)} 筆記錄。")
                logger.info("開始進行跨日期重複數據處理 (保留最新記錄)...")
                original_count = len(combined_raw_df)
                
                # 使用統一的去重和流水號分配邏輯
                final_combined_df = self.csv_processor.remove_duplicates_and_assign_serial(combined_raw_df)
                
                deduplicated_count = len(final_combined_df)
                if original_count > deduplicated_count:
                    logger.info(f"跨日期去重完成，保留 {deduplicated_count} 筆最新記錄。")
                else:
                    logger.info(f"無需跨日期去重，待同步記錄數: {deduplicated_count}。")

                doc_type_col_internal = '文件類型'
                invalid_rows = final_combined_df[~final_combined_df[doc_type_col_internal].isin(['發文', '收文'])]
                if not invalid_rows.empty:
                    logger.error(f"!!! 去重後發現 '{doc_type_col_internal}' 列存在非預期值: {invalid_rows[doc_type_col_internal].unique()}，行索引: {invalid_rows.index.tolist()}")

            except Exception as final_proc_err:
                logger.critical(f"最終數據處理出錯: {final_proc_err}", exc_info=True)
                return

            logger.info("--- 階段 2: 儲存最終結果 ---")
            
            # 儲存 CSV (去重並按日期排序後的)
            try:
                output_file = os.path.join(self.folder_path, "combined_list_final.csv")
                final_columns_for_output = self.csv_processor.final_columns # 使用統一的 final_columns
                for col in final_columns_for_output:
                     if col not in final_combined_df.columns:
                         logger.warning(f"最終 DataFrame 缺少欄位 '{col}'，添加空值輸出。")
                         final_combined_df[col] = ''
                output_df_to_save = final_combined_df[final_columns_for_output].fillna('')
                output_df_to_save.to_csv(output_file, index=False, encoding='utf-8-sig')
                logger.info(f"已儲存最終整合檔案 (包含 {len(output_df_to_save)} 筆唯一最新記錄，按日期排序): {output_file}")
            except Exception as save_err:
                logger.error(f"儲存最終整合檔案 '{output_file}' 失敗: {save_err}", exc_info=True)

            end_time = time.time()
            logger.info(f"=== 公文匯入流程結束 (耗時: {end_time - start_time:.2f} 秒) ===")
        except Exception as e:
            logger.critical(f"公文匯入主流程未預期錯誤: {e}", exc_info=True)
            raise

if __name__ == "__main__":
    logger.info("開始執行公文匯入腳本...")
    try:
        sync_processor = DocumentImportProcessor(config)
        sync_processor.process_documents()

    except ValueError as ve:
        logger.critical(f"腳本初始化失敗: {ve}")
    except FileNotFoundError as fnfe:
        logger.critical(f"腳本初始化失敗: {fnfe}")
    except Exception as main_exc:
        logger.critical(f"執行時發生嚴重錯誤: {main_exc}", exc_info=True)
    finally:
        logger.info("腳本執行完畢。")
