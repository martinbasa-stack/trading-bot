from dataclasses import dataclass

@dataclass
class SaveCandle:
    high: float
    low: float
    close: float 


@dataclass
class Trackers:
    go_to_high : bool = False
    go_to_low : bool = False
    go_to_colse : bool = False
    to_high_done : bool = False
    to_low_done : bool = False
    to_colse_done : bool = False