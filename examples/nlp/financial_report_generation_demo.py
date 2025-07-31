#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融報告生成示例

此示例展示如何使用 FinancialReportGenerator 生成智能金融分析報告。
基於大語言模型和網絡搜索，自動生成結構化的市場分析報告。

功能特色：
- 自動網絡搜索相關信息
- 基於 LLM 的智能分析
- 結構化報告生成
- 批量主題處理

使用前準備：
1. 安裝依賴：pip install langchain langchain-openai langchain-community
2. 設置 API 密鑰：OpenAI API Key 和 Tavily API Key
3. 配置模型參數

Example:
    python examples/nlp/financial_report_generation_demo.py
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.nlp.report_generator import FinancialReportGenerator, ReportConfig

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_demo_config() -> ReportConfig:
    """設置示例配置
    
    Returns:
        ReportConfig: 報告生成配置
    """
    # LLM 配置
    llm_config = {
        "model": "gpt-3.5-turbo",  # 或使用其他模型
        "api_key": os.getenv("OPENAI_API_KEY", "your-openai-api-key"),
        "base_url": os.getenv("OPENAI_BASE_URL"),  # 可選，用於自定義端點
        "max_tokens": 4000,
        "temperature": 0.1
    }
    
    # Tavily 搜索 API 密鑰
    tavily_api_key = os.getenv("TAVILY_API_KEY", "your-tavily-api-key")
    
    # 分析主題
    topics = [
        "人工智能股票",
        "新能源汽車行業",
        "半導體產業趨勢",
        "生物科技投資機會",
        "ESG投資"
    ]
    
    # 創建配置
    config = ReportConfig(
        llm_config=llm_config,
        tavily_api_key=tavily_api_key,
        search_top_k=8,
        output_dir="examples/output/reports",
        topics=topics
    )
    
    return config


def demo_single_report():
    """示例：生成單個報告"""
    logger.info("=== 單個報告生成示例 ===")
    
    try:
        # 設置配置
        config = setup_demo_config()
        
        # 創建生成器
        generator = FinancialReportGenerator(config)
        
        # 生成單個報告
        topic = "人工智能股票投資分析"
        logger.info(f"生成報告主題: {topic}")
        
        report_content = generator.generate_single_report(topic)
        
        # 保存報告
        file_path = generator.save_report(topic, report_content)
        
        logger.info(f"報告生成成功: {file_path}")
        
        # 顯示報告摘要
        print("\n" + "="*50)
        print("報告內容預覽:")
        print("="*50)
        print(report_content[:500] + "..." if len(report_content) > 500 else report_content)
        
    except Exception as e:
        logger.error(f"單個報告生成失敗: {e}")


def demo_batch_reports():
    """示例：批量生成報告"""
    logger.info("=== 批量報告生成示例 ===")
    
    try:
        # 設置配置
        config = setup_demo_config()
        
        # 創建生成器
        generator = FinancialReportGenerator(config)
        
        # 批量生成報告
        logger.info(f"開始批量生成 {len(config.topics)} 個報告")
        
        report_paths = generator.generate_reports()
        
        # 顯示結果
        logger.info(f"批量生成完成，共生成 {len(report_paths)} 份報告")
        
        # 獲取摘要
        summary = generator.get_report_summary()
        
        print("\n" + "="*50)
        print("批量生成摘要:")
        print("="*50)
        print(f"總報告數: {summary['total_reports']}")
        print(f"輸出目錄: {summary['output_dir']}")
        print(f"最新報告: {summary.get('latest_report', 'N/A')}")
        print("\n生成的報告文件:")
        for i, path in enumerate(report_paths, 1):
            print(f"  {i}. {Path(path).name}")
            
    except Exception as e:
        logger.error(f"批量報告生成失敗: {e}")


def demo_custom_topics():
    """示例：自定義主題報告生成"""
    logger.info("=== 自定義主題報告生成示例 ===")
    
    try:
        # 設置配置（不包含預設主題）
        config = setup_demo_config()
        config.topics = None  # 清空預設主題
        
        # 創建生成器
        generator = FinancialReportGenerator(config)
        
        # 自定義主題列表
        custom_topics = [
            "量化交易策略分析",
            "加密貨幣市場趨勢",
            "房地產投資信託(REITs)"
        ]
        
        # 生成自定義主題報告
        logger.info(f"生成自定義主題報告: {custom_topics}")
        
        report_paths = generator.generate_reports(custom_topics)
        
        logger.info(f"自定義主題報告生成完成，共 {len(report_paths)} 份")
        
        # 顯示結果
        print("\n" + "="*50)
        print("自定義主題報告:")
        print("="*50)
        for topic, path in zip(custom_topics, report_paths):
            print(f"  主題: {topic}")
            print(f"  文件: {Path(path).name}")
            print()
            
    except Exception as e:
        logger.error(f"自定義主題報告生成失敗: {e}")


def demo_error_handling():
    """示例：錯誤處理和異常情況"""
    logger.info("=== 錯誤處理示例 ===")
    
    try:
        # 測試無效配置
        invalid_config = ReportConfig(
            llm_config={},  # 空配置
            tavily_api_key=""  # 空密鑰
        )
        
        try:
            generator = FinancialReportGenerator(invalid_config)
        except ValueError as e:
            logger.info(f"✅ 成功捕獲配置錯誤: {e}")
        
        # 測試無效主題
        valid_config = setup_demo_config()
        generator = FinancialReportGenerator(valid_config)
        
        try:
            generator.generate_reports([])  # 空主題列表
        except ValueError as e:
            logger.info(f"✅ 成功捕獲主題錯誤: {e}")
            
        logger.info("錯誤處理測試完成")
        
    except Exception as e:
        logger.error(f"錯誤處理測試失敗: {e}")


def main():
    """主函數"""
    print("🤖 金融報告生成示例")
    print("=" * 50)
    
    # 檢查環境變數
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  警告: 未設置 OPENAI_API_KEY 環境變數")
        print("   請設置: export OPENAI_API_KEY=your-api-key")
        
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️  警告: 未設置 TAVILY_API_KEY 環境變數")
        print("   請設置: export TAVILY_API_KEY=your-api-key")
        
    print()
    
    # 運行示例
    try:
        # 1. 單個報告生成
        demo_single_report()
        
        print("\n" + "="*50 + "\n")
        
        # 2. 批量報告生成
        demo_batch_reports()
        
        print("\n" + "="*50 + "\n")
        
        # 3. 自定義主題
        demo_custom_topics()
        
        print("\n" + "="*50 + "\n")
        
        # 4. 錯誤處理
        demo_error_handling()
        
        print("\n🎉 所有示例運行完成！")
        
    except KeyboardInterrupt:
        logger.info("用戶中斷執行")
    except Exception as e:
        logger.error(f"示例運行失敗: {e}")
        raise


if __name__ == "__main__":
    main()
