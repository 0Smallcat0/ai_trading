#!/usr/bin/env python3
"""
品質通知系統

此系統實現了自動化的程式碼品質通知功能，包括：
- Slack/Teams 整合
- 品質閾值警報
- 每日/週報自動發送
- PR 品質評分自動評論

Example:
    >>> from scripts.notification_system import NotificationSystem
    >>> notifier = NotificationSystem()
    >>> notifier.send_quality_alert("Pylint score dropped below 8.0")
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests


class NotificationSystem:
    """品質通知系統.
    
    提供多種通知渠道的品質問題警報和報告功能。
    """

    def __init__(self, config_path: Optional[str] = None):
        """初始化通知系統.
        
        Args:
            config_path: 配置檔案路徑
        """
        self.config = self._load_config(config_path)
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL') or self.config.get('slack', {}).get('webhook_url')
        self.teams_webhook = os.getenv('TEAMS_WEBHOOK_URL') or self.config.get('teams', {}).get('webhook_url')
        self.github_token = os.getenv('GITHUB_TOKEN') or self.config.get('github', {}).get('token')
        
        # 品質閾值
        self.quality_thresholds = self.config.get('thresholds', {
            'pylint_critical': 7.0,
            'pylint_warning': 8.0,
            'coverage_critical': 70.0,
            'coverage_warning': 75.0,
            'complexity_critical': 20.0,
            'complexity_warning': 15.0,
            'maintainability_critical': 10.0,
            'maintainability_warning': 20.0
        })

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """載入配置.
        
        Args:
            config_path: 配置檔案路徑
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 載入配置失敗: {e}")
        
        # 預設配置
        return {
            'slack': {
                'enabled': True,
                'channel': '#code-quality',
                'username': 'Quality Bot'
            },
            'teams': {
                'enabled': True
            },
            'github': {
                'enabled': True,
                'repo': 'Cookieeeeeeeeeeeeeee/ai_trading'
            },
            'schedule': {
                'daily_report': '09:00',
                'weekly_report': 'monday:09:00'
            }
        }

    def send_slack_notification(self, message: str, severity: str = 'info') -> bool:
        """發送 Slack 通知.
        
        Args:
            message: 通知訊息
            severity: 嚴重程度 (info, warning, error, critical)
            
        Returns:
            bool: 是否發送成功
        """
        if not self.slack_webhook or not self.config.get('slack', {}).get('enabled', True):
            print("⚠️ Slack 通知未配置或已禁用")
            return False

        # 根據嚴重程度設定顏色和圖示
        color_map = {
            'info': '#36a64f',      # 綠色
            'warning': '#ff9500',   # 橙色
            'error': '#ff0000',     # 紅色
            'critical': '#8b0000'   # 深紅色
        }
        
        emoji_map = {
            'info': ':white_check_mark:',
            'warning': ':warning:',
            'error': ':x:',
            'critical': ':rotating_light:'
        }

        payload = {
            'channel': self.config.get('slack', {}).get('channel', '#code-quality'),
            'username': self.config.get('slack', {}).get('username', 'Quality Bot'),
            'attachments': [{
                'color': color_map.get(severity, '#36a64f'),
                'fields': [{
                    'title': f"{emoji_map.get(severity, ':information_source:')} 程式碼品質通知",
                    'value': message,
                    'short': False
                }],
                'footer': 'AI Trading Quality System',
                'ts': int(datetime.now().timestamp())
            }]
        }

        try:
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            print(f"✅ Slack 通知已發送: {severity}")
            return True
        except Exception as e:
            print(f"❌ Slack 通知發送失敗: {e}")
            return False

    def send_teams_notification(self, message: str, severity: str = 'info') -> bool:
        """發送 Teams 通知.
        
        Args:
            message: 通知訊息
            severity: 嚴重程度
            
        Returns:
            bool: 是否發送成功
        """
        if not self.teams_webhook or not self.config.get('teams', {}).get('enabled', True):
            print("⚠️ Teams 通知未配置或已禁用")
            return False

        # Teams 卡片格式
        color_map = {
            'info': 'Good',
            'warning': 'Warning', 
            'error': 'Attention',
            'critical': 'Attention'
        }

        payload = {
            '@type': 'MessageCard',
            '@context': 'http://schema.org/extensions',
            'themeColor': '0076D7' if severity == 'info' else 'FF9500' if severity == 'warning' else 'FF0000',
            'summary': '程式碼品質通知',
            'sections': [{
                'activityTitle': '程式碼品質通知',
                'activitySubtitle': f'嚴重程度: {severity.upper()}',
                'activityImage': 'https://github.com/fluidicon.png',
                'facts': [{
                    'name': '訊息',
                    'value': message
                }, {
                    'name': '時間',
                    'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }],
                'markdown': True
            }]
        }

        try:
            response = requests.post(self.teams_webhook, json=payload, timeout=10)
            response.raise_for_status()
            print(f"✅ Teams 通知已發送: {severity}")
            return True
        except Exception as e:
            print(f"❌ Teams 通知發送失敗: {e}")
            return False

    def send_github_comment(self, pr_number: int, comment: str) -> bool:
        """在 GitHub PR 中發送評論.
        
        Args:
            pr_number: PR 編號
            comment: 評論內容
            
        Returns:
            bool: 是否發送成功
        """
        if not self.github_token:
            print("⚠️ GitHub token 未配置")
            return False

        repo = self.config.get('github', {}).get('repo', 'Cookieeeeeeeeeeeeeee/ai_trading')
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        payload = {'body': comment}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            print(f"✅ GitHub PR 評論已發送: #{pr_number}")
            return True
        except Exception as e:
            print(f"❌ GitHub PR 評論發送失敗: {e}")
            return False

    def check_quality_thresholds(self, quality_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """檢查品質閾值.
        
        Args:
            quality_data: 品質數據
            
        Returns:
            List[Dict[str, Any]]: 警報列表
        """
        alerts = []

        # 檢查 Pylint 評分
        pylint_scores = quality_data.get('pylint_scores', {})
        if pylint_scores:
            avg_pylint = sum(pylint_scores.values()) / len(pylint_scores)
            
            if avg_pylint < self.quality_thresholds['pylint_critical']:
                alerts.append({
                    'type': 'pylint',
                    'severity': 'critical',
                    'message': f'Pylint 平均評分 ({avg_pylint:.1f}) 低於臨界值 ({self.quality_thresholds["pylint_critical"]})',
                    'value': avg_pylint,
                    'threshold': self.quality_thresholds['pylint_critical']
                })
            elif avg_pylint < self.quality_thresholds['pylint_warning']:
                alerts.append({
                    'type': 'pylint',
                    'severity': 'warning',
                    'message': f'Pylint 平均評分 ({avg_pylint:.1f}) 低於警告值 ({self.quality_thresholds["pylint_warning"]})',
                    'value': avg_pylint,
                    'threshold': self.quality_thresholds['pylint_warning']
                })

        # 檢查測試覆蓋率
        coverage_data = quality_data.get('test_coverage', {})
        if 'coverage_percentage' in coverage_data:
            coverage = coverage_data['coverage_percentage']
            
            if coverage < self.quality_thresholds['coverage_critical']:
                alerts.append({
                    'type': 'coverage',
                    'severity': 'critical',
                    'message': f'測試覆蓋率 ({coverage:.1f}%) 低於臨界值 ({self.quality_thresholds["coverage_critical"]}%)',
                    'value': coverage,
                    'threshold': self.quality_thresholds['coverage_critical']
                })
            elif coverage < self.quality_thresholds['coverage_warning']:
                alerts.append({
                    'type': 'coverage',
                    'severity': 'warning',
                    'message': f'測試覆蓋率 ({coverage:.1f}%) 低於警告值 ({self.quality_thresholds["coverage_warning"]}%)',
                    'value': coverage,
                    'threshold': self.quality_thresholds['coverage_warning']
                })

        # 檢查複雜度
        complexity_data = quality_data.get('code_metrics', {}).get('complexity', {})
        if 'average_complexity' in complexity_data:
            avg_complexity = complexity_data['average_complexity']
            
            if avg_complexity > self.quality_thresholds['complexity_critical']:
                alerts.append({
                    'type': 'complexity',
                    'severity': 'critical',
                    'message': f'平均複雜度 ({avg_complexity:.1f}) 超過臨界值 ({self.quality_thresholds["complexity_critical"]})',
                    'value': avg_complexity,
                    'threshold': self.quality_thresholds['complexity_critical']
                })
            elif avg_complexity > self.quality_thresholds['complexity_warning']:
                alerts.append({
                    'type': 'complexity',
                    'severity': 'warning',
                    'message': f'平均複雜度 ({avg_complexity:.1f}) 超過警告值 ({self.quality_thresholds["complexity_warning"]})',
                    'value': avg_complexity,
                    'threshold': self.quality_thresholds['complexity_warning']
                })

        # 檢查可維護性
        maintainability_data = quality_data.get('code_metrics', {}).get('maintainability', {})
        if 'average_mi' in maintainability_data:
            avg_mi = maintainability_data['average_mi']
            
            if avg_mi < self.quality_thresholds['maintainability_critical']:
                alerts.append({
                    'type': 'maintainability',
                    'severity': 'critical',
                    'message': f'可維護性指標 ({avg_mi:.1f}) 低於臨界值 ({self.quality_thresholds["maintainability_critical"]})',
                    'value': avg_mi,
                    'threshold': self.quality_thresholds['maintainability_critical']
                })
            elif avg_mi < self.quality_thresholds['maintainability_warning']:
                alerts.append({
                    'type': 'maintainability',
                    'severity': 'warning',
                    'message': f'可維護性指標 ({avg_mi:.1f}) 低於警告值 ({self.quality_thresholds["maintainability_warning"]})',
                    'value': avg_mi,
                    'threshold': self.quality_thresholds['maintainability_warning']
                })

        return alerts

    def send_quality_alerts(self, quality_data: Dict[str, Any]) -> bool:
        """發送品質警報.
        
        Args:
            quality_data: 品質數據
            
        Returns:
            bool: 是否發送成功
        """
        alerts = self.check_quality_thresholds(quality_data)
        
        if not alerts:
            print("✅ 所有品質指標都在正常範圍內")
            return True

        success = True
        
        for alert in alerts:
            message = f"🚨 **品質警報**\n\n{alert['message']}\n\n請及時處理以維持程式碼品質。"
            
            # 發送到 Slack
            if not self.send_slack_notification(message, alert['severity']):
                success = False
            
            # 發送到 Teams
            if not self.send_teams_notification(message, alert['severity']):
                success = False

        return success

    def generate_daily_report(self, quality_data: Dict[str, Any]) -> str:
        """生成每日品質報告.

        Args:
            quality_data: 品質數據

        Returns:
            str: 報告內容
        """
        report_date = datetime.now().strftime('%Y-%m-%d')

        # 基本統計
        pylint_scores = quality_data.get('pylint_scores', {})
        avg_pylint = sum(pylint_scores.values()) / len(pylint_scores) if pylint_scores else 0

        complexity_data = quality_data.get('code_metrics', {}).get('complexity', {})
        avg_complexity = complexity_data.get('average_complexity', 0)

        maintainability_data = quality_data.get('code_metrics', {}).get('maintainability', {})
        avg_mi = maintainability_data.get('average_mi', 0)

        file_sizes = quality_data.get('file_sizes', {})
        violations = len(file_sizes.get('violations', []))

        # 生成報告
        report = f"""
📊 **每日程式碼品質報告** - {report_date}

## 📈 關鍵指標
• **Pylint 評分**: {avg_pylint:.1f}/10 {'✅' if avg_pylint >= 8.5 else '⚠️' if avg_pylint >= 8.0 else '❌'}
• **平均複雜度**: {avg_complexity:.1f} {'✅' if avg_complexity <= 10 else '⚠️' if avg_complexity <= 15 else '❌'}
• **可維護性指標**: {avg_mi:.1f} {'✅' if avg_mi >= 20 else '⚠️' if avg_mi >= 10 else '❌'}
• **檔案大小違規**: {violations} 個 {'✅' if violations == 0 else '⚠️'}

## 🎯 品質狀態
"""

        # 檢查警報
        alerts = self.check_quality_thresholds(quality_data)
        if alerts:
            critical_alerts = [a for a in alerts if a['severity'] == 'critical']
            warning_alerts = [a for a in alerts if a['severity'] == 'warning']

            if critical_alerts:
                report += f"🚨 **緊急問題**: {len(critical_alerts)} 個\n"
                for alert in critical_alerts[:3]:  # 只顯示前3個
                    report += f"  • {alert['message']}\n"

            if warning_alerts:
                report += f"⚠️ **警告問題**: {len(warning_alerts)} 個\n"
                for alert in warning_alerts[:3]:  # 只顯示前3個
                    report += f"  • {alert['message']}\n"
        else:
            report += "✅ **狀態良好**: 所有指標都在正常範圍內\n"

        # 改進建議
        recommendations = quality_data.get('recommendations', [])
        if recommendations:
            high_priority = [r for r in recommendations if r['priority'] == 'high']
            if high_priority:
                report += f"\n## 💡 優先改進建議\n"
                for rec in high_priority[:3]:  # 只顯示前3個
                    report += f"• {rec['issue']} - {rec['action']}\n"

        report += f"\n📋 完整報告: [查看詳細報告](docs/reports/quality-report-latest.html)"

        return report

    def generate_weekly_report(self, historical_data: List[Dict[str, Any]]) -> str:
        """生成週報.

        Args:
            historical_data: 歷史品質數據

        Returns:
            str: 週報內容
        """
        week_start = datetime.now() - timedelta(days=7)
        week_end = datetime.now()

        # 過濾本週數據
        week_data = []
        for data in historical_data:
            if 'timestamp' in data:
                data_time = datetime.fromisoformat(data['timestamp'])
                if week_start <= data_time <= week_end:
                    week_data.append(data)

        if len(week_data) < 2:
            return "⚠️ 本週數據不足，無法生成週報"

        # 計算趨勢
        first_data = week_data[0]
        last_data = week_data[-1]

        def get_avg_pylint(data):
            scores = data.get('pylint_scores', {})
            return sum(scores.values()) / len(scores) if scores else 0

        def get_avg_complexity(data):
            return data.get('code_metrics', {}).get('complexity', {}).get('average_complexity', 0)

        def get_avg_mi(data):
            return data.get('code_metrics', {}).get('maintainability', {}).get('average_mi', 0)

        pylint_trend = get_avg_pylint(last_data) - get_avg_pylint(first_data)
        complexity_trend = get_avg_complexity(last_data) - get_avg_complexity(first_data)
        mi_trend = get_avg_mi(last_data) - get_avg_mi(first_data)

        def trend_emoji(value, reverse=False):
            if reverse:  # 對於複雜度，下降是好的
                return '📈' if value < -0.1 else '📉' if value > 0.1 else '➡️'
            else:  # 對於 Pylint 和 MI，上升是好的
                return '📈' if value > 0.1 else '📉' if value < -0.1 else '➡️'

        report = f"""
📊 **週度程式碼品質報告** - {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')}

## 📈 本週趨勢
• **Pylint 評分**: {trend_emoji(pylint_trend)} {pylint_trend:+.1f} (當前: {get_avg_pylint(last_data):.1f})
• **平均複雜度**: {trend_emoji(complexity_trend, True)} {complexity_trend:+.1f} (當前: {get_avg_complexity(last_data):.1f})
• **可維護性指標**: {trend_emoji(mi_trend)} {mi_trend:+.1f} (當前: {get_avg_mi(last_data):.1f})

## 📊 本週統計
• **品質檢查次數**: {len(week_data)}
• **數據收集天數**: {(week_end - week_start).days}
"""

        # 本週改進
        if pylint_trend > 0.1 or mi_trend > 0.1 or complexity_trend < -0.1:
            report += "\n## 🎉 本週改進\n"
            if pylint_trend > 0.1:
                report += f"• Pylint 評分提升 {pylint_trend:.1f} 分\n"
            if mi_trend > 0.1:
                report += f"• 可維護性指標提升 {mi_trend:.1f}\n"
            if complexity_trend < -0.1:
                report += f"• 平均複雜度降低 {abs(complexity_trend):.1f}\n"

        # 需要關注的問題
        if pylint_trend < -0.1 or mi_trend < -0.1 or complexity_trend > 0.1:
            report += "\n## ⚠️ 需要關注\n"
            if pylint_trend < -0.1:
                report += f"• Pylint 評分下降 {abs(pylint_trend):.1f} 分\n"
            if mi_trend < -0.1:
                report += f"• 可維護性指標下降 {abs(mi_trend):.1f}\n"
            if complexity_trend > 0.1:
                report += f"• 平均複雜度增加 {complexity_trend:.1f}\n"

        report += f"\n📋 詳細分析: [查看趨勢圖表](docs/reports/charts/)"

        return report

    def send_daily_report(self, quality_data: Dict[str, Any]) -> bool:
        """發送每日報告.

        Args:
            quality_data: 品質數據

        Returns:
            bool: 是否發送成功
        """
        report = self.generate_daily_report(quality_data)

        success = True

        # 發送到 Slack
        if not self.send_slack_notification(report, 'info'):
            success = False

        # 發送到 Teams
        if not self.send_teams_notification(report, 'info'):
            success = False

        return success

    def send_weekly_report(self, historical_data: List[Dict[str, Any]]) -> bool:
        """發送週報.

        Args:
            historical_data: 歷史品質數據

        Returns:
            bool: 是否發送成功
        """
        report = self.generate_weekly_report(historical_data)

        success = True

        # 發送到 Slack
        if not self.send_slack_notification(report, 'info'):
            success = False

        # 發送到 Teams
        if not self.send_teams_notification(report, 'info'):
            success = False

        return success

    def generate_pr_quality_comment(self, quality_data: Dict[str, Any], pr_number: int) -> str:
        """生成 PR 品質評論.

        Args:
            quality_data: 品質數據
            pr_number: PR 編號

        Returns:
            str: 評論內容
        """
        # 計算總體評分
        pylint_scores = quality_data.get('pylint_scores', {})
        avg_pylint = sum(pylint_scores.values()) / len(pylint_scores) if pylint_scores else 0

        complexity_data = quality_data.get('code_metrics', {}).get('complexity', {})
        avg_complexity = complexity_data.get('average_complexity', 0)

        maintainability_data = quality_data.get('code_metrics', {}).get('maintainability', {})
        avg_mi = maintainability_data.get('average_mi', 0)

        # 計算總體評分 (0-100)
        pylint_score = min(avg_pylint * 10, 100)  # Pylint 分數轉換為百分制
        complexity_score = max(100 - avg_complexity * 5, 0)  # 複雜度越低分數越高
        mi_score = min(avg_mi * 2.5, 100)  # MI 指標轉換為百分制

        overall_score = (pylint_score + complexity_score + mi_score) / 3

        # 評分等級
        if overall_score >= 90:
            grade = "A"
            emoji = "🏆"
            status = "優秀"
        elif overall_score >= 80:
            grade = "B"
            emoji = "✅"
            status = "良好"
        elif overall_score >= 70:
            grade = "C"
            emoji = "⚠️"
            status = "可接受"
        elif overall_score >= 60:
            grade = "D"
            emoji = "❌"
            status = "需改進"
        else:
            grade = "F"
            emoji = "🚨"
            status = "不合格"

        comment = f"""
## {emoji} 程式碼品質評分報告

**總體評分**: {overall_score:.1f}/100 ({grade} - {status})

### 📊 詳細指標

| 指標 | 分數 | 狀態 | 目標 |
|------|------|------|------|
| Pylint 評分 | {avg_pylint:.1f}/10 | {'✅' if avg_pylint >= 8.5 else '⚠️' if avg_pylint >= 8.0 else '❌'} | ≥8.5 |
| 平均複雜度 | {avg_complexity:.1f} | {'✅' if avg_complexity <= 10 else '⚠️' if avg_complexity <= 15 else '❌'} | ≤10 |
| 可維護性指標 | {avg_mi:.1f} | {'✅' if avg_mi >= 20 else '⚠️' if avg_mi >= 10 else '❌'} | ≥20 |

### 🎯 品質檢查結果
"""

        # 檢查警報
        alerts = self.check_quality_thresholds(quality_data)
        if alerts:
            critical_alerts = [a for a in alerts if a['severity'] == 'critical']
            warning_alerts = [a for a in alerts if a['severity'] == 'warning']

            if critical_alerts:
                comment += f"\n🚨 **緊急問題** ({len(critical_alerts)} 個):\n"
                for alert in critical_alerts:
                    comment += f"- {alert['message']}\n"

            if warning_alerts:
                comment += f"\n⚠️ **警告問題** ({len(warning_alerts)} 個):\n"
                for alert in warning_alerts:
                    comment += f"- {alert['message']}\n"
        else:
            comment += "\n✅ **所有品質檢查都通過了！**\n"

        # 改進建議
        recommendations = quality_data.get('recommendations', [])
        if recommendations:
            high_priority = [r for r in recommendations if r['priority'] == 'high']
            if high_priority:
                comment += f"\n### 💡 建議改進 (高優先級)\n"
                for rec in high_priority[:3]:  # 只顯示前3個
                    comment += f"- **{rec['issue']}**: {rec['action']}\n"

        comment += f"\n---\n*此評論由自動化品質檢查系統生成 - PR #{pr_number}*"

        return comment

    def send_pr_quality_comment(self, quality_data: Dict[str, Any], pr_number: int) -> bool:
        """發送 PR 品質評論.

        Args:
            quality_data: 品質數據
            pr_number: PR 編號

        Returns:
            bool: 是否發送成功
        """
        comment = self.generate_pr_quality_comment(quality_data, pr_number)
        return self.send_github_comment(pr_number, comment)
