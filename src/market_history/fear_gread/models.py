from dataclasses import dataclass

@dataclass
class FearGread:
    value: int
    value_classification: str
    timestamp: int
    time_until_update: int = 0
