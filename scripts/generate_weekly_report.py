#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
週報自動化生成工具

此腳本用於生成代碼品質週報，包含檔案大小統計、Pylint分數趨勢、
測試覆蓋率變化等關鍵指標。

使用方法:
    python scripts/generate_weekly_report.py
    python scripts/generate_weekly_report.py --output reports/weekly/report.md
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class WeeklyReportGenerator:
    """週報生成器"""
    
    def __init__(self):
        """初始化生成器"""
        self.report_date = datetime.now()
        self.week_start = self.report_date - timedelta(days=self.report_date.weekday())
        
    def load_file_size_data(self) -> Dict:
        """載入檔案大小分析數據"""
        try:
            with open('reports/weekly/file_size_analysis.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'analysis': {'oversized_files': 0, 'total_files': 0}}
    
    def load_pylint_data(self) -> Dict:
        """載入Pylint分析數據"""
        try:
            with open('reports/weekly/pylint_report.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 計算平均分數
                if isinstance(data, list) and data:
                    total_score = sum(item.get('score', 0) for item in data if 'score' in item)
                    avg_score = total_score / len(data) if data else 0
                    return {'average_score': avg_score, 'total_issues': len(data)}
                return {'average_score': 0, 'total_issues': 0}
        except (FileNotFoundError, json.JSONDecodeError):
            return {'average_score': 0, 'total_issues': 0}
    
    def load_coverage_data(self) -> Dict:
        """載入測試覆蓋率數據"""
        try:
            with open('reports/weekly/coverage_report.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'coverage_percentage': 0, 'total_lines': 0, 'covered_lines': 0}
    
    def generate_file_size_section(self, data: Dict) -> str:
        """生成檔案大小分析章節"""
        analysis = data.get('analysis', {})
        oversized = analysis.get('oversized_files', 0)
        total = analysis.get('total_files', 0)
        compliance_rate = ((total - oversized) / total * 100) if total > 0 else 0
        
        status_emoji = "✅" if oversized == 0 else "⚠️" if oversized <= 5 else "❌"
        
        return f"""## 📏 檔案大小合規性

{status_emoji} **合規率**: {compliance_rate:.1f}% ({total - oversized}/{total} 檔案)

- **總檔案數**: {total}
- **超大檔案數**: {oversized}
- **合規標準**: ≤300行

### 趨勢分析
- 本週新增超大檔案: 待實現
- 本週修復檔案: 待實現
- 整體趨勢: {"改善" if oversized <= 5 else "需要關注"}
"""
    
    def generate_pylint_section(self, data: Dict) -> str:
        """生成Pylint分析章節"""
        score = data.get('average_score', 0)
        issues = data.get('total_issues', 0)
        
        status_emoji = "✅" if score >= 8.5 else "⚠️" if score >= 7.0 else "❌"
        
        return f"""## 🔍 代碼品質 (Pylint)

{status_emoji} **平均分數**: {score:.2f}/10.0

- **目標分數**: ≥8.5
- **總問題數**: {issues}
- **品質等級**: {"優秀" if score >= 9.0 else "良好" if score >= 8.5 else "需改進"}

### 主要問題類型
- 待實現詳細分析
"""
    
    def generate_coverage_section(self, data: Dict) -> str:
        """生成測試覆蓋率章節"""
        coverage = data.get('coverage_percentage', 0)
        total_lines = data.get('total_lines', 0)
        covered_lines = data.get('covered_lines', 0)
        
        status_emoji = "✅" if coverage >= 80 else "⚠️" if coverage >= 70 else "❌"
        
        return f"""## 🧪 測試覆蓋率

{status_emoji} **覆蓋率**: {coverage:.1f}%

- **目標覆蓋率**: ≥80%
- **總代碼行數**: {total_lines:,}
- **已覆蓋行數**: {covered_lines:,}
- **未覆蓋行數**: {total_lines - covered_lines:,}

### 覆蓋率分析
- 核心模組覆蓋率: 待實現
- 新增代碼覆蓋率: 待實現
"""
    
    def generate_recommendations(self, file_data: Dict, pylint_data: Dict, coverage_data: Dict) -> str:
        """生成改進建議"""
        recommendations = []
        
        # 檔案大小建議
        oversized = file_data.get('analysis', {}).get('oversized_files', 0)
        if oversized > 0:
            recommendations.append(f"🔧 重構 {oversized} 個超大檔案，拆分為更小的模組")
        
        # Pylint建議
        pylint_score = pylint_data.get('average_score', 0)
        if pylint_score < 8.5:
            recommendations.append(f"📝 提升代碼品質，目標Pylint分數從 {pylint_score:.1f} 提升到 8.5+")
        
        # 覆蓋率建議
        coverage = coverage_data.get('coverage_percentage', 0)
        if coverage < 80:
            recommendations.append(f"🧪 增加測試覆蓋率，從 {coverage:.1f}% 提升到 80%+")
        
        if not recommendations:
            recommendations.append("🎉 所有品質指標都達標，繼續保持！")
        
        return f"""## 📋 改進建議

### 本週行動項目
""" + "\n".join(f"{i+1}. {rec}" for i, rec in enumerate(recommendations)) + """

### 長期目標
- 建立自動化品質監控
- 完善CI/CD流程
- 提升開發效率
"""
    
    def generate_report(self) -> str:
        """生成完整週報"""
        # 載入數據
        file_data = self.load_file_size_data()
        pylint_data = self.load_pylint_data()
        coverage_data = self.load_coverage_data()
        
        # 生成報告
        report = f"""# AI交易系統代碼品質週報

**報告日期**: {self.report_date.strftime('%Y年%m月%d日')}  
**報告週期**: {self.week_start.strftime('%Y-%m-%d')} ~ {(self.week_start + timedelta(days=6)).strftime('%Y-%m-%d')}  
**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{self.generate_file_size_section(file_data)}

{self.generate_pylint_section(pylint_data)}

{self.generate_coverage_section(coverage_data)}

{self.generate_recommendations(file_data, pylint_data, coverage_data)}

## 📊 歷史趨勢

### 品質指標變化
- 檔案大小合規率: 待實現趨勢圖
- Pylint平均分數: 待實現趨勢圖  
- 測試覆蓋率: 待實現趨勢圖

---

*此報告由自動化系統生成，如有問題請聯繫開發團隊*
"""
        return report


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='生成代碼品質週報')
    parser.add_argument('--output', type=str, help='輸出檔案路徑')
    
    args = parser.parse_args()
    
    generator = WeeklyReportGenerator()
    report = generator.generate_report()
    
    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 週報已生成: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
