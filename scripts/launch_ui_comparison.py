#!/usr/bin/env python3
"""
AI 交易系統 UI 版本對比啟動器

此腳本可以同時啟動新舊兩個版本的 Web UI，方便進行對比測試。

使用方式:
    python launch_ui_comparison.py
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def print_banner():
    """顯示啟動橫幅"""
    print("=" * 60)
    print("🚀 AI 交易系統 UI/UX 對比測試")
    print("=" * 60)
    print()

def check_dependencies():
    """檢查依賴"""
    try:
        import streamlit
        print("✅ Streamlit 已安裝")
        return True
    except ImportError:
        print("❌ Streamlit 未安裝，請執行: pip install streamlit")
        return False

def launch_ui_version(script_path, port, version_name):
    """啟動指定版本的 UI"""
    try:
        print(f"🚀 正在啟動 {version_name}...")
        
        # 構建啟動命令
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            script_path,
            "--server.address=127.0.0.1",
            f"--server.port={port}",
            "--server.headless=true"
        ]
        
        # 啟動進程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待啟動
        time.sleep(3)
        
        if process.poll() is None:
            print(f"✅ {version_name} 啟動成功")
            print(f"   URL: http://localhost:{port}")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {version_name} 啟動失敗")
            print(f"   錯誤: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ 啟動 {version_name} 時發生錯誤: {e}")
        return None

def main():
    """主函數"""
    print_banner()
    
    # 檢查依賴
    if not check_dependencies():
        return
    
    # 檢查文件是否存在
    old_ui_path = "src/ui/web_ui_production.py"
    new_ui_path = "src/ui/web_ui_redesigned.py"
    
    if not Path(old_ui_path).exists():
        print(f"❌ 找不到舊版 UI 文件: {old_ui_path}")
        return
    
    if not Path(new_ui_path).exists():
        print(f"❌ 找不到新版 UI 文件: {new_ui_path}")
        return
    
    print("📁 UI 文件檢查完成")
    print()
    
    # 啟動兩個版本
    processes = []
    
    # 啟動舊版 UI
    old_process = launch_ui_version(
        old_ui_path,
        8503,
        "舊版 UI (Production)"
    )
    if old_process:
        processes.append(("舊版 UI", old_process, 8503))

    print()

    # 啟動新版 UI
    new_process = launch_ui_version(
        new_ui_path,
        8504,
        "新版 UI (Redesigned)"
    )
    if new_process:
        processes.append(("新版 UI", new_process, 8504))
    
    print()
    print("=" * 60)
    print("🎯 對比測試指南")
    print("=" * 60)
    
    if processes:
        print("📊 可用的 UI 版本:")
        for name, _, port in processes:
            print(f"   • {name}: http://localhost:{port}")
        
        print()
        print("🔍 建議測試項目:")
        print("   1. 首頁信息密度對比")
        print("   2. 導航效率測試")
        print("   3. 新手友好度評估")
        print("   4. 視覺設計對比")
        print("   5. 功能可發現性測試")
        
        print()
        print("⚡ 快速對比:")
        print("   • 舊版: 側邊欄導航，功能分散")
        print("   • 新版: 儀表板中心，信息整合")
        
        print()
        print("🌐 自動打開瀏覽器...")
        
        # 自動打開瀏覽器
        try:
            time.sleep(2)
            webbrowser.open("http://localhost:8503")
            time.sleep(1)
            webbrowser.open("http://localhost:8504")
            print("✅ 瀏覽器已打開")
        except Exception as e:
            print(f"⚠️ 無法自動打開瀏覽器: {e}")
            print("   請手動訪問上述 URL")
        
        print()
        print("⌨️ 按 Ctrl+C 停止所有服務")
        
        try:
            # 等待用戶中斷
            while True:
                time.sleep(1)
                
                # 檢查進程是否還在運行
                running_processes = []
                for name, process, port in processes:
                    if process.poll() is None:
                        running_processes.append((name, process, port))
                    else:
                        print(f"⚠️ {name} 已停止運行")
                
                processes = running_processes
                
                if not processes:
                    print("ℹ️ 所有 UI 服務已停止")
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 正在停止所有服務...")
            
            # 停止所有進程
            for name, process, port in processes:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"✅ {name} 已停止")
                except subprocess.TimeoutExpired:
                    process.kill()
                    print(f"🔪 強制停止 {name}")
                except Exception as e:
                    print(f"⚠️ 停止 {name} 時發生錯誤: {e}")
            
            print("✅ 所有服務已停止")
    
    else:
        print("❌ 沒有成功啟動任何 UI 服務")
        print("請檢查錯誤信息並重試")

if __name__ == "__main__":
    main()
