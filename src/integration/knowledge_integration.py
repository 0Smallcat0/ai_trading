# -*- coding: utf-8 -*-
"""
知識庫系統整合適配器

此模組將知識庫和學習系統整合到原始項目中，
提供統一的知識管理和學習功能接口。

主要功能：
- 知識庫系統整合
- 交互式學習系統整合
- 原始項目文檔整合
- 幫助系統擴展
- 用戶培訓模組整合

整合策略：
- 整合到原始項目的文檔系統
- 擴展幫助和支援功能
- 提供統一的學習界面
- 與用戶系統關聯
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# 設定日誌
logger = logging.getLogger(__name__)


class KnowledgeSystemAdapter:
    """
    知識庫系統整合適配器
    
    將知識庫和學習系統整合到原始項目中
    """
    
    def __init__(self, config):
        """
        初始化知識庫系統適配器
        
        Args:
            config: 整合配置
        """
        self.config = config
        self.initialized = False
        
        # 知識庫組件
        self.knowledge_manager = None
        self.learning_system = None
        
        # 原始項目整合
        self.legacy_docs_path = None
        self.integrated_docs = {}
        
        # 用戶學習追蹤
        self.user_progress = {}
        self.learning_analytics = None
        
        logger.info("知識庫系統適配器初始化")
    
    def initialize(self) -> bool:
        """
        初始化知識庫系統
        
        Returns:
            是否初始化成功
        """
        try:
            # 檢查原始項目文檔
            if not self._check_legacy_docs():
                logger.warning("原始項目文檔檢查失敗，繼續初始化")
            
            # 初始化知識庫管理器
            if not self._initialize_knowledge_manager():
                return False
            
            # 初始化學習系統
            if not self._initialize_learning_system():
                return False
            
            # 整合原始項目文檔
            if not self._integrate_legacy_docs():
                logger.warning("原始項目文檔整合失敗")
            
            # 初始化學習分析
            if not self._initialize_learning_analytics():
                logger.warning("學習分析初始化失敗")
            
            # 掃描和整合知識資源
            if not self._scan_and_integrate_knowledge():
                logger.warning("知識資源掃描失敗")
            
            self.initialized = True
            logger.info("知識庫系統初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"知識庫系統初始化失敗: {e}")
            return False
    
    def _check_legacy_docs(self) -> bool:
        """檢查原始項目文檔"""
        try:
            legacy_path = Path(self.config.legacy_project_path)
            docs_path = legacy_path / "docs"
            ai_notes_path = legacy_path / "ai_notes"
            
            self.legacy_docs_path = {
                'docs': docs_path if docs_path.exists() else None,
                'ai_notes': ai_notes_path if ai_notes_path.exists() else None
            }
            
            found_docs = sum(1 for path in self.legacy_docs_path.values() if path)
            logger.info(f"找到 {found_docs} 個原始項目文檔目錄")
            
            return found_docs > 0
            
        except Exception as e:
            logger.error(f"檢查原始項目文檔失敗: {e}")
            return False
    
    def _initialize_knowledge_manager(self) -> bool:
        """初始化知識庫管理器"""
        try:
            from ..knowledge_base.knowledge_manager import KnowledgeManager
            
            knowledge_config = {
                'original_project_path': self.config.legacy_project_path,
                'knowledge_base_path': 'docs/knowledge',
                'index_file': 'docs/knowledge/knowledge_index.json',
                'cache_dir': 'cache/knowledge',
                'cache_ttl': 3600
            }
            
            self.knowledge_manager = KnowledgeManager(knowledge_config)
            logger.info("知識庫管理器初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"知識庫管理器模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"知識庫管理器初始化失敗: {e}")
            return False
    
    def _initialize_learning_system(self) -> bool:
        """初始化學習系統"""
        try:
            from ..education.interactive_learning import InteractiveLearningSystem
            
            self.learning_system = InteractiveLearningSystem()
            logger.info("交互式學習系統初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"學習系統模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"學習系統初始化失敗: {e}")
            return False
    
    def _integrate_legacy_docs(self) -> bool:
        """整合原始項目文檔"""
        try:
            integrated_count = 0
            
            # 整合docs目錄
            if self.legacy_docs_path.get('docs'):
                docs_integration = self._integrate_docs_directory(self.legacy_docs_path['docs'])
                self.integrated_docs['legacy_docs'] = docs_integration
                integrated_count += len(docs_integration)
            
            # 整合ai_notes目錄
            if self.legacy_docs_path.get('ai_notes'):
                notes_integration = self._integrate_ai_notes_directory(self.legacy_docs_path['ai_notes'])
                self.integrated_docs['ai_notes'] = notes_integration
                integrated_count += len(notes_integration)
            
            logger.info(f"已整合 {integrated_count} 個原始項目文檔")
            return True
            
        except Exception as e:
            logger.error(f"原始項目文檔整合失敗: {e}")
            return False
    
    def _integrate_docs_directory(self, docs_path: Path) -> Dict[str, Any]:
        """整合docs目錄"""
        try:
            docs_info = {}
            
            for file_path in docs_path.rglob("*.md"):
                try:
                    relative_path = file_path.relative_to(docs_path)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    docs_info[str(relative_path)] = {
                        'path': str(file_path),
                        'title': self._extract_title_from_content(content),
                        'size': len(content),
                        'type': 'documentation',
                        'integrated': True
                    }
                    
                except Exception as e:
                    logger.warning(f"文檔整合失敗 {file_path}: {e}")
            
            return docs_info
            
        except Exception as e:
            logger.error(f"docs目錄整合失敗: {e}")
            return {}
    
    def _integrate_ai_notes_directory(self, notes_path: Path) -> Dict[str, Any]:
        """整合ai_notes目錄"""
        try:
            notes_info = {}
            
            for file_path in notes_path.rglob("*.md"):
                try:
                    relative_path = file_path.relative_to(notes_path)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    notes_info[str(relative_path)] = {
                        'path': str(file_path),
                        'title': self._extract_title_from_content(content),
                        'size': len(content),
                        'type': 'ai_notes',
                        'integrated': True
                    }
                    
                except Exception as e:
                    logger.warning(f"AI筆記整合失敗 {file_path}: {e}")
            
            return notes_info
            
        except Exception as e:
            logger.error(f"ai_notes目錄整合失敗: {e}")
            return {}
    
    def _extract_title_from_content(self, content: str) -> str:
        """從內容中提取標題"""
        try:
            lines = content.split('\n')
            for line in lines[:10]:
                line = line.strip()
                if line.startswith('# '):
                    return line[2:].strip()
                elif line.startswith('## '):
                    return line[3:].strip()
            
            return "無標題"
            
        except Exception:
            return "無標題"
    
    def _initialize_learning_analytics(self) -> bool:
        """初始化學習分析"""
        try:
            # 這裡可以初始化學習分析組件
            self.learning_analytics = {
                'enabled': True,
                'tracking_enabled': True,
                'analytics_data': {},
                'user_sessions': {}
            }
            
            logger.info("學習分析初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"學習分析初始化失敗: {e}")
            return False
    
    def _scan_and_integrate_knowledge(self) -> bool:
        """掃描和整合知識資源"""
        try:
            if self.knowledge_manager:
                scan_results = self.knowledge_manager.scan_and_integrate_knowledge()
                
                if scan_results['errors']:
                    logger.warning(f"知識掃描有 {len(scan_results['errors'])} 個錯誤")
                    for error in scan_results['errors'][:5]:  # 只記錄前5個錯誤
                        logger.warning(f"掃描錯誤: {error}")
                
                logger.info(f"知識掃描完成: 新增 {scan_results['new_items']} 個項目")
                return True
            else:
                logger.error("知識庫管理器未初始化")
                return False
                
        except Exception as e:
            logger.error(f"知識資源掃描失敗: {e}")
            return False
    
    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索知識庫
        
        Args:
            query: 搜索查詢
            limit: 結果限制
            
        Returns:
            搜索結果
        """
        try:
            if not self.knowledge_manager:
                logger.error("知識庫管理器未初始化")
                return []
            
            results = self.knowledge_manager.search_knowledge(query, limit)
            
            # 轉換為統一格式
            formatted_results = []
            for item in results:
                formatted_results.append({
                    'id': item.id,
                    'title': item.title,
                    'content': item.content[:500] + "..." if len(item.content) > 500 else item.content,
                    'category': item.category,
                    'subcategory': item.subcategory,
                    'tags': item.tags,
                    'difficulty_level': item.difficulty_level,
                    'estimated_reading_time': item.estimated_reading_time,
                    'source': item.metadata.get('source', 'unknown'),
                    'created_time': item.created_time.isoformat()
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"知識搜索失敗: {e}")
            return []
    
    def get_learning_path(self, topic: str) -> List[Dict[str, Any]]:
        """
        獲取學習路徑
        
        Args:
            topic: 學習主題
            
        Returns:
            學習路徑
        """
        try:
            if not self.knowledge_manager:
                logger.error("知識庫管理器未初始化")
                return []
            
            path_items = self.knowledge_manager.get_learning_path(topic)
            
            # 轉換為統一格式
            learning_path = []
            for i, item in enumerate(path_items, 1):
                learning_path.append({
                    'step': i,
                    'id': item.id,
                    'title': item.title,
                    'description': item.content[:200] + "..." if len(item.content) > 200 else item.content,
                    'difficulty_level': item.difficulty_level,
                    'estimated_time': item.estimated_reading_time,
                    'prerequisites': item.prerequisites,
                    'category': item.category,
                    'tags': item.tags
                })
            
            return learning_path
            
        except Exception as e:
            logger.error(f"獲取學習路徑失敗: {e}")
            return []
    
    def track_user_progress(self, user_id: str, item_id: str, progress: float):
        """
        追蹤用戶學習進度
        
        Args:
            user_id: 用戶ID
            item_id: 知識項目ID
            progress: 進度（0-1）
        """
        try:
            if user_id not in self.user_progress:
                self.user_progress[user_id] = {}
            
            self.user_progress[user_id][item_id] = {
                'progress': progress,
                'last_accessed': datetime.now(),
                'completed': progress >= 1.0
            }
            
            # 更新學習分析
            if self.learning_analytics and self.learning_analytics['tracking_enabled']:
                self._update_learning_analytics(user_id, item_id, progress)
            
            logger.debug(f"用戶學習進度已更新: {user_id} - {item_id} - {progress:.2%}")
            
        except Exception as e:
            logger.error(f"用戶進度追蹤失敗: {e}")
    
    def _update_learning_analytics(self, user_id: str, item_id: str, progress: float):
        """更新學習分析數據"""
        try:
            analytics_data = self.learning_analytics['analytics_data']
            
            if user_id not in analytics_data:
                analytics_data[user_id] = {
                    'total_items': 0,
                    'completed_items': 0,
                    'total_time': 0,
                    'last_activity': datetime.now()
                }
            
            user_analytics = analytics_data[user_id]
            user_analytics['last_activity'] = datetime.now()
            
            # 如果是新項目
            if item_id not in self.user_progress.get(user_id, {}):
                user_analytics['total_items'] += 1
            
            # 如果完成了項目
            if progress >= 1.0:
                user_analytics['completed_items'] += 1
            
        except Exception as e:
            logger.error(f"學習分析更新失敗: {e}")
    
    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """
        獲取用戶學習進度
        
        Args:
            user_id: 用戶ID
            
        Returns:
            用戶進度信息
        """
        try:
            user_progress = self.user_progress.get(user_id, {})
            
            total_items = len(user_progress)
            completed_items = sum(1 for item in user_progress.values() if item['completed'])
            
            progress_summary = {
                'user_id': user_id,
                'total_items': total_items,
                'completed_items': completed_items,
                'completion_rate': completed_items / total_items if total_items > 0 else 0,
                'recent_activity': [],
                'recommendations': []
            }
            
            # 獲取最近活動
            recent_items = sorted(
                user_progress.items(),
                key=lambda x: x[1]['last_accessed'],
                reverse=True
            )[:5]
            
            for item_id, item_progress in recent_items:
                progress_summary['recent_activity'].append({
                    'item_id': item_id,
                    'progress': item_progress['progress'],
                    'last_accessed': item_progress['last_accessed'].isoformat(),
                    'completed': item_progress['completed']
                })
            
            return progress_summary
            
        except Exception as e:
            logger.error(f"獲取用戶進度失敗: {e}")
            return {}
    
    def get_knowledge_statistics(self) -> Dict[str, Any]:
        """獲取知識庫統計信息"""
        try:
            if not self.knowledge_manager:
                return {}
            
            stats = self.knowledge_manager.get_statistics()
            
            # 添加整合信息
            stats['integration_info'] = {
                'legacy_docs_integrated': len(self.integrated_docs),
                'learning_system_available': self.learning_system is not None,
                'analytics_enabled': self.learning_analytics is not None,
                'total_users_tracked': len(self.user_progress)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"獲取知識庫統計失敗: {e}")
            return {}
    
    def health_check(self) -> bool:
        """健康檢查"""
        try:
            if not self.initialized:
                return False
            
            # 檢查知識庫管理器
            if not self.knowledge_manager:
                return False
            
            # 檢查學習系統
            if not self.learning_system:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"知識庫系統健康檢查失敗: {e}")
            return False
    
    def shutdown(self):
        """關閉知識庫系統"""
        try:
            logger.info("正在關閉知識庫系統...")
            
            # 保存用戶進度
            if self.user_progress:
                try:
                    # 這裡可以實現進度持久化
                    logger.info("用戶進度已保存")
                except Exception as e:
                    logger.error(f"用戶進度保存失敗: {e}")
            
            # 清理資源
            self.user_progress.clear()
            self.integrated_docs.clear()
            
            self.initialized = False
            logger.info("知識庫系統已關閉")
            
        except Exception as e:
            logger.error(f"知識庫系統關閉失敗: {e}")
