from dataclasses import dataclass

@dataclass
class IndicatorValues:
    i_type: str = ""
    interval: str = ""
    in1: int = 20
    in2: int = 0
    in3: int = 0
    in4: int = 0

    val1: list = None
    val2: list = None
    val3: list = None
    val4: list = None
