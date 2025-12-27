from dataclasses import dataclass

from solders.solders import TransactionStatus

@dataclass
class PendingTrans:
    signature: str
    sent_at: int
    status: int
    trans_stat: TransactionStatus

@dataclass
class SwapResult:
    tx_id: str
    mint_1: str
    amount_1: float
    mint_2: str
    amount_2: float
    price: float
    fee_lamports: int
    slot: int
    timestamp: int