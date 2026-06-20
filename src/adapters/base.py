from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import yaml
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class BaseAdapter(ABC):
    """
    Base class for all protocol adapters.
    Implements global risk controls and common utility methods.
    """
    
    def __init__(self, w3, wallet, config_path: str = "config.yaml"):
        self.w3 = w3
        self.wallet = wallet
        self.config = self._load_config(config_path)
        self.rpc_url = w3.provider.endpoint if hasattr(w3.provider, 'endpoint') else "unknown"
        self.private_key = wallet.key if hasattr(wallet, 'key') else None

    def _load_config(self, path: str) -> Dict[str, Any]:
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    @abstractmethod
    def validate(self, **kwargs) -> bool:
        """Validate transaction parameters against risk rules."""
        pass

    @abstractmethod
    def dry_run(self, **kwargs) -> Any:
        """Simulate transaction and return estimated results."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Broadcast transaction to the network."""
        pass

    def check_risk_rules(self, wallet_balance: float, amount_usd: float, operation: str) -> bool:
        """
        Global risk control check.
        Returns True if operation is allowed, False otherwise.
        """
        risk_cfg = self.config.get("risk", {})
        
        # 1. Check min ETH balance
        if wallet_balance < risk_cfg.get("min_eth_balance", 0.005):
            return False
            
        # 2. Check max position percentage
        # Note: This requires knowing the total wallet value in USD
        # For now, we check against a simple percentage of current balance if amount is in ETH
        # (This logic should be expanded based on the specific adapter)
        
        return True
