#!/usr/bin/env python3
"""
Quick System Health Check
"""

import requests
import subprocess
import json

def check_services():
    print("=== System Health Check ===")

    # Check Docker containers
    print("\n1. Docker Services:")
    try:
        result = subprocess.run(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("Docker check failed")
    except Exception as e:
        print(f"Docker error: {e}")

    # Check API endpoints
    print("\n2. API Endpoints:")
    endpoints = [
        ("Backend Health", "http://localhost:8001/health"),
        ("CSRF Token", "http://localhost:8001/api/secure-site-management/csrf-token"),
        ("Auth Me", "http://localhost:8001/api/auth/me"),
        ("Frontend", "http://localhost:3000")
    ]

    for name, url in endpoints:
        try:
            if "csrf-token" in url:
                response = requests.post(url, json={}, timeout=5)
            else:
                response = requests.get(url, timeout=5)

            status = "OK" if response.status_code == 200 else f"ERROR ({response.status_code})"
            print(f"  {name}: {status}")

        except Exception as e:
            print(f"  {name}: FAILED - {str(e)[:50]}")

    print("\n3. Configuration Files:")
    import os
    configs = [".env", ".env.master", "docker-compose.unified.yml"]
    for config in configs:
        exists = "EXISTS" if os.path.exists(config) else "MISSING"
        print(f"  {config}: {exists}")

if __name__ == "__main__":
    check_services()