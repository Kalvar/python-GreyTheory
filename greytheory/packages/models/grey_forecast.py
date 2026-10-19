from dataclasses import dataclass
from typing import Optional


@dataclass
class GreyForecast:
    tag: str = ""
    k: int = 0
    original_value: float = 0.0
    forecast_value: float = 0.0
    error_rate: Optional[float] = None
    average_error_rate: Optional[float] = None
