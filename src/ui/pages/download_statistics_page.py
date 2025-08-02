"""
下載統計報告頁面
提供詳細的下載歷史分析和統計報告
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

class DownloadStatisticsAnalyzer:
    """下載統計分析器"""
    
    def __init__(self):
        self.history_file = "data/download_history.json"
    
    def load_history(self):
        """載入下載歷史"""
        try:
            if Path(self.history_file).exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            st.error(f"載入歷史數據失敗: {e}")
            return []
    
    def show_overview_metrics(self, history):
        """顯示總覽指標"""
        if not history:
            st.info("📊 暫無下載歷史數據")
            return
        
        # 計算總體統計
        total_downloads = len(history)
        total_stocks = sum(h.get('total', 0) for h in history)
        total_successful = sum(h.get('successful', 0) for h in history)
        total_skipped = sum(h.get('skipped', 0) for h in history)
        total_failed = sum(h.get('failed', 0) for h in history)
        total_duration = sum(h.get('duration', 0) for h in history)
        
        avg_success_rate = np.mean([h.get('success_rate', 0) for h in history])
        
        st.subheader("📊 總體統計")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("下載次數", total_downloads)
        
        with col2:
            st.metric("處理股票", f"{total_stocks:,} 檔")
        
        with col3:
            st.metric("平均成功率", f"{avg_success_rate:.1f}%")
        
        with col4:
            st.metric("總節省時間", f"{total_skipped * 5:.0f} 秒", 
                     help="基於每檔問題股票節省5秒計算")
        
        with col5:
            st.metric("總下載時間", f"{total_duration:.1f} 秒")
    
    def show_trend_analysis(self, history):
        """顯示趨勢分析"""
        if len(history) < 2:
            st.info("📈 需要至少2次下載記錄才能顯示趨勢")
            return
        
        st.subheader("📈 趨勢分析")
        
        # 準備數據
        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        
        # 創建子圖
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('成功率趨勢', '下載時間趨勢', '股票數量趨勢', '跳過比例趨勢'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # 成功率趨勢
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['success_rate'], 
                      mode='lines+markers', name='成功率',
                      line=dict(color='green')),
            row=1, col=1
        )
        
        # 下載時間趨勢
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['duration'], 
                      mode='lines+markers', name='下載時間',
                      line=dict(color='blue')),
            row=1, col=2
        )
        
        # 股票數量趨勢
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['total'], 
                      mode='lines+markers', name='股票數量',
                      line=dict(color='orange')),
            row=2, col=1
        )
        
        # 跳過比例趨勢
        df['skip_rate'] = (df['skipped'] / df['total'] * 100).fillna(0)
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['skip_rate'], 
                      mode='lines+markers', name='跳過比例',
                      line=dict(color='red')),
            row=2, col=2
        )
        
        # 更新布局
        fig.update_layout(height=600, showlegend=False)
        fig.update_xaxes(title_text="時間")
        fig.update_yaxes(title_text="成功率 (%)", row=1, col=1)
        fig.update_yaxes(title_text="時間 (秒)", row=1, col=2)
        fig.update_yaxes(title_text="股票數量", row=2, col=1)
        fig.update_yaxes(title_text="跳過比例 (%)", row=2, col=2)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def show_performance_analysis(self, history):
        """顯示性能分析"""
        if not history:
            return
        
        st.subheader("⚡ 性能分析")
        
        # 最近的下載記錄
        latest = history[-1]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**最近下載性能**")
            
            # 性能指標
            if latest.get('total', 0) > 0:
                avg_time_per_stock = latest['duration'] / latest['total']
                st.metric("每檔股票平均時間", f"{avg_time_per_stock:.2f} 秒")
                
                efficiency_score = (latest.get('successful', 0) + latest.get('skipped', 0)) / latest['total'] * 100
                st.metric("處理效率", f"{efficiency_score:.1f}%", 
                         help="成功下載和智能跳過的比例")
        
        with col2:
            st.write("**智能跳過效果**")
            
            if latest.get('skipped', 0) > 0:
                time_saved = latest['skipped'] * 5  # 假設每檔問題股票節省5秒
                st.metric("節省時間", f"{time_saved} 秒")
                
                skip_rate = latest['skipped'] / latest['total'] * 100
                st.metric("跳過比例", f"{skip_rate:.1f}%")
        
        # 性能分布圖
        if len(history) >= 5:
            df = pd.DataFrame(history)
            df['avg_time_per_stock'] = df['duration'] / df['total']
            
            fig = px.histogram(df, x='avg_time_per_stock', 
                             title='每檔股票平均處理時間分布',
                             labels={'avg_time_per_stock': '平均時間 (秒)', 'count': '次數'})
            st.plotly_chart(fig, use_container_width=True)
    
    def show_detailed_history(self, history):
        """顯示詳細歷史"""
        if not history:
            return
        
        st.subheader("📋 詳細下載歷史")
        
        # 準備表格數據
        table_data = []
        for i, record in enumerate(reversed(history[-20:]), 1):  # 最近20次
            table_data.append({
                '序號': i,
                '時間': datetime.fromisoformat(record['timestamp']).strftime('%m-%d %H:%M'),
                '總數': record.get('total', 0),
                '成功': record.get('successful', 0),
                '跳過': record.get('skipped', 0),
                '失敗': record.get('failed', 0),
                '成功率': f"{record.get('success_rate', 0):.1f}%",
                '耗時': f"{record.get('duration', 0):.1f}s",
                '效率': f"{(record.get('successful', 0) + record.get('skipped', 0)) / max(record.get('total', 1), 1) * 100:.1f}%"
            })
        
        df_table = pd.DataFrame(table_data)
        
        # 使用顏色標示性能
        def highlight_performance(val):
            if isinstance(val, str) and val.endswith('%'):
                num_val = float(val.replace('%', ''))
                if num_val >= 90:
                    return 'background-color: lightgreen'
                elif num_val >= 70:
                    return 'background-color: lightyellow'
                else:
                    return 'background-color: lightcoral'
            return ''
        
        styled_df = df_table.style.applymap(highlight_performance, subset=['成功率', '效率'])
        st.dataframe(styled_df, use_container_width=True)
    
    def show_problem_stock_analysis(self, history):
        """顯示問題股票分析"""
        st.subheader("🎯 問題股票分析")
        
        # 統計所有詳細記錄中的問題股票
        problem_stocks = {}
        total_skipped = 0
        
        for record in history:
            details = record.get('details', [])
            for detail in details:
                if detail.get('status') in ['skipped', 'failed']:
                    symbol = detail.get('symbol', '')
                    if symbol:
                        if symbol not in problem_stocks:
                            problem_stocks[symbol] = {'count': 0, 'status': detail['status']}
                        problem_stocks[symbol]['count'] += 1
                        
                        if detail['status'] == 'skipped':
                            total_skipped += 1
        
        if problem_stocks:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**問題股票統計**")
                
                # 排序並顯示前10個問題股票
                sorted_problems = sorted(problem_stocks.items(), 
                                       key=lambda x: x[1]['count'], reverse=True)[:10]
                
                problem_df = pd.DataFrame([
                    {
                        '股票代碼': symbol,
                        '出現次數': data['count'],
                        '狀態': '跳過' if data['status'] == 'skipped' else '失敗'
                    }
                    for symbol, data in sorted_problems
                ])
                
                st.dataframe(problem_df, use_container_width=True)
            
            with col2:
                st.write("**跳過效果統計**")
                
                time_saved = total_skipped * 5  # 每次跳過節省5秒
                st.metric("總跳過次數", total_skipped)
                st.metric("累計節省時間", f"{time_saved} 秒 ({time_saved/60:.1f} 分鐘)")
                
                # 問題股票類型分布
                if len(sorted_problems) > 0:
                    fig = px.pie(
                        values=[data['count'] for _, data in sorted_problems[:5]],
                        names=[symbol for symbol, _ in sorted_problems[:5]],
                        title="前5大問題股票分布"
                    )
                    st.plotly_chart(fig, use_container_width=True)

def show_download_statistics_page():
    """顯示下載統計頁面"""
    st.title("📊 下載統計報告")
    st.markdown("---")
    
    analyzer = DownloadStatisticsAnalyzer()
    history = analyzer.load_history()
    
    if not history:
        st.info("📊 暫無下載歷史數據，請先執行一些下載操作")
        st.markdown("### 💡 建議")
        st.markdown("- 前往 **增強下載** 頁面執行股票數據下載")
        st.markdown("- 啟用 **自動保存結果** 選項")
        st.markdown("- 下載完成後返回此頁面查看統計報告")
        return
    
    # 總覽指標
    analyzer.show_overview_metrics(history)
    
    st.markdown("---")
    
    # 趨勢分析
    analyzer.show_trend_analysis(history)
    
    st.markdown("---")
    
    # 性能分析
    analyzer.show_performance_analysis(history)
    
    st.markdown("---")
    
    # 問題股票分析
    analyzer.show_problem_stock_analysis(history)
    
    st.markdown("---")
    
    # 詳細歷史
    analyzer.show_detailed_history(history)
    
    # 數據導出
    st.markdown("---")
    st.subheader("📤 數據導出")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 導出統計數據"):
            df_export = pd.DataFrame(history)
            csv = df_export.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="💾 下載 CSV 文件",
                data=csv,
                file_name=f"download_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("🗑️ 清除歷史數據"):
            if st.button("⚠️ 確認清除", type="secondary"):
                try:
                    if Path(analyzer.history_file).exists():
                        Path(analyzer.history_file).unlink()
                    st.success("✅ 歷史數據已清除")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ 清除失敗: {e}")

if __name__ == "__main__":
    show_download_statistics_page()
