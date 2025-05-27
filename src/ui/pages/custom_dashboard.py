"""自定義儀表板頁面

提供拖拽式儀表板創建、編輯和管理功能。

此模組提供以下功能：
- 儀表板列表管理
- 創建新儀表板
- 編輯現有儀表板
- 模板庫瀏覽和使用
- 儀表板匯入匯出

主要類別：
    無

主要函數：
    show_custom_dashboard: 主要頁面顯示函數
    show_dashboard_list: 顯示儀表板列表
    show_create_dashboard: 顯示創建儀表板頁面
    show_edit_dashboard: 顯示編輯儀表板頁面
    show_template_library: 顯示模板庫
    show_import_export: 顯示匯入匯出頁面
    filter_dashboards: 篩選儀表板
    render_dashboard_card: 渲染儀表板卡片

使用範例：
    from src.ui.pages.custom_dashboard import show_custom_dashboard
    show_custom_dashboard()

注意事項：
    - 依賴 dashboard_manager 進行儀表板管理
    - 依賴 widget_library 提供小工具支援
    - 需要適當的認證權限
    - 支援多種儀表板模板
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

from src.ui.components.dashboard.dashboard_editor import DashboardEditor
from src.ui.components.dashboard.widget_library import widget_library
from src.ui.utils.dashboard_manager import dashboard_manager, DashboardConfig
from src.ui.components.auth import require_auth

logger = logging.getLogger(__name__)


@require_auth
def show_custom_dashboard():
    """顯示自定義儀表板頁面"""
    st.set_page_config(
        page_title="自定義儀表板",
        page_icon="🎨",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 頁面標題
    st.title("🎨 自定義儀表板")
    st.markdown("---")

    # 側邊欄導航
    with st.sidebar:
        st.header("🎛️ 儀表板管理")

        page_mode = st.selectbox(
            "選擇模式",
            ["儀表板列表", "創建新儀表板", "編輯儀表板", "模板庫", "匯入匯出"],
            index=0,
        )

        st.markdown("---")

    # 主要內容區域
    if page_mode == "儀表板列表":
        show_dashboard_list()
    elif page_mode == "創建新儀表板":
        show_create_dashboard()
    elif page_mode == "編輯儀表板":
        show_edit_dashboard()
    elif page_mode == "模板庫":
        show_template_library()
    elif page_mode == "匯入匯出":
        show_import_export()


def show_dashboard_list():
    """顯示儀表板列表"""
    st.subheader("📋 我的儀表板")

    # 獲取儀表板列表
    dashboards = dashboard_manager.list_dashboards()

    if dashboards:
        # 搜尋和篩選
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            search_query = st.text_input("🔍 搜尋儀表板", key="dashboard_search")

        with col2:
            template_filter = st.selectbox(
                "模板類型",
                [
                    "全部",
                    "custom",
                    "trading_monitor",
                    "technical_analysis",
                    "portfolio_overview",
                ],
            )

        with col3:
            sort_by = st.selectbox("排序方式", ["更新時間", "創建時間", "名稱"])
            if sort_by:
                st.info(f"按 {sort_by} 排序")

        # 篩選儀表板
        filtered_dashboards = filter_dashboards(
            dashboards, search_query, template_filter
        )

        # 顯示儀表板卡片
        for i in range(0, len(filtered_dashboards), 3):
            cols = st.columns(3)

            for j, col in enumerate(cols):
                if i + j < len(filtered_dashboards):
                    dashboard = filtered_dashboards[i + j]
                    with col:
                        render_dashboard_card(dashboard)
    else:
        st.info("🎯 您還沒有創建任何儀表板，點擊左側「創建新儀表板」開始吧！")


def filter_dashboards(
    dashboards: List[Dict[str, Any]], search_query: str, template_filter: str
) -> List[Dict[str, Any]]:
    """篩選儀表板

    Args:
        dashboards: 儀表板列表
        search_query: 搜尋關鍵字
        template_filter: 模板篩選

    Returns:
        篩選後的儀表板列表
    """
    filtered = dashboards

    # 搜尋篩選
    if search_query:
        filtered = [
            d
            for d in filtered
            if search_query.lower() in d["name"].lower()
            or search_query.lower() in d["description"].lower()
        ]

    # 模板類型篩選
    if template_filter != "全部":
        filtered = [d for d in filtered if d["template_type"] == template_filter]

    return filtered


def render_dashboard_card(dashboard: Dict[str, Any]):
    """渲染儀表板卡片

    Args:
        dashboard: 儀表板資訊
    """
    with st.container():
        st.markdown(
            f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <h4 style="margin: 0 0 8px 0;">{dashboard['name']}</h4>
            <p style="color: #666; font-size: 14px; margin: 0 0 12px 0;">
                {dashboard['description'] or '無描述'}
            </p>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <small style="color: #999;">
                    {dashboard['widget_count']} 個組件
                </small>
                <small style="color: #999;">
                    {datetime.fromisoformat(dashboard['updated_at']).strftime('%Y-%m-%d %H:%M')}
                </small>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 操作按鈕
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("👁️ 查看", key=f"view_{dashboard['config_id']}"):
                view_dashboard(dashboard["config_id"])

        with col2:
            if st.button("✏️ 編輯", key=f"edit_{dashboard['config_id']}"):
                edit_dashboard(dashboard["config_id"])

        with col3:
            if st.button("📋 複製", key=f"copy_{dashboard['config_id']}"):
                copy_dashboard(dashboard["config_id"])

        with col4:
            if st.button("🗑️ 刪除", key=f"delete_{dashboard['config_id']}"):
                delete_dashboard(dashboard["config_id"])


def show_create_dashboard():
    """顯示創建儀表板頁面"""
    st.subheader("🆕 創建新儀表板")

    # 基本資訊
    with st.form("create_dashboard_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("儀表板名稱", placeholder="例如：我的交易監控")
            description = st.text_area(
                "描述", placeholder="簡單描述這個儀表板的用途..."
            )

        with col2:
            template_type = st.selectbox(
                "選擇模板",
                [
                    ("custom", "空白儀表板"),
                    ("trading_monitor", "交易監控"),
                    ("technical_analysis", "技術分析"),
                    ("portfolio_overview", "投資組合概覽"),
                ],
                format_func=lambda x: x[1],
            )

            theme = st.selectbox("主題", ["light", "dark"])

        submitted = st.form_submit_button("🎨 創建儀表板", type="primary")

        if submitted:
            if name:
                try:
                    # 創建儀表板
                    config = dashboard_manager.create_dashboard(
                        name=name,
                        description=description,
                        template_type=template_type[0],
                    )
                    config.theme = theme

                    # 儲存配置
                    dashboard_manager.save_dashboard(config)

                    st.success(f"✅ 儀表板「{name}」創建成功！")

                    # 跳轉到編輯模式
                    st.session_state.edit_dashboard_id = config.config_id
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ 創建失敗：{e}")
            else:
                st.error("❌ 請輸入儀表板名稱")


def show_edit_dashboard():
    """顯示編輯儀表板頁面"""
    st.subheader("✏️ 編輯儀表板")

    # 選擇要編輯的儀表板
    dashboards = dashboard_manager.list_dashboards()

    if not dashboards:
        st.info("🎯 您還沒有創建任何儀表板")
        return

    # 儀表板選擇
    dashboard_options = {d["config_id"]: d["name"] for d in dashboards}

    # 檢查是否有預選的儀表板
    default_id = st.session_state.get("edit_dashboard_id")
    default_index = 0

    if default_id and default_id in dashboard_options:
        default_index = list(dashboard_options.keys()).index(default_id)

    selected_id = st.selectbox(
        "選擇儀表板",
        list(dashboard_options.keys()),
        format_func=lambda x: dashboard_options[x],
        index=default_index,
    )

    if selected_id:
        # 載入儀表板配置
        config = dashboard_manager.load_dashboard(selected_id)

        if config:
            # 創建編輯器
            editor = DashboardEditor()
            editor.render_editor(config)
        else:
            st.error("❌ 無法載入儀表板配置")


def show_template_library():
    """顯示模板庫"""
    st.subheader("📚 儀表板模板庫")

    # 獲取小工具模板
    templates = widget_library.get_widget_templates()
    if templates:
        st.info(
            f"💡 選擇模板快速創建包含預設組件的儀表板（共 {len(templates)} 個模板）"
        )
    else:
        st.info("💡 選擇模板快速創建包含預設組件的儀表板")

    # 預設儀表板模板
    dashboard_templates = {
        "交易監控儀表板": {
            "description": "包含股價監控、市場狀態、交易活動等組件",
            "template_type": "trading_monitor",
            "widgets": [
                "stock_price_card",
                "market_status",
                "candlestick_chart",
                "trading_activity",
            ],
        },
        "技術分析儀表板": {
            "description": "包含K線圖、技術指標、相關性分析等組件",
            "template_type": "technical_analysis",
            "widgets": [
                "candlestick_chart",
                "rsi_indicator",
                "macd_indicator",
                "bollinger_bands",
            ],
        },
        "投資組合儀表板": {
            "description": "包含投資組合摘要、資產配置、績效分析等組件",
            "template_type": "portfolio_overview",
            "widgets": ["portfolio_summary", "allocation_pie", "performance_chart"],
        },
    }

    # 顯示模板卡片
    for template_name, template_info in dashboard_templates.items():
        with st.expander(f"📋 {template_name}", expanded=False):
            st.write(template_info["description"])

            st.write("**包含組件：**")
            for widget_type in template_info["widgets"]:
                widget_info = widget_library.get_widget_info(widget_type)
                if widget_info:
                    st.write(f"• {widget_info['name']}")

            if st.button(
                f"使用此模板", key=f"use_template_{template_info['template_type']}"
            ):
                use_template(template_info)


def show_import_export():
    """顯示匯入匯出頁面"""
    st.subheader("📤📥 匯入匯出")

    tab1, tab2 = st.tabs(["匯出儀表板", "匯入儀表板"])

    with tab1:
        st.write("### 匯出儀表板配置")

        dashboards = dashboard_manager.list_dashboards()

        if dashboards:
            dashboard_options = {d["config_id"]: d["name"] for d in dashboards}

            selected_id = st.selectbox(
                "選擇要匯出的儀表板",
                list(dashboard_options.keys()),
                format_func=lambda x: dashboard_options[x],
                key="export_dashboard",
            )

            if st.button("📤 匯出配置"):
                export_config = dashboard_manager.export_dashboard(selected_id)
                if export_config:
                    st.download_button(
                        label="💾 下載配置檔案",
                        data=export_config,
                        file_name=f"dashboard_{dashboard_options[selected_id]}.json",
                        mime="application/json",
                    )

                    # 顯示配置預覽
                    with st.expander("配置預覽"):
                        st.code(export_config, language="json")
        else:
            st.info("沒有可匯出的儀表板")

    with tab2:
        st.write("### 匯入儀表板配置")

        # 文件上傳
        uploaded_file = st.file_uploader(
            "選擇配置檔案", type=["json"], help="上傳之前匯出的儀表板配置檔案"
        )

        if uploaded_file:
            try:
                # 讀取檔案內容
                config_data = uploaded_file.read().decode("utf-8")

                # 顯示配置預覽
                with st.expander("配置預覽"):
                    st.code(config_data, language="json")

                if st.button("📥 匯入配置"):
                    config = dashboard_manager.import_dashboard(config_data)
                    if config:
                        st.success(f"✅ 成功匯入儀表板「{config.name}」")
                    else:
                        st.error("❌ 匯入失敗，請檢查配置檔案格式")

            except Exception as e:
                st.error(f"❌ 讀取檔案失敗：{e}")


def view_dashboard(dashboard_id: str):
    """查看儀表板

    Args:
        dashboard_id: 儀表板ID
    """
    config = dashboard_manager.load_dashboard(dashboard_id)
    if config:
        st.session_state.view_dashboard_id = dashboard_id
        st.success(f"正在查看儀表板：{config.name}")
        # 這裡可以跳轉到查看模式
    else:
        st.error("無法載入儀表板")


def edit_dashboard(dashboard_id: str):
    """編輯儀表板

    Args:
        dashboard_id: 儀表板ID
    """
    st.session_state.edit_dashboard_id = dashboard_id
    st.rerun()


def copy_dashboard(dashboard_id: str):
    """複製儀表板

    Args:
        dashboard_id: 儀表板ID
    """
    config = dashboard_manager.load_dashboard(dashboard_id)
    if config:
        # 創建副本
        new_config = dashboard_manager.create_dashboard(
            name=f"{config.name} (副本)",
            description=config.description,
            template_type=config.template_type,
        )

        # 複製小工具
        new_config.widgets = config.widgets.copy()
        new_config.theme = config.theme
        new_config.auto_refresh = config.auto_refresh
        new_config.refresh_interval = config.refresh_interval

        # 儲存副本
        dashboard_manager.save_dashboard(new_config)
        st.success(f"✅ 已複製儀表板「{config.name}」")
        st.rerun()
    else:
        st.error("❌ 複製失敗")


def delete_dashboard(dashboard_id: str):
    """刪除儀表板

    Args:
        dashboard_id: 儀表板ID
    """
    config = dashboard_manager.load_dashboard(dashboard_id)
    if config:
        # 確認刪除
        if st.button(
            f"⚠️ 確認刪除「{config.name}」", key=f"confirm_delete_{dashboard_id}"
        ):
            if dashboard_manager.delete_dashboard(dashboard_id):
                st.success(f"✅ 已刪除儀表板「{config.name}」")
                st.rerun()
            else:
                st.error("❌ 刪除失敗")


def use_template(template_info: Dict[str, Any]):
    """使用模板創建儀表板

    Args:
        template_info: 模板資訊
    """
    # 生成模板名稱
    template_name = f"基於模板的儀表板 - {datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        config = dashboard_manager.create_dashboard(
            name=template_name,
            description=template_info["description"],
            template_type=template_info["template_type"],
        )

        dashboard_manager.save_dashboard(config)
        st.success(f"✅ 已使用模板創建儀表板「{template_name}」")

        # 跳轉到編輯模式
        st.session_state.edit_dashboard_id = config.config_id
        st.rerun()

    except Exception as e:
        st.error(f"❌ 使用模板失敗：{e}")


if __name__ == "__main__":
    show_custom_dashboard()
