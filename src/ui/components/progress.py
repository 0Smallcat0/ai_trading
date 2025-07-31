"""
進度條組件

此模組提供各種進度條和狀態顯示組件。
"""

import streamlit as st
import time
from typing import Optional, Dict, Any
from datetime import datetime


class ProgressTracker:
    """進度追蹤器"""

    def __init__(self, total_steps: int, title: str = "處理進度"):
        """
        初始化進度追蹤器

        Args:
            total_steps: 總步驟數
            title: 進度條標題
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.title = title
        self.start_time = datetime.now()

        # 建立 Streamlit 元件
        self.title_placeholder = st.empty()
        self.progress_bar = st.progress(0)
        self.status_placeholder = st.empty()
        self.time_placeholder = st.empty()

        self._update_display()

    def update(self, step: int, message: str = ""):
        """
        更新進度

        Args:
            step: 當前步驟
            message: 狀態訊息
        """
        self.current_step = min(step, self.total_steps)
        self.current_message = message
        self._update_display()

    def increment(self, message: str = ""):
        """
        增加一步

        Args:
            message: 狀態訊息
        """
        self.update(self.current_step + 1, message)

    def _update_display(self):
        """更新顯示"""
        progress = self.current_step / self.total_steps if self.total_steps > 0 else 0

        # 更新標題
        self.title_placeholder.markdown(f"### {self.title}")

        # 更新進度條
        self.progress_bar.progress(progress)

        # 更新狀態
        status_text = f"步驟 {self.current_step}/{self.total_steps}"
        if hasattr(self, "current_message") and self.current_message:
            status_text += f" - {self.current_message}"
        self.status_placeholder.text(status_text)

        # 更新時間資訊
        elapsed = datetime.now() - self.start_time
        if progress > 0:
            estimated_total = elapsed / progress
            remaining = estimated_total - elapsed
            time_text = f"已用時: {self._format_duration(elapsed)} | 預估剩餘: {self._format_duration(remaining)}"
        else:
            time_text = f"已用時: {self._format_duration(elapsed)}"

        self.time_placeholder.text(time_text)

    def _format_duration(self, duration):
        """格式化時間長度"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def complete(self, message: str = "完成"):
        """標記為完成"""
        self.update(self.total_steps, message)
        self.status_placeholder.success(f"✅ {message}")


def show_simple_progress(
    progress: float, message: str = "", show_percentage: bool = True
):
    """
    顯示簡單進度條

    Args:
        progress: 進度 (0-100)
        message: 狀態訊息
        show_percentage: 是否顯示百分比
    """
    # 確保進度在有效範圍內
    progress = max(0, min(100, progress))

    if message:
        st.text(message)

    # 顯示進度條
    st.progress(progress / 100)

    if show_percentage:
        st.text(f"進度: {progress:.1f}%")


def show_step_progress(
    current_step: int, total_steps: int, step_names: Optional[list] = None
):
    """
    顯示步驟式進度

    Args:
        current_step: 當前步驟 (從1開始)
        total_steps: 總步驟數
        step_names: 步驟名稱列表
    """
    st.markdown("### 處理步驟")

    # 建立步驟顯示
    for i in range(1, total_steps + 1):
        step_name = (
            step_names[i - 1] if step_names and i - 1 < len(step_names) else f"步驟 {i}"
        )

        if i < current_step:
            # 已完成的步驟
            st.markdown(f"✅ {step_name}")
        elif i == current_step:
            # 當前步驟
            st.markdown(f"🔄 {step_name} (進行中)")
        else:
            # 未開始的步驟
            st.markdown(f"⏳ {step_name}")


def show_task_status(task_info: Dict[str, Any]):
    """
    顯示任務狀態

    Args:
        task_info: 任務資訊字典
    """
    status = task_info.get("status", "unknown")
    progress = task_info.get("progress", 0)
    message = task_info.get("message", "")
    start_time = task_info.get("start_time")
    end_time = task_info.get("end_time")

    # 狀態圖示和顏色
    status_config = {
        "pending": {"icon": "⏳", "color": "#ffc107", "text": "等待中"},
        "running": {"icon": "🔄", "color": "#007bff", "text": "執行中"},
        "completed": {"icon": "✅", "color": "#28a745", "text": "已完成"},
        "error": {"icon": "❌", "color": "#dc3545", "text": "錯誤"},
        "cancelled": {"icon": "⏹️", "color": "#6c757d", "text": "已取消"},
    }

    config = status_config.get(
        status, {"icon": "❓", "color": "#6c757d", "text": "未知"}
    )

    # 顯示狀態卡片
    st.markdown(
        f"""
    <div style="
        border: 1px solid {config['color']};
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        background-color: {config['color']}15;
    ">
        <h4 style="margin: 0; color: {config['color']};">
            {config['icon']} 任務狀態: {config['text']}
        </h4>
        <p style="margin: 8px 0 0 0;">
            {message}
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 顯示進度條
    if status == "running":
        st.progress(progress / 100)
        st.text(f"進度: {progress:.1f}%")
    elif status == "completed":
        st.progress(1.0)
        st.text("進度: 100%")

    # 顯示時間資訊
    if start_time:
        st.text(f"開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if end_time:
            duration = end_time - start_time
            st.text(f"結束時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.text(f"執行時間: {duration}")
        elif status == "running":
            elapsed = datetime.now() - start_time
            st.text(f"已執行時間: {elapsed}")


def show_loading_spinner(message: str = "載入中..."):
    """
    顯示載入動畫

    Args:
        message: 載入訊息
    """
    with st.spinner(message):
        # 這個函數需要在 with 語句中使用
        # 例如: with show_loading_spinner("處理中..."): do_something()
        yield


def show_countdown(seconds: int, message: str = "倒數計時"):
    """
    顯示倒數計時

    Args:
        seconds: 倒數秒數
        message: 顯示訊息
    """
    countdown_placeholder = st.empty()

    for i in range(seconds, 0, -1):
        countdown_placeholder.text(f"{message}: {i} 秒")
        time.sleep(1)

    countdown_placeholder.text(f"{message}: 完成!")


class MultiTaskProgress:
    """多任務進度追蹤器"""

    def __init__(self, tasks: Dict[str, int]):
        """
        初始化多任務進度追蹤器

        Args:
            tasks: 任務字典 {任務名稱: 總步驟數}
        """
        self.tasks = tasks
        self.progress = {name: 0 for name in tasks.keys()}
        self.messages = {name: "" for name in tasks.keys()}

        # 建立顯示元件
        self.container = st.container()
        self.progress_bars = {}
        self.status_placeholders = {}

        with self.container:
            for task_name in tasks.keys():
                st.markdown(f"**{task_name}**")
                self.progress_bars[task_name] = st.progress(0)
                self.status_placeholders[task_name] = st.empty()

    def update_task(self, task_name: str, current_step: int, message: str = ""):
        """
        更新特定任務的進度

        Args:
            task_name: 任務名稱
            current_step: 當前步驟
            message: 狀態訊息
        """
        if task_name not in self.tasks:
            return

        total_steps = self.tasks[task_name]
        progress = min(current_step / total_steps, 1.0) if total_steps > 0 else 0

        self.progress[task_name] = progress
        self.messages[task_name] = message

        # 更新顯示
        self.progress_bars[task_name].progress(progress)
        status_text = f"步驟 {current_step}/{total_steps}"
        if message:
            status_text += f" - {message}"
        self.status_placeholders[task_name].text(status_text)

    def get_overall_progress(self) -> float:
        """獲取整體進度"""
        if not self.progress:
            return 0
        return sum(self.progress.values()) / len(self.progress)

    def is_all_completed(self) -> bool:
        """檢查是否所有任務都已完成"""
        return all(progress >= 1.0 for progress in self.progress.values())
