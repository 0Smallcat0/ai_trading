#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dash + Plotly 動態技術指標選擇系統

基於設計文檔的完整實現示例
"""

import dash
from dash import dcc, html, Input, Output, State, callback, ctx, ALL, MATCH
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# 初始化Dash應用
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# 技術指標配置
INDICATOR_CONFIG = {
    'RSI': {
        'name': 'RSI',
        'description': '相對強弱指標 - 動能震盪指標，判斷超買超賣',
        'color': '#ff6b6b',
        'min_days': 14
    },
    'MACD': {
        'name': 'MACD',
        'description': '移動平均收斂散度 - 趨勢跟隨指標',
        'color': '#4ecdc4',
        'min_days': 26
    },
    'SMA': {
        'name': 'SMA',
        'description': '簡單移動平均線 - 趨勢確認指標',
        'color': '#45b7d1',
        'min_days': 20
    },
    'EMA': {
        'name': 'EMA',
        'description': '指數移動平均線 - 敏感趨勢指標',
        'color': '#f9ca24',
        'min_days': 20
    },
    'BBANDS': {
        'name': 'BBANDS',
        'description': '布林帶 - 波動通道分析',
        'color': '#6c5ce7',
        'min_days': 20
    },
    'KD': {
        'name': 'KD',
        'description': '隨機指標 - 短線買賣點判斷',
        'color': '#fd79a8',
        'min_days': 9
    },
    'CCI': {
        'name': 'CCI',
        'description': '順勢指標 - 極值分析',
        'color': '#00b894',
        'min_days': 20
    },
    'ATR': {
        'name': 'ATR',
        'description': '平均真實波幅 - 風險管理指標',
        'color': '#e17055',
        'min_days': 14
    }
}

# 預設模板
DEFAULT_TEMPLATES = {
    'basic': {
        'name': '基礎分析',
        'indicators': ['RSI', 'MACD'],
        'description': '適合新手的基礎技術指標組合'
    },
    'advanced': {
        'name': '進階分析',
        'indicators': ['RSI', 'MACD', 'BBANDS', 'KD'],
        'description': '適合有經驗交易者的完整分析'
    },
    'trend_following': {
        'name': '趨勢跟隨',
        'indicators': ['SMA', 'EMA', 'MACD'],
        'description': '專注於趨勢識別和跟隨'
    }
}

def generate_sample_data(symbol="2330.TW", days=120):
    """生成示例股票數據"""
    np.random.seed(42)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # 生成價格數據
    initial_price = 100.0
    prices = [initial_price]
    
    for i in range(1, len(dates)):
        trend = 0.0005 * np.sin(i / 20)
        noise = np.random.normal(0, 0.015)
        daily_return = trend + noise
        new_price = prices[-1] * (1 + daily_return)
        prices.append(max(new_price, 1.0))
    
    # 生成OHLC數據
    df = pd.DataFrame({
        'date': dates,
        'close': prices
    })
    
    df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])
    daily_range = np.random.uniform(0.005, 0.02, len(df))
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + daily_range * 0.7)
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - daily_range * 0.7)
    
    # 生成成交量
    price_change = df['close'].pct_change().abs().fillna(0)
    base_volume = 5000000
    volume_multiplier = 1 + price_change * 3
    volume_values = base_volume * volume_multiplier * np.random.uniform(0.5, 1.5, len(df))
    df['volume'] = volume_values.astype(int)
    
    return df

def create_indicator_grid():
    """創建網格式指標選擇器"""
    indicator_cards = []
    
    for key, config in INDICATOR_CONFIG.items():
        card = dbc.Card([
            dbc.CardBody([
                html.Div([
                    dbc.Checkbox(
                        id={'type': 'indicator-check', 'index': key},
                        value=False,
                        style={'transform': 'scale(1.2)'}
                    ),
                    html.H6(
                        config['name'], 
                        className='card-title',
                        style={'color': config['color'], 'margin': '5px 0'}
                    ),
                    html.P(
                        config['description'],
                        className='card-text',
                        style={'font-size': '0.8rem', 'color': '#aaa'}
                    ),
                    dbc.Badge(
                        f"需{config['min_days']}天",
                        color='secondary',
                        className='mb-1'
                    )
                ])
            ])
        ], 
        style={
            'background': '#2d2d2d',
            'border': f'2px solid {config["color"]}',
            'border-radius': '8px',
            'margin': '5px'
        })
        indicator_cards.append(card)
    
    return html.Div([
        html.Div([
            html.H5("📊 技術指標選擇", style={'color': '#00ff88'}),
            dbc.ButtonGroup([
                dbc.Button("全選", id='btn-select-all', size='sm', color='success'),
                dbc.Button("清除", id='btn-clear-all', size='sm', color='danger'),
                dbc.Button("常用組合", id='btn-common', size='sm', color='info')
            ], style={'margin-bottom': '10px'})
        ]),
        html.Div(
            indicator_cards,
            style={
                'display': 'grid',
                'grid-template-columns': 'repeat(auto-fit, minmax(200px, 1fr))',
                'gap': '10px',
                'max-height': '400px',
                'overflow-y': 'auto'
            }
        )
    ])

def create_theme_switcher():
    """創建主題切換器"""
    return html.Div([
        html.Label("🎨 主題選擇", style={'color': '#00ff88'}),
        dcc.RadioItems(
            id='theme-switcher',
            options=[
                {'label': '🌙 深色', 'value': 'dark'},
                {'label': '☀️ 淺色', 'value': 'light'},
                {'label': '🔆 高對比', 'value': 'high_contrast'}
            ],
            value='dark',
            inline=True,
            style={'margin': '10px 0'}
        )
    ])

def create_template_manager():
    """創建模板管理器"""
    return html.Div([
        html.H5("💾 模板管理", style={'color': '#00ff88'}),
        
        # 預設模板
        html.Div([
            html.H6("📋 預設模板"),
            dbc.ButtonGroup([
                dbc.Button(
                    template['name'],
                    id={'type': 'template-btn', 'template': key},
                    size='sm',
                    color='info',
                    className='me-2 mb-2'
                ) for key, template in DEFAULT_TEMPLATES.items()
            ])
        ], style={'margin-bottom': '15px'}),
        
        # 自定義模板
        html.Div([
            html.H6("🎨 自定義模板"),
            dbc.InputGroup([
                dbc.Input(
                    id='template-name-input',
                    placeholder='輸入模板名稱...',
                    type='text'
                ),
                dbc.Button(
                    "💾 保存當前設置",
                    id='save-template-btn',
                    color='success'
                )
            ], className='mb-2'),
            
            html.Div(id='custom-templates-list')
        ])
    ])

def create_responsive_layout():
    """創建響應式布局"""
    return dbc.Container([
        # 標題區
        dbc.Row([
            dbc.Col([
                html.H1("📊 動態技術指標選擇系統", 
                       style={'color': '#00ff88', 'text-align': 'center'})
            ], width=12)
        ], className='mb-4'),
        
        # 主要內容區
        dbc.Row([
            # 左側控制面板
            dbc.Col([
                # 指標選擇
                create_indicator_grid(),
                html.Hr(),
                # 主題切換
                create_theme_switcher(),
                html.Hr(),
                # 模板管理
                create_template_manager()
            ], width=12, lg=4, className='mb-3'),
            
            # 右側圖表區
            dbc.Col([
                # 載入指示器
                dcc.Loading(
                    id="loading-chart",
                    type="dot",
                    children=[
                        dcc.Graph(
                            id='main-chart',
                            style={'height': '80vh'},
                            config={
                                'responsive': True,
                                'displayModeBar': True,
                                'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
                            }
                        )
                    ]
                ),
                
                # 數據狀態指示器
                html.Div([
                    html.Span("數據狀態: "),
                    html.Span(id='data-status-badge')
                ], style={'margin-top': '10px'})
            ], width=12, lg=8)
        ]),
        
        # 隱藏的數據存儲
        dcc.Store(id='stock-data-store', data=generate_sample_data().to_dict('records'))
    ], fluid=True)

# 設置應用布局
app.layout = create_responsive_layout()

# 回調函數
@callback(
    [Output({'type': 'indicator-check', 'index': ALL}, 'value')],
    [Input('btn-select-all', 'n_clicks'),
     Input('btn-clear-all', 'n_clicks'),
     Input('btn-common', 'n_clicks')],
    prevent_initial_call=True
)
def handle_bulk_selection(select_all, clear_all, common):
    """處理批量選擇操作"""
    ctx_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if ctx_id == 'btn-select-all':
        return [[True] * len(INDICATOR_CONFIG)]
    elif ctx_id == 'btn-clear-all':
        return [[False] * len(INDICATOR_CONFIG)]
    elif ctx_id == 'btn-common':
        # 常用組合：RSI + MACD + SMA
        common_indicators = ['RSI', 'MACD', 'SMA']
        values = [key in common_indicators for key in INDICATOR_CONFIG.keys()]
        return [values]
    
    return [[False] * len(INDICATOR_CONFIG)]

if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=8050)
