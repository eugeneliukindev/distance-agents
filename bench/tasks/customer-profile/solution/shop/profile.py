import re
from dataclasses import dataclass
from datetime import date

MAX_NAME_LENGTH = 100
PHONE = re.compile(r"\+7[0-9]{10}")


class InvalidProfile(Exception):
    pass


@dataclass(frozen=True)
class Profile:
    """A validated customer profile. Raises InvalidProfile."""

    name: str
    phone: str
    birth_date: date

    def __post_init__(self) -> None:
        if not 1 <= len(self.name) <= MAX_NAME_LENGTH:
            raise InvalidProfile(f"name must be 1 to {MAX_NAME_LENGTH} characters")
        if not PHONE.fullmatch(self.phone):
            raise InvalidProfile("phone must be +7 followed by 10 digits")

    def ensure_born_by(self, today: date) -> None:
        """Raises InvalidProfile if the birth date is after today."""
        if self.birth_date > today:
            raise InvalidProfile("birth_date must not be in the future")
