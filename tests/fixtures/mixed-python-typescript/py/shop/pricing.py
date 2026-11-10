# aio-sdlc-node: 11111111-1111-4111-8111-111111111111
class PriceCalculator:
    """Computes prices."""

    def __init__(self):
        self.rate = 1

    def total(self, amount):
        return amount * self.rate

    def _rounding(self, value):
        return value


def format_price(value):
    return str(value)
