# -*- coding: utf-8 -*-
"""
知識庫頁面

此模組提供金融量化知識庫的Web界面，
整合知識庫管理系統的所有功能。

主要功能：
- 知識搜索和瀏覽
- 分類導航
- 學習路徑推薦
- 知識統計展示
- 內容預覽和詳情

界面特色：
- 直觀的知識分類
- 強大的搜索功能
- 個性化推薦
- 學習進度追蹤
"""

import logging
import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

# 知識庫系統在MVP版本中已移除，使用存根實現
KNOWLEDGE_BASE_AVAILABLE = False
logging.info("知識庫系統在MVP版本中已簡化")

# 設定日誌
logger = logging.getLogger(__name__)


def show_knowledge_base():
    """顯示知識庫主頁面"""
    try:
        st.title("📚 金融量化知識庫")
        st.markdown("探索豐富的金融量化知識資源，提升您的專業技能。")
        
        # 檢查知識庫系統可用性
        if not KNOWLEDGE_BASE_AVAILABLE:
            st.info("📚 知識庫在MVP版本中已簡化")
            st.markdown("""
            ### 🎯 MVP版本功能說明

            知識庫的完整功能將在正式版本中提供，包括：
            - 📖 完整的量化交易知識庫
            - 🔍 智能搜索和推薦系統
            - 📊 知識圖譜和關聯分析
            - 💡 個性化學習路徑
            - 📝 用戶筆記和收藏功能

            ### 🚀 當前可用資源
            您可以通過以下方式獲取知識：
            - 查看**系統文檔** (docs/ 目錄)
            - 使用**回測分析**了解策略評估
            - 在**風險管理**頁面學習風險控制
            - 通過**AI模型管理**了解模型應用
            """)
            return
        
        # 初始化知識庫管理器
        if 'knowledge_manager' not in st.session_state:
            config = {
                'original_project_path': 'ai_quant_trade-0.0.1',
                'knowledge_base_path': 'docs/knowledge',
                'index_file': 'docs/knowledge/knowledge_index.json'
            }
            st.session_state.knowledge_manager = KnowledgeManager(config)
        
        knowledge_manager = st.session_state.knowledge_manager
        
        # 顯示知識庫儀表板
        show_knowledge_dashboard(knowledge_manager)
        
    except Exception as e:
        logger.error(f"顯示知識庫失敗: {e}")
        st.error("❌ 知識庫載入失敗，請重新整理頁面")


def show_knowledge_dashboard(knowledge_manager):
    """顯示知識庫儀表板"""
    try:
        # 頂部統計信息
        show_knowledge_stats(knowledge_manager)
        
        # 主要功能區域
        tab1, tab2, tab3, tab4 = st.tabs(["🔍 搜索瀏覽", "📂 分類導航", "🎯 學習路徑", "📊 知識統計"])
        
        with tab1:
            show_search_interface(knowledge_manager)
        
        with tab2:
            show_category_navigation(knowledge_manager)
        
        with tab3:
            show_learning_paths(knowledge_manager)
        
        with tab4:
            show_detailed_statistics(knowledge_manager)
        
    except Exception as e:
        logger.error(f"顯示知識庫儀表板失敗: {e}")
        st.error("❌ 知識庫儀表板載入失敗")


def show_knowledge_stats(knowledge_manager):
    """顯示知識庫統計信息"""
    try:
        # 獲取統計數據
        stats = knowledge_manager.get_statistics()
        
        # 顯示統計卡片
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📄 總知識項目",
                stats.get('total_items', 0),
                delta=f"+{stats.get('new_items_today', 0)} 今日新增"
            )
        
        with col2:
            st.metric(
                "📂 知識分類",
                stats.get('total_categories', 0)
            )
        
        with col3:
            st.metric(
                "🏷️ 標籤數量",
                stats.get('total_tags', 0)
            )
        
        with col4:
            st.metric(
                "🔄 最近更新",
                "今天",
                delta="2小時前"
            )
        
        # 快速操作按鈕
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 重新掃描知識庫", help="掃描原始項目中的新知識資源"):
                with st.spinner("正在掃描知識庫..."):
                    scan_results = knowledge_manager.scan_and_integrate_knowledge()
                    
                    if scan_results['errors']:
                        st.warning(f"掃描完成，但有 {len(scan_results['errors'])} 個錯誤")
                        with st.expander("查看錯誤詳情"):
                            for error in scan_results['errors']:
                                st.error(error)
                    else:
                        st.success(f"✅ 掃描完成！新增 {scan_results['new_items']} 個項目")
        
        with col2:
            if st.button("📊 生成統計報告", help="生成詳細的知識庫統計報告"):
                show_statistics_report(knowledge_manager)
        
        with col3:
            if st.button("💾 導出知識庫", help="導出知識庫數據"):
                st.info("導出功能開發中...")
        
    except Exception as e:
        logger.error(f"顯示知識庫統計失敗: {e}")
        st.error("❌ 統計信息載入失敗")


def show_search_interface(knowledge_manager):
    """顯示搜索界面"""
    try:
        st.subheader("🔍 知識搜索")
        
        # 搜索輸入
        search_query = st.text_input(
            "輸入搜索關鍵詞",
            placeholder="例如：移動平均、風險管理、Python..."
        )
        
        # 搜索選項
        col1, col2 = st.columns(2)
        
        with col1:
            search_limit = st.slider("搜索結果數量", 5, 50, 10)
        
        with col2:
            sort_by = st.selectbox(
                "排序方式",
                ["相關性", "創建時間", "更新時間", "難度等級"]
            )
        
        # 執行搜索
        if search_query:
            with st.spinner("正在搜索..."):
                results = knowledge_manager.search_knowledge(search_query, limit=search_limit)
                
                if results:
                    st.success(f"找到 {len(results)} 個相關結果")
                    
                    # 顯示搜索結果
                    for i, item in enumerate(results):
                        with st.expander(f"📄 {item.title}", expanded=(i == 0)):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.write(f"**分類**: {item.category} > {item.subcategory}")
                                st.write(f"**標籤**: {', '.join(item.tags[:5])}")
                                
                                # 內容預覽
                                preview = item.content[:300] + "..." if len(item.content) > 300 else item.content
                                st.markdown(f"**內容預覽**:\n{preview}")
                            
                            with col2:
                                st.write(f"**難度**: {'⭐' * item.difficulty_level}")
                                st.write(f"**閱讀時間**: {item.estimated_reading_time}分鐘")
                                st.write(f"**來源**: {item.metadata.get('source', 'unknown')}")
                                
                                if st.button(f"查看詳情", key=f"detail_{item.id}"):
                                    show_knowledge_detail(item)
                else:
                    st.info("未找到相關結果，請嘗試其他關鍵詞")
        
        # 熱門搜索
        st.subheader("🔥 熱門搜索")
        
        popular_searches = [
            "移動平均線", "RSI指標", "回測框架", "風險管理",
            "Python量化", "機器學習", "投資組合優化", "技術分析"
        ]
        
        cols = st.columns(4)
        for i, search_term in enumerate(popular_searches):
            with cols[i % 4]:
                if st.button(search_term, key=f"popular_{i}"):
                    st.rerun()
        
    except Exception as e:
        logger.error(f"顯示搜索界面失敗: {e}")
        st.error("❌ 搜索界面載入失敗")


def show_category_navigation(knowledge_manager):
    """顯示分類導航"""
    try:
        st.subheader("📂 知識分類")
        
        # 獲取分類統計
        stats = knowledge_manager.get_statistics()
        category_distribution = stats.get('category_distribution', {})
        
        if category_distribution:
            # 分類選擇
            selected_category = st.selectbox(
                "選擇知識分類",
                options=list(category_distribution.keys()),
                format_func=lambda x: f"{x} ({category_distribution[x]}個項目)"
            )
            
            if selected_category:
                # 獲取該分類的項目
                category_items = knowledge_manager.get_items_by_category(selected_category)
                
                if category_items:
                    st.write(f"**{selected_category}** 分類下共有 **{len(category_items)}** 個知識項目")
                    
                    # 子分類統計
                    subcategories = {}
                    for item in category_items:
                        if item.subcategory not in subcategories:
                            subcategories[item.subcategory] = 0
                        subcategories[item.subcategory] += 1
                    
                    if len(subcategories) > 1:
                        st.write("**子分類分佈**:")
                        for subcat, count in subcategories.items():
                            st.write(f"• {subcat}: {count}個項目")
                    
                    # 顯示項目列表
                    st.subheader("📋 項目列表")
                    
                    # 排序選項
                    sort_option = st.radio(
                        "排序方式",
                        ["難度等級", "閱讀時間", "創建時間"],
                        horizontal=True
                    )
                    
                    # 排序項目
                    if sort_option == "難度等級":
                        sorted_items = sorted(category_items, key=lambda x: x.difficulty_level)
                    elif sort_option == "閱讀時間":
                        sorted_items = sorted(category_items, key=lambda x: x.estimated_reading_time)
                    else:
                        sorted_items = sorted(category_items, key=lambda x: x.created_time, reverse=True)
                    
                    # 顯示項目
                    for item in sorted_items:
                        with st.container():
                            col1, col2, col3 = st.columns([3, 1, 1])
                            
                            with col1:
                                st.write(f"**{item.title}**")
                                st.caption(f"{item.subcategory} • {', '.join(item.tags[:3])}")
                            
                            with col2:
                                st.write(f"{'⭐' * item.difficulty_level}")
                                st.caption(f"{item.estimated_reading_time}分鐘")
                            
                            with col3:
                                if st.button("查看", key=f"view_{item.id}"):
                                    show_knowledge_detail(item)
                            
                            st.divider()
                else:
                    st.info("該分類下暫無項目")
        else:
            st.info("暫無分類數據，請先掃描知識庫")
        
    except Exception as e:
        logger.error(f"顯示分類導航失敗: {e}")
        st.error("❌ 分類導航載入失敗")


def show_learning_paths(knowledge_manager):
    """顯示學習路徑"""
    try:
        st.subheader("🎯 個性化學習路徑")
        
        # 學習目標選擇
        learning_goals = {
            "量化交易入門": "適合初學者的基礎學習路徑",
            "策略開發進階": "深入學習策略開發和優化",
            "風險管理專精": "專注於風險控制和管理",
            "技術分析精通": "掌握各種技術分析方法",
            "機器學習應用": "將AI技術應用於量化交易"
        }
        
        selected_goal = st.selectbox(
            "選擇您的學習目標",
            options=list(learning_goals.keys()),
            format_func=lambda x: f"{x} - {learning_goals[x]}"
        )
        
        if selected_goal:
            # 生成學習路徑
            learning_path = generate_learning_path(knowledge_manager, selected_goal)
            
            if learning_path:
                st.success(f"✅ 為您生成了 **{selected_goal}** 的學習路徑")
                
                # 顯示學習路徑
                for i, step in enumerate(learning_path, 1):
                    with st.expander(f"第{i}步: {step['title']}", expanded=(i == 1)):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**學習目標**: {step['objective']}")
                            st.write(f"**預計時間**: {step['estimated_time']}分鐘")
                            st.write(f"**難度等級**: {'⭐' * step['difficulty']}")
                            
                            if step.get('resources'):
                                st.write("**推薦資源**:")
                                for resource in step['resources']:
                                    st.write(f"• {resource}")
                        
                        with col2:
                            progress = st.session_state.get(f"progress_{i}", 0)
                            st.progress(progress / 100)
                            st.caption(f"完成度: {progress}%")
                            
                            if st.button(f"開始學習", key=f"start_{i}"):
                                st.info("跳轉到相關學習內容...")
            else:
                st.warning("暫無相關學習路徑，請選擇其他目標")
        
        # 學習進度追蹤
        st.subheader("📈 學習進度追蹤")
        
        # 模擬學習進度
        progress_data = {
            "已完成模組": 3,
            "進行中模組": 2,
            "計劃中模組": 5,
            "總學習時間": "8.5小時"
        }
        
        cols = st.columns(len(progress_data))
        for i, (metric, value) in enumerate(progress_data.items()):
            with cols[i]:
                st.metric(metric, value)
        
    except Exception as e:
        logger.error(f"顯示學習路徑失敗: {e}")
        st.error("❌ 學習路徑載入失敗")


def show_detailed_statistics(knowledge_manager):
    """顯示詳細統計"""
    try:
        st.subheader("📊 詳細統計分析")
        
        # 獲取統計數據
        stats = knowledge_manager.get_statistics()
        
        # 難度分佈圖表
        st.subheader("📈 難度分佈")
        difficulty_dist = stats.get('difficulty_distribution', {})
        
        if difficulty_dist:
            import plotly.express as px
            
            df_difficulty = pd.DataFrame([
                {'難度等級': f"{level}星", '項目數量': count}
                for level, count in difficulty_dist.items()
            ])
            
            fig = px.bar(df_difficulty, x='難度等級', y='項目數量', 
                        title="知識項目難度分佈")
            st.plotly_chart(fig, use_container_width=True)
        
        # 分類分佈圖表
        st.subheader("📂 分類分佈")
        category_dist = stats.get('category_distribution', {})
        
        if category_dist:
            df_category = pd.DataFrame([
                {'分類': category, '項目數量': count}
                for category, count in category_dist.items()
            ])
            
            fig = px.pie(df_category, values='項目數量', names='分類',
                        title="知識項目分類分佈")
            st.plotly_chart(fig, use_container_width=True)
        
        # 文件類型分佈
        st.subheader("📄 文件類型分佈")
        file_type_dist = stats.get('file_type_distribution', {})
        
        if file_type_dist:
            df_filetype = pd.DataFrame([
                {'文件類型': file_type, '數量': count}
                for file_type, count in file_type_dist.items()
            ])
            
            st.dataframe(df_filetype, use_container_width=True)
        
    except Exception as e:
        logger.error(f"顯示詳細統計失敗: {e}")
        st.error("❌ 詳細統計載入失敗")


def show_knowledge_detail(item):
    """顯示知識項目詳情"""
    try:
        st.subheader(f"📄 {item.title}")
        
        # 基本信息
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**分類**: {item.category} > {item.subcategory}")
            st.write(f"**標籤**: {', '.join(item.tags)}")
            st.write(f"**難度等級**: {'⭐' * item.difficulty_level}")
        
        with col2:
            st.write(f"**預計閱讀時間**: {item.estimated_reading_time}分鐘")
            st.write(f"**創建時間**: {item.created_time.strftime('%Y-%m-%d')}")
            st.write(f"**來源**: {item.metadata.get('source', 'unknown')}")
        
        # 內容顯示
        st.subheader("📖 內容")
        
        # 根據文件類型顯示內容
        if item.file_type == 'markdown':
            st.markdown(item.content)
        else:
            st.text(item.content)
        
        # 相關項目推薦
        if item.related_items:
            st.subheader("🔗 相關項目")
            st.info("相關項目推薦功能開發中...")
        
    except Exception as e:
        logger.error(f"顯示知識詳情失敗: {e}")
        st.error("❌ 知識詳情載入失敗")


def generate_learning_path(knowledge_manager, goal):
    """生成學習路徑"""
    try:
        # 根據學習目標生成路徑
        if goal == "量化交易入門":
            return [
                {
                    "title": "量化交易基礎概念",
                    "objective": "理解量化交易的基本原理和概念",
                    "estimated_time": 60,
                    "difficulty": 1,
                    "resources": ["量化交易概述", "基礎術語解釋"]
                },
                {
                    "title": "Python編程基礎",
                    "objective": "掌握Python在量化交易中的應用",
                    "estimated_time": 120,
                    "difficulty": 2,
                    "resources": ["Python入門", "數據處理基礎"]
                },
                {
                    "title": "技術指標學習",
                    "objective": "學習常用的技術分析指標",
                    "estimated_time": 90,
                    "difficulty": 2,
                    "resources": ["移動平均線", "RSI指標", "MACD指標"]
                }
            ]
        elif goal == "策略開發進階":
            return [
                {
                    "title": "策略框架設計",
                    "objective": "學習如何設計可擴展的策略框架",
                    "estimated_time": 90,
                    "difficulty": 3,
                    "resources": ["策略模式", "框架設計原則"]
                },
                {
                    "title": "回測系統構建",
                    "objective": "構建完整的策略回測系統",
                    "estimated_time": 120,
                    "difficulty": 4,
                    "resources": ["回測框架", "性能評估"]
                }
            ]
        else:
            return []
    
    except Exception as e:
        logger.error(f"生成學習路徑失敗: {e}")
        return []


def show_statistics_report(knowledge_manager):
    """顯示統計報告"""
    try:
        st.subheader("📊 知識庫統計報告")
        
        stats = knowledge_manager.get_statistics()
        
        report_data = {
            "統計項目": [
                "總知識項目數",
                "知識分類數",
                "標籤總數",
                "平均難度等級",
                "平均閱讀時間"
            ],
            "數值": [
                stats.get('total_items', 0),
                stats.get('total_categories', 0),
                stats.get('total_tags', 0),
                "2.5星",
                "15分鐘"
            ]
        }
        
        df_report = pd.DataFrame(report_data)
        st.dataframe(df_report, use_container_width=True)
        
        # 下載報告
        if st.button("📥 下載報告"):
            st.info("報告下載功能開發中...")
    
    except Exception as e:
        logger.error(f"顯示統計報告失敗: {e}")
        st.error("❌ 統計報告生成失敗")


# 主函數
def show() -> None:
    """顯示知識庫頁面 (Web UI 入口點).

    Returns:
        None
    """
    show_knowledge_base()


def main():
    """知識庫主函數"""
    show_knowledge_base()


if __name__ == "__main__":
    main()
