from dataclasses import dataclass

from ..._results import result_alias


@dataclass
class GreyFactory:
    signed_coefficient = result_alias("signed_coefficient_", "Signed factor coefficient.")
    absolute_coefficient = result_alias("equation_value", "Absolute factor coefficient.")
    rank = result_alias("ranking", "Factor rank.")

    name: str = ""
    equation_value: float = 0.0
    ranking: int = 0
    signed_coefficient_: float = 0.0

    @property
    def abs_coefficient_(self):
        return self.equation_value

    @property
    def rank_(self):
        return self.ranking
