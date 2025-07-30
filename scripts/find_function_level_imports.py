#!/usr/bin/env python3
"""
Function-Level Import Finder

This script systematically identifies all function-level import statements
across the codebase to support performance optimization efforts.

Based on the performance optimization requirements to identify and relocate
the 36 function-level imports mentioned in docs/性能優化建議.md.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
import json


@dataclass
class ImportInfo:
    """Information about a function-level import"""
    file_path: str
    function_name: str
    line_number: int
    import_statement: str
    import_type: str  # 'import' or 'from_import'
    module_name: str
    imported_names: List[str]


class FunctionLevelImportFinder:
    """Finds all function-level imports in Python files"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.function_imports: List[ImportInfo] = []
        self.stats = {
            'total_files_scanned': 0,
            'files_with_function_imports': 0,
            'total_function_imports': 0,
            'import_types': {},
            'most_common_modules': {},
        }
    
    def find_all_function_imports(self) -> List[ImportInfo]:
        """Find all function-level imports in the project"""
        print("🔍 Scanning for function-level imports...")
        
        # Scan all Python files in src/ directory
        src_dir = self.project_root / "src"
        if not src_dir.exists():
            print(f"❌ Source directory not found: {src_dir}")
            return []
        
        for py_file in src_dir.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            self.stats['total_files_scanned'] += 1
            file_imports = self._analyze_file(py_file)
            
            if file_imports:
                self.stats['files_with_function_imports'] += 1
                self.function_imports.extend(file_imports)
        
        self._update_stats()
        return self.function_imports
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            '__pycache__',
            '.git',
            '.pytest_cache',
            '.venv',
            'venv',
            'env',
            '.tox',
            'build',
            'dist',
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _analyze_file(self, file_path: Path) -> List[ImportInfo]:
        """Analyze a single Python file for function-level imports"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            return self._find_function_imports_in_ast(tree, file_path, content)
            
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"⚠️  Skipping {file_path}: {e}")
            return []
        except Exception as e:
            print(f"❌ Error analyzing {file_path}: {e}")
            return []
    
    def _find_function_imports_in_ast(self, tree: ast.AST, file_path: Path, content: str) -> List[ImportInfo]:
        """Find function-level imports in AST"""
        imports = []
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_imports = self._find_imports_in_function(node, file_path, lines)
                imports.extend(function_imports)
        
        return imports
    
    def _find_imports_in_function(self, func_node: ast.AST, file_path: Path, lines: List[str]) -> List[ImportInfo]:
        """Find imports within a specific function"""
        imports = []
        
        for node in ast.walk(func_node):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Skip if this is the function definition itself
                if node == func_node:
                    continue
                
                import_info = self._create_import_info(node, func_node, file_path, lines)
                if import_info:
                    imports.append(import_info)
        
        return imports
    
    def _create_import_info(self, import_node: ast.AST, func_node: ast.AST, 
                           file_path: Path, lines: List[str]) -> ImportInfo:
        """Create ImportInfo object from AST nodes"""
        try:
            line_num = import_node.lineno
            import_statement = lines[line_num - 1].strip() if line_num <= len(lines) else ""
            
            if isinstance(import_node, ast.Import):
                module_names = [alias.name for alias in import_node.names]
                return ImportInfo(
                    file_path=str(file_path.relative_to(self.project_root)),
                    function_name=func_node.name,
                    line_number=line_num,
                    import_statement=import_statement,
                    import_type='import',
                    module_name=module_names[0] if module_names else '',
                    imported_names=module_names
                )
            
            elif isinstance(import_node, ast.ImportFrom):
                module_name = import_node.module or ''
                imported_names = [alias.name for alias in import_node.names]
                return ImportInfo(
                    file_path=str(file_path.relative_to(self.project_root)),
                    function_name=func_node.name,
                    line_number=line_num,
                    import_statement=import_statement,
                    import_type='from_import',
                    module_name=module_name,
                    imported_names=imported_names
                )
        
        except Exception as e:
            print(f"⚠️  Error creating import info: {e}")
            return None
    
    def _update_stats(self):
        """Update statistics"""
        self.stats['total_function_imports'] = len(self.function_imports)
        
        # Count import types
        for imp in self.function_imports:
            self.stats['import_types'][imp.import_type] = \
                self.stats['import_types'].get(imp.import_type, 0) + 1
        
        # Count most common modules
        for imp in self.function_imports:
            module = imp.module_name
            self.stats['most_common_modules'][module] = \
                self.stats['most_common_modules'].get(module, 0) + 1
    
    def print_report(self):
        """Print detailed report of findings"""
        print("\n" + "="*80)
        print("📊 FUNCTION-LEVEL IMPORT ANALYSIS REPORT")
        print("="*80)
        
        print(f"\n📈 Statistics:")
        print(f"  • Total files scanned: {self.stats['total_files_scanned']}")
        print(f"  • Files with function imports: {self.stats['files_with_function_imports']}")
        print(f"  • Total function-level imports: {self.stats['total_function_imports']}")
        
        if self.stats['import_types']:
            print(f"\n📋 Import Types:")
            for import_type, count in self.stats['import_types'].items():
                print(f"  • {import_type}: {count}")
        
        if self.stats['most_common_modules']:
            print(f"\n🔝 Most Common Modules (Top 10):")
            sorted_modules = sorted(self.stats['most_common_modules'].items(), 
                                  key=lambda x: x[1], reverse=True)[:10]
            for module, count in sorted_modules:
                print(f"  • {module}: {count} imports")
        
        print(f"\n📝 Detailed Import List:")
        print("-" * 80)
        
        # Group by file for better readability
        by_file = {}
        for imp in self.function_imports:
            if imp.file_path not in by_file:
                by_file[imp.file_path] = []
            by_file[imp.file_path].append(imp)
        
        for file_path, imports in sorted(by_file.items()):
            print(f"\n📁 {file_path}")
            for imp in sorted(imports, key=lambda x: x.line_number):
                print(f"  Line {imp.line_number:3d} | {imp.function_name}() | {imp.import_statement}")
    
    def save_results(self, output_file: str = "function_imports_analysis.json"):
        """Save results to JSON file"""
        output_path = self.project_root / output_file
        
        # Convert ImportInfo objects to dictionaries
        results = {
            'stats': self.stats,
            'imports': [
                {
                    'file_path': imp.file_path,
                    'function_name': imp.function_name,
                    'line_number': imp.line_number,
                    'import_statement': imp.import_statement,
                    'import_type': imp.import_type,
                    'module_name': imp.module_name,
                    'imported_names': imp.imported_names
                }
                for imp in self.function_imports
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_path}")


def main():
    """Main function"""
    project_root = os.getcwd()
    
    print("🚀 Function-Level Import Finder")
    print(f"📂 Project root: {project_root}")
    
    finder = FunctionLevelImportFinder(project_root)
    imports = finder.find_all_function_imports()
    
    finder.print_report()
    finder.save_results()
    
    print(f"\n✅ Analysis complete! Found {len(imports)} function-level imports.")
    
    if len(imports) > 0:
        print("\n🎯 Next Steps:")
        print("1. Review the detailed import list above")
        print("2. Prioritize imports from src.ai.*, src.ui.components.*, src.core.*")
        print("3. Implement import caching using @st.cache_resource")
        print("4. Move imports to file headers where possible")
        print("5. Run performance tests to measure improvements")


if __name__ == "__main__":
    main()
