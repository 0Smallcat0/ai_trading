#!/usr/bin/env python3
"""
AI Module Registry - Phase 2 Performance Optimization

Centralized registry for AI modules with lazy loading integration.
Provides standardized loading functions and fallback mechanisms
for heavy AI modules like SelfLearningAgent.

Features:
- Standardized AI module loading functions
- Automatic fallback mechanisms for failed imports
- Performance monitoring and error handling
- Integration with AI lazy loader system
"""

import logging
from typing import Optional, Any, Dict, Callable
import time
from pathlib import Path

from .ai_lazy_loader import register_ai_module

logger = logging.getLogger(__name__)


def load_self_learning_agent() -> Optional[Any]:
    """Load SelfLearningAgent with fallback mechanisms"""
    start_time = time.time()
    
    try:
        # Try to import the main SelfLearningAgent
        from src.ai.self_learning_agent import SelfLearningAgent
        
        # Initialize with optimized settings for faster startup
        agent = SelfLearningAgent(
            agent_id="web_ui_agent",
            model_path="models/web_ui/"
        )
        
        load_time = time.time() - start_time
        logger.info(f"SelfLearningAgent loaded successfully in {load_time:.2f}s")
        return agent
        
    except ImportError as e:
        logger.warning(f"Failed to import SelfLearningAgent: {e}")
        return _create_self_learning_agent_fallback()
    
    except Exception as e:
        logger.error(f"Error initializing SelfLearningAgent: {e}")
        return _create_self_learning_agent_fallback()


def load_integrated_feature_calculator() -> Optional[Any]:
    """Load IntegratedFeatureCalculator with fallback mechanisms"""
    start_time = time.time()
    
    try:
        from src.core.integrated_feature_calculator import IntegratedFeatureCalculator
        
        # Initialize with optimized settings
        calculator = IntegratedFeatureCalculator()
        
        load_time = time.time() - start_time
        logger.info(f"IntegratedFeatureCalculator loaded successfully in {load_time:.2f}s")
        return calculator
        
    except ImportError as e:
        logger.warning(f"Failed to import IntegratedFeatureCalculator: {e}")
        return _create_feature_calculator_fallback()
    
    except Exception as e:
        logger.error(f"Error initializing IntegratedFeatureCalculator: {e}")
        return _create_feature_calculator_fallback()


def load_interactive_charts() -> Optional[Dict[str, Any]]:
    """Load interactive charts components with fallback mechanisms"""
    start_time = time.time()
    
    try:
        from src.ui.components.interactive_charts import (
            agent_integrated_display,
            create_integrated_chart,
            generate_trading_signals
        )
        
        components = {
            'agent_integrated_display': agent_integrated_display,
            'create_integrated_chart': create_integrated_chart,
            'generate_trading_signals': generate_trading_signals
        }
        
        load_time = time.time() - start_time
        logger.info(f"Interactive charts loaded successfully in {load_time:.2f}s")
        return components
        
    except ImportError as e:
        logger.warning(f"Failed to import interactive charts: {e}")
        return _create_interactive_charts_fallback()
    
    except Exception as e:
        logger.error(f"Error loading interactive charts: {e}")
        return _create_interactive_charts_fallback()


def load_ai_model_management_service() -> Optional[Any]:
    """Load AI Model Management Service with fallback mechanisms"""
    start_time = time.time()
    
    try:
        from src.core.ai_model_management_service import AIModelManagementService
        
        service = AIModelManagementService()
        
        load_time = time.time() - start_time
        logger.info(f"AI Model Management Service loaded successfully in {load_time:.2f}s")
        return service
        
    except ImportError as e:
        logger.warning(f"Failed to import AI Model Management Service: {e}")
        return _create_ai_model_service_fallback()
    
    except Exception as e:
        logger.error(f"Error initializing AI Model Management Service: {e}")
        return _create_ai_model_service_fallback()


def load_enhanced_data_visualization() -> Optional[Any]:
    """Load Enhanced Data Visualization with fallback mechanisms"""
    start_time = time.time()
    
    try:
        from src.ui.components.enhanced_data_visualization import EnhancedDataVisualizer
        
        visualizer = EnhancedDataVisualizer()
        
        load_time = time.time() - start_time
        logger.info(f"Enhanced Data Visualization loaded successfully in {load_time:.2f}s")
        return visualizer
        
    except ImportError as e:
        logger.warning(f"Failed to import Enhanced Data Visualization: {e}")
        return _create_data_visualization_fallback()
    
    except Exception as e:
        logger.error(f"Error initializing Enhanced Data Visualization: {e}")
        return _create_data_visualization_fallback()


# Fallback implementations
def _create_self_learning_agent_fallback() -> Any:
    """Create fallback SelfLearningAgent implementation"""
    
    class SelfLearningAgentFallback:
        """Fallback implementation for SelfLearningAgent"""
        
        def __init__(self, agent_id: str = "fallback", model_path: str = ""):
            self.agent_id = agent_id
            self.model_path = model_path
            self.is_fallback = True
            logger.info("Using SelfLearningAgent fallback implementation")
        
        def learn_from_interaction(self, interaction_data: Dict[str, Any]) -> None:
            """Fallback learning method"""
            logger.debug("Fallback: learn_from_interaction called")
        
        def get_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
            """Fallback recommendations method"""
            return {
                'recommendations': ['基礎分析建議', '技術指標建議'],
                'confidence': 0.5,
                'source': 'fallback'
            }
        
        def optimize_parameters(self, objective: str) -> Dict[str, Any]:
            """Fallback parameter optimization"""
            return {
                'optimized_params': {'param1': 1.0, 'param2': 0.5},
                'score': 0.7,
                'source': 'fallback'
            }
    
    return SelfLearningAgentFallback()


def _create_feature_calculator_fallback() -> Any:
    """Create fallback IntegratedFeatureCalculator implementation"""
    
    class FeatureCalculatorFallback:
        """Fallback implementation for IntegratedFeatureCalculator"""
        
        def __init__(self):
            self.is_fallback = True
            logger.info("Using IntegratedFeatureCalculator fallback implementation")
        
        def calculate_features(self, data, indicators=None, multipliers=None):
            """Fallback feature calculation"""
            import pandas as pd
            import numpy as np
            
            # Basic technical indicators calculation
            if indicators is None:
                indicators = ['RSI', 'MACD', 'SMA']
            
            result = data.copy()
            
            # Simple RSI calculation
            if 'RSI' in indicators:
                delta = data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                result['RSI'] = 100 - (100 / (1 + rs))
            
            # Simple MACD calculation
            if 'MACD' in indicators:
                ema12 = data['close'].ewm(span=12).mean()
                ema26 = data['close'].ewm(span=26).mean()
                result['MACD'] = ema12 - ema26
                result['MACD_signal'] = result['MACD'].ewm(span=9).mean()
            
            # Simple SMA calculation
            if 'SMA' in indicators:
                result['SMA_20'] = data['close'].rolling(window=20).mean()
            
            return result
    
    return FeatureCalculatorFallback()


def _create_interactive_charts_fallback() -> Dict[str, Any]:
    """Create fallback interactive charts implementation"""
    
    def agent_integrated_display_fallback(*args, **kwargs):
        """Fallback for agent_integrated_display"""
        import streamlit as st
        st.info("🔄 AI整合圖表功能使用基礎版本")
        return None
    
    def create_integrated_chart_fallback(*args, **kwargs):
        """Fallback for create_integrated_chart"""
        import plotly.graph_objects as go
        
        # Create basic chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[1, 2, 3, 4],
            y=[10, 11, 12, 13],
            mode='lines',
            name='基礎圖表'
        ))
        fig.update_layout(title="基礎圖表 (備用版本)")
        return fig
    
    def generate_trading_signals_fallback(*args, **kwargs):
        """Fallback for generate_trading_signals"""
        return {
            'signals': [
                {'type': 'buy', 'strength': 0.6, 'reason': '基礎訊號'},
                {'type': 'hold', 'strength': 0.8, 'reason': '基礎訊號'}
            ],
            'source': 'fallback'
        }
    
    return {
        'agent_integrated_display': agent_integrated_display_fallback,
        'create_integrated_chart': create_integrated_chart_fallback,
        'generate_trading_signals': generate_trading_signals_fallback
    }


def _create_ai_model_service_fallback() -> Any:
    """Create fallback AI Model Management Service implementation"""
    
    class AIModelServiceFallback:
        """Fallback implementation for AI Model Management Service"""
        
        def __init__(self):
            self.is_fallback = True
            logger.info("Using AI Model Management Service fallback implementation")
        
        def get_available_models(self) -> Dict[str, Any]:
            """Fallback model listing"""
            return {
                'models': ['基礎預測模型', '簡單分類模型'],
                'count': 2,
                'source': 'fallback'
            }
        
        def load_model(self, model_name: str) -> Any:
            """Fallback model loading"""
            logger.info(f"Fallback: Loading model {model_name}")
            return {'model': 'fallback_model', 'status': 'loaded'}
    
    return AIModelServiceFallback()


def _create_data_visualization_fallback() -> Any:
    """Create fallback Enhanced Data Visualization implementation"""
    
    class DataVisualizationFallback:
        """Fallback implementation for Enhanced Data Visualization"""
        
        def __init__(self):
            self.is_fallback = True
            logger.info("Using Enhanced Data Visualization fallback implementation")
        
        def create_enhanced_chart(self, data, chart_type='line'):
            """Fallback chart creation"""
            import plotly.graph_objects as go
            
            fig = go.Figure()
            if 'close' in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data['close'],
                    mode='lines',
                    name='股價'
                ))
            
            fig.update_layout(title="基礎圖表 (備用版本)")
            return fig
    
    return DataVisualizationFallback()


def register_all_ai_modules() -> None:
    """Register all AI modules with the lazy loader"""
    
    # Register SelfLearningAgent (highest priority, longest load time)
    register_ai_module(
        module_name="self_learning_agent",
        import_path="src.ai.self_learning_agent",
        loader_func=load_self_learning_agent,
        priority=10,
        estimated_load_time=15.0,
        dependencies=[],
        fallback_available=True
    )
    
    # Register IntegratedFeatureCalculator
    register_ai_module(
        module_name="integrated_feature_calculator",
        import_path="src.core.integrated_feature_calculator",
        loader_func=load_integrated_feature_calculator,
        priority=9,
        estimated_load_time=2.0,
        dependencies=[],
        fallback_available=True
    )
    
    # Register Interactive Charts
    register_ai_module(
        module_name="interactive_charts",
        import_path="src.ui.components.interactive_charts",
        loader_func=load_interactive_charts,
        priority=8,
        estimated_load_time=1.5,
        dependencies=["integrated_feature_calculator"],
        fallback_available=True
    )
    
    # Register AI Model Management Service
    register_ai_module(
        module_name="ai_model_management_service",
        import_path="src.core.ai_model_management_service",
        loader_func=load_ai_model_management_service,
        priority=7,
        estimated_load_time=3.0,
        dependencies=[],
        fallback_available=True
    )
    
    # Register Enhanced Data Visualization
    register_ai_module(
        module_name="enhanced_data_visualization",
        import_path="src.ui.components.enhanced_data_visualization",
        loader_func=load_enhanced_data_visualization,
        priority=6,
        estimated_load_time=1.0,
        dependencies=[],
        fallback_available=True
    )
    
    logger.info("All AI modules registered with lazy loader")


# Auto-register modules when imported
register_all_ai_modules()
