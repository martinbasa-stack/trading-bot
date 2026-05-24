from dataclasses import dataclass

@dataclass
class UserBalances:
    token_mint: str
    token_simbol: str
    savings_mint: str
    amount: float
    exchange_rate: float
    decimals: int
    reserve : str
    a_amount: int
    supply_apy : float