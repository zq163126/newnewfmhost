import os
import sys
import time
from datetime import datetime
import requests

# ==================== 🔧 核心配置区 ====================
LOGIN_URL = "https://laehfeigoiycigkfknfn.supabase.co/auth/v1/token?grant_type=password"
EMAIL = os.getenv("MY_EMAIL")
PASSWORD = os.getenv("MY_PASSWORD")
SUPABASE_ANON_KEY = os.getenv("ANON_KEY")

# 接口 A：触发续期动作的接口
RENEW_ACTION_URL = "https://freemchost.com/_serverFn/798181797bd95a02dee916a26c18d3539a58152db8660e097ca48d7cdd8ee50c"

SERVER_ID = "0ac36ad6-6dbe-4766-a92e-498d68866539"
SCKEY = os.getenv("SCKEY")

if not all([EMAIL, PASSWORD, SUPABASE_ANON_KEY]):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 🛑 错误: 未能在环境中检测到必要的凭证 (MY_EMAIL, MY_PASSWORD 或 ANON_KEY)。", flush=True)
    sys.exit(1)
# =====================================================

def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)
    sys.stdout.flush()

def notify(title, content):
    if SCKEY:
        try:
            requests.post(f"https://sctapi.ftqq.com/{SCKEY}.send", data={"title": title, "desp": content}, timeout=5)
        except Exception as e:
            log(f"🔔 推送通知失败: {e}")

def get_new_token():
    log("🔑 正在尝试模拟登录以获取个人 Token...")

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "origin": "https://freemchost.com",
        "referer": "https://freemchost.com/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    }

    payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "gotrue_meta_security": {}
    }

    try:
        response = requests.post(LOGIN_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                log("✅ 成功模拟登录，已捕获最新专属 Token！")
                return token
        log(f"❌ 登录失败，状态码: {response.status_code}")
    except Exception as e:
        log(f"💥 登录请求引发异常: {e}")
    return None

def run_direct_renew():
    log("▶️ 开始运行：登录后直接执行续期动作（步骤 1）...")

    token = get_new_token()
    if not token:
        log("🛑 未能取得有效 Token，流程被迫中断。")
        notify("服务器自动续期失败", "模拟登录未成功获取 Token，请查看本地日志。")
        sys.exit(1)

    base_headers = {
        "accept": "application/x-tss-framed, application/x-ndjson, application/json",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "origin": "https://freemchost.com",
        "referer": f"https://freemchost.com/app/servers/{SERVER_ID}",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "x-tsr-serverfn": "true"
    }

    # 接口 A 的续期 Payload
    renew_payload = {
        "t": {
            "t": 10,
            "i": 0,
            "p": {
                "k": ["data"],
                "v": [
                    {
                        "t": 10,
                        "i": 1,
                        "p": {
                            "k": ["serverId"],
                            "v": [{"t": 1, "s": SERVER_ID}]
                        },
                        "o": 0
                    }
                ]
            }
        },
        "f": 63,
        "m": []
    }

    # ----------------------------------------------------
    # 直接执行【步骤 1】：发送 [接口 A] 触发续期动作
    # ----------------------------------------------------
    log("⚡ 步骤 1: 登录完成，直接发送 [接口 A] 触发续期动作...")
    
    try:
        action_res = requests.post(RENEW_ACTION_URL, headers=base_headers, json=renew_payload, timeout=15)
        log(f"📥 [接口 A] HTTP 响应状态码: {action_res.status_code}")
        log(f"📄 [接口 A] 原始返回内容:\n{action_res.text}")

        if action_res.status_code == 200:
            log("✅ [接口 A] 请求已发送完毕！请查看上方原始返回内容。")
        else:
            log(f"❌ 续期动作请求失败，HTTP 状态码: {action_res.status_code}")
            notify("服务器自动续期失败", f"续期 Action 接口返回状态码: {action_res.status_code}")
            sys.exit(1)
            
    except Exception as e:
        log(f"💥 续期动作接口引发异常: {e}")
        notify("服务器自动续期异常", f"Action 阶段异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_direct_renew()
