"""
資料庫查詢優化模組

此模組負責處理資料庫查詢的優化，包括：
- 查詢路由優化
- 分片選擇策略
- 效能分析和建議
- 查詢計劃優化

主要功能：
- 根據查詢條件選擇最佳資料來源
- 分析分片覆蓋率
- 提供查詢效能建議
- 優化跨分片查詢

Example:
    >>> from src.database.query_optimizer import QueryOptimizer
    >>> optimizer = QueryOptimizer(session, sharding_manager)
    >>> optimization = optimizer.optimize_query_performance(MarketDaily, start_date, end_date)
"""

import logging
from datetime import date
from typing import Dict, Any, List, Optional, Type, Union

from src.database.schema import MarketDaily, MarketMinute, MarketTick

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """資料庫查詢優化器.
    
    負責分析查詢條件並提供最佳的查詢策略建議。
    
    Attributes:
        session: SQLAlchemy 會話
        sharding_manager: 分片管理器
    """
    
    def __init__(self, session, sharding_manager) -> None:
        """初始化查詢優化器.
        
        Args:
            session: SQLAlchemy 會話
            sharding_manager: 分片管理器
        """
        self.session = session
        self.sharding_manager = sharding_manager
        
        logger.info("查詢優化器初始化完成")

    def optimize_query_performance(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """優化查詢效能.

        根據查詢條件選擇最佳的資料來源（分片或原始表）。

        Args:
            table_class: 資料表類別
            start_date: 查詢開始日期
            end_date: 查詢結束日期
            symbols: 股票代碼列表

        Returns:
            Dict[str, Any]: 查詢優化建議

        Raises:
            ValueError: 當參數無效時
            RuntimeError: 當優化過程中發生錯誤時
        """
        if start_date > end_date:
            raise ValueError("開始日期不能大於結束日期")

        try:
            logger.info(
                "開始優化查詢效能: %s, %s 到 %s", 
                table_class.__tablename__, start_date, end_date
            )
            
            # 獲取相關分片
            shards = self.sharding_manager.get_shards_for_query(
                table_class, start_date, end_date, symbols
            )

            # 計算查詢範圍
            date_range_days = (end_date - start_date).days + 1

            optimization = self._initialize_optimization_result(
                table_class, date_range_days, len(shards)
            )

            if shards:
                self._analyze_shard_coverage(
                    optimization, shards, start_date, end_date, date_range_days
                )
            else:
                self._handle_no_shards_case(optimization)

            self._generate_optimization_recommendation(optimization)
            
            logger.info(
                "查詢優化完成: 建議策略 %s, 預估效能 %s", 
                optimization["recommendation"], 
                optimization["estimated_performance"]
            )

            return optimization

        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            raise RuntimeError(f"優化查詢效能時發生錯誤: {e}") from e

    def _initialize_optimization_result(
        self, 
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]], 
        date_range_days: int, 
        shard_count: int
    ) -> Dict[str, Any]:
        """初始化優化結果字典.
        
        Args:
            table_class: 資料表類別
            date_range_days: 查詢日期範圍天數
            shard_count: 相關分片數量
            
        Returns:
            Dict[str, Any]: 初始化的優化結果
        """
        return {
            "table_name": table_class.__tablename__,
            "query_date_range_days": date_range_days,
            "available_shards": shard_count,
            "shard_coverage_days": 0,
            "shard_coverage_ratio": 0.0,
            "recommendation": "use_original_table",
            "estimated_performance": "low",
            "optimization_details": {
                "shard_analysis": {},
                "performance_factors": [],
                "alternative_strategies": []
            }
        }

    def _analyze_shard_coverage(
        self, 
        optimization: Dict[str, Any], 
        shards: List, 
        start_date: date, 
        end_date: date, 
        date_range_days: int
    ) -> None:
        """分析分片覆蓋率.
        
        Args:
            optimization: 優化結果字典
            shards: 相關分片列表
            start_date: 查詢開始日期
            end_date: 查詢結束日期
            date_range_days: 查詢日期範圍天數
        """
        shard_coverage_days = 0
        shard_details = []
        
        for shard in shards:
            # 計算分片與查詢範圍的重疊
            shard_start = max(shard.start_date, start_date)
            shard_end = min(shard.end_date, end_date)
            
            if shard_start <= shard_end:
                overlap_days = (shard_end - shard_start).days + 1
                shard_coverage_days += overlap_days
                
                shard_details.append({
                    "shard_id": shard.shard_id,
                    "shard_path": shard.shard_path,
                    "overlap_days": overlap_days,
                    "compression_type": shard.compression_type,
                    "row_count": shard.row_count
                })

        coverage_ratio = shard_coverage_days / date_range_days if date_range_days > 0 else 0
        
        optimization["shard_coverage_days"] = shard_coverage_days
        optimization["shard_coverage_ratio"] = coverage_ratio
        optimization["optimization_details"]["shard_analysis"] = {
            "total_shards": len(shards),
            "covering_shards": len(shard_details),
            "shard_details": shard_details
        }

    def _handle_no_shards_case(self, optimization: Dict[str, Any]) -> None:
        """處理沒有相關分片的情況.
        
        Args:
            optimization: 優化結果字典
        """
        optimization["optimization_details"]["performance_factors"].append(
            "無可用分片，必須使用原始表"
        )
        optimization["optimization_details"]["alternative_strategies"].append(
            "考慮為此查詢範圍創建分片以提升未來查詢效能"
        )

    def _generate_optimization_recommendation(self, optimization: Dict[str, Any]) -> None:
        """生成優化建議.
        
        Args:
            optimization: 優化結果字典
        """
        coverage_ratio = optimization["shard_coverage_ratio"]
        
        if coverage_ratio >= 0.8:  # 80% 以上覆蓋率
            optimization["recommendation"] = "use_shards"
            optimization["estimated_performance"] = "high"
            optimization["optimization_details"]["performance_factors"].extend([
                "高分片覆蓋率，建議使用分片查詢",
                "預期查詢效能顯著提升"
            ])
            
        elif coverage_ratio >= 0.5:  # 50-80% 覆蓋率
            optimization["recommendation"] = "use_hybrid"
            optimization["estimated_performance"] = "medium"
            optimization["optimization_details"]["performance_factors"].extend([
                "中等分片覆蓋率，建議混合查詢策略",
                "部分資料從分片讀取，部分從原始表讀取"
            ])
            optimization["optimization_details"]["alternative_strategies"].append(
                "考慮為未覆蓋的日期範圍創建額外分片"
            )
            
        elif coverage_ratio > 0:  # 0-50% 覆蓋率
            optimization["recommendation"] = "use_original_table"
            optimization["estimated_performance"] = "low"
            optimization["optimization_details"]["performance_factors"].extend([
                "低分片覆蓋率，建議使用原始表查詢",
                "分片查詢的額外開銷可能超過效能收益"
            ])
            optimization["optimization_details"]["alternative_strategies"].extend([
                "考慮為此查詢範圍創建完整分片",
                "評估是否需要調整分片策略"
            ])
            
        else:  # 無覆蓋率
            optimization["recommendation"] = "use_original_table"
            optimization["estimated_performance"] = "baseline"
            optimization["optimization_details"]["performance_factors"].append(
                "無分片覆蓋，使用原始表查詢"
            )

    def analyze_query_patterns(
        self, 
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]], 
        query_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析查詢模式並提供分片策略建議.
        
        Args:
            table_class: 資料表類別
            query_history: 查詢歷史記錄
            
        Returns:
            Dict[str, Any]: 查詢模式分析結果
        """
        if not query_history:
            return {
                "pattern_analysis": "無查詢歷史資料",
                "sharding_recommendations": []
            }
        
        # 分析查詢日期範圍模式
        date_ranges = []
        symbol_patterns = {}
        
        for query in query_history:
            if "start_date" in query and "end_date" in query:
                range_days = (query["end_date"] - query["start_date"]).days + 1
                date_ranges.append(range_days)
            
            if "symbols" in query and query["symbols"]:
                for symbol in query["symbols"]:
                    symbol_patterns[symbol] = symbol_patterns.get(symbol, 0) + 1
        
        # 計算統計
        avg_range = sum(date_ranges) / len(date_ranges) if date_ranges else 0
        most_queried_symbols = sorted(
            symbol_patterns.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        # 生成建議
        recommendations = []
        
        if avg_range <= 7:
            recommendations.append("查詢多為短期範圍，建議使用週級分片")
        elif avg_range <= 30:
            recommendations.append("查詢多為中期範圍，建議使用月級分片")
        else:
            recommendations.append("查詢多為長期範圍，建議使用季度級分片")
        
        if most_queried_symbols:
            top_symbols = [symbol for symbol, _ in most_queried_symbols[:5]]
            recommendations.append(
                f"高頻查詢股票 {top_symbols}，考慮為這些股票創建專用分片"
            )
        
        return {
            "pattern_analysis": {
                "total_queries": len(query_history),
                "average_date_range_days": avg_range,
                "most_queried_symbols": most_queried_symbols,
                "date_range_distribution": {
                    "short_term": len([r for r in date_ranges if r <= 7]),
                    "medium_term": len([r for r in date_ranges if 7 < r <= 30]),
                    "long_term": len([r for r in date_ranges if r > 30])
                }
            },
            "sharding_recommendations": recommendations
        }

    def estimate_query_cost(
        self, 
        optimization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """估算查詢成本.
        
        Args:
            optimization: 優化結果字典
            
        Returns:
            Dict[str, Any]: 查詢成本估算
        """
        base_cost = optimization["query_date_range_days"] * 100  # 基礎成本
        
        if optimization["recommendation"] == "use_shards":
            # 分片查詢成本較低
            estimated_cost = base_cost * 0.3
            cost_factors = ["使用壓縮分片，I/O 成本降低", "索引優化，查詢速度提升"]
            
        elif optimization["recommendation"] == "use_hybrid":
            # 混合查詢成本中等
            estimated_cost = base_cost * 0.6
            cost_factors = ["部分使用分片，部分使用原始表", "需要額外的資料合併成本"]
            
        else:
            # 原始表查詢成本較高
            estimated_cost = base_cost
            cost_factors = ["全表掃描，I/O 成本較高", "無壓縮優化"]
        
        return {
            "estimated_cost": estimated_cost,
            "cost_unit": "相對成本單位",
            "cost_factors": cost_factors,
            "optimization_potential": max(0, base_cost - estimated_cost)
        }
