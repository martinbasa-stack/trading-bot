from dataclasses import dataclass

@dataclass
class HLRecord:
    high: float
    low: float
    close: float 
    @classmethod
    def from_close(cls, value: float):
        #Create new record where high = low = close = value.
        return cls(high=value, low=value, close=value)