"""語言切換器模組

此模組提供 Streamlit 語言切換組件和語言狀態管理功能。
支援中英文切換，並提供簡潔的語言選擇界面。

主要功能：
- 語言切換組件
- 語言狀態管理
- 語言資源載入
- 本地化文字獲取

Example:
    基本使用：
    ```python
    from src.ui.localization.language_switcher import LanguageSwitcher
    
    # 初始化語言切換器
    switcher = LanguageSwitcher()
    
    # 顯示語言切換組件
    switcher.show_language_selector()
    
    # 獲取本地化文字
    text = switcher.get_text("common.save")
    ```

Note:
    此模組依賴於 Streamlit 和語言資源文件，確保所有依賴已正確安裝。
"""

import json
import os
from typing import Dict, Any, Optional
import logging

import streamlit as st


class LanguageSwitcher:
    """語言切換器類
    
    提供語言切換功能和本地化文字管理。支援中英文切換，
    並提供簡潔的語言選擇界面和語言狀態管理。
    
    Attributes:
        supported_languages: 支援的語言列表
        default_language: 預設語言
        language_resources: 語言資源快取
        
    Methods:
        show_language_selector: 顯示語言選擇器
        get_current_language: 獲取當前語言
        set_language: 設定語言
        get_text: 獲取本地化文字
        load_language_resources: 載入語言資源
    """
    
    # 支援的語言配置 (增強版)
    SUPPORTED_LANGUAGES = {
        "zh_TW": {
            "name": "繁體中文",
            "native_name": "繁體中文",
            "flag": "🇹🇼",
            "file": "zh_TW.json",
            "direction": "ltr",
            "date_format": "YYYY/MM/DD",
            "currency_symbol": "NT$",
            "decimal_separator": ".",
            "thousand_separator": ","
        },
        "zh_CN": {
            "name": "简体中文",
            "native_name": "简体中文",
            "flag": "🇨🇳",
            "file": "zh_CN.json",
            "direction": "ltr",
            "date_format": "YYYY年MM月DD日",
            "currency_symbol": "¥",
            "decimal_separator": ".",
            "thousand_separator": ","
        },
        "en_US": {
            "name": "English (US)",
            "native_name": "English",
            "flag": "🇺🇸",
            "file": "en_US.json",
            "direction": "ltr",
            "date_format": "MM/DD/YYYY",
            "currency_symbol": "$",
            "decimal_separator": ".",
            "thousand_separator": ","
        },
        "ja_JP": {
            "name": "日本語",
            "native_name": "日本語",
            "flag": "🇯🇵",
            "file": "ja_JP.json",
            "direction": "ltr",
            "date_format": "YYYY年MM月DD日",
            "currency_symbol": "¥",
            "decimal_separator": ".",
            "thousand_separator": ","
        }
    }
    
    DEFAULT_LANGUAGE = "zh_TW"
    
    def __init__(self):
        """初始化語言切換器

        載入語言資源並初始化語言狀態。
        """
        self.language_resources: Dict[str, Dict[str, Any]] = {}
        self.fallback_chain: Dict[str, List[str]] = {
            "zh_CN": ["zh_TW", "en_US"],
            "ja_JP": ["en_US", "zh_TW"],
            "zh_TW": ["en_US"],
            "en_US": ["zh_TW"]
        }
        self._load_all_language_resources()
        self._initialize_language_state()
        self._setup_language_detection()
        
    def _load_all_language_resources(self) -> None:
        """載入所有語言資源
        
        從語言資源文件載入所有支援語言的文字資源。
        
        Raises:
            FileNotFoundError: 當語言資源文件不存在時
            json.JSONDecodeError: 當語言資源文件格式錯誤時
        """
        localization_dir = os.path.dirname(os.path.abspath(__file__))
        
        for lang_code, lang_info in self.SUPPORTED_LANGUAGES.items():
            try:
                file_path = os.path.join(localization_dir, lang_info["file"])
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.language_resources[lang_code] = json.load(f)
                logging.info("語言資源載入成功: %s", lang_code)
            except FileNotFoundError:
                logging.error("語言資源文件未找到: %s", file_path)
                self.language_resources[lang_code] = {}
            except json.JSONDecodeError as e:
                logging.error("語言資源文件格式錯誤 %s: %s", file_path, e)
                self.language_resources[lang_code] = {}
            except Exception as e:
                logging.error("載入語言資源時發生錯誤 %s: %s", file_path, e)
                self.language_resources[lang_code] = {}
                
    def _initialize_language_state(self) -> None:
        """初始化語言狀態

        在 Streamlit session state 中初始化語言設定。
        """
        if "language" not in st.session_state:
            # 嘗試從用戶偏好或瀏覽器語言檢測
            detected_language = self._detect_user_language()
            st.session_state["language"] = detected_language
            logging.info("語言狀態初始化為: %s", detected_language)

        if "language_changed" not in st.session_state:
            st.session_state["language_changed"] = False

    def _setup_language_detection(self) -> None:
        """設置語言檢測"""
        if "browser_language_detected" not in st.session_state:
            st.session_state["browser_language_detected"] = False

    def _detect_user_language(self) -> str:
        """檢測用戶語言偏好

        Returns:
            str: 檢測到的語言代碼
        """
        # 1. 檢查用戶偏好設置
        if hasattr(st.session_state, 'user_preferences'):
            user_prefs = st.session_state.user_preferences
            if hasattr(user_prefs, 'language') and user_prefs.language in self.SUPPORTED_LANGUAGES:
                return user_prefs.language

        # 2. 檢查瀏覽器語言（模擬）
        # 在實際應用中，可以通過 JavaScript 獲取瀏覽器語言
        browser_lang = self._get_browser_language()
        if browser_lang in self.SUPPORTED_LANGUAGES:
            return browser_lang

        # 3. 返回默認語言
        return self.DEFAULT_LANGUAGE

    def _get_browser_language(self) -> str:
        """獲取瀏覽器語言（模擬）

        Returns:
            str: 瀏覽器語言代碼
        """
        # 這裡可以通過 JavaScript 組件獲取真實的瀏覽器語言
        # 目前返回默認值
        return self.DEFAULT_LANGUAGE
            
    def show_language_selector(self, 
                             key: str = "language_selector",
                             show_in_sidebar: bool = True) -> str:
        """顯示語言選擇器
        
        在 Streamlit 界面中顯示語言選擇組件。
        
        Args:
            key: Streamlit 組件的唯一鍵值
            show_in_sidebar: 是否在側邊欄顯示
            
        Returns:
            str: 選擇的語言代碼
        """
        # 準備選項
        options = []
        option_mapping = {}
        
        for lang_code, lang_info in self.SUPPORTED_LANGUAGES.items():
            display_text = f"{lang_info['flag']} {lang_info['name']}"
            options.append(display_text)
            option_mapping[display_text] = lang_code
            
        # 獲取當前選擇的索引
        current_lang = self.get_current_language()
        current_display = None
        for display, code in option_mapping.items():
            if code == current_lang:
                current_display = display
                break
                
        current_index = options.index(current_display) if current_display else 0
        
        # 顯示選擇器
        container = st.sidebar if show_in_sidebar else st
        
        with container:
            selected_display = st.selectbox(
                label=self.get_text("settings.language", "語言 / Language"),
                options=options,
                index=current_index,
                key=key
            )
            
        # 更新語言設定
        selected_lang = option_mapping[selected_display]
        if selected_lang != current_lang:
            self.set_language(selected_lang)
            st.rerun()
            
        return selected_lang
        
    def get_current_language(self) -> str:
        """獲取當前語言
        
        Returns:
            str: 當前語言代碼
        """
        return st.session_state.get("language", self.DEFAULT_LANGUAGE)
        
    def set_language(self, language_code: str) -> bool:
        """設定語言
        
        Args:
            language_code: 語言代碼
            
        Returns:
            bool: 設定是否成功
        """
        if language_code in self.SUPPORTED_LANGUAGES:
            st.session_state["language"] = language_code
            logging.info("語言設定為: %s", language_code)
            return True
        else:
            logging.warning("不支援的語言代碼: %s", language_code)
            return False
            
    def get_text(self, key: str, default: str = "", **kwargs) -> str:
        """獲取本地化文字 (增強版)

        根據當前語言設定獲取對應的本地化文字。
        支援巢狀鍵值、參數替換和回退機制。

        Args:
            key: 文字鍵值，支援點號分隔的巢狀鍵值
            default: 預設文字，當找不到對應文字時返回
            **kwargs: 用於字符串格式化的參數

        Returns:
            str: 本地化文字

        Example:
            >>> switcher.get_text("common.save")
            "儲存"
            >>> switcher.get_text("messages.welcome", name="John")
            "歡迎, John!"
        """
        current_lang = self.get_current_language()

        # 嘗試當前語言
        text = self._get_text_from_language(key, current_lang)

        # 如果找不到，嘗試回退語言鏈
        if text is None:
            fallback_languages = self.fallback_chain.get(current_lang, [])
            for fallback_lang in fallback_languages:
                text = self._get_text_from_language(key, fallback_lang)
                if text is not None:
                    logging.debug(f"使用回退語言 {fallback_lang} 獲取文字: {key}")
                    break

        # 如果仍然找不到，使用默認值或鍵值
        if text is None:
            text = default if default else key
            logging.warning(f"找不到本地化文字: {key}")

        # 參數替換
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError) as e:
                logging.warning(f"文字格式化失敗 {key}: {e}")

        return str(text)

    def _get_text_from_language(self, key: str, language: str) -> Optional[str]:
        """從指定語言獲取文字

        Args:
            key: 文字鍵值
            language: 語言代碼

        Returns:
            Optional[str]: 文字內容，如果找不到返回 None
        """
        resources = self.language_resources.get(language, {})
        keys = key.split('.')
        value = resources

        try:
            for k in keys:
                value = value[k]
            return str(value)
        except (KeyError, TypeError):
            return None
            
    def get_language_info(self, language_code: Optional[str] = None) -> Dict[str, str]:
        """獲取語言資訊
        
        Args:
            language_code: 語言代碼，如果為 None 則使用當前語言
            
        Returns:
            Dict[str, str]: 語言資訊字典
        """
        if language_code is None:
            language_code = self.get_current_language()
            
        return self.SUPPORTED_LANGUAGES.get(language_code, {})
        
    def is_rtl_language(self, language_code: Optional[str] = None) -> bool:
        """檢查是否為右到左語言
        
        Args:
            language_code: 語言代碼，如果為 None 則使用當前語言
            
        Returns:
            bool: 是否為右到左語言
        """
        # 目前支援的語言都是左到右，未來可擴展
        return False
        
    def get_date_format(self) -> str:
        """獲取當前語言的日期格式
        
        Returns:
            str: 日期格式字串
        """
        return self.get_text("formats.date.format", "YYYY/MM/DD")
        
    def get_number_format(self) -> Dict[str, str]:
        """獲取當前語言的數字格式

        Returns:
            Dict[str, str]: 數字格式設定
        """
        current_lang = self.get_current_language()
        lang_info = self.SUPPORTED_LANGUAGES.get(current_lang, {})

        return {
            "decimal_separator": lang_info.get("decimal_separator", "."),
            "thousand_separator": lang_info.get("thousand_separator", ",")
        }

    def format_number(self, number: float, decimals: int = 2) -> str:
        """格式化數字

        Args:
            number: 要格式化的數字
            decimals: 小數位數

        Returns:
            str: 格式化後的數字字符串
        """
        format_info = self.get_number_format()

        # 格式化數字
        formatted = f"{number:,.{decimals}f}"

        # 替換分隔符
        if format_info["thousand_separator"] != ",":
            formatted = formatted.replace(",", "TEMP")
            formatted = formatted.replace(".", format_info["decimal_separator"])
            formatted = formatted.replace("TEMP", format_info["thousand_separator"])
        elif format_info["decimal_separator"] != ".":
            formatted = formatted.replace(".", format_info["decimal_separator"])

        return formatted

    def format_currency(self, amount: float, currency: str = "USD") -> str:
        """格式化貨幣

        Args:
            amount: 金額
            currency: 貨幣代碼

        Returns:
            str: 格式化後的貨幣字符串
        """
        current_lang = self.get_current_language()
        lang_info = self.SUPPORTED_LANGUAGES.get(current_lang, {})

        # 獲取貨幣符號
        currency_symbol = lang_info.get("currency_symbol", "$")

        # 格式化金額
        formatted_amount = self.format_number(amount, 2)

        # 根據語言決定貨幣符號位置
        if current_lang in ["zh_TW", "zh_CN", "ja_JP"]:
            return f"{currency_symbol}{formatted_amount}"
        else:
            return f"{currency_symbol}{formatted_amount}"

    def format_date(self, date_obj, include_time: bool = False) -> str:
        """格式化日期

        Args:
            date_obj: 日期對象
            include_time: 是否包含時間

        Returns:
            str: 格式化後的日期字符串
        """
        current_lang = self.get_current_language()
        lang_info = self.SUPPORTED_LANGUAGES.get(current_lang, {})

        date_format = lang_info.get("date_format", "YYYY/MM/DD")

        if include_time:
            if current_lang in ["zh_TW", "zh_CN", "ja_JP"]:
                return date_obj.strftime("%Y年%m月%d日 %H:%M:%S")
            else:
                return date_obj.strftime("%m/%d/%Y %H:%M:%S")
        else:
            if current_lang in ["zh_TW", "zh_CN", "ja_JP"]:
                return date_obj.strftime("%Y年%m月%d日")
            else:
                return date_obj.strftime("%m/%d/%Y")

    def get_language_direction(self, language_code: Optional[str] = None) -> str:
        """獲取語言方向

        Args:
            language_code: 語言代碼

        Returns:
            str: 'ltr' 或 'rtl'
        """
        if language_code is None:
            language_code = self.get_current_language()

        lang_info = self.SUPPORTED_LANGUAGES.get(language_code, {})
        return lang_info.get("direction", "ltr")

    def get_available_languages(self) -> List[Dict[str, str]]:
        """獲取可用語言列表

        Returns:
            List[Dict[str, str]]: 語言信息列表
        """
        languages = []
        for code, info in self.SUPPORTED_LANGUAGES.items():
            languages.append({
                "code": code,
                "name": info["name"],
                "native_name": info["native_name"],
                "flag": info["flag"]
            })
        return languages

    def validate_language_resources(self) -> Dict[str, List[str]]:
        """驗證語言資源完整性

        Returns:
            Dict[str, List[str]]: 驗證結果，包含缺失的鍵值
        """
        validation_results = {}

        # 以默認語言為基準
        default_resources = self.language_resources.get(self.DEFAULT_LANGUAGE, {})
        default_keys = self._get_all_keys(default_resources)

        for lang_code, resources in self.language_resources.items():
            if lang_code == self.DEFAULT_LANGUAGE:
                continue

            lang_keys = self._get_all_keys(resources)
            missing_keys = default_keys - lang_keys

            if missing_keys:
                validation_results[lang_code] = list(missing_keys)

        return validation_results

    def _get_all_keys(self, data: Dict[str, Any], prefix: str = "") -> set:
        """遞歸獲取所有鍵值

        Args:
            data: 數據字典
            prefix: 鍵值前綴

        Returns:
            set: 所有鍵值的集合
        """
        keys = set()

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                keys.update(self._get_all_keys(value, full_key))
            else:
                keys.add(full_key)

        return keys


# 全域語言切換器實例
_language_switcher = None


def get_language_switcher() -> LanguageSwitcher:
    """獲取全域語言切換器實例
    
    Returns:
        LanguageSwitcher: 語言切換器實例
    """
    global _language_switcher
    if _language_switcher is None:
        _language_switcher = LanguageSwitcher()
    return _language_switcher


def get_text(key: str, default: str = "") -> str:
    """便捷函數：獲取本地化文字
    
    Args:
        key: 文字鍵值
        default: 預設文字
        
    Returns:
        str: 本地化文字
    """
    return get_language_switcher().get_text(key, default)


def show_language_selector(**kwargs) -> str:
    """便捷函數：顯示語言選擇器
    
    Args:
        **kwargs: 傳遞給 LanguageSwitcher.show_language_selector 的參數
        
    Returns:
        str: 選擇的語言代碼
    """
    return get_language_switcher().show_language_selector(**kwargs)
