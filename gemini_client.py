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

def call_gemini_api(log_data_str):
    """调用 Gemini API 并获取分析结果"""
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        print("错误：Gemini API Key 未在 config.py 中配置。")
        return None
    if not config.GEMINI_API_URL or "YOUR_PROJECT_ID" in config.GEMINI_API_URL:
        print("错误：Gemini API URL 未在 config.py 中正确配置项目ID。")
        return None

    headers = {
        "Authorization": f"Bearer {config.GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    # 根据 PRD 文档构建请求体
    # 注意：PRD 中的示例是图文问答，这里我们只需要文本
    # 我们需要构建一个更适合日志分析的 systemInstruction 和 user prompt
    system_prompt = (
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

    payload = {
        "systemInstruction": {
            "role": "system",
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"请分析以下日志数据：\n\n{log_data_str}"}]
            }
        ],
        "generationConfig": {
            "response_mime_type": config.GEMINI_RESPONSE_MIME_TYPE,
            "max_output_tokens": config.GEMINI_MAX_OUTPUT_TOKENS
        },
        "safetySettings": [ # 沿用 PRD 中的安全设置示例
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

        response = requests.post(config.GEMINI_API_URL, headers=headers, json=payload, timeout=120) # 增加超时时间
        response.raise_for_status()  # 如果请求失败 (状态码 4xx or 5xx), 会抛出 HTTPError
        
        # 尝试解析 JSON 响应
        response_json = response.json()

        # 从响应中提取模型生成的文本内容
        # 根据 PRD 的响应结构，内容在 candidates[0].content.parts[0].text
        if (response_json.get("candidates") and 
            len(response_json["candidates"]) > 0 and
            response_json["candidates"][0].get("content") and
            response_json["candidates"][0]["content"].get("parts") and
            len(response_json["candidates"][0]["content"]["parts"]) > 0 and
            response_json["candidates"][0]["content"]["parts"][0].get("text")):
            
            model_output_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
            # 尝试将模型输出的文本再次解析为 JSON
            try:
                parsed_model_output = json.loads(model_output_text)
                if config.LOG_GEMINI_API_CALLS:
                    _log_api_call(request_payload=payload, response_data={"parsed_model_output": parsed_model_output, "raw_api_response": response_json})
                return parsed_model_output
            except json.JSONDecodeError as e:
                error_msg = f"Gemini API 返回的文本不是有效的 JSON 格式: {model_output_text}. Error: {e}"
                print(error_msg)
                error_detail = {"error": "Invalid JSON response from model", "raw_output": model_output_text}
                if config.LOG_GEMINI_API_CALLS:
                    _log_api_call(request_payload=payload, response_data={"raw_api_response": response_json, "model_text_output": model_output_text}, error_message=error_msg)
                return error_detail
        else:
            error_msg = f"Gemini API 响应结构不符合预期: {response_json}"
            print(error_msg)
            error_detail = {"error": "Unexpected API response structure", "raw_response": response_json}
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