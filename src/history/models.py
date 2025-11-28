from dataclasses import dataclass
import numpy as np

@dataclass
class IntervalData:
    time_open:  np.ndarray
    time_close: np.ndarray
    open:  np.ndarray
    close: np.ndarray
    high: np.ndarray
    low: np.ndarray
    volume: np.ndarray


@dataclass
class PairHistory:
    symbol1: str
    symbol2: str
    intervals: dict  # interval string -> IntervalData