#!/usr/bin/env python3
"""
乾坤測繪公文管理系統 - 自動化監控腳本
"""
import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SystemMonitor:
    """系統監控類"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_base = config.get('api_base', 'http://localhost:8001')
        self.frontend_base = config.get('frontend_base', 'http://localhost:3000')
        self.check_interval = config.get('check_interval', 300)  # 5分鐘
        self.alert_thresholds = config.get('alert_thresholds', {})
        self.email_config = config.get('email', {})
        self.notification_history = []

    async def run_health_checks(self) -> Dict[str, Any]:
        """執行完整的健康檢查"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {},
            'alerts': []
        }

        # 1. API 健康檢查
        api_health = await self.check_api_health()
        results['checks']['api'] = api_health

        # 2. 前端健康檢查
        frontend_health = await self.check_frontend_health()
        results['checks']['frontend'] = frontend_health

        # 3. 資料庫效能檢查
        db_performance = await self.check_database_performance()
        results['checks']['database'] = db_performance

        # 4. 快取狀態檢查
        cache_health = await self.check_cache_health()
        results['checks']['cache'] = cache_health

        # 5. 系統資源檢查
        system_resources = await self.check_system_resources()
        results['checks']['system'] = system_resources

        # 評估整體狀態
        results['overall_status'] = self.evaluate_overall_status(results['checks'])

        # 生成警報
        results['alerts'] = self.generate_alerts(results['checks'])

        return results

    async def check_api_health(self) -> Dict[str, Any]:
        """檢查 API 健康狀態"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # 基本健康檢查
                start_time = time.time()
                async with session.get(f"{self.api_base}/health") as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status == 200:
                        data = await response.json() if response.content_type == 'application/json' else {}

                        return {
                            'status': 'healthy',
                            'response_time_ms': round(response_time, 2),
                            'http_status': response.status,
                            'database_status': data.get('database', 'unknown')
                        }
                    else:
                        return {
                            'status': 'unhealthy',
                            'response_time_ms': round(response_time, 2),
                            'http_status': response.status,
                            'error': f'HTTP {response.status}'
                        }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': 'API無法連接'
            }

    async def check_frontend_health(self) -> Dict[str, Any]:
        """檢查前端健康狀態"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                start_time = time.time()
                async with session.get(self.frontend_base) as response:
                    response_time = (time.time() - start_time) * 1000

                    if response.status == 200:
                        return {
                            'status': 'healthy',
                            'response_time_ms': round(response_time, 2),
                            'http_status': response.status
                        }
                    else:
                        return {
                            'status': 'unhealthy',
                            'response_time_ms': round(response_time, 2),
                            'http_status': response.status
                        }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': '前端無法連接'
            }

    async def check_database_performance(self) -> Dict[str, Any]:
        """檢查資料庫效能"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(f"{self.api_base}/api/health/health/detailed") as response:
                    if response.status == 200:
                        data = await response.json()
                        db_check = data.get('checks', {}).get('database', {})
                        tables_check = data.get('checks', {}).get('tables', {})

                        # 計算平均回應時間
                        response_times = []
                        if 'response_time_ms' in db_check:
                            response_times.append(db_check['response_time_ms'])

                        for table_info in tables_check.values():
                            if isinstance(table_info, dict) and 'response_time_ms' in table_info:
                                response_times.append(table_info['response_time_ms'])

                        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

                        return {
                            'status': db_check.get('status', 'unknown'),
                            'average_response_time_ms': round(avg_response_time, 2),
                            'tables_healthy': sum(1 for t in tables_check.values()
                                                if isinstance(t, dict) and t.get('status') == 'healthy'),
                            'total_tables': len(tables_check)
                        }
                    else:
                        return {
                            'status': 'error',
                            'message': f'無法獲取詳細健康檢查 (HTTP {response.status})'
                        }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': '無法檢查資料庫效能'
            }

    async def check_cache_health(self) -> Dict[str, Any]:
        """檢查快取健康狀態"""
        # 這裡可以添加快取健康檢查邏輯
        # 由於我們使用記憶體快取，可以通過 API 端點檢查
        return {
            'status': 'healthy',
            'type': 'memory_cache',
            'message': '記憶體快取運行正常'
        }

    async def check_system_resources(self) -> Dict[str, Any]:
        """檢查系統資源"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{self.api_base}/api/health/health/detailed") as response:
                    if response.status == 200:
                        data = await response.json()
                        system_check = data.get('checks', {}).get('system', {})

                        return {
                            'status': system_check.get('status', 'unknown'),
                            'memory_usage_percent': system_check.get('memory_usage_percent', 0),
                            'available_memory_gb': system_check.get('available_memory_gb', 0)
                        }
                    else:
                        return {
                            'status': 'error',
                            'message': '無法獲取系統資源信息'
                        }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def evaluate_overall_status(self, checks: Dict[str, Any]) -> str:
        """評估整體系統狀態"""
        critical_services = ['api', 'database']

        # 檢查關鍵服務
        for service in critical_services:
            if service in checks:
                status = checks[service].get('status')
                if status in ['error', 'unhealthy']:
                    return 'critical'

        # 檢查所有服務
        all_statuses = [check.get('status') for check in checks.values()]

        if 'error' in all_statuses:
            return 'degraded'
        elif 'warning' in all_statuses:
            return 'warning'
        else:
            return 'healthy'

    def generate_alerts(self, checks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成警報"""
        alerts = []
        thresholds = self.alert_thresholds

        # API 回應時間警報
        api_check = checks.get('api', {})
        api_response_time = api_check.get('response_time_ms', 0)
        if api_response_time > thresholds.get('api_response_time_ms', 5000):
            alerts.append({
                'type': 'performance',
                'severity': 'warning',
                'service': 'api',
                'message': f'API 回應時間過長: {api_response_time:.2f}ms',
                'threshold': thresholds.get('api_response_time_ms', 5000)
            })

        # 資料庫效能警報
        db_check = checks.get('database', {})
        db_response_time = db_check.get('average_response_time_ms', 0)
        if db_response_time > thresholds.get('db_response_time_ms', 1000):
            alerts.append({
                'type': 'performance',
                'severity': 'warning',
                'service': 'database',
                'message': f'資料庫回應時間過長: {db_response_time:.2f}ms',
                'threshold': thresholds.get('db_response_time_ms', 1000)
            })

        # 記憶體使用警報
        system_check = checks.get('system', {})
        memory_usage = system_check.get('memory_usage_percent', 0)
        if memory_usage > thresholds.get('memory_usage_percent', 90):
            alerts.append({
                'type': 'resource',
                'severity': 'critical',
                'service': 'system',
                'message': f'記憶體使用率過高: {memory_usage:.1f}%',
                'threshold': thresholds.get('memory_usage_percent', 90)
            })

        # 服務不可用警報
        for service_name, service_check in checks.items():
            if service_check.get('status') in ['error', 'unhealthy']:
                alerts.append({
                    'type': 'availability',
                    'severity': 'critical',
                    'service': service_name,
                    'message': f'{service_name} 服務不可用',
                    'details': service_check.get('error', service_check.get('message', ''))
                })

        return alerts

    async def send_alert_notification(self, alerts: List[Dict[str, Any]]):
        """發送警報通知"""
        if not alerts or not self.email_config.get('enabled', False):
            return

        # 避免重複通知 (簡單去重)
        new_alerts = []
        for alert in alerts:
            alert_key = f"{alert['service']}_{alert['type']}_{alert['severity']}"
            if alert_key not in [h.get('key') for h in self.notification_history[-10:]]:
                new_alerts.append(alert)
                self.notification_history.append({
                    'key': alert_key,
                    'timestamp': datetime.now(),
                    'alert': alert
                })

        if not new_alerts:
            return

        try:
            subject = f"【乾坤測繪公文系統】系統警報 - {len(new_alerts)} 個問題"

            body = "系統監控發現以下問題：\n\n"
            for i, alert in enumerate(new_alerts, 1):
                body += f"{i}. [{alert['severity'].upper()}] {alert['service']}: {alert['message']}\n"

            body += f"\n檢查時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            body += f"系統地址: {self.api_base}\n"

            await self.send_email(subject, body)

        except Exception as e:
            logger.error(f"發送警報通知失敗: {e}")

    async def send_email(self, subject: str, body: str):
        """發送電子郵件通知"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from']
            msg['To'] = ', '.join(self.email_config['to'])
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            if self.email_config.get('use_tls', True):
                server.starttls()

            if self.email_config.get('username') and self.email_config.get('password'):
                server.login(self.email_config['username'], self.email_config['password'])

            server.send_message(msg)
            server.quit()

            logger.info(f"警報通知已發送: {subject}")

        except Exception as e:
            logger.error(f"發送郵件失敗: {e}")

    async def save_monitoring_data(self, data: Dict[str, Any]):
        """保存監控數據"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"monitoring_data_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"監控數據已保存: {filename}")

        except Exception as e:
            logger.error(f"保存監控數據失敗: {e}")

    async def run_continuous_monitoring(self):
        """運行持續監控"""
        logger.info("開始持續監控...")

        while True:
            try:
                # 執行健康檢查
                results = await self.run_health_checks()

                # 記錄結果
                logger.info(f"監控結果 - 整體狀態: {results['overall_status']}, "
                          f"警報數量: {len(results['alerts'])}")

                # 發送警報
                if results['alerts']:
                    await self.send_alert_notification(results['alerts'])

                # 保存監控數據 (可選)
                if self.config.get('save_monitoring_data', False):
                    await self.save_monitoring_data(results)

                # 等待下次檢查
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                await asyncio.sleep(60)  # 錯誤時等待1分鐘

def load_config(config_file: str = 'monitoring_config.json') -> Dict[str, Any]:
    """載入監控配置"""
    default_config = {
        'api_base': 'http://localhost:8001',
        'frontend_base': 'http://localhost:3000',
        'check_interval': 300,
        'alert_thresholds': {
            'api_response_time_ms': 5000,
            'db_response_time_ms': 1000,
            'memory_usage_percent': 90
        },
        'email': {
            'enabled': False,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'use_tls': True,
            'from': 'system@example.com',
            'to': ['admin@example.com'],
            'username': '',
            'password': ''
        },
        'save_monitoring_data': False
    }

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 合併默認配置
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
    except FileNotFoundError:
        logger.warning(f"配置文件 {config_file} 不存在，使用默認配置")
        # 創建默認配置文件
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return default_config

async def main():
    """主函數"""
    # 載入配置
    config = load_config()

    # 創建監控器
    monitor = SystemMonitor(config)

    # 運行單次檢查或持續監控
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # 單次檢查
        results = await monitor.run_health_checks()
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        # 持續監控
        await monitor.run_continuous_monitoring()

if __name__ == '__main__':
    asyncio.run(main())