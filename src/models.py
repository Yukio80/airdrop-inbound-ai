from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from decimal import Decimal

@dataclass
class SwapResult:
    tx_hash: Optional[str]
    amount_in: Decimal
    amount_out_min: Decimal
    token_in: str
    token_out: str
    gas_estimate: int
    status: str  # 'success', 'failed', 'dry_run'

@dataclass
class SupplyResult:
    tx_hash: Optional[str]
    asset: str
    amount: Decimal
    atoken_received: Optional[str]
    gas_used: int
    status: str

@dataclass
class WithdrawResult:
    tx_hash: Optional[str]
    asset: str
    amount: Decimal
    gas_used: int
    status: str

@dataclass
class BridgeResult:
    bridged: bool
    tx_hash: Optional[str]
    balance_before: Decimal
    balance_after: Decimal
    status: str

@dataclass
class QuestTask:
    campaign_id: str
    task_id: str
    task_type: str
    contract_address: str
    calldata_template: str

@dataclass
class ExecutionReport:
    adapter_name: str
    action: str
    status: str
    tx_hash: Optional[str]
    gas_used: Optional[int]
    error: Optional[str] = None
