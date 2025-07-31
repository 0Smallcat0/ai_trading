#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
優化的 Streamlit 應用啟動腳本
解決頁面加載時間過長的問題
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_environment():
    """設置環境變量以優化性能"""
    logger.info("🔧 設置性能優化環境變量...")
    
    # 設置環境變量
    env_vars = {
        'STREAMLIT_SERVER_HEADLESS': 'true',
        'STREAMLIT_SERVER_ENABLE_CORS': 'false',
        'STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION': 'false',
        'STREAMLIT_BROWSER_GATHER_USAGE_STATS': 'false',
        'STREAMLIT_RUNNER_MAGIC_ENABLED': 'false',
        'STREAMLIT_RUNNER_INSTALL_TRACER': 'false',
        'STREAMLIT_RUNNER_FIX_MATPLOTLIB': 'false',
        'STREAMLIT_CLIENT_CACHING': 'true',
        'STREAMLIT_SERVER_MAX_UPLOAD_SIZE': '200',
        'STREAMLIT_SERVER_MAX_MESSAGE_SIZE': '200',
        'PYTHONUNBUFFERED': '1',
        'PYTHONDONTWRITEBYTECODE': '1',
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"設置 {key}={value}")
    
    logger.info("✅ 環境變量設置完成")

def check_dependencies():
    """檢查關鍵依賴項"""
    logger.info("🔧 檢查關鍵依賴項...")
    
    critical_modules = [
        'streamlit',
        'pandas',
        'numpy',
        'sqlite3',
        'schedule'
    ]
    
    missing_modules = []
    for module in critical_modules:
        try:
            __import__(module)
            logger.info(f"✅ {module} 可用")
        except ImportError:
            missing_modules.append(module)
            logger.warning(f"❌ {module} 不可用")
    
    if missing_modules:
        logger.error(f"缺少關鍵模組: {missing_modules}")
        return False
    
    logger.info("✅ 所有關鍵依賴項都可用")
    return True

def pre_warm_application():
    """預熱應用程序"""
    logger.info("🔧 預熱應用程序...")
    
    try:
        # 預先導入重要模組
        import pandas as pd
        import numpy as np
        import sqlite3
        import streamlit as st
        
        # 預先創建一些對象
        _ = pd.DataFrame({'test': [1, 2, 3]})
        _ = np.array([1, 2, 3])
        
        logger.info("✅ 應用程序預熱完成")
        return True
    except Exception as e:
        logger.error(f"❌ 預熱失敗: {e}")
        return False

def start_streamlit():
    """啟動 Streamlit 應用"""
    logger.info("🚀 啟動 Streamlit 應用...")
    
    # 構建啟動命令
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "src/ui/web_ui.py",
        "--server.address=127.0.0.1",
        "--server.port=8501",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--runner.magicEnabled=false",
        "--client.caching=true",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false"
    ]
    
    logger.info(f"執行命令: {' '.join(cmd)}")
    
    try:
        # 啟動應用
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        logger.info("✅ Streamlit 應用已啟動")
        logger.info("🌐 應用地址: http://127.0.0.1:8501")
        logger.info("⏱️  等待應用完全載入...")
        
        # 監控啟動過程
        start_time = time.time()
        app_ready = False
        
        while True:
            output = process.stdout.readline()
            if output:
                print(output.strip())
                
                # 檢查應用是否準備就緒
                if "You can now view your Streamlit app" in output:
                    app_ready = True
                    load_time = time.time() - start_time
                    logger.info(f"🎉 應用載入完成！載入時間: {load_time:.2f}s")
                    break
                
                # 檢查錯誤
                if "error" in output.lower() or "exception" in output.lower():
                    logger.warning(f"⚠️  檢測到可能的問題: {output.strip()}")
            
            # 檢查進程是否結束
            if process.poll() is not None:
                break
            
            # 超時檢查
            if time.time() - start_time > 30:
                logger.warning("⏱️  啟動時間超過30秒，可能存在性能問題")
                break
        
        # 等待進程結束
        process.wait()
        
        if app_ready:
            logger.info("✅ Streamlit 應用運行完成")
        else:
            logger.warning("⚠️  應用可能未正常啟動")
        
        return process.returncode == 0
        
    except Exception as e:
        logger.error(f"❌ 啟動 Streamlit 應用失敗: {e}")
        return False

def main():
    """主函數"""
    logger.info("🚀 開始優化啟動 Streamlit 應用...")
    
    # 檢查工作目錄
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    logger.info(f"工作目錄: {os.getcwd()}")
    
    # 執行啟動步驟
    steps = [
        ("設置環境", setup_environment),
        ("檢查依賴", check_dependencies),
        ("預熱應用", pre_warm_application),
    ]
    
    for name, step_func in steps:
        logger.info(f"\n--- {name} ---")
        if not step_func():
            logger.error(f"❌ {name} 失敗，終止啟動")
            return False
    
    # 啟動應用
    logger.info("\n--- 啟動應用 ---")
    return start_streamlit()

if __name__ == "__main__":
    success = main()
    if not success:
        logger.error("❌ 應用啟動失敗")
        sys.exit(1)
    else:
        logger.info("✅ 應用啟動成功")
