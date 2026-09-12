import os
import sys
import time
from datetime import datetime, timezone
import requests

# ==================== 🔧 核心配置区 ====================
LOGIN_URL = "https://laehfeigoiycigkfknfn.supabase.co/auth/v1/token?grant_type=password"
EMAIL = os.getenv("MY_EMAIL")
PASSWORD = os.getenv("MY_PASSWORD")
SUPABASE_ANON_KEY = os.getenv("ANON_KEY")

RENEW_ACTION_URL = "https://freemchost.com/_serverFn/798181797bd95a02dee916a26c18d3539a58152db8660e097ca48d7cdd8ee50c"
RENEW_DETAIL_URL = "https://freemchost.com/_serverFn/c3a45c08362f2f613bbb6d511a3733a9e85e561709d48bec9280e82a4aa4f47d"

SERVER_ID = "0ac36ad6-6dbe-4766-a92e-498d68866539"
SCKEY = os.getenv("SCKEY")

# 允许续期的阈值天数（低于或等于此天数时触发续期动作）
RENEW_THRESHOLD_DAYS = 2.0

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

def parse_action_response(res_json):
    action_info = {"expires_at": None, "status_code": "成功"}
    try:
        if isinstance(res_json, dict):
            outer_p = res_json.get("p", {})
            keys = outer_p.get("k", [])
            values = outer_p.get("v", [])

            if "result" in keys:
                idx = keys.index("result")
                if idx < len(values):
                    result_node_p = values[idx].get("p", {})
                    sub_keys = result_node_p.get("k", [])
                    sub_values = result_node_p.get("v", [])

                    if "expires_at" in sub_keys:
                        sub_idx = sub_keys.index("expires_at")
                        if sub_idx < len(sub_values):
                            action_info["expires_at"] = sub_values[sub_idx].get("s")
            
            if "error" in keys:
                err_idx = keys.index("error")
                if err_idx < len(values):
                    err_val = values[err_idx]
                    if isinstance(err_val, dict):
                        msg_obj = err_val.get("message", {})
                        if isinstance(msg_obj, dict):
                            action_info["status_code"] = msg_obj.get("s", str(msg_obj))
                        else:
                            action_info["status_code"] = str(msg_obj)
                    else:
                        action_info["status_code"] = str(err_val)
    except Exception as e:
        log(f"解析续期动作响应异常: {e}")
    return action_info

def parse_detail_response(res_json):
    info = {"name": "未知", "status": "未知", "expires_at": None}
    try:
        if not isinstance(res_json, dict):
            return info

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

def fetch_server_details(session_headers, payload):
    try:
        res = requests.post(RENEW_DETAIL_URL, headers=session_headers, json=payload, timeout=15)
        if res.status_code == 200:
            return parse_detail_response(res.json())
    except Exception as e:
        log(f"⚠️ 拉取服务器详情异常: {e}")
    return {"name": "未知", "status": "未知", "expires_at": None}

def run_auto_renew():
    log("▶️ 开始全自动登录 + 智能链式续期检查流程...")

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

    # 1. 接口 B (详情查询) 专用 Payload（参数名为 serverId）
    detail_payload = {
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

    # 2. 接口 A (触发动作) 专用 Payload（参数名为 id）
    action_payload = {
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
                            "k": ["id"],
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
    # 步骤 1: 请求 [接口 B] 初始化上下文并预查服务器状态
    # ----------------------------------------------------
    log("🔍 步骤 1: 请求 [接口 B] 加载页面上下文并校验服务器到期时间...")
    before_info = fetch_server_details(base_headers, detail_payload)
    
    server_name = before_info["name"]
    server_status = before_info["status"]
    expires_at_str = before_info["expires_at"]

    log(f"📌 [当前信息] 服务器名称: {server_name} | 状态: {server_status} | 到期时间: {expires_at_str}")

    expire_dt = parse_iso_datetime(expires_at_str)
    now_utc = datetime.now(timezone.utc)

    if expire_dt:
        time_left = expire_dt - now_utc
        days_left = time_left.total_seconds() / 86400.0
        
        if days_left > RENEW_THRESHOLD_DAYS:
            log("--------------------------------------------------")
            log(f"💡 评估结果: 暂无需续期 (距到期仍有 {days_left:.1f} 天，未进入 <={RENEW_THRESHOLD_DAYS} 天续期窗口)")
            log(f"📌 当前到期时间: {expires_at_str}")
            log("--------------------------------------------------")
            sys.exit(0)
        else:
            log(f"⚠️ 评估结果: 已进入续期窗口 (剩余 {days_left:.1f} 天 <= {RENEW_THRESHOLD_DAYS} 天)，准备发送续期指令...")
    else:
        log("⚠️ 无法精确计算剩余天数，默认触发续期指令...")

    # ⏳ 页面防抖等待
    log("⏳ 正在模拟人类浏览页面，等待 3 秒后点击续期按钮...")
    time.sleep(3)

    # ----------------------------------------------------
    # 步骤 2: 发送 [接口 A] 触发续期动作
    # ----------------------------------------------------
    log("⚡ 步骤 2: 发送 [接口 A] 触发续期动作...")
    action_info = {"status_code": "成功", "expires_at": None}
    
    try:
        action_res = requests.post(RENEW_ACTION_URL, headers=base_headers, json=action_payload, timeout=15)
        if action_res.status_code == 200:
            res_json = action_res.json()
            action_info = parse_action_response(res_json)
            
            log("    📥 [接口 A 返回快照] ----------------------------")
            log(f"    动作响应状态 : {action_info['status_code']}")
            if action_info['expires_at']:
                log(f"    捕获动作到期时间: {action_info['expires_at']}")
            log("    ------------------------------------------------")
        else:
            log(f"❌ 续期动作请求失败，HTTP 状态码: {action_res.status_code}")
            notify("服务器自动续期失败", f"续期 Action 接口返回状态码: {action_res.status_code}")
            sys.exit(1)
    except Exception as e:
        log(f"💥 续期动作接口异常: {e}")
        notify("服务器自动续期异常", f"Action 阶段异常: {e}")
        sys.exit(1)

    # ----------------------------------------------------
    # 步骤 3: 再次请求 [接口 B] 确认续期后的最新数据 (等待 2 秒以确保 DB 写入完成)
    # ----------------------------------------------------
    time.sleep(2)
    log("🔍 步骤 3: 再次请求 [接口 B] 二次确认续期后的最新数据...")
    after_info = fetch_server_details(base_headers, detail_payload)

    final_name = after_info["name"] if after_info["name"] != "未知" else server_name
    final_status = after_info["status"] if after_info["status"] != "未知" else server_status
    final_expires_at = action_info["expires_at"] or after_info["expires_at"] or expires_at_str

    log("🎉【全链路自动续期/确认完成】-----------------------")
    log(f" 服务器名称: {final_name}")
    log(f" 当前运行状态: {final_status}")
    log(f" 续期前到期时间: {expires_at_str}")
    log(f" 续期后到期时间: {final_expires_at}")
    
    if final_expires_at != expires_at_str:
        log(" ✅ 状态判定: 成功延长续期！")
        notify(
            "服务器自动续期成功", 
            f"服务器 [{final_name}] 已成功续期！\n"
            f"当前状态：{final_status}\n"
            f"最新到期时间：{final_expires_at}"
        )
    else:
        err_msg = action_info.get("status_code", "时间未刷新")
        log(f" ⚠️ 状态判定: 到期时间未发生变动 (服务端响应: {err_msg})")
        notify(
            "服务器续期状态通知", 
            f"服务器 [{final_name}]\n"
            f"提示: 到期时间未发生变化 ({err_msg})\n"
            f"当前到期时间：{final_expires_at}"
        )
    log("--------------------------------------------------")

if __name__ == "__main__":
    run_auto_renew()
