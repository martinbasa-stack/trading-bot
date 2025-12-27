from dataclasses import dataclass

@dataclass
class TokenDataClass:
    mint: str
    decimals: int
    supply: int
    name: str
    symbol: str
    uri: str
            