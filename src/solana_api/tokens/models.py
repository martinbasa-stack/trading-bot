from dataclasses import dataclass

@dataclass
class TokenDataClass:
    mint: str
    decimals: int
    supply: int
    name: str
    symbol: str
    uri: str
    en_savings: bool = False
    min_deposit: float = 10.0
    min_apy: float = 0.5 # In %
            