"""
資料驗證模組

此模組提供資料驗證功能，用於確保資料的品質和完整性。
包括時間序列連續性檢查、缺失值檢查、異常值檢查等。

主要功能：
- 時間序列連續性檢查
- 缺失值檢查和報告
- 異常值檢測和標記
- 資料類型和範圍驗證
- 資料完整性驗證（使用校驗碼）
"""

import hashlib
import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session


# 自定義 JSON 編碼器，處理日期、時間和 DataFrame 類型
class CustomJSONEncoder(json.JSONEncoder):
    """
    CustomJSONEncoder

    """

    def default(self, obj):
        """
        default

        Args:
            obj:
        """
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)


from src.config import LOG_LEVEL
from src.database.schema import DataChecksum, MarketDaily, MarketMinute, SystemLog

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class DataValidator:
    """
    資料驗證器

    提供各種資料驗證功能，確保資料的品質和完整性。
    """

    def __init__(self, session: Session):
        """
        初始化資料驗證器

        Args:
            session: SQLAlchemy 會話
        """
        self.session = session
        self.validation_results = {}

    def validate_time_series_continuity(
        self, table_class, symbol: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        驗證時間序列的連續性

        檢查指定時間範圍內的資料是否有缺失的日期或時間點。

        Args:
            table_class: 資料表類別 (MarketDaily, MarketMinute, MarketTick)
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, Any]: 驗證結果，包含是否連續、缺失的日期等
        """
        # 根據資料表類別選擇日期欄位
        if table_class == MarketDaily:
            table_class.date
            # 生成預期的日期範圍（僅工作日）
            expected_dates = self._generate_trading_dates(start_date, end_date)

            # 查詢實際的日期
            query = (
                select(table_class.date)
                .where(
                    and_(
                        table_class.symbol == symbol,
                        table_class.date >= start_date,
                        table_class.date <= end_date,
                    )
                )
                .order_by(table_class.date)
            )
            actual_dates = [row[0] for row in self.session.execute(query).fetchall()]

            # 找出缺失的日期
            missing_dates = sorted(set(expected_dates) - set(actual_dates))

            # 計算連續性指標
            continuity = (
                1.0 - (len(missing_dates) / len(expected_dates))
                if expected_dates
                else 1.0
            )

            result = {
                "is_continuous": len(missing_dates) == 0,
                "continuity_score": continuity,
                "missing_dates": missing_dates,
                "expected_count": len(expected_dates),
                "actual_count": len(actual_dates),
            }
        else:
            # 對於分鐘和 Tick 資料，檢查時間間隔
            table_class.timestamp

            # 查詢實際的時間戳
            query = (
                select(table_class.timestamp)
                .where(
                    and_(
                        table_class.symbol == symbol,
                        func.date(table_class.timestamp) >= start_date,
                        func.date(table_class.timestamp) <= end_date,
                    )
                )
                .order_by(table_class.timestamp)
            )
            timestamps = [row[0] for row in self.session.execute(query).fetchall()]

            if not timestamps:
                return {
                    "is_continuous": False,
                    "continuity_score": 0.0,
                    "missing_intervals": [],
                    "expected_count": 0,
                    "actual_count": 0,
                }

            # 檢查時間間隔
            if table_class == MarketMinute:
                # 對於分鐘資料，檢查是否有缺失的分鐘
                expected_interval = timedelta(minutes=1)
            else:
                # 對於 Tick 資料，我們不能假設固定的時間間隔
                # 只檢查是否有異常大的間隔
                intervals = [
                    (timestamps[i + 1] - timestamps[i]).total_seconds()
                    for i in range(len(timestamps) - 1)
                ]
                if not intervals:
                    return {
                        "is_continuous": True,
                        "continuity_score": 1.0,
                        "missing_intervals": [],
                        "expected_count": 1,
                        "actual_count": 1,
                    }

                avg_interval = sum(intervals) / len(intervals)
                std_interval = np.std(intervals)
                threshold = avg_interval + 3 * std_interval

                large_intervals = [
                    (timestamps[i], timestamps[i + 1], intervals[i])
                    for i in range(len(intervals))
                    if intervals[i] > threshold
                ]

                continuity = (
                    1.0 - (len(large_intervals) / len(intervals)) if intervals else 1.0
                )

                return {
                    "is_continuous": len(large_intervals) == 0,
                    "continuity_score": continuity,
                    "large_intervals": large_intervals,
                    "avg_interval": avg_interval,
                    "std_interval": std_interval,
                    "threshold": threshold,
                    "actual_count": len(timestamps),
                }

            # 對於分鐘資料，檢查是否有缺失的分鐘
            missing_intervals = []
            for i in range(len(timestamps) - 1):
                interval = timestamps[i + 1] - timestamps[i]
                if interval > expected_interval:
                    missing_intervals.append(
                        (timestamps[i], timestamps[i + 1], interval.total_seconds())
                    )

            # 計算連續性指標
            total_intervals = len(timestamps) - 1
            continuity = (
                1.0 - (len(missing_intervals) / total_intervals)
                if total_intervals > 0
                else 1.0
            )

            result = {
                "is_continuous": len(missing_intervals) == 0,
                "continuity_score": continuity,
                "missing_intervals": missing_intervals,
                "expected_interval": expected_interval.total_seconds(),
                "actual_count": len(timestamps),
            }

        # 儲存驗證結果
        key = f"{table_class.__tablename__}_{symbol}_{start_date}_{end_date}"
        self.validation_results[key] = result

        return result

    def check_missing_values(
        self, table_class, symbol: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        檢查缺失值

        檢查指定時間範圍內的資料是否有缺失值。

        Args:
            table_class: 資料表類別 (MarketDaily, MarketMinute, MarketTick)
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, Any]: 檢查結果，包含缺失值的欄位和比例
        """
        # 根據資料表類別選擇日期欄位和查詢條件
        if table_class == MarketDaily:
            table_class.date
            query = select(table_class).where(
                and_(
                    table_class.symbol == symbol,
                    table_class.date >= start_date,
                    table_class.date <= end_date,
                )
            )
        else:
            table_class.timestamp
            query = select(table_class).where(
                and_(
                    table_class.symbol == symbol,
                    func.date(table_class.timestamp) >= start_date,
                    func.date(table_class.timestamp) <= end_date,
                )
            )

        # 執行查詢並轉換為 DataFrame
        from src.database.parquet_utils import query_to_dataframe

        df = query_to_dataframe(self.session, query)

        if df.empty:
            return {
                "has_missing": False,
                "missing_counts": {},
                "missing_percentages": {},
                "total_rows": 0,
            }

        # 計算每個欄位的缺失值數量和比例
        missing_counts = df.isnull().sum().to_dict()
        missing_percentages = (df.isnull().sum() / len(df) * 100).to_dict()

        # 過濾掉沒有缺失值的欄位
        missing_counts = {k: v for k, v in missing_counts.items() if v > 0}
        missing_percentages = {k: v for k, v in missing_percentages.items() if v > 0}

        result = {
            "has_missing": bool(missing_counts),
            "missing_counts": missing_counts,
            "missing_percentages": missing_percentages,
            "total_rows": len(df),
        }

        # 儲存驗證結果
        key = f"missing_{table_class.__tablename__}_{symbol}_{start_date}_{end_date}"
        self.validation_results[key] = result

        return result

    def detect_outliers(
        self,
        table_class,
        symbol: str,
        start_date: date,
        end_date: date,
        method: str = "zscore",
        threshold: float = 3.0,
    ) -> Dict[str, Any]:
        """
        檢測異常值

        使用統計方法檢測指定時間範圍內的異常值。

        Args:
            table_class: 資料表類別 (MarketDaily, MarketMinute, MarketTick)
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            method: 檢測方法，可選 "zscore" 或 "iqr"
            threshold: 閾值，對於 zscore 方法表示標準差的倍數，對於 iqr 方法表示四分位距的倍數

        Returns:
            Dict[str, Any]: 檢測結果，包含異常值的欄位和數量
        """
        # 根據資料表類別選擇日期欄位和查詢條件
        if table_class == MarketDaily:
            table_class.date
            query = select(table_class).where(
                and_(
                    table_class.symbol == symbol,
                    table_class.date >= start_date,
                    table_class.date <= end_date,
                )
            )
        else:
            table_class.timestamp
            query = select(table_class).where(
                and_(
                    table_class.symbol == symbol,
                    func.date(table_class.timestamp) >= start_date,
                    func.date(table_class.timestamp) <= end_date,
                )
            )

        # 執行查詢並轉換為 DataFrame
        from src.database.parquet_utils import query_to_dataframe

        df = query_to_dataframe(self.session, query)

        if df.empty:
            return {
                "has_outliers": False,
                "outlier_counts": {},
                "outlier_percentages": {},
                "total_rows": 0,
            }

        # 只檢查數值型欄位
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

        outliers = {}
        outlier_indices = set()

        for col in numeric_cols:
            col_outliers = set()

            if method == "zscore":
                # Z-score 方法
                mean = df[col].mean()
                std = df[col].std()
                if std == 0:  # 避免除以零
                    continue

                z_scores = (df[col] - mean) / std
                col_outliers = set(df.index[abs(z_scores) > threshold].tolist())

            elif method == "iqr":
                # IQR 方法
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                if iqr == 0:  # 避免除以零
                    continue

                lower_bound = q1 - threshold * iqr
                upper_bound = q3 + threshold * iqr

                col_outliers = set(
                    df.index[(df[col] < lower_bound) | (df[col] > upper_bound)].tolist()
                )

            outliers[col] = col_outliers
            outlier_indices.update(col_outliers)

        # 計算每個欄位的異常值數量和比例
        outlier_counts = {
            col: len(indices) for col, indices in outliers.items() if indices
        }
        outlier_percentages = {
            col: len(indices) / len(df) * 100
            for col, indices in outliers.items()
            if indices
        }

        # 獲取異常值的資料
        outlier_data = (
            df.loc[list(outlier_indices)] if outlier_indices else pd.DataFrame()
        )

        result = {
            "has_outliers": bool(outlier_indices),
            "outlier_counts": outlier_counts,
            "outlier_percentages": outlier_percentages,
            "total_outliers": len(outlier_indices),
            "total_rows": len(df),
            "outlier_data": outlier_data,
        }

        # 儲存驗證結果
        key = f"outliers_{table_class.__tablename__}_{symbol}_{start_date}_{end_date}"
        self.validation_results[key] = result

        return result

    def verify_data_integrity(self, table_class, record_id: int) -> Dict[str, Any]:
        """
        驗證資料完整性

        使用校驗碼驗證資料的完整性。

        Args:
            table_class: 資料表類別
            record_id: 記錄 ID

        Returns:
            Dict[str, Any]: 驗證結果
        """
        # 查詢記錄
        record = self.session.query(table_class).filter_by(id=record_id).first()
        if not record:
            return {
                "is_valid": False,
                "error": f"找不到記錄: {table_class.__tablename__} ID={record_id}",
            }

        # 查詢校驗記錄
        checksum_record = (
            self.session.query(DataChecksum)
            .filter_by(table_name=table_class.__tablename__, record_id=record_id)
            .first()
        )

        if not checksum_record:
            return {
                "is_valid": False,
                "error": f"找不到校驗記錄: {table_class.__tablename__} ID={record_id}",
            }

        # 計算當前校驗碼
        current_checksum = self._calculate_checksum(
            record, checksum_record.checksum_fields
        )

        # 比較校驗碼
        is_valid = current_checksum == checksum_record.checksum

        result = {
            "is_valid": is_valid,
            "stored_checksum": checksum_record.checksum,
            "current_checksum": current_checksum,
            "checksum_fields": checksum_record.checksum_fields,
            "verified_at": datetime.now(),
        }

        # 更新校驗記錄
        checksum_record.verified_at = result["verified_at"]
        checksum_record.is_valid = is_valid
        self.session.commit()

        return result

    def _calculate_checksum(self, record, fields: List[str]) -> str:
        """
        計算記錄的校驗碼

        Args:
            record: 資料記錄
            fields: 參與校驗的欄位

        Returns:
            str: 校驗碼
        """
        # 構建用於校驗的資料字典
        data = {}
        for field in fields:
            if hasattr(record, field):
                value = getattr(record, field)
                # 處理日期和時間類型
                if isinstance(value, (date, datetime)):
                    value = value.isoformat()
                data[field] = value

        # 將資料轉換為 JSON 字串並計算 SHA-256 校驗碼
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _generate_trading_dates(self, start_date: date, end_date: date) -> List[date]:
        """
        生成交易日期列表

        生成指定範圍內的交易日期（排除週末）。
        注意：此函數不考慮假日，僅排除週末。

        Args:
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            List[date]: 交易日期列表
        """
        trading_dates = []
        current_date = start_date

        while current_date <= end_date:
            # 排除週末（週六和週日）
            if current_date.weekday() < 5:
                trading_dates.append(current_date)
            current_date += timedelta(days=1)

        return trading_dates

    def log_validation_result(
        self, validation_type: str, result: Dict[str, Any]
    ) -> None:
        """
        記錄驗證結果

        將驗證結果記錄到系統日誌。

        Args:
            validation_type: 驗證類型
            result: 驗證結果
        """
        # 將結果轉換為 JSON 字串，使用自定義編碼器處理日期和時間
        result_json = json.dumps(result, cls=CustomJSONEncoder)
        result_dict = json.loads(result_json)

        # 創建日誌記錄
        log_entry = SystemLog(
            timestamp=datetime.now(),
            level="INFO" if result.get("is_valid", True) else "WARNING",
            module="data_validation",
            message=f"資料驗證: {validation_type}",
            details=result_dict,
        )

        # 添加到資料庫
        self.session.add(log_entry)
        self.session.commit()
