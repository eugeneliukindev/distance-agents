class OrderNotFound(Exception):
    pass


class OrderNotPayable(Exception):
    """The order is already paid."""


class PaymentDeclined(Exception):
    """The bank declined the payment. Retrying with the same card will not help."""


class PaymentUnavailable(Exception):
    """The payment service failed or did not answer. Retrying later may help."""


class OutOfStock(Exception):
    """The warehouse has not enough goods for the order."""


class WarehouseUnavailable(Exception):
    """The warehouse service failed or did not answer. Retrying later may help."""
