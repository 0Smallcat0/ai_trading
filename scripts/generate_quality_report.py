#!/usr/bin/env python3
"""
品質報告生成腳本

此腳本生成詳細的程式碼品質報告，包括：
- Pylint 評分分析
- 測試覆蓋率統計
- 檔案大小檢查
- 安全掃描結果
- 趨勢分析

Example:
    >>> python scripts/generate_quality_report.py
"""

import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from radon.complexity import cc_visit
from radon.metrics import mi_visit, h_visit


class QualityReportGenerator:
    """品質報告生成器.
    
    生成詳細的程式碼品質報告，包括各種品質指標的分析和趨勢。
    """

    def __init__(self, output_dir: str = "docs/reports"):
        """初始化報告生成器.
        
        Args:
            output_dir: 報告輸出目錄
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now()

    def generate_report(self) -> None:
        """生成完整的品質報告.

        Example:
            >>> generator = QualityReportGenerator()
            >>> generator.generate_report()
        """
        print("🚀 開始生成增強版品質報告...")

        # 收集品質數據
        quality_data = self._collect_quality_data()

        # 載入歷史數據
        historical_data = self._load_historical_data()

        # 生成趨勢圖表
        charts = self._generate_trend_charts(quality_data, historical_data)

        # 生成依賴關係圖
        dependency_graph = self._generate_dependency_graph(
            quality_data.get('code_metrics', {}).get('dependencies', {})
        )
        if dependency_graph:
            charts['dependency_graph'] = dependency_graph

        # 生成可操作建議
        recommendations = self._generate_actionable_recommendations(quality_data)
        quality_data['recommendations'] = recommendations
        quality_data['charts'] = charts

        # 生成 HTML 報告
        html_report = self._generate_html_report(quality_data)

        # 保存報告
        report_path = self.output_dir / f"quality-report-{self.timestamp.strftime('%Y%m%d-%H%M%S')}.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_report)

        # 保存原始數據
        data_path = self.output_dir / f"quality-data-{self.timestamp.strftime('%Y%m%d-%H%M%S')}.json"
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(quality_data, f, indent=2, ensure_ascii=False, default=str)

        # 創建最新報告的符號連結
        latest_path = self.output_dir / "quality-report-latest.html"
        if latest_path.exists():
            latest_path.unlink()
        try:
            latest_path.symlink_to(report_path.name)
        except OSError:
            # Windows 可能不支援符號連結，直接複製
            import shutil
            shutil.copy2(report_path, latest_path)

        print(f"✅ 增強版品質報告已生成: {report_path}")
        print(f"📊 趨勢圖表已生成: {len(charts)} 個")
        print(f"💡 改進建議已生成: {len(recommendations)} 個")

    def _collect_quality_data(self) -> Dict[str, Any]:
        """收集品質數據.
        
        Returns:
            Dict[str, Any]: 品質數據字典
        """
        data = {
            "timestamp": self.timestamp.isoformat(),
            "pylint_scores": self._get_pylint_scores(),
            "file_sizes": self._get_file_sizes(),
            "test_coverage": self._get_test_coverage(),
            "security_issues": self._get_security_issues(),
            "dependency_vulnerabilities": self._get_dependency_vulnerabilities(),
            "code_metrics": self._get_code_metrics()
        }
        
        return data

    def _get_pylint_scores(self) -> Dict[str, float]:
        """獲取 Pylint 評分.
        
        Returns:
            Dict[str, float]: Pylint 評分字典
        """
        scores = {}
        
        # 檢查核心模組
        try:
            result = subprocess.run([
                "pylint", "src/risk_management/", "--output-format=text"
            ], capture_output=True, text=True, timeout=60)
            
            score_match = re.search(r"Your code has been rated at ([\d.]+)/10", result.stdout)
            if score_match:
                scores["core_modules"] = float(score_match.group(1))
        except Exception as e:
            print(f"⚠️ 無法獲取核心模組 Pylint 評分: {e}")
            scores["core_modules"] = 0.0

        # 檢查一般模組
        modules = ["src/api/", "src/ui/", "src/core/"]
        for module in modules:
            if os.path.exists(module):
                try:
                    result = subprocess.run([
                        "pylint", module, "--output-format=text"
                    ], capture_output=True, text=True, timeout=60)
                    
                    score_match = re.search(r"Your code has been rated at ([\d.]+)/10", result.stdout)
                    if score_match:
                        module_name = module.replace("src/", "").replace("/", "")
                        scores[module_name] = float(score_match.group(1))
                except Exception as e:
                    print(f"⚠️ 無法獲取 {module} Pylint 評分: {e}")
        
        return scores

    def _get_file_sizes(self) -> Dict[str, int]:
        """獲取檔案大小統計.
        
        Returns:
            Dict[str, int]: 檔案大小統計
        """
        file_sizes = {}
        violations = []
        
        for root, dirs, files in os.walk("src/"):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            line_count = len(f.readlines())
                        
                        file_sizes[filepath] = line_count
                        
                        if line_count > 300:
                            violations.append((filepath, line_count))
                    except Exception as e:
                        print(f"⚠️ 無法讀取檔案 {filepath}: {e}")
        
        return {
            "file_sizes": file_sizes,
            "violations": violations,
            "total_files": len(file_sizes),
            "max_size": max(file_sizes.values()) if file_sizes else 0,
            "avg_size": sum(file_sizes.values()) / len(file_sizes) if file_sizes else 0
        }

    def _get_test_coverage(self) -> Dict[str, Any]:
        """獲取測試覆蓋率.
        
        Returns:
            Dict[str, Any]: 測試覆蓋率數據
        """
        try:
            # 嘗試讀取覆蓋率 XML 報告
            coverage_file = Path("coverage.xml")
            if coverage_file.exists():
                # 這裡可以解析 XML 檔案獲取詳細覆蓋率
                return {"status": "available", "file": str(coverage_file)}
            else:
                return {"status": "not_available", "reason": "coverage.xml not found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_security_issues(self) -> Dict[str, Any]:
        """獲取安全問題.
        
        Returns:
            Dict[str, Any]: 安全問題數據
        """
        try:
            bandit_file = Path("bandit-report.json")
            if bandit_file.exists():
                with open(bandit_file, 'r', encoding='utf-8') as f:
                    bandit_data = json.load(f)
                
                return {
                    "total_issues": len(bandit_data.get("results", [])),
                    "high_severity": len([r for r in bandit_data.get("results", []) 
                                        if r.get("issue_severity") == "HIGH"]),
                    "medium_severity": len([r for r in bandit_data.get("results", []) 
                                          if r.get("issue_severity") == "MEDIUM"]),
                    "low_severity": len([r for r in bandit_data.get("results", []) 
                                       if r.get("issue_severity") == "LOW"])
                }
            else:
                return {"status": "not_available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_dependency_vulnerabilities(self) -> Dict[str, Any]:
        """獲取依賴漏洞.
        
        Returns:
            Dict[str, Any]: 依賴漏洞數據
        """
        try:
            safety_file = Path("safety-report.json")
            if safety_file.exists():
                with open(safety_file, 'r', encoding='utf-8') as f:
                    safety_data = json.load(f)
                
                return {
                    "total_vulnerabilities": len(safety_data),
                    "vulnerabilities": safety_data
                }
            else:
                return {"status": "not_available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_code_metrics(self) -> Dict[str, Any]:
        """獲取程式碼指標.

        Returns:
            Dict[str, Any]: 程式碼指標數據
        """
        metrics = {
            "total_lines": 0,
            "total_files": 0,
            "modules": {},
            "complexity": self._get_complexity_metrics(),
            "dependencies": self._get_dependency_analysis(),
            "maintainability": self._get_maintainability_index()
        }

        for root, dirs, files in os.walk("src/"):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            lines = len(f.readlines())

                        metrics["total_lines"] += lines
                        metrics["total_files"] += 1

                        # 按模組統計
                        module = root.replace("src/", "").split("/")[0]
                        if module not in metrics["modules"]:
                            metrics["modules"][module] = {"files": 0, "lines": 0}

                        metrics["modules"][module]["files"] += 1
                        metrics["modules"][module]["lines"] += lines

                    except Exception as e:
                        print(f"⚠️ 無法讀取檔案 {filepath}: {e}")

        return metrics

    def _get_complexity_metrics(self) -> Dict[str, Any]:
        """獲取程式碼複雜度指標.

        Returns:
            Dict[str, Any]: 複雜度指標數據
        """
        complexity_data = {
            "average_complexity": 0,
            "max_complexity": 0,
            "high_complexity_functions": [],
            "complexity_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0},
            "files": {}
        }

        total_complexity = 0
        function_count = 0

        for root, dirs, files in os.walk("src/"):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # 計算循環複雜度
                        complexity_results = cc_visit(content)
                        file_complexities = []

                        for result in complexity_results:
                            complexity = result.complexity
                            total_complexity += complexity
                            function_count += 1

                            file_complexities.append({
                                "name": result.name,
                                "complexity": complexity,
                                "line": result.lineno
                            })

                            # 記錄高複雜度函數
                            if complexity > 10:
                                complexity_data["high_complexity_functions"].append({
                                    "file": filepath,
                                    "function": result.name,
                                    "complexity": complexity,
                                    "line": result.lineno
                                })

                            # 更新最大複雜度
                            if complexity > complexity_data["max_complexity"]:
                                complexity_data["max_complexity"] = complexity

                            # 複雜度分級 (A=1-5, B=6-10, C=11-20, D=21-30, E=31-40, F=41+)
                            if complexity <= 5:
                                complexity_data["complexity_distribution"]["A"] += 1
                            elif complexity <= 10:
                                complexity_data["complexity_distribution"]["B"] += 1
                            elif complexity <= 20:
                                complexity_data["complexity_distribution"]["C"] += 1
                            elif complexity <= 30:
                                complexity_data["complexity_distribution"]["D"] += 1
                            elif complexity <= 40:
                                complexity_data["complexity_distribution"]["E"] += 1
                            else:
                                complexity_data["complexity_distribution"]["F"] += 1

                        complexity_data["files"][filepath] = {
                            "functions": file_complexities,
                            "average": sum(c["complexity"] for c in file_complexities) / len(file_complexities) if file_complexities else 0
                        }

                    except Exception as e:
                        print(f"⚠️ 無法分析檔案複雜度 {filepath}: {e}")

        if function_count > 0:
            complexity_data["average_complexity"] = total_complexity / function_count

        return complexity_data

    def _get_dependency_analysis(self) -> Dict[str, Any]:
        """分析模組間依賴關係.

        Returns:
            Dict[str, Any]: 依賴關係數據
        """
        dependencies = {
            "internal_imports": {},
            "external_imports": {},
            "circular_dependencies": [],
            "dependency_graph": {},
            "coupling_metrics": {}
        }

        # 收集所有 Python 檔案的導入
        for root, dirs, files in os.walk("src/"):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    module_name = filepath.replace("src/", "").replace("/", ".").replace(".py", "")

                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        tree = ast.parse(content)
                        imports = self._extract_imports(tree)

                        dependencies["internal_imports"][module_name] = imports["internal"]
                        dependencies["external_imports"][module_name] = imports["external"]

                    except Exception as e:
                        print(f"⚠️ 無法分析依賴關係 {filepath}: {e}")

        # 檢測循環依賴
        dependencies["circular_dependencies"] = self._detect_circular_dependencies(
            dependencies["internal_imports"]
        )

        # 計算耦合度指標
        dependencies["coupling_metrics"] = self._calculate_coupling_metrics(
            dependencies["internal_imports"]
        )

        return dependencies

    def _extract_imports(self, tree: ast.AST) -> Dict[str, List[str]]:
        """提取 AST 中的導入語句.

        Args:
            tree: AST 樹

        Returns:
            Dict[str, List[str]]: 內部和外部導入列表
        """
        imports = {"internal": [], "external": []}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("src."):
                        imports["internal"].append(alias.name)
                    else:
                        imports["external"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("src."):
                    imports["internal"].append(node.module)
                elif node.module:
                    imports["external"].append(node.module)

        return imports

    def _detect_circular_dependencies(self, internal_imports: Dict[str, List[str]]) -> List[List[str]]:
        """檢測循環依賴.

        Args:
            internal_imports: 內部導入字典

        Returns:
            List[List[str]]: 循環依賴列表
        """
        circular_deps = []

        def has_path(start: str, end: str, visited: Set[str]) -> bool:
            if start == end:
                return True
            if start in visited:
                return False

            visited.add(start)
            for dep in internal_imports.get(start, []):
                if has_path(dep, end, visited.copy()):
                    return True
            return False

        # 檢查每對模組是否存在循環依賴
        modules = list(internal_imports.keys())
        for i, module_a in enumerate(modules):
            for module_b in modules[i+1:]:
                if (has_path(module_a, module_b, set()) and
                    has_path(module_b, module_a, set())):
                    circular_deps.append([module_a, module_b])

        return circular_deps

    def _calculate_coupling_metrics(self, internal_imports: Dict[str, List[str]]) -> Dict[str, Any]:
        """計算耦合度指標.

        Args:
            internal_imports: 內部導入字典

        Returns:
            Dict[str, Any]: 耦合度指標
        """
        metrics = {
            "afferent_coupling": {},  # 傳入耦合 (Ca)
            "efferent_coupling": {},  # 傳出耦合 (Ce)
            "instability": {},        # 不穩定性 (I = Ce / (Ca + Ce))
            "abstractness": {}        # 抽象度 (A)
        }

        modules = list(internal_imports.keys())

        # 計算傳出耦合 (Ce)
        for module in modules:
            metrics["efferent_coupling"][module] = len(internal_imports.get(module, []))

        # 計算傳入耦合 (Ca)
        for module in modules:
            ca = 0
            for other_module in modules:
                if module in internal_imports.get(other_module, []):
                    ca += 1
            metrics["afferent_coupling"][module] = ca

        # 計算不穩定性 (I)
        for module in modules:
            ca = metrics["afferent_coupling"][module]
            ce = metrics["efferent_coupling"][module]
            if ca + ce > 0:
                metrics["instability"][module] = ce / (ca + ce)
            else:
                metrics["instability"][module] = 0

        return metrics

    def _get_maintainability_index(self) -> Dict[str, Any]:
        """計算可維護性指標.

        Returns:
            Dict[str, Any]: 可維護性指標數據
        """
        maintainability_data = {
            "average_mi": 0,
            "files": {},
            "low_maintainability": []
        }

        total_mi = 0
        file_count = 0

        for root, dirs, files in os.walk("src/"):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # 計算可維護性指標
                        mi_results = mi_visit(content, multi=True)
                        if mi_results:
                            mi_score = mi_results[0].mi
                            total_mi += mi_score
                            file_count += 1

                            maintainability_data["files"][filepath] = mi_score

                            # 記錄低可維護性檔案 (MI < 20)
                            if mi_score < 20:
                                maintainability_data["low_maintainability"].append({
                                    "file": filepath,
                                    "mi_score": mi_score
                                })

                    except Exception as e:
                        print(f"⚠️ 無法計算可維護性指標 {filepath}: {e}")

        if file_count > 0:
            maintainability_data["average_mi"] = total_mi / file_count

        return maintainability_data

    def _load_historical_data(self) -> List[Dict[str, Any]]:
        """載入歷史品質數據.

        Returns:
            List[Dict[str, Any]]: 歷史數據列表
        """
        historical_data = []
        reports_dir = Path("docs/reports")

        if reports_dir.exists():
            for file_path in reports_dir.glob("quality-data-*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        historical_data.append(data)
                except Exception as e:
                    print(f"⚠️ 無法載入歷史數據 {file_path}: {e}")

        # 按時間排序
        historical_data.sort(key=lambda x: x.get('timestamp', ''))
        return historical_data

    def _generate_trend_charts(self, current_data: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """生成趨勢圖表.

        Args:
            current_data: 當前品質數據
            historical_data: 歷史品質數據

        Returns:
            Dict[str, str]: 圖表檔案路徑字典
        """
        charts = {}

        if len(historical_data) < 2:
            print("⚠️ 歷史數據不足，無法生成趨勢圖表")
            return charts

        # 準備數據
        dates = []
        pylint_scores = []
        complexity_scores = []
        maintainability_scores = []

        for data in historical_data:
            if 'timestamp' in data:
                dates.append(datetime.fromisoformat(data['timestamp']))

                # Pylint 評分
                pylint_data = data.get('pylint_scores', {})
                avg_pylint = sum(pylint_data.values()) / len(pylint_data) if pylint_data else 0
                pylint_scores.append(avg_pylint)

                # 複雜度評分
                complexity_data = data.get('code_metrics', {}).get('complexity', {})
                complexity_scores.append(complexity_data.get('average_complexity', 0))

                # 可維護性評分
                maintainability_data = data.get('code_metrics', {}).get('maintainability', {})
                maintainability_scores.append(maintainability_data.get('average_mi', 0))

        # 設置圖表樣式
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('程式碼品質趨勢分析', fontsize=16, fontweight='bold')

        # Pylint 評分趨勢
        axes[0, 0].plot(dates, pylint_scores, marker='o', linewidth=2, markersize=6)
        axes[0, 0].set_title('Pylint 評分趨勢')
        axes[0, 0].set_ylabel('評分')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axhline(y=8.5, color='orange', linestyle='--', alpha=0.7, label='目標線 (8.5)')
        axes[0, 0].legend()

        # 複雜度趨勢
        axes[0, 1].plot(dates, complexity_scores, marker='s', color='red', linewidth=2, markersize=6)
        axes[0, 1].set_title('平均循環複雜度趨勢')
        axes[0, 1].set_ylabel('複雜度')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].axhline(y=10, color='red', linestyle='--', alpha=0.7, label='警戒線 (10)')
        axes[0, 1].legend()

        # 可維護性趨勢
        axes[1, 0].plot(dates, maintainability_scores, marker='^', color='green', linewidth=2, markersize=6)
        axes[1, 0].set_title('可維護性指標趨勢')
        axes[1, 0].set_ylabel('MI 指標')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].axhline(y=20, color='orange', linestyle='--', alpha=0.7, label='警戒線 (20)')
        axes[1, 0].legend()

        # 複雜度分佈
        if current_data.get('code_metrics', {}).get('complexity', {}):
            complexity_dist = current_data['code_metrics']['complexity']['complexity_distribution']
            labels = list(complexity_dist.keys())
            values = list(complexity_dist.values())
            colors = ['green', 'lightgreen', 'yellow', 'orange', 'red', 'darkred']

            axes[1, 1].pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            axes[1, 1].set_title('當前複雜度分佈')

        plt.tight_layout()

        # 保存圖表
        charts_dir = Path("docs/reports/charts")
        charts_dir.mkdir(parents=True, exist_ok=True)

        chart_path = charts_dir / f"quality-trends-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()

        charts['trends'] = str(chart_path)

        return charts

    def _generate_dependency_graph(self, dependencies: Dict[str, Any]) -> str:
        """生成依賴關係圖.

        Args:
            dependencies: 依賴關係數據

        Returns:
            str: 圖表檔案路徑
        """
        try:
            import networkx as nx

            # 創建有向圖
            G = nx.DiGraph()

            # 添加節點和邊
            for module, deps in dependencies.get('internal_imports', {}).items():
                G.add_node(module)
                for dep in deps:
                    G.add_edge(module, dep)

            # 設置圖表
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(G, k=1, iterations=50)

            # 繪製節點
            nx.draw_networkx_nodes(G, pos, node_color='lightblue',
                                 node_size=1000, alpha=0.7)

            # 繪製邊
            nx.draw_networkx_edges(G, pos, edge_color='gray',
                                 arrows=True, arrowsize=20, alpha=0.5)

            # 繪製標籤
            labels = {node: node.split('.')[-1] for node in G.nodes()}
            nx.draw_networkx_labels(G, pos, labels, font_size=8)

            plt.title('模組依賴關係圖', fontsize=14, fontweight='bold')
            plt.axis('off')

            # 保存圖表
            charts_dir = Path("docs/reports/charts")
            charts_dir.mkdir(parents=True, exist_ok=True)

            graph_path = charts_dir / f"dependency-graph-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
            plt.savefig(graph_path, dpi=300, bbox_inches='tight')
            plt.close()

            return str(graph_path)

        except ImportError:
            print("⚠️ NetworkX 未安裝，無法生成依賴關係圖")
            return ""
        except Exception as e:
            print(f"⚠️ 生成依賴關係圖失敗: {e}")
            return ""

    def _generate_actionable_recommendations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成可操作的改進建議.

        Args:
            data: 品質數據

        Returns:
            List[Dict[str, Any]]: 改進建議列表
        """
        recommendations = []

        # 基於 Pylint 評分的建議
        pylint_scores = data.get('pylint_scores', {})
        for module, score in pylint_scores.items():
            if score < 8.5:
                recommendations.append({
                    'priority': 'high' if score < 7.0 else 'medium',
                    'category': 'code_quality',
                    'module': module,
                    'issue': f'Pylint 評分過低 ({score:.1f}/10)',
                    'action': f'檢查並修復 {module} 模組的程式碼品質問題',
                    'impact': '提升程式碼可讀性和維護性',
                    'effort': 'medium'
                })

        # 基於複雜度的建議
        complexity_data = data.get('code_metrics', {}).get('complexity', {})
        high_complexity_functions = complexity_data.get('high_complexity_functions', [])

        for func_data in high_complexity_functions[:5]:  # 只顯示前5個
            recommendations.append({
                'priority': 'high' if func_data['complexity'] > 20 else 'medium',
                'category': 'complexity',
                'module': func_data['file'],
                'issue': f'函數 {func_data["function"]} 複雜度過高 ({func_data["complexity"]})',
                'action': f'重構函數 {func_data["function"]}，拆分為更小的函數',
                'impact': '降低維護成本，提高測試覆蓋率',
                'effort': 'high' if func_data['complexity'] > 30 else 'medium'
            })

        # 基於可維護性的建議
        maintainability_data = data.get('code_metrics', {}).get('maintainability', {})
        low_maintainability = maintainability_data.get('low_maintainability', [])

        for file_data in low_maintainability[:3]:  # 只顯示前3個
            recommendations.append({
                'priority': 'medium',
                'category': 'maintainability',
                'module': file_data['file'],
                'issue': f'可維護性指標過低 ({file_data["mi_score"]:.1f})',
                'action': f'重構 {file_data["file"]}，簡化邏輯和減少複雜度',
                'impact': '提高程式碼可維護性和可讀性',
                'effort': 'medium'
            })

        # 基於依賴關係的建議
        dependencies = data.get('code_metrics', {}).get('dependencies', {})
        circular_deps = dependencies.get('circular_dependencies', [])

        for dep_pair in circular_deps[:3]:  # 只顯示前3個
            recommendations.append({
                'priority': 'high',
                'category': 'architecture',
                'module': f"{dep_pair[0]} ↔ {dep_pair[1]}",
                'issue': '存在循環依賴',
                'action': f'重構 {dep_pair[0]} 和 {dep_pair[1]} 之間的依賴關係',
                'impact': '提高模組獨立性，降低耦合度',
                'effort': 'high'
            })

        # 基於檔案大小的建議
        file_sizes = data.get('file_sizes', {})
        violations = file_sizes.get('violations', [])

        for filepath, line_count in violations[:3]:  # 只顯示前3個
            recommendations.append({
                'priority': 'medium',
                'category': 'file_size',
                'module': filepath,
                'issue': f'檔案過大 ({line_count} 行)',
                'action': f'拆分 {filepath} 為多個較小的檔案',
                'impact': '提高程式碼可讀性和模組化',
                'effort': 'medium'
            })

        # 按優先級排序
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))

        return recommendations

    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        """生成增強版 HTML 報告.

        Args:
            data: 品質數據

        Returns:
            str: HTML 報告內容
        """
        charts = data.get('charts', {})
        recommendations = data.get('recommendations', [])

        html = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>程式碼品質報告 (增強版) - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; font-size: 2.5em; }}
                h2 {{ color: #34495e; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-top: 40px; }}
                h3 {{ color: #2c3e50; margin-top: 25px; }}
                .metric {{ background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 5px solid #007bff; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .success {{ border-left-color: #28a745; background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); }}
                .warning {{ border-left-color: #ffc107; background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); }}
                .danger {{ border-left-color: #dc3545; background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); }}
                .score {{ font-size: 2.5em; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.1); }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }}
                th {{ background: linear-gradient(135deg, #495057 0%, #343a40 100%); color: white; font-weight: 600; }}
                tr:nth-child(even) {{ background-color: #f8f9fa; }}
                tr:hover {{ background-color: #e9ecef; }}
                .timestamp {{ color: #6c757d; font-size: 0.9em; text-align: center; margin-bottom: 30px; }}
                .chart-container {{ text-align: center; margin: 20px 0; }}
                .chart-container img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); }}
                .recommendation {{ background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
                .priority-high {{ border-left: 5px solid #dc3545; }}
                .priority-medium {{ border-left: 5px solid #ffc107; }}
                .priority-low {{ border-left: 5px solid #28a745; }}
                .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; text-transform: uppercase; }}
                .badge-high {{ background-color: #dc3545; color: white; }}
                .badge-medium {{ background-color: #ffc107; color: #212529; }}
                .badge-low {{ background-color: #28a745; color: white; }}
                .complexity-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
                .complexity-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #6c757d; }}
                .nav-tabs {{ display: flex; border-bottom: 2px solid #dee2e6; margin-bottom: 20px; }}
                .nav-tab {{ padding: 10px 20px; background: #f8f9fa; border: 1px solid #dee2e6; border-bottom: none; cursor: pointer; margin-right: 5px; border-radius: 8px 8px 0 0; }}
                .nav-tab.active {{ background: white; border-bottom: 2px solid white; }}
                .tab-content {{ display: none; }}
                .tab-content.active {{ display: block; }}
            </style>
            <script>
                function showTab(tabName) {{
                    // 隱藏所有標籤內容
                    var contents = document.getElementsByClassName('tab-content');
                    for (var i = 0; i < contents.length; i++) {{
                        contents[i].classList.remove('active');
                    }}

                    // 移除所有標籤的 active 類
                    var tabs = document.getElementsByClassName('nav-tab');
                    for (var i = 0; i < tabs.length; i++) {{
                        tabs[i].classList.remove('active');
                    }}

                    // 顯示選中的標籤內容
                    document.getElementById(tabName).classList.add('active');
                    event.target.classList.add('active');
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <h1>📊 程式碼品質報告 (增強版)</h1>
                <p class="timestamp">生成時間: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>

                <!-- 導航標籤 -->
                <div class="nav-tabs">
                    <div class="nav-tab active" onclick="showTab('overview')">總覽</div>
                    <div class="nav-tab" onclick="showTab('complexity')">複雜度分析</div>
                    <div class="nav-tab" onclick="showTab('dependencies')">依賴關係</div>
                    <div class="nav-tab" onclick="showTab('trends')">趨勢分析</div>
                    <div class="nav-tab" onclick="showTab('recommendations')">改進建議</div>
                </div>

                <!-- 總覽標籤 -->
                <div id="overview" class="tab-content active">
                    <h2>🎯 Pylint 評分</h2>
                    {self._generate_pylint_section(data.get('pylint_scores', {}))}

                    <h2>📏 檔案大小檢查</h2>
                    {self._generate_file_size_section(data.get('file_sizes', {}))}

                    <h2>🧪 測試覆蓋率</h2>
                    {self._generate_coverage_section(data.get('test_coverage', {}))}

                    <h2>🔒 安全檢查</h2>
                    {self._generate_security_section(data.get('security_issues', {}), data.get('dependency_vulnerabilities', {}))}

                    <h2>📈 基本程式碼指標</h2>
                    {self._generate_basic_metrics_section(data.get('code_metrics', {}))}
                </div>

                <!-- 複雜度分析標籤 -->
                <div id="complexity" class="tab-content">
                    <h2>🔍 程式碼複雜度分析</h2>
                    {self._generate_complexity_section(data.get('code_metrics', {}).get('complexity', {}))}

                    <h2>🛠️ 可維護性分析</h2>
                    {self._generate_maintainability_section(data.get('code_metrics', {}).get('maintainability', {}))}
                </div>

                <!-- 依賴關係標籤 -->
                <div id="dependencies" class="tab-content">
                    <h2>🔗 模組依賴關係分析</h2>
                    {self._generate_dependency_section(data.get('code_metrics', {}).get('dependencies', {}), charts.get('dependency_graph', ''))}
                </div>

                <!-- 趨勢分析標籤 -->
                <div id="trends" class="tab-content">
                    <h2>📈 品質趨勢分析</h2>
                    {self._generate_trends_section(charts.get('trends', ''))}
                </div>

                <!-- 改進建議標籤 -->
                <div id="recommendations" class="tab-content">
                    <h2>💡 可操作改進建議</h2>
                    {self._generate_recommendations_section(recommendations)}
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _generate_complexity_section(self, complexity_data: Dict[str, Any]) -> str:
        """生成複雜度分析區段."""
        if not complexity_data:
            return '<div class="metric warning">⚠️ 無複雜度分析數據</div>'

        avg_complexity = complexity_data.get('average_complexity', 0)
        max_complexity = complexity_data.get('max_complexity', 0)
        high_complexity_functions = complexity_data.get('high_complexity_functions', [])
        complexity_dist = complexity_data.get('complexity_distribution', {})

        status_class = "success" if avg_complexity <= 5 else "warning" if avg_complexity <= 10 else "danger"

        html = f'''
        <div class="metric {status_class}">
            <h3>複雜度統計</h3>
            <div class="complexity-grid">
                <div class="complexity-card">
                    <h4>平均複雜度</h4>
                    <div class="score">{avg_complexity:.1f}</div>
                    <p>目標: ≤5.0 (優秀), ≤10.0 (可接受)</p>
                </div>
                <div class="complexity-card">
                    <h4>最大複雜度</h4>
                    <div class="score">{max_complexity}</div>
                    <p>建議: ≤10 (可接受), ≤20 (需重構)</p>
                </div>
                <div class="complexity-card">
                    <h4>高複雜度函數</h4>
                    <div class="score">{len(high_complexity_functions)}</div>
                    <p>複雜度 >10 的函數數量</p>
                </div>
            </div>
        </div>
        '''

        if complexity_dist:
            html += '<h4>複雜度分佈:</h4><table><tr><th>等級</th><th>範圍</th><th>數量</th><th>百分比</th></tr>'
            total_functions = sum(complexity_dist.values())

            grade_info = {
                'A': ('1-5', '優秀'),
                'B': ('6-10', '良好'),
                'C': ('11-20', '需注意'),
                'D': ('21-30', '需重構'),
                'E': ('31-40', '高風險'),
                'F': ('41+', '極高風險')
            }

            for grade, count in complexity_dist.items():
                range_info, desc = grade_info.get(grade, ('未知', ''))
                percentage = (count / total_functions * 100) if total_functions > 0 else 0
                html += f'<tr><td>{grade} ({desc})</td><td>{range_info}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>'
            html += '</table>'

        if high_complexity_functions:
            html += '<h4>高複雜度函數列表:</h4><table><tr><th>檔案</th><th>函數</th><th>複雜度</th><th>行號</th></tr>'
            for func in high_complexity_functions[:10]:  # 只顯示前10個
                html += f'<tr><td>{func["file"]}</td><td>{func["function"]}</td><td>{func["complexity"]}</td><td>{func["line"]}</td></tr>'
            html += '</table>'

        return html

    def _generate_maintainability_section(self, maintainability_data: Dict[str, Any]) -> str:
        """生成可維護性分析區段."""
        if not maintainability_data:
            return '<div class="metric warning">⚠️ 無可維護性分析數據</div>'

        avg_mi = maintainability_data.get('average_mi', 0)
        low_maintainability = maintainability_data.get('low_maintainability', [])

        status_class = "success" if avg_mi >= 20 else "warning" if avg_mi >= 10 else "danger"

        html = f'''
        <div class="metric {status_class}">
            <h3>可維護性指標</h3>
            <div class="score">{avg_mi:.1f}</div>
            <p>可維護性指標 (MI): ≥20 (良好), 10-20 (可接受), <10 (需改進)</p>
        </div>
        '''

        if low_maintainability:
            html += '<h4>低可維護性檔案:</h4><table><tr><th>檔案</th><th>MI 指標</th></tr>'
            for file_data in low_maintainability:
                html += f'<tr><td>{file_data["file"]}</td><td>{file_data["mi_score"]:.1f}</td></tr>'
            html += '</table>'

        return html

    def _generate_dependency_section(self, dependencies: Dict[str, Any], graph_path: str) -> str:
        """生成依賴關係分析區段."""
        if not dependencies:
            return '<div class="metric warning">⚠️ 無依賴關係分析數據</div>'

        circular_deps = dependencies.get('circular_dependencies', [])
        coupling_metrics = dependencies.get('coupling_metrics', {})

        html = '<div class="metric">'

        if graph_path:
            html += f'''
            <h3>依賴關係圖</h3>
            <div class="chart-container">
                <img src="{graph_path}" alt="模組依賴關係圖" />
            </div>
            '''

        if circular_deps:
            html += f'''
            <h3>循環依賴檢測</h3>
            <div class="metric danger">
                <p>發現 {len(circular_deps)} 個循環依賴:</p>
                <ul>
            '''
            for dep_pair in circular_deps:
                html += f'<li>{dep_pair[0]} ↔ {dep_pair[1]}</li>'
            html += '</ul></div>'
        else:
            html += '<div class="metric success"><h3>循環依賴檢測</h3><p>✅ 未發現循環依賴</p></div>'

        if coupling_metrics:
            html += '''
            <h3>耦合度分析</h3>
            <table>
                <tr><th>模組</th><th>傳入耦合 (Ca)</th><th>傳出耦合 (Ce)</th><th>不穩定性 (I)</th></tr>
            '''

            for module in list(coupling_metrics.get('instability', {}).keys())[:10]:  # 只顯示前10個
                ca = coupling_metrics.get('afferent_coupling', {}).get(module, 0)
                ce = coupling_metrics.get('efferent_coupling', {}).get(module, 0)
                instability = coupling_metrics.get('instability', {}).get(module, 0)

                html += f'<tr><td>{module}</td><td>{ca}</td><td>{ce}</td><td>{instability:.2f}</td></tr>'

            html += '</table>'

        html += '</div>'
        return html

    def _generate_trends_section(self, trends_chart_path: str) -> str:
        """生成趨勢分析區段."""
        if not trends_chart_path:
            return '<div class="metric warning">⚠️ 歷史數據不足，無法生成趨勢分析</div>'

        html = f'''
        <div class="metric">
            <h3>品質趨勢圖表</h3>
            <div class="chart-container">
                <img src="{trends_chart_path}" alt="品質趨勢分析圖表" />
            </div>
            <p>此圖表顯示了 Pylint 評分、循環複雜度和可維護性指標的歷史趨勢。</p>
        </div>
        '''

        return html

    def _generate_recommendations_section(self, recommendations: List[Dict[str, Any]]) -> str:
        """生成改進建議區段."""
        if not recommendations:
            return '<div class="metric success">🎉 目前沒有發現需要改進的問題！</div>'

        html = '<div class="recommendations-container">'

        # 按優先級分組
        high_priority = [r for r in recommendations if r['priority'] == 'high']
        medium_priority = [r for r in recommendations if r['priority'] == 'medium']
        low_priority = [r for r in recommendations if r['priority'] == 'low']

        for priority, recs in [('高', high_priority), ('中', medium_priority), ('低', low_priority)]:
            if recs:
                html += f'<h3>優先級 {priority} ({len(recs)} 項)</h3>'

                for rec in recs:
                    priority_class = f"priority-{rec['priority']}"
                    badge_class = f"badge-{rec['priority']}"

                    html += f'''
                    <div class="recommendation {priority_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h4 style="margin: 0;">{rec['issue']}</h4>
                            <span class="badge {badge_class}">{rec['priority']}</span>
                        </div>
                        <p><strong>模組:</strong> {rec['module']}</p>
                        <p><strong>建議行動:</strong> {rec['action']}</p>
                        <p><strong>預期影響:</strong> {rec['impact']}</p>
                        <p><strong>工作量:</strong> {rec['effort']}</p>
                        <p><strong>類別:</strong> {rec['category']}</p>
                    </div>
                    '''

        html += '</div>'
        return html

    def _generate_basic_metrics_section(self, metrics_data: Dict[str, Any]) -> str:
        """生成基本程式碼指標區段."""
        if not metrics_data:
            return '<div class="metric warning">⚠️ 無程式碼指標數據</div>'

        total_lines = metrics_data.get("total_lines", 0)
        total_files = metrics_data.get("total_files", 0)
        modules = metrics_data.get("modules", {})

        html = f'''
        <div class="metric">
            <h3>整體統計</h3>
            <p>總程式碼行數: {total_lines:,}</p>
            <p>總檔案數: {total_files}</p>
        </div>
        '''

        if modules:
            html += '<h4>模組統計:</h4><table><tr><th>模組</th><th>檔案數</th><th>程式碼行數</th></tr>'
            for module, data in modules.items():
                html += f'<tr><td>{module}</td><td>{data["files"]}</td><td>{data["lines"]:,}</td></tr>'
            html += '</table>'

        return html

    def _generate_pylint_section(self, scores: Dict[str, float]) -> str:
        """生成 Pylint 評分區段."""
        if not scores:
            return '<div class="metric warning">⚠️ 無 Pylint 評分數據</div>'
        
        html = ""
        for module, score in scores.items():
            threshold = 9.0 if module == "core_modules" else 8.5
            status_class = "success" if score >= threshold else "danger"
            
            html += f'''
            <div class="metric {status_class}">
                <h3>{module.replace("_", " ").title()}</h3>
                <div class="score">{score:.1f}/10</div>
                <p>閾值: {threshold}/10</p>
            </div>
            '''
        
        return html

    def _generate_file_size_section(self, file_data: Dict[str, Any]) -> str:
        """生成檔案大小檢查區段."""
        if not file_data:
            return '<div class="metric warning">⚠️ 無檔案大小數據</div>'
        
        violations = file_data.get("violations", [])
        total_files = file_data.get("total_files", 0)
        avg_size = file_data.get("avg_size", 0)
        
        status_class = "success" if not violations else "danger"
        
        html = f'''
        <div class="metric {status_class}">
            <h3>檔案統計</h3>
            <p>總檔案數: {total_files}</p>
            <p>平均檔案大小: {avg_size:.1f} 行</p>
            <p>超標檔案數: {len(violations)}</p>
        </div>
        '''
        
        if violations:
            html += '<h4>超標檔案列表:</h4><table><tr><th>檔案</th><th>行數</th></tr>'
            for filepath, line_count in violations:
                html += f'<tr><td>{filepath}</td><td>{line_count}</td></tr>'
            html += '</table>'
        
        return html

    def _generate_coverage_section(self, coverage_data: Dict[str, Any]) -> str:
        """生成測試覆蓋率區段."""
        status = coverage_data.get("status", "unknown")
        
        if status == "available":
            return '<div class="metric success">✅ 測試覆蓋率報告可用</div>'
        elif status == "not_available":
            return '<div class="metric warning">⚠️ 測試覆蓋率報告不可用</div>'
        else:
            return f'<div class="metric danger">❌ 測試覆蓋率檢查錯誤: {coverage_data.get("error", "未知錯誤")}</div>'

    def _generate_security_section(self, security_data: Dict[str, Any], vuln_data: Dict[str, Any]) -> str:
        """生成安全檢查區段."""
        html = ""
        
        # Bandit 安全掃描
        if security_data.get("total_issues", 0) == 0:
            html += '<div class="metric success">✅ Bandit 安全掃描: 無問題</div>'
        else:
            total = security_data.get("total_issues", 0)
            high = security_data.get("high_severity", 0)
            medium = security_data.get("medium_severity", 0)
            low = security_data.get("low_severity", 0)
            
            status_class = "danger" if high > 0 else "warning" if medium > 0 else "success"
            html += f'''
            <div class="metric {status_class}">
                <h3>Bandit 安全掃描</h3>
                <p>總問題數: {total}</p>
                <p>高風險: {high}, 中風險: {medium}, 低風險: {low}</p>
            </div>
            '''
        
        # Safety 依賴檢查
        vuln_count = vuln_data.get("total_vulnerabilities", 0)
        if vuln_count == 0:
            html += '<div class="metric success">✅ Safety 依賴檢查: 無漏洞</div>'
        else:
            html += f'<div class="metric danger">❌ Safety 依賴檢查: 發現 {vuln_count} 個漏洞</div>'
        
        return html

    def _generate_metrics_section(self, metrics_data: Dict[str, Any]) -> str:
        """生成程式碼指標區段."""
        if not metrics_data:
            return '<div class="metric warning">⚠️ 無程式碼指標數據</div>'
        
        total_lines = metrics_data.get("total_lines", 0)
        total_files = metrics_data.get("total_files", 0)
        modules = metrics_data.get("modules", {})
        
        html = f'''
        <div class="metric">
            <h3>整體統計</h3>
            <p>總程式碼行數: {total_lines:,}</p>
            <p>總檔案數: {total_files}</p>
        </div>
        '''
        
        if modules:
            html += '<h4>模組統計:</h4><table><tr><th>模組</th><th>檔案數</th><th>程式碼行數</th></tr>'
            for module, data in modules.items():
                html += f'<tr><td>{module}</td><td>{data["files"]}</td><td>{data["lines"]:,}</td></tr>'
            html += '</table>'
        
        return html


def main():
    """主函數."""
    try:
        generator = QualityReportGenerator()
        generator.generate_report()
        print("🎉 品質報告生成完成！")
        return 0
    except Exception as e:
        print(f"❌ 品質報告生成失敗: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
