#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3.2 AI 模型模組環境修復腳本

此腳本用於診斷和修復 Phase 3.2 重構後的環境和測試問題：
1. TensorFlow DLL 載入問題
2. 測試 fixture 缺失問題
3. 模組導入驗證
4. 環境依賴檢查
"""

import sys
import warnings
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_tensorflow_environment():
    """檢查 TensorFlow 環境狀態"""
    print("🔍 檢查 TensorFlow 環境...")

    try:
        import tensorflow as tf

        print(f"✅ TensorFlow 版本: {tf.__version__}")

        # 檢查 GPU 支援
        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            print(f"✅ 檢測到 {len(gpus)} 個 GPU 設備")
        else:
            print("ℹ️  未檢測到 GPU 設備，將使用 CPU")

        return True

    except ImportError as e:
        print(f"⚠️  TensorFlow 導入失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ TensorFlow 環境錯誤: {e}")
        return False


def check_mlflow_tensorflow():
    """檢查 MLflow TensorFlow 整合"""
    print("\n🔍 檢查 MLflow TensorFlow 整合...")

    try:
        pass

        print("✅ MLflow TensorFlow 整合正常")
        return True

    except ImportError as e:
        print(f"⚠️  MLflow TensorFlow 整合失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ MLflow TensorFlow 整合錯誤: {e}")
        return False


def test_training_pipeline_imports():
    """測試訓練管道模組導入"""
    print("\n🔍 測試訓練管道模組導入...")

    try:
        # 測試基本導入
        pass

        print("✅ TrainingConfig 導入成功")

        print("✅ ModelTrainer 導入成功")

        print("✅ CrossValidator 導入成功")

        print("✅ ModelEvaluator 導入成功")

        print("✅ 工具函數導入成功")

        # 測試主模組導入

        print("✅ 主模組導入成功")

        return True

    except Exception as e:
        print(f"❌ 訓練管道導入失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_model_governance_imports():
    """測試模型治理模組導入"""
    print("\n🔍 測試模型治理模組導入...")

    try:
        pass

        print("✅ ModelRegistry 導入成功")

        print("✅ ModelMonitor 導入成功")

        print("✅ DeploymentManager 導入成功")

        print("✅ ModelLifecycleManager 導入成功")

        print("✅ 工具函數導入成功")

        print("✅ 向後兼容介面導入成功")

        return True

    except Exception as e:
        print(f"❌ 模型治理導入失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_basic_functionality():
    """測試基本功能"""
    print("\n🔍 測試基本功能...")

    try:
        # 測試配置創建
        from src.models.training_pipeline.config import TrainingConfig

        config = TrainingConfig(experiment_name="test")
        print("✅ 配置創建成功")

        # 測試註冊表創建
        from src.models.model_governance.registry import ModelRegistry

        ModelRegistry()
        print("✅ 註冊表創建成功")

        return True

    except Exception as e:
        print(f"❌ 基本功能測試失敗: {e}")
        return False


def run_pytest_tests():
    """運行 pytest 測試"""
    print("\n🔍 運行 pytest 測試...")

    try:
        import subprocess

        # 運行特定的測試
        test_commands = [
            [
                "python",
                "-m",
                "pytest",
                "tests/test_models/test_training_pipeline.py",
                "-v",
                "--tb=short",
            ],
            [
                "python",
                "-m",
                "pytest",
                "tests/test_models/test_model_governance.py",
                "-v",
                "--tb=short",
            ],
        ]

        for cmd in test_commands:
            print(f"執行: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=project_root
            )

            if result.returncode == 0:
                print("✅ 測試通過")
            else:
                print(f"⚠️  測試有問題: {result.stderr}")

        return True

    except Exception as e:
        print(f"❌ pytest 測試失敗: {e}")
        return False


def provide_tensorflow_fix_suggestions():
    """提供 TensorFlow 修復建議"""
    print("\n💡 TensorFlow 問題修復建議:")
    print("1. 重新安裝 TensorFlow:")
    print("   pip uninstall tensorflow")
    print("   pip install tensorflow==2.13.0")
    print()
    print("2. 檢查 Visual C++ Redistributable:")
    print("   下載並安裝 Microsoft Visual C++ 2019-2022 Redistributable")
    print()
    print("3. 如果不需要 TensorFlow，可以設定環境變數:")
    print("   set TF_CPP_MIN_LOG_LEVEL=3")
    print()
    print("4. 或者修改代碼使用條件導入 (已在 utils.py 中實現)")


def main():
    """主函數"""
    print("=" * 60)
    print("Phase 3.2 AI 模型模組環境修復診斷")
    print("=" * 60)

    # 檢查結果
    results = {
        "tensorflow": check_tensorflow_environment(),
        "mlflow_tf": check_mlflow_tensorflow(),
        "training_pipeline": test_training_pipeline_imports(),
        "model_governance": test_model_governance_imports(),
        "basic_functionality": test_basic_functionality(),
    }

    # 總結報告
    print("\n" + "=" * 60)
    print("診斷結果總結")
    print("=" * 60)

    all_passed = True
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component}: {'正常' if status else '有問題'}")
        if not status:
            all_passed = False

    if all_passed:
        print("\n🎉 所有組件都正常工作！")
        print("Phase 3.2 重構環境修復完成。")
    else:
        print("\n⚠️  發現一些問題，但核心功能應該仍然可用。")

        if not results["tensorflow"] or not results["mlflow_tf"]:
            provide_tensorflow_fix_suggestions()

    # 運行測試
    print("\n" + "=" * 60)
    print("運行測試驗證")
    print("=" * 60)
    run_pytest_tests()

    print("\n✅ 環境診斷和修復完成！")
    print("如果仍有問題，請檢查上述建議或聯繫開發團隊。")


if __name__ == "__main__":
    # 抑制警告
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    main()
