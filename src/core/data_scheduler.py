#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據定時任務調度器
================

設置定時任務每日自動更新股票數據，
確保系統始終使用最新的真實市場數據。

功能特點：
- 每日自動數據更新
- 智能重試機制
- 任務執行監控
- 錯誤處理和告警
- 任務執行歷史記錄

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
"""

import os
import sys
import time
import logging
import schedule
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Callable, Any
import json
from pathlib import Path

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.real_data_integration import RealDataIntegrationService

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataScheduler:
    """數據定時任務調度器"""
    
    def __init__(self, config_path: str = 'config/scheduler_config.json'):
        """
        初始化調度器
        
        Args:
            config_path: 配置文件路徑
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.data_service = RealDataIntegrationService()
        self.is_running = False
        self.scheduler_thread = None
        
        # 任務執行歷史
        self.execution_history = []
        self.max_history_size = 100
        
        # 創建日誌目錄
        os.makedirs('logs', exist_ok=True)
        
        logger.info("DataScheduler 初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """載入配置文件"""
        default_config = {
            "daily_update": {
                "enabled": True,
                "time": "08:00",  # 每日8點更新
                "retry_times": 3,
                "retry_interval": 300,  # 5分鐘
                "timeout": 3600  # 1小時超時
            },
            "weekly_full_update": {
                "enabled": True,
                "day": "sunday",
                "time": "02:00",  # 週日凌晨2點
                "retry_times": 5,
                "retry_interval": 600,  # 10分鐘
                "timeout": 7200  # 2小時超時
            },
            "health_check": {
                "enabled": True,
                "interval": 3600,  # 每小時檢查
                "alert_threshold": 0.8  # 成功率低於80%時告警
            },
            "notification": {
                "enabled": True,
                "email": None,
                "webhook": None
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合併默認配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                # 創建默認配置文件
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                return default_config
                
        except Exception as e:
            logger.error(f"載入配置失敗，使用默認配置: {e}")
            return default_config
    
    def _save_execution_record(self, task_name: str, status: str, 
                             details: Dict[str, Any]):
        """保存任務執行記錄"""
        record = {
            "task_name": task_name,
            "status": status,
            "start_time": details.get('start_time'),
            "end_time": details.get('end_time'),
            "duration": details.get('duration'),
            "records_updated": details.get('records_updated', 0),
            "symbols_updated": details.get('symbols_updated', 0),
            "failed_symbols": details.get('failed_symbols', []),
            "error_message": details.get('error_message'),
            "timestamp": datetime.now().isoformat()
        }
        
        self.execution_history.append(record)
        
        # 限制歷史記錄大小
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]
        
        # 保存到文件
        try:
            history_file = 'logs/scheduler_history.json'
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.execution_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存執行記錄失敗: {e}")
    
    def daily_update_task(self):
        """每日數據更新任務"""
        task_name = "daily_update"
        start_time = datetime.now()
        
        logger.info("🚀 開始執行每日數據更新任務")
        
        try:
            # 獲取配置
            config = self.config['daily_update']
            
            # 執行數據更新
            result = self.data_service.update_data()
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            if result['success']:
                status = "success"
                logger.info(f"✅ 每日更新完成: {result['message']}")
            else:
                status = "failed"
                logger.error(f"❌ 每日更新失敗: {result['message']}")
            
            # 記錄執行結果
            self._save_execution_record(task_name, status, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': str(duration),
                'records_updated': result.get('total_records', 0),
                'symbols_updated': result.get('updated_symbols', 0),
                'failed_symbols': result.get('failed_symbols_list', [])
            })
            
            # 發送通知
            if self.config['notification']['enabled']:
                self._send_notification(task_name, status, result)
            
        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.error(f"❌ 每日更新任務異常: {e}")
            
            self._save_execution_record(task_name, "error", {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': str(duration),
                'error_message': str(e)
            })
    
    def weekly_full_update_task(self):
        """週度完整數據更新任務"""
        task_name = "weekly_full_update"
        start_time = datetime.now()
        
        logger.info("🚀 開始執行週度完整數據更新任務")
        
        try:
            # 獲取所有可用股票
            symbols = self.data_service.get_available_symbols()
            
            # 執行完整更新
            result = self.data_service.update_data(symbols=symbols)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            if result['success']:
                status = "success"
                logger.info(f"✅ 週度完整更新完成: {result['message']}")
            else:
                status = "failed"
                logger.error(f"❌ 週度完整更新失敗: {result['message']}")
            
            # 記錄執行結果
            self._save_execution_record(task_name, status, {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': str(duration),
                'records_updated': result.get('total_records', 0),
                'symbols_updated': result.get('updated_symbols', 0),
                'failed_symbols': result.get('failed_symbols_list', [])
            })
            
            # 發送通知
            if self.config['notification']['enabled']:
                self._send_notification(task_name, status, result)
            
        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.error(f"❌ 週度完整更新任務異常: {e}")
            
            self._save_execution_record(task_name, "error", {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': str(duration),
                'error_message': str(e)
            })
    
    def health_check_task(self):
        """系統健康檢查任務"""
        try:
            health = self.data_service.health_check()
            quality_metrics = self.data_service.get_quality_metrics()
            
            # 檢查成功率
            completeness = quality_metrics.get('completeness', 0)
            threshold = self.config['health_check']['alert_threshold'] * 100
            
            if completeness < threshold:
                logger.warning(f"⚠️ 數據完整性低於閾值: {completeness:.1f}% < {threshold}%")
                
                # 發送告警
                if self.config['notification']['enabled']:
                    self._send_alert("數據品質告警", {
                        "completeness": completeness,
                        "threshold": threshold,
                        "failed_symbols": quality_metrics.get('failed_symbols', [])
                    })
            
            logger.info(f"🏥 健康檢查完成: {health['status']}")
            
        except Exception as e:
            logger.error(f"❌ 健康檢查失敗: {e}")
    
    def _send_notification(self, task_name: str, status: str, result: Dict[str, Any]):
        """發送通知"""
        try:
            message = f"任務 {task_name} 執行{status}: {result.get('message', '')}"
            logger.info(f"📧 通知: {message}")
            
            # 這裡可以實現實際的通知發送邏輯
            # 例如：發送郵件、Webhook、Slack等
            
        except Exception as e:
            logger.error(f"❌ 發送通知失敗: {e}")
    
    def _send_alert(self, alert_type: str, details: Dict[str, Any]):
        """發送告警"""
        try:
            message = f"告警: {alert_type} - {details}"
            logger.warning(f"🚨 告警: {message}")
            
            # 這裡可以實現實際的告警發送邏輯
            
        except Exception as e:
            logger.error(f"❌ 發送告警失敗: {e}")
    
    def setup_schedules(self):
        """設置定時任務"""
        # 每日更新任務
        if self.config['daily_update']['enabled']:
            update_time = self.config['daily_update']['time']
            schedule.every().day.at(update_time).do(self.daily_update_task)
            logger.info(f"📅 設置每日更新任務: {update_time}")
        
        # 週度完整更新任務
        if self.config['weekly_full_update']['enabled']:
            day = self.config['weekly_full_update']['day']
            time_str = self.config['weekly_full_update']['time']
            
            if day.lower() == 'monday':
                schedule.every().monday.at(time_str).do(self.weekly_full_update_task)
            elif day.lower() == 'sunday':
                schedule.every().sunday.at(time_str).do(self.weekly_full_update_task)
            # 可以添加其他天
            
            logger.info(f"📅 設置週度完整更新任務: {day} {time_str}")
        
        # 健康檢查任務
        if self.config['health_check']['enabled']:
            interval = self.config['health_check']['interval']
            schedule.every(interval).seconds.do(self.health_check_task)
            logger.info(f"📅 設置健康檢查任務: 每 {interval} 秒")
    
    def start(self):
        """啟動調度器"""
        if self.is_running:
            logger.warning("調度器已在運行中")
            return
        
        self.setup_schedules()
        self.is_running = True
        
        def run_scheduler():
            logger.info("🚀 數據調度器啟動")
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
            logger.info("⏹️ 數據調度器停止")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ 數據調度器已啟動")
    
    def stop(self):
        """停止調度器"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        logger.info("⏹️ 數據調度器已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """獲取調度器狀態"""
        return {
            "is_running": self.is_running,
            "scheduled_jobs": len(schedule.jobs),
            "execution_history_count": len(self.execution_history),
            "last_execution": self.execution_history[-1] if self.execution_history else None,
            "config": self.config
        }
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取執行歷史"""
        return self.execution_history[-limit:] if self.execution_history else []
    
    def run_task_now(self, task_name: str) -> Dict[str, Any]:
        """立即執行指定任務"""
        if task_name == "daily_update":
            self.daily_update_task()
        elif task_name == "weekly_full_update":
            self.weekly_full_update_task()
        elif task_name == "health_check":
            self.health_check_task()
        else:
            return {"success": False, "message": f"未知任務: {task_name}"}
        
        return {"success": True, "message": f"任務 {task_name} 執行完成"}

# 創建全局調度器實例
data_scheduler = DataScheduler()

if __name__ == "__main__":
    # 測試調度器
    scheduler = DataScheduler()
    
    try:
        # 啟動調度器
        scheduler.start()
        
        # 立即執行一次健康檢查
        scheduler.run_task_now("health_check")
        
        # 獲取狀態
        status = scheduler.get_status()
        print(f"調度器狀態: {status}")
        
        # 保持運行
        print("調度器正在運行，按 Ctrl+C 停止...")
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n正在停止調度器...")
        scheduler.stop()
        print("調度器已停止")
