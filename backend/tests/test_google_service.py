"""測試 Google Calendar Service 初始化"""
import os
import sys

# 確保工作目錄正確
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(f"Working directory: {os.getcwd()}")

# 載入服務
from app.services.document_calendar_service import DocumentCalendarService

# 初始化新實例
service = DocumentCalendarService()

print(f"Service Ready: {service.is_ready()}")
print(f"Calendar ID: {service.calendar_id}")
print(f"Service object: {service.service}")
print(f"Credentials: {service.credentials}")

if service.is_ready():
    print("\n✅ Google Calendar Service 初始化成功!")
else:
    print("\n❌ Google Calendar Service 初始化失敗")
