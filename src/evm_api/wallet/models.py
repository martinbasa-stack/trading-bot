from dataclasses import dataclass

@dataclass
class PendingTrans:
    hash: str
    sent_at: int
    status: str
    trans_stat: str    
    auto_delete: bool = False

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


ONEINCH_ROUTER_ABI = [
    {
        "name": "swap",
        "type": "function",
        "inputs": [
            {"name": "executor", "type": "address"},
            {
                "name": "desc",
                "type": "tuple",
                "components": [
                    {"name": "srcToken", "type": "address"},
                    {"name": "dstToken", "type": "address"},
                    {"name": "srcReceiver", "type": "address"},
                    {"name": "dstReceiver", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "minReturnAmount", "type": "uint256"},
                    {"name": "flags", "type": "uint256"},
                    {"name": "permit", "type": "bytes"},
                ],
            },
            {"name": "permit", "type": "bytes"},
            {"name": "data", "type": "bytes"},
        ],
        "outputs": [{"name": "returnAmount", "type": "uint256"}],
    }
]
