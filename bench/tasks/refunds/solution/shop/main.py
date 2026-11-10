from dataclasses import dataclass

from shop.checkout import CardPayment, CashOnDelivery, Checkout
from shop.db import connect
from shop.refunds import CardRefund, CashRefund
from shop.web.app import App


@dataclass(frozen=True)
class Config:
    db_path: str
    acquirer_url: str
    tasks_url: str


def build_app(config: Config) -> App:
    refunds = {CardPayment.name: CardRefund(config.acquirer_url), CashOnDelivery.name: CashRefund(config.tasks_url)}
    return App(Checkout(connect(config.db_path), config.acquirer_url, refunds), config.acquirer_url)
