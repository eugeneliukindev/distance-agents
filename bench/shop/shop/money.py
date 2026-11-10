from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    @staticmethod
    def zero(currency: str) -> "Money":
        return Money(Decimal("0"), currency)

    def plus(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def times(self, factor: Decimal) -> "Money":
        """Multiplies and rounds to cents."""
        return Money((self.amount * factor).quantize(Decimal("0.01")), self.currency)

    def _require_same_currency(self, other: "Money") -> None:
        if other.currency != self.currency:
            raise ValueError(f"currency mismatch: {self.currency} and {other.currency}")
