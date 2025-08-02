"""
日誌系統功能演示

此腳本演示了 Phase 5.4 實現的日誌系統功能，包括：
- 合規性日誌記錄
- 敏感資料遮罩
- 日誌分析和異常檢測
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logging.compliance import (
    ComplianceLogger,
    ComplianceEventType,
    ComplianceLevel,
)
from src.logging.data_masking import DataMasker, SensitiveDataType, MaskingStrategy
from src.logging.analyzer import LogAnalyzer


def demo_compliance_logging():
    """演示合規性日誌記錄"""
    print("=== 合規性日誌記錄演示 ===")

    # 創建臨時目錄
    temp_dir = tempfile.mkdtemp()
    log_dir = os.path.join(temp_dir, "compliance")
    key_dir = os.path.join(temp_dir, "keys")

    # 初始化合規日誌記錄器
    compliance_logger = ComplianceLogger(
        log_dir=log_dir, key_dir=key_dir, enable_encryption=True
    )

    print(f"日誌目錄: {log_dir}")
    print(f"密鑰目錄: {key_dir}")

    # 記錄不同類型的合規事件
    events = [
        {
            "type": ComplianceEventType.TRADING_DECISION,
            "level": ComplianceLevel.HIGH,
            "description": "執行大額股票交易決策",
            "details": {
                "symbol": "AAPL",
                "quantity": 1000,
                "price": 150.25,
                "total_value": 150250.00,
            },
            "business_context": {
                "strategy": "momentum_trading",
                "risk_score": 7.5,
                "portfolio_id": "P001",
            },
            "regulatory_context": {
                "regulation": "MiFID II",
                "compliance_check": "passed",
                "approval_required": True,
            },
        },
        {
            "type": ComplianceEventType.RISK_ASSESSMENT,
            "level": ComplianceLevel.MEDIUM,
            "description": "投資組合風險評估",
            "details": {
                "portfolio_value": 1000000.00,
                "var_95": 25000.00,
                "sharpe_ratio": 1.25,
            },
            "business_context": {
                "assessment_type": "daily",
                "risk_model": "monte_carlo",
            },
            "regulatory_context": {
                "regulation": "Basel III",
                "risk_limit_check": "within_limits",
            },
        },
        {
            "type": ComplianceEventType.DATA_EXPORT,
            "level": ComplianceLevel.CRITICAL,
            "description": "客戶資料匯出請求",
            "details": {
                "export_type": "customer_data",
                "record_count": 1500,
                "file_format": "CSV",
            },
            "business_context": {
                "requester": "compliance_team",
                "purpose": "regulatory_audit",
            },
            "regulatory_context": {
                "regulation": "GDPR",
                "data_protection_approval": "required",
                "retention_period": "7_years",
            },
        },
    ]

    # 記錄事件
    logged_events = []
    for event_data in events:
        event = compliance_logger.log_event(
            event_type=event_data["type"],
            level=event_data["level"],
            user_id="demo_user",
            description=event_data["description"],
            details=event_data["details"],
            business_context=event_data["business_context"],
            regulatory_context=event_data["regulatory_context"],
        )
        logged_events.append(event)
        print(f"✓ 記錄事件: {event.event_id} - {event.description}")

    # 驗證事件完整性
    print("\n--- 事件完整性驗證 ---")
    for event in logged_events:
        event_data = event.to_dict()
        is_valid = compliance_logger.verify_event(event_data)
        status = "✓ 有效" if is_valid else "✗ 無效"
        print(f"{status}: {event.event_id}")

    # 生成合規報告
    print("\n--- 生成合規報告 ---")
    start_date = datetime.now() - timedelta(hours=1)
    end_date = datetime.now() + timedelta(hours=1)

    report = compliance_logger.generate_compliance_report(
        start_date=start_date, end_date=end_date
    )

    print(f"報告ID: {report['report_id']}")
    print(f"總事件數: {report['total_events']}")
    print(f"完整性評分: {report['integrity_check']['integrity_score']:.2%}")
    print(f"按類型統計: {report['summary']['by_type']}")
    print(f"按級別統計: {report['summary']['by_level']}")

    # 清理
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)

    return report


def demo_data_masking():
    """演示敏感資料遮罩"""
    print("\n=== 敏感資料遮罩演示 ===")

    # 初始化資料遮罩器
    masker = DataMasker()

    # 測試資料
    sensitive_data = {
        "user_info": {
            "name": "張三",
            "email": "zhang.san@example.com",
            "phone": "0912-345-678",
            "id_number": "A123456789",
        },
        "credentials": {
            "password": "mySecretPassword123",
            "api_key": "sk-1234567890abcdef1234567890abcdef",
            "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        },
        "financial_info": {
            "credit_card": "4532-1234-5678-9012",
            "bank_account": "123-456-789",
            "balance": 50000.00,
        },
        "system_logs": [
            "用戶登入成功，IP: 192.168.1.100",
            "API 呼叫: GET /api/users/zhang.san@example.com",
            "密碼變更請求，用戶: A123456789",
        ],
    }

    print("原始資料:")
    print_data(sensitive_data, indent=2)

    # 應用遮罩
    masked_data = masker.mask_data(sensitive_data)

    print("\n遮罩後資料:")
    print_data(masked_data, indent=2)

    # 測試不同的遮罩策略
    print("\n--- 測試不同遮罩策略 ---")
    test_text = "API金鑰: sk-abcdef123456, 密碼: secret123"

    strategies = [("原始", test_text), ("預設遮罩", masker.mask_data(test_text))]

    # 添加自定義規則測試不同策略
    masker.add_custom_rule(
        name="雜湊測試",
        data_type=SensitiveDataType.CUSTOM,
        pattern=r"secret\d+",
        strategy=MaskingStrategy.HASH,
        field_names=[],
    )

    strategies.append(("雜湊遮罩", masker.mask_data(test_text)))

    masker.remove_rule("雜湊測試")
    masker.add_custom_rule(
        name="標記化測試",
        data_type=SensitiveDataType.CUSTOM,
        pattern=r"secret\d+",
        strategy=MaskingStrategy.TOKENIZE,
        field_names=[],
    )

    strategies.append(("標記化", masker.mask_data(test_text)))

    for name, result in strategies:
        print(f"{name}: {result}")

    # 顯示統計信息
    print("\n--- 遮罩規則統計 ---")
    stats = masker.get_statistics()
    print(f"總規則數: {stats['total_rules']}")
    print(f"啟用規則數: {stats['enabled_rules']}")
    print(f"按類型統計: {stats['by_type']}")
    print(f"按策略統計: {stats['by_strategy']}")

    return masked_data


def demo_log_analysis():
    """演示日誌分析"""
    print("\n=== 日誌分析演示 ===")

    # 初始化日誌分析器
    analyzer = LogAnalyzer()

    # 模擬一些日誌數據
    import pandas as pd
    import json

    # 創建模擬日誌數據
    log_data = []
    base_time = datetime.now() - timedelta(hours=2)

    for i in range(100):
        timestamp = base_time + timedelta(minutes=i)

        # 模擬不同類型的日誌
        if i % 20 == 0:
            level = "ERROR"
            message = f"資料庫連接失敗: Connection timeout after 30s"
        elif i % 10 == 0:
            level = "WARNING"
            message = f"API 請求處理時間過長: {5 + (i % 5)}s"
        else:
            level = "INFO"
            message = f"API 請求處理完成: GET /api/data/{i}"

        log_entry = {
            "timestamp": timestamp.isoformat(),
            "level": level,
            "message": message,
            "category": "api",
            "data": {
                "execution_time": 0.5 + (i % 10) * 0.5,
                "operation": f"api_call_{i}",
                "user_id": f"user_{i % 5}",
            },
        }
        log_data.append(log_entry)

    # 轉換為 DataFrame
    df = pd.DataFrame(log_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # 模擬 load_logs 方法
    original_load_logs = analyzer.load_logs
    analyzer.load_logs = lambda *args, **kwargs: df

    try:
        # 執行異常檢測
        print("--- 異常檢測 ---")
        anomalies = analyzer.detect_anomalies()

        print(f"錯誤激增: {len(anomalies['error_spikes'])} 個")
        print(f"異常模式: {len(anomalies['unusual_patterns'])} 個")
        print(f"效能問題: {len(anomalies['performance_issues'])} 個")
        print(f"安全問題: {len(anomalies['security_concerns'])} 個")

        # 生成分析報告
        print("\n--- 分析報告 ---")
        report = analyzer.generate_analysis_report()

        print(f"報告ID: {report['report_id']}")
        print(f"總日誌數: {report['total_logs']}")
        print(f"錯誤日誌數: {report['summary']['error_logs']}")
        print(f"警告日誌數: {report['summary']['warning_logs']}")
        print(f"建議數量: {len(report['recommendations'])}")

        if report["recommendations"]:
            print("\n建議:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"  {i}. [{rec['priority']}] {rec['description']}")
                print(f"     行動: {rec['action']}")

    finally:
        # 恢復原始方法
        analyzer.load_logs = original_load_logs

    return report


def print_data(data, indent=0):
    """格式化打印資料"""
    spaces = " " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{spaces}{key}:")
                print_data(value, indent + 2)
            else:
                print(f"{spaces}{key}: {value}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                print(f"{spaces}[{i}]:")
                print_data(item, indent + 2)
            else:
                print(f"{spaces}[{i}]: {item}")
    else:
        print(f"{spaces}{data}")


def main():
    """主函數"""
    print("Phase 5.4 日誌系統與審計追蹤功能演示")
    print("=" * 50)

    try:
        # 演示合規性日誌記錄
        compliance_report = demo_compliance_logging()

        # 演示敏感資料遮罩
        masked_data = demo_data_masking()

        # 演示日誌分析
        analysis_report = demo_log_analysis()

        print("\n" + "=" * 50)
        print("✓ 所有功能演示完成！")
        print("\n功能摘要:")
        print("- 合規性日誌記錄: 支援加密簽名和完整性驗證")
        print("- 敏感資料遮罩: 多種遮罩策略和自定義規則")
        print("- 日誌分析: 異常檢測和智能建議")

    except Exception as e:
        print(f"\n❌ 演示過程中發生錯誤: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
