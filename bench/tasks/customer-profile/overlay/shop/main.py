from dataclasses import dataclass

from shop.checkout import Checkout
from shop.customers import CustomerBook
from shop.db import connect
from shop.web.app import App


@dataclass(frozen=True)
class Config:
    db_path: str
    acquirer_url: str


def build_app(config: Config) -> App:
    db = connect(config.db_path)
    return App(Checkout(db, config.acquirer_url), CustomerBook(db))
