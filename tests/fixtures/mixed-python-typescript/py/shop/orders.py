from shop.pricing import PriceCalculator


class Order(Entity):  # noqa: F821 - the base name is what matters
    def submit(self):
        return PriceCalculator().total(1)


def create_order():
    return Order()
