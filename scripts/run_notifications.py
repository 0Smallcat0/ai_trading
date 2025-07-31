#!/usr/bin/env python3
"""
通知系統執行腳本

此腳本執行各種通知功能，包括：
- 品質警報檢查和發送
- 每日/週報生成和發送
- PR 品質評論
- 定時任務管理

Example:
    >>> python scripts/run_notifications.py --check-alerts
    >>> python scripts/run_notifications.py --daily-report
    >>> python scripts/run_notifications.py --pr-comment 123
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from notification_system import NotificationSystem


def load_latest_quality_data() -> Dict[str, Any]:
    """載入最新的品質數據.
    
    Returns:
        Dict[str, Any]: 品質數據
    """
    reports_dir = Path("docs/reports")
    
    # 尋找最新的品質數據檔案
    data_files = list(reports_dir.glob("quality-data-*.json"))
    if not data_files:
        print("❌ 找不到品質數據檔案")
        return {}
    
    # 按修改時間排序，取最新的
    latest_file = max(data_files, key=lambda f: f.stat().st_mtime)
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 載入品質數據失敗: {e}")
        return {}


def load_historical_quality_data() -> List[Dict[str, Any]]:
    """載入歷史品質數據.
    
    Returns:
        List[Dict[str, Any]]: 歷史品質數據列表
    """
    reports_dir = Path("docs/reports")
    historical_data = []
    
    for data_file in reports_dir.glob("quality-data-*.json"):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                historical_data.append(data)
        except Exception as e:
            print(f"⚠️ 載入歷史數據失敗 {data_file}: {e}")
    
    # 按時間排序
    historical_data.sort(key=lambda x: x.get('timestamp', ''))
    return historical_data


def check_and_send_alerts(notifier: NotificationSystem) -> bool:
    """檢查並發送品質警報.
    
    Args:
        notifier: 通知系統實例
        
    Returns:
        bool: 是否成功
    """
    print("🔍 檢查品質警報...")
    
    quality_data = load_latest_quality_data()
    if not quality_data:
        return False
    
    return notifier.send_quality_alerts(quality_data)


def send_daily_report(notifier: NotificationSystem) -> bool:
    """發送每日報告.
    
    Args:
        notifier: 通知系統實例
        
    Returns:
        bool: 是否成功
    """
    print("📊 生成並發送每日報告...")
    
    quality_data = load_latest_quality_data()
    if not quality_data:
        return False
    
    return notifier.send_daily_report(quality_data)


def send_weekly_report(notifier: NotificationSystem) -> bool:
    """發送週報.
    
    Args:
        notifier: 通知系統實例
        
    Returns:
        bool: 是否成功
    """
    print("📈 生成並發送週報...")
    
    historical_data = load_historical_quality_data()
    if len(historical_data) < 2:
        print("⚠️ 歷史數據不足，無法生成週報")
        return False
    
    return notifier.send_weekly_report(historical_data)


def send_pr_comment(notifier: NotificationSystem, pr_number: int) -> bool:
    """發送 PR 品質評論.
    
    Args:
        notifier: 通知系統實例
        pr_number: PR 編號
        
    Returns:
        bool: 是否成功
    """
    print(f"💬 為 PR #{pr_number} 生成品質評論...")
    
    quality_data = load_latest_quality_data()
    if not quality_data:
        return False
    
    return notifier.send_pr_quality_comment(quality_data, pr_number)


def test_notifications(notifier: NotificationSystem) -> bool:
    """測試通知功能.
    
    Args:
        notifier: 通知系統實例
        
    Returns:
        bool: 是否成功
    """
    print("🧪 測試通知功能...")
    
    test_message = f"通知系統測試 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    success = True
    
    # 測試 Slack
    if not notifier.send_slack_notification(test_message, 'info'):
        success = False
    
    # 測試 Teams
    if not notifier.send_teams_notification(test_message, 'info'):
        success = False
    
    return success


def setup_scheduled_tasks() -> None:
    """設置定時任務.
    
    Note:
        此功能需要配合 cron 或 GitHub Actions 定時任務使用
    """
    print("⏰ 設置定時任務...")
    
    # 生成 cron 配置建議
    cron_config = """
# 每日品質報告 (每天上午 9:00)
0 9 * * * cd /path/to/project && python scripts/run_notifications.py --daily-report

# 週報 (每週一上午 9:00)
0 9 * * 1 cd /path/to/project && python scripts/run_notifications.py --weekly-report

# 品質警報檢查 (每 4 小時)
0 */4 * * * cd /path/to/project && python scripts/run_notifications.py --check-alerts
"""
    
    print("建議的 cron 配置:")
    print(cron_config)
    
    # 生成 GitHub Actions 配置
    github_actions_config = """
name: Quality Notifications

on:
  schedule:
    # 每日報告 (UTC 01:00 = 台北時間 09:00)
    - cron: '0 1 * * *'
    # 週報 (每週一 UTC 01:00)
    - cron: '0 1 * * 1'
  workflow_run:
    workflows: ["Code Quality Check"]
    types: [completed]

jobs:
  notifications:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        pip install requests
    - name: Send notifications
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        TEAMS_WEBHOOK_URL: ${{ secrets.TEAMS_WEBHOOK_URL }}
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      run: |
        if [ "${{ github.event_name }}" = "schedule" ]; then
          if [ "$(date +%u)" = "1" ]; then
            python scripts/run_notifications.py --weekly-report
          else
            python scripts/run_notifications.py --daily-report
          fi
        else
          python scripts/run_notifications.py --check-alerts
        fi
"""
    
    # 保存 GitHub Actions 配置
    actions_dir = Path(".github/workflows")
    actions_dir.mkdir(parents=True, exist_ok=True)
    
    with open(actions_dir / "quality-notifications.yml", 'w', encoding='utf-8') as f:
        f.write(github_actions_config)
    
    print("✅ GitHub Actions 配置已生成: .github/workflows/quality-notifications.yml")


def main():
    """主函數."""
    parser = argparse.ArgumentParser(description="通知系統執行腳本")
    parser.add_argument(
        "--config", 
        default="config/notification_config.json",
        help="配置檔案路徑"
    )
    parser.add_argument(
        "--check-alerts", 
        action="store_true",
        help="檢查並發送品質警報"
    )
    parser.add_argument(
        "--daily-report", 
        action="store_true",
        help="發送每日報告"
    )
    parser.add_argument(
        "--weekly-report", 
        action="store_true",
        help="發送週報"
    )
    parser.add_argument(
        "--pr-comment", 
        type=int,
        help="為指定 PR 發送品質評論"
    )
    parser.add_argument(
        "--test", 
        action="store_true",
        help="測試通知功能"
    )
    parser.add_argument(
        "--setup-schedule", 
        action="store_true",
        help="設置定時任務"
    )
    
    args = parser.parse_args()
    
    # 如果沒有指定任何操作，顯示幫助
    if not any([args.check_alerts, args.daily_report, args.weekly_report, 
                args.pr_comment, args.test, args.setup_schedule]):
        parser.print_help()
        return 1
    
    # 初始化通知系統
    try:
        notifier = NotificationSystem(args.config)
    except Exception as e:
        print(f"❌ 初始化通知系統失敗: {e}")
        return 1
    
    success = True
    
    # 執行指定的操作
    if args.setup_schedule:
        setup_scheduled_tasks()
    
    if args.test:
        if not test_notifications(notifier):
            success = False
    
    if args.check_alerts:
        if not check_and_send_alerts(notifier):
            success = False
    
    if args.daily_report:
        if not send_daily_report(notifier):
            success = False
    
    if args.weekly_report:
        if not send_weekly_report(notifier):
            success = False
    
    if args.pr_comment:
        if not send_pr_comment(notifier, args.pr_comment):
            success = False
    
    if success:
        print("✅ 所有通知操作都成功完成")
        return 0
    else:
        print("❌ 部分通知操作失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
