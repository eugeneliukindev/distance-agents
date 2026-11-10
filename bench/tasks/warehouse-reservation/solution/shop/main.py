from dataclasses import dataclass

from shop.acquirer import AcquirerClient
from shop.api_client import JsonApiClient
from shop.checkout import Checkout
from shop.db import connect
from shop.warehouse import WarehouseClient
from shop.web.app import App


@dataclass(frozen=True)
class Config:
    db_path: str
    acquirer_url: str
    warehouse_url: str


def build_app(config: Config) -> App:
    warehouse = WarehouseClient(JsonApiClient(config.warehouse_url))
    return App(Checkout(connect(config.db_path), AcquirerClient(config.acquirer_url), warehouse))
