from dataclasses import dataclass

from shop.adapters.card_acquirer import HttpCardAcquirer
from shop.adapters.sqlite_orders import SqliteOrders
from shop.infra.http import HttpClient
from shop.orders.checkout import Checkout
from shop.web.app import App


@dataclass(frozen=True)
class Config:
    db_path: str
    acquirer_url: str


def build_app(config: Config) -> App:
    """Entry point: the only place that creates adapters and wires them together."""
    orders = SqliteOrders(config.db_path)
    acquirer = HttpCardAcquirer(HttpClient(config.acquirer_url))
    return App(Checkout(orders, acquirer))
