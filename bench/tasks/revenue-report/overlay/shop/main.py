from dataclasses import dataclass

from shop.checkout import Checkout
from shop.db import connect
from shop.order_store import SqliteOrderStore
from shop.web.app import App


@dataclass(frozen=True)
class Config:
    db_path: str
    acquirer_url: str


def build_app(config: Config) -> App:
    return App(Checkout(SqliteOrderStore(connect(config.db_path)), config.acquirer_url))
