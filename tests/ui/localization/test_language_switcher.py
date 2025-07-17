"""語言切換器測試模組

測試語言切換器的各項功能，包括語言切換、文字獲取、資源載入等。
"""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
import sys

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ui.localization.language_switcher import LanguageSwitcher, get_text, get_language_switcher


class TestLanguageSwitcher:
    """語言切換器測試類"""
    
    def setup_method(self):
        """測試前設定"""
        # 創建臨時語言資源文件
        self.temp_dir = tempfile.mkdtemp()
        
        # 中文資源
        self.zh_data = {
            "common": {
                "save": "儲存",
                "cancel": "取消"
            },
            "app": {
                "title": "測試應用"
            }
        }
        
        # 英文資源
        self.en_data = {
            "common": {
                "save": "Save", 
                "cancel": "Cancel"
            },
            "app": {
                "title": "Test App"
            }
        }
        
        # 寫入測試資源文件
        with open(os.path.join(self.temp_dir, "zh_TW.json"), 'w', encoding='utf-8') as f:
            json.dump(self.zh_data, f, ensure_ascii=False)
            
        with open(os.path.join(self.temp_dir, "en_US.json"), 'w', encoding='utf-8') as f:
            json.dump(self.en_data, f, ensure_ascii=False)
    
    def teardown_method(self):
        """測試後清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.ui.localization.language_switcher.os.path.dirname')
    def test_language_switcher_initialization(self, mock_dirname):
        """測試語言切換器初始化"""
        mock_dirname.return_value = self.temp_dir
        
        switcher = LanguageSwitcher()
        
        # 檢查語言資源是否載入
        assert "zh_TW" in switcher.language_resources
        assert "en_US" in switcher.language_resources
        assert switcher.language_resources["zh_TW"]["common"]["save"] == "儲存"
        assert switcher.language_resources["en_US"]["common"]["save"] == "Save"
    
    @patch('streamlit.session_state', {})
    def test_initialize_language_state(self):
        """測試語言狀態初始化"""
        import streamlit as st
        
        switcher = LanguageSwitcher()
        switcher._initialize_language_state()
        
        assert st.session_state["language"] == "zh_TW"
    
    @patch('streamlit.session_state', {"language": "en_US"})
    def test_get_current_language(self):
        """測試獲取當前語言"""
        switcher = LanguageSwitcher()
        
        assert switcher.get_current_language() == "en_US"
    
    @patch('streamlit.session_state', {})
    def test_set_language_valid(self):
        """測試設定有效語言"""
        import streamlit as st
        
        switcher = LanguageSwitcher()
        result = switcher.set_language("en_US")
        
        assert result is True
        assert st.session_state["language"] == "en_US"
    
    @patch('streamlit.session_state', {})
    def test_set_language_invalid(self):
        """測試設定無效語言"""
        switcher = LanguageSwitcher()
        result = switcher.set_language("invalid_lang")
        
        assert result is False
    
    @patch('src.ui.localization.language_switcher.os.path.dirname')
    @patch('streamlit.session_state', {"language": "zh_TW"})
    def test_get_text_valid_key(self, mock_dirname):
        """測試獲取有效鍵值的文字"""
        mock_dirname.return_value = self.temp_dir
        
        switcher = LanguageSwitcher()
        text = switcher.get_text("common.save")
        
        assert text == "儲存"
    
    @patch('src.ui.localization.language_switcher.os.path.dirname')
    @patch('streamlit.session_state', {"language": "zh_TW"})
    def test_get_text_invalid_key(self, mock_dirname):
        """測試獲取無效鍵值的文字"""
        mock_dirname.return_value = self.temp_dir
        
        switcher = LanguageSwitcher()
        text = switcher.get_text("invalid.key", "預設值")
        
        assert text == "預設值"
    
    @patch('src.ui.localization.language_switcher.os.path.dirname')
    @patch('streamlit.session_state', {"language": "en_US"})
    def test_get_text_english(self, mock_dirname):
        """測試英文文字獲取"""
        mock_dirname.return_value = self.temp_dir
        
        switcher = LanguageSwitcher()
        text = switcher.get_text("common.save")
        
        assert text == "Save"
    
    @patch('src.ui.localization.language_switcher.os.path.dirname')
    @patch('streamlit.session_state', {"language": "invalid_lang"})
    def test_get_text_fallback_to_default(self, mock_dirname):
        """測試回退到預設語言"""
        mock_dirname.return_value = self.temp_dir
        
        switcher = LanguageSwitcher()
        text = switcher.get_text("common.save")
        
        # 應該回退到預設語言（中文）
        assert text == "儲存"
    
    def test_get_language_info(self):
        """測試獲取語言資訊"""
        switcher = LanguageSwitcher()
        info = switcher.get_language_info("zh_TW")
        
        assert info["name"] == "繁體中文"
        assert info["flag"] == "🇹🇼"
        assert info["file"] == "zh_TW.json"
    
    def test_is_rtl_language(self):
        """測試右到左語言檢查"""
        switcher = LanguageSwitcher()
        
        # 目前支援的語言都不是 RTL
        assert switcher.is_rtl_language("zh_TW") is False
        assert switcher.is_rtl_language("en_US") is False
    
    @patch('src.ui.localization.language_switcher.os.path.dirname')
    @patch('streamlit.session_state', {"language": "zh_TW"})
    def test_get_date_format(self, mock_dirname):
        """測試獲取日期格式"""
        mock_dirname.return_value = self.temp_dir
        
        # 添加格式資料到測試資源
        self.zh_data["formats"] = {"date": {"format": "YYYY/MM/DD"}}
        with open(os.path.join(self.temp_dir, "zh_TW.json"), 'w', encoding='utf-8') as f:
            json.dump(self.zh_data, f, ensure_ascii=False)
        
        switcher = LanguageSwitcher()
        date_format = switcher.get_date_format()
        
        assert date_format == "YYYY/MM/DD"
    
    @patch('src.ui.localization.language_switcher.os.path.dirname')
    @patch('streamlit.session_state', {"language": "zh_TW"})
    def test_get_number_format(self, mock_dirname):
        """測試獲取數字格式"""
        mock_dirname.return_value = self.temp_dir
        
        # 添加格式資料到測試資源
        self.zh_data["formats"] = {
            "number": {
                "decimal_separator": ".",
                "thousand_separator": ","
            }
        }
        with open(os.path.join(self.temp_dir, "zh_TW.json"), 'w', encoding='utf-8') as f:
            json.dump(self.zh_data, f, ensure_ascii=False)
        
        switcher = LanguageSwitcher()
        number_format = switcher.get_number_format()
        
        assert number_format["decimal_separator"] == "."
        assert number_format["thousand_separator"] == ","
    
    @patch('streamlit.selectbox')
    @patch('streamlit.sidebar')
    @patch('streamlit.session_state', {"language": "zh_TW"})
    def test_show_language_selector(self, mock_sidebar, mock_selectbox):
        """測試顯示語言選擇器"""
        mock_selectbox.return_value = "🇺🇸 English"
        
        switcher = LanguageSwitcher()
        
        # 模擬 sidebar 上下文管理器
        mock_sidebar.__enter__ = MagicMock(return_value=mock_sidebar)
        mock_sidebar.__exit__ = MagicMock(return_value=None)
        
        with patch('streamlit.rerun'):
            result = switcher.show_language_selector()
        
        assert result == "en_US"
        mock_selectbox.assert_called_once()


class TestGlobalFunctions:
    """全域函數測試類"""
    
    @patch('src.ui.localization.language_switcher.get_language_switcher')
    def test_get_text_function(self, mock_get_switcher):
        """測試全域 get_text 函數"""
        mock_switcher = MagicMock()
        mock_switcher.get_text.return_value = "測試文字"
        mock_get_switcher.return_value = mock_switcher
        
        result = get_text("test.key", "預設值")
        
        assert result == "測試文字"
        mock_switcher.get_text.assert_called_once_with("test.key", "預設值")
    
    def test_get_language_switcher_singleton(self):
        """測試語言切換器單例模式"""
        switcher1 = get_language_switcher()
        switcher2 = get_language_switcher()
        
        assert switcher1 is switcher2


class TestErrorHandling:
    """錯誤處理測試類"""
    
    @patch('src.ui.localization.language_switcher.os.path.dirname')
    def test_missing_language_file(self, mock_dirname):
        """測試語言文件缺失的處理"""
        # 指向不存在的目錄
        mock_dirname.return_value = "/nonexistent/path"
        
        switcher = LanguageSwitcher()
        
        # 應該有空的語言資源
        assert switcher.language_resources["zh_TW"] == {}
        assert switcher.language_resources["en_US"] == {}
    
    @patch('src.ui.localization.language_switcher.os.path.dirname')
    def test_invalid_json_file(self, mock_dirname):
        """測試無效 JSON 文件的處理"""
        temp_dir = tempfile.mkdtemp()
        mock_dirname.return_value = temp_dir
        
        try:
            # 創建無效的 JSON 文件
            with open(os.path.join(temp_dir, "zh_TW.json"), 'w') as f:
                f.write("invalid json content")
            
            switcher = LanguageSwitcher()
            
            # 應該有空的語言資源
            assert switcher.language_resources["zh_TW"] == {}
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__])
