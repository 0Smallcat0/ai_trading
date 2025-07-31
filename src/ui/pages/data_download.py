#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據下載頁面
===========

提供股票數據下載功能，支援日期範圍選擇、測試模式和進度顯示。
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import logging
import asyncio
import threading
from typing import List, Optional
import time
import signal

# 設定日誌
logger = logging.getLogger(__name__)

# 全局停止標誌
_download_stop_flag = threading.Event()
_download_thread = None


def _format_duration(duration):
    """格式化時間間隔顯示"""
    if isinstance(duration, timedelta):
        total_seconds = int(duration.total_seconds())
    else:
        total_seconds = int(duration)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}小時{minutes}分{seconds}秒"
    elif minutes > 0:
        return f"{minutes}分{seconds}秒"
    else:
        return f"{seconds}秒"


def show_data_download_page():
    """顯示數據下載頁面"""
    st.title("📥 股票數據下載")
    
    # 創建兩欄布局
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📅 下載設定")
        
        # 日期範圍選擇器
        start_date = st.date_input(
            "開始日期",
            value=date(2021, 1, 1),
            min_value=date(2020, 1, 1),
            max_value=date.today(),
            help="選擇數據下載的開始日期"
        )
        
        end_date = st.date_input(
            "結束日期", 
            value=date.today(),
            min_value=start_date,
            max_value=date.today(),
            help="選擇數據下載的結束日期"
        )
        
        # 測試模式選項
        test_mode = st.checkbox(
            "🧪 測試模式",
            value=False,
            help="啟用測試模式將僅下載前10檔股票，用於快速測試"
        )
        
        # 數據源選擇
        data_source = st.selectbox(
            "數據源",
            options=["AUTO", "TWSE", "TPEX", "YAHOO"],
            index=0,
            help="選擇數據來源，AUTO 會自動選擇最佳來源"
        )
        
    with col2:
        # 空白區域
        st.empty()
    
    st.markdown("---")
    
    # 下載控制區域
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("🚀 開始下載", type="primary", use_container_width=True):
            if start_date >= end_date:
                st.error("❌ 開始日期必須早於結束日期")
            else:
                start_download_async(start_date, end_date, test_mode, data_source)

    with col2:
        if st.button("⏹️ 停止下載", use_container_width=True):
            stop_download()


def start_download_async(start_date: date, end_date: date, test_mode: bool, data_source: str):
    """異步開始數據下載"""
    global _download_thread, _download_stop_flag

    # 檢查是否已有下載在進行
    if _download_thread and _download_thread.is_alive():
        st.warning("⚠️ 已有下載任務在進行中，請先停止當前任務")
        return

    # 重置停止標誌
    _download_stop_flag.clear()

    # 在新線程中啟動下載
    _download_thread = threading.Thread(
        target=start_download,
        args=(start_date, end_date, test_mode, data_source),
        daemon=True
    )
    _download_thread.start()
    st.success("🚀 下載任務已啟動")


def start_download(start_date: date, end_date: date, test_mode: bool, data_source: str):
    """開始數據下載"""
    try:
        # 導入必要的模組
        from src.data_sources.enhanced_real_data_crawler import EnhancedRealDataCrawler
        from src.core.real_data_integration import RealDataIntegrationService

        # 初始化下載器
        from src.data_sources.real_data_crawler import RealDataCrawler
        crawler = RealDataCrawler(db_path='sqlite:///data/enhanced_stock_database.db')
        integration_service = RealDataIntegrationService(db_path='sqlite:///data/enhanced_stock_database.db')

        # 獲取完整股票列表
        st.info("🔍 正在獲取股票列表...")

        # 嘗試從台股清單管理器獲取完整列表
        try:
            from src.data_sources.taiwan_stock_list_manager import TaiwanStockListManager
            stock_manager = TaiwanStockListManager()

            # 先檢查資料庫中是否有股票清單
            all_stocks = stock_manager.get_all_stocks()

            if not all_stocks:
                # 如果資料庫為空，嘗試更新股票清單
                st.info("🔄 首次使用，正在獲取完整股票清單...")
                with st.spinner("正在從證交所獲取股票清單，請稍候..."):
                    try:
                        update_result = stock_manager.update_stock_list(force_update=True)
                        if update_result and update_result.get('total_stocks', 0) > 0:
                            all_stocks = stock_manager.get_all_stocks()
                            st.success(f"✅ 成功更新股票清單：{update_result['total_stocks']} 檔股票")
                        else:
                            st.warning("⚠️ 股票清單更新失敗，將使用預設清單")
                    except Exception as update_e:
                        st.warning(f"⚠️ 股票清單更新失敗：{update_e}")
                        logger.warning(f"股票清單更新失敗: {update_e}")

            if all_stocks:
                full_stock_list = [stock.symbol for stock in all_stocks]
                st.success(f"✅ 成功獲取 {len(full_stock_list)} 檔股票清單")

                # 顯示股票分布統計
                twse_count = len([s for s in all_stocks if s.market == '上市'])
                tpex_count = len([s for s in all_stocks if s.market == '上櫃'])

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("總股票數", len(full_stock_list))
                with col_b:
                    st.metric("上市股票", twse_count)
                with col_c:
                    st.metric("上櫃股票", tpex_count)
            else:
                # 回退到整合服務的股票列表
                full_stock_list = integration_service.stock_universe
                st.warning(f"⚠️ 無法獲取完整股票清單，使用預設列表：{len(full_stock_list)} 檔股票")

        except Exception as e:
            # 回退到整合服務的股票列表
            full_stock_list = integration_service.stock_universe
            st.warning(f"⚠️ 無法獲取完整股票列表，使用預設列表：{len(full_stock_list)} 檔股票")
            logger.warning(f"股票列表獲取失敗: {e}")

        # 根據模式選擇股票
        if test_mode:
            # 測試模式：僅下載前10檔股票
            stock_list = full_stock_list[:10]
            st.info(f"🧪 測試模式：將下載 {len(stock_list)} 檔股票")
        else:
            # 完整模式：下載所有股票
            stock_list = full_stock_list
            st.info(f"📈 完整模式：將下載 {len(stock_list)} 檔股票")

        # 初始化下載進度追蹤
        total_symbols = len(stock_list)
        completed_symbols = 0
        failed_symbols = 0
        total_records = 0
        start_time = datetime.now()

        # 創建進度容器
        progress_container = st.container()

        with progress_container:
            st.subheader("📊 下載進度")

            # 創建進度顯示元件
            progress_bar = st.progress(0)
            progress_text = st.empty()
            status_text = st.empty()
            time_info = st.empty()

            # 智能掃描階段
            st.markdown("### 🔍 數據庫掃描階段")
            scan_status = st.empty()
            scan_status.text("正在掃描數據庫中的現有數據...")

            # 執行智能掃描
            scan_result = crawler.scan_existing_data(stock_list, start_date, end_date)

            # 顯示掃描結果
            scan_status.success("✅ 數據庫掃描完成")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("完整數據", len(scan_result['complete_symbols']), "可跳過")
            with col2:
                st.metric("部分數據", len(scan_result['partial_symbols']), "需補充")
            with col3:
                st.metric("缺失數據", len(scan_result['missing_symbols']), "需爬取")
            with col4:
                st.metric("預計跳過記錄", scan_result['total_existing_records'], "已存在")

            # 確定需要爬取的股票
            symbols_to_crawl = scan_result['missing_symbols'] + scan_result['partial_symbols']

            if not symbols_to_crawl:
                st.success("🎉 所有股票數據已存在，無需下載！")
                return

            st.info(f"📋 發現 {len(scan_result['complete_symbols'])} 檔股票已有數據，將爬取 {len(symbols_to_crawl)} 檔新股票")

            # 更新總數為實際需要爬取的數量
            total_symbols = len(symbols_to_crawl)
            stock_list = symbols_to_crawl

            # 開始下載
            for i, symbol in enumerate(symbols_to_crawl):
                # 檢查停止標誌
                if _download_stop_flag.is_set():
                    st.warning("⏹️ 下載已被用戶停止")
                    break

                try:
                    current_progress = (i + 1) / total_symbols
                    progress_percentage = current_progress * 100

                    # 更新進度條
                    progress_bar.progress(current_progress)

                    # 更新詳細進度信息
                    progress_text.markdown(f"""
                    **下載進度**: {i + 1}/{total_symbols} 檔股票 ({progress_percentage:.1f}%)

                    📊 **統計資訊**:
                    - 已完成: {completed_symbols} 檔
                    - 失敗: {failed_symbols} 檔
                    - 總記錄數: {total_records:,} 筆
                    """)

                    status_text.text(f"🔄 正在下載 {symbol}...")

                    # 計算預估剩餘時間和完成時間
                    if i > 0:
                        elapsed_time = datetime.now() - start_time
                        avg_time_per_stock = elapsed_time.total_seconds() / i
                        remaining_stocks = total_symbols - i
                        estimated_remaining_seconds = avg_time_per_stock * remaining_stocks
                        estimated_remaining = timedelta(seconds=estimated_remaining_seconds)
                        estimated_completion = datetime.now() + estimated_remaining

                        time_info.markdown(f"""
                        ⏱️ **時間資訊**:
                        - 已用時: {_format_duration(elapsed_time)}
                        - 預估剩餘: {_format_duration(estimated_remaining)}
                        - 預估完成: {estimated_completion.strftime('%H:%M:%S')}
                        - 平均速度: {avg_time_per_stock:.1f}秒/檔
                        """)

                    # 執行下載
                    download_start = datetime.now()
                    result = crawler.crawl_stock_data_range(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date
                    )
                    download_duration = datetime.now() - download_start

                    if result is not None and not result.empty:
                        # 保存到資料庫
                        crawler.save_to_database(result)
                        completed_symbols += 1
                        total_records += len(result)

                        # 顯示成功信息（限制顯示數量避免界面過長）
                        if i < 5 or i % 10 == 0:  # 只顯示前5個和每10個
                            st.success(f"✅ {symbol}: 下載 {len(result)} 筆記錄 "
                                     f"(耗時: {download_duration.total_seconds():.1f}秒)")
                    else:
                        failed_symbols += 1
                        if i < 5 or i % 10 == 0:  # 只顯示前5個和每10個
                            st.warning(f"⚠️ {symbol}: 無數據或下載失敗")

                    # 更新進度條
                    progress_bar.progress(current_progress)

                    # 統計信息已移除，保持簡潔的進度顯示

                    # 短暫延遲避免過於頻繁的請求
                    time.sleep(0.5)

                except Exception as e:
                    failed_symbols += 1
                    if i < 5 or i % 10 == 0:  # 只顯示前5個和每10個
                        st.error(f"❌ {symbol}: 下載失敗 - {str(e)}")
                    logger.error(f"下載 {symbol} 失敗: {e}")

            # 完成下載
            total_duration = datetime.now() - start_time
            final_progress = 100.0

            # 更新最終進度
            progress_bar.progress(1.0)
            progress_text.markdown(f"""
            **✅ 下載完成！**

            📊 **最終統計**:
            - 處理股票: {total_symbols} 檔 (100%)
            - 成功下載: {completed_symbols} 檔
            - 失敗數量: {failed_symbols} 檔
            - 總記錄數: {total_records:,} 筆
            """)

            status_text.text("🎉 所有下載任務已完成")

            time_info.markdown(f"""
            ⏱️ **完成時間資訊**:
            - 總耗時: {_format_duration(total_duration)}
            - 平均速度: {total_duration.total_seconds()/total_symbols:.1f}秒/檔
            - 完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """)

            # 最終統計摘要
            success_rate = (completed_symbols / total_symbols * 100) if total_symbols > 0 else 0

            if success_rate >= 90:
                st.success(f"""
                🎉 下載任務圓滿完成！

                📈 **成果摘要**:
                - 總股票數: {total_symbols:,} 檔
                - 成功率: {success_rate:.1f}%
                - 新增記錄: {total_records:,} 筆
                - 總耗時: {_format_duration(total_duration)}
                """)
            elif success_rate >= 70:
                st.warning(f"""
                ⚠️ 下載任務基本完成，但有部分失敗

                📊 **成果摘要**:
                - 總股票數: {total_symbols:,} 檔
                - 成功率: {success_rate:.1f}%
                - 失敗數量: {failed_symbols} 檔
                - 新增記錄: {total_records:,} 筆
                - 總耗時: {_format_duration(total_duration)}

                建議檢查失敗的股票並重新下載。
                """)
            else:
                st.error(f"""
                ❌ 下載任務完成，但成功率較低

                📊 **成果摘要**:
                - 總股票數: {total_symbols:,} 檔
                - 成功率: {success_rate:.1f}%
                - 失敗數量: {failed_symbols} 檔
                - 新增記錄: {total_records:,} 筆
                - 總耗時: {_format_duration(total_duration)}

                請檢查網路連接狀態。
                """)
            
    except ImportError as e:
        st.error(f"❌ 模組導入失敗: {e}")
        st.info("請確保相關的數據下載模組已正確安裝")
    except Exception as e:
        st.error(f"❌ 下載過程發生錯誤: {e}")
        logger.error(f"數據下載失敗: {e}")


def stop_download():
    """停止數據下載"""
    global _download_stop_flag, _download_thread

    if _download_thread and _download_thread.is_alive():
        # 設置停止標誌
        _download_stop_flag.set()
        st.warning("⏹️ 正在停止下載，請稍候...")

        # 等待線程結束（最多等待5秒）
        _download_thread.join(timeout=5)

        if _download_thread.is_alive():
            st.error("❌ 無法正常停止下載線程，可能需要重啟應用")
        else:
            st.success("✅ 下載已成功停止")
            _download_thread = None
    else:
        st.info("ℹ️ 當前沒有正在進行的下載任務")





if __name__ == "__main__":
    show_data_download_page()
