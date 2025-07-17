"""
用戶支援服務測試模組

測試新手引導、操作記錄和幫助文檔服務的功能。

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.services.user_support.onboarding_service import (
    OnboardingService,
    UserProgress,
    Tutorial,
    OnboardingStage,
    TutorialType,
    Achievement,
    OnboardingServiceError
)
from src.services.user_support.operation_log_service import (
    OperationLogService,
    OperationLog,
    OperationType,
    OperationResult,
    OperationLogError
)
from src.services.user_support.help_service import (
    HelpService,
    HelpDocument,
    FAQ,
    DocumentType,
    DocumentStatus,
    HelpServiceError
)


class TestOnboardingService:
    """測試新手引導服務"""

    @pytest.fixture
    def onboarding_service(self):
        """創建新手引導服務實例"""
        return OnboardingService()

    @pytest.fixture
    def sample_user_progress(self):
        """創建範例用戶進度"""
        return UserProgress("user123")

    @pytest.fixture
    def sample_tutorial(self):
        """創建範例教程"""
        return Tutorial(
            tutorial_id="test_tutorial",
            title="測試教程",
            description="這是一個測試教程",
            tutorial_type=TutorialType.INTERACTIVE,
            stage=OnboardingStage.WELCOME,
            content={"steps": ["步驟1", "步驟2"]}
        )

    def test_init_success(self, onboarding_service):
        """測試服務初始化成功"""
        assert onboarding_service is not None
        assert len(onboarding_service._tutorials) > 0  # 有預設教程
        assert onboarding_service._user_progress == {}

    def test_user_progress_creation(self, sample_user_progress):
        """測試用戶進度創建"""
        assert sample_user_progress.user_id == "user123"
        assert sample_user_progress.current_stage == OnboardingStage.WELCOME
        assert sample_user_progress.completed_stages == []
        assert sample_user_progress.achievements == []

    def test_user_progress_to_dict(self, sample_user_progress):
        """測試用戶進度轉換為字典"""
        progress_dict = sample_user_progress.to_dict()
        
        assert progress_dict["user_id"] == "user123"
        assert progress_dict["current_stage"] == "welcome"
        assert progress_dict["completed_stages"] == []
        assert "completion_percentage" in progress_dict

    def test_user_progress_completion_percentage(self, sample_user_progress):
        """測試用戶進度完成百分比計算"""
        # 初始狀態
        assert sample_user_progress.get_completion_percentage() == 0.0
        
        # 完成一個階段
        sample_user_progress.completed_stages.append(OnboardingStage.WELCOME)
        percentage = sample_user_progress.get_completion_percentage()
        assert percentage > 0.0

    def test_tutorial_creation(self, sample_tutorial):
        """測試教程創建"""
        assert sample_tutorial.tutorial_id == "test_tutorial"
        assert sample_tutorial.title == "測試教程"
        assert sample_tutorial.tutorial_type == TutorialType.INTERACTIVE
        assert sample_tutorial.stage == OnboardingStage.WELCOME

    def test_tutorial_to_dict(self, sample_tutorial):
        """測試教程轉換為字典"""
        tutorial_dict = sample_tutorial.to_dict()
        
        assert tutorial_dict["tutorial_id"] == "test_tutorial"
        assert tutorial_dict["title"] == "測試教程"
        assert tutorial_dict["tutorial_type"] == "interactive"
        assert tutorial_dict["stage"] == "welcome"

    def test_start_onboarding_new_user(self, onboarding_service):
        """測試新用戶開始引導"""
        result = onboarding_service.start_onboarding("user123")
        
        assert "user123" in onboarding_service._user_progress
        assert result["current_stage"] == "welcome"
        assert "next_tutorials" in result
        
        # 檢查是否獲得首次登入成就
        progress = onboarding_service._user_progress["user123"]
        assert Achievement.FIRST_LOGIN in progress.achievements

    def test_start_onboarding_existing_user(self, onboarding_service):
        """測試現有用戶開始引導"""
        # 先創建用戶進度
        progress = UserProgress("user123")
        onboarding_service._user_progress["user123"] = progress
        
        result = onboarding_service.start_onboarding("user123")
        
        assert result["current_stage"] == "welcome"

    def test_get_user_progress(self, onboarding_service, sample_user_progress):
        """測試獲取用戶進度"""
        onboarding_service._user_progress["user123"] = sample_user_progress
        
        progress = onboarding_service.get_user_progress("user123")
        
        assert progress is not None
        assert progress["user_id"] == "user123"

    def test_get_nonexistent_user_progress(self, onboarding_service):
        """測試獲取不存在用戶的進度"""
        progress = onboarding_service.get_user_progress("nonexistent")
        
        assert progress is None

    def test_complete_tutorial(self, onboarding_service):
        """測試完成教程"""
        # 先開始引導
        onboarding_service.start_onboarding("user123")
        
        # 獲取可用教程
        tutorials = onboarding_service.get_available_tutorials("user123")
        assert len(tutorials) > 0
        
        tutorial_id = tutorials[0]["tutorial_id"]
        
        result = onboarding_service.complete_tutorial("user123", tutorial_id)
        
        assert "message" in result
        assert "progress" in result
        
        # 檢查教程是否標記為完成
        progress = onboarding_service._user_progress["user123"]
        assert tutorial_id in progress.completed_tutorials

    def test_complete_tutorial_nonexistent_user(self, onboarding_service):
        """測試不存在用戶完成教程"""
        with pytest.raises(OnboardingServiceError):
            onboarding_service.complete_tutorial("nonexistent", "tutorial_id")

    def test_complete_tutorial_nonexistent_tutorial(self, onboarding_service):
        """測試完成不存在的教程"""
        onboarding_service.start_onboarding("user123")
        
        with pytest.raises(OnboardingServiceError):
            onboarding_service.complete_tutorial("user123", "nonexistent_tutorial")

    def test_get_available_tutorials(self, onboarding_service):
        """測試獲取可用教程"""
        onboarding_service.start_onboarding("user123")
        
        tutorials = onboarding_service.get_available_tutorials("user123")
        
        assert isinstance(tutorials, list)
        # 應該有 WELCOME 階段的教程
        welcome_tutorials = [t for t in tutorials if t["stage"] == "welcome"]
        assert len(welcome_tutorials) > 0

    def test_get_achievements(self, onboarding_service):
        """測試獲取用戶成就"""
        onboarding_service.start_onboarding("user123")
        
        achievements = onboarding_service.get_achievements("user123")
        
        assert isinstance(achievements, list)
        assert len(achievements) > 0  # 應該有首次登入成就

    def test_get_recommendations(self, onboarding_service):
        """測試獲取個人化推薦"""
        onboarding_service.start_onboarding("user123")
        
        recommendations = onboarding_service.get_recommendations("user123")
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0


class TestOperationLogService:
    """測試操作記錄服務"""

    @pytest.fixture
    def log_service(self):
        """創建操作記錄服務實例"""
        return OperationLogService()

    @pytest.fixture
    def sample_operation_log(self):
        """創建範例操作記錄"""
        return OperationLog(
            user_id="user123",
            operation_type=OperationType.LOGIN,
            operation_name="用戶登入",
            result=OperationResult.SUCCESS,
            ip_address="192.168.1.1"
        )

    def test_init_success(self, log_service):
        """測試服務初始化成功"""
        assert log_service is not None
        assert log_service._operation_logs == []
        assert log_service._max_logs == 10000
        assert log_service._retention_days == 90

    def test_operation_log_creation(self, sample_operation_log):
        """測試操作記錄創建"""
        assert sample_operation_log.user_id == "user123"
        assert sample_operation_log.operation_type == OperationType.LOGIN
        assert sample_operation_log.operation_name == "用戶登入"
        assert sample_operation_log.result == OperationResult.SUCCESS
        assert sample_operation_log.log_id is not None

    def test_operation_log_to_dict(self, sample_operation_log):
        """測試操作記錄轉換為字典"""
        log_dict = sample_operation_log.to_dict()
        
        assert log_dict["user_id"] == "user123"
        assert log_dict["operation_type"] == "login"
        assert log_dict["operation_name"] == "用戶登入"
        assert log_dict["result"] == "success"
        assert "timestamp" in log_dict

    def test_log_operation(self, log_service):
        """測試記錄操作"""
        log_id = log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.LOGIN,
            operation_name="用戶登入",
            result=OperationResult.SUCCESS,
            ip_address="192.168.1.1"
        )
        
        assert log_id is not None
        assert len(log_service._operation_logs) == 1

    def test_get_user_operations(self, log_service):
        """測試獲取用戶操作記錄"""
        # 記錄一些操作
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.LOGIN,
            operation_name="用戶登入"
        )
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.VIEW_PAGE,
            operation_name="查看頁面"
        )
        
        operations = log_service.get_user_operations("user123")
        
        assert len(operations) == 2
        assert operations[0]["user_id"] == "user123"

    def test_get_user_operations_with_filters(self, log_service):
        """測試使用篩選條件獲取用戶操作記錄"""
        # 記錄不同類型的操作
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.LOGIN,
            operation_name="用戶登入"
        )
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.VIEW_PAGE,
            operation_name="查看頁面"
        )
        
        # 測試按操作類型篩選
        login_ops = log_service.get_user_operations(
            "user123",
            operation_type=OperationType.LOGIN
        )
        assert len(login_ops) == 1
        assert login_ops[0]["operation_type"] == "login"

    def test_get_operation_statistics(self, log_service):
        """測試獲取操作統計"""
        # 記錄一些操作
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.LOGIN,
            operation_name="用戶登入",
            result=OperationResult.SUCCESS
        )
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.VIEW_PAGE,
            operation_name="查看頁面",
            result=OperationResult.SUCCESS
        )
        
        stats = log_service.get_operation_statistics("user123")
        
        assert stats["total_operations"] == 2
        assert stats["success_rate"] == 100.0
        assert "by_operation_type" in stats
        assert "by_result" in stats

    def test_detect_anomalies(self, log_service):
        """測試檢測異常操作"""
        # 記錄大量操作以觸發高頻警報
        for i in range(150):
            log_service.log_operation(
                user_id="user123",
                operation_type=OperationType.VIEW_PAGE,
                operation_name=f"查看頁面 {i}"
            )
        
        anomalies = log_service.detect_anomalies("user123")
        
        # 應該檢測到高頻操作
        high_freq_anomalies = [a for a in anomalies if a["type"] == "high_frequency"]
        assert len(high_freq_anomalies) > 0

    def test_detect_consecutive_failures(self, log_service):
        """測試檢測連續失敗"""
        # 記錄連續失敗操作
        for i in range(6):
            log_service.log_operation(
                user_id="user123",
                operation_type=OperationType.PLACE_ORDER,
                operation_name=f"下單 {i}",
                result=OperationResult.FAILED
            )
        
        anomalies = log_service.detect_anomalies("user123")
        
        # 應該檢測到連續失敗
        failure_anomalies = [a for a in anomalies if a["type"] == "consecutive_failures"]
        assert len(failure_anomalies) > 0

    def test_export_logs_json(self, log_service):
        """測試匯出 JSON 格式記錄"""
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.LOGIN,
            operation_name="用戶登入"
        )
        
        exported_data = log_service.export_logs(user_id="user123", format_type="json")
        
        assert exported_data is not None
        assert "user123" in exported_data

    def test_export_logs_csv(self, log_service):
        """測試匯出 CSV 格式記錄"""
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.LOGIN,
            operation_name="用戶登入"
        )
        
        exported_data = log_service.export_logs(user_id="user123", format_type="csv")
        
        assert exported_data is not None
        assert "user123" in exported_data

    def test_get_recent_errors(self, log_service):
        """測試獲取最近錯誤記錄"""
        # 記錄一些成功和失敗操作
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.LOGIN,
            operation_name="用戶登入",
            result=OperationResult.SUCCESS
        )
        log_service.log_operation(
            user_id="user123",
            operation_type=OperationType.PLACE_ORDER,
            operation_name="下單",
            result=OperationResult.FAILED,
            error_message="餘額不足"
        )
        
        errors = log_service.get_recent_errors("user123")
        
        assert len(errors) == 1
        assert errors[0]["result"] == "failed"


class TestHelpService:
    """測試幫助文檔服務"""

    @pytest.fixture
    def help_service(self):
        """創建幫助文檔服務實例"""
        return HelpService()

    @pytest.fixture
    def sample_document(self):
        """創建範例幫助文檔"""
        return HelpDocument(
            doc_id="test_doc",
            title="測試文檔",
            content="這是一個測試文檔的內容",
            doc_type=DocumentType.USER_GUIDE,
            category="測試分類",
            tags=["測試", "文檔"]
        )

    @pytest.fixture
    def sample_faq(self):
        """創建範例FAQ"""
        return FAQ(
            faq_id="test_faq",
            question="這是測試問題嗎？",
            answer="是的，這是一個測試問題。",
            category="測試分類",
            tags=["測試", "FAQ"]
        )

    def test_init_success(self, help_service):
        """測試服務初始化成功"""
        assert help_service is not None
        assert len(help_service._documents) > 0  # 有預設文檔
        assert len(help_service._faqs) > 0  # 有預設FAQ

    def test_help_document_creation(self, sample_document):
        """測試幫助文檔創建"""
        assert sample_document.doc_id == "test_doc"
        assert sample_document.title == "測試文檔"
        assert sample_document.doc_type == DocumentType.USER_GUIDE
        assert sample_document.status == DocumentStatus.PUBLISHED

    def test_help_document_to_dict(self, sample_document):
        """測試幫助文檔轉換為字典"""
        doc_dict = sample_document.to_dict()
        
        assert doc_dict["doc_id"] == "test_doc"
        assert doc_dict["title"] == "測試文檔"
        assert doc_dict["doc_type"] == "user_guide"
        assert doc_dict["status"] == "published"

    def test_help_document_update_content(self, sample_document):
        """測試更新文檔內容"""
        original_version = sample_document.version
        
        sample_document.update_content("新的內容", "author2")
        
        assert sample_document.content == "新的內容"
        assert sample_document.author == "author2"
        assert sample_document.version != original_version

    def test_faq_creation(self, sample_faq):
        """測試FAQ創建"""
        assert sample_faq.faq_id == "test_faq"
        assert sample_faq.question == "這是測試問題嗎？"
        assert sample_faq.answer == "是的，這是一個測試問題。"
        assert sample_faq.category == "測試分類"

    def test_faq_to_dict(self, sample_faq):
        """測試FAQ轉換為字典"""
        faq_dict = sample_faq.to_dict()
        
        assert faq_dict["faq_id"] == "test_faq"
        assert faq_dict["question"] == "這是測試問題嗎？"
        assert faq_dict["answer"] == "是的，這是一個測試問題。"

    def test_add_document(self, help_service, sample_document):
        """測試添加文檔"""
        initial_count = len(help_service._documents)
        
        help_service.add_document(sample_document)
        
        assert len(help_service._documents) == initial_count + 1
        assert "test_doc" in help_service._documents

    def test_get_document(self, help_service, sample_document):
        """測試獲取文檔"""
        help_service.add_document(sample_document)
        
        doc = help_service.get_document("test_doc", "user123")
        
        assert doc is not None
        assert doc["doc_id"] == "test_doc"
        assert sample_document.view_count == 1

    def test_get_nonexistent_document(self, help_service):
        """測試獲取不存在的文檔"""
        doc = help_service.get_document("nonexistent")
        
        assert doc is None

    def test_search_documents(self, help_service, sample_document):
        """測試搜尋文檔"""
        help_service.add_document(sample_document)
        
        results = help_service.search_documents("測試")
        
        assert len(results) > 0
        # 應該包含我們添加的文檔
        test_docs = [r for r in results if r["doc_id"] == "test_doc"]
        assert len(test_docs) > 0

    def test_search_documents_with_filters(self, help_service, sample_document):
        """測試使用篩選條件搜尋文檔"""
        help_service.add_document(sample_document)
        
        # 測試按文檔類型篩選
        results = help_service.search_documents(
            "測試",
            doc_type=DocumentType.USER_GUIDE
        )
        assert len(results) > 0
        
        # 測試按分類篩選
        results = help_service.search_documents(
            "測試",
            category="測試分類"
        )
        assert len(results) > 0

    def test_add_faq(self, help_service, sample_faq):
        """測試添加FAQ"""
        initial_count = len(help_service._faqs)
        
        help_service.add_faq(sample_faq)
        
        assert len(help_service._faqs) == initial_count + 1
        assert "test_faq" in help_service._faqs

    def test_get_faq(self, help_service, sample_faq):
        """測試獲取FAQ"""
        help_service.add_faq(sample_faq)
        
        faq = help_service.get_faq("test_faq", "user123")
        
        assert faq is not None
        assert faq["faq_id"] == "test_faq"
        assert sample_faq.view_count == 1

    def test_search_faqs(self, help_service, sample_faq):
        """測試搜尋FAQ"""
        help_service.add_faq(sample_faq)
        
        results = help_service.search_faqs("測試")
        
        assert len(results) > 0
        # 應該包含我們添加的FAQ
        test_faqs = [r for r in results if r["faq_id"] == "test_faq"]
        assert len(test_faqs) > 0

    def test_get_popular_content(self, help_service, sample_document, sample_faq):
        """測試獲取熱門內容"""
        # 添加內容並增加查看次數
        help_service.add_document(sample_document)
        help_service.add_faq(sample_faq)
        
        sample_document.view_count = 10
        sample_faq.view_count = 5
        
        popular = help_service.get_popular_content()
        
        assert len(popular) > 0

    def test_get_categories(self, help_service):
        """測試獲取分類統計"""
        categories = help_service.get_categories()
        
        assert isinstance(categories, dict)
        assert len(categories) > 0

    def test_mark_helpful(self, help_service, sample_document, sample_faq):
        """測試標記內容為有用"""
        help_service.add_document(sample_document)
        help_service.add_faq(sample_faq)
        
        # 測試標記文檔為有用
        result = help_service.mark_helpful("test_doc", "document")
        assert result is True
        assert sample_document.helpful_count == 1
        
        # 測試標記FAQ為有用
        result = help_service.mark_helpful("test_faq", "faq")
        assert result is True
        assert sample_faq.helpful_count == 1

    def test_get_user_recommendations(self, help_service):
        """測試獲取用戶個人化推薦"""
        recommendations = help_service.get_user_recommendations("user123")
        
        assert isinstance(recommendations, list)
        # 新用戶應該獲得熱門內容推薦
        assert len(recommendations) > 0
