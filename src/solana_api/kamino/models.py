from dataclasses import dataclass

@dataclass
class UserBalances:
    token_mint: str
    token_simbol: str
    amount: float
    exchange_rate: float
    decimals: int
    reserve : str
    k_amount: int
    supply_apy : float