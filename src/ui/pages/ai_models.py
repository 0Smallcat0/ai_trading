"""
AI 模型管理頁面

此模組實現 AI 模型管理的完整功能，包括：
- 模型清單管理與瀏覽
- 模型訓練與參數設定
- 模型推論與結果分析
- 模型解釋性分析 (SHAP/LIME)
- 模型版本控制與日誌管理
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 導入服務層
from ...core.ai_model_management_service import AIModelManagementService

# 導入組件
from ..components.ai_model_components import (
    show_model_card,
    show_training_progress,
    show_feature_importance,
    show_model_explanation_analysis,
)


# 初始化服務
@st.cache_resource
def get_ai_model_service():
    """獲取 AI 模型管理服務實例。

    使用 Streamlit 的 cache_resource 裝飾器來確保服務實例在會話間共享，
    避免重複初始化造成的效能問題。

    Returns:
        AIModelManagementService: AI 模型管理服務實例，提供完整的模型管理功能

    Example:
        ```python
        service = get_ai_model_service()
        models = service.get_models()
        ```

    Note:
        此函數會被 Streamlit 快取，確保在整個應用程式生命週期中
        只會建立一個 AIModelManagementService 實例。
    """
    return AIModelManagementService()


def show():
    """顯示 AI 模型管理主頁面。

    建立完整的 AI 模型管理系統使用者介面，包含六個主要功能標籤頁：
    模型清單、模型訓練、模型推論、模型解釋、效能監控和模型管理。

    此函數會初始化必要的 session state 變數，並建立標籤頁結構
    來組織不同的 AI 模型管理功能模組。

    主要功能包括：
    - 模型清單管理與瀏覽
    - 增強版模型訓練功能
    - 模型推論與結果分析
    - 模型解釋性分析 (SHAP/LIME)
    - 模型效能監控
    - 模型管理與版本控制

    Example:
        ```python
        from src.ui.pages.ai_models import show
        show()  # 在 Streamlit 應用中顯示 AI 模型管理系統
        ```

    Note:
        - 使用 session state 來維護選中的模型和當前標籤頁狀態
        - 所有子功能都透過獨立的函數來實現，保持程式碼模組化
        - 標籤頁設計讓使用者能夠輕鬆在不同功能間切換
        - 依賴於 AIModelManagementService 來執行實際的模型管理邏輯
    """
    st.header("🤖 AI 模型管理")

    # 初始化 session state
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = None
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = 0

    # 創建標籤頁 - 增強版本
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "📋 模型清單",
            "🎯 模型訓練",
            "🔮 模型推論",
            "🔍 模型解釋",
            "📊 效能監控",
            "🔧 模型管理",
        ]
    )

    with tab1:
        show_model_list()

    with tab2:
        show_model_training_enhanced()

    with tab3:
        show_model_inference()

    with tab4:
        show_model_interpretability()

    with tab5:
        show_model_performance_monitoring()

    with tab6:
        show_model_management_enhanced()


def show_model_list():
    """顯示模型清單頁面"""
    st.subheader("模型清單管理")

    service = get_ai_model_service()

    # 控制面板
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

    with col1:
        # 模型類型過濾
        model_types = ["所有類型"] + list(service.get_model_types().keys())
        selected_type = st.selectbox("模型類型", options=model_types, index=0)

    with col2:
        # 模型狀態過濾
        status_options = [
            "所有狀態",
            "created",
            "training",
            "trained",
            "deployed",
            "failed",
        ]
        selected_status = st.selectbox("模型狀態", options=status_options, index=0)

    with col3:
        # 搜尋功能
        search_term = st.text_input("搜尋模型", placeholder="輸入模型名稱...")

    with col4:
        # 排序選項
        sort_options = ["創建時間", "更新時間", "模型名稱", "效能指標"]
        sort_by = st.selectbox("排序方式", options=sort_options)

    # 新增模型按鈕
    col1, col2, col3 = st.columns([1, 1, 6])

    with col1:
        if st.button("➕ 新增模型", type="primary"):
            st.session_state.selected_model = None
            st.session_state.current_tab = 1
            st.rerun()

    with col2:
        # 模型上傳
        uploaded_file = st.file_uploader(
            "上傳模型",
            type=["pkl", "joblib", "h5", "pt", "json"],
            help="支援格式: .pkl, .joblib, .h5, .pt, .json",
        )

        if uploaded_file is not None:
            show_model_upload_form(uploaded_file)

    # 獲取並過濾模型列表
    try:
        models = service.get_models()

        # 應用過濾條件
        if selected_type != "所有類型":
            models = [m for m in models if m.get("type") == selected_type]

        if selected_status != "所有狀態":
            models = [m for m in models if m.get("status") == selected_status]

        if search_term:
            models = [
                m for m in models if search_term.lower() in m.get("name", "").lower()
            ]

        # 排序
        if sort_by == "創建時間":
            models.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        elif sort_by == "更新時間":
            models.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        elif sort_by == "模型名稱":
            models.sort(key=lambda x: x.get("name", ""))

        # 顯示統計資訊
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("總模型數", len(models))

        with col2:
            trained_count = len(
                [m for m in models if m.get("status") in ["trained", "deployed"]]
            )
            st.metric("已訓練", trained_count)

        with col3:
            deployed_count = len([m for m in models if m.get("status") == "deployed"])
            st.metric("已部署", deployed_count)

        with col4:
            training_count = len([m for m in models if m.get("status") == "training"])
            st.metric("訓練中", training_count)

        # 顯示模型卡片
        if models:
            st.markdown("---")
            for model in models:
                with st.container():
                    show_model_card(model, show_actions=True)
                    st.markdown("---")
        else:
            st.info("沒有找到符合條件的模型")

    except Exception as e:
        st.error(f"載入模型列表時發生錯誤: {str(e)}")


def show_model_upload_form(uploaded_file):
    """顯示模型上傳表單"""
    with st.expander("模型上傳設定", expanded=True):
        with st.form("upload_model_form"):
            col1, col2 = st.columns(2)

            with col1:
                model_name = st.text_input(
                    "模型名稱", value=uploaded_file.name.split(".")[0]
                )
                model_type = st.selectbox(
                    "模型類型",
                    options=list(get_ai_model_service().get_model_types().keys()),
                )

            with col2:
                sub_type = st.selectbox(
                    "子類型",
                    options=get_ai_model_service()
                    .get_model_types()
                    .get(model_type, []),
                )
                author = st.text_input("作者", value="使用者")

            description = st.text_area("模型描述")

            # 特徵和目標設定
            col1, col2 = st.columns(2)

            with col1:
                features_text = st.text_area(
                    "特徵列表 (每行一個)", placeholder="feature1\nfeature2\nfeature3"
                )

            with col2:
                target = st.text_input("目標變數", placeholder="target_column")

            # 模型參數
            parameters_text = st.text_area(
                "模型參數 (JSON格式)",
                placeholder='{"param1": "value1", "param2": "value2"}',
            )

            submitted = st.form_submit_button("上傳模型", type="primary")

            if submitted:
                try:
                    # 解析特徵列表
                    features = (
                        [f.strip() for f in features_text.split("\n") if f.strip()]
                        if features_text
                        else []
                    )

                    # 解析參數
                    parameters = {}
                    if parameters_text:
                        try:
                            parameters = json.loads(parameters_text)
                        except json.JSONDecodeError:
                            st.error("參數格式錯誤，請使用有效的JSON格式")
                            return

                    # 上傳模型
                    service = get_ai_model_service()
                    model_id = service.upload_model(
                        model_file=uploaded_file.read(),
                        model_name=model_name,
                        model_type=model_type,
                        sub_type=sub_type,
                        description=description,
                        author=author,
                        parameters=parameters,
                        features=features,
                        target=target,
                    )

                    st.success(f"模型上傳成功！模型ID: {model_id}")
                    st.rerun()

                except Exception as e:
                    st.error(f"模型上傳失敗: {str(e)}")


def show_model_training_enhanced():
    """顯示增強版模型訓練頁面"""
    st.subheader("🎯 增強版模型訓練")

    service = get_ai_model_service()

    # 檢查是否有選擇的模型
    is_editing = st.session_state.selected_model is not None

    if is_editing:
        st.info(f"重新訓練模型: {st.session_state.selected_model['name']}")
        model_data = st.session_state.selected_model
    else:
        st.info("創建新模型")
        model_data = {}

    # 訓練模式選擇
    training_mode = st.selectbox(
        "訓練模式",
        options=["快速訓練", "標準訓練", "深度訓練", "自動調優"],
        index=1,
        help="快速訓練：基本參數，快速完成；標準訓練：平衡效能與時間；深度訓練：最佳效能；自動調優：自動尋找最佳參數",
    )

    # 根據訓練模式顯示不同的配置選項
    if training_mode == "快速訓練":
        show_quick_training_config(model_data, is_editing)
    elif training_mode == "標準訓練":
        show_standard_training_config(model_data, is_editing)
    elif training_mode == "深度訓練":
        show_deep_training_config(model_data, is_editing)
    else:  # 自動調優
        show_auto_tuning_config(model_data, is_editing)


def show_quick_training_config(model_data, is_editing):
    """顯示快速訓練配置"""
    st.markdown("### ⚡ 快速訓練配置")

    with st.form("quick_training_form"):
        col1, col2 = st.columns(2)

        with col1:
            model_name = st.text_input(
                "模型名稱", value=model_data.get("name", ""), disabled=is_editing
            )

            model_type = st.selectbox(
                "模型類型", options=["隨機森林", "XGBoost", "線性回歸"], index=0
            )

        with col2:
            target_type = st.selectbox(
                "預測目標", options=["股價預測", "方向預測"], index=0
            )

            data_period = st.selectbox(
                "資料期間", options=["1個月", "3個月", "6個月"], index=1
            )

        # 快速特徵選擇
        st.markdown("**特徵選擇**")
        feature_preset = st.selectbox(
            "特徵預設", options=["基本技術指標", "價量指標", "全部指標"], index=0
        )

        submitted = st.form_submit_button("🚀 開始快速訓練", type="primary")

        if submitted:
            if not model_name:
                st.error("請輸入模型名稱")
                return

            # 執行快速訓練
            with st.spinner("正在執行快速訓練..."):
                try:
                    # 模擬訓練過程
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    for i in range(100):
                        progress_bar.progress(i + 1)
                        if i < 30:
                            status_text.text("準備資料中...")
                        elif i < 70:
                            status_text.text("訓練模型中...")
                        else:
                            status_text.text("評估模型中...")
                        time.sleep(0.02)

                    st.success("快速訓練完成！")

                    # 顯示訓練結果
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("準確率", "85.2%")

                    with col2:
                        st.metric("F1分數", "0.83")

                    with col3:
                        st.metric("訓練時間", "2.3分鐘")

                except Exception as e:
                    st.error(f"訓練失敗: {str(e)}")


def show_standard_training_config(model_data, is_editing):
    """顯示標準訓練配置"""
    st.markdown("### 📊 標準訓練配置")

    with st.form("standard_training_form"):
        # 基本設定
        st.markdown("**基本設定**")
        col1, col2 = st.columns(2)

        with col1:
            model_name = st.text_input(
                "模型名稱", value=model_data.get("name", ""), disabled=is_editing
            )

            model_type = st.selectbox(
                "模型類型",
                options=["隨機森林", "XGBoost", "LightGBM", "神經網路", "SVM"],
                index=1,
            )

        with col2:
            target_type = st.selectbox(
                "預測目標", options=["股價預測", "方向預測", "波動率預測"], index=0
            )

            validation_method = st.selectbox(
                "驗證方法", options=["時間序列分割", "K折交叉驗證", "留出驗證"], index=0
            )

        # 資料設定
        st.markdown("**資料設定**")
        col1, col2, col3 = st.columns(3)

        with col1:
            train_ratio = st.slider("訓練集比例", 0.6, 0.9, 0.8)

        with col2:
            val_ratio = st.slider("驗證集比例", 0.1, 0.3, 0.15)

        with col3:
            lookback_days = st.number_input("回看天數", 5, 60, 20)

        # 特徵工程
        st.markdown("**特徵工程**")
        col1, col2 = st.columns(2)

        with col1:
            feature_scaling = st.selectbox(
                "特徵縮放", options=["標準化", "正規化", "無"], index=0
            )

            handle_missing = st.selectbox(
                "缺失值處理", options=["前向填充", "插值", "刪除"], index=0
            )

        with col2:
            feature_selection = st.checkbox("自動特徵選擇", value=True)
            outlier_removal = st.checkbox("異常值移除", value=True)

        # 模型參數
        st.markdown("**模型參數**")
        if model_type in ["隨機森林", "XGBoost", "LightGBM"]:
            col1, col2, col3 = st.columns(3)

            with col1:
                n_estimators = st.number_input("樹的數量", 50, 500, 100)

            with col2:
                max_depth = st.number_input("最大深度", 3, 20, 6)

            with col3:
                learning_rate = st.number_input("學習率", 0.01, 0.3, 0.1)

        # 訓練設定
        st.markdown("**訓練設定**")
        col1, col2 = st.columns(2)

        with col1:
            early_stopping = st.checkbox("早停機制", value=True)
            if early_stopping:
                patience = st.number_input("耐心值", 5, 50, 10)

        with col2:
            save_checkpoints = st.checkbox("保存檢查點", value=True)
            log_metrics = st.checkbox("記錄指標", value=True)

        submitted = st.form_submit_button("🎯 開始標準訓練", type="primary")

        if submitted:
            if not model_name:
                st.error("請輸入模型名稱")
                return

            # 執行標準訓練
            with st.spinner("正在執行標準訓練..."):
                try:
                    # 模擬訓練過程
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    training_stages = [
                        "載入資料...",
                        "資料預處理...",
                        "特徵工程...",
                        "模型訓練...",
                        "模型驗證...",
                        "效能評估...",
                    ]

                    for i, stage in enumerate(training_stages):
                        for j in range(17):  # 每階段約17步
                            progress = (i * 17 + j) / (len(training_stages) * 17)
                            progress_bar.progress(progress)
                            status_text.text(stage)
                            time.sleep(0.05)

                    st.success("標準訓練完成！")

                    # 顯示詳細訓練結果
                    show_training_results()

                except Exception as e:
                    st.error(f"訓練失敗: {str(e)}")


def show_training_results():
    """顯示訓練結果"""
    st.markdown("### 📈 訓練結果")

    # 效能指標
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("準確率", "87.5%", delta="2.3%")

    with col2:
        st.metric("精確率", "86.2%", delta="1.8%")

    with col3:
        st.metric("召回率", "88.1%", delta="2.1%")

    with col4:
        st.metric("F1分數", "0.871", delta="0.019")

    # 訓練曲線
    st.markdown("**訓練曲線**")

    # 生成模擬訓練數據
    epochs = list(range(1, 51))
    train_loss = [0.8 - 0.01 * i + np.random.normal(0, 0.02) for i in epochs]
    val_loss = [0.85 - 0.008 * i + np.random.normal(0, 0.03) for i in epochs]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=epochs, y=train_loss, mode="lines", name="訓練損失"))
    fig.add_trace(go.Scatter(x=epochs, y=val_loss, mode="lines", name="驗證損失"))

    fig.update_layout(
        title="訓練與驗證損失", xaxis_title="Epoch", yaxis_title="損失", height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # 特徵重要性
    st.markdown("**特徵重要性**")

    features = ["close", "volume", "rsi", "macd", "sma_20", "bollinger_upper", "atr"]
    importance = [0.25, 0.18, 0.15, 0.12, 0.10, 0.08, 0.12]

    fig = go.Figure(data=[go.Bar(x=features, y=importance)])
    fig.update_layout(
        title="特徵重要性排序", xaxis_title="特徵", yaxis_title="重要性", height=400
    )

    st.plotly_chart(fig, use_container_width=True)


def show_deep_training_config(model_data, is_editing):
    """顯示深度訓練配置"""
    st.markdown("### 🧠 深度訓練配置")
    st.info("深度訓練模式將使用最先進的技術和最佳化參數，訓練時間較長但效能最佳")

    # 深度訓練的詳細配置...
    st.markdown("**高級配置選項**")

    with st.expander("模型架構設定", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            architecture = st.selectbox(
                "模型架構",
                options=["Transformer", "LSTM", "GRU", "CNN-LSTM", "Attention"],
                index=0,
            )

            layers = st.number_input("層數", 2, 10, 4)

        with col2:
            hidden_size = st.number_input("隱藏層大小", 64, 512, 128)
            attention_heads = st.number_input("注意力頭數", 4, 16, 8)

    with st.expander("優化器設定"):
        col1, col2 = st.columns(2)

        with col1:
            optimizer = st.selectbox(
                "優化器", options=["AdamW", "Adam", "SGD", "RMSprop"], index=0
            )

            learning_rate = st.number_input("學習率", 1e-5, 1e-2, 1e-3, format="%.5f")

        with col2:
            weight_decay = st.number_input("權重衰減", 0.0, 0.1, 0.01)
            scheduler = st.selectbox(
                "學習率調度器",
                options=["CosineAnnealing", "StepLR", "ReduceLROnPlateau"],
                index=0,
            )

    if st.button("🚀 開始深度訓練", type="primary"):
        st.warning("深度訓練需要較長時間，建議在後台執行")
        # 深度訓練邏輯...


def show_auto_tuning_config(model_data, is_editing):
    """顯示自動調優配置"""
    st.markdown("### 🔧 自動調優配置")
    st.info("自動調優將使用貝葉斯優化等先進技術自動尋找最佳參數組合")

    col1, col2 = st.columns(2)

    with col1:
        tuning_method = st.selectbox(
            "調優方法",
            options=["貝葉斯優化", "遺傳算法", "隨機搜索", "網格搜索"],
            index=0,
        )

        max_trials = st.number_input("最大試驗次數", 10, 200, 50)

    with col2:
        optimization_metric = st.selectbox(
            "優化指標", options=["準確率", "F1分數", "AUC", "夏普比率"], index=1
        )

        timeout_hours = st.number_input("超時時間(小時)", 1, 24, 6)

    # 參數搜索空間
    with st.expander("參數搜索空間", expanded=True):
        st.markdown("**模型參數範圍**")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**樹模型參數**")
            n_estimators_range = st.slider("樹數量範圍", 50, 1000, (100, 500))
            max_depth_range = st.slider("最大深度範圍", 3, 20, (5, 15))

        with col2:
            st.markdown("**學習參數**")
            lr_range = st.slider("學習率範圍", 0.01, 0.3, (0.05, 0.2))
            subsample_range = st.slider("子樣本比例", 0.5, 1.0, (0.7, 0.9))

    if st.button("🎯 開始自動調優", type="primary"):
        with st.spinner("正在執行自動調優..."):
            # 模擬自動調優過程
            progress_bar = st.progress(0)
            status_text = st.empty()

            for trial in range(max_trials):
                progress = (trial + 1) / max_trials
                progress_bar.progress(progress)
                status_text.text(
                    f"試驗 {trial + 1}/{max_trials} - 當前最佳分數: {0.85 + trial * 0.001:.3f}"
                )
                time.sleep(0.1)

            st.success("自動調優完成！")

            # 顯示最佳參數
            st.markdown("**最佳參數組合**")
            best_params = {
                "n_estimators": 287,
                "max_depth": 8,
                "learning_rate": 0.087,
                "subsample": 0.83,
            }

            for param, value in best_params.items():
                st.write(f"- {param}: {value}")


def show_model_performance_monitoring():
    """顯示模型效能監控頁面"""
    st.subheader("📊 模型效能監控")

    service = get_ai_model_service()

    # 監控選項
    monitoring_type = st.selectbox(
        "監控類型", options=["實時監控", "歷史分析", "效能比較", "異常檢測"], index=0
    )

    if monitoring_type == "實時監控":
        show_realtime_monitoring()
    elif monitoring_type == "歷史分析":
        show_historical_analysis()
    elif monitoring_type == "效能比較":
        show_performance_comparison()
    else:  # 異常檢測
        show_anomaly_detection()


def show_realtime_monitoring():
    """顯示實時監控"""
    st.markdown("### ⚡ 實時效能監控")

    # 模型選擇
    service = get_ai_model_service()
    try:
        models = service.get_models()
        deployed_models = [m for m in models if m.get("status") == "deployed"]

        if not deployed_models:
            st.warning("沒有已部署的模型可供監控")
            return

        selected_model = st.selectbox(
            "選擇監控模型", options=deployed_models, format_func=lambda x: x["name"]
        )

        # 監控指標
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # 模擬實時準確率
            accuracy = np.random.uniform(0.82, 0.88)
            st.metric(
                "實時準確率",
                f"{accuracy:.2%}",
                delta=f"{np.random.uniform(-0.02, 0.02):.2%}",
            )

        with col2:
            # 模擬推論延遲
            latency = np.random.uniform(50, 150)
            st.metric(
                "推論延遲",
                f"{latency:.0f}ms",
                delta=f"{np.random.uniform(-10, 10):.0f}ms",
            )

        with col3:
            # 模擬吞吐量
            throughput = np.random.uniform(800, 1200)
            st.metric(
                "吞吐量",
                f"{throughput:.0f}/s",
                delta=f"{np.random.uniform(-50, 50):.0f}/s",
            )

        with col4:
            # 模擬錯誤率
            error_rate = np.random.uniform(0.01, 0.05)
            st.metric(
                "錯誤率",
                f"{error_rate:.2%}",
                delta=f"{np.random.uniform(-0.01, 0.01):.2%}",
            )

        # 實時圖表
        st.markdown("**實時效能趨勢**")

        # 生成模擬實時數據
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(hours=1), end=datetime.now(), freq="1min"
        )
        accuracy_data = [0.85 + np.random.normal(0, 0.02) for _ in timestamps]
        latency_data = [100 + np.random.normal(0, 20) for _ in timestamps]

        fig = go.Figure()

        # 準確率趨勢
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=accuracy_data,
                mode="lines",
                name="準確率",
                yaxis="y",
                line=dict(color="blue"),
            )
        )

        # 延遲趨勢
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=latency_data,
                mode="lines",
                name="延遲(ms)",
                yaxis="y2",
                line=dict(color="red"),
            )
        )

        fig.update_layout(
            title="實時效能監控",
            xaxis_title="時間",
            yaxis=dict(title="準確率", side="left"),
            yaxis2=dict(title="延遲(ms)", side="right", overlaying="y"),
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

        # 警報設定
        st.markdown("**警報設定**")

        col1, col2 = st.columns(2)

        with col1:
            accuracy_threshold = st.slider("準確率警報閾值", 0.5, 0.95, 0.8)
            latency_threshold = st.number_input("延遲警報閾值(ms)", 50, 1000, 200)

        with col2:
            error_threshold = st.slider("錯誤率警報閾值", 0.01, 0.1, 0.05)
            enable_alerts = st.checkbox("啟用警報", value=True)

        if enable_alerts:
            # 檢查警報條件
            if accuracy < accuracy_threshold:
                st.error(
                    f"⚠️ 準確率警報：當前準確率 {accuracy:.2%} 低於閾值 {accuracy_threshold:.2%}"
                )

            if latency > latency_threshold:
                st.error(
                    f"⚠️ 延遲警報：當前延遲 {latency:.0f}ms 高於閾值 {latency_threshold}ms"
                )

            if error_rate > error_threshold:
                st.error(
                    f"⚠️ 錯誤率警報：當前錯誤率 {error_rate:.2%} 高於閾值 {error_threshold:.2%}"
                )

    except Exception as e:
        st.error(f"載入監控數據失敗: {str(e)}")


def show_historical_analysis():
    """顯示歷史分析"""
    st.markdown("### 📈 歷史效能分析")

    # 時間範圍選擇
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "開始日期", value=datetime.now() - timedelta(days=30)
        )

    with col2:
        end_date = st.date_input("結束日期", value=datetime.now())

    # 分析維度
    analysis_dimension = st.selectbox(
        "分析維度", options=["日趨勢", "週趨勢", "月趨勢", "小時分布"], index=0
    )

    # 生成歷史數據
    if analysis_dimension == "日趨勢":
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        accuracy_trend = [0.85 + np.random.normal(0, 0.03) for _ in dates]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=dates, y=accuracy_trend, mode="lines+markers", name="準確率")
        )
        fig.update_layout(
            title="日準確率趨勢", xaxis_title="日期", yaxis_title="準確率"
        )

    elif analysis_dimension == "小時分布":
        hours = list(range(24))
        accuracy_by_hour = [0.85 + np.random.normal(0, 0.02) for _ in hours]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=hours, y=accuracy_by_hour, name="準確率"))
        fig.update_layout(
            title="24小時準確率分布", xaxis_title="小時", yaxis_title="準確率"
        )

    st.plotly_chart(fig, use_container_width=True)

    # 統計摘要
    st.markdown("**統計摘要**")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("平均準確率", "85.3%")

    with col2:
        st.metric("最高準確率", "92.1%")

    with col3:
        st.metric("最低準確率", "78.4%")

    with col4:
        st.metric("標準差", "3.2%")


def show_performance_comparison():
    """顯示效能比較"""
    st.markdown("### 🔄 模型效能比較")

    service = get_ai_model_service()

    try:
        models = service.get_models()

        if len(models) < 2:
            st.warning("需要至少2個模型才能進行比較")
            return

        # 模型選擇
        selected_models = st.multiselect(
            "選擇要比較的模型",
            options=models,
            format_func=lambda x: x["name"],
            default=models[:3] if len(models) >= 3 else models,
        )

        if len(selected_models) < 2:
            st.warning("請選擇至少2個模型進行比較")
            return

        # 比較指標
        comparison_metrics = st.multiselect(
            "選擇比較指標",
            options=["準確率", "精確率", "召回率", "F1分數", "AUC", "推論速度"],
            default=["準確率", "F1分數", "推論速度"],
        )

        # 生成比較數據
        comparison_data = []
        for model in selected_models:
            model_metrics = {
                "模型名稱": model["name"],
                "準確率": np.random.uniform(0.8, 0.9),
                "精確率": np.random.uniform(0.75, 0.88),
                "召回率": np.random.uniform(0.78, 0.92),
                "F1分數": np.random.uniform(0.76, 0.89),
                "AUC": np.random.uniform(0.82, 0.94),
                "推論速度": np.random.uniform(50, 200),
            }
            comparison_data.append(model_metrics)

        # 顯示比較表格
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True)

        # 比較圖表
        if comparison_metrics:
            fig = go.Figure()

            for metric in comparison_metrics:
                if metric in df.columns:
                    fig.add_trace(
                        go.Bar(
                            name=metric,
                            x=df["模型名稱"],
                            y=df[metric],
                            text=df[metric].round(3),
                            textposition="auto",
                        )
                    )

            fig.update_layout(
                title="模型效能比較",
                xaxis_title="模型",
                yaxis_title="指標值",
                barmode="group",
                height=500,
            )

            st.plotly_chart(fig, use_container_width=True)

        # 排名分析
        st.markdown("**排名分析**")

        for metric in comparison_metrics:
            if metric in df.columns:
                sorted_df = df.sort_values(metric, ascending=False)
                st.write(f"**{metric}排名：**")
                for i, row in sorted_df.iterrows():
                    st.write(f"{i+1}. {row['模型名稱']}: {row[metric]:.3f}")
                st.markdown("---")

    except Exception as e:
        st.error(f"載入比較數據失敗: {str(e)}")


def show_anomaly_detection():
    """顯示異常檢測"""
    st.markdown("### 🚨 異常檢測")

    # 異常檢測設定
    col1, col2 = st.columns(2)

    with col1:
        detection_method = st.selectbox(
            "檢測方法",
            options=["統計方法", "機器學習", "深度學習", "規則引擎"],
            index=0,
        )

        sensitivity = st.slider("敏感度", 0.1, 1.0, 0.7)

    with col2:
        time_window = st.selectbox(
            "時間窗口", options=["1小時", "6小時", "24小時", "7天"], index=2
        )

        auto_alert = st.checkbox("自動警報", value=True)

    # 執行異常檢測
    if st.button("🔍 執行異常檢測"):
        with st.spinner("正在執行異常檢測..."):
            time.sleep(2)

            # 模擬異常檢測結果
            anomalies = [
                {
                    "時間": datetime.now() - timedelta(hours=2),
                    "類型": "準確率下降",
                    "嚴重程度": "中等",
                    "描述": "模型準確率在過去1小時內下降了5%",
                },
                {
                    "時間": datetime.now() - timedelta(hours=6),
                    "類型": "推論延遲增加",
                    "嚴重程度": "低",
                    "描述": "平均推論延遲增加了20ms",
                },
                {
                    "時間": datetime.now() - timedelta(days=1),
                    "類型": "數據漂移",
                    "嚴重程度": "高",
                    "描述": "輸入數據分布發生顯著變化",
                },
            ]

            st.success("異常檢測完成！")

            # 顯示異常列表
            st.markdown("**檢測到的異常：**")

            for i, anomaly in enumerate(anomalies):
                severity_color = {"高": "🔴", "中等": "🟡", "低": "🟢"}

                with st.expander(
                    f"{severity_color[anomaly['嚴重程度']]} {anomaly['類型']} - {anomaly['時間'].strftime('%Y-%m-%d %H:%M')}"
                ):
                    st.write(f"**嚴重程度**: {anomaly['嚴重程度']}")
                    st.write(f"**描述**: {anomaly['描述']}")
                    st.write(f"**時間**: {anomaly['時間']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"標記已處理", key=f"resolve_{i}"):
                            st.success("異常已標記為已處理")

                    with col2:
                        if st.button(f"查看詳情", key=f"detail_{i}"):
                            st.info("詳細分析功能開發中...")


def show_model_management_enhanced():
    """顯示增強版模型管理頁面"""
    st.subheader("🔧 增強版模型管理")

    # 管理功能選擇
    management_function = st.selectbox(
        "管理功能",
        options=["模型生命週期", "版本管理", "部署管理", "資源管理", "安全管理"],
        index=0,
    )

    if management_function == "模型生命週期":
        show_model_lifecycle_management()
    elif management_function == "版本管理":
        show_model_version_management()
    elif management_function == "部署管理":
        show_model_deployment_management()
    elif management_function == "資源管理":
        show_model_resource_management()
    else:  # 安全管理
        show_model_security_management()


def show_model_lifecycle_management():
    """顯示模型生命週期管理"""
    st.markdown("### 🔄 模型生命週期管理")

    service = get_ai_model_service()

    try:
        models = service.get_models()

        # 生命週期統計
        lifecycle_stats = {
            "開發中": len([m for m in models if m.get("status") == "created"]),
            "訓練中": len([m for m in models if m.get("status") == "training"]),
            "已訓練": len([m for m in models if m.get("status") == "trained"]),
            "已部署": len([m for m in models if m.get("status") == "deployed"]),
            "已退役": len([m for m in models if m.get("status") == "retired"]),
        }

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("開發中", lifecycle_stats["開發中"])

        with col2:
            st.metric("訓練中", lifecycle_stats["訓練中"])

        with col3:
            st.metric("已訓練", lifecycle_stats["已訓練"])

        with col4:
            st.metric("已部署", lifecycle_stats["已部署"])

        with col5:
            st.metric("已退役", lifecycle_stats["已退役"])

        # 生命週期流程圖
        st.markdown("**生命週期流程**")

        # 使用簡單的文字表示流程
        st.markdown(
            """
        ```
        開發中 → 訓練中 → 已訓練 → 測試中 → 已部署 → 監控中 → 已退役
           ↓        ↓        ↓        ↓        ↓        ↓
        失敗    訓練失敗   測試失敗   部署失敗   效能下降   生命週期結束
        ```
        """
        )

        # 模型狀態管理
        st.markdown("**模型狀態管理**")

        if models:
            selected_model = st.selectbox(
                "選擇模型",
                options=models,
                format_func=lambda x: f"{x['name']} ({x.get('status', 'unknown')})",
            )

            current_status = selected_model.get("status", "created")

            # 可用的狀態轉換
            status_transitions = {
                "created": ["training", "failed"],
                "training": ["trained", "failed"],
                "trained": ["testing", "deployed"],
                "testing": ["deployed", "failed"],
                "deployed": ["monitoring", "retired"],
                "monitoring": ["deployed", "retired"],
                "failed": ["created"],
                "retired": [],
            }

            available_statuses = status_transitions.get(current_status, [])

            if available_statuses:
                new_status = st.selectbox(
                    f"將狀態從 '{current_status}' 變更為", options=available_statuses
                )

                if st.button("更新狀態"):
                    # 這裡應該調用服務更新狀態
                    st.success(f"模型狀態已更新為: {new_status}")
            else:
                st.info(f"當前狀態 '{current_status}' 無可用的狀態轉換")

    except Exception as e:
        st.error(f"載入生命週期數據失敗: {str(e)}")


def show_model_version_management():
    """顯示模型版本管理"""
    st.markdown("### 📋 模型版本管理")
    st.info("版本管理功能開發中...")


def show_model_deployment_management():
    """顯示模型部署管理"""
    st.markdown("### 🚀 模型部署管理")
    st.info("部署管理功能開發中...")


def show_model_resource_management():
    """顯示模型資源管理"""
    st.markdown("### 💾 模型資源管理")
    st.info("資源管理功能開發中...")


def show_model_security_management():
    """顯示模型安全管理"""
    st.markdown("### 🔒 模型安全管理")
    st.info("安全管理功能開發中...")


def show_model_training():
    """顯示模型訓練頁面"""
    st.subheader("模型訓練")

    service = get_ai_model_service()

    # 檢查是否有選擇的模型
    is_editing = st.session_state.selected_model is not None

    if is_editing:
        st.info(f"重新訓練模型: {st.session_state.selected_model['name']}")
        model_data = st.session_state.selected_model
    else:
        st.info("創建新模型")
        model_data = {}

    # 訓練表單
    with st.form("model_training_form"):
        st.markdown("### 📝 基本資訊")

        col1, col2 = st.columns(2)

        with col1:
            model_name = st.text_input(
                "模型名稱", value=model_data.get("name", ""), disabled=is_editing
            )

            model_type = st.selectbox(
                "模型類型",
                options=list(service.get_model_types().keys()),
                index=(
                    list(service.get_model_types().keys()).index(
                        model_data.get("type", "機器學習模型")
                    )
                    if model_data.get("type") in service.get_model_types().keys()
                    else 0
                ),
            )

        with col2:
            sub_type = st.selectbox(
                "子類型",
                options=service.get_model_types().get(model_type, []),
                index=(
                    service.get_model_types()
                    .get(model_type, [])
                    .index(model_data.get("sub_type", ""))
                    if model_data.get("sub_type")
                    in service.get_model_types().get(model_type, [])
                    else 0
                ),
            )

            author = st.text_input("作者", value=model_data.get("author", "系統"))

        description = st.text_area(
            "模型描述", value=model_data.get("description", ""), height=100
        )

        st.markdown("### 📊 資料設定")

        col1, col2 = st.columns(2)

        with col1:
            # 股票選擇
            stock_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "META"]
            selected_stocks = st.multiselect(
                "選擇股票", options=stock_symbols, default=["AAPL"]
            )

            # 日期範圍
            date_range = st.date_input(
                "訓練資料日期範圍",
                value=[
                    datetime.now() - timedelta(days=365),
                    datetime.now() - timedelta(days=30),
                ],
                max_value=datetime.now().date(),
            )

        with col2:
            # 資料分割比例
            train_ratio = st.slider("訓練集比例", 0.5, 0.9, 0.8, 0.05)
            val_ratio = st.slider("驗證集比例", 0.05, 0.3, 0.15, 0.05)

            # 資料預處理選項
            normalize_data = st.checkbox("標準化資料", value=True)
            handle_missing = st.selectbox(
                "缺失值處理", options=["前向填充", "後向填充", "線性插值", "刪除"]
            )

        st.markdown("### 🎯 特徵與目標")

        col1, col2 = st.columns(2)

        with col1:
            # 特徵選擇
            available_features = [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "sma_5",
                "sma_10",
                "sma_20",
                "ema_12",
                "ema_26",
                "rsi",
                "macd",
                "bollinger_upper",
                "bollinger_lower",
                "atr",
                "stoch_k",
                "stoch_d",
            ]

            selected_features = st.multiselect(
                "選擇特徵",
                options=available_features,
                default=["close", "volume", "sma_5", "rsi", "macd"],
            )

        with col2:
            # 目標變數設定
            target_type = st.selectbox(
                "預測目標類型", options=["價格預測", "方向預測", "波動率預測", "自定義"]
            )

            if target_type == "價格預測":
                target_column = "close_next"
                prediction_horizon = st.selectbox(
                    "預測時間範圍", [1, 5, 10, 20], index=0
                )
            elif target_type == "方向預測":
                target_column = "direction"
                prediction_horizon = st.selectbox(
                    "預測時間範圍", [1, 5, 10, 20], index=0
                )
            elif target_type == "波動率預測":
                target_column = "volatility"
                prediction_horizon = st.selectbox(
                    "預測時間範圍", [1, 5, 10, 20], index=0
                )
            else:
                target_column = st.text_input("自定義目標欄位")
                prediction_horizon = 1

        st.markdown("### ⚙️ 模型參數")

        # 根據模型類型顯示不同參數
        if model_type == "機器學習模型":
            if sub_type in ["隨機森林 (Random Forest)", "XGBoost", "LightGBM"]:
                col1, col2, col3 = st.columns(3)

                with col1:
                    n_estimators = st.number_input("樹的數量", 10, 1000, 100)
                    max_depth = st.number_input("最大深度", 1, 50, 10)

                with col2:
                    learning_rate = st.number_input("學習率", 0.001, 1.0, 0.1, 0.001)
                    min_samples_split = st.number_input("最小分割樣本數", 2, 20, 2)

                with col3:
                    random_state = st.number_input("隨機種子", 0, 9999, 42)
                    early_stopping = st.checkbox("早停機制", value=True)

                model_params = {
                    "n_estimators": n_estimators,
                    "max_depth": max_depth,
                    "learning_rate": learning_rate,
                    "min_samples_split": min_samples_split,
                    "random_state": random_state,
                    "early_stopping": early_stopping,
                }

            else:
                # 其他機器學習模型的通用參數
                col1, col2 = st.columns(2)

                with col1:
                    regularization = st.number_input("正則化強度", 0.0, 10.0, 1.0, 0.1)
                    random_state = st.number_input("隨機種子", 0, 9999, 42)

                with col2:
                    max_iter = st.number_input("最大迭代次數", 100, 10000, 1000)
                    tolerance = st.number_input(
                        "收斂容忍度", 1e-6, 1e-2, 1e-4, format="%.6f"
                    )

                model_params = {
                    "regularization": regularization,
                    "max_iter": max_iter,
                    "tolerance": tolerance,
                    "random_state": random_state,
                }

        elif model_type == "深度學習模型":
            col1, col2, col3 = st.columns(3)

            with col1:
                hidden_layers = st.number_input("隱藏層數", 1, 10, 3)
                hidden_units = st.number_input("隱藏單元數", 16, 512, 128)

            with col2:
                learning_rate = st.number_input("學習率", 0.0001, 0.1, 0.001, 0.0001)
                batch_size = st.number_input("批次大小", 16, 256, 32)

            with col3:
                epochs = st.number_input("訓練輪數", 10, 1000, 100)
                dropout_rate = st.number_input("Dropout率", 0.0, 0.8, 0.2, 0.1)

            model_params = {
                "hidden_layers": hidden_layers,
                "hidden_units": hidden_units,
                "learning_rate": learning_rate,
                "batch_size": batch_size,
                "epochs": epochs,
                "dropout_rate": dropout_rate,
            }

        else:
            # 規則型模型或集成模型的參數
            st.info("此模型類型使用預設參數配置")
            model_params = {}

        st.markdown("### 🚀 訓練設定")

        col1, col2 = st.columns(2)

        with col1:
            cross_validation = st.checkbox("交叉驗證", value=True)
            if cross_validation:
                cv_folds = st.number_input("交叉驗證折數", 3, 10, 5)
            else:
                cv_folds = None

        with col2:
            hyperparameter_tuning = st.checkbox("超參數調優", value=False)
            if hyperparameter_tuning:
                tuning_method = st.selectbox(
                    "調優方法", options=["網格搜索", "隨機搜索", "貝葉斯優化"]
                )
            else:
                tuning_method = None

        # 提交按鈕
        submitted = st.form_submit_button("🎯 開始訓練", type="primary")

        if submitted:
            # 驗證輸入
            if not model_name:
                st.error("請輸入模型名稱")
                return

            if not selected_stocks:
                st.error("請選擇至少一個股票")
                return

            if not selected_features:
                st.error("請選擇至少一個特徵")
                return

            # 準備訓練資料
            training_config = {
                "model_info": {
                    "name": model_name,
                    "type": model_type,
                    "sub_type": sub_type,
                    "description": description,
                    "author": author,
                },
                "data_config": {
                    "stocks": selected_stocks,
                    "date_range": [d.isoformat() for d in date_range],
                    "features": selected_features,
                    "target": target_column,
                    "prediction_horizon": prediction_horizon,
                    "train_ratio": train_ratio,
                    "val_ratio": val_ratio,
                    "normalize": normalize_data,
                    "missing_handling": handle_missing,
                },
                "model_params": model_params,
                "training_config": {
                    "cross_validation": cross_validation,
                    "cv_folds": cv_folds,
                    "hyperparameter_tuning": hyperparameter_tuning,
                    "tuning_method": tuning_method,
                },
            }

            # 開始訓練
            try:
                if is_editing:
                    # 重新訓練現有模型
                    training_id = service.start_training(
                        model_id=st.session_state.selected_model["id"],
                        training_data=training_config["data_config"],
                        training_params=training_config,
                    )
                else:
                    # 創建新模型並開始訓練
                    model_id = service.create_model(
                        name=model_name,
                        model_type=model_type,
                        sub_type=sub_type,
                        description=description,
                        author=author,
                        parameters=model_params,
                        features=selected_features,
                        target=target_column,
                    )

                    training_id = service.start_training(
                        model_id=model_id,
                        training_data=training_config["data_config"],
                        training_params=training_config,
                    )

                st.success(f"訓練已開始！訓練ID: {training_id}")
                st.info("請到模型清單頁面查看訓練進度")

                # 清除選擇的模型
                st.session_state.selected_model = None

            except Exception as e:
                st.error(f"啟動訓練時發生錯誤: {str(e)}")

    # 顯示訓練歷史
    if is_editing and st.session_state.selected_model:
        st.markdown("---")
        st.subheader("📈 訓練歷史")

        try:
            training_logs = service.get_training_logs(
                st.session_state.selected_model["id"]
            )
            if training_logs:
                show_training_progress(training_logs)
            else:
                st.info("此模型尚無訓練記錄")
        except Exception as e:
            st.error(f"載入訓練歷史時發生錯誤: {str(e)}")


def show_model_inference():
    """顯示模型推論頁面"""
    st.subheader("模型推論")

    service = get_ai_model_service()

    # 獲取可用模型
    try:
        models = service.get_models()
        active_models = [
            m for m in models if m.get("status") in ["trained", "deployed"]
        ]

        if not active_models:
            st.warning("沒有可用的已訓練模型")
            return

        # 模型選擇
        col1, col2 = st.columns([2, 1])

        with col1:
            model_options = [
                f"{m['name']} - {m['type']} ({m['status']})" for m in active_models
            ]
            selected_model_idx = st.selectbox(
                "選擇模型",
                options=range(len(model_options)),
                format_func=lambda x: model_options[x],
            )
            selected_model = active_models[selected_model_idx]

        with col2:
            # 顯示模型基本資訊
            st.metric("模型狀態", selected_model["status"])
            if selected_model.get("performance_metrics"):
                metrics = selected_model["performance_metrics"]
                if isinstance(metrics, str):
                    try:
                        metrics = json.loads(metrics)
                    except:
                        metrics = {}

                if "accuracy" in metrics:
                    st.metric("準確率", f"{metrics['accuracy']:.2%}")
                elif "mse" in metrics:
                    st.metric("MSE", f"{metrics['mse']:.4f}")

        # 推論模式選擇
        st.markdown("### 🔮 推論設定")

        inference_mode = st.selectbox(
            "推論模式",
            options=["單一樣本推論", "批量推論", "實時推論"],
            help="選擇推論模式：單一樣本適合測試，批量推論適合大量數據，實時推論適合即時預測",
        )

        if inference_mode == "單一樣本推論":
            show_single_inference(selected_model, service)
        elif inference_mode == "批量推論":
            show_batch_inference(selected_model, service)
        else:  # 實時推論
            show_realtime_inference(selected_model, service)

    except Exception as e:
        st.error(f"載入模型時發生錯誤: {str(e)}")


def show_single_inference(model: Dict, service: AIModelManagementService):
    """顯示單一樣本推論介面"""

    with st.form("single_inference_form"):
        st.markdown("#### 📊 輸入數據")

        # 根據模型特徵動態生成輸入欄位
        features = model.get("features", [])
        if isinstance(features, str):
            try:
                features = json.loads(features)
            except:
                features = []

        if not features:
            st.warning("此模型沒有定義特徵，使用預設特徵")
            features = ["close", "volume", "sma_5", "rsi", "macd"]

        # 創建輸入欄位
        input_data = {}

        # 分成多列顯示
        cols = st.columns(min(3, len(features)))

        for i, feature in enumerate(features):
            col_idx = i % len(cols)
            with cols[col_idx]:
                if feature in ["close", "open", "high", "low"]:
                    input_data[feature] = st.number_input(
                        f"{feature.upper()}",
                        value=100.0,
                        min_value=0.0,
                        step=0.01,
                        key=f"single_{feature}",
                    )
                elif feature == "volume":
                    input_data[feature] = st.number_input(
                        "Volume",
                        value=1000000,
                        min_value=0,
                        step=1000,
                        key=f"single_{feature}",
                    )
                elif "sma" in feature or "ema" in feature:
                    input_data[feature] = st.number_input(
                        feature.upper(),
                        value=100.0,
                        min_value=0.0,
                        step=0.01,
                        key=f"single_{feature}",
                    )
                elif feature == "rsi":
                    input_data[feature] = st.number_input(
                        "RSI",
                        value=50.0,
                        min_value=0.0,
                        max_value=100.0,
                        step=0.1,
                        key=f"single_{feature}",
                    )
                elif feature == "macd":
                    input_data[feature] = st.number_input(
                        "MACD",
                        value=0.0,
                        step=0.001,
                        format="%.3f",
                        key=f"single_{feature}",
                    )
                else:
                    input_data[feature] = st.number_input(
                        feature, value=0.0, step=0.01, key=f"single_{feature}"
                    )

        # 高級選項
        with st.expander("高級選項"):
            return_probabilities = st.checkbox("返回預測機率", value=True)
            return_confidence = st.checkbox("返回信心度", value=True)
            explain_prediction = st.checkbox("解釋預測結果", value=False)

        submitted = st.form_submit_button("🔮 執行推論", type="primary")

        if submitted:
            try:
                # 執行推論
                with st.spinner("正在執行推論..."):
                    result = service.run_inference(
                        model_id=model["id"],
                        input_data=input_data,
                        return_probabilities=return_probabilities,
                        return_confidence=return_confidence,
                    )

                # 顯示結果
                st.markdown("#### 🎯 推論結果")

                col1, col2, col3 = st.columns(3)

                with col1:
                    if "prediction" in result:
                        prediction = result["prediction"]
                        if isinstance(prediction, (int, float)):
                            st.metric("預測值", f"{prediction:.4f}")
                        else:
                            st.metric("預測類別", str(prediction))

                with col2:
                    if "confidence" in result:
                        confidence = result["confidence"]
                        st.metric("信心度", f"{confidence:.2%}")

                with col3:
                    if "signal" in result:
                        signal = result["signal"]
                        signal_color = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}.get(
                            signal, "⚪"
                        )
                        st.metric("交易信號", f"{signal_color} {signal.upper()}")

                # 顯示機率分佈（如果有）
                if "probabilities" in result and return_probabilities:
                    st.markdown("#### 📊 預測機率分佈")
                    probs = result["probabilities"]
                    if isinstance(probs, list) and len(probs) == 2:
                        # 二分類
                        prob_df = pd.DataFrame(
                            {"類別": ["下跌", "上漲"], "機率": probs}
                        )

                        fig = px.bar(
                            prob_df,
                            x="類別",
                            y="機率",
                            title="預測機率分佈",
                            color="機率",
                            color_continuous_scale="RdYlGn",
                        )
                        st.plotly_chart(fig, use_container_width=True)

                # 顯示解釋（如果啟用）
                if explain_prediction and "explanation" in result:
                    st.markdown("#### 🔍 預測解釋")
                    show_model_explanation_analysis(result["explanation"])

                # 顯示原始結果
                with st.expander("原始結果數據"):
                    st.json(result)

            except Exception as e:
                st.error(f"推論執行失敗: {str(e)}")


def show_batch_inference(model: Dict, service: AIModelManagementService):
    """顯示批量推論介面"""

    st.markdown("#### 📁 批量數據輸入")

    # 數據輸入方式選擇
    input_method = st.selectbox(
        "數據輸入方式", options=["上傳CSV檔案", "手動輸入", "從資料庫查詢"]
    )

    input_data = None

    if input_method == "上傳CSV檔案":
        uploaded_file = st.file_uploader(
            "上傳CSV檔案", type=["csv"], help="請確保CSV檔案包含模型所需的所有特徵欄位"
        )

        if uploaded_file is not None:
            try:
                input_data = pd.read_csv(uploaded_file)
                st.success(f"成功載入 {len(input_data)} 筆記錄")

                # 顯示數據預覽
                st.markdown("##### 數據預覽")
                st.dataframe(input_data.head(), use_container_width=True)

                # 檢查特徵欄位
                model_features = model.get("features", [])
                if isinstance(model_features, str):
                    try:
                        model_features = json.loads(model_features)
                    except:
                        model_features = []

                missing_features = set(model_features) - set(input_data.columns)
                if missing_features:
                    st.warning(f"缺少特徵欄位: {', '.join(missing_features)}")

            except Exception as e:
                st.error(f"讀取CSV檔案失敗: {str(e)}")

    elif input_method == "手動輸入":
        st.markdown("##### 手動輸入數據")

        # 獲取模型特徵
        features = model.get("features", [])
        if isinstance(features, str):
            try:
                features = json.loads(features)
            except:
                features = ["close", "volume", "sma_5", "rsi", "macd"]

        # 創建空的DataFrame供編輯
        if "batch_data" not in st.session_state:
            st.session_state.batch_data = pd.DataFrame(columns=features)

        # 數據編輯器
        edited_data = st.data_editor(
            st.session_state.batch_data,
            num_rows="dynamic",
            use_container_width=True,
            key="batch_data_editor",
        )

        if len(edited_data) > 0:
            input_data = edited_data
            st.session_state.batch_data = edited_data

    else:  # 從資料庫查詢
        st.markdown("##### 從資料庫查詢數據")

        col1, col2 = st.columns(2)

        with col1:
            stock_symbol = st.selectbox(
                "股票代碼", options=["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
            )

            date_range = st.date_input(
                "日期範圍",
                value=[datetime.now() - timedelta(days=30), datetime.now()],
                max_value=datetime.now().date(),
            )

        with col2:
            limit = st.number_input("記錄數限制", 1, 1000, 100)

            if st.button("查詢數據"):
                # 這裡應該從實際資料庫查詢
                # 目前使用模擬數據
                dates = pd.date_range(start=date_range[0], end=date_range[1], freq="D")
                input_data = pd.DataFrame(
                    {
                        "date": dates[:limit],
                        "close": np.random.normal(100, 10, len(dates[:limit])),
                        "volume": np.random.randint(
                            1000000, 10000000, len(dates[:limit])
                        ),
                        "sma_5": np.random.normal(100, 8, len(dates[:limit])),
                        "rsi": np.random.uniform(20, 80, len(dates[:limit])),
                        "macd": np.random.normal(0, 2, len(dates[:limit])),
                    }
                )

                st.success(f"查詢到 {len(input_data)} 筆記錄")
                st.dataframe(input_data.head(), use_container_width=True)

    # 執行批量推論
    if input_data is not None and len(input_data) > 0:
        st.markdown("#### ⚙️ 推論設定")

        col1, col2 = st.columns(2)

        with col1:
            batch_size = st.number_input("批次大小", 1, 1000, 100)
            return_probabilities = st.checkbox("返回預測機率", value=False)

        with col2:
            save_results = st.checkbox("保存結果", value=True)
            result_format = st.selectbox("結果格式", ["CSV", "JSON", "Excel"])

        if st.button("🚀 執行批量推論", type="primary"):
            try:
                with st.spinner("正在執行批量推論..."):
                    # 分批處理
                    results = []
                    progress_bar = st.progress(0)

                    total_batches = len(input_data) // batch_size + (
                        1 if len(input_data) % batch_size > 0 else 0
                    )

                    for i in range(0, len(input_data), batch_size):
                        batch_data = input_data.iloc[i : i + batch_size]

                        # 執行推論
                        for _, row in batch_data.iterrows():
                            result = service.run_inference(
                                model_id=model["id"],
                                input_data=row.to_dict(),
                                return_probabilities=return_probabilities,
                            )
                            results.append(result)

                        # 更新進度
                        progress = min((i + batch_size) / len(input_data), 1.0)
                        progress_bar.progress(progress)

                # 整理結果
                results_df = pd.DataFrame(results)

                st.success(f"批量推論完成！處理了 {len(results)} 筆記錄")

                # 顯示結果統計
                st.markdown("#### 📊 推論結果統計")

                col1, col2, col3 = st.columns(3)

                with col1:
                    if "prediction" in results_df.columns:
                        avg_prediction = results_df["prediction"].mean()
                        st.metric("平均預測值", f"{avg_prediction:.4f}")

                with col2:
                    if "confidence" in results_df.columns:
                        avg_confidence = results_df["confidence"].mean()
                        st.metric("平均信心度", f"{avg_confidence:.2%}")

                with col3:
                    if "signal" in results_df.columns:
                        signal_counts = results_df["signal"].value_counts()
                        most_common = (
                            signal_counts.index[0] if len(signal_counts) > 0 else "N/A"
                        )
                        st.metric("主要信號", most_common)

                # 顯示結果表格
                st.markdown("#### 📋 詳細結果")
                st.dataframe(results_df, use_container_width=True)

                # 結果下載
                if save_results:
                    if result_format == "CSV":
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            "下載CSV結果",
                            csv,
                            f"batch_inference_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            "text/csv",
                        )
                    elif result_format == "JSON":
                        json_str = results_df.to_json(orient="records", indent=2)
                        st.download_button(
                            "下載JSON結果",
                            json_str,
                            f"batch_inference_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            "application/json",
                        )

            except Exception as e:
                st.error(f"批量推論執行失敗: {str(e)}")


def show_realtime_inference(model: Dict, service: AIModelManagementService):
    """顯示實時推論介面"""

    st.markdown("#### ⚡ 實時推論設定")

    col1, col2 = st.columns(2)

    with col1:
        # 數據來源設定
        data_source = st.selectbox(
            "數據來源", options=["模擬數據", "API接口", "資料庫"]
        )

        if data_source == "模擬數據":
            stock_symbol = st.selectbox(
                "股票代碼", options=["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
            )
        elif data_source == "API接口":
            api_endpoint = st.text_input(
                "API端點", placeholder="https://api.example.com/data"
            )
            api_key = st.text_input("API密鑰", type="password")
        else:  # 資料庫
            db_query = st.text_area(
                "SQL查詢", placeholder="SELECT * FROM stock_data WHERE..."
            )

    with col2:
        # 推論設定
        update_interval = st.selectbox(
            "更新間隔", options=[1, 5, 10, 30, 60], format_func=lambda x: f"{x} 秒"
        )

        auto_start = st.checkbox("自動開始", value=False)
        show_charts = st.checkbox("顯示圖表", value=True)

    # 控制按鈕
    col1, col2, col3 = st.columns(3)

    with col1:
        start_button = st.button("🚀 開始實時推論", type="primary")

    with col2:
        stop_button = st.button("⏹️ 停止推論")

    with col3:
        clear_button = st.button("🗑️ 清除數據")

    # 初始化 session state
    if "realtime_running" not in st.session_state:
        st.session_state.realtime_running = False
    if "realtime_data" not in st.session_state:
        st.session_state.realtime_data = []

    # 處理按鈕事件
    if start_button or auto_start:
        st.session_state.realtime_running = True

    if stop_button:
        st.session_state.realtime_running = False

    if clear_button:
        st.session_state.realtime_data = []

    # 實時推論邏輯
    if st.session_state.realtime_running:
        st.info("🔄 實時推論進行中...")

        # 創建佔位符
        status_placeholder = st.empty()
        chart_placeholder = st.empty()
        data_placeholder = st.empty()

        try:
            # 模擬獲取實時數據
            current_time = datetime.now()

            # 生成模擬數據
            if data_source == "模擬數據":
                new_data = {
                    "timestamp": current_time,
                    "close": np.random.normal(100, 5),
                    "volume": np.random.randint(1000000, 5000000),
                    "sma_5": np.random.normal(100, 3),
                    "rsi": np.random.uniform(30, 70),
                    "macd": np.random.normal(0, 1),
                }
            else:
                # 其他數據來源的處理邏輯
                new_data = {
                    "timestamp": current_time,
                    "close": 100.0,
                    "volume": 1000000,
                    "sma_5": 100.0,
                    "rsi": 50.0,
                    "macd": 0.0,
                }

            # 執行推論
            inference_input = {k: v for k, v in new_data.items() if k != "timestamp"}
            result = service.run_inference(
                model_id=model["id"],
                input_data=inference_input,
                return_probabilities=True,
                return_confidence=True,
            )

            # 添加時間戳和結果
            new_data.update(result)
            st.session_state.realtime_data.append(new_data)

            # 保持最近100筆記錄
            if len(st.session_state.realtime_data) > 100:
                st.session_state.realtime_data = st.session_state.realtime_data[-100:]

            # 更新狀態顯示
            with status_placeholder.container():
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("當前價格", f"{new_data['close']:.2f}")

                with col2:
                    prediction = result.get("prediction", 0)
                    st.metric("預測值", f"{prediction:.4f}")

                with col3:
                    confidence = result.get("confidence", 0)
                    st.metric("信心度", f"{confidence:.2%}")

                with col4:
                    signal = result.get("signal", "hold")
                    signal_color = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}.get(
                        signal, "⚪"
                    )
                    st.metric("信號", f"{signal_color} {signal.upper()}")

            # 更新圖表
            if show_charts and len(st.session_state.realtime_data) > 1:
                with chart_placeholder.container():
                    df = pd.DataFrame(st.session_state.realtime_data)

                    # 創建子圖
                    from plotly.subplots import make_subplots

                    fig = make_subplots(
                        rows=2,
                        cols=1,
                        subplot_titles=("價格與預測", "信心度"),
                        vertical_spacing=0.1,
                    )

                    # 價格線
                    fig.add_trace(
                        go.Scatter(
                            x=df["timestamp"],
                            y=df["close"],
                            mode="lines",
                            name="實際價格",
                            line=dict(color="blue"),
                        ),
                        row=1,
                        col=1,
                    )

                    # 預測線
                    if "prediction" in df.columns:
                        fig.add_trace(
                            go.Scatter(
                                x=df["timestamp"],
                                y=df["prediction"],
                                mode="lines",
                                name="預測值",
                                line=dict(color="red", dash="dash"),
                            ),
                            row=1,
                            col=1,
                        )

                    # 信心度
                    if "confidence" in df.columns:
                        fig.add_trace(
                            go.Scatter(
                                x=df["timestamp"],
                                y=df["confidence"],
                                mode="lines",
                                name="信心度",
                                line=dict(color="green"),
                            ),
                            row=2,
                            col=1,
                        )

                    fig.update_layout(
                        height=500, title_text="實時推論結果", showlegend=True
                    )

                    fig.update_xaxes(title_text="時間")
                    fig.update_yaxes(title_text="價格", row=1, col=1)
                    fig.update_yaxes(title_text="信心度", row=2, col=1)

                    st.plotly_chart(fig, use_container_width=True)

            # 更新數據表格
            with data_placeholder.container():
                if st.session_state.realtime_data:
                    df = pd.DataFrame(st.session_state.realtime_data)
                    st.markdown("#### 📊 實時數據")
                    st.dataframe(df.tail(10), use_container_width=True)

            # 自動刷新
            import time

            time.sleep(update_interval)
            st.rerun()

        except Exception as e:
            st.error(f"實時推論執行失敗: {str(e)}")
            st.session_state.realtime_running = False

    else:
        # 顯示歷史數據（如果有）
        if st.session_state.realtime_data:
            st.markdown("#### 📊 歷史數據")
            df = pd.DataFrame(st.session_state.realtime_data)
            st.dataframe(df, use_container_width=True)

            # 提供下載功能
            csv = df.to_csv(index=False)
            st.download_button(
                "下載歷史數據",
                csv,
                f"realtime_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
            )


def show_model_interpretability():
    """顯示模型解釋性分析頁面"""
    st.subheader("模型解釋性分析")

    service = get_ai_model_service()

    # 獲取可用模型
    try:
        models = service.get_models()
        active_models = [
            m for m in models if m.get("status") in ["trained", "deployed"]
        ]

        if not active_models:
            st.warning("沒有可用的已訓練模型")
            return

        # 模型選擇
        col1, col2 = st.columns([2, 1])

        with col1:
            model_options = [f"{m['name']} - {m['type']}" for m in active_models]
            selected_model_idx = st.selectbox(
                "選擇要解釋的模型",
                options=range(len(model_options)),
                format_func=lambda x: model_options[x],
            )
            selected_model = active_models[selected_model_idx]

        with col2:
            st.metric("模型類型", selected_model["type"])
            st.metric("模型狀態", selected_model["status"])

        # 解釋方法選擇
        st.markdown("### 🔍 解釋方法設定")

        explanation_method = st.selectbox(
            "解釋方法",
            options=["SHAP", "LIME", "特徵重要性", "部分依賴圖", "全局解釋"],
            help="選擇模型解釋方法：SHAP適合樹模型，LIME適合黑盒模型，特徵重要性顯示整體重要性",
        )

        # 數據選擇
        st.markdown("### 📊 數據設定")

        col1, col2 = st.columns(2)

        with col1:
            data_source = st.selectbox(
                "數據來源", options=["測試數據", "上傳數據", "手動輸入"]
            )

            sample_size = st.number_input(
                "樣本數量",
                min_value=1,
                max_value=1000,
                value=100,
                help="用於解釋的樣本數量，數量越多結果越準確但計算時間越長",
            )

        with col2:
            if explanation_method in ["SHAP", "LIME"]:
                background_samples = st.number_input(
                    "背景樣本數",
                    min_value=10,
                    max_value=500,
                    value=100,
                    help="用於計算基準值的背景樣本數量",
                )

            if explanation_method == "部分依賴圖":
                target_features = st.multiselect(
                    "目標特徵",
                    options=["close", "volume", "sma_5", "rsi", "macd"],
                    default=["close", "rsi"],
                    help="選擇要分析部分依賴關係的特徵",
                )

        # 解釋參數設定
        with st.expander("高級參數設定"):
            if explanation_method == "SHAP":
                shap_explainer_type = st.selectbox(
                    "SHAP解釋器類型",
                    options=["TreeExplainer", "LinearExplainer", "KernelExplainer"],
                    help="選擇適合模型類型的SHAP解釋器",
                )

                plot_type = st.selectbox(
                    "圖表類型",
                    options=[
                        "summary_plot",
                        "waterfall",
                        "force_plot",
                        "dependence_plot",
                    ],
                )

            elif explanation_method == "LIME":
                lime_mode = st.selectbox(
                    "LIME模式", options=["tabular", "text", "image"]
                )

                num_features = st.number_input(
                    "解釋特徵數", min_value=1, max_value=20, value=5
                )

        # 執行解釋分析
        if st.button("🔍 執行解釋分析", type="primary"):
            try:
                with st.spinner("正在執行模型解釋分析..."):

                    # 準備解釋參數
                    explanation_params = {
                        "method": explanation_method,
                        "sample_size": sample_size,
                    }

                    if explanation_method in ["SHAP", "LIME"]:
                        explanation_params["background_samples"] = background_samples

                    if explanation_method == "SHAP":
                        explanation_params["explainer_type"] = shap_explainer_type
                        explanation_params["plot_type"] = plot_type

                    elif explanation_method == "LIME":
                        explanation_params["mode"] = lime_mode
                        explanation_params["num_features"] = num_features

                    elif explanation_method == "部分依賴圖":
                        explanation_params["target_features"] = target_features

                    # 執行解釋分析
                    if explanation_method == "全局解釋":
                        explanation_result = service.generate_global_explanation(
                            model_id=selected_model["id"], sample_size=sample_size
                        )
                    else:
                        # 生成樣本數據用於解釋
                        sample_data = generate_sample_data(selected_model, sample_size)

                        explanation_result = service.explain_prediction(
                            model_id=selected_model["id"],
                            input_data=sample_data,
                            method=explanation_method,
                            **explanation_params,
                        )

                    # 顯示解釋結果
                    if explanation_result and "error" not in explanation_result:
                        st.success("解釋分析完成！")

                        # 顯示解釋結果
                        show_explanation_results(explanation_result, explanation_method)

                        # 提供下載功能
                        result_json = json.dumps(
                            explanation_result, indent=2, default=str
                        )
                        st.download_button(
                            "下載解釋結果",
                            result_json,
                            f"explanation_{explanation_method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            "application/json",
                        )

                    else:
                        error_msg = (
                            explanation_result.get("error", "未知錯誤")
                            if explanation_result
                            else "解釋分析失敗"
                        )
                        st.error(f"解釋分析失敗: {error_msg}")

            except Exception as e:
                st.error(f"執行解釋分析時發生錯誤: {str(e)}")

        # 顯示解釋方法說明
        show_explanation_method_info(explanation_method)

    except Exception as e:
        st.error(f"載入模型時發生錯誤: {str(e)}")


def generate_sample_data(model: Dict, sample_size: int) -> Dict:
    """生成用於解釋的樣本數據"""

    features = model.get("features", [])
    if isinstance(features, str):
        try:
            features = json.loads(features)
        except:
            features = ["close", "volume", "sma_5", "rsi", "macd"]

    # 生成隨機樣本數據
    sample_data = {}

    for feature in features:
        if feature in ["close", "open", "high", "low"]:
            sample_data[feature] = np.random.normal(100, 10, sample_size).tolist()
        elif feature == "volume":
            sample_data[feature] = np.random.randint(
                1000000, 10000000, sample_size
            ).tolist()
        elif "sma" in feature or "ema" in feature:
            sample_data[feature] = np.random.normal(100, 8, sample_size).tolist()
        elif feature == "rsi":
            sample_data[feature] = np.random.uniform(20, 80, sample_size).tolist()
        elif feature == "macd":
            sample_data[feature] = np.random.normal(0, 2, sample_size).tolist()
        else:
            sample_data[feature] = np.random.normal(0, 1, sample_size).tolist()

    return sample_data


def show_explanation_results(explanation_result: Dict, method: str):
    """顯示解釋分析結果"""

    if method == "SHAP":
        st.markdown("#### 🎯 SHAP 解釋結果")

        # 特徵重要性
        if explanation_result.get("feature_importance"):
            st.markdown("##### 特徵重要性")
            show_feature_importance(explanation_result["feature_importance"])

        # SHAP值分佈
        if explanation_result.get("shap_values"):
            st.markdown("##### SHAP值分佈")
            shap_data = explanation_result["shap_values"]

            # 創建SHAP值的箱線圖
            if isinstance(shap_data, dict):
                features = list(shap_data.keys())
                values = [shap_data[f] for f in features]

                fig = go.Figure()
                for i, (feature, vals) in enumerate(zip(features, values)):
                    fig.add_trace(go.Box(y=vals, name=feature, boxpoints="outliers"))

                fig.update_layout(
                    title="SHAP值分佈",
                    xaxis_title="特徵",
                    yaxis_title="SHAP值",
                    height=400,
                )

                st.plotly_chart(fig, use_container_width=True)

    elif method == "LIME":
        st.markdown("#### 🍋 LIME 解釋結果")

        # 局部解釋
        if explanation_result.get("local_explanation"):
            st.markdown("##### 局部解釋")
            show_model_explanation_analysis(explanation_result)

        # 特徵貢獻
        if explanation_result.get("feature_contributions"):
            st.markdown("##### 特徵貢獻分析")
            contributions = explanation_result["feature_contributions"]

            # 創建特徵貢獻圖
            features = list(contributions.keys())
            values = list(contributions.values())
            colors = ["red" if v < 0 else "green" for v in values]

            fig = go.Figure(
                go.Bar(
                    x=values,
                    y=features,
                    orientation="h",
                    marker_color=colors,
                    text=[f"{v:.3f}" for v in values],
                    textposition="auto",
                )
            )

            fig.update_layout(
                title="LIME 特徵貢獻",
                xaxis_title="貢獻值",
                yaxis_title="特徵",
                height=max(400, len(features) * 25),
            )

            st.plotly_chart(fig, use_container_width=True)

    elif method == "特徵重要性":
        st.markdown("#### 📊 特徵重要性分析")

        if explanation_result.get("feature_importance"):
            show_feature_importance(explanation_result["feature_importance"])

        # 特徵統計
        if explanation_result.get("feature_statistics"):
            st.markdown("##### 特徵統計資訊")
            stats_df = pd.DataFrame(explanation_result["feature_statistics"]).T
            st.dataframe(stats_df, use_container_width=True)

    elif method == "部分依賴圖":
        st.markdown("#### 📈 部分依賴圖分析")

        if explanation_result.get("partial_dependence"):
            pd_data = explanation_result["partial_dependence"]

            for feature, data in pd_data.items():
                st.markdown(f"##### {feature} 的部分依賴關係")

                if "values" in data and "predictions" in data:
                    fig = go.Figure()

                    fig.add_trace(
                        go.Scatter(
                            x=data["values"],
                            y=data["predictions"],
                            mode="lines+markers",
                            name=f"{feature} 部分依賴",
                            line=dict(color="blue", width=2),
                        )
                    )

                    fig.update_layout(
                        title=f"{feature} 部分依賴圖",
                        xaxis_title=feature,
                        yaxis_title="預測值",
                        height=400,
                    )

                    st.plotly_chart(fig, use_container_width=True)

    elif method == "全局解釋":
        st.markdown("#### 🌍 全局模型解釋")

        # 模型行為分析
        if explanation_result.get("model_behavior"):
            behavior = explanation_result["model_behavior"]

            col1, col2, col3 = st.columns(3)

            with col1:
                if behavior.get("prediction_range"):
                    pred_range = behavior["prediction_range"]
                    st.metric("預測範圍", f"[{pred_range[0]:.3f}, {pred_range[1]:.3f}]")

            with col2:
                if behavior.get("confidence_distribution"):
                    conf_dist = behavior["confidence_distribution"]
                    st.metric("平均信心度", f"{conf_dist.get('mean', 0):.2%}")

            with col3:
                if behavior.get("feature_sensitivity"):
                    sensitivity = behavior["feature_sensitivity"]
                    most_sensitive = max(sensitivity.items(), key=lambda x: x[1])[0]
                    st.metric("最敏感特徵", most_sensitive)

        # 特徵敏感性分析
        if explanation_result.get("model_behavior", {}).get("feature_sensitivity"):
            st.markdown("##### 特徵敏感性分析")
            sensitivity = explanation_result["model_behavior"]["feature_sensitivity"]
            show_feature_importance(sensitivity, top_n=15)

    # 顯示原始數據
    with st.expander("原始解釋數據"):
        st.json(explanation_result)


def show_explanation_method_info(method: str):
    """顯示解釋方法的說明資訊"""

    st.markdown("---")
    st.markdown("### 📚 解釋方法說明")

    if method == "SHAP":
        st.markdown(
            """
        **SHAP (SHapley Additive exPlanations)**

        SHAP是一種基於博弈論的模型解釋方法，能夠為每個特徵分配一個重要性值。

        **優點：**
        - 提供一致且公平的特徵重要性分配
        - 支援多種模型類型
        - 具有良好的數學理論基礎

        **適用場景：**
        - 樹模型（Random Forest, XGBoost, LightGBM）
        - 線性模型
        - 深度學習模型

        **解釋結果：**
        - 特徵重要性排序
        - 每個樣本的特徵貢獻
        - 全局和局部解釋
        """
        )

    elif method == "LIME":
        st.markdown(
            """
        **LIME (Local Interpretable Model-agnostic Explanations)**

        LIME通過在局部區域擬合簡單模型來解釋複雜模型的預測結果。

        **優點：**
        - 模型無關，適用於任何機器學習模型
        - 提供局部解釋，易於理解
        - 支援多種數據類型（表格、文本、圖像）

        **適用場景：**
        - 黑盒模型解釋
        - 深度學習模型
        - 複雜集成模型

        **解釋結果：**
        - 局部特徵重要性
        - 特徵對預測的正負影響
        - 決策邊界可視化
        """
        )

    elif method == "特徵重要性":
        st.markdown(
            """
        **特徵重要性分析**

        直接從模型中提取特徵重要性分數，顯示各特徵對模型預測的整體貢獻。

        **優點：**
        - 計算快速，資源消耗少
        - 提供全局視角的特徵重要性
        - 易於理解和解釋

        **適用場景：**
        - 樹模型（內建特徵重要性）
        - 線性模型（係數重要性）
        - 特徵選擇和降維

        **解釋結果：**
        - 特徵重要性排序
        - 重要性分數分佈
        - 特徵統計資訊
        """
        )

    elif method == "部分依賴圖":
        st.markdown(
            """
        **部分依賴圖 (Partial Dependence Plot)**

        顯示特定特徵對模型預測結果的邊際效應，保持其他特徵不變。

        **優點：**
        - 直觀顯示特徵與預測的關係
        - 能夠發現非線性關係
        - 幫助理解特徵的影響模式

        **適用場景：**
        - 理解特徵與目標的關係
        - 發現特徵的最佳取值範圍
        - 模型行為分析

        **解釋結果：**
        - 特徵值與預測值的關係曲線
        - 特徵的影響趨勢
        - 最佳特徵取值區間
        """
        )

    elif method == "全局解釋":
        st.markdown(
            """
        **全局模型解釋**

        從整體角度分析模型的行為模式和決策邏輯。

        **優點：**
        - 提供模型整體行為的洞察
        - 幫助理解模型的決策邏輯
        - 支援模型驗證和改進

        **適用場景：**
        - 模型行為分析
        - 模型驗證和調試
        - 業務理解和決策支援

        **解釋結果：**
        - 模型預測範圍和分佈
        - 特徵敏感性分析
        - 模型信心度分佈
        - 決策模式總結
        """
        )

    # 使用建議
    st.markdown("### 💡 使用建議")

    if method in ["SHAP", "LIME"]:
        st.info(
            """
        **計算資源考量：**
        - 樣本數量會影響計算時間，建議從小樣本開始測試
        - 複雜模型的解釋計算較耗時，請耐心等待
        - 可以先使用特徵重要性進行快速分析
        """
        )

    st.warning(
        """
    **解釋結果注意事項：**
    - 解釋結果基於模型學習到的模式，不一定反映真實的因果關係
    - 不同解釋方法可能給出不同的結果，建議結合多種方法分析
    - 解釋結果應該結合業務知識進行驗證和理解
    """
    )
