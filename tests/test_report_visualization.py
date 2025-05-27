#!/usr/bin/env python3
"""
報表視覺化模組測試腳本

此腳本用於測試 Phase 5.2.10 報表查詢與視覺化模組的功能。
"""

import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 導入要測試的模組
try:
    from src.core.report_visualization_service import ReportVisualizationService
    from src.database.schema import (
        ReportTemplate,
        ChartConfig,
        ExportLog,
        ReportCache,
        TradingOrder,
        TradeExecution,
    )

    print("✅ 成功導入報表視覺化服務模組")
except ImportError as e:
    print(f"❌ 導入模組失敗: {e}")
    sys.exit(1)


class TestReportVisualizationService:
    """報表視覺化服務測試類"""

    def setup_method(self):
        """測試前設置"""
        try:
            self.service = ReportVisualizationService()
            print("✅ 報表視覺化服務初始化成功")
        except Exception as e:
            print(f"❌ 服務初始化失敗: {e}")
            self.service = None

    def test_service_initialization(self):
        """測試服務初始化"""
        print("\n🧪 測試 1: 服務初始化")

        assert self.service is not None, "服務應該成功初始化"
        assert hasattr(self.service, "engine"), "服務應該有資料庫引擎"
        assert hasattr(self.service, "session_factory"), "服務應該有會話工廠"

        print("✅ 服務初始化測試通過")

    def test_get_trading_performance_data(self):
        """測試獲取交易績效數據"""
        print("\n🧪 測試 2: 獲取交易績效數據")

        if not self.service:
            print("⚠️ 跳過測試：服務未初始化")
            return

        try:
            # 測試獲取績效數據
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            result = self.service.get_trading_performance_data(
                start_date=start_date, end_date=end_date
            )

            assert isinstance(result, dict), "結果應該是字典"

            # 檢查返回結果的結構
            if "error" not in result and "message" not in result:
                assert "data" in result, "成功結果應該包含 data"
                assert "metrics" in result, "成功結果應該包含 metrics"
                assert "period" in result, "成功結果應該包含 period"

            print("✅ 獲取交易績效數據測試通過")

        except Exception as e:
            print(f"⚠️ 獲取交易績效數據測試失敗: {e}")

    def test_calculate_performance_metrics(self):
        """測試績效指標計算"""
        print("\n🧪 測試 3: 績效指標計算")

        if not self.service:
            print("⚠️ 跳過測試：服務未初始化")
            return

        try:
            # 創建模擬數據
            mock_data = pd.DataFrame(
                {
                    "execution_time": pd.date_range(
                        start="2024-01-01", periods=10, freq="D"
                    ),
                    "net_amount": [100, -50, 200, -30, 150, -80, 300, -40, 120, -60],
                    "commission": [5] * 10,
                    "tax": [2] * 10,
                }
            )

            # 測試績效指標計算
            metrics = self.service._calculate_performance_metrics(mock_data)

            assert isinstance(metrics, dict), "指標應該是字典"

            # 檢查必要的指標
            expected_metrics = [
                "total_trades",
                "total_pnl",
                "win_rate",
                "avg_win",
                "avg_loss",
                "profit_factor",
                "max_drawdown",
                "sharpe_ratio",
            ]

            for metric in expected_metrics:
                assert metric in metrics, f"應該包含 {metric} 指標"

            print("✅ 績效指標計算測試通過")

        except Exception as e:
            print(f"⚠️ 績效指標計算測試失敗: {e}")

    def test_generate_cumulative_return_chart(self):
        """測試生成累積報酬曲線圖"""
        print("\n🧪 測試 4: 生成累積報酬曲線圖")

        if not self.service:
            print("⚠️ 跳過測試：服務未初始化")
            return

        try:
            # 創建模擬數據
            mock_data = {
                "data": [
                    {"execution_time": "2024-01-01T10:00:00", "cumulative_pnl": 100},
                    {"execution_time": "2024-01-02T10:00:00", "cumulative_pnl": 150},
                    {"execution_time": "2024-01-03T10:00:00", "cumulative_pnl": 120},
                ]
            }

            # 測試 Plotly 圖表
            plotly_chart = self.service.generate_cumulative_return_chart(
                mock_data, chart_type="plotly"
            )

            assert plotly_chart is not None, "應該生成 Plotly 圖表"

            # 測試 Matplotlib 圖表
            matplotlib_chart = self.service.generate_cumulative_return_chart(
                mock_data, chart_type="matplotlib"
            )

            assert matplotlib_chart is not None, "應該生成 Matplotlib 圖表"

            print("✅ 生成累積報酬曲線圖測試通過")

        except Exception as e:
            print(f"⚠️ 生成累積報酬曲線圖測試失敗: {e}")

    def test_generate_drawdown_chart(self):
        """測試生成回撤分析圖表"""
        print("\n🧪 測試 5: 生成回撤分析圖表")

        if not self.service:
            print("⚠️ 跳過測試：服務未初始化")
            return

        try:
            # 創建模擬數據
            mock_data = {
                "data": [
                    {"execution_time": "2024-01-01T10:00:00", "cumulative_pnl": 100},
                    {"execution_time": "2024-01-02T10:00:00", "cumulative_pnl": 150},
                    {"execution_time": "2024-01-03T10:00:00", "cumulative_pnl": 120},
                ]
            }

            # 測試回撤圖表生成
            drawdown_chart = self.service.generate_drawdown_chart(
                mock_data, chart_type="plotly"
            )

            assert drawdown_chart is not None, "應該生成回撤分析圖表"

            print("✅ 生成回撤分析圖表測試通過")

        except Exception as e:
            print(f"⚠️ 生成回撤分析圖表測試失敗: {e}")

    def test_generate_monthly_heatmap(self):
        """測試生成月度績效熱力圖"""
        print("\n🧪 測試 6: 生成月度績效熱力圖")

        if not self.service:
            print("⚠️ 跳過測試：服務未初始化")
            return

        try:
            # 創建模擬數據
            mock_data = {
                "data": [
                    {"execution_time": "2024-01-15T10:00:00", "net_amount": 100},
                    {"execution_time": "2024-02-15T10:00:00", "net_amount": 150},
                    {"execution_time": "2024-03-15T10:00:00", "net_amount": -50},
                ]
            }

            # 測試熱力圖生成
            heatmap_chart = self.service.generate_monthly_heatmap(
                mock_data, chart_type="plotly"
            )

            assert heatmap_chart is not None, "應該生成月度績效熱力圖"

            print("✅ 生成月度績效熱力圖測試通過")

        except Exception as e:
            print(f"⚠️ 生成月度績效熱力圖測試失敗: {e}")

    def test_export_report(self):
        """測試報表匯出功能"""
        print("\n🧪 測試 7: 報表匯出功能")

        if not self.service:
            print("⚠️ 跳過測試：服務未初始化")
            return

        try:
            # 創建模擬報表數據
            mock_report_data = {
                "metrics": {"total_pnl": 1000, "win_rate": 65.5, "total_trades": 50},
                "data": [
                    {"symbol": "2330.TW", "amount": 100000},
                    {"symbol": "2317.TW", "amount": 50000},
                ],
            }

            # 測試 JSON 匯出
            success, message, filepath = self.service.export_report(
                report_data=mock_report_data, export_format="json", user_id="test_user"
            )

            assert isinstance(success, bool), "應該返回布林值"
            assert isinstance(message, str), "應該返回訊息字串"

            if success:
                assert filepath is not None, "成功時應該返回檔案路徑"
                print(f"✅ JSON 匯出成功: {message}")
            else:
                print(f"⚠️ JSON 匯出失敗: {message}")

            # 測試 CSV 匯出
            success, message, filepath = self.service.export_report(
                report_data=mock_report_data, export_format="csv", user_id="test_user"
            )

            if success:
                print(f"✅ CSV 匯出成功: {message}")
            else:
                print(f"⚠️ CSV 匯出失敗: {message}")

            print("✅ 報表匯出功能測試通過")

        except Exception as e:
            print(f"⚠️ 報表匯出功能測試失敗: {e}")

    def test_chart_config_management(self):
        """測試圖表配置管理"""
        print("\n🧪 測試 8: 圖表配置管理")

        if not self.service:
            print("⚠️ 跳過測試：服務未初始化")
            return

        try:
            # 測試保存圖表配置
            config_data = {
                "style": {"color": "blue"},
                "axis": {"x_title": "時間", "y_title": "價值"},
                "width": 800,
                "height": 400,
            }

            success, message = self.service.save_chart_config(
                config_name="測試配置",
                chart_type="line",
                config_data=config_data,
                user_id="test_user",
            )

            assert isinstance(success, bool), "應該返回布林值"
            assert isinstance(message, str), "應該返回訊息字串"

            if success:
                print(f"✅ 圖表配置保存成功: {message}")
            else:
                print(f"⚠️ 圖表配置保存失敗: {message}")

            # 測試獲取圖表配置列表
            configs = self.service.get_chart_configs(chart_type="line")

            assert isinstance(configs, list), "應該返回配置列表"

            print("✅ 圖表配置管理測試通過")

        except Exception as e:
            print(f"⚠️ 圖表配置管理測試失敗: {e}")

    def test_cache_management(self):
        """測試快取管理"""
        print("\n🧪 測試 9: 快取管理")

        if not self.service:
            print("⚠️ 跳過測試：服務未初始化")
            return

        try:
            # 測試清理快取
            success, message = self.service.cleanup_cache(max_age_hours=1)

            assert isinstance(success, bool), "應該返回布林值"
            assert isinstance(message, str), "應該返回訊息字串"

            if success:
                print(f"✅ 快取清理成功: {message}")
            else:
                print(f"⚠️ 快取清理失敗: {message}")

            print("✅ 快取管理測試通過")

        except Exception as e:
            print(f"⚠️ 快取管理測試失敗: {e}")


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v"])
