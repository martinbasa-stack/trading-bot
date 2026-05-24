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
            

ERC20_ABI = [
    {
        "name": "decimals",
        "outputs": [{"type": "uint8"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "name": "symbol",
        "outputs": [{"type": "string"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "name": "name",
        "outputs": [{"type": "string"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "name": "totalSupply",
        "outputs": [{"type": "uint256"}],
        "inputs": [],
        "stateMutability": "view",
        "type": "function",
    },
]