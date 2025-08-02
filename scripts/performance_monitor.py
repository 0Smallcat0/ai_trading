#!/usr/bin/env python3
"""
CI/CD 性能監控腳本

此腳本監控和分析 GitHub Actions 工作流程的執行性能，包括：
- 執行時間追蹤
- 性能趨勢分析
- 瓶頸識別
- 優化建議生成

Example:
    >>> python scripts/performance_monitor.py
    >>> python scripts/performance_monitor.py --analyze-trends
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests


class PerformanceMonitor:
    """CI/CD 性能監控器.
    
    監控 GitHub Actions 工作流程的執行性能並提供分析報告。
    """

    def __init__(self, repo_owner: str, repo_name: str, token: Optional[str] = None):
        """初始化性能監控器.
        
        Args:
            repo_owner: GitHub 倉庫擁有者
            repo_name: GitHub 倉庫名稱
            token: GitHub API token
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.api_base = "https://api.github.com"
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {self.token}' if self.token else None
        }
        
        # 性能目標
        self.performance_targets = {
            'total_time': 300,  # 5分鐘
            'quick_checks': 120,  # 2分鐘
            'static_analysis': 180,  # 3分鐘
            'security_checks': 120,  # 2分鐘
            'tests': 240,  # 4分鐘
            'quality_report': 60,  # 1分鐘
        }

    def get_workflow_runs(self, days: int = 7) -> List[Dict[str, Any]]:
        """獲取工作流程執行記錄.
        
        Args:
            days: 獲取最近幾天的記錄
            
        Returns:
            List[Dict[str, Any]]: 工作流程執行記錄列表
        """
        try:
            since = (datetime.now() - timedelta(days=days)).isoformat()
            
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/actions/runs"
            params = {
                'per_page': 100,
                'created': f'>{since}',
                'status': 'completed'
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json().get('workflow_runs', [])
            
        except Exception as e:
            print(f"❌ 獲取工作流程記錄失敗: {e}")
            return []

    def get_workflow_jobs(self, run_id: int) -> List[Dict[str, Any]]:
        """獲取工作流程作業詳情.
        
        Args:
            run_id: 工作流程執行 ID
            
        Returns:
            List[Dict[str, Any]]: 作業詳情列表
        """
        try:
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}/jobs"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            return response.json().get('jobs', [])
            
        except Exception as e:
            print(f"❌ 獲取作業詳情失敗: {e}")
            return []

    def analyze_performance(self, days: int = 7) -> Dict[str, Any]:
        """分析性能數據.
        
        Args:
            days: 分析最近幾天的數據
            
        Returns:
            Dict[str, Any]: 性能分析結果
        """
        print(f"📊 分析最近 {days} 天的性能數據...")
        
        runs = self.get_workflow_runs(days)
        if not runs:
            print("⚠️ 沒有找到工作流程執行記錄")
            return {}

        analysis = {
            'total_runs': len(runs),
            'successful_runs': 0,
            'failed_runs': 0,
            'average_duration': 0,
            'job_performance': {},
            'trends': [],
            'bottlenecks': [],
            'recommendations': []
        }

        total_duration = 0
        job_durations = {}

        for run in runs:
            if run['conclusion'] == 'success':
                analysis['successful_runs'] += 1
            else:
                analysis['failed_runs'] += 1

            # 計算執行時間
            start_time = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
            duration = (end_time - start_time).total_seconds()
            
            total_duration += duration

            # 獲取作業詳情
            jobs = self.get_workflow_jobs(run['id'])
            for job in jobs:
                job_name = job['name']
                if job_name not in job_durations:
                    job_durations[job_name] = []

                if job['started_at'] and job['completed_at']:
                    job_start = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
                    job_end = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
                    job_duration = (job_end - job_start).total_seconds()
                    job_durations[job_name].append(job_duration)

        # 計算平均值
        if analysis['total_runs'] > 0:
            analysis['average_duration'] = total_duration / analysis['total_runs']

        # 分析作業性能
        for job_name, durations in job_durations.items():
            if durations:
                analysis['job_performance'][job_name] = {
                    'average_duration': sum(durations) / len(durations),
                    'max_duration': max(durations),
                    'min_duration': min(durations),
                    'runs': len(durations)
                }

        # 識別瓶頸
        analysis['bottlenecks'] = self._identify_bottlenecks(analysis['job_performance'])
        
        # 生成建議
        analysis['recommendations'] = self._generate_recommendations(analysis)

        return analysis

    def _identify_bottlenecks(self, job_performance: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """識別性能瓶頸.
        
        Args:
            job_performance: 作業性能數據
            
        Returns:
            List[Dict[str, Any]]: 瓶頸列表
        """
        bottlenecks = []
        
        for job_name, perf in job_performance.items():
            avg_duration = perf['average_duration']
            
            # 檢查是否超過目標時間
            for target_name, target_time in self.performance_targets.items():
                if target_name.lower() in job_name.lower():
                    if avg_duration > target_time:
                        bottlenecks.append({
                            'job': job_name,
                            'average_duration': avg_duration,
                            'target_duration': target_time,
                            'excess_time': avg_duration - target_time,
                            'severity': 'high' if avg_duration > target_time * 1.5 else 'medium'
                        })
                    break

        return sorted(bottlenecks, key=lambda x: x['excess_time'], reverse=True)

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """生成優化建議.
        
        Args:
            analysis: 性能分析結果
            
        Returns:
            List[str]: 優化建議列表
        """
        recommendations = []
        
        # 基於總執行時間的建議
        avg_duration = analysis.get('average_duration', 0)
        if avg_duration > self.performance_targets['total_time']:
            recommendations.append(
                f"總執行時間 ({avg_duration:.0f}s) 超過目標 ({self.performance_targets['total_time']}s)，"
                "建議進一步並行化或優化依賴安裝"
            )

        # 基於瓶頸的建議
        bottlenecks = analysis.get('bottlenecks', [])
        for bottleneck in bottlenecks[:3]:  # 只顯示前3個瓶頸
            job = bottleneck['job']
            excess = bottleneck['excess_time']
            
            if 'test' in job.lower():
                recommendations.append(
                    f"{job} 超時 {excess:.0f}s，建議優化測試並行度或減少測試範圍"
                )
            elif 'static' in job.lower() or 'pylint' in job.lower():
                recommendations.append(
                    f"{job} 超時 {excess:.0f}s，建議優化 Pylint 配置或使用快取"
                )
            elif 'security' in job.lower():
                recommendations.append(
                    f"{job} 超時 {excess:.0f}s，建議優化安全掃描範圍或使用快取"
                )

        # 基於成功率的建議
        success_rate = analysis['successful_runs'] / analysis['total_runs'] if analysis['total_runs'] > 0 else 0
        if success_rate < 0.9:
            recommendations.append(
                f"成功率 ({success_rate:.1%}) 偏低，建議檢查測試穩定性和依賴管理"
            )

        return recommendations

    def generate_performance_report(self, days: int = 7) -> str:
        """生成性能報告.
        
        Args:
            days: 分析天數
            
        Returns:
            str: HTML 格式的性能報告
        """
        analysis = self.analyze_performance(days)
        
        if not analysis:
            return "<p>無法生成性能報告：沒有數據</p>"

        html = f"""
        <div class="performance-report">
            <h2>🚀 CI/CD 性能報告</h2>
            <p><strong>分析期間:</strong> 最近 {days} 天</p>
            
            <h3>📊 總體統計</h3>
            <ul>
                <li>總執行次數: {analysis['total_runs']}</li>
                <li>成功次數: {analysis['successful_runs']}</li>
                <li>失敗次數: {analysis['failed_runs']}</li>
                <li>成功率: {analysis['successful_runs']/analysis['total_runs']*100:.1f}%</li>
                <li>平均執行時間: {analysis['average_duration']:.0f}s</li>
            </ul>
            
            <h3>⏱️ 作業性能</h3>
            <table border="1">
                <tr>
                    <th>作業名稱</th>
                    <th>平均時間</th>
                    <th>最大時間</th>
                    <th>最小時間</th>
                    <th>執行次數</th>
                </tr>
        """
        
        for job_name, perf in analysis['job_performance'].items():
            html += f"""
                <tr>
                    <td>{job_name}</td>
                    <td>{perf['average_duration']:.0f}s</td>
                    <td>{perf['max_duration']:.0f}s</td>
                    <td>{perf['min_duration']:.0f}s</td>
                    <td>{perf['runs']}</td>
                </tr>
            """
        
        html += "</table>"
        
        # 瓶頸分析
        if analysis['bottlenecks']:
            html += "<h3>🔍 性能瓶頸</h3><ul>"
            for bottleneck in analysis['bottlenecks']:
                severity_icon = "🔴" if bottleneck['severity'] == 'high' else "🟡"
                html += f"""
                    <li>{severity_icon} {bottleneck['job']}: 
                    平均 {bottleneck['average_duration']:.0f}s 
                    (目標 {bottleneck['target_duration']}s, 
                    超時 {bottleneck['excess_time']:.0f}s)</li>
                """
            html += "</ul>"
        
        # 優化建議
        if analysis['recommendations']:
            html += "<h3>💡 優化建議</h3><ul>"
            for rec in analysis['recommendations']:
                html += f"<li>{rec}</li>"
            html += "</ul>"
        
        html += "</div>"
        
        return html

    def save_performance_data(self, analysis: Dict[str, Any], output_file: str = "performance_data.json"):
        """保存性能數據.
        
        Args:
            analysis: 性能分析結果
            output_file: 輸出檔案名稱
        """
        try:
            output_path = Path("docs/reports") / output_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 添加時間戳
            analysis['timestamp'] = datetime.now().isoformat()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 性能數據已保存到 {output_path}")
            
        except Exception as e:
            print(f"❌ 保存性能數據失敗: {e}")


def main():
    """主函數."""
    parser = argparse.ArgumentParser(description="CI/CD 性能監控")
    parser.add_argument(
        "--repo", 
        default="Cookieeeeeeeeeeeeeee/ai_trading",
        help="GitHub 倉庫 (格式: owner/repo)"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        default=7,
        help="分析天數"
    )
    parser.add_argument(
        "--output", 
        default="performance_report.html",
        help="輸出報告檔案名稱"
    )
    
    args = parser.parse_args()
    
    try:
        repo_owner, repo_name = args.repo.split('/')
    except ValueError:
        print("❌ 倉庫格式錯誤，請使用 owner/repo 格式")
        return 1
    
    monitor = PerformanceMonitor(repo_owner, repo_name)
    
    # 生成性能分析
    analysis = monitor.analyze_performance(args.days)
    
    if not analysis:
        print("❌ 無法獲取性能數據")
        return 1
    
    # 生成報告
    report_html = monitor.generate_performance_report(args.days)
    
    # 保存報告
    try:
        output_path = Path("docs/reports") / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>CI/CD 性能報告</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                {report_html}
            </body>
            </html>
            """)
        
        print(f"✅ 性能報告已生成: {output_path}")
        
    except Exception as e:
        print(f"❌ 保存報告失敗: {e}")
        return 1
    
    # 保存原始數據
    monitor.save_performance_data(analysis)
    
    # 顯示關鍵指標
    print("\n📊 關鍵性能指標:")
    print(f"  平均執行時間: {analysis['average_duration']:.0f}s")
    print(f"  成功率: {analysis['successful_runs']/analysis['total_runs']*100:.1f}%")
    
    if analysis['bottlenecks']:
        print(f"  發現 {len(analysis['bottlenecks'])} 個性能瓶頸")
    
    if analysis['average_duration'] <= 300:
        print("🎉 性能目標達成！(<5分鐘)")
    else:
        print("⚠️ 性能目標未達成 (≥5分鐘)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
