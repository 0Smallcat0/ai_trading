# -*- coding: utf-8 -*-
"""
知識庫管理器

此模組負責整合和管理來自原始項目的金融量化知識資源，
提供統一的知識庫訪問接口。

主要功能：
- 掃描和整合原始項目知識資源
- 建立知識庫索引和分類
- 提供知識檢索和推薦
- 管理學習路徑和進度
- 支援多格式文檔解析

設計原則：
- 不修改原始項目文件
- 建立統一的知識訪問接口
- 支援增量更新和擴展
- 提供智能搜索和推薦
"""

import logging
import os
import json
import pickle
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
from datetime import datetime
import re

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class KnowledgeItem:
    """知識項目數據類"""
    id: str
    title: str
    content: str
    category: str
    subcategory: str
    tags: List[str]
    source_path: str
    file_type: str
    created_time: datetime
    updated_time: datetime
    difficulty_level: int  # 1-5, 1為初級，5為高級
    estimated_reading_time: int  # 分鐘
    prerequisites: List[str]  # 前置知識
    related_items: List[str]  # 相關項目ID
    metadata: Dict[str, Any]


@dataclass
class KnowledgeCategory:
    """知識分類數據類"""
    id: str
    name: str
    description: str
    parent_id: Optional[str]
    children: List[str]
    item_count: int
    difficulty_range: Tuple[int, int]


class KnowledgeManager:
    """
    知識庫管理器
    
    負責整合原始項目的知識資源並提供統一的管理接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化知識庫管理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.original_project_path = config.get('original_project_path', 'ai_quant_trade-0.0.1')
        self.knowledge_base_path = config.get('knowledge_base_path', 'docs/knowledge')
        self.index_file = config.get('index_file', 'docs/knowledge/knowledge_index.json')
        
        # 知識庫數據
        self.knowledge_items: Dict[str, KnowledgeItem] = {}
        self.categories: Dict[str, KnowledgeCategory] = {}
        self.tags_index: Dict[str, List[str]] = {}
        self.content_index: Dict[str, List[str]] = {}
        
        # 確保目錄存在
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
        os.makedirs(self.knowledge_base_path, exist_ok=True)
        
        # 載入現有索引
        self._load_index()
        
        logger.info("知識庫管理器初始化完成")
    
    def scan_and_integrate_knowledge(self) -> Dict[str, Any]:
        """
        掃描並整合原始項目的知識資源
        
        Returns:
            掃描結果統計
        """
        logger.info("開始掃描原始項目知識資源...")
        
        scan_stats = {
            'total_files': 0,
            'processed_files': 0,
            'new_items': 0,
            'updated_items': 0,
            'categories_created': 0,
            'errors': []
        }
        
        try:
            # 掃描ai_notes目錄
            ai_notes_path = os.path.join(self.original_project_path, 'ai_notes')
            if os.path.exists(ai_notes_path):
                self._scan_ai_notes(ai_notes_path, scan_stats)
            
            # 掃描docs目錄
            docs_path = os.path.join(self.original_project_path, 'docs')
            if os.path.exists(docs_path):
                self._scan_docs(docs_path, scan_stats)
            
            # 掃描示例代碼
            examples_path = os.path.join(self.original_project_path, 'egs_data')
            if os.path.exists(examples_path):
                self._scan_examples(examples_path, scan_stats)
            
            # 掃描策略實現
            strategies_path = os.path.join(self.original_project_path, 'egs_trade')
            if os.path.exists(strategies_path):
                self._scan_strategies(strategies_path, scan_stats)
            
            # 更新索引
            self._update_content_index()
            self._save_index()
            
            logger.info(f"知識資源掃描完成: {scan_stats}")
            return scan_stats
            
        except Exception as e:
            logger.error(f"知識資源掃描失敗: {e}")
            scan_stats['errors'].append(str(e))
            return scan_stats
    
    def _scan_ai_notes(self, path: str, stats: Dict[str, Any]):
        """掃描ai_notes目錄"""
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(('.md', '.txt')):
                        file_path = os.path.join(root, file)
                        stats['total_files'] += 1
                        
                        try:
                            # 解析文件內容
                            item = self._parse_ai_notes_file(file_path)
                            if item:
                                self._add_or_update_item(item, stats)
                                stats['processed_files'] += 1
                        except Exception as e:
                            logger.error(f"處理文件失敗 {file_path}: {e}")
                            stats['errors'].append(f"{file_path}: {str(e)}")
                            
        except Exception as e:
            logger.error(f"掃描ai_notes目錄失敗: {e}")
            stats['errors'].append(f"ai_notes: {str(e)}")
    
    def _parse_ai_notes_file(self, file_path: str) -> Optional[KnowledgeItem]:
        """解析ai_notes文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 生成唯一ID
            item_id = hashlib.md5(file_path.encode()).hexdigest()
            
            # 從路徑推斷分類
            rel_path = os.path.relpath(file_path, self.original_project_path)
            path_parts = rel_path.split(os.sep)
            
            if len(path_parts) >= 3:
                category = path_parts[1]  # ai_notes下的第一級目錄
                subcategory = path_parts[2] if len(path_parts) > 3 else "通用"
            else:
                category = "其他"
                subcategory = "通用"
            
            # 提取標題
            title = self._extract_title_from_content(content) or os.path.splitext(os.path.basename(file_path))[0]
            
            # 提取標籤
            tags = self._extract_tags_from_path_and_content(rel_path, content)
            
            # 估算難度和閱讀時間
            difficulty = self._estimate_difficulty(content, category)
            reading_time = self._estimate_reading_time(content)
            
            return KnowledgeItem(
                id=item_id,
                title=title,
                content=content,
                category=category,
                subcategory=subcategory,
                tags=tags,
                source_path=file_path,
                file_type='markdown' if file_path.endswith('.md') else 'text',
                created_time=datetime.now(),
                updated_time=datetime.now(),
                difficulty_level=difficulty,
                estimated_reading_time=reading_time,
                prerequisites=[],
                related_items=[],
                metadata={'source': 'ai_notes', 'original_path': rel_path}
            )
            
        except Exception as e:
            logger.error(f"解析文件失敗 {file_path}: {e}")
            return None
    
    def _scan_docs(self, path: str, stats: Dict[str, Any]):
        """掃描docs目錄"""
        # 類似於_scan_ai_notes的實現
        pass
    
    def _scan_examples(self, path: str, stats: Dict[str, Any]):
        """掃描示例代碼"""
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(('.py', '.ipynb', '.md', '.txt')):
                        file_path = os.path.join(root, file)
                        stats['total_files'] += 1
                        
                        try:
                            item = self._parse_example_file(file_path)
                            if item:
                                self._add_or_update_item(item, stats)
                                stats['processed_files'] += 1
                        except Exception as e:
                            logger.error(f"處理示例文件失敗 {file_path}: {e}")
                            stats['errors'].append(f"{file_path}: {str(e)}")
                            
        except Exception as e:
            logger.error(f"掃描examples目錄失敗: {e}")
            stats['errors'].append(f"examples: {str(e)}")
    
    def _parse_example_file(self, file_path: str) -> Optional[KnowledgeItem]:
        """解析示例文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            item_id = hashlib.md5(file_path.encode()).hexdigest()
            rel_path = os.path.relpath(file_path, self.original_project_path)
            
            # 從路徑推斷分類
            if 'qstock' in rel_path:
                category = "數據工具"
                subcategory = "qstock"
            elif 'backtest' in rel_path:
                category = "回測框架"
                subcategory = "示例"
            elif 'rl' in rel_path:
                category = "強化學習"
                subcategory = "示例"
            else:
                category = "代碼示例"
                subcategory = "通用"
            
            title = self._extract_title_from_content(content) or os.path.splitext(os.path.basename(file_path))[0]
            tags = self._extract_tags_from_path_and_content(rel_path, content)
            
            return KnowledgeItem(
                id=item_id,
                title=title,
                content=content,
                category=category,
                subcategory=subcategory,
                tags=tags,
                source_path=file_path,
                file_type=os.path.splitext(file_path)[1][1:],
                created_time=datetime.now(),
                updated_time=datetime.now(),
                difficulty_level=self._estimate_difficulty(content, category),
                estimated_reading_time=self._estimate_reading_time(content),
                prerequisites=[],
                related_items=[],
                metadata={'source': 'examples', 'original_path': rel_path}
            )
            
        except Exception as e:
            logger.error(f"解析示例文件失敗 {file_path}: {e}")
            return None
    
    def _scan_strategies(self, path: str, stats: Dict[str, Any]):
        """掃描策略實現"""
        # 類似實現
        pass
    
    def _extract_title_from_content(self, content: str) -> Optional[str]:
        """從內容中提取標題"""
        lines = content.split('\n')
        for line in lines[:10]:  # 只檢查前10行
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            elif line.startswith('## '):
                return line[3:].strip()
        return None
    
    def _extract_tags_from_path_and_content(self, path: str, content: str) -> List[str]:
        """從路徑和內容中提取標籤"""
        tags = []
        
        # 從路徑提取標籤
        path_tags = ['量化交易', '金融']
        if 'ai_notes' in path:
            path_tags.append('理論知識')
        if 'examples' in path:
            path_tags.append('代碼示例')
        if 'rl' in path:
            path_tags.append('強化學習')
        if 'backtest' in path:
            path_tags.append('回測')
        if 'data' in path:
            path_tags.append('數據')
        
        tags.extend(path_tags)
        
        # 從內容提取標籤（簡化實現）
        content_lower = content.lower()
        keyword_tags = {
            'python': 'Python',
            'pandas': 'Pandas',
            'numpy': 'NumPy',
            'matplotlib': '可視化',
            'plotly': '可視化',
            'machine learning': '機器學習',
            'deep learning': '深度學習',
            'neural network': '神經網絡',
            'strategy': '策略',
            'portfolio': '投資組合',
            'risk': '風險管理',
            'return': '收益分析'
        }
        
        for keyword, tag in keyword_tags.items():
            if keyword in content_lower:
                tags.append(tag)
        
        return list(set(tags))  # 去重
    
    def _estimate_difficulty(self, content: str, category: str) -> int:
        """估算內容難度"""
        # 基於內容長度、技術術語密度等估算難度
        content_length = len(content)
        
        # 技術術語
        technical_terms = [
            'algorithm', 'optimization', 'regression', 'classification',
            'neural network', 'deep learning', 'reinforcement learning',
            'portfolio', 'sharpe ratio', 'volatility', 'correlation'
        ]
        
        term_count = sum(1 for term in technical_terms if term.lower() in content.lower())
        
        # 基礎難度
        if category in ['01_资源', '概述']:
            base_difficulty = 1
        elif category in ['理論', '工具及框架']:
            base_difficulty = 2
        elif category in ['大模型', '強化學習']:
            base_difficulty = 4
        else:
            base_difficulty = 3
        
        # 根據內容調整
        if content_length > 5000:
            base_difficulty += 1
        if term_count > 5:
            base_difficulty += 1
        
        return min(5, max(1, base_difficulty))
    
    def _estimate_reading_time(self, content: str) -> int:
        """估算閱讀時間（分鐘）"""
        # 假設平均閱讀速度為每分鐘200字
        char_count = len(content)
        return max(1, char_count // 200)
    
    def _add_or_update_item(self, item: KnowledgeItem, stats: Dict[str, Any]):
        """添加或更新知識項目"""
        if item.id in self.knowledge_items:
            stats['updated_items'] += 1
        else:
            stats['new_items'] += 1
        
        self.knowledge_items[item.id] = item
        
        # 更新分類
        self._update_category(item.category, item.subcategory, stats)
        
        # 更新標籤索引
        for tag in item.tags:
            if tag not in self.tags_index:
                self.tags_index[tag] = []
            if item.id not in self.tags_index[tag]:
                self.tags_index[tag].append(item.id)
    
    def _update_category(self, category: str, subcategory: str, stats: Dict[str, Any]):
        """更新分類信息"""
        category_id = category.replace(' ', '_').lower()
        
        if category_id not in self.categories:
            self.categories[category_id] = KnowledgeCategory(
                id=category_id,
                name=category,
                description=f"{category}相關知識",
                parent_id=None,
                children=[],
                item_count=0,
                difficulty_range=(1, 5)
            )
            stats['categories_created'] += 1
        
        # 更新項目計數
        self.categories[category_id].item_count += 1
    
    def _update_content_index(self):
        """更新內容索引"""
        self.content_index.clear()
        
        for item_id, item in self.knowledge_items.items():
            # 簡單的關鍵詞索引
            words = re.findall(r'\w+', item.content.lower())
            for word in set(words):
                if len(word) > 2:  # 忽略太短的詞
                    if word not in self.content_index:
                        self.content_index[word] = []
                    if item_id not in self.content_index[word]:
                        self.content_index[word].append(item_id)
    
    def search_knowledge(self, query: str, limit: int = 10) -> List[KnowledgeItem]:
        """搜索知識庫"""
        query_words = re.findall(r'\w+', query.lower())
        item_scores = {}
        
        for word in query_words:
            if word in self.content_index:
                for item_id in self.content_index[word]:
                    if item_id not in item_scores:
                        item_scores[item_id] = 0
                    item_scores[item_id] += 1
        
        # 按分數排序
        sorted_items = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for item_id, score in sorted_items[:limit]:
            if item_id in self.knowledge_items:
                results.append(self.knowledge_items[item_id])
        
        return results
    
    def get_items_by_category(self, category: str) -> List[KnowledgeItem]:
        """按分類獲取知識項目"""
        return [item for item in self.knowledge_items.values() if item.category == category]
    
    def get_items_by_tags(self, tags: List[str]) -> List[KnowledgeItem]:
        """按標籤獲取知識項目"""
        item_ids = set()
        for tag in tags:
            if tag in self.tags_index:
                item_ids.update(self.tags_index[tag])
        
        return [self.knowledge_items[item_id] for item_id in item_ids if item_id in self.knowledge_items]
    
    def get_learning_path(self, target_topic: str) -> List[KnowledgeItem]:
        """獲取學習路徑"""
        # 簡化實現：按難度排序相關項目
        related_items = self.search_knowledge(target_topic, limit=20)
        return sorted(related_items, key=lambda x: x.difficulty_level)
    
    def _save_index(self):
        """保存索引"""
        try:
            index_data = {
                'knowledge_items': {k: asdict(v) for k, v in self.knowledge_items.items()},
                'categories': {k: asdict(v) for k, v in self.categories.items()},
                'tags_index': self.tags_index,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"知識庫索引已保存: {self.index_file}")
            
        except Exception as e:
            logger.error(f"保存索引失敗: {e}")
    
    def _load_index(self):
        """載入索引"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                # 重建知識項目
                for item_id, item_data in index_data.get('knowledge_items', {}).items():
                    # 轉換日期字符串回datetime對象
                    if isinstance(item_data.get('created_time'), str):
                        item_data['created_time'] = datetime.fromisoformat(item_data['created_time'])
                    if isinstance(item_data.get('updated_time'), str):
                        item_data['updated_time'] = datetime.fromisoformat(item_data['updated_time'])
                    
                    self.knowledge_items[item_id] = KnowledgeItem(**item_data)
                
                # 重建分類
                for cat_id, cat_data in index_data.get('categories', {}).items():
                    self.categories[cat_id] = KnowledgeCategory(**cat_data)
                
                # 重建標籤索引
                self.tags_index = index_data.get('tags_index', {})
                
                logger.info(f"知識庫索引已載入: {len(self.knowledge_items)} 個項目")
            
        except Exception as e:
            logger.error(f"載入索引失敗: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取知識庫統計信息"""
        return {
            'total_items': len(self.knowledge_items),
            'total_categories': len(self.categories),
            'total_tags': len(self.tags_index),
            'difficulty_distribution': self._get_difficulty_distribution(),
            'category_distribution': self._get_category_distribution(),
            'file_type_distribution': self._get_file_type_distribution()
        }
    
    def _get_difficulty_distribution(self) -> Dict[int, int]:
        """獲取難度分佈"""
        distribution = {i: 0 for i in range(1, 6)}
        for item in self.knowledge_items.values():
            distribution[item.difficulty_level] += 1
        return distribution
    
    def _get_category_distribution(self) -> Dict[str, int]:
        """獲取分類分佈"""
        distribution = {}
        for item in self.knowledge_items.values():
            if item.category not in distribution:
                distribution[item.category] = 0
            distribution[item.category] += 1
        return distribution
    
    def _get_file_type_distribution(self) -> Dict[str, int]:
        """獲取文件類型分佈"""
        distribution = {}
        for item in self.knowledge_items.values():
            if item.file_type not in distribution:
                distribution[item.file_type] = 0
            distribution[item.file_type] += 1
        return distribution
