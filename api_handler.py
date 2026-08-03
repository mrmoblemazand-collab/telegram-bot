import requests
import json
from datetime import datetime, timedelta

class PanelAPI:
    """کلاس برای مدیریت API های مختلف پنل‌ها"""
    
    def __init__(self, panel_type: str, token_or_url: str):
        self.panel_type = panel_type
        self.token_or_url = token_or_url
        self.timeout = 10
    
    # ==================== Marzban ====================
    def marzban_create_user(self, username: str, data_limit_gb: int = 10, days: int = 30):
        """ایجاد اکاونت در Marzban"""
        try:
            # توکن Marzban معمولاً شامل URL و token است: http://url/token
            if "http" in self.token_or_url:
                base_url = self.token_or_url.rstrip('/')
            else:
                return {"error": "❌ فرمت توکن اشتباه است"}
            
            # تبدیل به bytes
            data_limit_bytes = data_limit_gb * 1024 * 1024 * 1024
            expire_date = (datetime.now() + timedelta(days=days)).timestamp()
            
            # درخواست API
            api_url = f"{base_url}/api/users"
            payload = {
                "username": username,
                "data_limit": data_limit_bytes,
                "expire": int(expire_date)
            }
            
            response = requests.post(
                api_url,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 201:
                return {
                    "success": True,
                    "message": f"✅ اکاونت {username} در Marzban ساخته شد",
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ خطا: {response.status_code} - {response.text}"
                }
        
        except requests.exceptions.Timeout:
            return {"error": "❌ تایم‌اوت! سرور پاسخ نداد"}
        except requests.exceptions.ConnectionError:
            return {"error": "❌ نتوانستم به سرور متصل شوم"}
        except Exception as e:
            return {"error": f"❌ خطا: {str(e)}"}
    
    # ==================== 3x-ui ====================
    def xui_create_user(self, email: str, data_limit_gb: int = 10, days: int = 30):
        """ایجاد اکاونت در 3x-ui"""
        try:
            # توکن 3x-ui: http://url:port/cookie_value
            parts = self.token_or_url.rsplit('/', 1)
            if len(parts) == 2:
                base_url = parts[0]
                cookie_value = parts[1]
            else:
                return {"error": "❌ فرمت توکن 3x-ui اشتباه"}
            
            # تبدیل به GB
            data_limit_gb_value = data_limit_gb * 1024 * 1024 * 1024
            expiry_time = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
            
            api_url = f"{base_url}/xui/api/inbounds/addClient"
            
            headers = {
                "Cookie": f"session={cookie_value}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "id": 0,
                "inboundId": 1,
                "enable": True,
                "email": email,
                "limitIp": 0,
                "totalGB": int(data_limit_gb_value),
                "expiryTime": expiry_time,
                "tgId": "",
                "subId": email,
                "reset": 0
            }
            
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"✅ اکاونت {email} در 3x-ui ساخته شد",
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ خطا: {response.status_code}"
                }
        
        except requests.exceptions.Timeout:
            return {"error": "❌ تایم‌اوت!"}
        except requests.exceptions.ConnectionError:
            return {"error": "❌ نتوانستم متصل شوم"}
        except Exception as e:
            return {"error": f"❌ خطا: {str(e)}"}
    
    # ==================== Luffy Panel ====================
    def luffy_create_user(self, username: str, data_limit_gb: int = 10, days: int = 30):
        """ایجاد اکاونت در Luffy Panel"""
        try:
            base_url = self.token_or_url.rstrip('/')
            data_limit_bytes = data_limit_gb * 1024 * 1024 * 1024
            
            api_url = f"{base_url}/api/users/add"
            payload = {
                "username": username,
                "data_limit": data_limit_bytes,
                "days": days
            }
            
            response = requests.post(api_url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"✅ اکاونت در Luffy ساخته شد",
                    "data": response.json()
                }
            else:
                return {"success": False, "error": f"❌ خطا: {response.status_code}"}
        
        except Exception as e:
            return {"error": f"❌ خطا: {str(e)}"}
    
    # ==================== PasarGuard ====================
    def pasarguard_create_user(self, username: str, data_limit_gb: int = 10):
        """ایجاد اکاونت در PasarGuard"""
        try:
            base_url = self.token_or_url.rstrip('/')
            
            api_url = f"{base_url}/api/client/add"
            payload = {
                "username": username,
                "quota": int(data_limit_gb * 1024 * 1024 * 1024)
            }
            
            response = requests.post(api_url, json=payload, timeout=self.timeout)
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "message": f"✅ اکاونت در PasarGuard ساخته شد",
                    "data": response.json()
                }
            else:
                return {"success": False, "error": f"❌ خطا: {response.status_code}"}
        
        except Exception as e:
            return {"error": f"❌ خطا: {str(e)}"}
    
    # ==================== تابع کلی برای ایجاد اکاونت ====================
    def create_account(self, username: str, data_limit_gb: int = 10, days: int = 30):
        """تابع کلی برای ایجاد اکاونت در هر پنل"""
        
        if self.panel_type == "marzban":
            return self.marzban_create_user(username, data_limit_gb, days)
        
        elif self.panel_type == "3xui":
            return self.xui_create_user(username, data_limit_gb, days)
        
        elif self.panel_type == "luffy":
            return self.luffy_create_user(username, data_limit_gb, days)
        
        elif self.panel_type == "pasarguard":
            return self.pasarguard_create_user(username, data_limit_gb)
        
        else:
            return {"error": f"❌ پنل {self.panel_type} پشتیبانی نمی‌شود"}


def test_panel_connection(panel_type: str, token: str) -> dict:
    """تست اتصال به پنل"""
    try:
        api = PanelAPI(panel_type, token)
        
        if panel_type == "marzban":
            url = token.rstrip('/')
            response = requests.get(f"{url}/api/system/status", timeout=5)
        elif panel_type == "3xui":
            url = token.rsplit('/', 1)[0]
            response = requests.get(f"{url}/xui/api/inbounds/list", timeout=5)
        else:
            url = token.rstrip('/')
            response = requests.get(f"{url}/api/status", timeout=5)
        
        if response.status_code == 200:
            return {"success": True, "message": "✅ اتصال موفق!"}
        else:
            return {"success": False, "error": f"❌ کد: {response.status_code}"}
    
    except Exception as e:
        return {"success": False, "error": f"❌ خطا: {str(e)}"}