# 🚀 Freemchost 服务器全自动续期助手 (使用gemini生成)

源代码作者：https://github.com/zhisibi/renew-freemchost

[注册地址](https://freemchost.com)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-GitHub%20Actions-orange)

本脚本用于全自动管理 **Freemchost** 游戏/应用服务器（基于 Pterodactyl 翼龙面板）的续期流程。针对免费微型套餐（Free mini）**每 48 小时需手动续期一次**的严格限制，本系统采用全新的**“链式双接口”机制**，配合 GitHub Actions 实现每日全自动安全续期、多维度状态校验以及消息推送。

---

## ✨ 核心特性

* **全自动链式运行**：自动模拟登录获取个人专属 Access Token，并动态注入后续所有内部函数路由。
* **双接口闭环验证**：
  * **接口 A (Action 路由)**：下发核心续期指令，并深度解析轻量级压缩包，精准捕获 `expires_at` 到期时间。
  * **接口 B (Detail 路由)**：续期动作生效后，紧接着拉取最终服务器完整状态（服务器名称、在线状态等），确保续期结果 100% 真实有效。
* **透明化步骤监控**：完美输出步骤 1/2（续期动作）的返回快照与执行状态码（Error Code），让每一笔自动化续期都有据可查。
* **零依赖云端托管**：完全基于 GitHub Actions 虚拟环境运行，无需本地服务器或常驻后台，完全免费。
* **安全凭证防护**：账户、密码、密钥全线接入 GitHub Secrets 加密存储，拒绝源码泄露风险，安全防封。

---

## 🔍 核心参数获取指引（最新抓包教程）

当网站后端升级或你更换了新的服务器时，脚本中的路由参数需要同步更新。请按照以下步骤获取最新值：

### 1. 抓取双接口路由 (`RENEW_ACTION_URL` 与 `RENEW_DETAIL_URL`)
1. 使用电脑浏览器登录 [Freemchost 官网](https://new.freemchost.com)。
2. 进入你的服务器控制台管理页面（此时地址栏通常显示为 `https://new.freemchost.com/app/servers/xxxxx`）。
3. 按下键盘上的 **F12** 键（或右键点击页面选择“检查”），切换到 **Network（网络）** 标签页。
4. 在过滤框中输入 `_serverFn` 锁定目标请求，并清空旧的抓包记录。
5. **获取【接口 A：Action 路由】**：在网页上点击 **"Renew"（续期）** 按钮。此时网络面板会立刻弹出一个全新的 `POST` 请求（URL 后面带有一长串哈希特征码）。点击该请求，在右侧的 **Headers（标头）** 中找到 **Request URL** 完整复制出来，它就是最新的 `RENEW_ACTION_URL`。
6. **获取【接口 B：Detail 路由】**：续期完成后，点击网页上的刷新按钮或者切换一下菜单让页面刷新。此时网络面板会弹出另一个 `_serverFn` 请求，里面返回了包含服务器名称、面板地址在内的完整大 JSON。复制该请求的 **Request URL**，它就是最新的 `RENEW_DETAIL_URL`。

### 2. 获取 `SERVER_ID`
* 最简单的方法：直接在**浏览器地址栏**的 URL 尾部（`/app/servers/` 后面那一串 36 位长、带连字符的 UUID）复制即可。

### 3. 抓取 `ANON_KEY` (Supabase 公钥)
1. 退出当前的登录状态，回到 Freemchost 登录页面。打开 F12 开发者工具，切换到 **Network（网络）** 标签。
2. 在过滤框中输入 `token?grant_type=password`。
3. 输入邮箱和密码点击登录，点击下方的抓包请求。
4. 在右侧 **Headers（标头）** -> **Request Headers（请求标头）** 区域中找到 `apikey` 或 `authorization` 字段。后面那串以 `eyJhbGci...` 开头的几百位超长字符串就是 `ANON_KEY`（复制 `authorization` 时注意去掉前面的 `Bearer ` 关键字）。

---

## 🛠️ 快速部署指南

### 1. 配置 GitHub Secrets
将本仓库 Fork 或推送到你的私有/公开 GitHub 仓库后，点击仓库顶部的 **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**，依次添加以下加密变量：

| Secret 名称 | 填入的值 / 示例 | 说明 |
| :--- | :--- | :--- |
| `MY_EMAIL` | `your_email@gmail.com` | 你的 Freemchost 登录邮箱 (必填) |
| `MY_PASSWORD` | `your_password` | 你的 Freemchost 登录密码 (必填) |
| `ANON_KEY` | `eyJhbGciOiJIUzI1NiIs...` | 前端抓取到的 Supabase 专属公钥 (必填) |
| `SCKEY` | `SCT123456T...` | （可选）Server酱微信推送公钥 |

### 2. 配置文件结构
请确保你的 GitHub 仓库中包含以下核心文件且路径严格一致：
```text
├── .github/
│   └── workflows/
│       └── auto_renew.yml      # GitHub Actions 工作流配置文件
├── renew.py                    # 完美改造后的链式核心 Python 续期脚本
└── README.md                   # 本说明文件
