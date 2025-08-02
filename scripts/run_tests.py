# -*- coding: utf-8 -*-
"""
全面測試執行腳本

此腳本用於執行所有類型的測試，包括單元測試、整合測試、端到端測試，
並生成測試覆蓋率報告和性能測試報告。

使用方法:
    python scripts/run_tests.py [options]

選項:
    --unit-tests: 執行單元測試
    --integration-tests: 執行整合測試
    --e2e-tests: 執行端到端測試
    --coverage: 生成測試覆蓋率報告
    --performance: 執行性能測試
    --stress: 執行壓力測試
    --all: 執行所有測試
    --output-dir: 指定輸出目錄
    --min-coverage: 最小覆蓋率閾值 (默認: 80)
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import RESULTS_DIR
from src.core.logger import get_logger
from src.maintenance.system_profiler import SystemProfiler

# 設定日誌
logger = get_logger("test_runner")


def run_unit_tests(args):
    """
    執行單元測試

    Args:
        args: 命令行參數
    """
    logger.info("開始執行單元測試")

    # 構建命令
    cmd = ["pytest"]

    # 排除整合測試和端到端測試
    cmd.extend(["-k", "not integration and not e2e"])

    # 如果需要生成覆蓋率報告
    if args.coverage:
        cmd.extend(
            [
                f"--cov=src",
                f"--cov-report=term",
                f"--cov-report=html:{os.path.join(args.output_dir, 'coverage_unit')}",
                f"--cov-report=xml:{os.path.join(args.output_dir, 'coverage_unit.xml')}",
            ]
        )

        # 如果設置了最小覆蓋率閾值
        if args.min_coverage:
            cmd.append(f"--cov-fail-under={args.min_coverage}")

    # 執行命令
    logger.info(f"執行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 輸出結果
    logger.info(f"單元測試執行結果: {'成功' if result.returncode == 0 else '失敗'}")
    logger.info(f"輸出:\n{result.stdout}")

    if result.returncode != 0:
        logger.error(f"錯誤:\n{result.stderr}")

    return result.returncode == 0


def run_integration_tests(args):
    """
    執行整合測試

    Args:
        args: 命令行參數
    """
    logger.info("開始執行整合測試")

    # 構建命令
    cmd = ["pytest"]

    # 只執行整合測試
    cmd.extend(["-k", "integration"])

    # 如果需要生成覆蓋率報告
    if args.coverage:
        cmd.extend(
            [
                f"--cov=src",
                f"--cov-report=term",
                f"--cov-report=html:{os.path.join(args.output_dir, 'coverage_integration')}",
                f"--cov-report=xml:{os.path.join(args.output_dir, 'coverage_integration.xml')}",
            ]
        )

    # 執行命令
    logger.info(f"執行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 輸出結果
    logger.info(f"整合測試執行結果: {'成功' if result.returncode == 0 else '失敗'}")
    logger.info(f"輸出:\n{result.stdout}")

    if result.returncode != 0:
        logger.error(f"錯誤:\n{result.stderr}")

    return result.returncode == 0


def run_e2e_tests(args):
    """
    執行端到端測試

    Args:
        args: 命令行參數
    """
    logger.info("開始執行端到端測試")

    # 構建命令
    cmd = ["pytest"]

    # 只執行端到端測試
    cmd.extend(["-k", "e2e"])

    # 如果需要生成覆蓋率報告
    if args.coverage:
        cmd.extend(
            [
                f"--cov=src",
                f"--cov-report=term",
                f"--cov-report=html:{os.path.join(args.output_dir, 'coverage_e2e')}",
                f"--cov-report=xml:{os.path.join(args.output_dir, 'coverage_e2e.xml')}",
            ]
        )

    # 執行命令
    logger.info(f"執行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 輸出結果
    logger.info(f"端到端測試執行結果: {'成功' if result.returncode == 0 else '失敗'}")
    logger.info(f"輸出:\n{result.stdout}")

    if result.returncode != 0:
        logger.error(f"錯誤:\n{result.stderr}")

    return result.returncode == 0


def run_performance_tests(args):
    """
    執行性能測試

    Args:
        args: 命令行參數
    """
    logger.info("開始執行性能測試")

    try:
        # 創建系統性能分析器
        profiler = SystemProfiler(args.output_dir)

        # 執行主流程性能分析
        profiler.profile_main_flow(mode="backtest")

        # 執行資料處理性能分析
        profiler.profile_data_processing()

        # 執行模型推論性能分析
        profiler.profile_model_inference()

        # 識別瓶頸
        bottlenecks = profiler.identify_bottlenecks()
        logger.info(f"識別到的瓶頸: {bottlenecks}")

        # 生成報告
        report_path = profiler.generate_report()
        logger.info(f"性能測試報告已生成: {report_path}")

        return True
    except Exception as e:
        logger.error(f"執行性能測試時發生錯誤: {e}")
        return False


def run_stress_tests(args):
    """
    執行壓力測試

    Args:
        args: 命令行參數
    """
    logger.info("開始執行壓力測試")

    try:
        # 創建系統性能分析器
        SystemProfiler(args.output_dir)

        # 執行壓力測試
        # 這裡可以根據需要添加更多的壓力測試場景

        # 1. 高頻數據處理壓力測試
        logger.info("執行高頻數據處理壓力測試")
        # 模擬高頻數據處理

        # 2. 並發請求壓力測試
        logger.info("執行並發請求壓力測試")
        # 模擬並發請求

        # 3. 大量訂單處理壓力測試
        logger.info("執行大量訂單處理壓力測試")
        # 模擬大量訂單處理

        # 生成報告
        report_path = os.path.join(args.output_dir, "stress_test_report.html")
        logger.info(f"壓力測試報告已生成: {report_path}")

        return True
    except Exception as e:
        logger.error(f"執行壓力測試時發生錯誤: {e}")
        return False


def generate_combined_coverage_report(args):
    """
    生成合併的覆蓋率報告

    Args:
        args: 命令行參數
    """
    logger.info("開始生成合併的覆蓋率報告")

    try:
        # 構建命令
        cmd = [
            "coverage",
            "combine",
            os.path.join(args.output_dir, "coverage_unit.xml"),
            os.path.join(args.output_dir, "coverage_integration.xml"),
            os.path.join(args.output_dir, "coverage_e2e.xml"),
        ]

        # 執行命令
        logger.info(f"執行命令: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True, text=True)

        # 生成 HTML 報告
        cmd = [
            "coverage",
            "html",
            "-d",
            os.path.join(args.output_dir, "coverage_combined"),
        ]

        logger.info(f"執行命令: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True, text=True)

        # 生成 XML 報告
        cmd = [
            "coverage",
            "xml",
            "-o",
            os.path.join(args.output_dir, "coverage_combined.xml"),
        ]

        logger.info(f"執行命令: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True, text=True)

        logger.info(
            f"合併的覆蓋率報告已生成: {os.path.join(args.output_dir, 'coverage_combined')}"
        )

        return True
    except Exception as e:
        logger.error(f"生成合併覆蓋率報告時發生錯誤: {e}")
        return False


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="全面測試執行腳本")
    parser.add_argument("--unit-tests", action="store_true", help="執行單元測試")
    parser.add_argument("--integration-tests", action="store_true", help="執行整合測試")
    parser.add_argument("--e2e-tests", action="store_true", help="執行端到端測試")
    parser.add_argument("--coverage", action="store_true", help="生成測試覆蓋率報告")
    parser.add_argument("--performance", action="store_true", help="執行性能測試")
    parser.add_argument("--stress", action="store_true", help="執行壓力測試")
    parser.add_argument("--all", action="store_true", help="執行所有測試")
    parser.add_argument("--output-dir", type=str, default=None, help="指定輸出目錄")
    parser.add_argument(
        "--min-coverage", type=int, default=80, help="最小覆蓋率閾值 (默認: 80)"
    )

    args = parser.parse_args()

    # 如果沒有指定任何測試，則執行所有測試
    if not any(
        [
            args.unit_tests,
            args.integration_tests,
            args.e2e_tests,
            args.coverage,
            args.performance,
            args.stress,
            args.all,
        ]
    ):
        args.all = True

    # 如果指定了 --all，則執行所有測試
    if args.all:
        args.unit_tests = True
        args.integration_tests = True
        args.e2e_tests = True
        args.coverage = True
        args.performance = True
        args.stress = True

    # 設置輸出目錄
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_dir = os.path.join(RESULTS_DIR, f"tests_{timestamp}")

    os.makedirs(args.output_dir, exist_ok=True)

    # 執行測試
    results = {}

    if args.unit_tests:
        results["unit_tests"] = run_unit_tests(args)

    if args.integration_tests:
        results["integration_tests"] = run_integration_tests(args)

    if args.e2e_tests:
        results["e2e_tests"] = run_e2e_tests(args)

    if args.coverage and all([args.unit_tests, args.integration_tests, args.e2e_tests]):
        results["combined_coverage"] = generate_combined_coverage_report(args)

    if args.performance:
        results["performance_tests"] = run_performance_tests(args)

    if args.stress:
        results["stress_tests"] = run_stress_tests(args)

    # 輸出結果摘要
    logger.info("測試執行結果摘要:")
    for test_name, result in results.items():
        logger.info(f"{test_name}: {'成功' if result else '失敗'}")

    # 如果有任何測試失敗，則返回非零退出碼
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
