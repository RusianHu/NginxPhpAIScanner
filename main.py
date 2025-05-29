# main.py
import time
import json
import os
import subprocess # 用于执行外部命令
# import requests # requests 已移至 gemini_client.py
from datetime import datetime

# 从 gemini_client.py 导入封装的 API 调用函数
from gemini_client import call_gemini_api

# 从 config.py 导入配置
try:
    import config
except ImportError:
    print("错误：找不到 config.py 文件。请确保该文件存在于项目根目录中。")
    exit()

def read_latest_log_lines(log_path, num_lines):
    """读取日志文件的最后 N 行"""
    if not os.path.exists(log_path):
        print(f"警告：日志文件 {log_path} 不存在。")
        return []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return lines[-num_lines:]
    except Exception as e:
        print(f"读取日志文件 {log_path} 时出错: {e}")
        return []

# def call_gemini_api(log_data_str): ... # 此函数已移至 gemini_client.py

def update_report_html(analysis_results):
    """将分析结果更新到静态 HTML 报告页面"""
    # TODO: 实现 HTML 生成逻辑
    # 目前仅打印到控制台
    print("更新报告...")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z") # 更友好的时间格式
    
    # HTML 头部、样式和页面结构
    html_header = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nginx PHP AI 安全检测报告</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🛡️</text></svg>">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
            margin: 0;
            padding: 0; /* Body padding removed, handled by container or specific sections */
            background-color: #f8f9fa;
            color: #212529;
            line-height: 1.6;
        }}
        .container {{
            background-color: #ffffff;
            padding: 20px 30px 30px 30px; /* top, right, bottom, left */
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.07);
            max-width: 1200px;
            margin: 30px auto; /* Added top/bottom margin for body */
        }}
        h1 {{
            color: #343a40;
            border-bottom: 2px solid #007bff;
            padding-bottom: 15px;
            margin-top: 0;
            margin-bottom: 10px; /* Reduced margin to h1 */
            font-size: 2rem;
        }}
        h2 {{
            color: #495057;
            margin-top: 2.5rem;
            margin-bottom: 1.2rem;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 10px;
            font-size: 1.6rem;
        }}
        .report-meta {{
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 25px; /* Increased margin below meta */
        }}
        .log-entry {{
            border: 1px solid #e9ecef;
            padding: 20px;
            margin-bottom: 25px;
            border-radius: 6px;
            background-color: #ffffff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.04);
            transition: box-shadow 0.2s ease-in-out;
        }}
        .log-entry:hover {{
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}
        .log-entry p {{
            margin: 10px 0;
        }}
        .log-entry strong.label {{ /* For "Description:", "Recommendation:" etc. */
            color: #343a40; /* Darker label */
            font-weight: 600; /* Slightly bolder */
        }}
        /* Severity border colors */
        .severity-critical {{ border-left: 6px solid #dc3545; }}
        .severity-high {{ border-left: 6px solid #fd7e14; }}
        .severity-medium {{ border-left: 6px solid #ffc107; }}
        .severity-low {{ border-left: 6px solid #17a2b8; }}
        .severity-info {{ border-left: 6px solid #6c757d; }}

        .severity-badge {{
            display: inline-block;
            padding: 0.3em 0.6em;
            font-size: 0.75em; /* Smaller badge text */
            font-weight: 700; /* Bolder badge text */
            line-height: 1;
            text-align: center;
            white-space: nowrap;
            vertical-align: baseline;
            border-radius: 0.3rem; /* Slightly more rounded */
            text-transform: uppercase;
            margin-left: 8px;
        }}
        /* Badge specific colors */
        .severity-critical .severity-badge {{ background-color: #dc3545; color: white; }}
        .severity-high .severity-badge {{ background-color: #fd7e14; color: white; }}
        .severity-medium .severity-badge {{ background-color: #ffc107; color: #212529; }}
        .severity-low .severity-badge {{ background-color: #17a2b8; color: white; }}
        .severity-info .severity-badge {{ background-color: #6c757d; color: white; }}

        .summary {{
            font-style: normal;
            background-color: #f1f3f5; /* Lighter summary background */
            padding: 12px 15px;
            border-radius: 4px;
            margin-top: 15px;
            border-left: 3px solid #adb5bd; /* Subtle left border for summary */
        }}
        .error {{ /* Enhanced error styling */
            color: #721c24;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-left-width: 6px; /* Match severity border */
            padding: 15px 20px;
            border-radius: 6px;
        }}
        .error strong {{ color: #721c24; }}
        .raw-output {{
            background-color: #e9ecef;
            padding: 12px 15px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 350px; /* Increased max height */
            overflow-y: auto;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            font-size: 0.875em;
            margin-top: 8px;
        }}
        hr {{
            border: 0;
            border-top: 1px solid #e0e0e0; /* Lighter hr */
            margin: 3rem 0; /* More spacing around hr */
        }}
        footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 25px;
            border-top: 1px solid #dee2e6;
            font-size: 0.9em;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Nginx PHP AI 安全检测报告</h1>
        <p class="report-meta">最后更新时间: {current_time}</p>
"""

    # Actual footer content (without </div></body></html>)
    html_footer_content = f"""
        <footer>
            <p>报告由 NginxPhpAIScanner 生成 &copy; {datetime.now().year}</p>
        </footer>"""
    
    # This marker is used to strip the end of an existing HTML file
    # It should match the very end of the file structure, after the container div.
    body_end_marker = "    </div>\n</body>\n</html>" # Kept same as original for existing file parsing logic

    report_content_accumulator = "" # Use a new variable to build current run's content

    if not os.path.exists(config.REPORT_HTML_PATH):
        report_content_accumulator = html_header # Start with header
    else:
        try:
            with open(config.REPORT_HTML_PATH, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            # Try to strip the old footer and the final </div></body></html>
            # This part is sensitive to the exact structure of the old file's end.
            # We assume the old file ends with body_end_marker, and any footer content is before it.
            
            # A more robust way to handle existing content would be to parse out
            # the actual log entries if the structure is known.
            # For now, we stick to the original logic of replacing body_end_marker.
            if body_end_marker in existing_content:
                # This gets content before "    </div>\n</body>\n</html>"
                # This gets content before "    </div>\n</body>\n</html>"
                content_before_end_marker = existing_content.replace(body_end_marker, "")
                # Now, try to remove the old footer content if it exists
                # We assume the old footer is exactly html_footer_content
                if html_footer_content in content_before_end_marker:
                    report_content_accumulator = content_before_end_marker.replace(html_footer_content, "")
                else:
                    # If the exact footer content isn't found (e.g., it was modified or not there),
                    # we might risk leaving an old footer or part of it.
                    # A more robust solution might involve searching for <footer> tags.
                    # For now, we proceed with the content before the end marker.
                    report_content_accumulator = content_before_end_marker
            else:
                 # Fallback if marker not found: preserve existing content and append.
                 # This might lead to malformed HTML if the existing file is also malformed,
                 # but it prevents data loss.
                 print(f"警告：报告文件 {config.REPORT_HTML_PATH} 结构可能已损坏或不完整 (未找到结束标记)。将尝试追加新内容。")
                 report_content_accumulator = existing_content
        except Exception as e:
            print(f"读取现有报告 {config.REPORT_HTML_PATH} 失败: {e}")
            report_content_accumulator = html_header

    # Append new analysis results for this run
    for result_group in analysis_results:
        log_type_display = result_group.get('log_type', '未知日志').replace('_', ' ').title()
        # Format analysis_time if it's a string, otherwise use as is (assuming it's already formatted)
        analysis_time_raw = result_group.get('timestamp', datetime.now().isoformat())
        try:
            # Attempt to parse if it's a full ISO string, then reformat
            analysis_dt = datetime.fromisoformat(analysis_time_raw.replace("Z", "+00:00"))
            analysis_time_display = analysis_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        except ValueError:
            analysis_time_display = analysis_time_raw # Use as is if not standard ISO or already formatted

        report_content_accumulator += f"<h2>{log_type_display} 分析 ({analysis_time_display})</h2>\n"

        if result_group.get("error"):
            report_content_accumulator += f"<div class='log-entry error'>\n"
            report_content_accumulator += f"  <p><strong class='label'>错误:</strong> {result_group['error']}</p>\n"
            if result_group.get("raw_output"):
                report_content_accumulator += f"  <p><strong class='label'>原始模型输出:</strong></p><pre class='raw-output'>{result_group['raw_output']}</pre>\n"
            if result_group.get("raw_response"):
                report_content_accumulator += f"  <p><strong class='label'>原始API响应:</strong></p><pre class='raw-output'>{json.dumps(result_group['raw_response'], indent=2, ensure_ascii=False)}</pre>\n"
            report_content_accumulator += "</div>\n"
            continue

        findings = result_group.get('findings', [])
        summary = result_group.get('summary', '没有提供摘要。')

        if not findings:
            report_content_accumulator += f"<div class='log-entry severity-info'>\n" # Default to info if no findings
            report_content_accumulator += f"  <p><strong class='label'>状态:</strong> 未发现明显异常。</p>\n"
            report_content_accumulator += f"  <p class='summary'><strong class='label'>摘要:</strong> {summary}</p>\n"
            report_content_accumulator += "</div>\n"
        else:
            for finding in findings:
                severity = finding.get('severity', 'info').lower()
                description = finding.get('description', '无描述。')
                recommendation = finding.get('recommendation', '')
                log_lines = finding.get('log_lines', [])

                report_content_accumulator += f"<div class='log-entry severity-{severity}'>\n"
                report_content_accumulator += f"  <p><strong class='label'>严重性:</strong> <span class='severity-badge severity-{severity}'>{severity.upper()}</span></p>\n"
                report_content_accumulator += f"  <p><strong class='label'>描述:</strong> {description}</p>\n"
                if recommendation:
                    report_content_accumulator += f"  <p><strong class='label'>建议:</strong> {recommendation}</p>\n"
                if log_lines:
                    report_content_accumulator += f"  <p><strong class='label'>相关日志:</strong></p><pre class='raw-output'>{''.join(log_lines)}</pre>\n"
                report_content_accumulator += "</div>\n"
            report_content_accumulator += f"<p class='summary'><strong class='label'>总体摘要:</strong> {summary}</p>\n"
        
        report_content_accumulator += "<hr>\n"

    # Combine accumulated content with the new footer and the final HTML tags
    final_html_output = report_content_accumulator + html_footer_content + body_end_marker

    try:
        with open(config.REPORT_HTML_PATH, 'w', encoding='utf-8') as f:
            f.write(final_html_output)
        print(f"报告已更新: {config.REPORT_HTML_PATH}")
    except Exception as e:
        print(f"写入报告 {config.REPORT_HTML_PATH} 失败: {e}")

def is_nginx_running():
    """检查 Nginx 服务是否正在运行并监听端口"""
    try:
        # 检查 systemd 服务状态
        active_check = subprocess.run(['systemctl', 'is-active', 'nginx'], capture_output=True, text=True, check=False)
        if active_check.stdout.strip() != "active":
            print(f"Nginx 服务状态不是 'active': {active_check.stdout.strip()}")
            # 即使 systemctl is-active 不是 active，也继续检查端口，因为 'active (exited)' 状态也可能发生
            # return False

        # 检查 Nginx 是否在监听端口 (通常是 80 或 443)
        # 优先使用 ss，如果不存在则尝试 netstat
        try:
            listen_check = subprocess.run(['ss', '-tlpn'], capture_output=True, text=True, check=True)
        except FileNotFoundError:
            print("未找到 'ss' 命令，尝试使用 'netstat'...")
            try:
                listen_check = subprocess.run(['netstat', '-tlpn'], capture_output=True, text=True, check=True)
            except FileNotFoundError:
                print("错误：未找到 'ss' 或 'netstat' 命令，无法检查 Nginx 监听端口。")
                return False # 无法确认，保守处理
        
        if 'nginx' in listen_check.stdout:
            print("Nginx 正在运行并监听端口。")
            return True
        else:
            print("Nginx 可能已启动 (systemctl is-active)，但未检测到其监听任何端口。")
            print("ss/netstat output:\n", listen_check.stdout)
            return False

    except subprocess.CalledProcessError as e:
        print(f"执行命令检查 Nginx 状态时出错: {e}")
        if e.stderr:
            print(f"错误输出: {e.stderr}")
        return False
    except FileNotFoundError:
        print("错误：未找到 'systemctl' 命令。此脚本可能未在支持 systemd 的系统上运行，或者 systemctl 不在 PATH 中。")
        # 在这种情况下，可以考虑其他检查方法或让用户配置
        return False # 无法确认，保守处理
    except Exception as e:
        print(f"检查 Nginx 状态时发生未知错误: {e}")
        return False

def main_scan_loop():
    """主扫描循环"""
    if config.ENABLE_NGINX_STATUS_CHECK:
        print("正在检查 Nginx 服务状态 (根据配置 ENABLE_NGINX_STATUS_CHECK=True)...")
        if not is_nginx_running():
            print("Nginx 服务未运行或未正确监听端口。请检查 Nginx 配置和状态。")
            print("安全检测服务将退出。")
            # 可以在这里添加错误信息到HTML报告
            error_report_nginx = [{
                "timestamp": datetime.now().isoformat(),
                "log_type": "system_check",
                "error": "Nginx 服务未运行或未正确监听端口。",
                "summary": "无法启动安全扫描，因为依赖的 Nginx 服务存在问题。"
            }]
            # 尝试更新报告，即使服务未启动，也记录下这个问题
            # 确保 REPORT_HTML_PATH 已定义，否则 update_report_html 可能会失败
            if hasattr(config, 'REPORT_HTML_PATH') and config.REPORT_HTML_PATH:
                 # 首次运行时，如果报告文件不存在，先创建一个空的报告结构
                if not os.path.exists(config.REPORT_HTML_PATH):
                    update_report_html([]) # 创建基础HTML
                update_report_html(error_report_nginx)
            else:
                print("错误：REPORT_HTML_PATH 未在 config.py 中配置，无法记录 Nginx 状态错误到报告。")
            exit()
        print("Nginx 服务状态正常。")
    else:
        print("Nginx 启动状态检测已禁用 (根据配置 ENABLE_NGINX_STATUS_CHECK=False)。")

    print(f"Nginx PHP AI 安全检测服务启动，每 {config.SCAN_INTERVAL_SECONDS} 秒检测一次。")
    
    # 首次运行时，如果报告文件不存在，先创建一个空的报告结构
    if not os.path.exists(config.REPORT_HTML_PATH):
        update_report_html([]) # 传入空列表以创建基础HTML结构

    while True:
        print(f"\n[{datetime.now().isoformat()}] 开始新一轮日志检测...")
        all_analysis_results_for_this_run = []

        log_files_to_scan = {
            "nginx_access": config.NGINX_ACCESS_LOG_PATH,
            "nginx_error": config.NGINX_ERROR_LOG_PATH,
            "php_fpm": config.PHP_FPM_LOG_PATH,
        }

        for log_type, log_path in log_files_to_scan.items():
            print(f"正在读取 {log_type} 日志: {log_path}")
            latest_lines = read_latest_log_lines(log_path, config.LOG_LINES_TO_READ)

            if not latest_lines:
                print(f"{log_type} 日志为空或读取失败，跳过分析。")
                # 即使日志为空，也为报告生成一个条目
                empty_log_result = {
                    "timestamp": datetime.now().isoformat(),
                    "log_type": log_type,
                    "findings": [],
                    "summary": f"日志文件 {log_path} 为空或无法读取。"
                }
                all_analysis_results_for_this_run.append(empty_log_result)
                continue

            log_data_str = "".join(latest_lines)
            print(f"准备调用 Gemini API 分析 {log_type} 日志 ({len(latest_lines)} 行)...")
            
            analysis_result = call_gemini_api(log_data_str)

            if analysis_result:
                # 确保结果中包含 log_type 和 timestamp，即使API调用失败
                analysis_result.setdefault("log_type", log_type)
                analysis_result.setdefault("timestamp", datetime.now().isoformat())
                all_analysis_results_for_this_run.append(analysis_result)
                print(f"Gemini API 对 {log_type} 日志分析完成。")
                # print(json.dumps(analysis_result, indent=2, ensure_ascii=False)) # 调试输出
            else:
                print(f"Gemini API 对 {log_type} 日志分析失败。")
                # API 调用彻底失败时，也记录一个错误条目
                error_result = {
                    "timestamp": datetime.now().isoformat(),
                    "log_type": log_type,
                    "error": "API call returned no result or an unrecoverable error.",
                    "summary": "无法从Gemini API获取分析结果。"
                }
                all_analysis_results_for_this_run.append(error_result)
        
        if all_analysis_results_for_this_run:
            update_report_html(all_analysis_results_for_this_run)
        else:
            print("本轮没有日志数据被分析，不更新报告。")

        print(f"本轮检测完成，等待 {config.SCAN_INTERVAL_SECONDS} 秒...")
        time.sleep(config.SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    # 确保必要的配置存在
    required_configs = {
        "GEMINI_API_KEY": getattr(config, "GEMINI_API_KEY", "YOUR_GEMINI_API_KEY"),
        "GEMINI_API_URL": getattr(config, "GEMINI_API_URL", "YOUR_PROJECT_ID"),
        "NGINX_ACCESS_LOG_PATH": getattr(config, "NGINX_ACCESS_LOG_PATH", None),
        "NGINX_ERROR_LOG_PATH": getattr(config, "NGINX_ERROR_LOG_PATH", None),
        "PHP_FPM_LOG_PATH": getattr(config, "PHP_FPM_LOG_PATH", None),
        "REPORT_HTML_PATH": getattr(config, "REPORT_HTML_PATH", None),
        "LOG_LINES_TO_READ": getattr(config, "LOG_LINES_TO_READ", 0),
        "SCAN_INTERVAL_SECONDS": getattr(config, "SCAN_INTERVAL_SECONDS", 0),
        "ENABLE_NGINX_STATUS_CHECK": getattr(config, "ENABLE_NGINX_STATUS_CHECK", True), # 添加新的配置项检查，默认为True
    }
    # 打印 Nginx 状态检测的配置状态
    print(f"配置加载：Nginx 状态检测已 {'启用' if required_configs['ENABLE_NGINX_STATUS_CHECK'] else '禁用'} (通过 ENABLE_NGINX_STATUS_CHECK 配置)。")

    missing_configs = False
    if required_configs["GEMINI_API_KEY"] == "YOUR_GEMINI_API_KEY":
        print("错误：请在 config.py 中配置您的 GEMINI_API_KEY。")
        missing_configs = True
    if "YOUR_PROJECT_ID" in required_configs["GEMINI_API_URL"]:
        print("错误：请在 config.py 中正确配置您的 GEMINI_API_URL (包含 PROJECT_ID)。")
        missing_configs = True
    for key, value in required_configs.items():
        if value is None or (isinstance(value, (int, float)) and value == 0 and key not in ["SCAN_INTERVAL_SECONDS"]): # SCAN_INTERVAL_SECONDS 可以是0用于测试
            if key not in ["GEMINI_API_KEY", "GEMINI_API_URL"]: # 上面已经检查过了
                print(f"错误：配置项 {key} 未在 config.py 中设置或值无效。")
                missing_configs = True
    
    if missing_configs:
        print("请检查 config.py 文件并补全缺失的配置项后重试。")
        exit()

    try:
        main_scan_loop()
    except KeyboardInterrupt:
        print("\n服务已手动停止。")
    except Exception as e:
        print(f"服务发生未捕获的致命错误: {e}")
        # 在发生致命错误时，尝试记录到报告中
        error_report = [{
            "timestamp": datetime.now().isoformat(),
            "log_type": "system_error",
            "error": f"服务发生未捕获的致命错误: {e}",
            "summary": "服务意外终止。"
        }]
        update_report_html(error_report)