"""
幫助文檔服務 (Help Service)

此模組提供幫助文檔的核心服務功能，包括：
- 幫助文檔管理
- 常見問題解答
- 搜尋功能
- 文檔版本控制
- 使用統計分析

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import logging
import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """文檔類型枚舉"""
    USER_GUIDE = "user_guide"
    API_REFERENCE = "api_reference"
    TUTORIAL = "tutorial"
    FAQ = "faq"
    TROUBLESHOOTING = "troubleshooting"
    RELEASE_NOTES = "release_notes"
    QUICK_START = "quick_start"


class DocumentStatus(Enum):
    """文檔狀態枚舉"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    UNDER_REVIEW = "under_review"


class HelpDocument:
    """
    幫助文檔類別
    
    Attributes:
        doc_id: 文檔唯一識別碼
        title: 標題
        content: 內容
        doc_type: 文檔類型
        status: 文檔狀態
        tags: 標籤列表
        category: 分類
        author: 作者
        version: 版本
        created_at: 創建時間
        updated_at: 更新時間
        view_count: 查看次數
        helpful_count: 有用評分次數
        metadata: 額外資訊
    """

    def __init__(
        self,
        doc_id: str,
        title: str,
        content: str,
        doc_type: DocumentType,
        category: str,
        author: str = "system",
        tags: Optional[List[str]] = None,
        status: DocumentStatus = DocumentStatus.PUBLISHED,
        **metadata
    ):
        """
        初始化幫助文檔
        
        Args:
            doc_id: 文檔ID
            title: 標題
            content: 內容
            doc_type: 文檔類型
            category: 分類
            author: 作者
            tags: 標籤列表
            status: 文檔狀態
            **metadata: 額外資訊
        """
        self.doc_id = doc_id
        self.title = title
        self.content = content
        self.doc_type = doc_type
        self.status = status
        self.tags = tags or []
        self.category = category
        self.author = author
        self.version = "1.0"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.view_count = 0
        self.helpful_count = 0
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 文檔資訊字典
        """
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "doc_type": self.doc_type.value,
            "status": self.status.value,
            "tags": self.tags,
            "category": self.category,
            "author": self.author,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "view_count": self.view_count,
            "helpful_count": self.helpful_count,
            "metadata": self.metadata
        }

    def update_content(self, content: str, author: str) -> None:
        """
        更新文檔內容
        
        Args:
            content: 新內容
            author: 更新者
        """
        self.content = content
        self.author = author
        self.updated_at = datetime.now()
        
        # 更新版本號
        version_parts = self.version.split('.')
        if len(version_parts) >= 2:
            minor_version = int(version_parts[1]) + 1
            self.version = f"{version_parts[0]}.{minor_version}"


class FAQ:
    """
    常見問題類別
    
    Attributes:
        faq_id: FAQ唯一識別碼
        question: 問題
        answer: 答案
        category: 分類
        tags: 標籤列表
        priority: 優先級
        view_count: 查看次數
        helpful_count: 有用評分次數
        created_at: 創建時間
        updated_at: 更新時間
    """

    def __init__(
        self,
        faq_id: str,
        question: str,
        answer: str,
        category: str,
        tags: Optional[List[str]] = None,
        priority: int = 1
    ):
        """
        初始化FAQ
        
        Args:
            faq_id: FAQ ID
            question: 問題
            answer: 答案
            category: 分類
            tags: 標籤列表
            priority: 優先級 (1-5, 5最高)
        """
        self.faq_id = faq_id
        self.question = question
        self.answer = answer
        self.category = category
        self.tags = tags or []
        self.priority = priority
        self.view_count = 0
        self.helpful_count = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: FAQ資訊字典
        """
        return {
            "faq_id": self.faq_id,
            "question": self.question,
            "answer": self.answer,
            "category": self.category,
            "tags": self.tags,
            "priority": self.priority,
            "view_count": self.view_count,
            "helpful_count": self.helpful_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class HelpServiceError(Exception):
    """幫助服務錯誤"""
    pass


class HelpService:
    """
    幫助文檔服務
    
    提供幫助文檔管理功能，包括文檔管理、搜尋、
    FAQ管理等。
    
    Attributes:
        _documents: 文檔字典
        _faqs: FAQ字典
        _search_index: 搜尋索引
        _view_history: 查看歷史
    """

    def __init__(self):
        """
        初始化幫助文檔服務
        """
        self._documents: Dict[str, HelpDocument] = {}
        self._faqs: Dict[str, FAQ] = {}
        self._search_index: Dict[str, List[str]] = {}  # 關鍵字 -> 文檔ID列表
        self._view_history: List[Dict[str, Any]] = []
        
        # 初始化預設文檔和FAQ
        self._init_default_content()
        
        logger.info("幫助文檔服務初始化成功")

    def add_document(self, document: HelpDocument) -> None:
        """
        添加文檔
        
        Args:
            document: 幫助文檔
        """
        self._documents[document.doc_id] = document
        self._update_search_index(document)
        logger.info("已添加文檔: %s", document.title)

    def get_document(self, doc_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        獲取文檔
        
        Args:
            doc_id: 文檔ID
            user_id: 用戶ID (用於記錄查看歷史)
            
        Returns:
            Optional[Dict[str, Any]]: 文檔資訊，不存在時返回 None
        """
        document = self._documents.get(doc_id)
        if not document:
            return None
        
        # 增加查看次數
        document.view_count += 1
        
        # 記錄查看歷史
        if user_id:
            self._record_view(user_id, doc_id, "document")
        
        return document.to_dict()

    def search_documents(
        self,
        query: str,
        doc_type: Optional[DocumentType] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜尋文檔
        
        Args:
            query: 搜尋關鍵字
            doc_type: 文檔類型篩選
            category: 分類篩選
            limit: 限制數量
            
        Returns:
            List[Dict[str, Any]]: 搜尋結果列表
        """
        try:
            # 分詞並搜尋
            keywords = self._tokenize(query.lower())
            candidate_docs = set()
            
            for keyword in keywords:
                if keyword in self._search_index:
                    candidate_docs.update(self._search_index[keyword])
            
            # 計算相關性分數並排序
            scored_docs = []
            for doc_id in candidate_docs:
                document = self._documents.get(doc_id)
                if not document:
                    continue
                
                # 應用篩選條件
                if doc_type and document.doc_type != doc_type:
                    continue
                if category and document.category != category:
                    continue
                if document.status != DocumentStatus.PUBLISHED:
                    continue
                
                # 計算相關性分數
                score = self._calculate_relevance_score(document, keywords)
                scored_docs.append((score, document))
            
            # 按分數排序
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            
            # 返回結果
            results = []
            for score, document in scored_docs[:limit]:
                doc_dict = document.to_dict()
                doc_dict["relevance_score"] = score
                results.append(doc_dict)
            
            return results
            
        except Exception as e:
            logger.error("搜尋文檔失敗: %s", e)
            return []

    def add_faq(self, faq: FAQ) -> None:
        """
        添加FAQ
        
        Args:
            faq: FAQ物件
        """
        self._faqs[faq.faq_id] = faq
        self._update_faq_search_index(faq)
        logger.info("已添加FAQ: %s", faq.question)

    def get_faq(self, faq_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        獲取FAQ
        
        Args:
            faq_id: FAQ ID
            user_id: 用戶ID (用於記錄查看歷史)
            
        Returns:
            Optional[Dict[str, Any]]: FAQ資訊，不存在時返回 None
        """
        faq = self._faqs.get(faq_id)
        if not faq:
            return None
        
        # 增加查看次數
        faq.view_count += 1
        
        # 記錄查看歷史
        if user_id:
            self._record_view(user_id, faq_id, "faq")
        
        return faq.to_dict()

    def search_faqs(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜尋FAQ
        
        Args:
            query: 搜尋關鍵字
            category: 分類篩選
            limit: 限制數量
            
        Returns:
            List[Dict[str, Any]]: 搜尋結果列表
        """
        try:
            keywords = self._tokenize(query.lower())
            scored_faqs = []
            
            for faq in self._faqs.values():
                # 應用篩選條件
                if category and faq.category != category:
                    continue
                
                # 計算相關性分數
                score = self._calculate_faq_relevance_score(faq, keywords)
                if score > 0:
                    scored_faqs.append((score, faq))
            
            # 按分數和優先級排序
            scored_faqs.sort(key=lambda x: (x[0], x[1].priority), reverse=True)
            
            # 返回結果
            results = []
            for score, faq in scored_faqs[:limit]:
                faq_dict = faq.to_dict()
                faq_dict["relevance_score"] = score
                results.append(faq_dict)
            
            return results
            
        except Exception as e:
            logger.error("搜尋FAQ失敗: %s", e)
            return []

    def get_popular_content(self, content_type: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """
        獲取熱門內容
        
        Args:
            content_type: 內容類型 (document/faq/all)
            limit: 限制數量
            
        Returns:
            List[Dict[str, Any]]: 熱門內容列表
        """
        popular_content = []
        
        if content_type in ["document", "all"]:
            # 按查看次數排序文檔
            sorted_docs = sorted(
                self._documents.values(),
                key=lambda x: x.view_count,
                reverse=True
            )
            
            for doc in sorted_docs[:limit if content_type == "document" else limit//2]:
                if doc.status == DocumentStatus.PUBLISHED:
                    doc_dict = doc.to_dict()
                    doc_dict["content_type"] = "document"
                    popular_content.append(doc_dict)
        
        if content_type in ["faq", "all"]:
            # 按查看次數排序FAQ
            sorted_faqs = sorted(
                self._faqs.values(),
                key=lambda x: x.view_count,
                reverse=True
            )
            
            for faq in sorted_faqs[:limit if content_type == "faq" else limit//2]:
                faq_dict = faq.to_dict()
                faq_dict["content_type"] = "faq"
                popular_content.append(faq_dict)
        
        # 重新按查看次數排序
        popular_content.sort(key=lambda x: x["view_count"], reverse=True)
        
        return popular_content[:limit]

    def get_categories(self) -> Dict[str, int]:
        """
        獲取分類統計
        
        Returns:
            Dict[str, int]: 分類及其文檔數量
        """
        categories = {}
        
        # 統計文檔分類
        for doc in self._documents.values():
            if doc.status == DocumentStatus.PUBLISHED:
                categories[doc.category] = categories.get(doc.category, 0) + 1
        
        # 統計FAQ分類
        for faq in self._faqs.values():
            categories[faq.category] = categories.get(faq.category, 0) + 1
        
        return categories

    def mark_helpful(self, content_id: str, content_type: str) -> bool:
        """
        標記內容為有用
        
        Args:
            content_id: 內容ID
            content_type: 內容類型 (document/faq)
            
        Returns:
            bool: 標記是否成功
        """
        try:
            if content_type == "document" and content_id in self._documents:
                self._documents[content_id].helpful_count += 1
                return True
            elif content_type == "faq" and content_id in self._faqs:
                self._faqs[content_id].helpful_count += 1
                return True
            else:
                return False
                
        except Exception as e:
            logger.error("標記有用失敗: %s", e)
            return False

    def get_user_recommendations(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        獲取用戶個人化推薦
        
        Args:
            user_id: 用戶ID
            limit: 限制數量
            
        Returns:
            List[Dict[str, Any]]: 推薦內容列表
        """
        try:
            # 分析用戶查看歷史
            user_views = [
                view for view in self._view_history
                if view["user_id"] == user_id
            ]
            
            if not user_views:
                # 新用戶推薦熱門內容
                return self.get_popular_content(limit=limit)
            
            # 分析用戶興趣
            viewed_categories = {}
            for view in user_views:
                content_id = view["content_id"]
                content_type = view["content_type"]
                
                if content_type == "document" and content_id in self._documents:
                    category = self._documents[content_id].category
                elif content_type == "faq" and content_id in self._faqs:
                    category = self._faqs[content_id].category
                else:
                    continue
                
                viewed_categories[category] = viewed_categories.get(category, 0) + 1
            
            # 基於興趣推薦
            recommendations = []
            viewed_content_ids = {view["content_id"] for view in user_views}
            
            # 推薦同類別的其他內容
            for category in sorted(viewed_categories.keys(), key=viewed_categories.get, reverse=True):
                for doc in self._documents.values():
                    if (doc.category == category and 
                        doc.doc_id not in viewed_content_ids and
                        doc.status == DocumentStatus.PUBLISHED):
                        doc_dict = doc.to_dict()
                        doc_dict["content_type"] = "document"
                        doc_dict["recommendation_reason"] = f"基於您對 {category} 的興趣"
                        recommendations.append(doc_dict)
                        
                        if len(recommendations) >= limit:
                            break
                
                if len(recommendations) >= limit:
                    break
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error("獲取用戶推薦失敗: %s", e)
            return self.get_popular_content(limit=limit)

    def _init_default_content(self) -> None:
        """
        初始化預設內容
        """
        # 預設文檔
        default_docs = [
            HelpDocument(
                doc_id="quick_start",
                title="快速開始指南",
                content="歡迎使用 AI 交易系統！本指南將幫助您快速上手...",
                doc_type=DocumentType.QUICK_START,
                category="入門指南",
                tags=["新手", "快速開始", "教程"]
            ),
            HelpDocument(
                doc_id="trading_basics",
                title="交易基礎知識",
                content="本文檔介紹股票交易的基本概念和操作方法...",
                doc_type=DocumentType.USER_GUIDE,
                category="交易指南",
                tags=["交易", "基礎", "股票"]
            ),
            HelpDocument(
                doc_id="risk_management",
                title="風險管理指南",
                content="風險管理是成功交易的關鍵，本指南將教您...",
                doc_type=DocumentType.USER_GUIDE,
                category="風險管理",
                tags=["風險", "管理", "安全"]
            )
        ]
        
        for doc in default_docs:
            self.add_document(doc)
        
        # 預設FAQ
        default_faqs = [
            FAQ(
                faq_id="how_to_start",
                question="如何開始使用系統？",
                answer="首先註冊帳戶，然後完成新手引導，設定您的投資偏好...",
                category="入門問題",
                tags=["新手", "開始"],
                priority=5
            ),
            FAQ(
                faq_id="forgot_password",
                question="忘記密碼怎麼辦？",
                answer="點擊登入頁面的「忘記密碼」連結，輸入您的電子郵件...",
                category="帳戶問題",
                tags=["密碼", "帳戶"],
                priority=4
            ),
            FAQ(
                faq_id="trading_fees",
                question="交易手續費如何計算？",
                answer="交易手續費根據不同券商而異，通常包括...",
                category="費用問題",
                tags=["手續費", "費用"],
                priority=3
            )
        ]
        
        for faq in default_faqs:
            self.add_faq(faq)

    def _update_search_index(self, document: HelpDocument) -> None:
        """
        更新搜尋索引
        
        Args:
            document: 文檔
        """
        # 提取關鍵字
        text = f"{document.title} {document.content} {' '.join(document.tags)}"
        keywords = self._tokenize(text.lower())
        
        # 更新索引
        for keyword in keywords:
            if keyword not in self._search_index:
                self._search_index[keyword] = []
            if document.doc_id not in self._search_index[keyword]:
                self._search_index[keyword].append(document.doc_id)

    def _update_faq_search_index(self, faq: FAQ) -> None:
        """
        更新FAQ搜尋索引
        
        Args:
            faq: FAQ
        """
        # FAQ使用相同的搜尋索引結構
        text = f"{faq.question} {faq.answer} {' '.join(faq.tags)}"
        keywords = self._tokenize(text.lower())
        
        for keyword in keywords:
            if keyword not in self._search_index:
                self._search_index[keyword] = []
            if faq.faq_id not in self._search_index[keyword]:
                self._search_index[keyword].append(faq.faq_id)

    def _tokenize(self, text: str) -> List[str]:
        """
        分詞
        
        Args:
            text: 文本
            
        Returns:
            List[str]: 關鍵字列表
        """
        # 簡化的分詞實作
        # 移除標點符號並分割
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        # 過濾短詞和停用詞
        stop_words = {'的', '是', '在', '和', '與', '或', '但', '如果', '因為', '所以'}
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        return keywords

    def _calculate_relevance_score(self, document: HelpDocument, keywords: List[str]) -> float:
        """
        計算文檔相關性分數
        
        Args:
            document: 文檔
            keywords: 關鍵字列表
            
        Returns:
            float: 相關性分數
        """
        score = 0.0
        text = f"{document.title} {document.content} {' '.join(document.tags)}".lower()
        
        for keyword in keywords:
            # 標題匹配權重更高
            if keyword in document.title.lower():
                score += 3.0
            # 標籤匹配
            elif keyword in [tag.lower() for tag in document.tags]:
                score += 2.0
            # 內容匹配
            elif keyword in text:
                score += 1.0
        
        # 考慮查看次數和有用評分
        score += document.view_count * 0.01
        score += document.helpful_count * 0.1
        
        return score

    def _calculate_faq_relevance_score(self, faq: FAQ, keywords: List[str]) -> float:
        """
        計算FAQ相關性分數
        
        Args:
            faq: FAQ
            keywords: 關鍵字列表
            
        Returns:
            float: 相關性分數
        """
        score = 0.0
        question_text = faq.question.lower()
        answer_text = faq.answer.lower()
        
        for keyword in keywords:
            # 問題匹配權重最高
            if keyword in question_text:
                score += 5.0
            # 答案匹配
            elif keyword in answer_text:
                score += 2.0
            # 標籤匹配
            elif keyword in [tag.lower() for tag in faq.tags]:
                score += 1.0
        
        # 考慮優先級、查看次數和有用評分
        score += faq.priority * 0.5
        score += faq.view_count * 0.01
        score += faq.helpful_count * 0.1
        
        return score

    def _record_view(self, user_id: str, content_id: str, content_type: str) -> None:
        """
        記錄查看歷史
        
        Args:
            user_id: 用戶ID
            content_id: 內容ID
            content_type: 內容類型
        """
        view_record = {
            "user_id": user_id,
            "content_id": content_id,
            "content_type": content_type,
            "timestamp": datetime.now().isoformat()
        }
        
        self._view_history.append(view_record)
        
        # 限制歷史記錄數量
        if len(self._view_history) > 1000:
            self._view_history = self._view_history[-1000:]
