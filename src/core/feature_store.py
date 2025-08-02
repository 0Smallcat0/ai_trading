"""
特徵存儲與版本控制模組

此模組提供特徵存儲、版本控制和元數據管理功能，支援特徵的保存、載入和追蹤。
可以選擇性地與 MLflow 整合，提供更強大的特徵追蹤和版本控制功能。

主要功能：
- 特徵存儲和載入
- 特徵版本控制
- 特徵元數據管理
- MLflow 整合（可選）
"""

import datetime
import hashlib
import json
import logging
import os
import warnings
from typing import Dict, List, Optional, Tuple

import pandas as pd

# 嘗試導入 MLflow
try:
    import mlflow

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    warnings.warn("無法匯入 MLflow，部分特徵追蹤功能將無法使用")

# 設定日誌
logger = logging.getLogger(__name__)


class FeatureStore:
    """
    特徵存儲類

    提供特徵的存儲、載入和版本控制功能。
    """

    def __init__(
        self, base_dir="data/features", use_mlflow=False, mlflow_tracking_uri=None
    ):
        """
        初始化特徵存儲

        Args:
            base_dir (str): 特徵存儲的基礎目錄
            use_mlflow (bool): 是否使用 MLflow 進行特徵追蹤
            mlflow_tracking_uri (str, optional): MLflow 追蹤伺服器 URI
        """
        self.base_dir = base_dir
        self.use_mlflow = use_mlflow and MLFLOW_AVAILABLE

        # 確保基礎目錄存在
        os.makedirs(base_dir, exist_ok=True)

        # 初始化 MLflow
        if self.use_mlflow:
            if mlflow_tracking_uri:
                mlflow.set_tracking_uri(mlflow_tracking_uri)
            logger.info(f"MLflow 追蹤 URI: {mlflow.get_tracking_uri()}")

    def save_features(
        self,
        features_df: pd.DataFrame,
        name: str,
        metadata: Dict = None,
        version: str = None,
        tags: List[str] = None,
    ) -> str:
        """
        保存特徵

        Args:
            features_df (pd.DataFrame): 特徵資料框架
            name (str): 特徵名稱
            metadata (Dict, optional): 特徵元數據
            version (str, optional): 特徵版本，如果為 None 則自動生成
            tags (List[str], optional): 特徵標籤

        Returns:
            str: 特徵版本
        """
        if features_df.empty:
            logger.warning("嘗試保存空的特徵資料框架")
            return None

        # 如果沒有提供版本，則自動生成
        if version is None:
            version = self._generate_version(features_df)

        # 準備元數據
        if metadata is None:
            metadata = {}

        metadata.update(
            {
                "name": name,
                "version": version,
                "created_at": datetime.datetime.now().isoformat(),
                "shape": features_df.shape,
                "columns": features_df.columns.tolist(),
                "index_type": str(type(features_df.index)),
                "dtypes": {
                    col: str(dtype) for col, dtype in features_df.dtypes.items()
                },
                "tags": tags or [],
            }
        )

        # 創建特徵目錄
        feature_dir = os.path.join(self.base_dir, name, version)
        os.makedirs(feature_dir, exist_ok=True)

        # 保存特徵資料
        features_path = os.path.join(feature_dir, "features.parquet")
        features_df.to_parquet(features_path)

        # 保存元數據
        metadata_path = os.path.join(feature_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"特徵 '{name}' 版本 '{version}' 已保存到 {feature_dir}")

        # 如果使用 MLflow，則記錄特徵
        if self.use_mlflow:
            self._log_to_mlflow(features_df, name, version, metadata, tags)

        return version

    def load_features(
        self, name: str, version: str = "latest"
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        載入特徵

        Args:
            name (str): 特徵名稱
            version (str, optional): 特徵版本，如果為 "latest" 則載入最新版本

        Returns:
            Tuple[pd.DataFrame, Dict]: 特徵資料框架和元數據
        """
        # 如果版本為 "latest"，則找出最新版本
        if version == "latest":
            version = self._get_latest_version(name)
            if version is None:
                logger.warning(f"找不到特徵 '{name}' 的任何版本")
                return pd.DataFrame(), {}

        # 構建特徵路徑
        feature_dir = os.path.join(self.base_dir, name, version)
        features_path = os.path.join(feature_dir, "features.parquet")
        metadata_path = os.path.join(feature_dir, "metadata.json")

        # 檢查文件是否存在
        if not os.path.exists(features_path) or not os.path.exists(metadata_path):
            logger.warning(f"找不到特徵 '{name}' 版本 '{version}' 的文件")
            return pd.DataFrame(), {}

        # 載入特徵資料
        features_df = pd.read_parquet(features_path)

        # 載入元數據
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        logger.info(f"已載入特徵 '{name}' 版本 '{version}'")

        return features_df, metadata

    def list_features(self) -> List[str]:
        """
        列出所有特徵名稱

        Returns:
            List[str]: 特徵名稱列表
        """
        if not os.path.exists(self.base_dir):
            return []

        return [
            d
            for d in os.listdir(self.base_dir)
            if os.path.isdir(os.path.join(self.base_dir, d))
        ]

    def list_versions(self, name: str) -> List[str]:
        """
        列出特徵的所有版本

        Args:
            name (str): 特徵名稱

        Returns:
            List[str]: 版本列表
        """
        feature_dir = os.path.join(self.base_dir, name)
        if not os.path.exists(feature_dir):
            return []

        return [
            d
            for d in os.listdir(feature_dir)
            if os.path.isdir(os.path.join(feature_dir, d))
        ]

    def get_metadata(self, name: str, version: str = "latest") -> Dict:
        """
        獲取特徵元數據

        Args:
            name (str): 特徵名稱
            version (str, optional): 特徵版本，如果為 "latest" 則獲取最新版本的元數據

        Returns:
            Dict: 特徵元數據
        """
        # 如果版本為 "latest"，則找出最新版本
        if version == "latest":
            version = self._get_latest_version(name)
            if version is None:
                logger.warning(f"找不到特徵 '{name}' 的任何版本")
                return {}

        # 構建元數據路徑
        metadata_path = os.path.join(self.base_dir, name, version, "metadata.json")

        # 檢查文件是否存在
        if not os.path.exists(metadata_path):
            logger.warning(f"找不到特徵 '{name}' 版本 '{version}' 的元數據")
            return {}

        # 載入元數據
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return metadata

    def search_features(
        self, tags: List[str] = None, name_pattern: str = None
    ) -> List[Dict]:
        """
        搜索特徵

        Args:
            tags (List[str], optional): 標籤列表，如果提供則只返回包含所有這些標籤的特徵
            name_pattern (str, optional): 名稱模式，如果提供則只返回名稱匹配此模式的特徵

        Returns:
            List[Dict]: 符合條件的特徵元數據列表
        """
        results = []

        # 遍歷所有特徵
        for name in self.list_features():
            # 檢查名稱模式
            if name_pattern and name_pattern not in name:
                continue

            # 獲取最新版本
            version = self._get_latest_version(name)
            if version is None:
                continue

            # 獲取元數據
            metadata = self.get_metadata(name, version)
            if not metadata:
                continue

            # 檢查標籤
            if tags:
                metadata_tags = set(metadata.get("tags", []))
                if not all(tag in metadata_tags for tag in tags):
                    continue

            results.append(metadata)

        return results

    def _generate_version(self, features_df: pd.DataFrame) -> str:
        """
        生成特徵版本

        基於特徵資料和當前時間生成唯一的版本字符串。

        Args:
            features_df (pd.DataFrame): 特徵資料框架

        Returns:
            str: 版本字符串
        """
        # 使用特徵資料的哈希值和當前時間生成版本
        hasher = hashlib.md5(usedforsecurity=False)
        hasher.update(pd.util.hash_pandas_object(features_df).values.tobytes())
        hasher.update(str(datetime.datetime.now()).encode())
        hash_str = hasher.hexdigest()[:8]

        # 添加時間戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        return f"{timestamp}_{hash_str}"

    def _get_latest_version(self, name: str) -> Optional[str]:
        """
        獲取特徵的最新版本

        Args:
            name (str): 特徵名稱

        Returns:
            Optional[str]: 最新版本，如果沒有版本則返回 None
        """
        versions = self.list_versions(name)
        if not versions:
            return None

        # 按照版本字符串排序，假設版本格式為 "時間戳_哈希值"
        versions.sort(reverse=True)

        return versions[0]

    def _log_to_mlflow(
        self,
        features_df: pd.DataFrame,
        name: str,
        version: str,
        metadata: Dict,
        tags: List[str] = None,
    ) -> None:
        """
        將特徵記錄到 MLflow

        Args:
            features_df (pd.DataFrame): 特徵資料框架
            name (str): 特徵名稱
            version (str): 特徵版本
            metadata (Dict): 特徵元數據
            tags (List[str], optional): 特徵標籤
        """
        if not self.use_mlflow:
            return

        # 創建 MLflow 實驗
        experiment_name = f"features/{name}"
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
            else:
                experiment_id = experiment.experiment_id
        except Exception as e:
            logger.error(f"創建 MLflow 實驗時發生錯誤: {e}")
            return

        # 開始 MLflow 運行
        try:
            with mlflow.start_run(experiment_id=experiment_id, run_name=version):
                # 記錄元數據
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        mlflow.log_param(key, value)

                # 記錄標籤
                if tags:
                    for tag in tags:
                        mlflow.set_tag(tag, True)

                # 記錄特徵統計信息
                try:
                    stats_dict = features_df.describe().to_dict()
                    mlflow.log_params(
                        {f"stats_{k}": str(v) for k, v in stats_dict.items()}
                    )
                except Exception as e:
                    logger.warning(f"記錄特徵統計信息時發生錯誤: {e}")

                # 保存特徵樣本
                try:
                    sample = features_df.head(100)
                    sample_path = "features_sample.parquet"
                    sample.to_parquet(sample_path)
                    mlflow.log_artifact(sample_path)
                    os.remove(sample_path)
                except Exception as e:
                    logger.warning(f"保存特徵樣本時發生錯誤: {e}")
        except Exception as e:
            logger.error(f"記錄到 MLflow 時發生錯誤: {e}")
