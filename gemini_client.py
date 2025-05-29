# gemini_client.py
import requests
import json
import config # 假设 config.py 仍然在根目录，并且 gemini_client.py 需要访问它
import datetime
import os

def _log_api_call(request_payload, response_data=None, error_message=None):
    """以 JSON Lines 格式记录 Gemini API 调用到日志文件"""
    if not config.LOG_GEMINI_API_CALLS:
        return

    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "request": request_payload,
    }
    if response_data is not None:
        log_entry["response"] = response_data
    if error_message:
        log_entry["error_info"] = error_message

    try:
        # 确保目录存在
        log_dir = os.path.dirname(config.GEMINI_API_LOG_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            # print(f"创建日志目录: {log_dir}") # 可以在调试时取消注释

        with open(config.GEMINI_API_LOG_PATH, 'a', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write('\n')
    except Exception as e:
        print(f"写入 Gemini API 日志失败: {e}")

def call_gemini_api(log_data_str, proxies=None):
    """
    调用 Gemini API 并获取分析结果。
    :param log_data_str: 要分析的日志数据字符串。
    :param proxies: 可选的代理配置字典，例如 {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}
    :return: API 分析结果或错误信息。
    """
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        print("错误：Gemini API Key 未在 config.py 中配置。")
        return None
    if not config.GEMINI_API_URL: #移除了对 PROJECT_ID 的检查, 因为 generativelanguage URL 不含它
        print("错误：Gemini API URL 未在 config.py 中配置。")
        return None

    # generativelanguage.googleapis.com 端点使用 API Key 作为 URL 参数
    api_url_with_key = f"{config.GEMINI_API_URL}?key={config.GEMINI_API_KEY}"

    headers = {
        "Content-Type": "application/json",
    }

    # 日志分析的 system_instruction 和 user prompt
    # 对于 generativelanguage.googleapis.com, 使用 system_instruction
    system_instruction_text = (
        "你是一个专业的网络安全分析师，专门分析 Nginx 和 PHP 日志以检测潜在的入侵或恶意活动。"
        "请仔细分析提供的日志片段，并以 JSON 格式返回你的分析结果。"
        "JSON 应包含以下字段："
        "  - 'timestamp': 分析执行的时间戳 (ISO 8601格式),"
        "  - 'log_type': 被分析的日志类型 (例如 'nginx_access', 'nginx_error', 'php_fpm'),"
        "  - 'findings': 一个包含具体发现的列表，每个发现是一个对象，包含："
        "    - 'severity': 威胁等级 (例如 'critical', 'high', 'medium', 'low', 'info'),"
        "    - 'description': 对发现的详细描述,"
        "    - 'recommendation': 针对该发现的建议措施 (可选),"
        "    - 'log_lines': 相关的原始日志行 (可选，最多5行)"
        "  - 'summary': 对本次分析的总体摘要。"
        "如果没有发现异常，'findings' 列表可以为空，并在 'summary' 中说明一切正常。"
        "确保返回的是一个有效的 JSON 对象。"
    )

    # 动态调整 maxOutputTokens
    # 目标设为 8192，除非配置中已设置更高且合理的值
    configured_max_tokens = getattr(config, 'GEMINI_MAX_OUTPUT_TOKENS', 2048) # 默认2048以防万一未配置
    target_max_output_tokens = 8192

    if configured_max_tokens > target_max_output_tokens and configured_max_tokens <= 8192: # 如果配置值在合理范围内且大于我们的目标
        effective_max_output_tokens = configured_max_tokens
    else:
        effective_max_output_tokens = target_max_output_tokens
        if configured_max_tokens < target_max_output_tokens:
             print(f"提示: config.GEMINI_MAX_OUTPUT_TOKENS ({configured_max_tokens}) 较小。")
             print(f"       本次调用将使用 {effective_max_output_tokens} 作为 maxOutputTokens 以尝试获取完整响应。")
        elif configured_max_tokens > 8192: # 如果配置值过大
            print(f"警告: config.GEMINI_MAX_OUTPUT_TOKENS ({configured_max_tokens}) 可能超过模型支持的上限。")
            print(f"       本次调用将使用 {effective_max_output_tokens} 作为 maxOutputTokens。")


    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction_text}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"请分析以下日志数据：\n\n{log_data_str}"}]
            }
        ],
        "generationConfig": {
            "responseMimeType": config.GEMINI_RESPONSE_MIME_TYPE,
            "maxOutputTokens": effective_max_output_tokens
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]
    }

    try:
        # 在发送请求前记录
        if config.LOG_GEMINI_API_CALLS:
            _log_api_call(request_payload=payload)
        response = requests.post(api_url_with_key, headers=headers, json=payload, timeout=180, proxies=proxies) # 增加超时时间
        response.raise_for_status()
        
        response_json = response.json()

        # 检查是否有候选内容以及 finishReason
        if not response_json.get("candidates") or not response_json["candidates"]:
            error_msg = f"Gemini API 响应中缺少 'candidates'。响应: {response_json}"
            print(error_msg)
            error_detail = {"error": "Missing 'candidates' in API response", "raw_response": response_json}
            if config.LOG_GEMINI_API_CALLS:
                _log_api_call(request_payload=payload, response_data=response_json, error_message=error_msg)
            return error_detail

        candidate = response_json["candidates"][0]
        finish_reason = candidate.get("finishReason")

        if (candidate.get("content") and
            candidate["content"].get("parts") and
            len(candidate["content"]["parts"]) > 0 and
            candidate["content"]["parts"][0].get("text")):
            
            model_output_text = candidate["content"]["parts"][0]["text"]
            try:
                parsed_model_output = json.loads(model_output_text)
                if config.LOG_GEMINI_API_CALLS:
                    _log_api_call(request_payload=payload, response_data={"parsed_model_output": parsed_model_output, "raw_api_response": response_json})
                # 如果因为MAX_TOKENS完成，也附加一个警告
                if finish_reason == "MAX_TOKENS":
                    parsed_model_output["warning_finish_reason"] = "MAX_TOKENS: Response might be truncated."
                return parsed_model_output
            except json.JSONDecodeError as e:
                error_msg = f"Gemini API 返回的文本不是有效的 JSON 格式: {model_output_text}. Error: {e}"
                print(error_msg)
                error_detail = {"error": "Invalid JSON response from model", "raw_output": model_output_text, "finish_reason": finish_reason}
                if config.LOG_GEMINI_API_CALLS:
                    _log_api_call(request_payload=payload, response_data={"raw_api_response": response_json, "model_text_output": model_output_text}, error_message=error_msg)
                return error_detail
        elif finish_reason == "MAX_TOKENS":
            error_msg = f"Gemini API 响应因 MAX_TOKENS 而截断，且未能提取有效文本内容。响应: {response_json}"
            print(error_msg)
            error_detail = {"error": "Response truncated due to MAX_TOKENS and no text content found", "raw_response": response_json, "finish_reason": finish_reason}
            if config.LOG_GEMINI_API_CALLS:
                _log_api_call(request_payload=payload, response_data=response_json, error_message=error_msg)
            return error_detail
        else:
            error_msg = f"Gemini API 响应结构不符合预期或缺少文本内容。Finish reason: {finish_reason}. 响应: {response_json}"
            print(error_msg)
            error_detail = {"error": "Unexpected API response structure or missing text", "raw_response": response_json, "finish_reason": finish_reason}
            if config.LOG_GEMINI_API_CALLS:
                _log_api_call(request_payload=payload, response_data=response_json, error_message=error_msg)
            return error_detail
    except requests.exceptions.RequestException as e:
        error_msg = f"调用 Gemini API 时发生网络错误: {e}"
        print(error_msg)
        if config.LOG_GEMINI_API_CALLS:
            _log_api_call(request_payload=payload, error_message=error_msg)
        return {"error": f"API request failed: {e}"}
    except json.JSONDecodeError as e: # 这个 catch 对应 response.json() 的解析错误
        raw_response_text = "Unknown (response object not available or text attribute missing)"
        if 'response' in locals() and hasattr(response, 'text'):
            raw_response_text = response.text
        error_msg = f"Gemini API 响应不是有效的 JSON 格式。响应内容: {raw_response_text}. Error: {e}"
        print(error_msg)
        if config.LOG_GEMINI_API_CALLS:
            _log_api_call(request_payload=payload, response_data={"raw_text": raw_response_text}, error_message=error_msg)
        return {"error": "API response is not valid JSON", "raw_response": raw_response_text}
    except Exception as e:
        error_msg = f"调用 Gemini API 时发生未知错误: {e}"
        print(error_msg)
        if config.LOG_GEMINI_API_CALLS:
            _log_api_call(request_payload=payload, error_message=error_msg)
        return {"error": f"Unknown error during API call: {e}"}