import math


def round_10s(x: float) -> float:
    if x <= 0 or math.isnan(x):
        return 1

    mult = 10 ** math.floor(math.log10(x))
    return math.ceil(x / mult) * mult
