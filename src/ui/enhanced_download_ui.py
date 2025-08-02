"""
增強的下載界面
包含實時進度條、可配置跳過選項和下載統計報告
"""

import streamlit as st
import pandas as pd
import time
from datetime import date, datetime
import json
from pathlib import Path
import sys

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.data_sources.real_data_crawler import RealDataCrawler

class EnhancedDownloadUI:
    """增強的下載界面類"""
    
    def __init__(self):
        self.crawler = None
        self.download_history_file = "data/download_history.json"
        self.config_file = "data/download_config.json"
        self._init_session_state()
        self._load_config()
    
    def _init_session_state(self):
        """初始化會話狀態"""
        if 'download_progress' not in st.session_state:
            st.session_state.download_progress = 0
        if 'download_status' not in st.session_state:
            st.session_state.download_status = "就緒"
        if 'download_results' not in st.session_state:
            st.session_state.download_results = []
        if 'current_stock' not in st.session_state:
            st.session_state.current_stock = ""
        if 'total_stocks' not in st.session_state:
            st.session_state.total_stocks = 0
        if 'processed_stocks' not in st.session_state:
            st.session_state.processed_stocks = 0
    
    def _load_config(self):
        """載入配置"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    st.session_state.skip_config = config.get('skip_config', {
                        'enable_smart_skip': True,
                        'enable_known_problematic': True,
                        'custom_skip_list': []
                    })
            else:
                st.session_state.skip_config = {
                    'enable_smart_skip': True,
                    'enable_known_problematic': True,
                    'custom_skip_list': []
                }
        except Exception as e:
            st.error(f"載入配置失敗: {e}")
            st.session_state.skip_config = {
                'enable_smart_skip': True,
                'enable_known_problematic': True,
                'custom_skip_list': []
            }
    
    def _save_config(self):
        """保存配置"""
        try:
            Path(self.config_file).parent.mkdir(exist_ok=True)
            config = {'skip_config': st.session_state.skip_config}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"保存配置失敗: {e}")
    
    def _save_download_history(self, results):
        """保存下載歷史"""
        try:
            Path(self.download_history_file).parent.mkdir(exist_ok=True)
            
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'total_stocks': results.get('total', 0),
                'successful': results.get('successful', 0),
                'failed': results.get('failed', 0),
                'skipped': results.get('skipped', 0),
                'duration': results.get('duration', 0),
                'success_rate': results.get('success_rate', 0),
                'details': results.get('details', [])
            }
            
            # 讀取現有歷史
            history = []
            if Path(self.download_history_file).exists():
                with open(self.download_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # 添加新記錄
            history.append(history_entry)
            
            # 保持最近100條記錄
            if len(history) > 100:
                history = history[-100:]
            
            # 保存歷史
            with open(self.download_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            st.error(f"保存下載歷史失敗: {e}")
    
    def _load_download_history(self):
        """載入下載歷史"""
        try:
            if Path(self.download_history_file).exists():
                with open(self.download_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            st.error(f"載入下載歷史失敗: {e}")
            return []
    
    def show_skip_configuration(self):
        """顯示跳過配置選項"""
        st.subheader("🔧 跳過配置選項")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.skip_config['enable_known_problematic'] = st.checkbox(
                "啟用已知問題股票跳過",
                value=st.session_state.skip_config.get('enable_known_problematic', True),
                help="跳過13檔已知問題股票，節省約3分鐘"
            )
            
            st.session_state.skip_config['enable_smart_skip'] = st.checkbox(
                "啟用智能檢測跳過",
                value=st.session_state.skip_config.get('enable_smart_skip', True),
                help="自動檢測6420-6450和9000+系列問題股票"
            )
        
        with col2:
            # 顯示當前跳過統計
            if hasattr(RealDataCrawler, 'KNOWN_PROBLEMATIC_STOCKS'):
                known_count = len(RealDataCrawler.KNOWN_PROBLEMATIC_STOCKS)
                st.metric("已知問題股票", f"{known_count} 檔")
            
            smart_range = "6420-6450, 9000+"
            st.metric("智能檢測範圍", smart_range)
        
        # 自定義跳過列表
        st.write("**自定義跳過股票**")
        custom_skip_text = st.text_area(
            "輸入要跳過的股票代碼 (每行一個)",
            value='\n'.join(st.session_state.skip_config.get('custom_skip_list', [])),
            height=100,
            help="例如: 1234.TW 或 5678.TWO"
        )
        
        if custom_skip_text:
            custom_list = [line.strip() for line in custom_skip_text.split('\n') if line.strip()]
            st.session_state.skip_config['custom_skip_list'] = custom_list
        else:
            st.session_state.skip_config['custom_skip_list'] = []
        
        # 保存配置按鈕
        if st.button("💾 保存跳過配置"):
            self._save_config()
            st.success("配置已保存！")
    
    def show_download_progress(self):
        """顯示實時進度條"""
        if st.session_state.processed_stocks > 0:
            progress = st.session_state.processed_stocks / st.session_state.total_stocks
            st.progress(progress)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("進度", f"{st.session_state.processed_stocks}/{st.session_state.total_stocks}")
            with col2:
                st.metric("完成率", f"{progress*100:.1f}%")
            with col3:
                st.metric("當前股票", st.session_state.current_stock)
            with col4:
                st.metric("狀態", st.session_state.download_status)
    
    def download_with_progress(self, symbols, start_date, end_date):
        """帶進度顯示的下載功能"""
        if not self.crawler:
            self.crawler = RealDataCrawler(db_path='sqlite:///data/enhanced_stock_database.db')
        
        # 應用跳過配置
        if not st.session_state.skip_config.get('enable_known_problematic', True):
            # 如果禁用已知問題股票跳過，清空列表
            original_problematic = self.crawler.KNOWN_PROBLEMATIC_STOCKS.copy()
            self.crawler.KNOWN_PROBLEMATIC_STOCKS = []
        
        # 添加自定義跳過列表
        custom_skip = st.session_state.skip_config.get('custom_skip_list', [])
        if custom_skip:
            self.crawler.KNOWN_PROBLEMATIC_STOCKS.extend(custom_skip)
        
        # 初始化進度
        st.session_state.total_stocks = len(symbols)
        st.session_state.processed_stocks = 0
        st.session_state.download_results = []
        
        # 創建進度顯示區域
        progress_container = st.container()
        results_container = st.container()
        
        start_time = time.time()
        successful = 0
        failed = 0
        skipped = 0
        
        for i, symbol in enumerate(symbols):
            # 更新進度狀態
            st.session_state.current_stock = symbol
            st.session_state.processed_stocks = i + 1
            st.session_state.download_status = f"處理中... ({i+1}/{len(symbols)})"
            
            # 更新進度顯示
            with progress_container:
                self.show_download_progress()
            
            try:
                # 下載數據
                data = self.crawler.crawl_date_range(symbol, start_date, end_date)
                
                if not data.empty:
                    successful += 1
                    result = {
                        'symbol': symbol,
                        'status': 'success',
                        'records': len(data),
                        'message': f"成功下載 {len(data)} 筆記錄"
                    }
                else:
                    # 檢查是否被跳過
                    if (symbol in self.crawler.KNOWN_PROBLEMATIC_STOCKS or 
                        (st.session_state.skip_config.get('enable_smart_skip', True) and 
                         self.crawler.is_likely_problematic(symbol))):
                        skipped += 1
                        result = {
                            'symbol': symbol,
                            'status': 'skipped',
                            'records': 0,
                            'message': "智能跳過"
                        }
                    else:
                        failed += 1
                        result = {
                            'symbol': symbol,
                            'status': 'failed',
                            'records': 0,
                            'message': "下載失敗"
                        }
                
                st.session_state.download_results.append(result)
                
                # 實時顯示結果
                with results_container:
                    if result['status'] == 'success':
                        st.success(f"✅ {symbol}: {result['message']}")
                    elif result['status'] == 'skipped':
                        st.info(f"⏭️ {symbol}: {result['message']}")
                    else:
                        st.error(f"❌ {symbol}: {result['message']}")
                
            except Exception as e:
                failed += 1
                result = {
                    'symbol': symbol,
                    'status': 'error',
                    'records': 0,
                    'message': f"錯誤: {str(e)}"
                }
                st.session_state.download_results.append(result)
                
                with results_container:
                    st.error(f"❌ {symbol}: {result['message']}")
        
        # 完成下載
        duration = time.time() - start_time
        total = len(symbols)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        st.session_state.download_status = "完成"
        
        # 保存下載歷史
        results_summary = {
            'total': total,
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'duration': duration,
            'success_rate': success_rate,
            'details': st.session_state.download_results
        }
        
        self._save_download_history(results_summary)
        
        return results_summary
    
    def show_download_statistics(self):
        """顯示下載統計報告"""
        st.subheader("📊 下載統計報告")
        
        history = self._load_download_history()
        
        if not history:
            st.info("暫無下載歷史記錄")
            return
        
        # 最近下載統計
        latest = history[-1]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("最近成功率", f"{latest['success_rate']:.1f}%")
        with col2:
            st.metric("成功下載", f"{latest['successful']} 檔")
        with col3:
            st.metric("智能跳過", f"{latest['skipped']} 檔")
        with col4:
            st.metric("下載時間", f"{latest['duration']:.1f} 秒")
        
        # 歷史趨勢圖
        if len(history) > 1:
            df_history = pd.DataFrame(history)
            df_history['timestamp'] = pd.to_datetime(df_history['timestamp'])
            
            st.subheader("📈 成功率趨勢")
            st.line_chart(df_history.set_index('timestamp')['success_rate'])
            
            st.subheader("⏱️ 下載時間趨勢")
            st.line_chart(df_history.set_index('timestamp')['duration'])
        
        # 詳細歷史表格
        st.subheader("📋 下載歷史")
        
        history_df = pd.DataFrame([
            {
                '時間': datetime.fromisoformat(h['timestamp']).strftime('%Y-%m-%d %H:%M'),
                '總數': h['total'],
                '成功': h['successful'],
                '失敗': h['failed'],
                '跳過': h['skipped'],
                '成功率': f"{h['success_rate']:.1f}%",
                '耗時': f"{h['duration']:.1f}s"
            }
            for h in history[-10:]  # 顯示最近10次
        ])
        
        st.dataframe(history_df, use_container_width=True)

def main():
    """主函數"""
    st.set_page_config(
        page_title="增強下載界面",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 增強的股票數據下載界面")
    
    ui = EnhancedDownloadUI()
    
    # 側邊欄配置
    with st.sidebar:
        st.header("⚙️ 配置選項")
        ui.show_skip_configuration()
    
    # 主界面
    tab1, tab2, tab3 = st.tabs(["📥 數據下載", "📊 統計報告", "ℹ️ 系統信息"])
    
    with tab1:
        st.header("📥 股票數據下載")
        
        # 下載參數
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("開始日期", value=date(2024, 7, 1))
        with col2:
            end_date = st.date_input("結束日期", value=date(2024, 7, 31))
        
        # 股票選擇
        stock_input = st.text_area(
            "股票代碼 (每行一個)",
            value="2330.TW\n0050.TW\n3443.TWO",
            height=100
        )
        
        if st.button("🚀 開始下載", type="primary"):
            symbols = [line.strip() for line in stock_input.split('\n') if line.strip()]
            
            if symbols:
                with st.spinner("正在下載..."):
                    results = ui.download_with_progress(symbols, start_date, end_date)
                
                st.success(f"下載完成！成功: {results['successful']}, 跳過: {results['skipped']}, 失敗: {results['failed']}")
            else:
                st.error("請輸入股票代碼")
    
    with tab2:
        ui.show_download_statistics()
    
    with tab3:
        st.header("ℹ️ 系統信息")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🎯 智能跳過功能")
            if hasattr(RealDataCrawler, 'KNOWN_PROBLEMATIC_STOCKS'):
                known_stocks = RealDataCrawler.KNOWN_PROBLEMATIC_STOCKS
                st.write(f"已知問題股票: {len(known_stocks)} 檔")
                with st.expander("查看詳細列表"):
                    for i, stock in enumerate(known_stocks, 1):
                        st.write(f"{i:2d}. {stock}")
        
        with col2:
            st.subheader("🔧 功能特色")
            st.write("✅ 實時進度條顯示")
            st.write("✅ 可配置跳過選項")
            st.write("✅ 下載歷史統計")
            st.write("✅ 智能檢測算法")
            st.write("✅ 多層次跳過機制")

if __name__ == "__main__":
    main()
