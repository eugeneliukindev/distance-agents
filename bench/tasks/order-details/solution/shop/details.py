from dataclasses import dataclass
from enum import Enum

MAX_NOTE_LENGTH = 200


class InvalidDetails(Exception):
    pass


class DeliveryWindow(Enum):
    MORNING = "morning"
    EVENING = "evening"


@dataclass(frozen=True)
class DetailsChange:
    """New values for order details; None means "keep the current value"."""

    customer_note: str | None = None
    gift_wrap: bool | None = None
    delivery_window: DeliveryWindow | None = None

    def __post_init__(self) -> None:
        if self.customer_note is not None and len(self.customer_note) > MAX_NOTE_LENGTH:
            raise InvalidDetails(f"customer_note is longer than {MAX_NOTE_LENGTH} characters")
