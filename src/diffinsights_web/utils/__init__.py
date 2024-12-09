import math


def round_10s(x):
    mult = 10 ** math.floor(math.log10(x))
    return math.ceil(x / mult) * mult
