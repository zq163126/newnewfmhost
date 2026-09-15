import os
import sys
import time
import re
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
import requests

# ==================== 🔧 核心配置区 ====================
LOGIN_URL = "https://laehfeigoiycigkfknfn.supabase.co/auth/v1/token?grant_type=password"
EMAIL = os.getenv("MY_EMAIL")
PASSWORD = os.getenv("MY_PASSWORD")
SUPABASE_ANON_KEY = os.getenv("ANON_KEY")

SERVER_ID = "0ac36ad6-6dbe-4766-a92e-498d68866539"
TARGET_URL = f"https://freemchost.com/app/servers/{SERVER_ID}"
SCKEY = os.getenv("SCKEY")
RENEW_THRESHOLD_DAYS = 2.0

RENEW_DETAIL_URL = "https://freemchost.com/_serverFn/c3a45c08362f2f613bbb6d511a3733a9e85e561709d48bec9280e82a4aa4f47d"

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

def parse_iso_datetime(dt_str):
    if not dt_str:
        return None
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None

def parse_detail_response(res_json):
    info = {"name": "未知", "status": "未知", "expires_at": None}
    try:
        outer_v = res_json.get("p", {}).get("v", [])
        if not outer_v:
            return info
        mid_v = outer_v[0].get("p", {}).get("v", [])
        if not mid_v:
            return info
        server_node = mid_v[0]
        keys = server_node.get("p", {}).get("k", [])
        values = server_node.get("p", {}).get("v", [])
        if "name" in keys:
            info["name"] = values[keys.index("name")].get("s", "未知")
        if "status" in keys:
            info["status"] = values[keys.index("status")].get("s", "未知")
        if "expires_at" in keys:
            info["expires_at"] = values[keys.index("expires_at")].get("s")
    except Exception as e:
        log(f"解析详情响应异常: {e}")
    return info

def get_new_token():
    log("🔑 正在尝试模拟登录以获取个人 Token...")
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "origin": "https://freemchost.com",
        "referer": "https://freemchost.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    }
    payload = {"email": EMAIL, "password": PASSWORD, "gotrue_meta_security": {}}
    try:
        response = requests.post(LOGIN_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                log("✅ 成功模拟登录，已捕获最新专属 Token！")
                return token
        log(f"❌ 登录失败，状态码: {response.status_code}")
    except Exception as e:
        log(f"💥 登录请求异常: {e}")
    return None

def fetch_server_details_api(token):
    headers = {
        "accept": "application/x-tss-framed, application/x-ndjson, application/json",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "origin": "https://freemchost.com",
        "referer": TARGET_URL,
        "x-tsr-serverfn": "true"
    }
    payload = {
        "t": {"t": 10, "i": 0, "p": {"k": ["data"], "v": [{"t": 10, "i": 1, "p": {"k": ["id"], "v": [{"t": 1, "s": SERVER_ID}]}, "o": 0}]}},
        "f": 63, "m": []
    }
    try:
        res = requests.post(RENEW_DETAIL_URL, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return parse_detail_response(res.json())
    except Exception as e:
        log(f"⚠️ 拉取详情异常: {e}")
    return {"name": "未知", "status": "未知", "expires_at": None}

def run_auto_renew_browser():
    log("▶️ 开始全自动登录 + 浏览器链式续期检查流程...")

    token = get_new_token()
    if not token:
        log("🛑 未能取得有效 Token，流程中断。")
        notify("服务器自动续期失败", "模拟登录未获取 Token")
        sys.exit(1)

    log("🔍 步骤 1: 请求 [接口 B] 校验服务器状态及到期时间...")
    before_info = fetch_server_details_api(token)
    server_name = before_info["name"]
    server_status = before_info["status"]
    expires_at_str = before_info["expires_at"]

    log(f"📌 [当前信息] 服务器名称: {server_name} | 状态: {server_status} | 到期时间: {expires_at_str}")

    expire_dt = parse_iso_datetime(expires_at_str)
    now_utc = datetime.now(timezone.utc)

    if expire_dt:
        days_left = (expire_dt - now_utc).total_seconds() / 86400.0
        if days_left > RENEW_THRESHOLD_DAYS:
            log(f"💡 评估结果: 暂无需续期 (距到期仍有 {days_left:.1f} 天)")
            sys.exit(0)
        else:
            log(f"⚠️ 评估结果: 已进入续期窗口 (剩余 {days_left:.1f} 天)，启动真实浏览器执行续期...")
    else:
        log("⚠️ 无法精确计算剩余天数，执行浏览器续期保底...")

    # 步骤 2: Playwright 注入 Token 并打开网页点击续期
    log("⚡ 步骤 2: 启动浏览器执行会话和弹窗续期...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        
        # 注入 LocalStorage 保持登录态
        context.add_init_script(f"""
            window.localStorage.setItem('supabase.auth.token', JSON.stringify({{
                currentSession: {{ access_token: '{token}' }},
                expiresAt: Date.now() + 3600 * 1000
            }}));
        """)
        
        page = context.new_page()
        try:
            log("🌐 打开目标服务器控制台页面...")
            page.goto(TARGET_URL, timeout=30000, wait_until="networkidle")
            time.sleep(3)

            log("🖱️ 寻找续期触发按钮（多路策略匹配）...")
            renew_regex = re.compile(r"续期|renew|extend|延长", re.IGNORECASE)
            
            # 策略 A: 宽泛标签匹配 (button, a, [role='button'], div/span 包含文字)
            target = page.locator("button, a, [role='button']").filter(has_text=renew_regex).first
            if target.count() == 0 or not target.is_visible(timeout=3000):
                target = page.locator("text=" + "续期") if page.locator("text=续期").count() > 0 else page.get_by_text(renew_regex).first

            if target.count() > 0:
                target.first.click(timeout=5000)
                log("🖱️ 已点击续期触发器，等待确认...")
                time.sleep(2)
                
                # 寻找弹窗内的确认提交按钮
                confirm_regex = re.compile(r"确认|confirm|submit|yes|ok|确定", re.IGNORECASE)
                confirm_btn = page.locator("button, [role='button']").filter(has_text=confirm_regex).first
                if confirm_btn.count() > 0 and confirm_btn.is_visible(timeout=3000):
                    confirm_btn.click()
                    log("🖱️ 已点击确认续期提交!")
                    time.sleep(3)
                else:
                    log("⚠️ 未显式找到弹窗确认按钮，可能点击即完成。")
            else:
                body_text = page.inner_text("body")[:400].replace("\n", " | ")
                log(f"⚠️ 未能命中续期按钮。页面文本片段预览: {body_text}")
        except Exception as e:
            log(f"💥 浏览器自动化操作异常: {e}")
        finally:
            browser.close()

    # 步骤 3: 二次校验
    log("🔍 步骤 3: 再次请求 [接口 B] 二次确认续期后的最新数据...")
    time.sleep(2)
    after_info = fetch_server_details_api(token)
    final_expires_at = after_info["expires_at"] or expires_at_str
    final_status = after_info["status"] if after_info["status"] != "未知" else server_status

    log("🎉【全链路自动续期/确认完成】-----------------------")
    log(f" 服务器名称: {server_name}")
    log(f" 当前运行状态: {final_status}")
    log(f" 续期前到期时间: {expires_at_str}")
    log(f" 续期后到期时间: {final_expires_at}")
    
    if final_expires_at != expires_at_str:
        log(" ✅ 状态判定: 成功延长续期！")
        notify("服务器自动续期成功", f"服务器 [{server_name}] 已成功续期至 {final_expires_at}")
    else:
        log(" ⚠️ 状态判定: 到期时间未发生变动。")
        notify("服务器续期状态通知", f"服务器 [{server_name}] 检查完毕，当前到期时间: {final_expires_at}")
    log("--------------------------------------------------")

if __name__ == "__main__":
    run_auto_renew_browser()
