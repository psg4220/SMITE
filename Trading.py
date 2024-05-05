import enum


class TradeType(enum.Enum):
    BUY = 0
    SELL = 1


class Trade:

    def __init__(
            self,
            trade_type: TradeType,
            base_ticker: str,
            quote_ticker: str,
            price: float,
            amount: float
    ):
        self.trade_type = trade_type
        self.base_ticker = base_ticker
        self.quote_ticker = quote_ticker
        self.price = price
        self.amount = amount

    def total(self):
        return self.price * self.amount

    def reciprocal_price(self):
        return 1 / self.price