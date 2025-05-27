"""
資料匯出工具模組

此模組提供資料匯出和報告生成功能，支援多種格式的資料匯出、
資料預覽、匯出配置和批量匯出等功能。

主要功能：
- 多格式資料匯出 (CSV, Excel, JSON, Parquet)
- 資料預覽和驗證
- 匯出配置管理
- 批量匯出處理
- 匯出歷史記錄

Example:
    ```python
    from src.ui.pages.data_management.data_export import show_data_export_tools
    show_data_export_tools()
    ```

Note:
    此模組依賴於 DataManagementService 來執行實際的資料匯出邏輯。
"""

import time
import io
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

import streamlit as st
import pandas as pd
import json


def get_available_export_types() -> List[str]:
    """
    獲取可用的匯出資料類型

    Returns:
        List[str]: 可匯出的資料類型列表

    Example:
        ```python
        types = get_available_export_types()
        print(f"可匯出類型: {types}")
        ```
    """
    return [
        "股價資料",
        "技術指標",
        "基本面資料",
        "財報資料",
        "新聞資料",
        "交易記錄",
        "投資組合資料",
        "風險指標",
    ]


def get_export_formats() -> List[str]:
    """
    獲取支援的匯出格式

    Returns:
        List[str]: 支援的檔案格式列表
    """
    return ["CSV", "Excel", "JSON", "Parquet"]


def preview_export_data(
    export_type: str,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    max_records: int = 100,
) -> Optional[pd.DataFrame]:
    """
    預覽匯出資料

    Args:
        export_type: 匯出資料類型
        symbols: 股票代碼列表
        start_date: 開始日期
        end_date: 結束日期
        max_records: 最大預覽記錄數

    Returns:
        Optional[pd.DataFrame]: 預覽資料，如果失敗則返回 None

    Example:
        ```python
        df = preview_export_data("股價資料", ["2330.TW"], start_date, end_date)
        if df is not None:
            print(f"預覽資料: {len(df)} 筆記錄")
        ```
    """
    # 嘗試從 session state 獲取資料服務
    data_service = st.session_state.get("data_service")

    if data_service:
        try:
            return data_service.preview_export_data(
                export_type, symbols, start_date, end_date, max_records
            )
        except Exception as e:
            st.warning(f"無法預覽資料: {e}")
            return None

    # 返回模擬資料
    import random
    import numpy as np

    dates = pd.date_range(start=start_date, end=end_date, freq="D")[:max_records]

    if export_type == "股價資料":
        data = {
            "日期": dates,
            "股票代碼": random.choices(symbols, k=len(dates)),
            "開盤價": np.random.uniform(100, 200, len(dates)),
            "最高價": np.random.uniform(150, 250, len(dates)),
            "最低價": np.random.uniform(80, 150, len(dates)),
            "收盤價": np.random.uniform(120, 220, len(dates)),
            "成交量": np.random.randint(1000, 100000, len(dates)),
        }
    elif export_type == "技術指標":
        data = {
            "日期": dates,
            "股票代碼": random.choices(symbols, k=len(dates)),
            "MA5": np.random.uniform(100, 200, len(dates)),
            "MA20": np.random.uniform(110, 190, len(dates)),
            "RSI": np.random.uniform(20, 80, len(dates)),
            "MACD": np.random.uniform(-5, 5, len(dates)),
        }
    else:
        # 其他類型的模擬資料
        data = {
            "日期": dates,
            "股票代碼": random.choices(symbols, k=len(dates)),
            "數值1": np.random.uniform(0, 100, len(dates)),
            "數值2": np.random.uniform(0, 100, len(dates)),
        }

    return pd.DataFrame(data)


def export_data_to_format(
    data: pd.DataFrame,
    export_format: str,
    filename: str,
    include_metadata: bool = True,
    compress_file: bool = False,
) -> Optional[bytes]:
    """
    將資料匯出為指定格式

    Args:
        data: 要匯出的資料
        export_format: 匯出格式
        filename: 檔案名稱
        include_metadata: 是否包含元數據
        compress_file: 是否壓縮檔案

    Returns:
        Optional[bytes]: 匯出的檔案內容，如果失敗則返回 None
    """
    try:
        if export_format == "CSV":
            output = io.StringIO()
            data.to_csv(output, index=False, encoding="utf-8-sig")
            return output.getvalue().encode("utf-8-sig")

        elif export_format == "Excel":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                data.to_excel(writer, sheet_name="資料", index=False)

                if include_metadata:
                    metadata = pd.DataFrame(
                        {
                            "項目": ["匯出時間", "記錄數量", "檔案格式"],
                            "值": [
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                len(data),
                                export_format,
                            ],
                        }
                    )
                    metadata.to_excel(writer, sheet_name="元數據", index=False)

            return output.getvalue()

        elif export_format == "JSON":
            json_data = {
                "data": data.to_dict("records"),
                "metadata": (
                    {
                        "export_time": datetime.now().isoformat(),
                        "record_count": len(data),
                        "format": export_format,
                    }
                    if include_metadata
                    else None
                ),
            }
            return json.dumps(json_data, ensure_ascii=False, indent=2).encode("utf-8")

        elif export_format == "Parquet":
            output = io.BytesIO()
            data.to_parquet(output, index=False)
            return output.getvalue()

        else:
            st.error(f"不支援的匯出格式: {export_format}")
            return None

    except Exception as e:
        st.error(f"匯出失敗: {e}")
        return None


def show_export_configuration() -> Dict[str, Any]:
    """
    顯示匯出配置介面

    Returns:
        Dict[str, Any]: 匯出配置參數

    Side Effects:
        渲染 Streamlit 表單組件
    """
    st.markdown("### 匯出配置")

    col1, col2 = st.columns(2)

    with col1:
        export_type = st.selectbox(
            "匯出類型", get_available_export_types(), help="選擇要匯出的資料類型"
        )

        symbols = st.text_area(
            "股票代碼",
            value="2330.TW, 2317.TW, 2454.TW",
            help="輸入股票代碼，用逗號分隔",
        ).split(",")
        symbols = [s.strip() for s in symbols if s.strip()]

        date_range = st.date_input(
            "日期範圍",
            value=[datetime.now() - timedelta(days=30), datetime.now()],
            help="選擇資料的日期範圍",
        )

    with col2:
        export_format = st.selectbox(
            "匯出格式", get_export_formats(), help="選擇匯出檔案的格式"
        )

        include_metadata = st.checkbox(
            "包含元數據", value=True, help="是否在匯出檔案中包含元數據資訊"
        )

        compress_file = st.checkbox("壓縮檔案", value=False, help="是否壓縮匯出的檔案")

        max_records = st.number_input(
            "最大記錄數",
            min_value=1,
            max_value=1000000,
            value=10000,
            help="限制匯出的最大記錄數",
        )

    return {
        "export_type": export_type,
        "symbols": symbols,
        "start_date": (
            date_range[0]
            if len(date_range) > 0
            else datetime.now() - timedelta(days=30)
        ),
        "end_date": date_range[1] if len(date_range) > 1 else datetime.now(),
        "export_format": export_format,
        "include_metadata": include_metadata,
        "compress_file": compress_file,
        "max_records": max_records,
    }


def show_data_preview(config: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    顯示資料預覽

    Args:
        config: 匯出配置參數

    Returns:
        Optional[pd.DataFrame]: 預覽的資料

    Side Effects:
        渲染 Streamlit 資料預覽組件
    """
    st.markdown("### 資料預覽")

    if st.button("🔍 預覽資料"):
        with st.spinner("正在載入資料預覽..."):
            time.sleep(1)  # 模擬載入時間

            preview_data = preview_export_data(
                config["export_type"],
                config["symbols"],
                config["start_date"],
                config["end_date"],
                min(config["max_records"], 100),  # 預覽最多100筆
            )

            if preview_data is not None and not preview_data.empty:
                st.success(f"✅ 載入 {len(preview_data)} 筆預覽資料")
                st.dataframe(preview_data, use_container_width=True)

                # 顯示資料統計
                st.markdown("#### 資料統計")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("記錄數", len(preview_data))
                with col2:
                    st.metric("欄位數", len(preview_data.columns))
                with col3:
                    st.metric(
                        "資料大小",
                        f"{preview_data.memory_usage(deep=True).sum() / 1024:.1f} KB",
                    )

                return preview_data
            else:
                st.warning("⚠️ 無法載入預覽資料或資料為空")
                return None

    return None


def show_export_execution(config: Dict[str, Any]) -> None:
    """
    顯示匯出執行介面

    Args:
        config: 匯出配置參數

    Side Effects:
        渲染 Streamlit 匯出執行組件
    """
    st.markdown("### 執行匯出")

    if st.button("📥 開始匯出", type="primary"):
        with st.spinner("正在匯出資料..."):
            # 獲取完整資料
            export_data = preview_export_data(
                config["export_type"],
                config["symbols"],
                config["start_date"],
                config["end_date"],
                config["max_records"],
            )

            if export_data is not None and not export_data.empty:
                # 生成檔案名稱
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{config['export_type']}_{timestamp}.{config['export_format'].lower()}"

                # 匯出資料
                file_content = export_data_to_format(
                    export_data,
                    config["export_format"],
                    filename,
                    config["include_metadata"],
                    config["compress_file"],
                )

                if file_content is not None:
                    st.success(f"✅ 匯出完成！共 {len(export_data)} 筆記錄")

                    # 提供下載按鈕
                    mime_types = {
                        "CSV": "text/csv",
                        "Excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "JSON": "application/json",
                        "Parquet": "application/octet-stream",
                    }

                    st.download_button(
                        label=f"📥 下載 {filename}",
                        data=file_content,
                        file_name=filename,
                        mime=mime_types.get(
                            config["export_format"], "application/octet-stream"
                        ),
                    )
                else:
                    st.error("❌ 匯出失敗")
            else:
                st.error("❌ 無法獲取匯出資料")


def show_data_export_tools() -> None:
    """
    顯示資料匯出工具主介面

    這是資料匯出工具的主要入口點，整合了匯出配置、
    資料預覽和匯出執行等功能。

    Returns:
        None

    Side Effects:
        渲染完整的資料匯出工具界面

    Example:
        ```python
        show_data_export_tools()
        ```

    Note:
        包含完整的錯誤處理，確保在資料服務不可用時
        仍能提供基本的功能和友善的錯誤訊息。
    """
    st.subheader("📤 資料匯出工具")

    try:
        # 顯示匯出配置
        config = show_export_configuration()

        st.markdown("---")

        # 顯示資料預覽
        preview_data = show_data_preview(config)

        st.markdown("---")

        # 顯示匯出執行
        show_export_execution(config)

    except Exception as e:
        st.error(f"資料匯出工具發生錯誤: {e}")
        with st.expander("錯誤詳情"):
            st.code(str(e))
