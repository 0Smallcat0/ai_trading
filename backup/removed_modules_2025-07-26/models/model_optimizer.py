# -*- coding: utf-8 -*-
"""
模型優化模組

此模組負責優化模型推論性能。
主要功能：
- 模型轉換為 ONNX 格式
- 模型量化
- 批次推論優化
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from src.config import MODELS_DIR
from src.core.logger import get_logger

# 設定日誌
logger = get_logger("model_optimizer")

# 檢查 ONNX 是否可用
try:
    import onnx
    import onnxruntime as ort

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("ONNX 相關套件未安裝，無法使用 ONNX 優化功能")

# 檢查 PyTorch 是否可用
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch 未安裝，無法使用 PyTorch 相關優化功能")

# 檢查 TensorFlow 是否可用
try:
    import tensorflow as tf

    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logger.warning("TensorFlow 未安裝，無法使用 TensorFlow 相關優化功能")


class ModelOptimizer:
    """模型優化器"""

    def __init__(self, model_dir: Optional[str] = None):
        """
        初始化模型優化器

        Args:
            model_dir: 模型目錄，如果為 None，則使用 MODELS_DIR
        """
        self.model_dir = model_dir or MODELS_DIR
        os.makedirs(self.model_dir, exist_ok=True)

    def convert_to_onnx(
        self,
        model,
        model_name: str,
        input_shape: Tuple,
        output_path: Optional[str] = None,
        dynamic_axes: Optional[Dict] = None,
    ) -> str:
        """
        將模型轉換為 ONNX 格式

        Args:
            model: 模型實例
            model_name: 模型名稱
            input_shape: 輸入形狀
            output_path: 輸出路徑，如果為 None，則使用 model_dir/model_name.onnx
            dynamic_axes: 動態軸配置

        Returns:
            str: ONNX 模型路徑
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX 相關套件未安裝，無法使用 ONNX 優化功能")

        # 設定輸出路徑
        if output_path is None:
            output_path = os.path.join(self.model_dir, f"{model_name}.onnx")

        # 根據模型類型進行轉換
        if TORCH_AVAILABLE and isinstance(model, torch.nn.Module):
            return self._convert_pytorch_to_onnx(
                model, model_name, input_shape, output_path, dynamic_axes
            )
        elif TF_AVAILABLE and isinstance(model, tf.keras.Model):
            return self._convert_tensorflow_to_onnx(
                model, model_name, input_shape, output_path
            )
        else:
            raise ValueError("不支援的模型類型，目前僅支援 PyTorch 和 TensorFlow 模型")

    def _convert_pytorch_to_onnx(
        self,
        model: "torch.nn.Module",
        model_name: str,
        input_shape: Tuple,
        output_path: str,
        dynamic_axes: Optional[Dict] = None,
    ) -> str:
        """
        將 PyTorch 模型轉換為 ONNX 格式

        Args:
            model: PyTorch 模型實例
            model_name: 模型名稱
            input_shape: 輸入形狀
            output_path: 輸出路徑
            dynamic_axes: 動態軸配置

        Returns:
            str: ONNX 模型路徑
        """
        logger.info(f"開始將 PyTorch 模型 {model_name} 轉換為 ONNX 格式")

        # 設定模型為評估模式
        model.eval()

        # 創建虛擬輸入
        dummy_input = torch.randn(input_shape)

        # 設定動態軸
        if dynamic_axes is None:
            dynamic_axes = {"input": {0: "batch_size"}, "output": {0: "batch_size"}}

        # 導出模型
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes=dynamic_axes,
        )

        # 驗證模型
        onnx_model = onnx.load(output_path)
        onnx.checker.check_model(onnx_model)

        logger.info(f"PyTorch 模型已成功轉換為 ONNX 格式，保存至 {output_path}")

        return output_path

    def _convert_tensorflow_to_onnx(
        self,
        model: "tf.keras.Model",
        model_name: str,
        input_shape: Tuple,
        output_path: str,
    ) -> str:
        """
        將 TensorFlow 模型轉換為 ONNX 格式

        Args:
            model: TensorFlow 模型實例
            model_name: 模型名稱
            input_shape: 輸入形狀
            output_path: 輸出路徑

        Returns:
            str: ONNX 模型路徑
        """
        logger.info(f"開始將 TensorFlow 模型 {model_name} 轉換為 ONNX 格式")

        # 保存為 SavedModel 格式
        temp_saved_model = os.path.join(
            self.model_dir, f"{model_name}_temp_saved_model"
        )
        model.save(temp_saved_model)

        # 使用 tf2onnx 轉換
        import tf2onnx
        import tf2onnx.convert

        # 創建虛擬輸入
        np.random.randn(*input_shape).astype(np.float32)

        # 轉換模型
        onnx_model, _ = tf2onnx.convert.from_keras(model)

        # 保存模型
        onnx.save(onnx_model, output_path)

        logger.info(f"TensorFlow 模型已成功轉換為 ONNX 格式，保存至 {output_path}")

        return output_path

    def create_onnx_session(self, onnx_path: str) -> "ort.InferenceSession":
        """
        創建 ONNX 推論會話

        Args:
            onnx_path: ONNX 模型路徑

        Returns:
            ort.InferenceSession: ONNX 推論會話
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX 相關套件未安裝，無法使用 ONNX 優化功能")

        # 創建推論會話
        session = ort.InferenceSession(onnx_path)

        return session

    def onnx_predict(
        self,
        session: "ort.InferenceSession",
        data: Union[np.ndarray, pd.DataFrame],
        input_name: str = "input",
    ) -> np.ndarray:
        """
        使用 ONNX 模型進行預測

        Args:
            session: ONNX 推論會話
            data: 輸入資料
            input_name: 輸入名稱

        Returns:
            np.ndarray: 預測結果
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX 相關套件未安裝，無法使用 ONNX 優化功能")

        # 轉換輸入資料
        if isinstance(data, pd.DataFrame):
            data = data.values.astype(np.float32)
        elif isinstance(data, np.ndarray):
            data = data.astype(np.float32)
        else:
            raise ValueError(
                "不支援的資料類型，僅支援 numpy.ndarray 和 pandas.DataFrame"
            )

        # 進行預測
        outputs = session.run(None, {input_name: data})

        return outputs[0]

    def batch_onnx_predict(
        self,
        session: "ort.InferenceSession",
        data: Union[np.ndarray, pd.DataFrame],
        batch_size: int = 100,
        input_name: str = "input",
    ) -> np.ndarray:
        """
        使用 ONNX 模型進行批次預測

        Args:
            session: ONNX 推論會話
            data: 輸入資料
            batch_size: 批次大小
            input_name: 輸入名稱

        Returns:
            np.ndarray: 預測結果
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX 相關套件未安裝，無法使用 ONNX 優化功能")

        # 轉換輸入資料
        if isinstance(data, pd.DataFrame):
            data = data.values.astype(np.float32)
        elif isinstance(data, np.ndarray):
            data = data.astype(np.float32)
        else:
            raise ValueError(
                "不支援的資料類型，僅支援 numpy.ndarray 和 pandas.DataFrame"
            )

        # 分批處理
        results = []
        for i in range(0, len(data), batch_size):
            batch_data = data[i : i + batch_size]
            batch_outputs = session.run(None, {input_name: batch_data})
            results.append(batch_outputs[0])

        # 合併結果
        return np.vstack(results)

    def compare_performance(
        self,
        original_model,
        onnx_path: str,
        test_data: Union[np.ndarray, pd.DataFrame],
        batch_sizes: List[int] = [1, 10, 50, 100, 500],
        num_runs: int = 5,
    ) -> Dict[str, Any]:
        """
        比較原始模型和 ONNX 模型的性能

        Args:
            original_model: 原始模型
            onnx_path: ONNX 模型路徑
            test_data: 測試資料
            batch_sizes: 批次大小列表
            num_runs: 執行次數

        Returns:
            Dict[str, Any]: 性能比較結果
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX 相關套件未安裝，無法使用 ONNX 優化功能")

        # 創建 ONNX 會話
        session = self.create_onnx_session(onnx_path)

        # 轉換測試資料
        if isinstance(test_data, pd.DataFrame):
            np_data = test_data.values.astype(np.float32)
        elif isinstance(test_data, np.ndarray):
            np_data = test_data.astype(np.float32)
        else:
            raise ValueError(
                "不支援的資料類型，僅支援 numpy.ndarray 和 pandas.DataFrame"
            )

        # 比較結果
        results = {
            "original": {},
            "onnx": {},
            "speedup": {},
        }

        # 測試不同批次大小
        for batch_size in batch_sizes:
            # 原始模型性能
            original_times = []
            for _ in range(num_runs):
                start_time = time.time()
                if hasattr(original_model, "batch_predict"):
                    _ = original_model.batch_predict(test_data, batch_size=batch_size)
                else:
                    # 分批處理
                    for i in range(0, len(np_data), batch_size):
                        batch_data = np_data[i : i + batch_size]
                        _ = original_model.predict(batch_data)
                end_time = time.time()
                original_times.append(end_time - start_time)

            # ONNX 模型性能
            onnx_times = []
            for _ in range(num_runs):
                start_time = time.time()
                _ = self.batch_onnx_predict(session, np_data, batch_size=batch_size)
                end_time = time.time()
                onnx_times.append(end_time - start_time)

            # 計算平均時間
            avg_original_time = sum(original_times) / num_runs
            avg_onnx_time = sum(onnx_times) / num_runs

            # 計算加速比
            speedup = (
                avg_original_time / avg_onnx_time if avg_onnx_time > 0 else float("inf")
            )

            # 記錄結果
            results["original"][batch_size] = avg_original_time
            results["onnx"][batch_size] = avg_onnx_time
            results["speedup"][batch_size] = speedup

        return results


# 如果直接執行此模組
if __name__ == "__main__":
    # 測試模型優化
    pass
