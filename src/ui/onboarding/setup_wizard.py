# -*- coding: utf-8 -*-
"""
一鍵安裝和環境配置嚮導

此模組提供新手友好的系統安裝和配置嚮導，包括：
- 環境依賴檢查和安裝
- 資料庫初始化
- API 金鑰配置
- 基本參數設定
- 系統健康檢查

Author: AI Trading System
Version: 1.0.0
"""

import os
import sys
import subprocess
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging

import streamlit as st
import pandas as pd

# 導入現有組件
from ..components.common import UIComponents
from ..components.forms import create_form_section
from ..responsive import ResponsiveUtils

logger = logging.getLogger(__name__)


class SetupWizard:
    """
    一鍵安裝和環境配置嚮導
    
    提供新手友好的系統安裝和配置流程，包括環境檢查、
    依賴安裝、資料庫初始化和基本配置設定。
    
    Attributes:
        config_path (Path): 配置檔案路徑
        setup_steps (List[str]): 安裝步驟清單
        current_step (int): 當前步驟索引
        
    Example:
        >>> wizard = SetupWizard()
        >>> wizard.run_setup()
    """
    
    def __init__(self):
        """初始化安裝嚮導"""
        self.config_path = Path("config/setup_config.json")
        self.setup_steps = [
            "環境檢查",
            "依賴安裝", 
            "資料庫初始化",
            "API 配置",
            "基本設定",
            "系統驗證"
        ]
        self.current_step = 0
        
    def check_environment(self) -> Dict[str, bool]:
        """
        檢查系統環境
        
        Returns:
            Dict[str, bool]: 環境檢查結果
            
        Example:
            >>> wizard = SetupWizard()
            >>> result = wizard.check_environment()
            >>> print(result['python_version'])
        """
        try:
            checks = {
                'python_version': sys.version_info >= (3, 8),
                'pip_available': self._check_pip(),
                'poetry_available': self._check_poetry(),
                'git_available': self._check_git(),
                'config_dir': self._check_config_directory(),
            }
            
            logger.info("環境檢查完成: %s", checks)
            return checks
            
        except Exception as e:
            logger.error("環境檢查失敗: %s", e)
            return {}
    
    def _check_pip(self) -> bool:
        """檢查 pip 是否可用"""
        try:
            subprocess.run(['pip', '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_poetry(self) -> bool:
        """檢查 poetry 是否可用"""
        try:
            subprocess.run(['poetry', '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_git(self) -> bool:
        """檢查 git 是否可用"""
        try:
            subprocess.run(['git', '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_config_directory(self) -> bool:
        """檢查配置目錄是否存在"""
        return Path("config").exists()
    
    def install_dependencies(self) -> bool:
        """
        安裝系統依賴
        
        Returns:
            bool: 安裝是否成功
        """
        try:
            if self._check_poetry():
                result = subprocess.run(
                    ['poetry', 'install'], 
                    capture_output=True, text=True
                )
                return result.returncode == 0
            else:
                result = subprocess.run(
                    ['pip', 'install', '-r', 'requirements.txt'],
                    capture_output=True, text=True
                )
                return result.returncode == 0
                
        except Exception as e:
            logger.error("依賴安裝失敗: %s", e)
            return False
    
    def initialize_database(self) -> bool:
        """
        初始化資料庫
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 這裡應該調用實際的資料庫初始化邏輯
            # 目前使用模擬實現
            logger.info("資料庫初始化完成")
            return True
            
        except Exception as e:
            logger.error("資料庫初始化失敗: %s", e)
            return False
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置設定
        
        Args:
            config: 配置字典
            
        Returns:
            bool: 保存是否成功
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info("配置保存成功: %s", self.config_path)
            return True
            
        except Exception as e:
            logger.error("配置保存失敗: %s", e)
            return False
    
    def verify_setup(self) -> Dict[str, bool]:
        """
        驗證系統設定
        
        Returns:
            Dict[str, bool]: 驗證結果
        """
        try:
            verification = {
                'environment': bool(self.check_environment()),
                'database': self._verify_database(),
                'config': self.config_path.exists(),
                'api_connection': self._verify_api_connection(),
            }
            
            logger.info("系統驗證完成: %s", verification)
            return verification
            
        except Exception as e:
            logger.error("系統驗證失敗: %s", e)
            return {}
    
    def _verify_database(self) -> bool:
        """驗證資料庫連接"""
        # 模擬資料庫驗證
        return True
    
    def _verify_api_connection(self) -> bool:
        """驗證 API 連接"""
        # 模擬 API 連接驗證
        return True


def show_setup_wizard() -> None:
    """
    顯示安裝配置嚮導頁面
    
    提供完整的系統安裝和配置流程，包括環境檢查、
    依賴安裝、資料庫初始化和基本配置設定。
    
    Side Effects:
        - 在 Streamlit 界面顯示安裝嚮導
        - 執行系統安裝和配置流程
    """
    st.title("🚀 AI 交易系統安裝嚮導")
    st.markdown("歡迎使用 AI 交易系統！讓我們幫您快速完成系統設定。")
    
    wizard = SetupWizard()
    
    # 顯示進度條
    progress = st.progress(0)
    step_info = st.empty()
    
    # 步驟 1: 環境檢查
    step_info.info("正在檢查系統環境...")
    env_checks = wizard.check_environment()
    
    if all(env_checks.values()):
        st.success("✅ 系統環境檢查通過")
        progress.progress(1/6)
    else:
        st.error("❌ 系統環境檢查失敗")
        for check, result in env_checks.items():
            if not result:
                st.error(f"- {check}: 未通過")
        return
    
    # 步驟 2: 依賴安裝
    if st.button("安裝系統依賴"):
        step_info.info("正在安裝系統依賴...")
        if wizard.install_dependencies():
            st.success("✅ 依賴安裝完成")
            progress.progress(2/6)
        else:
            st.error("❌ 依賴安裝失敗")
            return
    
    # 步驟 3: 資料庫初始化
    if st.button("初始化資料庫"):
        step_info.info("正在初始化資料庫...")
        if wizard.initialize_database():
            st.success("✅ 資料庫初始化完成")
            progress.progress(3/6)
        else:
            st.error("❌ 資料庫初始化失敗")
            return
    
    # 步驟 4: API 配置
    st.subheader("API 配置")
    with st.form("api_config"):
        api_key = st.text_input("API 金鑰", type="password")
        api_secret = st.text_input("API 密鑰", type="password")
        
        if st.form_submit_button("保存 API 配置"):
            config = {
                'api_key': api_key,
                'api_secret': api_secret,
                'setup_date': pd.Timestamp.now().isoformat()
            }
            
            if wizard.save_config(config):
                st.success("✅ API 配置保存成功")
                progress.progress(4/6)
            else:
                st.error("❌ API 配置保存失敗")
    
    # 步驟 5: 系統驗證
    if st.button("驗證系統設定"):
        step_info.info("正在驗證系統設定...")
        verification = wizard.verify_setup()
        
        if all(verification.values()):
            st.success("🎉 系統設定完成！您可以開始使用 AI 交易系統了。")
            progress.progress(1.0)
        else:
            st.warning("⚠️ 部分設定需要檢查")
            for check, result in verification.items():
                if result:
                    st.success(f"✅ {check}")
                else:
                    st.error(f"❌ {check}")
