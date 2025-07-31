#!/usr/bin/env python3
"""
相對導入修復腳本

此腳本系統性地掃描和修復 src/ui/pages/ 目錄中的相對導入問題，
將相對導入轉換為絕對導入以解決 ImportError 問題。
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RelativeImportFixer:
    """相對導入修復器"""
    
    def __init__(self, target_dir: str = "../../src/ui/pages"):
        self.target_dir = target_dir
        self.fixes_applied = []
        self.errors = []
        
    def scan_files(self) -> List[str]:
        """掃描目標目錄中的所有Python文件"""
        python_files = []
        
        for root, dirs, files in os.walk(self.target_dir):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def find_relative_imports(self, file_path: str) -> List[Tuple[int, str, str]]:
        """找出文件中的相對導入"""
        relative_imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                # 匹配相對導入模式
                patterns = [
                    r'from\s+\.\.\.(\w+(?:\.\w+)*)\s+import',  # from ...module import
                    r'from\s+\.\.(\w+(?:\.\w+)*)\s+import',   # from ..module import
                    r'from\s+\.(\w+(?:\.\w+)*)\s+import',     # from .module import
                    r'import\s+\.\.\.(\w+(?:\.\w+)*)',        # import ...module
                    r'import\s+\.\.(\w+(?:\.\w+)*)',          # import ..module
                    r'import\s+\.(\w+(?:\.\w+)*)',            # import .module
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line.strip())
                    if match:
                        relative_imports.append((i, line.strip(), match.group(0)))
        
        except Exception as e:
            logger.error(f"讀取文件失敗 {file_path}: {e}")
            self.errors.append(f"{file_path}: {str(e)}")
        
        return relative_imports
    
    def convert_relative_to_absolute(self, relative_import: str, file_path: str) -> str:
        """將相對導入轉換為絕對導入"""
        
        # 相對導入轉換映射
        conversion_map = {
            # 核心服務
            'from ...core.': 'from src.core.',
            'from ..core.': 'from src.core.',
            
            # UI組件
            'from ..components.': 'from src.ui.components.',
            'from ...ui.components.': 'from src.ui.components.',
            
            # UI響應式
            'from ..responsive': 'from src.ui.responsive',
            'from ...ui.responsive': 'from src.ui.responsive',
            
            # 教育模組
            'from ...education': 'from src.education',
            'from ..education': 'from src.education',
            
            # 新手引導
            'from ..onboarding': 'from src.ui.onboarding',
            'from ...ui.onboarding': 'from src.ui.onboarding',
            
            # 簡化組件
            'from ..simplified': 'from src.ui.simplified',
            'from ...ui.simplified': 'from src.ui.simplified',
            
            # 策略適配器
            'from ...strategies.': 'from src.strategies.',
            'from ..strategies.': 'from src.strategies.',
            
            # 知識庫
            'from ...knowledge_base': 'from src.knowledge_base',
            'from ..knowledge_base': 'from src.knowledge_base',
            
            # 模型管理
            'from ...models.': 'from src.models.',
            'from ..models.': 'from src.models.',
            
            # 數據管理
            'from ...data.': 'from src.data.',
            'from ..data.': 'from src.data.',
            
            # API路由
            'from ...api.': 'from src.api.',
            'from ..api.': 'from src.api.',
        }
        
        # 應用轉換
        converted = relative_import
        for old_pattern, new_pattern in conversion_map.items():
            if old_pattern in converted:
                converted = converted.replace(old_pattern, new_pattern)
                break
        
        return converted
    
    def fix_file(self, file_path: str) -> bool:
        """修復單個文件的相對導入"""
        relative_imports = self.find_relative_imports(file_path)
        
        if not relative_imports:
            return True
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixes_in_file = []
            
            # 逐行處理相對導入
            for line_num, original_line, import_part in relative_imports:
                # 轉換相對導入為絕對導入
                converted_line = self.convert_relative_to_absolute(original_line, file_path)
                
                if converted_line != original_line:
                    content = content.replace(original_line, converted_line)
                    fixes_in_file.append({
                        'line': line_num,
                        'original': original_line,
                        'converted': converted_line
                    })
            
            # 如果有修改，寫回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.fixes_applied.append({
                    'file': file_path,
                    'fixes': fixes_in_file
                })
                
                logger.info(f"✅ 修復文件: {file_path} ({len(fixes_in_file)} 個導入)")
                return True
            
        except Exception as e:
            logger.error(f"修復文件失敗 {file_path}: {e}")
            self.errors.append(f"{file_path}: {str(e)}")
            return False
        
        return True
    
    def add_error_handling(self, file_path: str):
        """為文件添加錯誤處理機制"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 檢查是否已經有try-except包裝
            if 'try:' in content and 'except ImportError:' in content:
                return
            
            # 找到導入語句的位置
            import_lines = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if line.strip().startswith('from src.') and 'import' in line:
                    import_lines.append(i)
            
            if import_lines:
                # 為導入添加try-except包裝
                # 這裡可以根據需要實現更複雜的錯誤處理邏輯
                pass
                
        except Exception as e:
            logger.error(f"添加錯誤處理失敗 {file_path}: {e}")
    
    def run_fixes(self) -> Dict:
        """運行所有修復"""
        logger.info("🔧 開始修復相對導入問題...")
        
        # 掃描文件
        python_files = self.scan_files()
        logger.info(f"📁 找到 {len(python_files)} 個Python文件")
        
        # 修復每個文件
        success_count = 0
        for file_path in python_files:
            if self.fix_file(file_path):
                success_count += 1
        
        # 生成報告
        report = {
            'total_files': len(python_files),
            'success_count': success_count,
            'fixes_applied': len(self.fixes_applied),
            'errors': len(self.errors),
            'details': {
                'fixes': self.fixes_applied,
                'errors': self.errors
            }
        }
        
        return report

def main():
    """主函數"""
    fixer = RelativeImportFixer()
    report = fixer.run_fixes()
    
    print("\n📊 修復報告:")
    print(f"總文件數: {report['total_files']}")
    print(f"成功處理: {report['success_count']}")
    print(f"應用修復: {report['fixes_applied']}")
    print(f"錯誤數量: {report['errors']}")
    
    if report['details']['fixes']:
        print("\n✅ 修復詳情:")
        for fix in report['details']['fixes']:
            print(f"  📄 {fix['file']}: {len(fix['fixes'])} 個修復")
    
    if report['details']['errors']:
        print("\n❌ 錯誤詳情:")
        for error in report['details']['errors']:
            print(f"  ⚠️ {error}")
    
    return 0 if report['errors'] == 0 else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
