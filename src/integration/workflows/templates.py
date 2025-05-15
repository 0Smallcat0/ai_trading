"""
工作流模板模組

此模組提供預定義的n8n工作流模板函數，用於創建各種自動化工作流。
"""

import copy
from typing import Any, Dict, List, Optional

from src.core.logger import logger

from .config import BASE_WORKFLOW_TEMPLATE, NODE_TEMPLATES


def get_market_data_workflow(
    name: str = "市場數據獲取工作流",
    schedule_interval: int = 15,
    api_url: str = "http://localhost:8000",
    symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    創建市場數據獲取工作流

    Args:
        name: 工作流名稱
        schedule_interval: 排程間隔（分鐘）
        api_url: API URL
        symbols: 股票代碼列表

    Returns:
        Dict[str, Any]: 工作流定義
    """
    # 複製基本模板
    workflow = copy.deepcopy(BASE_WORKFLOW_TEMPLATE)
    workflow["name"] = name
    workflow["tags"] = ["市場數據", "自動化"]

    # 設置節點
    nodes = []

    # 觸發器節點
    trigger_node = copy.deepcopy(NODE_TEMPLATES["schedule_trigger"])
    trigger_node["parameters"]["rule"]["interval"][0][
        "minuteInterval"
    ] = schedule_interval
    trigger_node["name"] = f"每{schedule_interval}分鐘觸發"
    trigger_node["position"] = [0, 0]
    nodes.append(trigger_node)

    # 獲取市場數據節點
    fetch_node = copy.deepcopy(NODE_TEMPLATES["http_request"])
    fetch_node["parameters"]["url"] = f"{api_url}/api/market-data/fetch"
    fetch_node["parameters"]["method"] = "POST"
    fetch_node["parameters"]["jsonParameters"] = True
    if symbols:
        fetch_node["parameters"]["bodyParametersJson"] = {"symbols": symbols}
    fetch_node["name"] = "獲取市場數據"
    fetch_node["position"] = [220, 0]
    nodes.append(fetch_node)

    # 檢查結果節點
    check_node = copy.deepcopy(NODE_TEMPLATES["if"])
    check_node["parameters"]["conditions"]["string"][0][
        "value1"
    ] = "={{ $json.success }}"
    check_node["parameters"]["conditions"]["string"][0]["operation"] = "equal"
    check_node["parameters"]["conditions"]["string"][0]["value2"] = "true"
    check_node["name"] = "檢查結果"
    check_node["position"] = [440, 0]
    nodes.append(check_node)

    # 處理數據節點
    process_node = copy.deepcopy(NODE_TEMPLATES["http_request"])
    process_node["parameters"]["url"] = f"{api_url}/api/market-data/process"
    process_node["parameters"]["method"] = "POST"
    process_node["parameters"]["jsonParameters"] = True
    process_node["name"] = "處理市場數據"
    process_node["position"] = [660, -100]
    nodes.append(process_node)

    # 錯誤通知節點
    error_node = copy.deepcopy(NODE_TEMPLATES["slack"])
    error_node["parameters"]["text"] = "=市場數據獲取失敗: {{ $json.error }}"
    error_node["parameters"]["channel"] = "trading-alerts"
    error_node["name"] = "發送錯誤通知"
    error_node["position"] = [660, 100]
    nodes.append(error_node)

    # 設置連接
    connections = {
        f"每{schedule_interval}分鐘觸發": {
            "main": [[{"node": "獲取市場數據", "type": "main", "index": 0}]]
        },
        "獲取市場數據": {"main": [[{"node": "檢查結果", "type": "main", "index": 0}]]},
        "檢查結果": {
            "main": [
                [{"node": "處理市場數據", "type": "main", "index": 0}],
                [{"node": "發送錯誤通知", "type": "main", "index": 0}],
            ]
        },
    }

    # 更新工作流
    workflow["nodes"] = nodes
    workflow["connections"] = connections

    logger.info(f"已創建市場數據獲取工作流: {name}")
    return workflow


def strategy_execution_workflow(
    name: str = "策略執行工作流",
    schedule_interval: int = 30,
    api_url: str = "http://localhost:8000",
    strategy_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    創建策略執行工作流

    Args:
        name: 工作流名稱
        schedule_interval: 排程間隔（分鐘）
        api_url: API URL
        strategy_id: 策略ID

    Returns:
        Dict[str, Any]: 工作流定義
    """
    # 複製基本模板
    workflow = copy.deepcopy(BASE_WORKFLOW_TEMPLATE)
    workflow["name"] = name
    workflow["tags"] = ["策略", "交易", "自動化"]

    # 設置節點
    nodes = []

    # 觸發器節點
    trigger_node = copy.deepcopy(NODE_TEMPLATES["schedule_trigger"])
    trigger_node["parameters"]["rule"]["interval"][0][
        "minuteInterval"
    ] = schedule_interval
    trigger_node["name"] = f"每{schedule_interval}分鐘觸發"
    trigger_node["position"] = [0, 0]
    nodes.append(trigger_node)

    # 生成訊號節點
    signal_node = copy.deepcopy(NODE_TEMPLATES["http_request"])
    signal_node["parameters"]["url"] = f"{api_url}/api/strategy/generate-signals"
    signal_node["parameters"]["method"] = "POST"
    signal_node["parameters"]["jsonParameters"] = True
    if strategy_id:
        signal_node["parameters"]["bodyParametersJson"] = {"strategy_id": strategy_id}
    signal_node["name"] = "生成交易訊號"
    signal_node["position"] = [220, 0]
    nodes.append(signal_node)

    # 檢查結果節點
    check_node = copy.deepcopy(NODE_TEMPLATES["if"])
    check_node["parameters"]["conditions"]["string"][0][
        "value1"
    ] = "={{ $json.success }}"
    check_node["parameters"]["conditions"]["string"][0]["operation"] = "equal"
    check_node["parameters"]["conditions"]["string"][0]["value2"] = "true"
    check_node["name"] = "檢查結果"
    check_node["position"] = [440, 0]
    nodes.append(check_node)

    # 執行交易節點
    execute_node = copy.deepcopy(NODE_TEMPLATES["http_request"])
    execute_node["parameters"]["url"] = f"{api_url}/api/trade/execute"
    execute_node["parameters"]["method"] = "POST"
    execute_node["parameters"]["jsonParameters"] = True
    execute_node["name"] = "執行交易"
    execute_node["position"] = [660, -100]
    nodes.append(execute_node)

    # 錯誤通知節點
    error_node = copy.deepcopy(NODE_TEMPLATES["slack"])
    error_node["parameters"]["text"] = "=交易訊號生成失敗: {{ $json.error }}"
    error_node["parameters"]["channel"] = "trading-alerts"
    error_node["name"] = "發送錯誤通知"
    error_node["position"] = [660, 100]
    nodes.append(error_node)

    # 設置連接
    connections = {
        f"每{schedule_interval}分鐘觸發": {
            "main": [[{"node": "生成交易訊號", "type": "main", "index": 0}]]
        },
        "生成交易訊號": {"main": [[{"node": "檢查結果", "type": "main", "index": 0}]]},
        "檢查結果": {
            "main": [
                [{"node": "執行交易", "type": "main", "index": 0}],
                [{"node": "發送錯誤通知", "type": "main", "index": 0}],
            ]
        },
    }

    # 更新工作流
    workflow["nodes"] = nodes
    workflow["connections"] = connections

    logger.info(f"已創建策略執行工作流: {name}")
    return workflow


def portfolio_rebalance_workflow(
    name: str = "投資組合再平衡工作流",
    schedule_interval: int = 1440,  # 默認每天執行一次
    api_url: str = "http://localhost:8000",
    portfolio_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    創建投資組合再平衡工作流

    Args:
        name: 工作流名稱
        schedule_interval: 排程間隔（分鐘）
        api_url: API URL
        portfolio_id: 投資組合ID

    Returns:
        Dict[str, Any]: 工作流定義
    """
    # 複製基本模板
    workflow = copy.deepcopy(BASE_WORKFLOW_TEMPLATE)
    workflow["name"] = name
    workflow["tags"] = ["投資組合", "再平衡", "自動化"]

    # 設置節點
    nodes = []

    # 觸發器節點
    trigger_node = copy.deepcopy(NODE_TEMPLATES["schedule_trigger"])
    trigger_node["parameters"]["rule"]["interval"][0][
        "minuteInterval"
    ] = schedule_interval
    trigger_node["name"] = f"每{schedule_interval}分鐘觸發"
    if schedule_interval == 1440:
        trigger_node["name"] = "每天觸發"
    trigger_node["position"] = [0, 0]
    nodes.append(trigger_node)

    # 分析投資組合節點
    analyze_node = copy.deepcopy(NODE_TEMPLATES["http_request"])
    analyze_node["parameters"]["url"] = f"{api_url}/api/portfolio/analyze"
    analyze_node["parameters"]["method"] = "POST"
    analyze_node["parameters"]["jsonParameters"] = True
    if portfolio_id:
        analyze_node["parameters"]["bodyParametersJson"] = {
            "portfolio_id": portfolio_id
        }
    analyze_node["name"] = "分析投資組合"
    analyze_node["position"] = [220, 0]
    nodes.append(analyze_node)

    # 檢查結果節點
    check_node = copy.deepcopy(NODE_TEMPLATES["if"])
    check_node["parameters"]["conditions"]["string"][0][
        "value1"
    ] = "={{ $json.rebalance_needed }}"
    check_node["parameters"]["conditions"]["string"][0]["operation"] = "equal"
    check_node["parameters"]["conditions"]["string"][0]["value2"] = "true"
    check_node["name"] = "檢查是否需要再平衡"
    check_node["position"] = [440, 0]
    nodes.append(check_node)

    # 執行再平衡節點
    rebalance_node = copy.deepcopy(NODE_TEMPLATES["http_request"])
    rebalance_node["parameters"]["url"] = f"{api_url}/api/portfolio/rebalance"
    rebalance_node["parameters"]["method"] = "POST"
    rebalance_node["parameters"]["jsonParameters"] = True
    rebalance_node["name"] = "執行再平衡"
    rebalance_node["position"] = [660, -100]
    nodes.append(rebalance_node)

    # 通知節點
    notify_node = copy.deepcopy(NODE_TEMPLATES["slack"])
    notify_node["parameters"]["text"] = "=投資組合再平衡完成: {{ $json.summary }}"
    notify_node["parameters"]["channel"] = "trading-alerts"
    notify_node["name"] = "發送再平衡通知"
    notify_node["position"] = [880, -100]
    nodes.append(notify_node)

    # 設置連接
    connections = {
        f"每{schedule_interval}分鐘觸發" if schedule_interval != 1440 else "每天觸發": {
            "main": [[{"node": "分析投資組合", "type": "main", "index": 0}]]
        },
        "分析投資組合": {
            "main": [[{"node": "檢查是否需要再平衡", "type": "main", "index": 0}]]
        },
        "檢查是否需要再平衡": {
            "main": [
                [{"node": "執行再平衡", "type": "main", "index": 0}],
                [],  # 不需要再平衡時不執行任何操作
            ]
        },
        "執行再平衡": {
            "main": [[{"node": "發送再平衡通知", "type": "main", "index": 0}]]
        },
    }

    # 更新工作流
    workflow["nodes"] = nodes
    workflow["connections"] = connections

    logger.info(f"已創建投資組合再平衡工作流: {name}")
    return workflow


def risk_monitoring_workflow(
    name: str = "風險監控工作流",
    schedule_interval: int = 60,  # 默認每小時執行一次
    api_url: str = "http://localhost:8000",
) -> Dict[str, Any]:
    """
    創建風險監控工作流

    Args:
        name: 工作流名稱
        schedule_interval: 排程間隔（分鐘）
        api_url: API URL

    Returns:
        Dict[str, Any]: 工作流定義
    """
    # 複製基本模板
    workflow = copy.deepcopy(BASE_WORKFLOW_TEMPLATE)
    workflow["name"] = name
    workflow["tags"] = ["風險管理", "監控", "自動化"]

    # 設置節點
    nodes = []

    # 觸發器節點
    trigger_node = copy.deepcopy(NODE_TEMPLATES["schedule_trigger"])
    trigger_node["parameters"]["rule"]["interval"][0][
        "minuteInterval"
    ] = schedule_interval
    trigger_node["name"] = f"每{schedule_interval}分鐘觸發"
    if schedule_interval == 60:
        trigger_node["name"] = "每小時觸發"
    trigger_node["position"] = [0, 0]
    nodes.append(trigger_node)

    # 檢查風險指標節點
    risk_node = copy.deepcopy(NODE_TEMPLATES["http_request"])
    risk_node["parameters"]["url"] = f"{api_url}/api/risk/check"
    risk_node["parameters"]["method"] = "POST"
    risk_node["parameters"]["jsonParameters"] = True
    risk_node["name"] = "檢查風險指標"
    risk_node["position"] = [220, 0]
    nodes.append(risk_node)

    # 檢查結果節點
    check_node = copy.deepcopy(NODE_TEMPLATES["if"])
    check_node["parameters"]["conditions"]["string"][0][
        "value1"
    ] = "={{ $json.risk_level }}"
    check_node["parameters"]["conditions"]["string"][0]["operation"] = "above"
    check_node["parameters"]["conditions"]["string"][0][
        "value2"
    ] = "3"  # 風險等級超過3時觸發警報
    check_node["name"] = "檢查風險等級"
    check_node["position"] = [440, 0]
    nodes.append(check_node)

    # 執行風險控制節點
    control_node = copy.deepcopy(NODE_TEMPLATES["http_request"])
    control_node["parameters"]["url"] = f"{api_url}/api/risk/control"
    control_node["parameters"]["method"] = "POST"
    control_node["parameters"]["jsonParameters"] = True
    control_node["name"] = "執行風險控制"
    control_node["position"] = [660, -100]
    nodes.append(control_node)

    # 發送警報節點
    alert_node = copy.deepcopy(NODE_TEMPLATES["slack"])
    alert_node["parameters"][
        "text"
    ] = "=⚠️ 風險警報: {{ $json.risk_description }}\n風險等級: {{ $json.risk_level }}/5\n受影響資產: {{ $json.affected_assets }}"
    alert_node["parameters"]["channel"] = "risk-alerts"
    alert_node["name"] = "發送風險警報"
    alert_node["position"] = [660, 100]
    nodes.append(alert_node)

    # 設置連接
    connections = {
        f"每{schedule_interval}分鐘觸發" if schedule_interval != 60 else "每小時觸發": {
            "main": [[{"node": "檢查風險指標", "type": "main", "index": 0}]]
        },
        "檢查風險指標": {
            "main": [[{"node": "檢查風險等級", "type": "main", "index": 0}]]
        },
        "檢查風險等級": {
            "main": [
                [{"node": "執行風險控制", "type": "main", "index": 0}],
                [],  # 風險等級正常時不執行任何操作
            ]
        },
        "執行風險控制": {
            "main": [[{"node": "發送風險警報", "type": "main", "index": 0}]]
        },
    }

    # 更新工作流
    workflow["nodes"] = nodes
    workflow["connections"] = connections

    logger.info(f"已創建風險監控工作流: {name}")
    return workflow


def reporting_workflow(
    name: str = "報告生成工作流",
    schedule_interval: int = 1440,  # 默認每天執行一次
    api_url: str = "http://localhost:8000",
    report_type: str = "daily",
) -> Dict[str, Any]:
    """
    創建報告生成工作流

    Args:
        name: 工作流名稱
        schedule_interval: 排程間隔（分鐘）
        api_url: API URL
        report_type: 報告類型 (daily, weekly, monthly)

    Returns:
        Dict[str, Any]: 工作流定義
    """
    # 複製基本模板
    workflow = copy.deepcopy(BASE_WORKFLOW_TEMPLATE)
    workflow["name"] = name
    workflow["tags"] = ["報告", "自動化"]

    # 設置節點
    nodes = []

    # 觸發器節點
    trigger_node = copy.deepcopy(NODE_TEMPLATES["schedule_trigger"])
    trigger_node["parameters"]["rule"]["interval"][0][
        "minuteInterval"
    ] = schedule_interval
    trigger_node["name"] = f"每{schedule_interval}分鐘觸發"
    if schedule_interval == 1440:
        trigger_node["name"] = "每天觸發"
    elif schedule_interval == 10080:  # 每週
        trigger_node["name"] = "每週觸發"
    elif schedule_interval == 43200:  # 每月
        trigger_node["name"] = "每月觸發"
    trigger_node["position"] = [0, 0]
    nodes.append(trigger_node)

    # 生成報告節點
    report_node = copy.deepcopy(NODE_TEMPLATES["http_request"])
    report_node["parameters"]["url"] = f"{api_url}/api/report/generate"
    report_node["parameters"]["method"] = "POST"
    report_node["parameters"]["jsonParameters"] = True
    report_node["parameters"]["bodyParametersJson"] = {"report_type": report_type}
    report_node["name"] = "生成報告"
    report_node["position"] = [220, 0]
    nodes.append(report_node)

    # 檢查結果節點
    check_node = copy.deepcopy(NODE_TEMPLATES["if"])
    check_node["parameters"]["conditions"]["string"][0][
        "value1"
    ] = "={{ $json.success }}"
    check_node["parameters"]["conditions"]["string"][0]["operation"] = "equal"
    check_node["parameters"]["conditions"]["string"][0]["value2"] = "true"
    check_node["name"] = "檢查結果"
    check_node["position"] = [440, 0]
    nodes.append(check_node)

    # 發送報告節點
    email_node = copy.deepcopy(NODE_TEMPLATES["email"])
    email_node["parameters"]["fromEmail"] = "trading-system@example.com"
    email_node["parameters"]["toEmail"] = "user@example.com"
    email_node["parameters"][
        "subject"
    ] = f"=交易系統{report_type}報告 - {{ $json.report_date }}"
    email_node["parameters"][
        "text"
    ] = "=請查看附件中的交易報告。\n\n摘要：\n{{ $json.summary }}"
    email_node["parameters"]["options"] = {"attachments": "={{ $json.report_url }}"}
    email_node["name"] = "發送報告郵件"
    email_node["position"] = [660, -100]
    nodes.append(email_node)

    # 錯誤通知節點
    error_node = copy.deepcopy(NODE_TEMPLATES["slack"])
    error_node["parameters"]["text"] = "=報告生成失敗: {{ $json.error }}"
    error_node["parameters"]["channel"] = "trading-alerts"
    error_node["name"] = "發送錯誤通知"
    error_node["position"] = [660, 100]
    nodes.append(error_node)

    # 設置連接
    connections = {
        (
            f"每{schedule_interval}分鐘觸發"
            if schedule_interval not in [1440, 10080, 43200]
            else (
                "每天觸發"
                if schedule_interval == 1440
                else "每週觸發" if schedule_interval == 10080 else "每月觸發"
            )
        ): {"main": [[{"node": "生成報告", "type": "main", "index": 0}]]},
        "生成報告": {"main": [[{"node": "檢查結果", "type": "main", "index": 0}]]},
        "檢查結果": {
            "main": [
                [{"node": "發送報告郵件", "type": "main", "index": 0}],
                [{"node": "發送錯誤通知", "type": "main", "index": 0}],
            ]
        },
    }

    # 更新工作流
    workflow["nodes"] = nodes
    workflow["connections"] = connections

    logger.info(f"已創建報告生成工作流: {name}")
    return workflow
