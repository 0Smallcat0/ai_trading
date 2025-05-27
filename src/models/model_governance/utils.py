# -*- coding: utf-8 -*-
"""
模型治理工具函數

此模組提供模型治理過程中使用的工具函數，包括：
- 模型元數據驗證
- 模型簽名創建
- 資料漂移計算
- 治理報告生成

Functions:
    validate_model_metadata: 驗證模型元數據
    create_model_signature: 創建模型簽名
    calculate_model_drift: 計算模型漂移
    generate_governance_report: 生成治理報告
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


def validate_model_metadata(model: ModelBase) -> None:
    """
    驗證模型元數據
    
    Args:
        model: 要驗證的模型實例
        
    Raises:
        ValueError: 當模型元數據無效時
        
    Example:
        >>> validate_model_metadata(trained_model)
    """
    if not hasattr(model, 'name') or not model.name:
        raise ValueError("模型必須有名稱")
    
    if not hasattr(model, 'trained') or not model.trained:
        raise ValueError("模型必須已經訓練")
    
    if not hasattr(model, 'model') or model.model is None:
        raise ValueError("模型實例不能為空")
    
    # 驗證特徵名稱
    if hasattr(model, 'feature_names') and model.feature_names:
        if not isinstance(model.feature_names, (list, tuple)):
            raise ValueError("特徵名稱必須是列表或元組")
        
        if len(set(model.feature_names)) != len(model.feature_names):
            raise ValueError("特徵名稱不能重複")
    
    logger.debug(f"模型元數據驗證通過: {model.name}")


def create_model_signature(model: ModelBase) -> Dict[str, Any]:
    """
    創建模型簽名
    
    Args:
        model: 模型實例
        
    Returns:
        模型簽名字典
        
    Example:
        >>> signature = create_model_signature(trained_model)
        >>> print(f"Input features: {signature['input_features']}")
    """
    try:
        signature = {
            "model_type": model.__class__.__name__,
            "input_features": model.feature_names or [],
            "output_type": "classification" if hasattr(model, 'is_classifier') and model.is_classifier else "regression",
            "target_name": model.target_name,
            "feature_count": len(model.feature_names) if model.feature_names else 0,
            "model_params": model.model_params,
            "created_at": model.version if hasattr(model, 'version') else None
        }
        
        # 添加模型特定的簽名資訊
        if hasattr(model.model, 'n_features_in_'):
            signature["n_features_in"] = model.model.n_features_in_
            
        if hasattr(model.model, 'classes_'):
            signature["classes"] = model.model.classes_.tolist()
            
        if hasattr(model.model, 'feature_importances_'):
            signature["has_feature_importance"] = True
            
        return signature
        
    except Exception as e:
        logger.error(f"創建模型簽名失敗: {e}")
        return {"error": str(e)}


def calculate_model_drift(
    baseline_features: pd.DataFrame,
    new_features: pd.DataFrame,
    method: str = "ks_test",
    threshold: float = 0.05
) -> Dict[str, Any]:
    """
    計算模型漂移
    
    Args:
        baseline_features: 基準特徵資料
        new_features: 新特徵資料
        method: 漂移檢測方法 ("ks_test", "chi2_test", "psi")
        threshold: 漂移閾值
        
    Returns:
        漂移檢測結果字典
        
    Example:
        >>> drift_result = calculate_model_drift(X_baseline, X_new)
        >>> if drift_result["drift_detected"]:
        ...     print("檢測到資料漂移!")
    """
    try:
        # 驗證輸入
        if baseline_features.empty or new_features.empty:
            return {"drift_detected": False, "message": "Empty data"}
        
        # 確保特徵一致
        common_features = list(set(baseline_features.columns) & set(new_features.columns))
        if not common_features:
            return {"drift_detected": False, "message": "No common features"}
        
        baseline_data = baseline_features[common_features]
        new_data = new_features[common_features]
        
        drift_results = {}
        drift_detected = False
        
        if method == "ks_test":
            drift_results = _calculate_ks_drift(baseline_data, new_data, threshold)
        elif method == "chi2_test":
            drift_results = _calculate_chi2_drift(baseline_data, new_data, threshold)
        elif method == "psi":
            drift_results = _calculate_psi_drift(baseline_data, new_data, threshold)
        else:
            return {"drift_detected": False, "error": f"Unknown method: {method}"}
        
        # 判斷是否檢測到漂移
        drift_detected = any(
            result.get("drift_detected", False) 
            for result in drift_results.values()
        )
        
        return {
            "drift_detected": drift_detected,
            "method": method,
            "threshold": threshold,
            "feature_results": drift_results,
            "summary": {
                "total_features": len(common_features),
                "drifted_features": sum(
                    1 for result in drift_results.values() 
                    if result.get("drift_detected", False)
                )
            }
        }
        
    except Exception as e:
        logger.error(f"計算模型漂移失敗: {e}")
        return {"drift_detected": False, "error": str(e)}


def _calculate_ks_drift(
    baseline_data: pd.DataFrame,
    new_data: pd.DataFrame,
    threshold: float
) -> Dict[str, Dict[str, Any]]:
    """
    使用 Kolmogorov-Smirnov 檢驗計算漂移
    
    Args:
        baseline_data: 基準資料
        new_data: 新資料
        threshold: 顯著性閾值
        
    Returns:
        每個特徵的漂移檢測結果
    """
    results = {}
    
    for feature in baseline_data.columns:
        try:
            baseline_values = baseline_data[feature].dropna()
            new_values = new_data[feature].dropna()
            
            if len(baseline_values) == 0 or len(new_values) == 0:
                results[feature] = {"drift_detected": False, "reason": "No valid data"}
                continue
            
            # 執行 KS 檢驗
            ks_statistic, p_value = stats.ks_2samp(baseline_values, new_values)
            
            results[feature] = {
                "drift_detected": p_value < threshold,
                "ks_statistic": float(ks_statistic),
                "p_value": float(p_value),
                "threshold": threshold
            }
            
        except Exception as e:
            results[feature] = {"drift_detected": False, "error": str(e)}
    
    return results


def _calculate_chi2_drift(
    baseline_data: pd.DataFrame,
    new_data: pd.DataFrame,
    threshold: float
) -> Dict[str, Dict[str, Any]]:
    """
    使用卡方檢驗計算漂移（適用於類別特徵）
    
    Args:
        baseline_data: 基準資料
        new_data: 新資料
        threshold: 顯著性閾值
        
    Returns:
        每個特徵的漂移檢測結果
    """
    results = {}
    
    for feature in baseline_data.columns:
        try:
            baseline_values = baseline_data[feature].dropna()
            new_values = new_data[feature].dropna()
            
            if len(baseline_values) == 0 or len(new_values) == 0:
                results[feature] = {"drift_detected": False, "reason": "No valid data"}
                continue
            
            # 創建頻率表
            all_values = pd.concat([baseline_values, new_values])
            unique_values = all_values.unique()
            
            baseline_counts = baseline_values.value_counts().reindex(unique_values, fill_value=0)
            new_counts = new_values.value_counts().reindex(unique_values, fill_value=0)
            
            # 執行卡方檢驗
            contingency_table = np.array([baseline_counts.values, new_counts.values])
            chi2_statistic, p_value, _, _ = stats.chi2_contingency(contingency_table)
            
            results[feature] = {
                "drift_detected": p_value < threshold,
                "chi2_statistic": float(chi2_statistic),
                "p_value": float(p_value),
                "threshold": threshold
            }
            
        except Exception as e:
            results[feature] = {"drift_detected": False, "error": str(e)}
    
    return results


def _calculate_psi_drift(
    baseline_data: pd.DataFrame,
    new_data: pd.DataFrame,
    threshold: float = 0.1
) -> Dict[str, Dict[str, Any]]:
    """
    使用 Population Stability Index (PSI) 計算漂移
    
    Args:
        baseline_data: 基準資料
        new_data: 新資料
        threshold: PSI 閾值（通常 0.1-0.2）
        
    Returns:
        每個特徵的漂移檢測結果
    """
    results = {}
    
    for feature in baseline_data.columns:
        try:
            baseline_values = baseline_data[feature].dropna()
            new_values = new_data[feature].dropna()
            
            if len(baseline_values) == 0 or len(new_values) == 0:
                results[feature] = {"drift_detected": False, "reason": "No valid data"}
                continue
            
            # 創建分箱
            _, bins = pd.qcut(baseline_values, q=10, retbins=True, duplicates='drop')
            
            # 計算基準和新資料的分佈
            baseline_dist = pd.cut(baseline_values, bins=bins, include_lowest=True).value_counts(normalize=True)
            new_dist = pd.cut(new_values, bins=bins, include_lowest=True).value_counts(normalize=True)
            
            # 對齊分佈
            baseline_dist = baseline_dist.reindex(baseline_dist.index.union(new_dist.index), fill_value=0.001)
            new_dist = new_dist.reindex(baseline_dist.index, fill_value=0.001)
            
            # 計算 PSI
            psi = np.sum((new_dist - baseline_dist) * np.log(new_dist / baseline_dist))
            
            results[feature] = {
                "drift_detected": psi > threshold,
                "psi_score": float(psi),
                "threshold": threshold
            }
            
        except Exception as e:
            results[feature] = {"drift_detected": False, "error": str(e)}
    
    return results


def generate_governance_report(
    registry,
    model_name: str = None,
    output_path: str = "governance_report.html"
) -> str:
    """
    生成治理報告
    
    Args:
        registry: 模型註冊表實例
        model_name: 特定模型名稱（可選）
        output_path: 報告輸出路徑
        
    Returns:
        報告檔案路徑
        
    Example:
        >>> report_path = generate_governance_report(registry, "my_model")
    """
    try:
        # 獲取模型資訊
        if model_name:
            models = [model_name]
        else:
            models = registry.list_models()
        
        # 生成 HTML 報告
        html_content = _generate_html_report(registry, models)
        
        # 保存報告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"治理報告已生成: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"生成治理報告失敗: {e}")
        raise RuntimeError(f"報告生成失敗: {e}") from e


def _generate_html_report(registry, models: List[str]) -> str:
    """
    生成 HTML 格式的治理報告
    
    Args:
        registry: 模型註冊表
        models: 模型名稱列表
        
    Returns:
        HTML 內容字串
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Model Governance Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1, h2 { color: #333; }
            .model-section { margin: 30px 0; border: 1px solid #ddd; padding: 20px; }
            .metric-table { border-collapse: collapse; width: 100%; margin: 20px 0; }
            .metric-table th, .metric-table td { 
                border: 1px solid #ddd; padding: 12px; text-align: left; 
            }
            .metric-table th { background-color: #f2f2f2; }
            .status-active { color: green; font-weight: bold; }
            .status-inactive { color: red; }
        </style>
    </head>
    <body>
        <h1>Model Governance Report</h1>
        <p>Generated on: """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
    """
    
    for model_name in models:
        try:
            versions = registry.list_versions(model_name)
            latest_version = max(versions) if versions else None
            
            if latest_version:
                model_info = registry.get_model_info(model_name, latest_version)
                
                html_content += f"""
                <div class="model-section">
                    <h2>Model: {model_name}</h2>
                    <table class="metric-table">
                        <tr><th>Property</th><th>Value</th></tr>
                        <tr><td>Latest Version</td><td>{latest_version}</td></tr>
                        <tr><td>Model Type</td><td>{model_info.get('model_type', 'N/A')}</td></tr>
                        <tr><td>Created At</td><td>{model_info.get('created_at', 'N/A')}</td></tr>
                        <tr><td>Status</td><td class="status-active">{model_info.get('status', 'N/A')}</td></tr>
                        <tr><td>Description</td><td>{model_info.get('description', 'N/A')}</td></tr>
                        <tr><td>Feature Count</td><td>{len(model_info.get('feature_names', []))}</td></tr>
                    </table>
                </div>
                """
        except Exception as e:
            html_content += f"""
            <div class="model-section">
                <h2>Model: {model_name}</h2>
                <p style="color: red;">Error loading model info: {e}</p>
            </div>
            """
    
    html_content += """
    </body>
    </html>
    """
    
    return html_content
