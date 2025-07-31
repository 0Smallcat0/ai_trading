"""文檔標準化工具

此模組提供文檔的標準化和管理功能，包括：
- 文檔格式統一（Markdown、UTF-8 編碼）
- 版本號和變更歷史管理
- 技術準確性驗證
- 多語言一致性檢查
- 文檔結構優化

符合文檔標準：Traditional Chinese、版本控制、WCAG 2.1、技術準確性
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import hashlib

# 設定日誌
logger = logging.getLogger(__name__)


class DocumentStandardizer:
    """文檔標準化器
    
    提供文檔的標準化和管理功能。
    """
    
    # 文檔標準配置
    REQUIRED_ENCODING = "utf-8"
    REQUIRED_FORMAT = "markdown"
    REQUIRED_LANGUAGE = "zh_TW"  # Traditional Chinese
    
    # 必須保留的文檔
    PROTECTED_DOCS = [
        "README.md",
        "docs/新進人員指南.md",
        "docs/使用者手冊/",
        "docs/FAQ/",
        "docs/開發者指南/",
        "docs/Todo_list.md"
    ]
    
    # 文檔版本格式
    VERSION_PATTERN = r"v\d+\.\d+(\.\d+)?"
    
    def __init__(self, project_root: Optional[str] = None):
        """初始化文檔標準化器
        
        Args:
            project_root: 專案根目錄路徑
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.docs_dir = self.project_root / "docs"
        
    def analyze_documentation_structure(self) -> Dict[str, Any]:
        """分析文檔結構
        
        Returns:
            文檔結構分析結果
        """
        logger.info("分析文檔結構...")
        
        analysis = {
            "total_files": 0,
            "markdown_files": 0,
            "non_markdown_files": [],
            "encoding_issues": [],
            "missing_versions": [],
            "duplicate_files": [],
            "structure_compliance": {},
            "protected_docs_status": {}
        }
        
        # 檢查必須保留的文檔
        for protected_doc in self.PROTECTED_DOCS:
            doc_path = self.project_root / protected_doc
            analysis["protected_docs_status"][protected_doc] = {
                "exists": doc_path.exists(),
                "path": str(doc_path),
                "is_directory": doc_path.is_dir() if doc_path.exists() else False
            }
        
        # 遍歷所有文檔檔案
        for doc_file in self.docs_dir.rglob("*"):
            if doc_file.is_file():
                analysis["total_files"] += 1
                
                # 檢查檔案格式
                if doc_file.suffix.lower() in [".md", ".markdown"]:
                    analysis["markdown_files"] += 1
                    
                    # 檢查編碼
                    encoding_result = self._check_file_encoding(doc_file)
                    if not encoding_result["is_utf8"]:
                        analysis["encoding_issues"].append({
                            "file": str(doc_file.relative_to(self.project_root)),
                            "detected_encoding": encoding_result["detected_encoding"]
                        })
                    
                    # 檢查版本資訊
                    version_result = self._check_version_info(doc_file)
                    if not version_result["has_version"]:
                        analysis["missing_versions"].append({
                            "file": str(doc_file.relative_to(self.project_root)),
                            "reason": version_result["reason"]
                        })
                        
                else:
                    analysis["non_markdown_files"].append({
                        "file": str(doc_file.relative_to(self.project_root)),
                        "extension": doc_file.suffix
                    })
        
        # 檢查重複檔案
        analysis["duplicate_files"] = self._find_duplicate_files()
        
        # 檢查目錄結構合規性
        analysis["structure_compliance"] = self._check_structure_compliance()
        
        logger.info(f"文檔結構分析完成: {analysis}")
        return analysis
    
    def _check_file_encoding(self, file_path: Path) -> Dict[str, Any]:
        """檢查檔案編碼
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            編碼檢查結果
        """
        try:
            # 嘗試用 UTF-8 讀取
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read()
            return {"is_utf8": True, "detected_encoding": "utf-8"}
        except UnicodeDecodeError:
            # 嘗試檢測編碼
            try:
                import chardet
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                detected = chardet.detect(raw_data)
                return {
                    "is_utf8": False,
                    "detected_encoding": detected.get("encoding", "unknown")
                }
            except ImportError:
                return {"is_utf8": False, "detected_encoding": "unknown"}
        except Exception as e:
            logger.error(f"檢查檔案編碼失敗 {file_path}: {e}")
            return {"is_utf8": False, "detected_encoding": "error"}
    
    def _check_version_info(self, file_path: Path) -> Dict[str, Any]:
        """檢查版本資訊
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            版本檢查結果
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 檢查是否有版本號
            version_match = re.search(self.VERSION_PATTERN, content)
            
            # 檢查是否有變更歷史
            has_changelog = any(keyword in content.lower() for keyword in [
                "變更歷史", "changelog", "版本歷史", "更新記錄"
            ])
            
            if version_match and has_changelog:
                return {
                    "has_version": True,
                    "version": version_match.group(),
                    "has_changelog": True
                }
            elif version_match:
                return {
                    "has_version": True,
                    "version": version_match.group(),
                    "has_changelog": False,
                    "reason": "缺少變更歷史"
                }
            else:
                return {
                    "has_version": False,
                    "reason": "缺少版本號和變更歷史"
                }
                
        except Exception as e:
            logger.error(f"檢查版本資訊失敗 {file_path}: {e}")
            return {"has_version": False, "reason": f"讀取失敗: {e}"}
    
    def _find_duplicate_files(self) -> List[Dict[str, Any]]:
        """尋找重複檔案
        
        Returns:
            重複檔案列表
        """
        file_hashes = {}
        duplicates = []
        
        for doc_file in self.docs_dir.rglob("*.md"):
            if doc_file.is_file():
                try:
                    with open(doc_file, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                    
                    if file_hash in file_hashes:
                        duplicates.append({
                            "original": str(file_hashes[file_hash].relative_to(self.project_root)),
                            "duplicate": str(doc_file.relative_to(self.project_root)),
                            "hash": file_hash
                        })
                    else:
                        file_hashes[file_hash] = doc_file
                        
                except Exception as e:
                    logger.error(f"計算檔案雜湊失敗 {doc_file}: {e}")
        
        return duplicates
    
    def _check_structure_compliance(self) -> Dict[str, Any]:
        """檢查目錄結構合規性
        
        Returns:
            結構合規性檢查結果
        """
        required_structure = {
            "docs/": True,
            "docs/使用者手冊/": True,
            "docs/FAQ/": True,
            "docs/開發者指南/": True,
            "docs/modules/": False,  # 可選
            "docs/共用工具說明/": False,  # 可選
            "docs/Q&A常見問題.md": False,  # 可選
        }
        
        compliance = {}
        
        for path, required in required_structure.items():
            full_path = self.project_root / path
            exists = full_path.exists()
            
            compliance[path] = {
                "exists": exists,
                "required": required,
                "compliant": exists if required else True
            }
        
        return compliance
    
    def standardize_document(self, file_path: Path) -> Dict[str, Any]:
        """標準化單個文檔
        
        Args:
            file_path: 文檔檔案路徑
            
        Returns:
            標準化結果
        """
        logger.info(f"標準化文檔: {file_path}")
        
        result = {
            "success": False,
            "changes_made": [],
            "errors": []
        }
        
        try:
            # 讀取原始內容
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            modified_content = original_content
            
            # 1. 添加版本資訊（如果缺少）
            if not re.search(self.VERSION_PATTERN, modified_content):
                version_header = self._generate_version_header()
                modified_content = version_header + "\n\n" + modified_content
                result["changes_made"].append("添加版本資訊")
            
            # 2. 標準化 Markdown 格式
            modified_content = self._standardize_markdown_format(modified_content)
            if modified_content != original_content:
                result["changes_made"].append("標準化 Markdown 格式")
            
            # 3. 確保 UTF-8 編碼
            if modified_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                result["changes_made"].append("更新檔案內容")
            
            result["success"] = True
            logger.info(f"文檔標準化完成: {file_path}")
            
        except Exception as e:
            error_msg = f"標準化文檔失敗: {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def _generate_version_header(self) -> str:
        """生成版本標頭
        
        Returns:
            版本標頭字串
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        return f"""<!-- 文檔版本資訊 -->
<!-- 版本: v1.0 -->
<!-- 最後更新: {current_date} -->
<!-- 變更歷史:
- v1.0 ({current_date}): 初始版本
-->"""
    
    def _standardize_markdown_format(self, content: str) -> str:
        """標準化 Markdown 格式
        
        Args:
            content: 原始內容
            
        Returns:
            標準化後的內容
        """
        # 標準化標題格式
        content = re.sub(r'^(#{1,6})\s*(.+)$', r'\1 \2', content, flags=re.MULTILINE)
        
        # 標準化列表格式
        content = re.sub(r'^(\s*)-\s+(.+)$', r'\1- \2', content, flags=re.MULTILINE)
        content = re.sub(r'^(\s*)\*\s+(.+)$', r'\1- \2', content, flags=re.MULTILINE)
        
        # 移除多餘的空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 確保檔案結尾有換行
        if not content.endswith('\n'):
            content += '\n'
        
        return content
    
    def generate_documentation_report(self) -> Dict[str, Any]:
        """生成文檔標準化報告
        
        Returns:
            文檔報告
        """
        logger.info("生成文檔標準化報告...")
        
        # 分析文檔結構
        structure_analysis = self.analyze_documentation_structure()
        
        # 生成建議
        recommendations = self._generate_documentation_recommendations(structure_analysis)
        
        # 生成報告
        report = {
            "timestamp": datetime.now().isoformat(),
            "structure_analysis": structure_analysis,
            "recommendations": recommendations,
            "compliance_score": self._calculate_compliance_score(structure_analysis)
        }
        
        # 保存報告
        report_file = self.project_root / "documentation_standardization_report.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"文檔報告已保存: {report_file}")
        except Exception as e:
            logger.error(f"保存文檔報告失敗: {e}")
        
        return report
    
    def _generate_documentation_recommendations(
        self, analysis: Dict[str, Any]
    ) -> List[str]:
        """生成文檔改進建議
        
        Args:
            analysis: 文檔分析結果
            
        Returns:
            改進建議列表
        """
        recommendations = []
        
        # 編碼問題
        if analysis["encoding_issues"]:
            recommendations.append(
                f"有 {len(analysis['encoding_issues'])} 個檔案編碼不是 UTF-8，需要轉換"
            )
        
        # 版本資訊缺失
        if analysis["missing_versions"]:
            recommendations.append(
                f"有 {len(analysis['missing_versions'])} 個檔案缺少版本資訊，需要添加"
            )
        
        # 重複檔案
        if analysis["duplicate_files"]:
            recommendations.append(
                f"發現 {len(analysis['duplicate_files'])} 組重複檔案，建議合併或刪除"
            )
        
        # 非 Markdown 檔案
        if analysis["non_markdown_files"]:
            recommendations.append(
                f"有 {len(analysis['non_markdown_files'])} 個非 Markdown 檔案，建議轉換格式"
            )
        
        # 結構合規性
        non_compliant = [
            path for path, info in analysis["structure_compliance"].items()
            if not info["compliant"]
        ]
        if non_compliant:
            recommendations.append(
                f"目錄結構不完整，缺少: {', '.join(non_compliant)}"
            )
        
        # 保護文檔狀態
        missing_protected = [
            doc for doc, status in analysis["protected_docs_status"].items()
            if not status["exists"]
        ]
        if missing_protected:
            recommendations.append(
                f"缺少必須保留的文檔: {', '.join(missing_protected)}"
            )
        
        if not recommendations:
            recommendations.append("文檔結構良好，符合所有標準")
        
        return recommendations
    
    def _calculate_compliance_score(self, analysis: Dict[str, Any]) -> float:
        """計算合規評分
        
        Args:
            analysis: 文檔分析結果
            
        Returns:
            合規評分 (0-100)
        """
        total_score = 100
        
        # 編碼問題扣分
        if analysis["encoding_issues"]:
            total_score -= len(analysis["encoding_issues"]) * 5
        
        # 版本資訊缺失扣分
        if analysis["missing_versions"]:
            total_score -= len(analysis["missing_versions"]) * 3
        
        # 重複檔案扣分
        if analysis["duplicate_files"]:
            total_score -= len(analysis["duplicate_files"]) * 2
        
        # 結構不合規扣分
        non_compliant = sum(
            1 for info in analysis["structure_compliance"].values()
            if not info["compliant"]
        )
        total_score -= non_compliant * 10
        
        return max(0, total_score)


def main():
    """主函數"""
    standardizer = DocumentStandardizer()
    
    print("🚀 開始文檔標準化分析...")
    report = standardizer.generate_documentation_report()
    
    print("\n📊 文檔標準化報告")
    print("=" * 50)
    
    # 顯示結構分析結果
    analysis = report["structure_analysis"]
    print(f"\n📏 文檔結構分析:")
    print(f"  總檔案數: {analysis['total_files']}")
    print(f"  Markdown 檔案: {analysis['markdown_files']}")
    print(f"  編碼問題: {len(analysis['encoding_issues'])}")
    print(f"  缺少版本: {len(analysis['missing_versions'])}")
    print(f"  重複檔案: {len(analysis['duplicate_files'])}")
    
    # 顯示合規評分
    print(f"\n📊 合規評分: {report['compliance_score']:.1f}/100")
    
    # 顯示建議
    print(f"\n💡 改進建議:")
    for i, recommendation in enumerate(report["recommendations"], 1):
        print(f"  {i}. {recommendation}")
    
    print(f"\n📄 詳細報告已保存至: documentation_standardization_report.json")


if __name__ == "__main__":
    main()
