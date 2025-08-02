"""
金融報告生成器模組

基於大語言模型和網絡搜索的智能金融報告生成系統。
支持多主題批量分析，自動生成結構化的市場分析報告。
"""

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
from tqdm import tqdm

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import StrOutputParser
    from langchain.prompts import PromptTemplate
    from langchain_community.tools.tavily_search import TavilySearchResults
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # 創建模擬類別
    class ChatOpenAI:
        def __init__(self, *args, **kwargs):
            pass
        def invoke(self, prompt):
            return type('MockResponse', (), {'content': f"模擬回應：{prompt}"})()

    class StrOutputParser:
        def parse(self, response):
            return getattr(response, 'content', str(response))

    class PromptTemplate:
        def __init__(self, template, input_variables):
            self.template = template
            self.input_variables = input_variables
        def format(self, **kwargs):
            return self.template.format(**kwargs)

    class TavilySearchResults:
        def __init__(self, *args, **kwargs):
            pass
        def run(self, query):
            return [{"title": "模擬搜尋結果", "content": f"關於 {query} 的模擬內容"}]

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """報告生成配置類
    
    Attributes:
        llm_config: 大語言模型配置
        tavily_api_key: Tavily 搜索 API 密鑰
        search_top_k: 搜索結果數量
        output_dir: 輸出目錄路徑
        topics: 分析主題列表
    """
    llm_config: Dict[str, Any]
    tavily_api_key: str
    search_top_k: int = 10
    output_dir: str = "reports"
    topics: Optional[List[str]] = None


class FinancialReportGenerator:
    """金融報告生成器
    
    基於 LangChain 和 Tavily 搜索的智能金融分析報告生成系統。
    能夠根據指定主題自動搜索相關信息並生成結構化的分析報告。
    
    Example:
        >>> config = ReportConfig(
        ...     llm_config={
        ...         "model": "gpt-3.5-turbo",
        ...         "api_key": "your-api-key",
        ...         "temperature": 0.1
        ...     },
        ...     tavily_api_key="your-tavily-key",
        ...     topics=["人工智能", "新能源汽車"]
        ... )
        >>> generator = FinancialReportGenerator(config)
        >>> generator.generate_reports()
    """
    
    # 報告生成提示模板
    REPORT_PROMPT = """###角色###
你是一名專業的金融市場分析師，請基於檢索到的信息進行分析，並生成高品質的行情分析報告。

###參考信息###
{doc}

###分析主題###
{topic}

###任務要求###
請基於參考信息對主題進行深入分析，並撰寫專業報告。具體要求：
- 分析要客觀、準確，基於事實數據
- 從參考信息中篩選最相關的內容作為分析依據
- 如果參考信息不足，請明確說明信息限制
- 使用繁體中文撰寫，保持專業性
- 採用 Markdown 格式，結構清晰

###報告結構###
# {topic} 市場分析報告

## 執行摘要
- 一句話總結當前市場狀況

## 市場熱點
- 總結主題相關的重要消息和事件
- 分析市場關注焦點

## 趨勢分析  
- 分析當前行情走勢
- 識別關鍵技術指標和基本面因素
- 評估短期和中期前景

## 風險評估
- 識別主要風險因素
- 評估市場不確定性

## 總結與建議
- 綜合分析結論
- 提供投資建議（如適用）

---
*報告生成時間: {timestamp}*
*數據來源: 網絡公開信息*
*免責聲明: 本報告僅供參考，不構成投資建議*
"""

    def __init__(self, config: ReportConfig):
        """初始化報告生成器
        
        Args:
            config: 報告生成配置
            
        Raises:
            ValueError: 當配置參數無效時
            ConnectionError: 當無法連接到 API 服務時
        """
        self.config = config
        self._validate_config()
        self._setup_search_tool()
        self._setup_llm_chain()
        
        # 確保輸出目錄存在
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"報告生成器初始化完成，輸出目錄: {config.output_dir}")

    def _validate_config(self) -> None:
        """驗證配置參數
        
        Raises:
            ValueError: 當必要參數缺失或無效時
        """
        if not self.config.llm_config:
            raise ValueError("LLM 配置不能為空")
            
        required_llm_keys = ["model", "api_key"]
        for key in required_llm_keys:
            if key not in self.config.llm_config:
                raise ValueError(f"LLM 配置缺少必要參數: {key}")
                
        if not self.config.tavily_api_key:
            raise ValueError("Tavily API 密鑰不能為空")
            
        if self.config.search_top_k <= 0:
            raise ValueError("搜索結果數量必須大於 0")

    def _setup_search_tool(self) -> None:
        """設置網絡搜索工具"""
        try:
            os.environ['TAVILY_API_KEY'] = self.config.tavily_api_key
            self.search_tool = TavilySearchResults(k=self.config.search_top_k)
            logger.info("搜索工具初始化成功")
        except Exception as e:
            logger.error(f"搜索工具初始化失敗: {e}")
            raise ConnectionError(f"無法初始化搜索工具: {e}") from e

    def _setup_llm_chain(self) -> None:
        """設置大語言模型鏈"""
        try:
            llm_config = self.config.llm_config
            
            # 創建 ChatOpenAI 實例
            llm = ChatOpenAI(
                model=llm_config["model"],
                openai_api_key=llm_config["api_key"],
                openai_api_base=llm_config.get("base_url"),
                max_tokens=llm_config.get("max_tokens", 4000),
                temperature=llm_config.get("temperature", 0.1)
            )
            
            # 創建提示模板
            prompt_template = PromptTemplate(
                template=self.REPORT_PROMPT,
                input_variables=["doc", "topic", "timestamp"],
            )
            
            # 創建處理鏈
            self.llm_chain = prompt_template | llm | StrOutputParser()
            logger.info("LLM 鏈初始化成功")
            
        except Exception as e:
            logger.error(f"LLM 鏈初始化失敗: {e}")
            raise ConnectionError(f"無法初始化 LLM 鏈: {e}") from e

    def search_topic_info(self, topic: str) -> str:
        """搜索主題相關信息
        
        Args:
            topic: 搜索主題
            
        Returns:
            str: 搜索結果文本
            
        Raises:
            RuntimeError: 當搜索失敗時
        """
        try:
            logger.info(f"搜索主題信息: {topic}")
            search_results = self.search_tool.invoke({"query": topic})
            
            if not search_results:
                logger.warning(f"未找到主題 '{topic}' 的相關信息")
                return "未找到相關信息"
                
            # 合併搜索結果
            combined_results = "\n---\n".join([
                result.get("content", "") for result in search_results
            ])
            
            logger.info(f"成功獲取 {len(search_results)} 條搜索結果")
            return combined_results
            
        except Exception as e:
            logger.error(f"搜索主題信息失敗: {e}")
            raise RuntimeError(f"搜索失敗: {e}") from e

    def generate_single_report(self, topic: str) -> str:
        """生成單個主題的報告
        
        Args:
            topic: 分析主題
            
        Returns:
            str: 生成的報告內容
            
        Raises:
            RuntimeError: 當報告生成失敗時
        """
        try:
            # 搜索相關信息
            search_results = self.search_topic_info(topic)
            
            # 生成時間戳
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 生成報告
            logger.info(f"生成報告: {topic}")
            report_content = self.llm_chain.invoke({
                'doc': search_results,
                'topic': topic,
                'timestamp': timestamp
            })
            
            logger.info(f"報告生成成功: {topic}")
            return report_content
            
        except Exception as e:
            logger.error(f"報告生成失敗 ({topic}): {e}")
            raise RuntimeError(f"報告生成失敗: {e}") from e

    def save_report(self, topic: str, content: str) -> str:
        """保存報告到文件
        
        Args:
            topic: 報告主題
            content: 報告內容
            
        Returns:
            str: 保存的文件路徑
        """
        # 清理文件名中的特殊字符
        safe_filename = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
        file_path = Path(self.config.output_dir) / f"{safe_filename}_report.md"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"報告已保存: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"保存報告失敗: {e}")
            raise RuntimeError(f"保存報告失敗: {e}") from e

    def generate_reports(self, topics: Optional[List[str]] = None) -> List[str]:
        """批量生成報告
        
        Args:
            topics: 主題列表，如果為 None 則使用配置中的主題
            
        Returns:
            List[str]: 生成的報告文件路徑列表
            
        Raises:
            ValueError: 當沒有指定主題時
        """
        if topics is None:
            topics = self.config.topics
            
        if not topics:
            raise ValueError("必須指定分析主題")
            
        logger.info(f"開始批量生成報告，共 {len(topics)} 個主題")
        
        report_paths = []
        
        # 使用進度條顯示處理進度
        for topic in tqdm(topics, desc="生成報告", unit="個"):
            try:
                # 生成報告內容
                report_content = self.generate_single_report(topic)
                
                # 保存報告
                file_path = self.save_report(topic, report_content)
                report_paths.append(file_path)
                
            except Exception as e:
                logger.error(f"處理主題 '{topic}' 時發生錯誤: {e}")
                continue
                
        logger.info(f"報告生成完成！成功生成 {len(report_paths)} 份報告")
        logger.info(f"輸出目錄: {self.config.output_dir}")
        
        return report_paths

    def get_report_summary(self) -> Dict[str, Any]:
        """獲取報告生成摘要
        
        Returns:
            Dict[str, Any]: 包含統計信息的摘要
        """
        output_dir = Path(self.config.output_dir)
        
        if not output_dir.exists():
            return {"total_reports": 0, "output_dir": str(output_dir)}
            
        report_files = list(output_dir.glob("*_report.md"))
        
        return {
            "total_reports": len(report_files),
            "output_dir": str(output_dir),
            "report_files": [f.name for f in report_files],
            "latest_report": max(report_files, key=lambda f: f.stat().st_mtime).name if report_files else None
        }
