from packages.models.grey_gm0n import GreyGM0N
from packages.models.grey_gm1n import GreyGM1N
from packages.models.grey_gm11 import GreyGM11

class GreyTheory:
    def __init__(self):
        self.gm0n = GreyGM0N()
        self.gm1n = GreyGM1N()
        self.gm11 = GreyGM11()


