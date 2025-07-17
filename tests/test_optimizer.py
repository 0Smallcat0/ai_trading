"""測試優化和管理工具

此模組提供測試的優化和管理功能，包括：
- 測試檔案大小檢查
- 測試覆蓋率分析
- 測試性能監控
- 測試資料管理
- 自動化測試報告

符合測試標準：≥80% 覆蓋率（核心模組 ≥90%），檔案 ≤300 行
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import json
import time
from datetime import datetime

# 設定日誌
logger = logging.getLogger(__name__)


class TestOptimizer:
    """測試優化器
    
    提供測試的優化和管理功能。
    """
    
    # 測試標準
    COVERAGE_THRESHOLDS = {
        "core_modules": 90,      # 核心模組覆蓋率要求
        "general_modules": 80,   # 一般模組覆蓋率要求
        "ui_modules": 70,        # UI 模組覆蓋率要求
    }
    
    MAX_FILE_LINES = 300        # 最大檔案行數
    
    # 核心模組列表
    CORE_MODULES = [
        "src/core",
        "src/api",
        "src/portfolio",
        "src/risk",
        "src/trading",
        "src/data",
    ]
    
    def __init__(self, project_root: Optional[str] = None):
        """初始化測試優化器
        
        Args:
            project_root: 專案根目錄路徑
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.tests_dir = self.project_root / "tests"
        self.src_dir = self.project_root / "src"
        
    def check_test_file_sizes(self) -> Dict[str, Any]:
        """檢查測試檔案大小
        
        Returns:
            檢查結果字典
        """
        logger.info("檢查測試檔案大小...")
        
        results = {
            "total_files": 0,
            "oversized_files": [],
            "compliant_files": [],
            "summary": {}
        }
        
        # 遍歷所有測試檔案
        for test_file in self.tests_dir.rglob("*.py"):
            if test_file.name.startswith("__"):
                continue
                
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                
                results["total_files"] += 1
                
                file_info = {
                    "path": str(test_file.relative_to(self.project_root)),
                    "lines": lines,
                    "compliant": lines <= self.MAX_FILE_LINES
                }
                
                if lines > self.MAX_FILE_LINES:
                    results["oversized_files"].append(file_info)
                    logger.warning(f"測試檔案過大: {test_file} ({lines} 行)")
                else:
                    results["compliant_files"].append(file_info)
                    
            except Exception as e:
                logger.error(f"讀取測試檔案失敗 {test_file}: {e}")
        
        # 生成摘要
        results["summary"] = {
            "total_files": results["total_files"],
            "oversized_count": len(results["oversized_files"]),
            "compliant_count": len(results["compliant_files"]),
            "compliance_rate": (
                len(results["compliant_files"]) / results["total_files"] * 100
                if results["total_files"] > 0 else 0
            )
        }
        
        logger.info(f"測試檔案大小檢查完成: {results['summary']}")
        return results
    
    def run_coverage_analysis(self) -> Dict[str, Any]:
        """執行測試覆蓋率分析
        
        Returns:
            覆蓋率分析結果
        """
        logger.info("執行測試覆蓋率分析...")
        
        try:
            # 執行 pytest 覆蓋率檢查
            cmd = [
                sys.executable, "-m", "pytest",
                str(self.tests_dir),
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json",
                "--cov-report=html:htmlcov",
                "-v"
            ]
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5分鐘超時
            )
            execution_time = time.time() - start_time
            
            # 解析覆蓋率結果
            coverage_data = self._parse_coverage_results()
            
            return {
                "success": result.returncode == 0,
                "execution_time": execution_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "coverage_data": coverage_data,
                "timestamp": datetime.now().isoformat()
            }
            
        except subprocess.TimeoutExpired:
            logger.error("測試覆蓋率分析超時")
            return {"success": False, "error": "測試執行超時"}
        except Exception as e:
            logger.error(f"測試覆蓋率分析失敗: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_coverage_results(self) -> Dict[str, Any]:
        """解析覆蓋率結果
        
        Returns:
            解析後的覆蓋率數據
        """
        coverage_file = self.project_root / "coverage.json"
        
        if not coverage_file.exists():
            logger.warning("覆蓋率 JSON 檔案不存在")
            return {}
        
        try:
            with open(coverage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 分析模組覆蓋率
            module_coverage = {}
            for file_path, file_data in data.get("files", {}).items():
                # 判斷模組類型
                module_type = self._classify_module(file_path)
                coverage_percent = file_data.get("summary", {}).get("percent_covered", 0)
                
                if module_type not in module_coverage:
                    module_coverage[module_type] = []
                
                module_coverage[module_type].append({
                    "file": file_path,
                    "coverage": coverage_percent,
                    "lines_covered": file_data.get("summary", {}).get("covered_lines", 0),
                    "lines_missing": file_data.get("summary", {}).get("missing_lines", 0),
                })
            
            # 計算平均覆蓋率
            summary = {}
            for module_type, files in module_coverage.items():
                if files:
                    avg_coverage = sum(f["coverage"] for f in files) / len(files)
                    threshold = self.COVERAGE_THRESHOLDS.get(module_type, 80)
                    
                    summary[module_type] = {
                        "average_coverage": avg_coverage,
                        "threshold": threshold,
                        "compliant": avg_coverage >= threshold,
                        "file_count": len(files),
                        "files": files
                    }
            
            return {
                "total_coverage": data.get("totals", {}).get("percent_covered", 0),
                "module_coverage": module_coverage,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"解析覆蓋率結果失敗: {e}")
            return {}
    
    def _classify_module(self, file_path: str) -> str:
        """分類模組類型
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            模組類型
        """
        for core_module in self.CORE_MODULES:
            if core_module in file_path:
                return "core_modules"
        
        if "ui" in file_path or "streamlit" in file_path:
            return "ui_modules"
        
        return "general_modules"
    
    def generate_test_report(self) -> Dict[str, Any]:
        """生成測試報告
        
        Returns:
            測試報告
        """
        logger.info("生成測試報告...")
        
        # 檢查檔案大小
        file_size_results = self.check_test_file_sizes()
        
        # 執行覆蓋率分析
        coverage_results = self.run_coverage_analysis()
        
        # 生成綜合報告
        report = {
            "timestamp": datetime.now().isoformat(),
            "file_size_check": file_size_results,
            "coverage_analysis": coverage_results,
            "recommendations": self._generate_recommendations(
                file_size_results, coverage_results
            )
        }
        
        # 保存報告
        report_file = self.project_root / "test_optimization_report.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"測試報告已保存: {report_file}")
        except Exception as e:
            logger.error(f"保存測試報告失敗: {e}")
        
        return report
    
    def _generate_recommendations(
        self, 
        file_size_results: Dict[str, Any], 
        coverage_results: Dict[str, Any]
    ) -> List[str]:
        """生成改進建議
        
        Args:
            file_size_results: 檔案大小檢查結果
            coverage_results: 覆蓋率分析結果
            
        Returns:
            改進建議列表
        """
        recommendations = []
        
        # 檔案大小建議
        if file_size_results["oversized_files"]:
            recommendations.append(
                f"有 {len(file_size_results['oversized_files'])} 個測試檔案超過 {self.MAX_FILE_LINES} 行限制，建議拆分"
            )
        
        # 覆蓋率建議
        if coverage_results.get("success") and coverage_results.get("coverage_data"):
            coverage_data = coverage_results["coverage_data"]
            
            for module_type, data in coverage_data.get("summary", {}).items():
                if not data["compliant"]:
                    recommendations.append(
                        f"{module_type} 覆蓋率 {data['average_coverage']:.1f}% "
                        f"低於要求的 {data['threshold']}%，需要增加測試"
                    )
        
        # 性能建議
        execution_time = coverage_results.get("execution_time", 0)
        if execution_time > 60:  # 超過 1 分鐘
            recommendations.append(
                f"測試執行時間 {execution_time:.1f}s 過長，建議優化測試性能"
            )
        
        if not recommendations:
            recommendations.append("測試狀況良好，符合所有標準")
        
        return recommendations


def main():
    """主函數"""
    optimizer = TestOptimizer()
    
    print("🚀 開始測試優化分析...")
    report = optimizer.generate_test_report()
    
    print("\n📊 測試優化報告")
    print("=" * 50)
    
    # 顯示檔案大小檢查結果
    file_summary = report["file_size_check"]["summary"]
    print(f"\n📏 檔案大小檢查:")
    print(f"  總檔案數: {file_summary['total_files']}")
    print(f"  符合標準: {file_summary['compliant_count']}")
    print(f"  超過限制: {file_summary['oversized_count']}")
    print(f"  合規率: {file_summary['compliance_rate']:.1f}%")
    
    # 顯示覆蓋率結果
    if report["coverage_analysis"].get("success"):
        coverage_data = report["coverage_analysis"]["coverage_data"]
        total_coverage = coverage_data.get("total_coverage", 0)
        print(f"\n📊 測試覆蓋率:")
        print(f"  總覆蓋率: {total_coverage:.1f}%")
        
        for module_type, data in coverage_data.get("summary", {}).items():
            status = "✅" if data["compliant"] else "❌"
            print(f"  {status} {module_type}: {data['average_coverage']:.1f}% "
                  f"(要求: {data['threshold']}%)")
    
    # 顯示建議
    print(f"\n💡 改進建議:")
    for i, recommendation in enumerate(report["recommendations"], 1):
        print(f"  {i}. {recommendation}")
    
    print(f"\n📄 詳細報告已保存至: test_optimization_report.json")


if __name__ == "__main__":
    main()
