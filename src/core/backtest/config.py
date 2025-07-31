"""
回測配置管理模組

此模組提供回測配置的定義、驗證和管理功能。
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """回測配置類
    
    定義回測所需的所有參數和設定。
    
    Attributes:
        strategy_name: 策略名稱
        symbols: 股票代碼列表
        start_date: 開始日期
        end_date: 結束日期
        initial_capital: 初始資金
        commission: 手續費率
        slippage: 滑點率
        strategy_params: 策略參數
        risk_params: 風險參數
        benchmark: 基準指數
        rebalance_frequency: 再平衡頻率
        max_position_size: 最大倉位大小
        min_position_size: 最小倉位大小
    """
    
    # 基本參數
    strategy_name: str
    symbols: List[str]
    start_date: Union[str, date, datetime]
    end_date: Union[str, date, datetime]
    initial_capital: float = 100000.0
    
    # 交易成本參數
    commission: float = 0.001  # 0.1%
    slippage: float = 0.001    # 0.1%
    
    # 策略參數
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    # 風險管理參數
    risk_params: Dict[str, Any] = field(default_factory=lambda: {
        'max_position_size': 0.2,      # 單一倉位最大20%
        'min_position_size': 0.01,     # 單一倉位最小1%
        'max_drawdown_limit': 0.15,    # 最大回撤限制15%
        'stop_loss': 0.05,             # 止損5%
        'take_profit': 0.15,           # 止盈15%
    })
    
    # 其他參數
    benchmark: Optional[str] = None
    rebalance_frequency: str = "daily"  # daily, weekly, monthly
    
    # 高級參數
    use_market_timing: bool = False
    use_sector_rotation: bool = False
    use_risk_parity: bool = False
    
    def __post_init__(self):
        """初始化後處理"""
        # 轉換日期格式
        self.start_date = self._parse_date(self.start_date)
        self.end_date = self._parse_date(self.end_date)
        
        # 驗證配置
        self._validate_config()
    
    def _parse_date(self, date_input: Union[str, date, datetime]) -> datetime:
        """解析日期
        
        Args:
            date_input: 日期輸入
            
        Returns:
            datetime: 解析後的日期
            
        Raises:
            ValueError: 當日期格式無效時
        """
        if isinstance(date_input, datetime):
            return date_input
        elif isinstance(date_input, date):
            return datetime.combine(date_input, datetime.min.time())
        elif isinstance(date_input, str):
            try:
                return pd.to_datetime(date_input)
            except Exception as e:
                raise ValueError(f"無效的日期格式: {date_input}") from e
        else:
            raise ValueError(f"不支援的日期類型: {type(date_input)}")
    
    def _validate_config(self) -> None:
        """驗證配置參數
        
        Raises:
            ValueError: 當配置無效時
        """
        # 驗證基本參數
        if not self.strategy_name:
            raise ValueError("策略名稱不能為空")
        
        if not self.symbols:
            raise ValueError("股票代碼列表不能為空")
        
        if self.start_date >= self.end_date:
            raise ValueError("開始日期必須早於結束日期")
        
        if self.initial_capital <= 0:
            raise ValueError("初始資金必須大於0")
        
        # 驗證交易成本參數
        if self.commission < 0 or self.commission > 0.1:
            raise ValueError("手續費率必須在0-10%之間")
        
        if self.slippage < 0 or self.slippage > 0.1:
            raise ValueError("滑點率必須在0-10%之間")
        
        # 驗證風險參數
        max_pos = self.risk_params.get('max_position_size', 0.2)
        min_pos = self.risk_params.get('min_position_size', 0.01)
        
        if max_pos <= 0 or max_pos > 1:
            raise ValueError("最大倉位大小必須在0-100%之間")
        
        if min_pos <= 0 or min_pos > max_pos:
            raise ValueError("最小倉位大小必須大於0且小於最大倉位大小")
        
        # 驗證再平衡頻率
        valid_frequencies = ['daily', 'weekly', 'monthly', 'quarterly']
        if self.rebalance_frequency not in valid_frequencies:
            raise ValueError(f"再平衡頻率必須是: {valid_frequencies}")
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            'strategy_name': self.strategy_name,
            'symbols': self.symbols,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'commission': self.commission,
            'slippage': self.slippage,
            'strategy_params': self.strategy_params,
            'risk_params': self.risk_params,
            'benchmark': self.benchmark,
            'rebalance_frequency': self.rebalance_frequency,
            'use_market_timing': self.use_market_timing,
            'use_sector_rotation': self.use_sector_rotation,
            'use_risk_parity': self.use_risk_parity,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BacktestConfig':
        """從字典創建配置
        
        Args:
            config_dict: 配置字典
            
        Returns:
            BacktestConfig: 配置實例
        """
        return cls(**config_dict)
    
    def get_trading_days(self) -> int:
        """獲取交易天數
        
        Returns:
            int: 交易天數
        """
        # 簡化計算，實際應該考慮交易日曆
        return (self.end_date - self.start_date).days
    
    def get_risk_limit(self, risk_type: str) -> float:
        """獲取風險限制
        
        Args:
            risk_type: 風險類型
            
        Returns:
            float: 風險限制值
        """
        return self.risk_params.get(risk_type, 0)


def validate_backtest_config(config: BacktestConfig) -> tuple[bool, str]:
    """驗證回測配置
    
    Args:
        config: 回測配置
        
    Returns:
        tuple[bool, str]: (是否有效, 錯誤訊息)
    """
    try:
        # 基本驗證已在 __post_init__ 中完成
        
        # 額外的業務邏輯驗證
        
        # 檢查日期範圍是否合理
        days = config.get_trading_days()
        if days < 1:
            return False, "回測期間太短，至少需要1天"
        
        if days > 365 * 10:  # 10年
            return False, "回測期間太長，最多支援10年"
        
        # 檢查股票數量
        if len(config.symbols) > 1000:
            return False, "股票數量太多，最多支援1000隻股票"
        
        # 檢查策略參數
        if config.strategy_params:
            # 這裡可以添加特定策略的參數驗證
            pass
        
        return True, ""
        
    except Exception as e:
        logger.error("配置驗證失敗: %s", e)
        return False, f"配置驗證失敗: {str(e)}"


def create_default_config(
    strategy_name: str,
    symbols: List[str],
    start_date: str,
    end_date: str,
    **kwargs
) -> BacktestConfig:
    """創建預設配置
    
    Args:
        strategy_name: 策略名稱
        symbols: 股票代碼列表
        start_date: 開始日期
        end_date: 結束日期
        **kwargs: 其他參數
        
    Returns:
        BacktestConfig: 配置實例
    """
    return BacktestConfig(
        strategy_name=strategy_name,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        **kwargs
    )


def load_config_from_file(file_path: str) -> BacktestConfig:
    """從文件載入配置
    
    Args:
        file_path: 配置文件路徑
        
    Returns:
        BacktestConfig: 配置實例
        
    Raises:
        FileNotFoundError: 當文件不存在時
        ValueError: 當配置格式無效時
    """
    import json
    import yaml
    from pathlib import Path
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {file_path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() == '.json':
                config_dict = json.load(f)
            elif path.suffix.lower() in ['.yml', '.yaml']:
                config_dict = yaml.safe_load(f)
            else:
                raise ValueError(f"不支援的配置文件格式: {path.suffix}")
        
        return BacktestConfig.from_dict(config_dict)
        
    except Exception as e:
        logger.error("載入配置文件失敗: %s", e)
        raise ValueError(f"載入配置文件失敗: {e}") from e


def save_config_to_file(config: BacktestConfig, file_path: str) -> None:
    """保存配置到文件
    
    Args:
        config: 回測配置
        file_path: 保存路徑
        
    Raises:
        ValueError: 當保存失敗時
    """
    import json
    import yaml
    from pathlib import Path
    
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        config_dict = config.to_dict()
        
        with open(path, 'w', encoding='utf-8') as f:
            if path.suffix.lower() == '.json':
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            elif path.suffix.lower() in ['.yml', '.yaml']:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            else:
                raise ValueError(f"不支援的配置文件格式: {path.suffix}")
        
        logger.info("配置已保存到: %s", file_path)
        
    except Exception as e:
        logger.error("保存配置文件失敗: %s", e)
        raise ValueError(f"保存配置文件失敗: {e}") from e
