#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PR品質檢查工具

此腳本用於生成PR的品質檢查報告。

使用方法:
    python scripts/pr_quality_check.py
    python scripts/pr_quality_check.py --output reports/pr/quality_report.md
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List


class PRQualityReporter:
    """PR品質報告生成器"""
    
    def __init__(self):
        """初始化報告生成器"""
        self.analysis_data = {}
        
    def load_analysis_data(self) -> Dict:
        """載入分析數據"""
        try:
            with open('reports/pr/changes_analysis.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def generate_summary_section(self, data: Dict) -> str:
        """生成摘要章節"""
        changed_files = data.get('changed_files_count', 0)
        python_files = data.get('python_files_count', 0)
        quality_score = data.get('quality_score', 10.0)
        
        # 判斷整體品質等級
        if quality_score >= 9.0:
            quality_level = "優秀 ✅"
            quality_emoji = "🎉"
        elif quality_score >= 8.5:
            quality_level = "良好 ✅"
            quality_emoji = "👍"
        elif quality_score >= 7.0:
            quality_level = "需改進 ⚠️"
            quality_emoji = "⚠️"
        else:
            quality_level = "不合格 ❌"
            quality_emoji = "❌"
        
        return f"""## {quality_emoji} 品質檢查摘要

**整體品質等級**: {quality_level}

### 📊 變更統計
- **變更檔案**: {changed_files} 個
- **Python檔案**: {python_files} 個
- **品質分數**: {quality_score:.1f}/10.0
"""
    
    def generate_file_size_section(self, data: Dict) -> str:
        """生成檔案大小檢查章節"""
        has_large_files = data.get('has_large_files', False)
        large_files = data.get('large_files', [])
        
        if not has_large_files:
            return """### 📏 檔案大小檢查 ✅

所有檔案都符合 ≤300行 的標準。
"""
        else:
            files_list = "\n".join([
                f"- `{file['path']}`: {file['lines']} 行"
                for file in large_files
            ])
            
            return f"""### 📏 檔案大小檢查 ❌

發現 {len(large_files)} 個超過300行的檔案：

{files_list}

**建議**: 請將這些檔案重構為更小的模組。
"""
    
    def generate_quality_section(self, data: Dict) -> str:
        """生成代碼品質章節"""
        quality_score = data.get('quality_score', 10.0)
        
        if quality_score >= 8.5:
            status = "✅"
            message = "代碼品質良好，符合標準。"
        else:
            status = "❌"
            message = f"代碼品質需要改進，目前分數 {quality_score:.1f} < 8.5。"
        
        return f"""### 🔍 代碼品質檢查 {status}

**Pylint分數**: {quality_score:.1f}/10.0

{message}
"""
    
    def generate_coverage_section(self, data: Dict) -> str:
        """生成測試覆蓋率章節"""
        coverage = data.get('test_coverage', 100.0)
        
        if coverage >= 80:
            status = "✅"
            message = "測試覆蓋率良好。"
        else:
            status = "❌"
            message = f"測試覆蓋率不足，目前 {coverage:.1f}% < 80%。"
        
        return f"""### 🧪 測試覆蓋率檢查 {status}

**覆蓋率**: {coverage:.1f}%

{message}
"""
    
    def generate_security_section(self, data: Dict) -> str:
        """生成安全檢查章節"""
        security_issues = data.get('security_issues', 0)
        
        if security_issues == 0:
            return """### 🔒 安全檢查 ✅

未發現安全問題。
"""
        else:
            return f"""### 🔒 安全檢查 ❌

發現 {security_issues} 個安全問題，請及時修復。
"""
    
    def generate_recommendations_section(self, data: Dict) -> str:
        """生成建議章節"""
        recommendations = data.get('recommendations', [])
        
        if not recommendations:
            return """## 🎉 恭喜！

此PR已通過所有品質檢查，可以進行審查和合併。
"""
        else:
            rec_list = "\n".join([
                f"{i+1}. {rec}"
                for i, rec in enumerate(recommendations)
            ])
            
            return f"""## 📋 改進建議

請在合併前處理以下問題：

{rec_list}

### 🔧 快速修復指南
- **檔案大小**: 使用模組化重構，將大檔案拆分為功能明確的小模組
- **代碼品質**: 運行 `poetry run pylint src/` 查看詳細問題
- **測試覆蓋**: 為新增/修改的代碼添加單元測試
- **安全問題**: 運行 `poetry run bandit -r src/` 查看安全問題
"""
    
    def generate_report(self) -> str:
        """生成完整報告"""
        data = self.load_analysis_data()
        
        if not data:
            return """# PR品質檢查報告

⚠️ 無法載入分析數據，請檢查分析腳本是否正常執行。

---
*報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        report = f"""# PR品質檢查報告

{self.generate_summary_section(data)}

## 📋 詳細檢查結果

{self.generate_file_size_section(data)}

{self.generate_quality_section(data)}

{self.generate_coverage_section(data)}

{self.generate_security_section(data)}

{self.generate_recommendations_section(data)}

---
*報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        return report


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='生成PR品質檢查報告')
    parser.add_argument('--output', type=str, help='輸出檔案路徑')
    
    args = parser.parse_args()
    
    reporter = PRQualityReporter()
    report = reporter.generate_report()
    
    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ PR品質報告已生成: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
