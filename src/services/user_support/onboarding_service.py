"""
新手引導服務 (Onboarding Service)

此模組提供新手引導的核心服務功能，包括：
- 新用戶引導流程
- 學習進度追蹤
- 互動式教程
- 成就系統
- 個人化推薦

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

logger = logging.getLogger(__name__)


class OnboardingStage(Enum):
    """引導階段枚舉"""
    WELCOME = "welcome"
    PROFILE_SETUP = "profile_setup"
    BASIC_TUTORIAL = "basic_tutorial"
    FIRST_STRATEGY = "first_strategy"
    FIRST_BACKTEST = "first_backtest"
    RISK_EDUCATION = "risk_education"
    LIVE_TRADING_PREP = "live_trading_prep"
    COMPLETED = "completed"


class TutorialType(Enum):
    """教程類型枚舉"""
    INTERACTIVE = "interactive"
    VIDEO = "video"
    DOCUMENT = "document"
    QUIZ = "quiz"
    HANDS_ON = "hands_on"


class Achievement(Enum):
    """成就類型枚舉"""
    FIRST_LOGIN = "first_login"
    PROFILE_COMPLETE = "profile_complete"
    TUTORIAL_COMPLETE = "tutorial_complete"
    FIRST_STRATEGY = "first_strategy"
    FIRST_BACKTEST = "first_backtest"
    RISK_QUIZ_PASS = "risk_quiz_pass"
    WEEK_STREAK = "week_streak"
    MONTH_STREAK = "month_streak"


class UserProgress:
    """
    用戶進度類別
    
    Attributes:
        user_id: 用戶ID
        current_stage: 當前階段
        completed_stages: 已完成階段列表
        completed_tutorials: 已完成教程列表
        achievements: 獲得的成就列表
        progress_data: 進度資料
        started_at: 開始時間
        last_activity: 最後活動時間
    """

    def __init__(self, user_id: str):
        """
        初始化用戶進度
        
        Args:
            user_id: 用戶ID
        """
        self.user_id = user_id
        self.current_stage = OnboardingStage.WELCOME
        self.completed_stages: List[OnboardingStage] = []
        self.completed_tutorials: List[str] = []
        self.achievements: List[Achievement] = []
        self.progress_data: Dict[str, Any] = {}
        self.started_at = datetime.now()
        self.last_activity = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 用戶進度資訊字典
        """
        return {
            "user_id": self.user_id,
            "current_stage": self.current_stage.value,
            "completed_stages": [stage.value for stage in self.completed_stages],
            "completed_tutorials": self.completed_tutorials,
            "achievements": [achievement.value for achievement in self.achievements],
            "progress_data": self.progress_data,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "completion_percentage": self.get_completion_percentage()
        }

    def get_completion_percentage(self) -> float:
        """
        獲取完成百分比
        
        Returns:
            float: 完成百分比 (0-100)
        """
        total_stages = len(OnboardingStage) - 1  # 排除 COMPLETED
        completed_count = len(self.completed_stages)
        return (completed_count / total_stages) * 100 if total_stages > 0 else 0


class Tutorial:
    """
    教程類別
    
    Attributes:
        tutorial_id: 教程ID
        title: 標題
        description: 描述
        tutorial_type: 教程類型
        stage: 所屬階段
        content: 教程內容
        estimated_minutes: 預估時間(分鐘)
        prerequisites: 前置條件
        rewards: 完成獎勵
    """

    def __init__(
        self,
        tutorial_id: str,
        title: str,
        description: str,
        tutorial_type: TutorialType,
        stage: OnboardingStage,
        content: Dict[str, Any],
        estimated_minutes: int = 10,
        prerequisites: Optional[List[str]] = None,
        rewards: Optional[List[Achievement]] = None
    ):
        """
        初始化教程
        
        Args:
            tutorial_id: 教程ID
            title: 標題
            description: 描述
            tutorial_type: 教程類型
            stage: 所屬階段
            content: 教程內容
            estimated_minutes: 預估時間(分鐘)
            prerequisites: 前置條件
            rewards: 完成獎勵
        """
        self.tutorial_id = tutorial_id
        self.title = title
        self.description = description
        self.tutorial_type = tutorial_type
        self.stage = stage
        self.content = content
        self.estimated_minutes = estimated_minutes
        self.prerequisites = prerequisites or []
        self.rewards = rewards or []

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 教程資訊字典
        """
        return {
            "tutorial_id": self.tutorial_id,
            "title": self.title,
            "description": self.description,
            "tutorial_type": self.tutorial_type.value,
            "stage": self.stage.value,
            "content": self.content,
            "estimated_minutes": self.estimated_minutes,
            "prerequisites": self.prerequisites,
            "rewards": [reward.value for reward in self.rewards]
        }


class OnboardingServiceError(Exception):
    """新手引導服務錯誤"""
    pass


class OnboardingService:
    """
    新手引導服務
    
    提供新用戶引導功能，包括進度追蹤、教程管理、
    成就系統等。
    
    Attributes:
        _user_progress: 用戶進度記錄
        _tutorials: 教程列表
        _progress_callbacks: 進度回調函數列表
        _achievement_callbacks: 成就回調函數列表
    """

    def __init__(self):
        """
        初始化新手引導服務
        """
        self._user_progress: Dict[str, UserProgress] = {}
        self._tutorials: Dict[str, Tutorial] = {}
        self._progress_callbacks: List[Callable[[str, OnboardingStage], None]] = []
        self._achievement_callbacks: List[Callable[[str, Achievement], None]] = []
        
        # 初始化預設教程
        self._init_default_tutorials()
        
        logger.info("新手引導服務初始化成功")

    def start_onboarding(self, user_id: str) -> Dict[str, Any]:
        """
        開始新手引導
        
        Args:
            user_id: 用戶ID
            
        Returns:
            Dict[str, Any]: 引導開始資訊
        """
        try:
            if user_id in self._user_progress:
                logger.info("用戶 %s 已存在引導記錄", user_id)
                return self._user_progress[user_id].to_dict()
            
            # 創建新的用戶進度
            progress = UserProgress(user_id)
            self._user_progress[user_id] = progress
            
            # 獲得首次登入成就
            self._award_achievement(user_id, Achievement.FIRST_LOGIN)
            
            logger.info("用戶 %s 開始新手引導", user_id)
            return {
                "message": "歡迎使用 AI 交易系統！",
                "current_stage": progress.current_stage.value,
                "next_tutorials": self.get_available_tutorials(user_id),
                "progress": progress.to_dict()
            }
            
        except Exception as e:
            logger.error("開始新手引導失敗: %s", e)
            raise OnboardingServiceError("引導開始失敗") from e

    def get_user_progress(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取用戶進度
        
        Args:
            user_id: 用戶ID
            
        Returns:
            Optional[Dict[str, Any]]: 用戶進度資訊，不存在時返回 None
        """
        progress = self._user_progress.get(user_id)
        return progress.to_dict() if progress else None

    def complete_tutorial(self, user_id: str, tutorial_id: str) -> Dict[str, Any]:
        """
        完成教程
        
        Args:
            user_id: 用戶ID
            tutorial_id: 教程ID
            
        Returns:
            Dict[str, Any]: 完成結果
            
        Raises:
            OnboardingServiceError: 完成失敗時拋出
        """
        try:
            if user_id not in self._user_progress:
                raise OnboardingServiceError("用戶引導記錄不存在")
            
            if tutorial_id not in self._tutorials:
                raise OnboardingServiceError("教程不存在")
            
            progress = self._user_progress[user_id]
            tutorial = self._tutorials[tutorial_id]
            
            # 檢查前置條件
            if not self._check_prerequisites(user_id, tutorial.prerequisites):
                raise OnboardingServiceError("不滿足前置條件")
            
            # 標記教程完成
            if tutorial_id not in progress.completed_tutorials:
                progress.completed_tutorials.append(tutorial_id)
                progress.last_activity = datetime.now()
            
            # 獲得獎勵
            for reward in tutorial.rewards:
                self._award_achievement(user_id, reward)
            
            # 檢查階段完成
            stage_completed = self._check_stage_completion(user_id, tutorial.stage)
            if stage_completed:
                self._complete_stage(user_id, tutorial.stage)
            
            logger.info("用戶 %s 完成教程: %s", user_id, tutorial_id)
            return {
                "message": f"恭喜完成教程: {tutorial.title}",
                "rewards": [reward.value for reward in tutorial.rewards],
                "stage_completed": stage_completed,
                "progress": progress.to_dict()
            }
            
        except Exception as e:
            logger.error("完成教程失敗: %s", e)
            raise OnboardingServiceError("教程完成失敗") from e

    def get_available_tutorials(self, user_id: str) -> List[Dict[str, Any]]:
        """
        獲取可用教程列表
        
        Args:
            user_id: 用戶ID
            
        Returns:
            List[Dict[str, Any]]: 可用教程列表
        """
        if user_id not in self._user_progress:
            return []
        
        progress = self._user_progress[user_id]
        available_tutorials = []
        
        for tutorial in self._tutorials.values():
            # 檢查是否已完成
            if tutorial.tutorial_id in progress.completed_tutorials:
                continue
            
            # 檢查階段是否匹配
            if tutorial.stage != progress.current_stage:
                continue
            
            # 檢查前置條件
            if not self._check_prerequisites(user_id, tutorial.prerequisites):
                continue
            
            available_tutorials.append(tutorial.to_dict())
        
        return available_tutorials

    def get_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """
        獲取用戶成就
        
        Args:
            user_id: 用戶ID
            
        Returns:
            List[Dict[str, Any]]: 成就列表
        """
        if user_id not in self._user_progress:
            return []
        
        progress = self._user_progress[user_id]
        achievements = []
        
        for achievement in progress.achievements:
            achievements.append({
                "achievement": achievement.value,
                "name": self._get_achievement_name(achievement),
                "description": self._get_achievement_description(achievement),
                "earned_at": progress.last_activity.isoformat()  # 簡化實作
            })
        
        return achievements

    def get_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        獲取個人化推薦
        
        Args:
            user_id: 用戶ID
            
        Returns:
            List[Dict[str, Any]]: 推薦列表
        """
        if user_id not in self._user_progress:
            return []
        
        progress = self._user_progress[user_id]
        recommendations = []
        
        # 基於當前階段的推薦
        if progress.current_stage == OnboardingStage.WELCOME:
            recommendations.append({
                "type": "tutorial",
                "title": "完成個人資料設定",
                "description": "設定您的投資偏好和風險承受度",
                "priority": "high"
            })
        elif progress.current_stage == OnboardingStage.BASIC_TUTORIAL:
            recommendations.append({
                "type": "tutorial",
                "title": "學習基礎交易概念",
                "description": "了解股票、訂單類型和基本分析",
                "priority": "high"
            })
        elif progress.current_stage == OnboardingStage.FIRST_STRATEGY:
            recommendations.append({
                "type": "tutorial",
                "title": "創建您的第一個策略",
                "description": "使用預設模板創建簡單的交易策略",
                "priority": "high"
            })
        
        # 基於活動時間的推薦
        days_since_activity = (datetime.now() - progress.last_activity).days
        if days_since_activity > 3:
            recommendations.append({
                "type": "reminder",
                "title": "繼續您的學習之旅",
                "description": "您已經幾天沒有學習了，繼續完成引導吧！",
                "priority": "medium"
            })
        
        return recommendations

    def add_progress_callback(
        self, 
        callback: Callable[[str, OnboardingStage], None]
    ) -> None:
        """
        添加進度回調函數
        
        Args:
            callback: 回調函數，接收用戶ID和新階段
        """
        self._progress_callbacks.append(callback)

    def add_achievement_callback(
        self, 
        callback: Callable[[str, Achievement], None]
    ) -> None:
        """
        添加成就回調函數
        
        Args:
            callback: 回調函數，接收用戶ID和成就
        """
        self._achievement_callbacks.append(callback)

    def _init_default_tutorials(self) -> None:
        """
        初始化預設教程
        """
        tutorials = [
            Tutorial(
                tutorial_id="welcome_intro",
                title="歡迎來到 AI 交易系統",
                description="了解系統基本功能和界面",
                tutorial_type=TutorialType.INTERACTIVE,
                stage=OnboardingStage.WELCOME,
                content={"steps": ["介紹主界面", "導覽功能選單", "設定個人偏好"]},
                estimated_minutes=5
            ),
            Tutorial(
                tutorial_id="profile_setup",
                title="設定個人投資檔案",
                description="配置您的投資目標和風險偏好",
                tutorial_type=TutorialType.HANDS_ON,
                stage=OnboardingStage.PROFILE_SETUP,
                content={"form_fields": ["投資經驗", "風險承受度", "投資目標"]},
                estimated_minutes=10,
                rewards=[Achievement.PROFILE_COMPLETE]
            ),
            Tutorial(
                tutorial_id="trading_basics",
                title="交易基礎知識",
                description="學習股票交易的基本概念",
                tutorial_type=TutorialType.VIDEO,
                stage=OnboardingStage.BASIC_TUTORIAL,
                content={"video_url": "/tutorials/trading_basics.mp4"},
                estimated_minutes=15
            ),
            Tutorial(
                tutorial_id="risk_education",
                title="風險管理教育",
                description="了解投資風險和管理方法",
                tutorial_type=TutorialType.QUIZ,
                stage=OnboardingStage.RISK_EDUCATION,
                content={"questions": 10, "pass_score": 80},
                estimated_minutes=20,
                rewards=[Achievement.RISK_QUIZ_PASS]
            )
        ]
        
        for tutorial in tutorials:
            self._tutorials[tutorial.tutorial_id] = tutorial

    def _check_prerequisites(self, user_id: str, prerequisites: List[str]) -> bool:
        """
        檢查前置條件
        
        Args:
            user_id: 用戶ID
            prerequisites: 前置條件列表
            
        Returns:
            bool: 是否滿足前置條件
        """
        if not prerequisites:
            return True
        
        progress = self._user_progress.get(user_id)
        if not progress:
            return False
        
        return all(prereq in progress.completed_tutorials for prereq in prerequisites)

    def _check_stage_completion(self, user_id: str, stage: OnboardingStage) -> bool:
        """
        檢查階段是否完成
        
        Args:
            user_id: 用戶ID
            stage: 階段
            
        Returns:
            bool: 階段是否完成
        """
        progress = self._user_progress[user_id]
        
        # 獲取該階段的所有教程
        stage_tutorials = [
            tutorial.tutorial_id for tutorial in self._tutorials.values()
            if tutorial.stage == stage
        ]
        
        # 檢查是否都已完成
        return all(
            tutorial_id in progress.completed_tutorials 
            for tutorial_id in stage_tutorials
        )

    def _complete_stage(self, user_id: str, stage: OnboardingStage) -> None:
        """
        完成階段
        
        Args:
            user_id: 用戶ID
            stage: 階段
        """
        progress = self._user_progress[user_id]
        
        if stage not in progress.completed_stages:
            progress.completed_stages.append(stage)
            
            # 進入下一階段
            next_stage = self._get_next_stage(stage)
            if next_stage:
                progress.current_stage = next_stage
                
                # 觸發進度回調
                for callback in self._progress_callbacks:
                    try:
                        callback(user_id, next_stage)
                    except Exception as e:
                        logger.error("執行進度回調時發生錯誤: %s", e)

    def _get_next_stage(self, current_stage: OnboardingStage) -> Optional[OnboardingStage]:
        """
        獲取下一階段
        
        Args:
            current_stage: 當前階段
            
        Returns:
            Optional[OnboardingStage]: 下一階段，無下一階段時返回 None
        """
        stages = list(OnboardingStage)
        try:
            current_index = stages.index(current_stage)
            if current_index < len(stages) - 1:
                return stages[current_index + 1]
        except ValueError:
            pass
        return None

    def _award_achievement(self, user_id: str, achievement: Achievement) -> None:
        """
        獲得成就
        
        Args:
            user_id: 用戶ID
            achievement: 成就
        """
        progress = self._user_progress[user_id]
        
        if achievement not in progress.achievements:
            progress.achievements.append(achievement)
            
            # 觸發成就回調
            for callback in self._achievement_callbacks:
                try:
                    callback(user_id, achievement)
                except Exception as e:
                    logger.error("執行成就回調時發生錯誤: %s", e)
            
            logger.info("用戶 %s 獲得成就: %s", user_id, achievement.value)

    def _get_achievement_name(self, achievement: Achievement) -> str:
        """
        獲取成就名稱
        
        Args:
            achievement: 成就
            
        Returns:
            str: 成就名稱
        """
        names = {
            Achievement.FIRST_LOGIN: "初次登入",
            Achievement.PROFILE_COMPLETE: "檔案完成",
            Achievement.TUTORIAL_COMPLETE: "教程完成",
            Achievement.FIRST_STRATEGY: "首個策略",
            Achievement.FIRST_BACKTEST: "首次回測",
            Achievement.RISK_QUIZ_PASS: "風險測驗通過",
            Achievement.WEEK_STREAK: "一週連續",
            Achievement.MONTH_STREAK: "一月連續"
        }
        return names.get(achievement, achievement.value)

    def _get_achievement_description(self, achievement: Achievement) -> str:
        """
        獲取成就描述
        
        Args:
            achievement: 成就
            
        Returns:
            str: 成就描述
        """
        descriptions = {
            Achievement.FIRST_LOGIN: "歡迎加入 AI 交易系統",
            Achievement.PROFILE_COMPLETE: "完成個人投資檔案設定",
            Achievement.TUTORIAL_COMPLETE: "完成所有基礎教程",
            Achievement.FIRST_STRATEGY: "創建第一個交易策略",
            Achievement.FIRST_BACKTEST: "執行第一次策略回測",
            Achievement.RISK_QUIZ_PASS: "通過風險管理測驗",
            Achievement.WEEK_STREAK: "連續一週活躍學習",
            Achievement.MONTH_STREAK: "連續一月活躍學習"
        }
        return descriptions.get(achievement, "獲得特殊成就")
