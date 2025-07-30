#!/usr/bin/env python3
"""
Function-Level Import Optimizer

This script implements Phase 1 of the performance optimization plan by:
1. Creating cached import functions using @st.cache_resource
2. Relocating function-level imports to file headers where possible
3. Implementing import caching for heavy modules

Based on the performance optimization requirements to optimize the 500 
function-level imports identified in the codebase analysis.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json
import re
from dataclasses import dataclass


@dataclass
class ImportOptimization:
    """Represents an import optimization action"""
    file_path: str
    original_line: int
    function_name: str
    import_statement: str
    module_name: str
    imported_names: List[str]
    optimization_type: str  # 'cache', 'header', 'skip'
    reason: str


class FunctionImportOptimizer:
    """Optimizes function-level imports for performance"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.optimizations: List[ImportOptimization] = []
        
        # Priority modules for caching (heavy imports)
        self.cache_priority_modules = {
            'src.ai.self_learning_agent',
            'src.core.integrated_feature_calculator', 
            'src.ui.components.interactive_charts',
            'src.core.ai_model_management_service',
            'src.core.data_management_service',
            'src.core.backtest.service',
            'src.ui.components.enhanced_data_visualization',
            'src.ui.components.enhanced_data_viewer',
            'tensorflow',
            'torch',
            'sklearn',
            'plotly',
            'talib',
            'optuna'
        }
        
        # Modules that should be moved to headers (lightweight)
        self.header_modules = {
            'json', 'os', 're', 'time', 'datetime', 'uuid', 'hashlib',
            'threading', 'math', 'secrets', 'traceback', 'argparse',
            'pathlib', 'shutil', 'socket', 'random'
        }
        
        # Modules to skip optimization (conditional imports)
        self.skip_modules = {
            'importlib', 'sys'  # Dynamic imports
        }
    
    def load_analysis_results(self, analysis_file: str = "function_imports_analysis.json") -> List[Dict]:
        """Load the function import analysis results"""
        analysis_path = self.project_root / analysis_file
        
        if not analysis_path.exists():
            print(f"❌ Analysis file not found: {analysis_path}")
            return []
        
        with open(analysis_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('imports', [])
    
    def analyze_optimizations(self, imports: List[Dict]) -> List[ImportOptimization]:
        """Analyze imports and determine optimization strategies"""
        optimizations = []
        
        for imp in imports:
            module_name = imp['module_name']
            optimization = self._determine_optimization_strategy(imp)
            optimizations.append(optimization)
        
        return optimizations
    
    def _determine_optimization_strategy(self, imp: Dict) -> ImportOptimization:
        """Determine the best optimization strategy for an import"""
        module_name = imp['module_name']
        file_path = imp['file_path']
        
        # Check if it's a priority module for caching
        if any(priority in module_name for priority in self.cache_priority_modules):
            return ImportOptimization(
                file_path=file_path,
                original_line=imp['line_number'],
                function_name=imp['function_name'],
                import_statement=imp['import_statement'],
                module_name=module_name,
                imported_names=imp['imported_names'],
                optimization_type='cache',
                reason=f"Heavy module {module_name} should be cached"
            )
        
        # Check if it should be moved to header
        elif module_name in self.header_modules:
            return ImportOptimization(
                file_path=file_path,
                original_line=imp['line_number'],
                function_name=imp['function_name'],
                import_statement=imp['import_statement'],
                module_name=module_name,
                imported_names=imp['imported_names'],
                optimization_type='header',
                reason=f"Lightweight module {module_name} can be moved to header"
            )
        
        # Check if it should be skipped
        elif any(skip in module_name for skip in self.skip_modules):
            return ImportOptimization(
                file_path=file_path,
                original_line=imp['line_number'],
                function_name=imp['function_name'],
                import_statement=imp['import_statement'],
                module_name=module_name,
                imported_names=imp['imported_names'],
                optimization_type='skip',
                reason=f"Dynamic import {module_name} should remain in function"
            )
        
        # Default to caching for src.* modules
        elif module_name.startswith('src.'):
            return ImportOptimization(
                file_path=file_path,
                original_line=imp['line_number'],
                function_name=imp['function_name'],
                import_statement=imp['import_statement'],
                module_name=module_name,
                imported_names=imp['imported_names'],
                optimization_type='cache',
                reason=f"Internal module {module_name} should be cached"
            )
        
        # Default to header for external modules
        else:
            return ImportOptimization(
                file_path=file_path,
                original_line=imp['line_number'],
                function_name=imp['function_name'],
                import_statement=imp['import_statement'],
                module_name=module_name,
                imported_names=imp['imported_names'],
                optimization_type='header',
                reason=f"External module {module_name} can be moved to header"
            )
    
    def generate_cache_functions(self, optimizations: List[ImportOptimization]) -> Dict[str, str]:
        """Generate cached import functions for heavy modules"""
        cache_functions = {}
        
        # Group by module for deduplication
        modules_to_cache = {}
        for opt in optimizations:
            if opt.optimization_type == 'cache':
                module = opt.module_name
                if module not in modules_to_cache:
                    modules_to_cache[module] = set()
                modules_to_cache[module].update(opt.imported_names)
        
        # Generate cache functions
        for module, imported_names in modules_to_cache.items():
            cache_func_name = self._generate_cache_function_name(module)
            
            # Create the cache function
            if len(imported_names) == 1 and list(imported_names)[0] == module.split('.')[-1]:
                # Simple import: from module import Class -> return Class
                class_name = list(imported_names)[0]
                cache_function = f'''@st.cache_resource
def {cache_func_name}():
    """Cached import for {module}"""
    try:
        from {module} import {class_name}
        return {class_name}
    except ImportError as e:
        logger.warning(f"Failed to import {module}: {{e}}")
        return None
'''
            else:
                # Multiple imports: return dictionary
                imports_str = ', '.join(imported_names)
                cache_function = f'''@st.cache_resource
def {cache_func_name}():
    """Cached import for {module}"""
    try:
        from {module} import {imports_str}
        return {{{', '.join(f"'{name}': {name}" for name in imported_names)}}}
    except ImportError as e:
        logger.warning(f"Failed to import {module}: {{e}}")
        return None
'''
            
            cache_functions[module] = cache_function
        
        return cache_functions
    
    def _generate_cache_function_name(self, module_name: str) -> str:
        """Generate a cache function name from module name"""
        # Convert module path to function name
        parts = module_name.replace('src.', '').split('.')
        name = '_'.join(parts)
        return f"get_cached_{name}"
    
    def print_optimization_plan(self, optimizations: List[ImportOptimization]):
        """Print the optimization plan"""
        print("\n" + "="*80)
        print("🚀 IMPORT OPTIMIZATION PLAN")
        print("="*80)
        
        # Count by optimization type
        counts = {}
        for opt in optimizations:
            counts[opt.optimization_type] = counts.get(opt.optimization_type, 0) + 1
        
        print(f"\n📊 Optimization Summary:")
        print(f"  • Cache optimizations: {counts.get('cache', 0)}")
        print(f"  • Header relocations: {counts.get('header', 0)}")
        print(f"  • Skipped (conditional): {counts.get('skip', 0)}")
        print(f"  • Total optimizations: {len(optimizations)}")
        
        # Group by file for detailed view
        by_file = {}
        for opt in optimizations:
            if opt.file_path not in by_file:
                by_file[opt.file_path] = []
            by_file[opt.file_path].append(opt)
        
        print(f"\n📝 Detailed Optimization Plan:")
        print("-" * 80)
        
        for file_path, opts in sorted(by_file.items()):
            if len(opts) > 0:  # Only show files with optimizations
                print(f"\n📁 {file_path} ({len(opts)} optimizations)")
                for opt in sorted(opts, key=lambda x: x.original_line):
                    icon = "🔄" if opt.optimization_type == "cache" else "⬆️" if opt.optimization_type == "header" else "⏭️"
                    print(f"  {icon} Line {opt.original_line:3d} | {opt.function_name}() | {opt.optimization_type.upper()}")
                    print(f"      {opt.import_statement}")
                    print(f"      → {opt.reason}")
    
    def save_optimization_plan(self, optimizations: List[ImportOptimization], 
                              output_file: str = "import_optimization_plan.json"):
        """Save optimization plan to JSON file"""
        output_path = self.project_root / output_file
        
        # Convert to serializable format
        plan_data = {
            'summary': {
                'total_optimizations': len(optimizations),
                'cache_optimizations': len([o for o in optimizations if o.optimization_type == 'cache']),
                'header_relocations': len([o for o in optimizations if o.optimization_type == 'header']),
                'skipped': len([o for o in optimizations if o.optimization_type == 'skip'])
            },
            'optimizations': [
                {
                    'file_path': opt.file_path,
                    'original_line': opt.original_line,
                    'function_name': opt.function_name,
                    'import_statement': opt.import_statement,
                    'module_name': opt.module_name,
                    'imported_names': opt.imported_names,
                    'optimization_type': opt.optimization_type,
                    'reason': opt.reason
                }
                for opt in optimizations
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(plan_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Optimization plan saved to: {output_path}")


def main():
    """Main function"""
    project_root = os.getcwd()
    
    print("🚀 Function Import Optimizer - Phase 1")
    print(f"📂 Project root: {project_root}")
    
    optimizer = FunctionImportOptimizer(project_root)
    
    # Load analysis results
    print("\n📊 Loading import analysis results...")
    imports = optimizer.load_analysis_results()
    
    if not imports:
        print("❌ No import analysis results found. Run find_function_level_imports.py first.")
        return
    
    print(f"✅ Loaded {len(imports)} function-level imports")
    
    # Analyze optimizations
    print("\n🔍 Analyzing optimization strategies...")
    optimizations = optimizer.analyze_optimizations(imports)
    
    # Generate cache functions
    print("\n⚡ Generating cache functions...")
    cache_functions = optimizer.generate_cache_functions(optimizations)
    
    print(f"✅ Generated {len(cache_functions)} cache functions")
    
    # Print optimization plan
    optimizer.print_optimization_plan(optimizations)
    
    # Save optimization plan
    optimizer.save_optimization_plan(optimizations)
    
    print(f"\n🎯 Next Steps:")
    print("1. Review the optimization plan above")
    print("2. Run the implementation script to apply optimizations")
    print("3. Test the optimized code for functionality")
    print("4. Measure performance improvements")
    print("5. Update Todo_list.md with progress")


if __name__ == "__main__":
    main()
