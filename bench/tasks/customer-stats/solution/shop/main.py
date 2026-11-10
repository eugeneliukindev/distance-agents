from dataclasses import dataclass

from shop.checkout import Checkout
from shop.db import connect
from shop.repository import SqliteOrderRepository
from shop.web.app import App


@dataclass(frozen=True)
class Config:
    db_path: str
    acquirer_url: str


def build_app(config: Config) -> App:
    orders = SqliteOrderRepository(connect(config.db_path))
    return App(Checkout(orders, config.acquirer_url), orders)
