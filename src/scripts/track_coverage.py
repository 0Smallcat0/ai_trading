# -*- coding: utf-8 -*-
"""
測試覆蓋率追蹤腳本

此腳本用於追蹤和改進測試覆蓋率，包括：
- 分析當前測試覆蓋率
- 識別未覆蓋的代碼區域
- 生成覆蓋率報告和可視化
- 提供改進建議

使用方法:
    python -m src.scripts.track_coverage [options]

選項:
    --analyze: 分析當前測試覆蓋率
    --identify-gaps: 識別未覆蓋的代碼區域
    --visualize: 生成覆蓋率可視化
    --suggest: 提供改進建議
    --all: 執行所有功能
    --output-dir: 指定輸出目錄
    --min-coverage: 最小覆蓋率閾值 (默認: 80)
"""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.config import RESULTS_DIR
from src.core.logger import get_logger

# 設定日誌
logger = get_logger("coverage_tracker")


def run_coverage_analysis(args):
    """
    執行覆蓋率分析

    Args:
        args: 命令行參數

    Returns:
        Dict: 覆蓋率分析結果
    """
    logger.info("開始執行覆蓋率分析")

    # 構建命令
    cmd = [
        "pytest",
        "--cov=src",
        f"--cov-report=term",
        f"--cov-report=html:{os.path.join(args.output_dir, 'coverage')}",
        f"--cov-report=xml:{os.path.join(args.output_dir, 'coverage.xml')}",
    ]

    # 執行命令
    logger.info(f"執行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 輸出結果
    logger.info(f"覆蓋率分析執行結果: {'成功' if result.returncode == 0 else '失敗'}")
    logger.info(f"輸出:\n{result.stdout}")

    if result.returncode != 0:
        logger.error(f"錯誤:\n{result.stderr}")
        return {}

    # 解析 XML 報告
    coverage_data = parse_coverage_xml(os.path.join(args.output_dir, "coverage.xml"))

    return coverage_data


def parse_coverage_xml(xml_path):
    """
    解析覆蓋率 XML 報告

    Args:
        xml_path: XML 報告路徑

    Returns:
        Dict: 覆蓋率數據
    """
    if not os.path.exists(xml_path):
        logger.error(f"覆蓋率 XML 報告不存在: {xml_path}")
        return {}

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # 獲取總體覆蓋率
        coverage = root.get("line-rate")
        if coverage:
            coverage = float(coverage) * 100

        # 獲取各個包的覆蓋率
        packages = {}
        for package in root.findall(".//package"):
            package_name = package.get("name")
            package_coverage = float(package.get("line-rate")) * 100

            # 獲取各個模組的覆蓋率
            modules = {}
            for module in package.findall(".//class"):
                module_name = module.get("name")
                module_coverage = float(module.get("line-rate")) * 100

                # 獲取未覆蓋的行
                uncovered_lines = []
                for line in module.findall(".//line"):
                    if line.get("hits") == "0":
                        uncovered_lines.append(int(line.get("number")))

                modules[module_name] = {
                    "coverage": module_coverage,
                    "uncovered_lines": uncovered_lines,
                }

            packages[package_name] = {"coverage": package_coverage, "modules": modules}

        return {"total_coverage": coverage, "packages": packages}

    except Exception as e:
        logger.error(f"解析覆蓋率 XML 報告時發生錯誤: {e}")
        return {}


def identify_coverage_gaps(coverage_data):
    """
    識別覆蓋率缺口

    Args:
        coverage_data: 覆蓋率數據

    Returns:
        Dict: 覆蓋率缺口
    """
    logger.info("開始識別覆蓋率缺口")

    gaps = {}

    # 檢查總體覆蓋率
    total_coverage = coverage_data.get("total_coverage")
    if total_coverage and total_coverage < 80:
        gaps["total"] = {
            "current": total_coverage,
            "target": 80,
            "gap": 80 - total_coverage,
        }

    # 檢查各個包的覆蓋率
    for package_name, package_data in coverage_data.get("packages", {}).items():
        package_coverage = package_data.get("coverage")
        if package_coverage and package_coverage < 80:
            if "packages" not in gaps:
                gaps["packages"] = {}

            gaps["packages"][package_name] = {
                "current": package_coverage,
                "target": 80,
                "gap": 80 - package_coverage,
            }

        # 檢查各個模組的覆蓋率
        for module_name, module_data in package_data.get("modules", {}).items():
            module_coverage = module_data.get("coverage")
            if module_coverage and module_coverage < 80:
                if "modules" not in gaps:
                    gaps["modules"] = {}

                gaps["modules"][module_name] = {
                    "current": module_coverage,
                    "target": 80,
                    "gap": 80 - module_coverage,
                    "uncovered_lines": module_data.get("uncovered_lines", []),
                }

    return gaps


def generate_coverage_visualization(coverage_data, args):
    """
    生成覆蓋率可視化

    Args:
        coverage_data: 覆蓋率數據
        args: 命令行參數

    Returns:
        str: 可視化報告路徑
    """
    logger.info("開始生成覆蓋率可視化")

    # 創建輸出目錄
    vis_dir = os.path.join(args.output_dir, "visualization")
    os.makedirs(vis_dir, exist_ok=True)

    # 生成總體覆蓋率圖表
    total_coverage = coverage_data.get("total_coverage")
    if total_coverage:
        plt.figure(figsize=(10, 6))
        plt.bar(["Total Coverage"], [total_coverage], color="blue")
        plt.axhline(y=80, color="r", linestyle="-", label="Target (80%)")
        plt.ylim(0, 100)
        plt.ylabel("Coverage (%)")
        plt.title("Total Code Coverage")
        plt.legend()
        plt.savefig(os.path.join(vis_dir, "total_coverage.png"))
        plt.close()

    # 生成各個包的覆蓋率圖表
    packages = coverage_data.get("packages", {})
    if packages:
        package_names = []
        package_coverages = []

        for package_name, package_data in packages.items():
            package_names.append(package_name)
            package_coverages.append(package_data.get("coverage", 0))

        plt.figure(figsize=(12, 8))
        bars = plt.bar(package_names, package_coverages, color="blue")
        plt.axhline(y=80, color="r", linestyle="-", label="Target (80%)")
        plt.ylim(0, 100)
        plt.ylabel("Coverage (%)")
        plt.title("Package Code Coverage")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.legend()

        # 添加數值標籤
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 1,
                f"{height:.1f}%",
                ha="center",
                va="bottom",
            )

        plt.savefig(os.path.join(vis_dir, "package_coverage.png"))
        plt.close()

    # 生成覆蓋率報告 HTML
    report_path = os.path.join(vis_dir, "coverage_report.html")
    with open(report_path, "w") as f:
        f.write(
            """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Code Coverage Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1, h2, h3 { color: #333; }
                .container { max-width: 1200px; margin: 0 auto; }
                .summary { margin-bottom: 30px; }
                .chart { margin-bottom: 30px; }
                .table { width: 100%; border-collapse: collapse; }
                .table th, .table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                .table th { background-color: #f2f2f2; }
                .good { color: green; }
                .warning { color: orange; }
                .bad { color: red; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Code Coverage Report</h1>
                
                <div class="summary">
                    <h2>Summary</h2>
                    <p>Total Coverage: <span class="{0}">{1:.1f}%</span></p>
                    <p>Target Coverage: 80%</p>
                </div>
                
                <div class="chart">
                    <h2>Total Coverage</h2>
                    <img src="total_coverage.png" alt="Total Coverage Chart">
                </div>
                
                <div class="chart">
                    <h2>Package Coverage</h2>
                    <img src="package_coverage.png" alt="Package Coverage Chart">
                </div>
                
                <div class="details">
                    <h2>Package Details</h2>
                    <table class="table">
                        <tr>
                            <th>Package</th>
                            <th>Coverage</th>
                            <th>Status</th>
                        </tr>
        """.format(
                (
                    "good"
                    if total_coverage >= 80
                    else "warning" if total_coverage >= 60 else "bad"
                ),
                total_coverage,
            )
        )

        # 添加包詳情
        for package_name, package_data in packages.items():
            package_coverage = package_data.get("coverage", 0)
            status_class = (
                "good"
                if package_coverage >= 80
                else "warning" if package_coverage >= 60 else "bad"
            )

            f.write(
                f"""
                        <tr>
                            <td>{package_name}</td>
                            <td>{package_coverage:.1f}%</td>
                            <td class="{status_class}">{
                                'Good' if package_coverage >= 80 else 'Warning' if package_coverage >= 60 else 'Needs Improvement'
                            }</td>
                        </tr>
            """
            )

        f.write(
            """
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        )

    logger.info(f"覆蓋率可視化已生成: {vis_dir}")

    return vis_dir


def suggest_coverage_improvements(gaps):
    """
    提供覆蓋率改進建議

    Args:
        gaps: 覆蓋率缺口

    Returns:
        Dict: 改進建議
    """
    logger.info("開始提供覆蓋率改進建議")

    suggestions = {}

    # 總體建議
    if "total" in gaps:
        suggestions["total"] = {
            "message": f"總體覆蓋率為 {gaps['total']['current']:.1f}%，需要提高 {gaps['total']['gap']:.1f}% 以達到目標。",
            "actions": [
                "優先關注覆蓋率最低的模組",
                "為核心功能添加更多測試",
                "使用參數化測試增加測試場景",
            ],
        }

    # 包級建議
    if "packages" in gaps:
        suggestions["packages"] = {}

        for package_name, package_gap in gaps["packages"].items():
            suggestions["packages"][package_name] = {
                "message": f"包 {package_name} 的覆蓋率為 {package_gap['current']:.1f}%，需要提高 {package_gap['gap']:.1f}% 以達到目標。",
                "actions": [
                    "檢查該包中的所有模組",
                    "為該包添加整合測試",
                    "確保該包的公共 API 有完整的測試",
                ],
            }

    # 模組級建議
    if "modules" in gaps:
        suggestions["modules"] = {}

        for module_name, module_gap in gaps["modules"].items():
            suggestions["modules"][module_name] = {
                "message": f"模組 {module_name} 的覆蓋率為 {module_gap['current']:.1f}%，需要提高 {module_gap['gap']:.1f}% 以達到目標。",
                "actions": [
                    f"添加測試以覆蓋以下行: {', '.join(map(str, module_gap['uncovered_lines'][:10]))}{'...' if len(module_gap['uncovered_lines']) > 10 else ''}",
                    "檢查該模組的異常處理路徑",
                    "使用模擬對象測試外部依賴",
                ],
            }

    return suggestions


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="測試覆蓋率追蹤腳本")
    parser.add_argument("--analyze", action="store_true", help="分析當前測試覆蓋率")
    parser.add_argument(
        "--identify-gaps", action="store_true", help="識別未覆蓋的代碼區域"
    )
    parser.add_argument("--visualize", action="store_true", help="生成覆蓋率可視化")
    parser.add_argument("--suggest", action="store_true", help="提供改進建議")
    parser.add_argument("--all", action="store_true", help="執行所有功能")
    parser.add_argument("--output-dir", type=str, default=None, help="指定輸出目錄")
    parser.add_argument(
        "--min-coverage", type=int, default=80, help="最小覆蓋率閾值 (默認: 80)"
    )

    args = parser.parse_args()

    # 如果沒有指定任何功能，則執行所有功能
    if not any(
        [args.analyze, args.identify_gaps, args.visualize, args.suggest, args.all]
    ):
        args.all = True

    # 如果指定了 --all，則執行所有功能
    if args.all:
        args.analyze = True
        args.identify_gaps = True
        args.visualize = True
        args.suggest = True

    # 設置輸出目錄
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_dir = os.path.join(RESULTS_DIR, f"coverage_{timestamp}")

    os.makedirs(args.output_dir, exist_ok=True)

    # 執行功能
    coverage_data = {}
    gaps = {}

    if args.analyze:
        coverage_data = run_coverage_analysis(args)

        # 保存覆蓋率數據
        with open(os.path.join(args.output_dir, "coverage_data.json"), "w") as f:
            json.dump(coverage_data, f, indent=2)

    if args.identify_gaps and coverage_data:
        gaps = identify_coverage_gaps(coverage_data)

        # 保存覆蓋率缺口
        with open(os.path.join(args.output_dir, "coverage_gaps.json"), "w") as f:
            json.dump(gaps, f, indent=2)

    if args.visualize and coverage_data:
        vis_dir = generate_coverage_visualization(coverage_data, args)
        logger.info(f"覆蓋率可視化已生成: {vis_dir}")

    if args.suggest and gaps:
        suggestions = suggest_coverage_improvements(gaps)

        # 保存改進建議
        with open(
            os.path.join(args.output_dir, "improvement_suggestions.json"), "w"
        ) as f:
            json.dump(suggestions, f, indent=2)

        # 輸出改進建議
        logger.info("覆蓋率改進建議:")

        if "total" in suggestions:
            logger.info(f"總體: {suggestions['total']['message']}")
            for action in suggestions["total"]["actions"]:
                logger.info(f"  - {action}")

        if "packages" in suggestions:
            logger.info("包級建議:")
            for package_name, package_suggestion in suggestions["packages"].items():
                logger.info(f"  {package_name}: {package_suggestion['message']}")
                for action in package_suggestion["actions"]:
                    logger.info(f"    - {action}")

        if "modules" in suggestions:
            logger.info("模組級建議:")
            for module_name, module_suggestion in suggestions["modules"].items():
                logger.info(f"  {module_name}: {module_suggestion['message']}")
                for action in module_suggestion["actions"]:
                    logger.info(f"    - {action}")

    logger.info(f"所有結果已保存至: {args.output_dir}")


if __name__ == "__main__":
    main()
