"""
增強下載頁面
集成實時進度條、可配置跳過選項和下載統計報告
"""

import streamlit as st
import pandas as pd
import time
import json
from datetime import date, datetime
from pathlib import Path
import sys

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.data_sources.real_data_crawler import RealDataCrawler

class DownloadProgressManager:
    """下載進度管理器"""
    
    def __init__(self):
        self.history_file = "data/download_history.json"
        self.config_file = "data/download_config.json"
        self._init_session_state()
    
    def _init_session_state(self):
        """初始化會話狀態"""
        if 'download_config' not in st.session_state:
            st.session_state.download_config = {
                'enable_smart_skip': True,
                'enable_known_problematic': True,
                'custom_skip_list': [],
                'show_progress_details': True,
                'auto_save_results': True
            }
        
        if 'download_stats' not in st.session_state:
            st.session_state.download_stats = {
                'current_progress': 0,
                'total_stocks': 0,
                'processed_stocks': 0,
                'current_stock': "",
                'status': "就緒",
                'start_time': None,
                'results': []
            }
    
    def show_configuration_panel(self):
        """顯示配置面板"""
        st.subheader("⚙️ 下載配置")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**跳過選項**")
            st.session_state.download_config['enable_known_problematic'] = st.checkbox(
                "跳過已知問題股票",
                value=st.session_state.download_config['enable_known_problematic'],
                help="跳過13檔已知問題股票，節省約3分鐘"
            )
            
            st.session_state.download_config['enable_smart_skip'] = st.checkbox(
                "啟用智能檢測跳過",
                value=st.session_state.download_config['enable_smart_skip'],
                help="自動檢測並跳過可能有問題的股票"
            )
        
        with col2:
            st.write("**界面選項**")
            st.session_state.download_config['show_progress_details'] = st.checkbox(
                "顯示詳細進度",
                value=st.session_state.download_config['show_progress_details'],
                help="顯示每檔股票的處理詳情"
            )
            
            st.session_state.download_config['auto_save_results'] = st.checkbox(
                "自動保存結果",
                value=st.session_state.download_config['auto_save_results'],
                help="自動保存下載歷史和統計"
            )
        
        # 自定義跳過列表
        with st.expander("🎯 自定義跳過股票"):
            custom_skip_text = st.text_area(
                "輸入要跳過的股票代碼 (每行一個)",
                value='\n'.join(st.session_state.download_config['custom_skip_list']),
                height=80,
                help="例如: 1234.TW 或 5678.TWO"
            )
            
            if custom_skip_text:
                custom_list = [line.strip() for line in custom_skip_text.split('\n') if line.strip()]
                st.session_state.download_config['custom_skip_list'] = custom_list
            else:
                st.session_state.download_config['custom_skip_list'] = []
            
            if st.session_state.download_config['custom_skip_list']:
                st.info(f"自定義跳過: {len(st.session_state.download_config['custom_skip_list'])} 檔股票")
    
    def show_real_time_progress(self):
        """顯示實時進度"""
        stats = st.session_state.download_stats
        
        if stats['total_stocks'] > 0:
            progress = stats['processed_stocks'] / stats['total_stocks']
            
            # 主進度條
            st.progress(progress, text=f"整體進度: {stats['processed_stocks']}/{stats['total_stocks']} ({progress*100:.1f}%)")
            
            # 詳細指標
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("當前股票", stats['current_stock'])
            
            with col2:
                st.metric("狀態", stats['status'])
            
            with col3:
                if stats['start_time']:
                    elapsed = time.time() - stats['start_time']
                    st.metric("已用時間", f"{elapsed:.1f}秒")
                else:
                    st.metric("已用時間", "0秒")
            
            with col4:
                if stats['processed_stocks'] > 0 and stats['start_time']:
                    elapsed = time.time() - stats['start_time']
                    avg_time = elapsed / stats['processed_stocks']
                    remaining = (stats['total_stocks'] - stats['processed_stocks']) * avg_time
                    st.metric("預估剩餘", f"{remaining:.1f}秒")
                else:
                    st.metric("預估剩餘", "計算中...")
    
    def download_with_enhanced_progress(self, symbols, start_date, end_date):
        """增強進度顯示的下載功能"""
        # 初始化爬蟲
        crawler = RealDataCrawler(db_path='sqlite:///data/enhanced_stock_database.db')
        
        # 應用配置
        config = st.session_state.download_config
        
        # 處理跳過配置
        original_problematic = crawler.KNOWN_PROBLEMATIC_STOCKS.copy()
        if not config['enable_known_problematic']:
            crawler.KNOWN_PROBLEMATIC_STOCKS = []
        
        # 添加自定義跳過
        if config['custom_skip_list']:
            crawler.KNOWN_PROBLEMATIC_STOCKS.extend(config['custom_skip_list'])
        
        # 初始化統計
        stats = st.session_state.download_stats
        stats['total_stocks'] = len(symbols)
        stats['processed_stocks'] = 0
        stats['start_time'] = time.time()
        stats['results'] = []
        
        # 創建容器
        progress_container = st.container()
        details_container = st.container() if config['show_progress_details'] else None
        
        # 統計變量
        successful = 0
        failed = 0
        skipped = 0
        
        # 處理每檔股票
        for i, symbol in enumerate(symbols):
            # 更新狀態
            stats['current_stock'] = symbol
            stats['processed_stocks'] = i + 1
            stats['status'] = f"處理中 ({i+1}/{len(symbols)})"
            
            # 更新進度顯示
            with progress_container:
                self.show_real_time_progress()
            
            try:
                # 記錄開始時間
                stock_start_time = time.time()
                
                # 下載數據
                data = crawler.crawl_date_range(symbol, start_date, end_date)
                
                # 計算耗時
                duration = time.time() - stock_start_time
                
                # 處理結果
                if not data.empty:
                    successful += 1
                    result = {
                        'symbol': symbol,
                        'status': 'success',
                        'records': len(data),
                        'duration': duration,
                        'message': f"成功下載 {len(data)} 筆記錄"
                    }
                    
                    if details_container:
                        with details_container:
                            st.success(f"✅ {symbol}: {result['message']} ({duration:.1f}s)")
                
                else:
                    # 判斷是跳過還是失敗
                    if (symbol in crawler.KNOWN_PROBLEMATIC_STOCKS or 
                        (config['enable_smart_skip'] and crawler.is_likely_problematic(symbol))):
                        skipped += 1
                        result = {
                            'symbol': symbol,
                            'status': 'skipped',
                            'records': 0,
                            'duration': duration,
                            'message': "智能跳過"
                        }
                        
                        if details_container:
                            with details_container:
                                st.info(f"⏭️ {symbol}: {result['message']} ({duration:.3f}s)")
                    else:
                        failed += 1
                        result = {
                            'symbol': symbol,
                            'status': 'failed',
                            'records': 0,
                            'duration': duration,
                            'message': "下載失敗"
                        }
                        
                        if details_container:
                            with details_container:
                                st.error(f"❌ {symbol}: {result['message']} ({duration:.1f}s)")
                
                stats['results'].append(result)
                
            except Exception as e:
                failed += 1
                duration = time.time() - stock_start_time
                result = {
                    'symbol': symbol,
                    'status': 'error',
                    'records': 0,
                    'duration': duration,
                    'message': f"錯誤: {str(e)[:50]}..."
                }
                stats['results'].append(result)
                
                if details_container:
                    with details_container:
                        st.error(f"❌ {symbol}: {result['message']} ({duration:.1f}s)")
            
            # 小延遲避免界面卡頓
            time.sleep(0.01)
        
        # 完成統計
        total_duration = time.time() - stats['start_time']
        stats['status'] = "完成"
        
        # 最終進度更新
        with progress_container:
            self.show_real_time_progress()
        
        # 返回結果摘要
        return {
            'total': len(symbols),
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'duration': total_duration,
            'success_rate': (successful / len(symbols) * 100) if symbols else 0,
            'details': stats['results']
        }
    
    def save_download_history(self, results):
        """保存下載歷史"""
        if not st.session_state.download_config['auto_save_results']:
            return
        
        try:
            Path(self.history_file).parent.mkdir(exist_ok=True)
            
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'config': st.session_state.download_config.copy(),
                **results
            }
            
            # 讀取現有歷史
            history = []
            if Path(self.history_file).exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # 添加新記錄
            history.append(history_entry)
            
            # 保持最近50條記錄
            if len(history) > 50:
                history = history[-50:]
            
            # 保存
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            st.success("✅ 下載歷史已保存")
            
        except Exception as e:
            st.error(f"❌ 保存歷史失敗: {e}")

def show_enhanced_download_page():
    """顯示增強下載頁面"""
    st.title("📊 增強股票數據下載")
    st.markdown("---")
    
    # 初始化管理器
    manager = DownloadProgressManager()
    
    # 配置面板
    with st.expander("⚙️ 下載配置", expanded=False):
        manager.show_configuration_panel()
    
    # 下載參數
    st.subheader("📥 下載參數設置")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "開始日期",
            value=date(2024, 7, 1),
            help="選擇數據下載的開始日期"
        )
    
    with col2:
        end_date = st.date_input(
            "結束日期", 
            value=date(2024, 7, 31),
            help="選擇數據下載的結束日期"
        )
    
    # 股票選擇
    st.subheader("🎯 股票選擇")
    
    # 預設選項
    preset_col1, preset_col2, preset_col3 = st.columns(3)
    
    with preset_col1:
        if st.button("📈 熱門股票", help="台積電、鴻海、聯發科等"):
            st.session_state.stock_input = "2330.TW\n2317.TW\n2454.TW\n2382.TW\n2308.TW"
    
    with preset_col2:
        if st.button("💰 ETF組合", help="台灣50、高股息等ETF"):
            st.session_state.stock_input = "0050.TW\n0056.TW\n006208.TW\n00878.TW\n00692.TW"
    
    with preset_col3:
        if st.button("🔬 測試組合", help="包含正常和問題股票的測試組合"):
            st.session_state.stock_input = "2330.TW\n0050.TW\n3443.TWO\n6424.TWO\n3227.TWO"
    
    # 股票代碼輸入
    stock_input = st.text_area(
        "股票代碼 (每行一個)",
        value=st.session_state.get('stock_input', "2330.TW\n0050.TW\n3443.TWO"),
        height=120,
        help="輸入股票代碼，每行一個。支持.TW (上市) 和.TWO (上櫃) 格式"
    )
    
    # 開始下載
    if st.button("🚀 開始增強下載", type="primary", use_container_width=True):
        symbols = [line.strip() for line in stock_input.split('\n') if line.strip()]
        
        if not symbols:
            st.error("❌ 請輸入至少一個股票代碼")
            return
        
        if start_date >= end_date:
            st.error("❌ 開始日期必須早於結束日期")
            return
        
        # 顯示下載信息
        st.info(f"📊 準備下載 {len(symbols)} 檔股票，日期範圍: {start_date} 至 {end_date}")
        
        # 執行下載
        with st.spinner("正在執行增強下載..."):
            results = manager.download_with_enhanced_progress(symbols, start_date, end_date)
        
        # 顯示結果摘要
        st.markdown("---")
        st.subheader("📊 下載結果摘要")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("總股票數", results['total'])
        with col2:
            st.metric("成功下載", results['successful'], delta=f"{results['success_rate']:.1f}%")
        with col3:
            st.metric("智能跳過", results['skipped'])
        with col4:
            st.metric("下載失敗", results['failed'])
        with col5:
            st.metric("總耗時", f"{results['duration']:.1f}秒")
        
        # 保存歷史
        manager.save_download_history(results)
        
        # 顯示詳細結果
        if results['details']:
            with st.expander("📋 詳細結果", expanded=False):
                df_results = pd.DataFrame(results['details'])
                st.dataframe(df_results, use_container_width=True)

if __name__ == "__main__":
    show_enhanced_download_page()
