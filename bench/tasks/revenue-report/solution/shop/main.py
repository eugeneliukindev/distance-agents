from dataclasses import dataclass
from datetime import datetime, timezone

from shop.checkout import Checkout
from shop.db import connect
from shop.order_store import SqliteOrderStore
from shop.web.app import App


@dataclass(frozen=True)
class Config:
    db_path: str
    acquirer_url: str


def build_app(config: Config) -> App:
    store = SqliteOrderStore(connect(config.db_path))
    checkout = Checkout(store, config.acquirer_url, today=lambda: datetime.now(timezone.utc).date())
    return App(checkout, paid_orders=store)
