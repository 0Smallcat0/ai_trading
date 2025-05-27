"""觸控導航組件模組

此模組提供專門針對觸控裝置優化的導航組件，包括滑動式導航和手勢支援。
"""

import streamlit as st
from typing import Dict, List, Any
from .utils import ResponsiveUtils


class TouchNavigationComponents:
    """觸控導航組件類

    提供專門針對觸控裝置優化的導航組件，確保在手機和平板上
    提供良好的導航體驗。

    主要功能：
    - 滑動式導航
    - 手勢支援
    - 觸控友善的頁面切換

    設計原則：
    - 手勢直觀性
    - 適當的間距避免誤觸
    - 視覺回饋和觸覺回饋
    """

    @staticmethod
    def swipe_navigation(
        pages: List[Dict[str, Any]], current_page_key: str = "current_page"
    ) -> str:
        """滑動式導航

        創建支援滑動手勢的頁面導航。

        Args:
            pages: 頁面列表，每個元素包含 name 和 key
            current_page_key: 當前頁面的 session state 鍵

        Returns:
            str: 當前選中的頁面鍵
        """
        if ResponsiveUtils.is_touch_device():
            # 手機版：使用滑動式導航
            st.markdown(
                """
                <style>
                .swipe-nav {
                    display: flex;
                    overflow-x: auto;
                    scroll-snap-type: x mandatory;
                    gap: 8px;
                    padding: 8px;
                    margin-bottom: 16px;
                }
                .swipe-nav-item {
                    flex: 0 0 auto;
                    scroll-snap-align: start;
                    padding: 12px 20px;
                    background: #f0f2f6;
                    border-radius: 20px;
                    white-space: nowrap;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    min-width: 120px;
                    text-align: center;
                }
                .swipe-nav-item.active {
                    background: #007bff;
                    color: white;
                }
                .swipe-nav-item:hover {
                    background: #e0e2e6;
                }
                .swipe-nav-item.active:hover {
                    background: #0056b3;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            current_page = st.session_state.get(current_page_key, pages[0]["key"])

            # 創建滑動導航 HTML
            nav_html = '<div class="swipe-nav">'
            for page in pages:
                active_class = "active" if page["key"] == current_page else ""
                nav_html += f"""
                <div class="swipe-nav-item {active_class}" 
                     onclick="selectPage('{page["key"]}')"
                     data-page="{page["key"]}">
                    {page.get("icon", "")} {page["name"]}
                </div>
                """
            nav_html += "</div>"

            # 添加 JavaScript 處理點擊事件
            nav_html += """
            <script>
            function selectPage(pageKey) {
                // 通過 Streamlit 的 postMessage API 更新 session state
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: { selected_page: pageKey }
                }, '*');
            }
            </script>
            """

            st.markdown(nav_html, unsafe_allow_html=True)

            # 使用選擇框作為備用方案
            page_names = [f"{p.get('icon', '')} {p['name']}" for p in pages]
            page_keys = [p["key"] for p in pages]
            current_index = (
                page_keys.index(current_page) if current_page in page_keys else 0
            )

            selected_index = st.selectbox(
                "選擇頁面",
                range(len(pages)),
                index=current_index,
                format_func=lambda i: page_names[i],
                key=f"{current_page_key}_selector",
            )

            selected_page = page_keys[selected_index]
            st.session_state[current_page_key] = selected_page

            return selected_page
        else:
            # 桌面版：使用標準標籤頁
            page_names = [f"{p.get('icon', '')} {p['name']}" for p in pages]
            tabs = st.tabs(page_names)

            current_page = st.session_state.get(current_page_key, pages[0]["key"])

            for i, (tab, page) in enumerate(zip(tabs, pages)):
                if page["key"] == current_page:
                    with tab:
                        st.session_state[current_page_key] = page["key"]
                        return page["key"]

            return pages[0]["key"]

    @staticmethod
    def touch_tabs(
        tab_configs: List[Dict[str, Any]], selected_key: str = "selected_tab"
    ) -> str:
        """觸控優化標籤頁

        創建針對觸控裝置優化的標籤頁組件。

        Args:
            tab_configs: 標籤頁配置列表
            selected_key: 選中標籤的 session state 鍵

        Returns:
            str: 當前選中的標籤鍵
        """
        if ResponsiveUtils.is_touch_device():
            # 手機版：使用下拉選單
            tab_names = [tab["name"] for tab in tab_configs]
            tab_keys = [tab["key"] for tab in tab_configs]

            current_tab = st.session_state.get(selected_key, tab_keys[0])
            current_index = (
                tab_keys.index(current_tab) if current_tab in tab_keys else 0
            )

            selected_index = st.selectbox(
                "選擇標籤",
                range(len(tab_configs)),
                index=current_index,
                format_func=lambda i: tab_names[i],
                key=f"{selected_key}_mobile",
            )

            selected_tab = tab_keys[selected_index]
            st.session_state[selected_key] = selected_tab

            return selected_tab
        else:
            # 桌面版：使用標準標籤頁
            tab_names = [tab["name"] for tab in tab_configs]
            tabs = st.tabs(tab_names)

            current_tab = st.session_state.get(selected_key, tab_configs[0]["key"])

            for i, (tab, config) in enumerate(zip(tabs, tab_configs)):
                if config["key"] == current_tab:
                    with tab:
                        st.session_state[selected_key] = config["key"]
                        return config["key"]

            return tab_configs[0]["key"]

    @staticmethod
    def touch_menu(
        menu_items: List[Dict[str, Any]], menu_key: str = "touch_menu"
    ) -> str:
        """觸控優化選單

        創建針對觸控裝置優化的選單組件。

        Args:
            menu_items: 選單項目列表
            menu_key: 選單的 session state 鍵

        Returns:
            str: 選中的選單項目鍵
        """
        if ResponsiveUtils.is_touch_device():
            # 觸控裝置使用較大的選單項目
            menu_style = """
            <style>
            .touch-menu-item {
                min-height: 48px;
                padding: 12px 16px;
                margin: 4px 0;
                border-radius: 8px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
            }
            .touch-menu-item:hover {
                background: #e9ecef;
                transform: translateY(-1px);
            }
            .touch-menu-item:active {
                transform: translateY(0);
                background: #dee2e6;
            }
            </style>
            """
            st.markdown(menu_style, unsafe_allow_html=True)

        # 使用選擇框實作
        item_names = [f"{item.get('icon', '')} {item['name']}" for item in menu_items]
        item_keys = [item["key"] for item in menu_items]

        current_item = st.session_state.get(menu_key, item_keys[0])
        current_index = (
            item_keys.index(current_item) if current_item in item_keys else 0
        )

        selected_index = st.selectbox(
            "選擇選單項目",
            range(len(menu_items)),
            index=current_index,
            format_func=lambda i: item_names[i],
            key=f"{menu_key}_selector",
        )

        selected_item = item_keys[selected_index]
        st.session_state[menu_key] = selected_item

        return selected_item
