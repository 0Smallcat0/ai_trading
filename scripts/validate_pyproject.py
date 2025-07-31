#!/usr/bin/env python3
"""
pyproject.toml 驗證腳本

此腳本驗證 pyproject.toml 檔案的語法正確性和配置完整性。
"""

import sys
import tomllib
from pathlib import Path
from typing import Dict, Any, List


def load_pyproject() -> Dict[str, Any]:
    """載入 pyproject.toml 檔案
    
    Returns:
        Dict[str, Any]: 解析後的配置字典
        
    Raises:
        FileNotFoundError: 當檔案不存在時
        tomllib.TOMLDecodeError: 當 TOML 語法錯誤時
    """
    pyproject_path = Path("pyproject.toml")
    
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml 檔案不存在")
    
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)


def validate_poetry_config(config: Dict[str, Any]) -> List[str]:
    """驗證 Poetry 配置
    
    Args:
        config: pyproject.toml 配置字典
        
    Returns:
        List[str]: 驗證錯誤列表
    """
    errors = []
    
    # 檢查必要的 Poetry 配置
    if "tool" not in config:
        errors.append("缺少 [tool] 區段")
        return errors
    
    if "poetry" not in config["tool"]:
        errors.append("缺少 [tool.poetry] 區段")
        return errors
    
    poetry_config = config["tool"]["poetry"]
    
    # 檢查必要欄位
    required_fields = ["name", "version", "description", "authors"]
    for field in required_fields:
        if field not in poetry_config:
            errors.append(f"缺少必要欄位: {field}")
    
    # 檢查版本格式
    if "version" in poetry_config:
        version = poetry_config["version"]
        if not isinstance(version, str) or not version:
            errors.append("版本號格式錯誤")
    
    # 檢查依賴配置
    if "dependencies" not in poetry_config:
        errors.append("缺少 [tool.poetry.dependencies] 區段")
    else:
        deps = poetry_config["dependencies"]
        if "python" not in deps:
            errors.append("缺少 Python 版本需求")
    
    return errors


def validate_dependency_groups(config: Dict[str, Any]) -> List[str]:
    """驗證依賴分組配置
    
    Args:
        config: pyproject.toml 配置字典
        
    Returns:
        List[str]: 驗證錯誤列表
    """
    errors = []
    
    poetry_config = config.get("tool", {}).get("poetry", {})
    
    # 檢查依賴分組
    expected_groups = ["dev", "test", "broker", "optional"]
    
    for group in expected_groups:
        group_key = f"group.{group}.dependencies"
        if group_key not in poetry_config:
            errors.append(f"缺少依賴分組: [tool.poetry.group.{group}.dependencies]")
    
    return errors


def validate_tool_configs(config: Dict[str, Any]) -> List[str]:
    """驗證工具配置
    
    Args:
        config: pyproject.toml 配置字典
        
    Returns:
        List[str]: 驗證錯誤列表
    """
    errors = []
    
    tool_config = config.get("tool", {})
    
    # 檢查必要的工具配置
    expected_tools = ["black", "isort", "pylint", "mypy", "pytest", "coverage"]
    
    for tool in expected_tools:
        if tool not in tool_config:
            errors.append(f"缺少工具配置: [tool.{tool}]")
    
    return errors


def validate_scripts(config: Dict[str, Any]) -> List[str]:
    """驗證腳本配置
    
    Args:
        config: pyproject.toml 配置字典
        
    Returns:
        List[str]: 驗證錯誤列表
    """
    errors = []
    
    poetry_config = config.get("tool", {}).get("poetry", {})
    
    if "scripts" not in poetry_config:
        errors.append("缺少 [tool.poetry.scripts] 區段")
        return errors
    
    scripts = poetry_config["scripts"]
    
    # 檢查必要的腳本
    expected_scripts = ["start", "web-ui"]
    
    for script in expected_scripts:
        if script not in scripts:
            errors.append(f"缺少腳本定義: {script}")
    
    return errors


def check_dependency_versions(config: Dict[str, Any]) -> List[str]:
    """檢查依賴版本格式
    
    Args:
        config: pyproject.toml 配置字典
        
    Returns:
        List[str]: 警告列表
    """
    warnings = []
    
    poetry_config = config.get("tool", {}).get("poetry", {})
    dependencies = poetry_config.get("dependencies", {})
    
    for dep_name, dep_spec in dependencies.items():
        if dep_name == "python":
            continue
            
        if isinstance(dep_spec, str):
            # 檢查版本約束格式
            if not any(op in dep_spec for op in ["^", "~", ">=", "<=", "==", "!="]):
                warnings.append(f"依賴 {dep_name} 缺少版本約束")
        elif isinstance(dep_spec, dict):
            # 檢查複雜依賴配置
            if "version" not in dep_spec:
                warnings.append(f"依賴 {dep_name} 缺少版本規範")
    
    return warnings


def main():
    """主函數"""
    print("🔍 驗證 pyproject.toml 配置...")
    
    try:
        # 載入配置
        config = load_pyproject()
        print("✅ TOML 語法正確")
        
        # 執行各項驗證
        all_errors = []
        all_warnings = []
        
        # 驗證 Poetry 基本配置
        errors = validate_poetry_config(config)
        all_errors.extend(errors)
        
        # 驗證依賴分組
        errors = validate_dependency_groups(config)
        all_errors.extend(errors)
        
        # 驗證工具配置
        errors = validate_tool_configs(config)
        all_errors.extend(errors)
        
        # 驗證腳本配置
        errors = validate_scripts(config)
        all_errors.extend(errors)
        
        # 檢查依賴版本
        warnings = check_dependency_versions(config)
        all_warnings.extend(warnings)
        
        # 輸出結果
        if all_errors:
            print("\n❌ 發現配置錯誤:")
            for error in all_errors:
                print(f"  • {error}")
        
        if all_warnings:
            print("\n⚠️ 發現配置警告:")
            for warning in all_warnings:
                print(f"  • {warning}")
        
        if not all_errors and not all_warnings:
            print("✅ pyproject.toml 配置完全正確!")
        elif not all_errors:
            print("✅ pyproject.toml 基本配置正確，但有一些建議改進")
        
        # 輸出統計信息
        poetry_config = config.get("tool", {}).get("poetry", {})
        deps_count = len(poetry_config.get("dependencies", {}))
        dev_deps_count = len(poetry_config.get("group", {}).get("dev", {}).get("dependencies", {}))
        
        print(f"\n📊 配置統計:")
        print(f"  • 生產依賴: {deps_count} 個")
        print(f"  • 開發依賴: {dev_deps_count} 個")
        print(f"  • Python 版本: {poetry_config.get('dependencies', {}).get('python', 'N/A')}")
        print(f"  • 專案版本: {poetry_config.get('version', 'N/A')}")
        
        return 0 if not all_errors else 1
        
    except FileNotFoundError as e:
        print(f"❌ 檔案錯誤: {e}")
        return 1
    except tomllib.TOMLDecodeError as e:
        print(f"❌ TOML 語法錯誤: {e}")
        return 1
    except Exception as e:
        print(f"❌ 未預期的錯誤: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
