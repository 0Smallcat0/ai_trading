# -*- coding: utf-8 -*-
"""數據源路由器

此模組實現智能數據源路由和備援機制，包括：
- 數據源選擇和優先級管理
- 自動故障轉移和備援切換
- 多數據源數據融合和去重
- 數據質量評估和選擇
- 性能監控和統計

主要功能：
- 根據數據類型和市場選擇最佳數據源
- 實現多數據源備援機制
- 數據質量評估和自動切換
- API 限制管理和負載均衡
- 數據融合和去重處理

Example:
    >>> router = DataSourceRouter(adapters)
    >>> response = await router.route_request(request)
    >>> merged_data = router.merge_data_sources([data1, data2])
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

from .base_data_source import BaseDataSource

# 設定日誌
logger = logging.getLogger(__name__)


class DataSourcePriority(Enum):
    """數據源優先級"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class DataSourcePerformance:
    """數據源性能統計"""
    success_count: int = 0
    failure_count: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    quality_score: float = 1.0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.success_count / self.total_requests
    
    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.success_rate >= 0.8 and self.quality_score >= 0.7


class DataSourceRouter:
    """數據源路由器
    
    負責智能選擇數據源、實現備援機制和數據融合。
    
    Attributes:
        adapters: 數據源適配器字典
        priorities: 數據源優先級配置
        performance_stats: 性能統計
        fallback_chains: 備援鏈配置
        
    Example:
        >>> adapters = {
        ...     'tushare': tushare_adapter,
        ...     'baostock': baostock_adapter,
        ...     'qstock': qstock_adapter
        ... }
        >>> router = DataSourceRouter(adapters)
        >>> data = await router.get_data(request)
    """
    
    def __init__(self, adapters: Dict[str, BaseDataSource]):
        """初始化數據源路由器
        
        Args:
            adapters: 數據源適配器字典
        """
        self.adapters = adapters
        self.performance_stats = {
            name: DataSourcePerformance() 
            for name in adapters.keys()
        }
        
        # 配置數據源優先級
        self.priorities = self._configure_priorities()
        
        # 配置備援鏈
        self.fallback_chains = self._configure_fallback_chains()
        
        # 數據融合配置
        self.merge_strategies = {
            'daily_data': self._merge_daily_data,
            'realtime_data': self._merge_realtime_data,
            'basic_info': self._merge_basic_info
        }
        
        logger.info(f"數據源路由器初始化完成，管理 {len(adapters)} 個數據源")
    
    def _configure_priorities(self) -> Dict[str, Dict[str, DataSourcePriority]]:
        """配置數據源優先級
        
        Returns:
            優先級配置字典
        """
        return {
            'daily_data': {
                'tushare': DataSourcePriority.HIGH,
                'baostock': DataSourcePriority.MEDIUM,
                'qstock': DataSourcePriority.LOW,
                'yahoo': DataSourcePriority.MEDIUM
            },
            'realtime_data': {
                'tushare': DataSourcePriority.HIGH,
                'qstock': DataSourcePriority.MEDIUM,
                'yahoo': DataSourcePriority.MEDIUM,
                'baostock': DataSourcePriority.LOW  # BaoStock 不支援實時數據
            },
            'basic_info': {
                'tushare': DataSourcePriority.HIGH,
                'baostock': DataSourcePriority.MEDIUM,
                'qstock': DataSourcePriority.LOW
            }
        }
    
    def _configure_fallback_chains(self) -> Dict[str, List[str]]:
        """配置備援鏈
        
        Returns:
            備援鏈配置
        """
        return {
            'a_stock_daily': ['tushare', 'baostock', 'qstock'],
            'a_stock_realtime': ['tushare', 'qstock'],
            'hk_stock': ['tushare', 'yahoo'],
            'us_stock': ['yahoo', 'tushare'],
            'basic_info': ['tushare', 'baostock']
        }
    
    async def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """路由數據請求
        
        Args:
            request: 數據請求
                - data_type: 數據類型 ('daily_data', 'realtime_data', 'basic_info')
                - symbols: 股票代碼列表
                - start_date: 開始日期
                - end_date: 結束日期
                - market: 市場類型 ('a_stock', 'hk_stock', 'us_stock')
                
        Returns:
            數據響應
        """
        data_type = request.get('data_type', 'daily_data')
        market = request.get('market', 'a_stock')
        
        # 選擇備援鏈
        fallback_key = f"{market}_{data_type.replace('_data', '')}"
        fallback_chain = self.fallback_chains.get(fallback_key, ['tushare', 'baostock'])
        
        # 按優先級排序
        sorted_sources = self._sort_sources_by_priority(fallback_chain, data_type)
        
        # 嘗試獲取數據
        for source_name in sorted_sources:
            if source_name not in self.adapters:
                continue
                
            adapter = self.adapters[source_name]
            
            try:
                # 檢查數據源可用性
                if not adapter.is_available():
                    logger.warning(f"數據源 {source_name} 不可用")
                    continue
                
                # 檢查 API 限制
                if hasattr(adapter, 'points_manager'):
                    if not adapter.points_manager.can_make_request():
                        logger.warning(f"數據源 {source_name} API 限制")
                        continue
                
                # 獲取數據
                start_time = time.time()
                data = await self._fetch_data_from_source(adapter, request)
                response_time = time.time() - start_time
                
                if data is not None and not data.empty:
                    # 更新性能統計
                    self._update_performance_stats(source_name, True, response_time, data)
                    
                    return {
                        'data': data,
                        'source': source_name,
                        'response_time': response_time,
                        'quality_score': self._calculate_data_quality(data)
                    }
                else:
                    logger.warning(f"數據源 {source_name} 返回空數據")
                    
            except Exception as e:
                logger.error(f"數據源 {source_name} 請求失敗: {e}")
                self._update_performance_stats(source_name, False, 0, None)
                continue
        
        raise RuntimeError("所有數據源都不可用")
    
    async def get_merged_data(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """獲取融合數據
        
        從多個數據源獲取數據並進行融合處理。
        
        Args:
            request: 數據請求
            
        Returns:
            融合後的數據響應
        """
        data_type = request.get('data_type', 'daily_data')
        market = request.get('market', 'a_stock')
        
        # 選擇多個數據源
        fallback_key = f"{market}_{data_type.replace('_data', '')}"
        sources = self.fallback_chains.get(fallback_key, ['tushare', 'baostock'])[:2]  # 最多使用2個源
        
        # 並行獲取數據
        tasks = []
        for source_name in sources:
            if source_name in self.adapters:
                task = self._safe_fetch_data(source_name, request)
                tasks.append(task)
        
        if not tasks:
            raise RuntimeError("沒有可用的數據源")
        
        # 等待所有任務完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 過濾有效結果
        valid_results = []
        for i, result in enumerate(results):
            if not isinstance(result, Exception) and result is not None:
                valid_results.append({
                    'data': result,
                    'source': sources[i],
                    'quality': self._calculate_data_quality(result)
                })
        
        if not valid_results:
            raise RuntimeError("所有數據源都返回無效數據")
        
        # 數據融合
        merge_strategy = self.merge_strategies.get(data_type, self._merge_default)
        merged_data = merge_strategy(valid_results)
        
        return {
            'data': merged_data,
            'sources': [r['source'] for r in valid_results],
            'quality_scores': {r['source']: r['quality'] for r in valid_results}
        }
    
    async def _safe_fetch_data(self, source_name: str, request: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """安全獲取數據"""
        try:
            adapter = self.adapters[source_name]
            if adapter.is_available():
                return await self._fetch_data_from_source(adapter, request)
        except Exception as e:
            logger.warning(f"從 {source_name} 獲取數據失敗: {e}")
        return None
    
    async def _fetch_data_from_source(self, adapter: BaseDataSource, request: Dict[str, Any]) -> pd.DataFrame:
        """從指定數據源獲取數據"""
        data_type = request.get('data_type', 'daily_data')
        
        if data_type == 'daily_data':
            return await adapter.get_daily_data(
                symbol=request['symbols'][0],  # 簡化處理，取第一個符號
                start_date=request.get('start_date'),
                end_date=request.get('end_date')
            )
        elif data_type == 'realtime_data':
            return await adapter.get_realtime_data(request['symbols'])
        else:
            raise ValueError(f"不支援的數據類型: {data_type}")
    
    def _sort_sources_by_priority(self, sources: List[str], data_type: str) -> List[str]:
        """按優先級排序數據源"""
        priorities = self.priorities.get(data_type, {})
        
        def get_priority_score(source: str) -> Tuple[int, float, float]:
            # 優先級、成功率、質量評分
            priority = priorities.get(source, DataSourcePriority.LOW).value
            stats = self.performance_stats.get(source, DataSourcePerformance())
            return (priority, -stats.success_rate, -stats.quality_score)
        
        return sorted(sources, key=get_priority_score)
    
    def _merge_daily_data(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """融合日線數據"""
        if len(results) == 1:
            return results[0]['data']
        
        # 按質量評分排序
        results.sort(key=lambda x: x['quality'], reverse=True)
        
        primary_data = results[0]['data']
        
        # 用其他數據源填補缺失值
        for result in results[1:]:
            secondary_data = result['data']
            primary_data = self._fill_missing_data(primary_data, secondary_data)
        
        return primary_data
    
    def _merge_realtime_data(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """融合實時數據"""
        if len(results) == 1:
            return results[0]['data']
        
        # 實時數據取最新的
        latest_result = max(results, key=lambda x: x['quality'])
        return latest_result['data']
    
    def _merge_basic_info(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """融合基本信息"""
        if len(results) == 1:
            return results[0]['data']
        
        # 合併所有基本信息
        all_data = []
        for result in results:
            all_data.append(result['data'])
        
        merged = pd.concat(all_data, ignore_index=True)
        return merged.drop_duplicates(subset=['symbol'], keep='first')
    
    def _merge_default(self, results: List[Dict[str, Any]]) -> pd.DataFrame:
        """默認融合策略"""
        return self._merge_daily_data(results)
    
    def _fill_missing_data(self, primary: pd.DataFrame, secondary: pd.DataFrame) -> pd.DataFrame:
        """用次要數據填補主要數據的缺失值"""
        if primary.empty:
            return secondary
        if secondary.empty:
            return primary
        
        # 按日期合併
        if 'date' in primary.columns and 'date' in secondary.columns:
            merged = primary.set_index('date').combine_first(secondary.set_index('date'))
            return merged.reset_index()
        
        return primary
    
    def _calculate_data_quality(self, data: pd.DataFrame) -> float:
        """計算數據質量評分"""
        if data.empty:
            return 0.0
        
        quality_score = 1.0
        
        # 檢查缺失值
        missing_ratio = data.isnull().sum().sum() / (data.shape[0] * data.shape[1])
        quality_score -= missing_ratio * 0.4
        
        # 檢查數據完整性
        if 'date' in data.columns and len(data) > 1:
            date_range = (data['date'].max() - data['date'].min()).days
            expected_days = date_range
            actual_days = len(data)
            completeness = min(1.0, actual_days / max(expected_days, 1))
            quality_score *= completeness
        
        return max(0.0, quality_score)
    
    def _update_performance_stats(
        self, 
        source_name: str, 
        success: bool, 
        response_time: float,
        data: Optional[pd.DataFrame]
    ):
        """更新性能統計"""
        stats = self.performance_stats[source_name]
        stats.total_requests += 1
        
        if success:
            stats.success_count += 1
            stats.last_success_time = datetime.now()
            
            # 更新平均響應時間
            if stats.avg_response_time == 0:
                stats.avg_response_time = response_time
            else:
                stats.avg_response_time = (stats.avg_response_time * 0.8 + response_time * 0.2)
            
            # 更新質量評分
            if data is not None:
                quality = self._calculate_data_quality(data)
                stats.quality_score = stats.quality_score * 0.8 + quality * 0.2
        else:
            stats.failure_count += 1
            stats.last_failure_time = datetime.now()
    
    def get_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """獲取性能統計"""
        return {
            name: {
                'success_rate': stats.success_rate,
                'avg_response_time': stats.avg_response_time,
                'quality_score': stats.quality_score,
                'is_healthy': stats.is_healthy,
                'total_requests': stats.total_requests,
                'last_success': stats.last_success_time.isoformat() if stats.last_success_time else None,
                'last_failure': stats.last_failure_time.isoformat() if stats.last_failure_time else None
            }
            for name, stats in self.performance_stats.items()
        }
    
    def get_recommended_source(self, data_type: str, market: str = 'a_stock') -> str:
        """獲取推薦的數據源
        
        Args:
            data_type: 數據類型
            market: 市場類型
            
        Returns:
            推薦的數據源名稱
        """
        fallback_key = f"{market}_{data_type.replace('_data', '')}"
        sources = self.fallback_chains.get(fallback_key, ['tushare'])
        sorted_sources = self._sort_sources_by_priority(sources, data_type)
        
        for source in sorted_sources:
            if source in self.adapters and self.adapters[source].is_available():
                stats = self.performance_stats[source]
                if stats.is_healthy:
                    return source
        
        return sorted_sources[0] if sorted_sources else 'tushare'
