# openrouter_client.py
import requests
import json
import time
import config
import datetime
import os
import http.client as http_client
import logging

# http.client debugging (暂不启用)
# http_client.HTTPConnection.debuglevel = 1
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

def _log_api_call(request_payload, response_data=None, error_message=None):
    """以 JSON Lines 格式记录 OpenRouter API 调用到日志文件"""
    if not config.LOG_AI_API_CALLS:
        return

    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "api_provider": "openrouter",
        "request": request_payload,
    }
    if response_data is not None:
        log_entry["response"] = response_data
    if error_message:
        log_entry["error_info"] = error_message

    try:
        # 确保目录存在
        log_dir = os.path.dirname(config.AI_API_LOG_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        with open(config.AI_API_LOG_PATH, 'a', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write('\n')
    except Exception as e:
        print(f"写入 OpenRouter API 日志失败: {e}")

def call_openrouter_api(log_data_str, proxies=None):
    """
    调用 OpenRouter API 并获取分析结果。
    :param log_data_str: 要分析的日志数据字符串。
    :param proxies: 可选的代理配置字典，例如 {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}
    :return: API 分析结果或错误信息。
    """
    if not config.OPENROUTER_API_KEY or config.OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
        print("错误：OpenRouter API Key 未在 config.py 中配置。")
        return None
    if not config.OPENROUTER_API_URL:
        print("错误：OpenRouter API URL 未在 config.py 中配置。")
        return None

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "NginxPhpAIScanner/1.0"  # 尝试使用自定义 User-Agent
    }

    # 构建系统提示，与 Gemini 保持一致
    system_instruction_text = """You are an AI assistant. The user will provide a Base64 encoded string containing server logs.
Your first step is to decode this Base64 string to get the plain text server logs.
Then, analyze these decoded server logs.
Respond ONLY with a single valid JSON object, structured as follows:
{
  "findings": [
    {
      "severity": "high | medium | low | info",
      "description": "Description of the issue found in the decoded logs.",
      "recommendation": "Suggested actions.",
      "log_lines": ["Relevant original DECODED log lines."]
    }
  ],
  "summary": "Summary of the analysis of the DECODED logs."
}
If no issues are found in the decoded logs, "findings" should be an empty array.
"""

    # 构建 OpenRouter API 请求负载
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_instruction_text
            },
            {
                "role": "user",
                "content": f"请分析以下日志数据：\n\n{log_data_str}"
            }
        ],
        "max_tokens": config.OPENROUTER_MAX_OUTPUT_TOKENS,
        "response_format": {"type": "json_object"}  # 恢复强制 JSON 输出
    }

    try:
        # 定义重试参数
        max_retries = 3
        retry_delay_seconds = 5
        connect_timeout = 30
        read_timeout = 120

        for attempt in range(max_retries):
            try:
                # 在发送请求前记录
                if config.LOG_AI_API_CALLS:
                    _log_api_call(request_payload=payload)

                print(f"尝试调用 OpenRouter API (第 {attempt + 1}/{max_retries} 次)...")
                response = requests.post(
                    config.OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=(connect_timeout, read_timeout),
                    proxies=proxies
                )
                response.raise_for_status()
                
                response_json = response.json()
                # 如果请求成功，跳出重试循环
                break
            except requests.exceptions.Timeout as e:
                error_msg = f"调用 OpenRouter API 时发生超时 (尝试 {attempt + 1}/{max_retries}): {e}"
                print(error_msg)
                if config.LOG_AI_API_CALLS:
                    _log_api_call(request_payload=payload, error_message=f"Attempt {attempt + 1} Timeout: {e}")
                if attempt < max_retries - 1:
                    print(f"{retry_delay_seconds} 秒后重试...")
                    time.sleep(retry_delay_seconds)
                else:
                    print("已达到最大重试次数，放弃。")
                    return {"error": f"API request failed after {max_retries} attempts due to timeout: {e}"}
            except requests.exceptions.RequestException as e:
                error_msg = f"调用 OpenRouter API 时发生网络错误 (尝试 {attempt + 1}/{max_retries}): {e}"
                print(error_msg)
                if config.LOG_AI_API_CALLS:
                    _log_api_call(request_payload=payload, error_message=f"Attempt {attempt + 1} RequestException: {e}")
                if attempt < max_retries - 1:
                    print(f"{retry_delay_seconds} 秒后重试...")
                    time.sleep(retry_delay_seconds)
                else:
                    print("已达到最大重试次数，放弃。")
                    return {"error": f"API request failed after {max_retries} attempts: {e}"}
        else:
            return {"error": "API request failed after all retries without a definitive success or specific error."}

        # 检查响应结构
        if not response_json.get("choices") or not response_json["choices"]:
            error_msg = f"OpenRouter API 响应中缺少 'choices'。响应: {response_json}"
            print(error_msg)
            error_detail = {"error": "Missing 'choices' in API response", "raw_response": response_json}
            if config.LOG_AI_API_CALLS:
                _log_api_call(request_payload=payload, response_data=response_json, error_message=error_msg)
            return error_detail

        choice = response_json["choices"][0]
        finish_reason = choice.get("finish_reason")
        
        if choice.get("message") and choice["message"].get("content"):
            model_output_text = choice["message"]["content"]

            # 处理可能被 markdown 代码块包装的 JSON 响应
            cleaned_text = model_output_text.strip()

            # 检查是否被 ```json 和 ``` 包装
            if cleaned_text.startswith("```json") and cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[7:-3].strip()
                print("检测到 markdown 'json' 代码块，已清理。")
            elif cleaned_text.startswith("```") and cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[3:-3].strip()
                print("检测到无标识 markdown 代码块，已清理。")
            
            # 进一步清理可能残余的语言标识符，例如 "json\n{...}"
            if cleaned_text.lower().startswith("json"):
                # 寻找第一个 '{' 或 '['
                first_bracket = cleaned_text.find('{')
                first_square_bracket = cleaned_text.find('[')
                
                start_index = -1
                if first_bracket != -1 and first_square_bracket != -1:
                    start_index = min(first_bracket, first_square_bracket)
                elif first_bracket != -1:
                    start_index = first_bracket
                elif first_square_bracket != -1:
                    start_index = first_square_bracket
                
                if start_index != -1:
                    cleaned_text = cleaned_text[start_index:]
                    print(f"检测到前缀语言标识符，已清理。处理后文本前缀: {cleaned_text[:30]}...")
                else:
                    # 如果有 "json" 开头但找不到括号，可能不是有效的json，让后续解析处理
                    pass

            try:
                parsed_model_output = json.loads(cleaned_text)
                if config.LOG_AI_API_CALLS:
                    _log_api_call(request_payload=payload, response_data={"parsed_model_output": parsed_model_output, "raw_api_response": response_json})

                # 如果因为长度限制完成，添加警告
                if finish_reason == "length":
                    parsed_model_output["warning_finish_reason"] = "length: Response might be truncated."
                return parsed_model_output
            except json.JSONDecodeError as e:
                error_msg = f"OpenRouter API 返回的文本不是有效的 JSON 格式: {model_output_text}. 清理后的文本: {cleaned_text}. Error: {e}"
                print(error_msg)
                error_detail = {"error": "Invalid JSON response from model", "raw_output": model_output_text, "cleaned_output": cleaned_text, "finish_reason": finish_reason}
                if config.LOG_AI_API_CALLS:
                    _log_api_call(request_payload=payload, response_data={"raw_api_response": response_json, "model_text_output": model_output_text, "cleaned_text": cleaned_text}, error_message=error_msg)
                return error_detail
        elif finish_reason == "length":
            error_msg = f"OpenRouter API 响应因长度限制而截断，且未能提取有效文本内容。响应: {response_json}"
            print(error_msg)
            error_detail = {"error": "Response truncated due to length limit and no text content found", "raw_response": response_json, "finish_reason": finish_reason}
            if config.LOG_AI_API_CALLS:
                _log_api_call(request_payload=payload, response_data=response_json, error_message=error_msg)
            return error_detail
        else:
            error_msg = f"OpenRouter API 响应结构不符合预期或缺少文本内容。Finish reason: {finish_reason}. 响应: {response_json}"
            print(error_msg)
            error_detail = {"error": "Unexpected API response structure or missing text", "raw_response": response_json, "finish_reason": finish_reason}
            if config.LOG_AI_API_CALLS:
                _log_api_call(request_payload=payload, response_data=response_json, error_message=error_msg)
            return error_detail

    except json.JSONDecodeError as e:
        raw_response_text = "Unknown (response object not available or text attribute missing)"
        if 'response' in locals() and response is not None and hasattr(response, 'text'):
            raw_response_text = response.text
        error_msg = f"OpenRouter API 响应不是有效的 JSON 格式。响应内容: {raw_response_text}. Error: {e}"
        print(error_msg)
        if config.LOG_AI_API_CALLS:
            _log_api_call(request_payload=payload, response_data={"raw_text": raw_response_text}, error_message=error_msg)
        return {"error": "API response is not valid JSON", "raw_response": raw_response_text}
    except Exception as e:
        error_msg = f"调用 OpenRouter API 时发生未知错误: {e}"
        print(error_msg)
        if config.LOG_AI_API_CALLS:
            _log_api_call(request_payload=payload, error_message=error_msg)
        return {"error": f"Unknown error during API call: {e}"}
