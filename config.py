# config.py

# ==================== AI API 提供商选择 ====================
# 可选值: "gemini" 或 "openrouter"
AI_PROVIDER = "openrouter"  # 默认使用 openrouter

# ==================== Gemini API 配置 ====================
# Gemini API Key
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"  # 请替换为你的 Gemini API Key

# ==================== OpenRouter API 配置 ====================
# OpenRouter API Key
OPENROUTER_API_KEY = "YOUR_OPENROUTER_API_KEY"  # 请替换为你的 OpenRouter API Key
# OpenRouter 模型选择 (可选择的模型请参考 https://openrouter.ai/models)
OPENROUTER_MODEL = "deepseek/deepseek-chat-v3-0324:free"

# OpenRouter API 基础 URL
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# OpenRouter 最大输出 tokens
OPENROUTER_MAX_OUTPUT_TOKENS = 2048

# 日志文件路径
NGINX_ACCESS_LOG_PATH = "/www/wwwlogs/yanshanlaosiji.top.log"
NGINX_ERROR_LOG_PATH = "/www/wwwlogs/yanshanlaosiji.top.error.log"
PHP_FPM_LOG_PATH = "/www/server/php/74/var/log/php-fpm.log"

# 每次检测读取的最新日志行数
LOG_LINES_TO_READ = 50

# ==================== Gemini API 详细配置 ====================
# Gemini API 与模型相关配置
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"
GEMINI_MAX_OUTPUT_TOKENS = 2048 # 增加 token 数量以容纳可能的 JSON 输出
GEMINI_RESPONSE_MIME_TYPE = "application/json"

# 静态报告页面路径
REPORT_HTML_PATH = "/www/wwwroot/yanshanlaosiji.top/NginxPhpAIScanner/report.html"

# 检测频率（秒）
SCAN_INTERVAL_SECONDS = 300

# ==================== API 调用日志配置 ====================
# 是否记录 AI API 请求和响应 (适用于 Gemini 和 OpenRouter)
LOG_AI_API_CALLS = True

# AI API 请求和响应的日志路径
AI_API_LOG_PATH = "/www/wwwroot/yanshanlaosiji.top/NginxPhpAIScanner/ai_api_log.json"

# 兼容性配置 (保持向后兼容)
LOG_GEMINI_API_CALLS = LOG_AI_API_CALLS  # 向后兼容
GEMINI_API_LOG_PATH = AI_API_LOG_PATH     # 向后兼容

# 是否启用 Nginx 启动状态检测 (默认为 False)
# 此功能目前主要适用于使用 systemd 的 Linux 系统 (如 Ubuntu 15.04+, Debian 8+, CentOS 7+ 等)。
# 如果在其他系统上运行或不希望进行此检测，可以将其设置为 False。
ENABLE_NGINX_STATUS_CHECK = False

# 代理服务器配置 (可选)
# 如果您的服务器需要通过代理访问外部网络 (例如 Google API)，请在此处配置。
# 将下面的 "your_proxy_address" 和 "port" 替换为您的实际代理服务器地址和端口。
# 如果代理需要认证，格式通常是 "http://user:password@your_proxy_address:port"
PROXIES = None
# 示例:
# PROXIES = {
#    "http": "http://127.0.0.1:7890",  # 替换为您的 HTTP 代理
#    "https": "http://127.0.0.1:7890", # 替换为您的 HTTPS 代理
# }
# 或者使用 SOCKS5 代理 (需要 pip install requests[socks])
# PROXIES = {
#    "http": "socks5h://127.0.0.1:1080", # socks5h 表示通过代理进行 DNS 解析
#    "https": "socks5h://127.0.0.1:1080",
# }