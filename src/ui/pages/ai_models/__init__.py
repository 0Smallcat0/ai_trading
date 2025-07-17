"""
AI 模型管理頁面模組

此模組提供 AI 模型管理的完整功能，包括：
- 模型清單管理與瀏覽
- 模型訓練與參數設定
- 模型推論與結果分析
- 模型解釋性分析 (SHAP/LIME)
- 模型版本控制與日誌管理

模組結構：
- base: 基礎功能和工具函數
- model_list: 模型清單管理
- model_training: 模型訓練功能
- model_inference: 模型推論功能
- model_interpretability: 模型解釋性分析
- model_monitoring: 模型監控功能
"""

from .base import show, get_ai_model_service, safe_strftime
from .model_list import show_model_list, show_model_upload_form
from .model_training import (
    show_model_training_enhanced,
    show_quick_training_config,
    show_standard_training_config,
    show_deep_training_config,
    show_auto_tuning_config,
    show_training_results,
    show_model_training
)
from .model_inference import (
    show_model_inference,
    show_single_inference,
    show_batch_inference,
    show_realtime_inference
)
from .model_interpretability import (
    show_model_interpretability,
    generate_sample_data,
    show_explanation_results,
    show_explanation_method_info
)
from .model_monitoring import (
    show_model_performance_monitoring,
    show_realtime_monitoring,
    show_historical_analysis,
    show_performance_comparison,
    show_anomaly_detection
)
from .model_management import (
    show_model_management_enhanced,
    show_model_lifecycle_management,
    show_model_version_management,
    show_model_deployment_management,
    show_model_resource_management,
    show_model_security_management
)

__all__ = [
    # 主要入口
    'show',
    'get_ai_model_service',
    'safe_strftime',
    
    # 模型清單
    'show_model_list',
    'show_model_upload_form',
    
    # 模型訓練
    'show_model_training_enhanced',
    'show_quick_training_config',
    'show_standard_training_config',
    'show_deep_training_config',
    'show_auto_tuning_config',
    'show_training_results',
    'show_model_training',
    
    # 模型推論
    'show_model_inference',
    'show_single_inference',
    'show_batch_inference',
    'show_realtime_inference',
    
    # 模型解釋性
    'show_model_interpretability',
    'generate_sample_data',
    'show_explanation_results',
    'show_explanation_method_info',
    
    # 模型監控
    'show_model_performance_monitoring',
    'show_realtime_monitoring',
    'show_historical_analysis',
    'show_performance_comparison',
    'show_anomaly_detection',
    
    # 模型管理
    'show_model_management_enhanced',
    'show_model_lifecycle_management',
    'show_model_version_management',
    'show_model_deployment_management',
    'show_model_resource_management',
    'show_model_security_management',
]

# 版本資訊
__version__ = "1.0.0"
__author__ = "AI Trading System Team"
__description__ = "AI模型管理頁面模組"
